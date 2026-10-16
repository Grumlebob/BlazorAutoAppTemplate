from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Any


DEFAULT_REPOSITORY = "Grumlebob/BlazorAutoAppTemplate"
SCHEMA_VERSION = 1
DEFAULT_MAX_BYTES = 1024 * 1024 * 1024
SUCCESS_RETENTION = timedelta(days=3)
FAILURE_RETENTION = timedelta(days=7)
RUN_RE = re.compile(r"^[1-9][0-9]*$")
JOBS = {"validate", "publish-main"}
STATUSES = {"success", "failure"}
COUNTER_NAMES = (
    "total",
    "executed",
    "passed",
    "failed",
    "error",
    "timeout",
    "aborted",
    "inconclusive",
    "notExecuted",
    "warning",
    "completed",
    "inProgress",
    "pending",
)


class ReportStoreError(ValueError):
    pass


def _fail(message: str) -> None:
    raise ReportStoreError(message)


def _validate_repository(repository: str) -> tuple[str, str]:
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        _fail("repository must use owner/name format")
    owner, name = repository.split("/", 1)
    if owner in {".", ".."} or name in {".", ".."}:
        _fail("repository contains an unsafe path component")
    return owner, name


def default_root(repository: str | None = None) -> Path:
    selected = repository or os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY)
    owner, name = _validate_repository(selected)
    base = Path(os.environ.get("CI_REPORT_ROOT", Path.home() / ".local" / "state" / "github-actions-reports")).expanduser()
    return base / owner.lower() / name.lower()


def _validate_identity(run_id: str, attempt: str, job: str) -> None:
    if not RUN_RE.fullmatch(run_id):
        _fail("run ID must be a positive decimal string")
    if not RUN_RE.fullmatch(attempt):
        _fail("run attempt must be a positive decimal string")
    if job not in JOBS:
        _fail(f"job must be one of: {', '.join(sorted(JOBS))}")


def _entry_name(run_id: str, attempt: str, job: str) -> str:
    _validate_identity(run_id, attempt, job)
    return f"{run_id}-{attempt}-{job}"


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("report manifest has an invalid created_utc value")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ReportStoreError("report manifest has an invalid created_utc value") from error
    if parsed.tzinfo != timezone.utc:
        _fail("report manifest timestamp must be UTC")
    return parsed


def _empty_counts() -> dict[str, int]:
    return {name: 0 for name in COUNTER_NAMES}


def _trx_counts(report_dir: Path) -> tuple[dict[str, int], int, int]:
    totals = _empty_counts()
    trx_count = 0
    malformed_count = 0
    for path in report_dir.rglob("*.trx"):
        trx_count += 1
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            malformed_count += 1
            continue
        for summary in root.iter():
            if summary.tag.rsplit("}", 1)[-1] != "ResultSummary":
                continue
            for counters in summary:
                if counters.tag.rsplit("}", 1)[-1] != "Counters":
                    continue
                for name in COUNTER_NAMES:
                    raw = counters.attrib.get(name)
                    if raw is not None and raw.isdigit():
                        totals[name] += int(raw)
    return totals, trx_count, malformed_count


def _safe_tree_bytes(path: Path) -> int:
    if path.is_symlink():
        return path.lstat().st_size
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        return 0
    total = 0
    for child in path.iterdir():
        total += _safe_tree_bytes(child)
    return total


def _reject_symlinks(path: Path) -> None:
    if path.is_symlink():
        _fail(f"report input must not contain symbolic links: {path}")
    if path.is_dir():
        for child in path.iterdir():
            _reject_symlinks(child)


