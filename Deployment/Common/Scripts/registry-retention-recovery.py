#!/usr/bin/env python3
"""Resume one verified abandoned GHCR reservation under its existing host lock.

This tool never takes over a live deployment lock. It only runs from the
trusted main registry-retention workflow, for the exact failed workflow
attempt named by the lock and its immutable reservation journal. The lock is
released only after every journaled package version is confirmed absent.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import urllib.parse


ROOT = Path(__file__).resolve().parents[3]
LIB = Path(__file__).resolve().parent / "Component/lib"
sys.path.insert(0, str(LIB))

import registry_lock_guard  # noqa: E402
from registry_retention import DIGEST, PACKAGE, RetentionError, normalize_repository  # noqa: E402

FINDER_SPEC = importlib.util.spec_from_file_location("registry_recovery_github", LIB / "find-successful-ci-run.py")
if FINDER_SPEC is None or FINDER_SPEC.loader is None:
    raise RuntimeError("GitHub API helper could not be loaded")
FINDER = importlib.util.module_from_spec(FINDER_SPEC)
FINDER_SPEC.loader.exec_module(FINDER)
JOURNAL = registry_lock_guard.JOURNAL
TOKEN_PATTERN = re.compile(r"[0-9]+-[0-9]+-[0-9]+\Z")
OWNER_PATTERN = re.compile(
    r"^(?P<host>[^:\n]+):pid=(?P<pid>[1-9][0-9]*):repo=(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
    r":run=(?P<run>[1-9][0-9]*)-(?P<attempt>[1-9][0-9]*):started=(?P<started>[0-9T:\-]+Z)$"
)
RECORD_SCHEMA = 1
LOCK_DIR_DEFAULT = Path("/tmp/localcluster-deploy.lockdir")


def _github_get(path: str, token: str):
    return FINDER.github_get(path, token)


def _read_regular(path: Path, *, limit: int) -> bytes:
    try:
        info = path.lstat()
    except OSError as error:
        raise RetentionError("the exact registry reservation lock is unavailable") from error
    if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or info.st_size > limit or info.st_mode & 0o022):
        raise RetentionError("the exact registry reservation lock contains an unsafe file")
    try:
        return path.read_bytes()
    except OSError as error:
        raise RetentionError("the exact registry reservation lock is unreadable") from error


def _context(*, owner_run_id: int, owner_attempt: int) -> tuple[str, str, str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    current_run_id = os.environ.get("GITHUB_RUN_ID", "")
    current_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    current_sha = os.environ.get("GITHUB_SHA", "")
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or not re.fullmatch(r"[1-9][0-9]{0,19}", current_run_id)
            or not re.fullmatch(r"[1-9][0-9]{0,19}", current_attempt)
            or not re.fullmatch(r"[0-9a-f]{40}", current_sha)
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or os.environ.get("GITHUB_WORKFLOW_REF")
            != repository + "/.github/workflows/registry-retention.yml@refs/heads/main"
            or os.environ.get("GIT_DIR") or os.environ.get("GIT_WORK_TREE")
            or owner_run_id < 1 or owner_attempt < 1
            or (current_run_id, current_attempt) == (str(owner_run_id), str(owner_attempt))):
        raise RetentionError("registry reservation recovery requires a separate trusted main workflow dispatch")
    return repository, current_run_id, current_attempt, current_sha


def _assert_checkout(current_sha: str, owner_sha: str) -> None:
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        shallow = subprocess.check_output(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, text=True,
        ).strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", owner_sha, current_sha],
            cwd=ROOT, capture_output=True, check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RetentionError("the trusted main checkout could not be verified") from error
    if head != current_sha or shallow != "false" or ancestor.returncode != 0:
        raise RetentionError("the abandoned reservation source is not an ancestor of this complete main checkout")


def _verify_owner_run(repository: str, run_id: int, attempt: int, token: str, current_sha: str) -> dict:
    run = _github_get(f"/repos/{repository}/actions/runs/{run_id}/attempts/{attempt}", token)
    source_repository = run.get("repository") if isinstance(run, dict) else None
    head_repository = run.get("head_repository") if isinstance(run, dict) else None
    source_name = source_repository.get("full_name") if isinstance(source_repository, dict) else None
    head_name = head_repository.get("full_name") if isinstance(head_repository, dict) else None
    expected = {
        "id": run_id,
        "run_attempt": attempt,
        "head_branch": "main",
        "event": "workflow_dispatch",
        "status": "completed",
        "conclusion": "failure",
    }
    if (not isinstance(run, dict) or any(run.get(key) != value for key, value in expected.items())
            or str(run.get("path", "")).split("@", 1)[0] != ".github/workflows/registry-retention.yml"
            or not isinstance(run.get("head_sha"), str)
            or not re.fullmatch(r"[0-9a-f]{40}", run["head_sha"])
            or not isinstance(source_name, str) or source_name.casefold() != repository.casefold()
            or not isinstance(head_name, str) or head_name.casefold() != repository.casefold()):
        raise RetentionError("the lock owner is not the exact completed failed registry-retention attempt")
    _assert_checkout(current_sha, run["head_sha"])
    return run


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as error:
        raise RetentionError("the lock owner process state is unavailable") from error
    return True


def _assert_no_owned_work() -> None:
    if os.name != "posix" or not Path("/proc").is_dir():
        raise RetentionError("reservation recovery must run on the native Linux deployment host")
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in {os.getpid(), os.getppid()}:
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", errors="replace")
        except FileNotFoundError:
            continue
        except PermissionError as error:
            raise RetentionError("a host process could not be inspected for active deployment work") from error
        except OSError as error:
            if not (entry / "cmdline").exists():
                continue
            raise RetentionError("the host process inventory is incomplete") from error
        if "ansible-playbook" in command or re.search(r"(?:^|[/\s])registry-retention\.py(?:$|[\s])", command):
            raise RetentionError("a registry-retention or deployment process is still active on the lock host")


def _lock_dir() -> Path:
    raw = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_DIR", str(LOCK_DIR_DEFAULT))
    path = Path(raw)
    if not path.is_absolute():
        raise RetentionError("the shared deployment lock path must be absolute")
    try:
        info = path.lstat()
    except OSError as error:
        raise RetentionError("the shared deployment lock is unavailable") from error
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise RetentionError("the shared deployment lock directory is unsafe")
    return path


def _load_lock(repository: str, owner_run_id: int, owner_attempt: int, *, require_journal: bool) -> dict:
    lock_dir = _lock_dir()
    expected_files = {"token", "owner", "created_epoch"} | ({JOURNAL} if require_journal else set())
    try:
        names = {item.name for item in lock_dir.iterdir()}
    except OSError as error:
        raise RetentionError("the shared deployment lock contents are unavailable") from error
    if names != expected_files:
        if not require_journal and JOURNAL in names:
            raise RetentionError("the exact reservation journal is still pending; lock remains held")
        raise RetentionError("the shared deployment lock has unexpected contents; it was left untouched")

    token = _read_regular(lock_dir / "token", limit=256).decode("ascii", errors="strict").strip()
    if not TOKEN_PATTERN.fullmatch(token):
        raise RetentionError("the shared deployment lock token is malformed")
    owner_line = _read_regular(lock_dir / "owner", limit=2048).decode("utf-8", errors="strict").strip()
    owner = OWNER_PATTERN.fullmatch(owner_line)
    if owner is None:
        raise RetentionError("the shared deployment lock owner is malformed")
    if (owner.group("host") != socket.gethostname()
            or owner.group("repo").casefold() != repository.casefold()
            or int(owner.group("run")) != owner_run_id
            or int(owner.group("attempt")) != owner_attempt):
        raise RetentionError("the shared lock does not belong to the requested registry-retention attempt")
    try:
        datetime.fromisoformat(owner.group("started").replace("Z", "+00:00"))
    except ValueError as error:
        raise RetentionError("the shared deployment lock start time is malformed") from error
    if _pid_is_alive(int(owner.group("pid"))):
        raise RetentionError("the exact registry-retention lock owner process is still alive")
    epoch = _read_regular(lock_dir / "created_epoch", limit=64).decode("ascii", errors="strict").strip()
    if not re.fullmatch(r"[1-9][0-9]{0,19}", epoch):
        raise RetentionError("the shared deployment lock creation time is malformed")

    journal = None
    if require_journal:
        journal = registry_lock_guard._read(lock_dir / JOURNAL)
        expected_repository = normalize_repository("https://github.com/" + repository)
        reservation_id = f"run-{owner_run_id}-{owner_attempt}"
        if journal["repository"].casefold() != expected_repository.casefold() or journal["reservation_id"] != reservation_id:
            raise RetentionError("the registry journal does not match this repository and exact failed attempt")
        if not 1 <= len(journal["candidates"]) <= 100:
            raise RetentionError("the registry journal is outside its fixed candidate bound")
        owner_name = repository.split("/", 1)[0]
        for item in journal["candidates"].values():
            package_owner = item["identity"]["package"].removeprefix("ghcr.io/").split("/", 1)[0]
            if package_owner.casefold() != owner_name.casefold() or not DIGEST.fullmatch(item["identity"]["digest"]):
                raise RetentionError("the registry journal contains an out-of-scope package identity")

    _assert_no_owned_work()
    return {
        "lock_dir": lock_dir,
        "token": token,
        "owner_line": owner_line,
        "owner": owner,
        "journal": journal,
    }


def _record_path(value: str) -> Path:
    runner_temp = os.environ.get("RUNNER_TEMP", "")
    if not runner_temp:
        raise RetentionError("the isolated runner temporary directory is unavailable")
    root = Path(runner_temp).resolve()
    path = Path(value)
    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise RetentionError("registry recovery record path must be absolute")
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as error:
        raise RetentionError("registry recovery record directory is unavailable") from error
    resolved = parent / path.name
    if root not in resolved.parents or not parent.is_dir():
        raise RetentionError("registry recovery record must remain inside runner temporary storage")
    return resolved


def _write_record(path: Path, value: dict) -> None:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(raw) > 1024 * 1024:
        raise RetentionError("registry recovery record exceeds its fixed bound")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise RetentionError("registry recovery record could not be created safely") from error


def _record_mac(value: dict, lock_token: str) -> str:
    unsigned = {key: item for key, item in value.items() if key != "record_hmac_sha256"}
    raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(lock_token.encode("ascii"), raw, hashlib.sha256).hexdigest()


def prepare(
    *,
    owner_run_id: int,
    owner_attempt: int,
    record: str = "",
) -> tuple[str, dict]:
    repository, current_run_id, current_attempt, current_sha = _context(
        owner_run_id=owner_run_id, owner_attempt=owner_attempt,
    )
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RetentionError("the existing workflow token is unavailable for recovery verification")
    _verify_owner_run(repository, owner_run_id, owner_attempt, token, current_sha)
    snapshot = _load_lock(repository, owner_run_id, owner_attempt, require_journal=True)
    journal = snapshot["journal"]
    counts = {"reserved": 0, "delete_requested": 0, "absent": 0}
    for candidate in journal["candidates"].values():
        counts[candidate["state"]] += 1
    summary = {
        "reservation_id": journal["reservation_id"],
        "candidate_count": len(journal["candidates"]),
        "states": counts,
        "repository": repository,
    }
    if record:
        record_path = _record_path(record)
        candidate_identities = []
        for key in journal["order"]:
            candidate_identities.append(journal["candidates"][key]["identity"])
        state = {
            "schema_version": RECORD_SCHEMA,
            "recovery_run_id": int(current_run_id),
            "recovery_attempt": int(current_attempt),
            "owner_run_id": owner_run_id,
            "owner_attempt": owner_attempt,
            "reservation_id": journal["reservation_id"],
            "owner_line_sha256": hashlib.sha256(snapshot["owner_line"].encode()).hexdigest(),
            "token_sha256": hashlib.sha256(snapshot["token"].encode()).hexdigest(),
            "journal_fingerprint": journal["fingerprint"],
            "candidates": candidate_identities,
        }
        state["record_hmac_sha256"] = _record_mac(state, snapshot["token"])
        _write_record(record_path, state)
    return snapshot["token"], summary


def _existing_version_ids(package: str, token: str, *, github_get=None) -> set[int]:
    if not PACKAGE.fullmatch(package):
        raise RetentionError("registry recovery package is malformed")
    getter = github_get or _github_get
    owner, name = package.removeprefix("ghcr.io/").split("/", 1)
    owner = urllib.parse.quote(owner, safe="")
    name = urllib.parse.quote(name, safe="")
    identities = set()
    for page in range(1, 101):
        result = getter(
            f"/users/{owner}/packages/container/{name}/versions?per_page=100&page={page}",
            token,
        )
        if not isinstance(result, list) or len(result) > 100:
            raise RetentionError("the exact GHCR version inventory is incomplete")
        for item in result:
            if not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] <= 0:
                raise RetentionError("the exact GHCR version inventory is malformed")
            if item["id"] in identities:
                raise RetentionError("the exact GHCR version inventory contains duplicate IDs")
            identities.add(item["id"])
        if len(result) < 100:
            return identities
    raise RetentionError("the exact GHCR version inventory exceeds its page bound")


def release(*, owner_run_id: int, owner_attempt: int, record: str) -> dict:
    repository, current_run_id, current_attempt, current_sha = _context(
        owner_run_id=owner_run_id, owner_attempt=owner_attempt,
    )
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RetentionError("the existing workflow token is unavailable for recovery verification")
    path = _record_path(record)
    raw = _read_regular(path, limit=1024 * 1024)
    try:
        state = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RetentionError("the registry recovery record is unreadable") from error
    expected_keys = {
        "schema_version", "recovery_run_id", "recovery_attempt", "owner_run_id", "owner_attempt",
        "reservation_id", "owner_line_sha256", "token_sha256", "journal_fingerprint", "candidates",
        "record_hmac_sha256",
    }
    if (not isinstance(state, dict) or set(state) != expected_keys
            or type(state.get("schema_version")) is not int or state.get("schema_version") != RECORD_SCHEMA
            or type(state.get("recovery_run_id")) is not int
            or state.get("recovery_run_id") != int(current_run_id)
            or type(state.get("recovery_attempt")) is not int
            or state.get("recovery_attempt") != int(current_attempt)
            or type(state.get("owner_run_id")) is not int
            or state.get("owner_run_id") != owner_run_id
            or type(state.get("owner_attempt")) is not int
            or state.get("owner_attempt") != owner_attempt
            or state.get("reservation_id") != f"run-{owner_run_id}-{owner_attempt}"
            or not isinstance(state.get("owner_line_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", state["owner_line_sha256"])
            or not isinstance(state.get("token_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", state["token_sha256"])
            or not isinstance(state.get("journal_fingerprint"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", state["journal_fingerprint"])
            or not isinstance(state.get("record_hmac_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", state["record_hmac_sha256"])
            or not isinstance(state.get("candidates"), list) or not 1 <= len(state["candidates"]) <= 100):
        raise RetentionError("the registry recovery record does not match this exact workflow attempt")
    seen_identities = set()
    owner_name = repository.split("/", 1)[0]
    for candidate in state["candidates"]:
        if (not isinstance(candidate, dict)
                or set(candidate) != {"package", "version_id", "digest", "tags", "created"}
                or not PACKAGE.fullmatch(str(candidate.get("package", "")))
                or type(candidate.get("version_id")) is not int or candidate["version_id"] <= 0
                or not DIGEST.fullmatch(str(candidate.get("digest", "")))
                or not isinstance(candidate.get("tags"), list)
                or any(not isinstance(tag, str) or not tag for tag in candidate["tags"])
                or len(candidate["tags"]) != len(set(candidate["tags"]))
                or not isinstance(candidate.get("created"), str)):
            raise RetentionError("the registry recovery record contains an invalid candidate identity")
        package_owner = candidate["package"].removeprefix("ghcr.io/").split("/", 1)[0]
        if package_owner.casefold() != owner_name.casefold():
            raise RetentionError("the registry recovery record contains an out-of-scope package")
        try:
            created = datetime.fromisoformat(candidate["created"])
            if created.tzinfo is None or created.utcoffset() is None:
                raise ValueError("missing timezone")
        except ValueError as error:
            raise RetentionError("the registry recovery record has an invalid creation time") from error
        identity = candidate["package"], candidate["version_id"]
        if identity in seen_identities:
            raise RetentionError("the registry recovery record contains duplicate version identities")
        seen_identities.add(identity)

    _verify_owner_run(repository, owner_run_id, owner_attempt, token, current_sha)
    snapshot = _load_lock(repository, owner_run_id, owner_attempt, require_journal=True)
    if (hashlib.sha256(snapshot["owner_line"].encode()).hexdigest() != state["owner_line_sha256"]
            or hashlib.sha256(snapshot["token"].encode()).hexdigest() != state["token_sha256"]
            or not hmac.compare_digest(_record_mac(state, snapshot["token"]), state["record_hmac_sha256"])):
        raise RetentionError("the shared deployment lock changed during registry recovery")
    journal = snapshot["journal"]
    journal_candidates = [journal["candidates"][key]["identity"] for key in journal["order"]]
    if (journal["fingerprint"] != state["journal_fingerprint"]
            or journal_candidates != state["candidates"]
            or any(entry["state"] != "absent" or entry["api_status"] != 404
                   for entry in journal["candidates"].values())):
        raise RetentionError("the exact registry reservation still has unresolved candidate states")

    by_package: dict[str, set[int]] = {}
    for candidate in state["candidates"]:
        by_package.setdefault(candidate["package"], set()).add(candidate["version_id"])
    present = 0
    for package, candidate_ids in by_package.items():
        present += len(candidate_ids & _existing_version_ids(package, token))
    if present:
        raise RetentionError("reserved GHCR versions remain present; the shared lock stays held")

    # Recheck owner, token, process and directory contents immediately before
    # releasing the lock. No recursive cleanup or unknown-file deletion occurs.
    snapshot = _load_lock(repository, owner_run_id, owner_attempt, require_journal=True)
    if (hashlib.sha256(snapshot["owner_line"].encode()).hexdigest() != state["owner_line_sha256"]
            or hashlib.sha256(snapshot["token"].encode()).hexdigest() != state["token_sha256"]
            or not hmac.compare_digest(_record_mac(state, snapshot["token"]), state["record_hmac_sha256"])):
        raise RetentionError("the shared deployment lock changed before release")
    journal = snapshot["journal"]
    if (journal["fingerprint"] != state["journal_fingerprint"]
            or any(entry["state"] != "absent" or entry["api_status"] != 404
                   for entry in journal["candidates"].values())):
        raise RetentionError("the exact registry reservation changed before release")
    journal_path = snapshot["lock_dir"] / JOURNAL
    journal_path.unlink()
    registry_lock_guard._sync_directory(snapshot["lock_dir"])
    snapshot = _load_lock(repository, owner_run_id, owner_attempt, require_journal=False)
    if (hashlib.sha256(snapshot["owner_line"].encode()).hexdigest() != state["owner_line_sha256"]
            or hashlib.sha256(snapshot["token"].encode()).hexdigest() != state["token_sha256"]
            or not hmac.compare_digest(_record_mac(state, snapshot["token"]), state["record_hmac_sha256"])):
        raise RetentionError("the shared deployment lock changed while releasing the verified reservation")
    for name in ("owner", "token", "created_epoch"):
        (snapshot["lock_dir"] / name).unlink()
    try:
        snapshot["lock_dir"].rmdir()
    except OSError as error:
        raise RetentionError("the verified registry lock files were removed but the lock directory remains") from error
    path.unlink()
    return {
        "outcome": "reservation_reconciled",
        "reservation_id": state["reservation_id"],
        "candidate_count": len(state["candidates"]),
        "confirmed_absent": len(state["candidates"]) - present,
        "lock": "released",
        "mutation": "lock-release-only",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "release"))
    parser.add_argument("--owner-run-id", type=int, required=True)
    parser.add_argument("--owner-attempt", type=int, required=True)
    parser.add_argument("--record", default="")
    parser.add_argument("--print-lock-token", action="store_true",
                        help="Print the verified lock token for shell command substitution only.")
    args = parser.parse_args(argv)
    if args.owner_run_id < 1 or args.owner_attempt < 1:
        parser.error("owner run and attempt must be positive")
    if args.action == "prepare":
        token, summary = prepare(
            owner_run_id=args.owner_run_id, owner_attempt=args.owner_attempt, record=args.record,
        )
        print(json.dumps(summary, sort_keys=True), file=sys.stderr)
        if args.print_lock_token:
            print(token)
        elif args.record:
            print("Registry reservation owner verified; the original lock remains held.")
        return 0
    if args.print_lock_token or not args.record:
        parser.error("release requires --record and cannot print a lock token")
    result = release(owner_run_id=args.owner_run_id, owner_attempt=args.owner_attempt, record=args.record)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RetentionError, subprocess.SubprocessError, UnicodeError) as error:
        print(f"Registry reservation recovery failed closed; the lock was left for inspection: {error}", file=sys.stderr)
        raise SystemExit(1)
