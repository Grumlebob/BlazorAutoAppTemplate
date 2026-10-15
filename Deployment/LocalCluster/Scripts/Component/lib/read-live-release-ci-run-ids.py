#!/usr/bin/env python3
"""Read the exact CI run identity from every currently running app container."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
RUN_ID_RE = re.compile(r"^[1-9][0-9]*$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def fail(message: str) -> None:
    raise SystemExit(f"live release identity read failed: {message}")


def validated_run_ids(host_results: list[dict[str, Any]], source_repo_url: str, repository: str) -> list[str]:
    if not host_results:
        raise ValueError("no app-server identity records were returned")
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("repository identity is malformed")
    expected_source = f"https://github.com/{repository}"
    if source_repo_url.casefold() != expected_source.casefold():
        raise ValueError("source repository URL does not match GITHUB_REPOSITORY")

    identities: set[tuple[str, str]] = set()
    for result in host_results:
        if type(result.get("rc")) is not int or result["rc"] != 0:
            raise ValueError("Ansible could not inspect every app server")
        output = result.get("stdout")
        if not isinstance(output, str) or not output.strip():
            raise ValueError("an app server returned no running web image identity")
        for line in output.splitlines():
            fields = line.split("\t", 2)
            if len(fields) != 3 or not fields[0].strip() or not fields[1].strip():
                raise ValueError("an app server returned malformed image identity data")
            try:
                labels = json.loads(fields[2])
            except json.JSONDecodeError as exc:
                raise ValueError("an app server returned malformed image labels") from exc
            if not isinstance(labels, dict):
                raise ValueError("an app server image has no label object")
            if labels.get("org.opencontainers.image.source", "").casefold() != expected_source.casefold():
                raise ValueError("a running image belongs to a different source repository")
            if labels.get("localcluster.ci.repository", "").casefold() != repository.casefold():
                raise ValueError("a running image has a different CI repository identity")
            run_id = labels.get("localcluster.ci.run_id")
            attempt = labels.get("localcluster.ci.run_attempt")
            if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
                raise ValueError("a running image has no valid CI run ID")
            if not isinstance(attempt, str) or not RUN_ID_RE.fullmatch(attempt):
                raise ValueError("a running image has no valid CI run attempt")
            identities.add((run_id, attempt))

    if not identities:
        raise ValueError("no running web image identity was found")
    if len(identities) != 1:
        raise ValueError("app servers are running different CI release identities")
    return [next(iter(identities))[0]]


def remote_identity_command(app_name: str, deploy_root: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", app_name):
        raise ValueError("app_name is malformed")
    if not re.fullmatch(r"/opt/[A-Za-z0-9_./-]+", deploy_root) or ".." in deploy_root.split("/"):
        raise ValueError("deploy_root is malformed")
    root = shlex.quote(deploy_root)
    expected_app = shlex.quote(app_name)
    return (
        "set -eu; "
        f"cd {root}; "
        "test -f .env; "
        "root_app=$(sed -n 's/^APP_NAME=//p' .env | tail -n 1); "
        f"test \"$root_app\" = {expected_app}; "
        "containers=$(docker compose ps -q web); test -n \"$containers\"; "
        "format_image=$(printf '%s%s%s%s%s' '{' '{' '.Image' '}' '}'); "
        "format_labels=$(printf '%s%s%s%s%s' '{' '{' 'json .Config.Labels' '}' '}'); "
        "for container in $containers; do "
        "image_id=$(docker inspect --format \"$format_image\" \"$container\"); "
        "labels=$(docker image inspect --format \"$format_labels\" \"$image_id\"); "
        "printf '%s\\t%s\\t%s\\n' \"$(hostname)\" \"$image_id\" \"$labels\"; "
        "done"
    )


def inspect_live_run_ids(app_name: str, deploy_root: str, repository: str, source_repo_url: str) -> list[str]:
    inventory = ROOT / "Deployment/LocalCluster/inventory/prod/hosts.yml"
    if not inventory.is_file():
        raise ValueError("production inventory is unavailable")
    command = remote_identity_command(app_name, deploy_root)
    with tempfile.TemporaryDirectory(prefix="live-release-identities-") as temporary:
        result = subprocess.run(
            [
                "ansible", "app_servers", "-i", str(inventory),
                "-m", "ansible.builtin.shell", "-a", command,
                "--tree", temporary,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise ValueError("Ansible could not inspect every app server")
        host_results = []
        for path in sorted(Path(temporary).iterdir()):
            if not path.is_file():
                continue
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("Ansible returned malformed host identity data") from exc
            if not isinstance(value, dict):
                raise ValueError("Ansible returned malformed host identity data")
            host_results.append(value)
        return validated_run_ids(host_results, source_repo_url, repository)


def main() -> int:
    try:
        app_name = os.environ["APP_NAME"]
        deploy_root = os.environ["DEPLOY_ROOT"]
        repository = os.environ["GITHUB_REPOSITORY"]
        server_url = os.environ["GITHUB_SERVER_URL"].rstrip("/")
        source_repo_url = f"{server_url}/{repository}"
        for run_id in inspect_live_run_ids(app_name, deploy_root, repository, source_repo_url):
            print(run_id)
        return 0
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