def _read_manifest(entry: Path, repository: str | None = DEFAULT_REPOSITORY) -> dict[str, Any] | None:
    if not entry.is_dir() or entry.is_symlink():
        return None
    manifest_path = entry / "ci-report.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return None
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    required = {
        "schema_version", "repository", "run_id", "attempt", "job", "status",
        "created_utc", "pinned", "report_bytes", "file_count", "trx_count", "malformed_trx_count", "trx_counts",
    }
    if (
        set(value) != required
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != SCHEMA_VERSION
        or (repository is not None and value.get("repository") != repository)
    ):
        return None
    try:
        _validate_repository(value.get("repository"))
    except ReportStoreError:
        return None
    if not all(isinstance(value.get(key), str) for key in ("run_id", "attempt", "job", "status")):
        return None
    try:
        _validate_identity(value["run_id"], value["attempt"], value["job"])
        _parse_utc(value["created_utc"])
    except (KeyError, ReportStoreError):
        return None
    if entry.name != _entry_name(value["run_id"], value["attempt"], value["job"]):
        return None
    if value.get("status") not in STATUSES or type(value.get("pinned")) is not bool:
        return None
    for key in ("report_bytes", "file_count", "trx_count", "malformed_trx_count"):
        if type(value.get(key)) is not int or value[key] < 0:
            return None
    if not isinstance(value.get("trx_counts"), dict) or set(value["trx_counts"]) != set(COUNTER_NAMES):
        return None
    if any(type(number) is not int or number < 0 for number in value["trx_counts"].values()):
        return None
    return value


def _lock(root: Path):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink():
        _fail(f"report root must not be a symbolic link: {root}")
    try:
        root.chmod(0o700)
    except OSError as error:
        raise ReportStoreError(f"cannot secure report root: {error}") from error
    lock_path = root / ".ci-report-store.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _unlock(descriptor: int) -> None:
    fcntl.flock(descriptor, fcntl.LOCK_UN)
    os.close(descriptor)


def _known_entries(root: Path, repository: str = DEFAULT_REPOSITORY) -> list[tuple[Path, dict[str, Any]]]:
    result: list[tuple[Path, dict[str, Any]]] = []
    for entry in root.iterdir():
        manifest = _read_manifest(entry, repository)
        if manifest is not None:
            result.append((entry, manifest))
    return result


def _unknown_entries(root: Path) -> list[str]:
    return [
        entry.name
        for entry in root.iterdir()
        if entry.name != ".ci-report-store.lock" and _read_manifest(entry, None) is None
    ]


def _store_bytes(root: Path) -> int:
    total = 0
    for child in root.iterdir():
        if child.name == ".ci-report-store.lock":
            continue
        total += _safe_tree_bytes(child)
    return total


def _prune_result(
    root: Path,
    *,
    repository: str,
    now: datetime,
    max_bytes: int,
    protect: Path | None = None,
    apply: bool,
) -> dict[str, Any]:
    _validate_repository(repository)
    unknown = _unknown_entries(root)
    if unknown:
        return {
            "planned": [], "removed": [], "unknown_entries": unknown,
            "blocked_reason": "unknown_store_entries", "dry_run": not apply,
        }

    entries = _known_entries(root, repository)
    entries.sort(key=lambda item: _parse_utc(item[1]["created_utc"]))
    planned: list[str] = []
    planned_set: set[str] = set()
    total = _store_bytes(root)

    def expired(entry: Path, manifest: dict[str, Any]) -> bool:
        if manifest["pinned"] or entry == protect:
            return False
        age_limit = SUCCESS_RETENTION if manifest["status"] == "success" else FAILURE_RETENTION
        return now - _parse_utc(manifest["created_utc"]) >= age_limit

    for entry, manifest in entries:
        if expired(entry, manifest):
            planned.append(entry.name)
            planned_set.add(entry.name)
            total -= _safe_tree_bytes(entry)

    if total > max_bytes:
        for entry, manifest in entries:
            if total <= max_bytes:
                break
            if manifest["pinned"] or entry == protect or entry.name in planned_set:
                continue
            size = _safe_tree_bytes(entry)
            planned.append(entry.name)
            planned_set.add(entry.name)
            total -= size

    removed: list[str] = []
    if apply:
        for name in planned:
            entry = root / name
            manifest = _read_manifest(entry, repository)
            if manifest is None or manifest["pinned"] or entry == protect:
                _fail(f"report entry changed after retention selection: {name}")
            shutil.rmtree(entry)
            removed.append(name)
    return {
        "planned": planned,
        "removed": removed,
        "unknown_entries": [],
        "blocked_reason": "protected_data_exceeds_byte_cap" if total > max_bytes else None,
        "dry_run": not apply,
    }


