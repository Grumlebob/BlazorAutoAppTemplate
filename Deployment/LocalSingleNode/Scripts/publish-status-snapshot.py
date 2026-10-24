#!/usr/bin/env python3
"""Publish the validated LocalSingleNode release status where operators can read it over SSH.

The input is the status document that release-status.py already produced under the shared
deployment lock, and that the workflow validated as read-only. This script validates it again,
then writes <backup_root>/status/release-status.json. The backup root is operator-readable by
design (its group is the install group), so the snapshot takes the same group and is readable by
the operator without sudo. The backup pruner only removes artifacts in the backup root itself, so
the status subdirectory is outside its reach. Only the status document and export metadata are
written: no tokens, keys, environment or deployment files.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile


DIRECTORY_NAME = "status"
FILE_NAME = "release-status.json"


class SnapshotError(RuntimeError):
    pass


def read_status(path: Path) -> dict:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise SnapshotError("status input is empty")
    value = json.loads(lines[-1])
    if not isinstance(value, dict):
        raise SnapshotError("status input is not a JSON object")
    if value.get("mutation") != "none" or value.get("shared_lock") != "held":
        raise SnapshotError("status input does not prove a read-only inspection under the shared lock")
    if value.get("target") != "localsinglenode":
        raise SnapshotError("status input is not for the LocalSingleNode target")
    return value


def backup_root_from(vars_path: Path) -> Path:
    config = json.loads(vars_path.read_text(encoding="utf-8"))
    root = config.get("backup_root")
    if not isinstance(root, str) or not Path(root).is_absolute():
        raise SnapshotError("deployment vars do not name an absolute backup_root")
    return Path(root)


def publish(status_path: Path, vars_path: Path, run_id: str) -> Path:
    value = read_status(status_path)
    root = backup_root_from(vars_path)
    if not root.is_dir():
        raise SnapshotError("backup_root is not an existing directory")
    group = root.stat().st_gid
    directory = root / DIRECTORY_NAME
    directory.mkdir(mode=0o750, exist_ok=True)
    os.chmod(directory, 0o750)
    if hasattr(os, "chown"):
        os.chown(directory, -1, group)
    snapshot = {
        "exported_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_run_id": run_id,
        "status": value,
    }
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".release-status.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.chmod(temporary, 0o640)
        if hasattr(os, "chown"):
            os.chown(temporary, -1, group)
        target = directory / FILE_NAME
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", required=True, type=Path, help="release-status.py output (last JSON line is used)")
    parser.add_argument("--deployment-vars", required=True, type=Path, help="deployment-vars.json from resolve-deployment.py")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    args = parser.parse_args(argv)
    try:
        target = publish(args.status, args.deployment_vars, args.run_id)
    except (OSError, ValueError, SnapshotError) as error:
        print(f"Operator status snapshot was not published: {error}", file=sys.stderr)
        return 1
    print(f"Published operator status snapshot: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
