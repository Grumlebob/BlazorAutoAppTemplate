#!/usr/bin/env python3
"""Delete only archived test-report artifacts after exact identity rechecks.

The manifest is reviewed archive evidence, not a live selection query. Every
run is bounded, requires the existing deployment lock, and verifies an exact
404 after a single DELETE request.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_API_ROOT = "https://api.github.com"
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_BATCH = 100
NAME = re.compile(r"(?:dotnet|react)-test-results-[1-9][0-9]*-[1-9][0-9]*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
ARCHIVE_FIELDS = {"name", "sha256", "artifact_count", "verified_readback"}
ARTIFACT_FIELDS = {
    "id", "name", "size_in_bytes", "digest", "created_at", "workflow_run",
    "download_bytes", "archive_sha256", "producer",
}
WORKFLOW_RUN_FIELDS = {"id", "repository_id", "head_repository_id", "head_branch", "head_sha"}
PRODUCER_FIELDS = {"id", "run_attempt", "head_sha", "status", "conclusion", "event"}
CONCLUSIONS = {"success", "failure", "cancelled", "timed_out", "action_required", "neutral", "skipped", "stale"}


class CleanupError(ValueError):
    """The archive evidence, lock or GitHub identity is not safe to use."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise CleanupError("archive manifest contains duplicate JSON keys")
        result[name] = value
    return result


def _positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _valid_repository(value: str) -> bool:
    return isinstance(value, str) and REPOSITORY.fullmatch(value) is not None