def _prune(
    root: Path,
    *,
    repository: str = DEFAULT_REPOSITORY,
    now: datetime,
    max_bytes: int,
    protect: Path | None = None,
) -> list[str]:
    return _prune_result(
        root, repository=repository, now=now, max_bytes=max_bytes, protect=protect, apply=True,
    )["removed"]


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def save_report(
    *,
    source: Path,
    root: Path,
    run_id: str,
    attempt: str,
    job: str,
    status: str,
    repository: str = DEFAULT_REPOSITORY,
    step_summary: Path | None = None,
    runner_name: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    _validate_identity(run_id, attempt, job)
    _validate_repository(repository)
    if status not in STATUSES:
        if status == "cancelled":
            return None
        _fail("status must be success or failure")
    if type(max_bytes) is not int or max_bytes < 1:
        _fail("maximum report-store size must be a positive integer")
    source = source.expanduser()
    if source.is_symlink():
        _fail("report source must not be a symbolic link")
    if source.exists():
        if not source.is_dir():
            _fail("report source must be a directory")
        _reject_symlinks(source)
    created = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    entry_name = _entry_name(run_id, attempt, job)
    descriptor = _lock(root)
    try:
        destination = root / entry_name
        if destination.exists() or destination.is_symlink():
            _fail(f"report entry already exists: {entry_name}")
        temporary = Path(tempfile.mkdtemp(prefix=f".pending-{entry_name}-", dir=root))
        temporary.chmod(0o700)
        try:
            report_dir = temporary / "report"
            if source.exists():
                shutil.copytree(source, report_dir, copy_function=shutil.copy2)
            else:
                report_dir.mkdir(mode=0o700)
            for file in report_dir.rglob("*"):
                if file.is_file() and not file.is_symlink():
                    file.chmod(stat.S_IMODE(file.stat().st_mode) & 0o600 or 0o600)
            counts, trx_count, malformed_count = _trx_counts(report_dir)
            report_bytes = _safe_tree_bytes(report_dir)
            file_count = sum(1 for path in report_dir.rglob("*") if path.is_file())
            metadata: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "repository": repository,
                "run_id": run_id,
                "attempt": attempt,
                "job": job,
                "status": status,
                "created_utc": _utc_text(created),
                "pinned": False,
                "report_bytes": report_bytes,
                "file_count": file_count,
                "trx_count": trx_count,
                "malformed_trx_count": malformed_count,
                "trx_counts": counts,
            }
            _write_json(temporary / "ci-report.json", metadata)
            os.replace(temporary, destination)
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

        _prune(root, repository=repository, now=created, max_bytes=max_bytes, protect=destination)
        if _store_bytes(root) > max_bytes:
            shutil.rmtree(destination)
            _fail("report store exceeds its byte cap after eligible reports were pruned")
        metadata["runner_name"] = runner_name or socket.gethostname()
        if step_summary is not None:
            append_summary(step_summary, metadata)
        return metadata
    finally:
        _unlock(descriptor)


