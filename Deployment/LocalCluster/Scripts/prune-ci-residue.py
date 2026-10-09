#!/usr/bin/env python3
"""Bounded reclamation of this repository's finished CI attempts; read-only by default.

Removes only Docker containers and networks labelled
localcluster.ci.repository=<this repository> whose GitHub run attempt finished
more than 24 hours ago. Docker volumes are never removed: CI and tests use
tmpfs. Must run under with-deploy-lock.sh when applying.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
API_ROOT = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
PREFIX = "localcluster.ci."
GRACE = timedelta(hours=24)
OWNERS = {"ci-smoke", "ci-build", "tests"}


def require_lock() -> None:
    """Mutations happen only inside with-deploy-lock.sh, which holds the token."""
    token = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_TOKEN", "")
    lock_dir = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_DIR", "")
    if not token or not lock_dir:
        raise RuntimeError("run under with-deploy-lock.sh; the deployment lock is not held")
    try:
        held = (Path(lock_dir) / "token").read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RuntimeError(f"deployment lock token is unreadable: {error}") from error
    if held != token:
        raise RuntimeError("deployment lock is held by another owner")
    # The token alone is not enough: the recorded owner must be this host and
    # one of this process's ancestors (the with-deploy-lock.sh wrapper).
    try:
        owner = (Path(lock_dir) / "owner").read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RuntimeError(f"deployment lock owner is unreadable: {error}") from error
    match = re.match(r"^([^:]+):pid=([0-9]+)(?::|$)", owner)
    if not match or match.group(1) != socket.gethostname():
        raise RuntimeError("deployment lock owner is not this host")
    owner_pid = int(match.group(2))
    pid = os.getppid()
    for _ in range(64):
        if pid == owner_pid:
            return
        if pid <= 1:
            break
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        except OSError:
            break
        pid = int(stat.rsplit(")", 1)[1].split()[1])
    raise RuntimeError("deployment lock owner is not an ancestor of this process")


def timestamp(value: str) -> datetime:
    value = re.sub(r"(\.\d{6})\d+", r"\1", value)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must have a timezone")
    return result


class Cleaner:
    def __init__(self, apply: bool, limit: int, app_name: str):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", app_name):
            raise ValueError("app_name must be a lowercase slug")
        self.network_pattern = re.compile(rf"{re.escape(app_name)}-ci-[a-z0-9][a-z0-9_.-]*")
        self.apply = apply
        self.limit = limit
        self.deadline = time.monotonic() + 300
        self.attempts = {}
        self.now = datetime.now(timezone.utc)
        self.counts = {"removed": 0, "eligible": 0, "protected": 0, "limited": 0}

    def budget(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("five-minute cleanup budget exhausted")
        return min(30, remaining)

    def command(self, *args: str) -> str:
        result = subprocess.run(
            args, text=True, capture_output=True, timeout=self.budget()
        )
        if result.returncode:
            # Never dump Docker inspect output, API bodies, or environments.
            raise RuntimeError(f"{args[0]} {args[1]} failed (exit {result.returncode})")
        return result.stdout.strip()

    def inspect(self, kind: str, name: str) -> dict:
        # Selected metadata only; never Config.Env or database contents.
        fields = {
            "container": {
                "Id": ".Id",
                "Created": ".Created",
                "Labels": ".Config.Labels",
                "Mounts": ".Mounts",
                "State": ".State.Status",
                "Restart": ".HostConfig.RestartPolicy.Name",
                "Privileged": ".HostConfig.Privileged",
            },
            "network": {
                "Name": ".Name",
                "Id": ".Id",
                "Created": ".Created",
                "Labels": ".Labels",
                "Containers": ".Containers",
                "Driver": ".Driver",
                "Scope": ".Scope",
            },
        }[kind]
        template = (
            "{"
            + ",".join(
                json.dumps(key) + ":{{json " + value + "}}"
                for key, value in fields.items()
            )
            + "}"
        )
        return json.loads(
            self.command("docker", kind, "inspect", "--format", template, name)
        )

    def attempt(self, run_id: str, attempt: str, fresh: bool = False) -> dict:
        key = (run_id, attempt)
        if fresh or key not in self.attempts:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise RuntimeError(
                    "GITHUB_TOKEN with actions:read is required for candidate ownership"
                )
            request = urllib.request.Request(
                f"{API_ROOT}/repos/{REPOSITORY}/actions/runs/{run_id}/attempts/{attempt}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urllib.request.urlopen(
                request, timeout=min(10, self.budget())
            ) as response:
                self.attempts[key] = json.load(response)
        return self.attempts[key]

    def ownership(self, item: dict, fresh: bool = False) -> bool:
        labels = item.get("Labels") or {}
        if (
            labels.get(PREFIX + "repository") != REPOSITORY
            or labels.get(PREFIX + "owner") not in OWNERS
        ):
            return False
        if any(key.startswith("com.docker.compose.") for key in labels):
            return False
        run_id = labels.get(PREFIX + "run_id", "")
        attempt = labels.get(PREFIX + "run_attempt", "")
        if not re.fullmatch(r"[1-9][0-9]*", run_id) or not re.fullmatch(
            r"[1-9][0-9]*", attempt
        ):
            return False
        if labels.get(PREFIX + "session") != f"{run_id}-{attempt}" or not labels.get(
            PREFIX + "purpose"
        ):
            return False
        try:
            created = timestamp(item["Created"])
            labelled = timestamp(labels[PREFIX + "created_at"])
        except (ValueError, KeyError, TypeError):
            return False
        if self.now - created < GRACE or abs(created - labelled) > timedelta(minutes=5):
            return False
        run = self.attempt(run_id, attempt, fresh)
        if (
            run.get("id") != int(run_id)
            or run.get("run_attempt") != int(attempt)
            or run.get("status") != "completed"
            or not run.get("conclusion")
            or run.get("path", "").split("@")[0] != ".github/workflows/ci.yml"
            or (run.get("head_repository") or {}).get("full_name") != REPOSITORY
        ):
            return False
        # Later metadata updates extend retention rather than deleting too early.
        completed = timestamp(run["updated_at"])
        started = timestamp(run["created_at"])
        return (
            self.now - completed >= GRACE
            and started - timedelta(minutes=5) <= created <= completed
            and started <= completed <= self.now
        )

    def disposable(self, kind: str, item: dict) -> bool:
        if kind == "container":
            # Never stop/delete a container attached to persistent or host data.
            return (
                item["State"] in ("running", "exited", "created")
                and item["Restart"] in ("", "no")
                and not item["Privileged"]
                and all(mount["Type"] == "tmpfs" for mount in item["Mounts"])
            )
        if kind == "network":
            return (
                self.network_pattern.fullmatch(str(item.get("Name", ""))) is not None
                and not item["Containers"]
                and item["Driver"] == "bridge"
                and item["Scope"] == "local"
            )
        # Volumes are never disposable here; CI storage is tmpfs.
        return False

    def consider(self, kind: str, item: dict) -> None:
        if not self.ownership(item) or not self.disposable(kind, item):
            self.counts["protected"] += 1
            return
        self.counts["eligible"] += 1
        if not self.apply:
            return
        if self.counts["removed"] >= self.limit:
            self.counts["limited"] += 1
            return
        require_lock()
        identifier = item["Id"]
        current = self.inspect(kind, identifier)
        if (
            current != item
            or not self.ownership(current, fresh=True)
            or not self.disposable(kind, current)
        ):
            raise RuntimeError("candidate changed before removal")
        if kind == "container" and current["State"] == "running":
            self.command("docker", "container", "stop", "--timeout", "10", identifier)
            stopped = self.inspect(kind, identifier)
            expected = dict(current, State=stopped["State"])
            if (
                stopped != expected
                or stopped["State"] not in ("exited", "created")
                or not self.disposable(kind, stopped)
            ):
                raise RuntimeError(
                    "container changed during stop; retained for inspection"
                )
        require_lock()
        self.command(
            "docker", kind, "rm", identifier
        )  # No force, wildcard, or broad prune.
        self.counts["removed"] += 1
        print(json.dumps({"removed_kind": kind, "id": identifier}), flush=True)

    def execute(self) -> None:
        for kind, listing in (
            ("container", ("ps", "-aq")),
            ("network", ("network", "ls", "-q")),
        ):
            names = self.command(
                "docker",
                *listing,
                "--filter",
                "label=" + PREFIX + "repository=" + REPOSITORY,
            ).splitlines()
            if len(names) > 500:
                raise RuntimeError(
                    "inventory exceeds 500 objects of one kind; review backlog"
                )
            for name in names:
                self.consider(kind, self.inspect(kind, name))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("limit must be between 1 and 100")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", REPOSITORY):
        parser.error("GITHUB_REPOSITORY must be set to owner/name")
    if args.apply:
        if socket.gethostname() != "node-main":
            parser.error("apply is restricted to node-main")
        require_lock()
    settings_reader = Path(__file__).resolve().parent / "Component/lib/read-deploy-setting.py"
    app_name = subprocess.run(
        [sys.executable, str(settings_reader), "app_name"],
        text=True, capture_output=True, check=True, timeout=30,
    ).stdout.strip()
    cleaner = Cleaner(args.apply, args.limit, app_name)
    try:
        cleaner.execute()
    finally:
        print(
            json.dumps(
                {"mode": "apply" if args.apply else "dry-run", **cleaner.counts}
            ),
            flush=True,
        )
    return 75 if cleaner.counts["limited"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        print(
            f"CI residue operation stopped; remaining resources protected: {error}",
            flush=True,
        )
        raise SystemExit(1)