def read_manifest(path: Path, repository: str) -> tuple[dict[str, Any], ...]:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_size > MAX_MANIFEST_BYTES:
            raise CleanupError("archive manifest file is unsafe or exceeds its size bound")
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_unique_pairs)
    except CleanupError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CleanupError("archive manifest is unreadable or malformed") from error

    if (not isinstance(value, dict) or set(value) != {"schema_version", "repository", "archive", "artifacts"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not _valid_repository(value["repository"])
            or value["repository"].casefold() != repository.casefold()
            or not isinstance(value["archive"], dict) or set(value["archive"]) != ARCHIVE_FIELDS
            or not isinstance(value["artifacts"], list) or len(value["artifacts"]) > 3000):
        raise CleanupError("archive manifest schema or repository identity is invalid")

    archive = value["archive"]
    expected_archive = f"{repository.split('/', 1)[1]}-legacy-diagnostics-20261017.zip"
    if (archive["name"] != expected_archive or not isinstance(archive["sha256"], str)
            or not SHA256.fullmatch(archive["sha256"])
            or type(archive["artifact_count"]) is not int or archive["artifact_count"] != len(value["artifacts"])
            or archive["verified_readback"] is not True):
        raise CleanupError("archive manifest does not attest the reviewed readback archive")

    identities: set[int] = set()
    rows = []
    for row in value["artifacts"]:
        if not isinstance(row, dict) or set(row) != ARTIFACT_FIELDS:
            raise CleanupError("archived artifact entry has an unsupported schema")
        workflow = row["workflow_run"]
        producer = row["producer"]
        if (not _positive_int(row["id"]) or row["id"] in identities
                or not isinstance(row["name"], str) or not NAME.fullmatch(row["name"])
                or not _positive_int(row["size_in_bytes"]) or not _positive_int(row["download_bytes"])
                or not isinstance(row["digest"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", row["digest"])
                or not isinstance(row["archive_sha256"], str) or not SHA256.fullmatch(row["archive_sha256"])
                or row["digest"] != "sha256:" + row["archive_sha256"] or not _timestamp(row["created_at"])
                or not isinstance(workflow, dict) or set(workflow) != WORKFLOW_RUN_FIELDS
                or not all(_positive_int(workflow[key]) for key in ("id", "repository_id", "head_repository_id"))
                or not isinstance(workflow["head_branch"], str) or not workflow["head_branch"]
                or not isinstance(workflow["head_sha"], str) or not SHA40.fullmatch(workflow["head_sha"])
                or not isinstance(producer, dict) or set(producer) != PRODUCER_FIELDS
                or not _positive_int(producer["id"]) or producer["id"] != workflow["id"]
                or not _positive_int(producer["run_attempt"])
                or producer["head_sha"] != workflow["head_sha"] or producer["status"] != "completed"
                or not isinstance(producer["conclusion"], str) or producer["conclusion"] not in CONCLUSIONS
                or not isinstance(producer["event"], str)
                or not producer["event"]):
            raise CleanupError("archived artifact identity or producer evidence is invalid")
        identities.add(row["id"])
        rows.append(row)
    return tuple(rows)


def require_shared_lock() -> None:
    lock_dir = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_DIR", "").strip()
    lock_token = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_TOKEN", "").strip()
    if not lock_dir or not lock_token:
        raise CleanupError("the shared deployment lock is required")
    directory = Path(lock_dir)
    try:
        directory_info = directory.lstat()
        token_info = (directory / "token").lstat()
        current_token = (directory / "token").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise CleanupError("the shared deployment lock cannot be verified") from error
    if (stat.S_ISLNK(directory_info.st_mode) or not stat.S_ISDIR(directory_info.st_mode)
            or stat.S_ISLNK(token_info.st_mode) or not stat.S_ISREG(token_info.st_mode)
            or current_token != lock_token):
        raise CleanupError("the shared deployment lock token is absent or changed")


def github_request(api_root: str, method: str, path: str, token: str, *, missing: bool = False) -> dict[str, Any] | None:
    """Make one bounded request. In particular, DELETE is never retried."""
    if method not in {"GET", "DELETE"} or not path.startswith("/") or path.startswith("//"):
        raise CleanupError("GitHub request identity is invalid")
    request = urllib.request.Request(
        f"{api_root.rstrip('/')}{path}", method=method,
        headers={
            "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        if missing and error.code == 404:
            return None
        raise CleanupError(f"GitHub {method} request failed with HTTP {error.code}") from None
    except (OSError, urllib.error.URLError) as error:
        raise CleanupError(f"GitHub {method} request failed; no retry was sent") from error
    if len(body) > 1024 * 1024:
        raise CleanupError("GitHub response exceeds its size bound")
    if not body:
        return {}
    try:
        value = json.loads(body, object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CleanupError("GitHub returned malformed JSON") from error
    if not isinstance(value, dict):
        raise CleanupError("GitHub returned an unsupported response")
    return value


def _artifact_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    try:
        return (
            type(actual["id"]) is int and actual["id"] == expected["id"]
            and actual["name"] == expected["name"]
            and type(actual["size_in_bytes"]) is int and actual["size_in_bytes"] == expected["size_in_bytes"]
            and actual["digest"] == expected["digest"] and actual["created_at"] == expected["created_at"]
            and type(actual["expired"]) is bool
            and all(actual["workflow_run"].get(key) == expected["workflow_run"][key]
                    for key in WORKFLOW_RUN_FIELDS)
        )
    except (KeyError, AttributeError, TypeError):
        return False


def _producer_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    try:
        repository = actual["repository"]
        head_repository = actual["head_repository"]
        return (
            type(actual["id"]) is int and actual["id"] == expected["id"]
            and type(actual["run_attempt"]) is int and actual["run_attempt"] == expected["run_attempt"]
            and actual["head_sha"] == expected["head_sha"] and actual["head_branch"]
            == expected.get("head_branch", actual["head_branch"])
            and actual["status"] == "completed" and actual["conclusion"] == expected["conclusion"]
            and actual["event"] == expected["event"]
            and type(repository["id"]) is int
            and repository["id"] == expected.get("repository_id", repository["id"])
            and type(head_repository["id"]) is int
            and head_repository["id"] == expected.get("head_repository_id", head_repository["id"])
        )
    except (KeyError, AttributeError, TypeError):
        return False


def cleanup_archived(
    rows: tuple[dict[str, Any], ...], *, repository: str, token: str, api_root: str = DEFAULT_API_ROOT,
    apply: bool = False, max_items: int = MAX_BATCH,
) -> dict[str, int]:
    if not _valid_repository(repository) or not token:
        raise CleanupError("repository and existing workflow token are required")
    if type(max_items) is not int or not 1 <= max_items <= MAX_BATCH:
        raise CleanupError("batch limit must be between 1 and 100")
    require_shared_lock()
    examined = candidates = deleted = absent = expired = 0
    run_cache: dict[tuple[int, int], dict[str, Any]] = {}
    for expected in rows:
        if candidates >= max_items:
            break
        artifact_id = expected["id"]
        require_shared_lock()
        actual = github_request(api_root, "GET", f"/repos/{repository}/actions/artifacts/{artifact_id}", token, missing=True)
        if actual is None:
            absent += 1
            continue
        examined += 1
        if not _artifact_matches(expected, actual):
            raise CleanupError(f"artifact {artifact_id} changed from its reviewed archive identity")
        run_key = expected["producer"]["id"], expected["producer"]["run_attempt"]
        if run_key not in run_cache:
            run_cache[run_key] = github_request(
                api_root, "GET",
                f"/repos/{repository}/actions/runs/{run_key[0]}/attempts/{run_key[1]}", token,
            ) or {}
        workflow_identity = expected["workflow_run"]
        producer_identity = {
            **expected["producer"], "head_branch": workflow_identity["head_branch"],
            "repository_id": workflow_identity["repository_id"],
            "head_repository_id": workflow_identity["head_repository_id"],
        }
        if not _producer_matches(producer_identity, run_cache[run_key]):
            raise CleanupError(f"producer {run_key[0]}/{run_key[1]} changed from archived evidence")
        if actual.get("expired") is True:
            expired += 1
            continue
        candidates += 1
        print(f"candidate artifact id={artifact_id} producer={run_key[0]}/{run_key[1]} bytes={expected['size_in_bytes']}")
        if not apply:
            continue

        # Recheck both the held lock and the exact immutable artifact just
        # before the one allowed DELETE request.
        require_shared_lock()
        latest = github_request(api_root, "GET", f"/repos/{repository}/actions/artifacts/{artifact_id}", token, missing=True)
        if latest is None:
            absent += 1
            candidates -= 1
            continue
        if not _artifact_matches(expected, latest):
            raise CleanupError(f"artifact {artifact_id} changed immediately before deletion")
        if latest["expired"] is True:
            expired += 1
            candidates -= 1
            continue
        require_shared_lock()
        github_request(api_root, "DELETE", f"/repos/{repository}/actions/artifacts/{artifact_id}", token)
        receipt = github_request(api_root, "GET", f"/repos/{repository}/actions/artifacts/{artifact_id}", token, missing=True)
        if receipt is not None:
            raise CleanupError(f"artifact {artifact_id} still exists after its single DELETE request")
        deleted += 1
        print(f"deleted artifact id={artifact_id}; exact-ID GET verified 404")
    return {"examined": examined, "candidates": candidates, "deleted": deleted, "already_absent": absent, "expired": expired}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--api-root", default=os.environ.get("GITHUB_API_URL", DEFAULT_API_ROOT))
    parser.add_argument("--max-items", type=int, default=MAX_BATCH)
    parser.add_argument("--apply", action="store_true", help="Send one DELETE per exact archived artifact and verify exact 404.")
    args = parser.parse_args(argv)
    try:
        rows = read_manifest(args.manifest, args.repository)
        result = cleanup_archived(rows, repository=args.repository, token=args.token,
                                  api_root=args.api_root, apply=args.apply, max_items=args.max_items)
    except (CleanupError, OSError, ValueError) as error:
        print(f"archived diagnostic cleanup stopped safely: {error}", file=sys.stderr)
        return 1
    print(json.dumps({**result, "repository": args.repository, "mutation": "delete" if args.apply else "none"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