def append_summary(path: Path, metadata: dict[str, Any]) -> None:
    counts = metadata["trx_counts"]
    host = metadata.get("runner_name", "the runner host")
    report_count = metadata["trx_count"]
    lines = [
        "## Local CI reports",
        f"- Status: `{metadata['status']}`; job: `{metadata['job']}`; "
        f"stored files: {metadata['file_count']} ({metadata['report_bytes']} bytes); TRX files: {report_count}.",
    ]
    if metadata["job"] == "validate":
        lines.append("- Test totals: " + ", ".join(
            f"{label}={counts[name]}" for label, name in (
                ("total", "total"), ("passed", "passed"), ("failed", "failed"),
                ("errors", "error"), ("not executed", "notExecuted"),
            )
        ))
    if metadata["malformed_trx_count"]:
        lines.append(f"- Malformed TRX files preserved: {metadata['malformed_trx_count']}.")
    lines.extend((
        f"- Saved on runner `{host}` for {3 if metadata['status'] == 'success' else 7} days, subject to the 1 GiB store cap.",
        "- Retrieve on that runner after checking out this commit:",
        "  `python3 Scripts/CI/ci_report_store.py get --run-id "
        f"{metadata['run_id']} --attempt {metadata['attempt']} --job {metadata['job']} "
        f"--repository {metadata['repository']} "
        f"--destination ./ci-report-{metadata['run_id']}-{metadata['attempt']}-{metadata['job']}`",
    ))
    with path.open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def list_reports(root: Path, repository: str = DEFAULT_REPOSITORY) -> list[dict[str, Any]]:
    _validate_repository(repository)
    if not root.exists():
        return []
    descriptor = _lock(root)
    try:
        reports = [manifest for _, manifest in _known_entries(root, repository)]
        return sorted(reports, key=lambda value: (int(value["run_id"]), int(value["attempt"]), value["job"]))
    finally:
        _unlock(descriptor)


def _mutate_pin(
    root: Path,
    run_id: str,
    attempt: str,
    job: str,
    pinned: bool,
    repository: str = DEFAULT_REPOSITORY,
) -> dict[str, Any]:
    name = _entry_name(run_id, attempt, job)
    _validate_repository(repository)
    descriptor = _lock(root)
    try:
        entry = root / name
        metadata = _read_manifest(entry, repository)
        if metadata is None:
            _fail(f"no valid report entry exists: {name}")
        metadata["pinned"] = pinned
        _write_json(entry / "ci-report.json", metadata)
        return metadata
    finally:
        _unlock(descriptor)


def restore_report(
    root: Path,
    run_id: str,
    attempt: str,
    job: str,
    destination: Path,
    repository: str = DEFAULT_REPOSITORY,
) -> Path:
    name = _entry_name(run_id, attempt, job)
    _validate_repository(repository)
    descriptor = _lock(root)
    try:
        entry = root / name
        if _read_manifest(entry, repository) is None:
            _fail(f"no valid report entry exists: {name}")
        source = entry / "report"
        if not source.is_dir() or source.is_symlink():
            _fail(f"report payload is missing or unsafe: {name}")
        _reject_symlinks(source)
        destination = destination.expanduser()
        if destination.exists() or destination.is_symlink():
            _fail("report destination already exists")
        resolved_root = root.resolve(strict=True)
        resolved_destination = destination.resolve(strict=False)
        if resolved_destination == resolved_root or resolved_root in resolved_destination.parents:
            _fail("report destination must be outside the report store")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(source, destination, copy_function=shutil.copy2)
        except BaseException:
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            raise
        return destination
    finally:
        _unlock(descriptor)


def _add_identity(parser: argparse.ArgumentParser, *, include_job: bool = True) -> None:
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    if include_job:
        parser.add_argument("--job", choices=sorted(JOBS), required=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Store and retrieve bounded runner-local GitHub Actions reports.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    save_parser = subparsers.add_parser("save", help="save one terminal job's diagnostic reports")
    _add_identity(save_parser, include_job=False)
    save_parser.add_argument("--root", type=Path, help="private local report root (defaults under the runner account)")
    save_parser.add_argument("--source", type=Path, required=True)
    save_parser.add_argument("--job", choices=sorted(JOBS), required=True)
    save_parser.add_argument("--status", choices=("success", "failure", "cancelled"), required=True)
    save_parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    save_parser.add_argument("--step-summary", type=Path)
    save_parser.add_argument("--runner-name", default=os.environ.get("RUNNER_NAME"))

    get_parser = subparsers.add_parser("get", help="restore a stored job report directory")
    _add_identity(get_parser)
    get_parser.add_argument("--root", type=Path, help="private local report root (defaults under the runner account)")
    get_parser.add_argument("--destination", type=Path, required=True)

    list_parser = subparsers.add_parser("list", help="list recognized local reports")
    list_parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY))
    list_parser.add_argument("--root", type=Path, help="private local report root (defaults under the runner account)")
    list_parser.add_argument("--json", action="store_true")

    prune_parser = subparsers.add_parser("prune", help="remove expired or over-cap unpinned reports")
    prune_parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY))
    prune_parser.add_argument("--root", type=Path, help="private local report root (defaults under the runner account)")
    prune_parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    prune_parser.add_argument("--dry-run", action="store_true", help="report eligible deletions without removing reports")

    pin_parser = subparsers.add_parser("pin", help="protect a report from retention cleanup")
    _add_identity(pin_parser)
    pin_parser.add_argument("--root", type=Path, help="private local report root (defaults under the runner account)")
    unpin_parser = subparsers.add_parser("unpin", help="allow retention cleanup of a protected report")
    _add_identity(unpin_parser)
    unpin_parser.add_argument("--root", type=Path, help="private local report root (defaults under the runner account)")

    args = parser.parse_args(argv)
    try:
        _validate_repository(args.repository)
        args.root = args.root or default_root(args.repository)
        if args.command == "save":
            result = save_report(
                source=args.source,
                root=args.root,
                run_id=args.run_id,
                attempt=args.attempt,
                job=args.job,
                status=args.status,
                repository=args.repository,
                step_summary=args.step_summary,
                runner_name=args.runner_name,
                max_bytes=args.max_bytes,
            )
            print(json.dumps(result or {"status": "cancelled", "saved": False}, sort_keys=True))
        elif args.command == "get":
            print(restore_report(args.root, args.run_id, args.attempt, args.job, args.destination, args.repository))
        elif args.command == "list":
            reports = list_reports(args.root, args.repository)
            if args.json:
                print(json.dumps(reports, indent=2, sort_keys=True))
            else:
                for report in reports:
                    print(
                        f"{report['run_id']} attempt {report['attempt']} {report['job']} "
                        f"{report['status']} {report['report_bytes']} bytes pinned={report['pinned']}"
                    )
                print(f"{len(reports)} report entr{'y' if len(reports) == 1 else 'ies'}")
        elif args.command == "prune":
            if type(args.max_bytes) is not int or args.max_bytes < 1:
                _fail("maximum report-store size must be a positive integer")
            if not args.root.exists():
                result = {
                    "planned": [], "removed": [], "unknown_entries": [],
                    "blocked_reason": None, "dry_run": args.dry_run,
                }
            else:
                descriptor = _lock(args.root)
                try:
                    result = _prune_result(
                        args.root,
                        repository=args.repository,
                        now=datetime.now(timezone.utc),
                        max_bytes=args.max_bytes,
                        apply=not args.dry_run,
                    )
                finally:
                    _unlock(descriptor)
            print(json.dumps({"repository": args.repository, **result}, sort_keys=True))
        elif args.command in {"pin", "unpin"}:
            result = _mutate_pin(args.root, args.run_id, args.attempt, args.job, args.command == "pin", args.repository)
            print(json.dumps({"run_id": result["run_id"], "attempt": result["attempt"], "job": result["job"], "pinned": result["pinned"]}, sort_keys=True))
        return 0
    except (OSError, ReportStoreError) as error:
        print(f"CI report store error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
