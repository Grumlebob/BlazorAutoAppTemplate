#!/usr/bin/env python3
"""Read LocalCluster release markers, local pins and active CD runs."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT_DIR / "Component" / "lib"))
sys.path.insert(0, str(ROOT / "Deployment/Common/Scripts/Component/lib"))
sys.path.insert(0, str(ROOT / "Scripts/Frontend"))

import pin_release_payload  # noqa: E402
from deploy_settings import load_settings  # noqa: E402
from release_settings import load_release_settings  # noqa: E402
from release_status import (  # noqa: E402
    ReleaseStatusError,
    list_active_deployment_runs,
    pin_state,
    summarize_marker,
    verify_offline_pin_restore,
)


def ansible_results(module: str, arguments: str, destination: Path) -> list[dict[str, Any]]:
    inventory = ROOT / "Deployment/LocalCluster/inventory/prod/hosts.yml"
    if not inventory.is_file():
        raise ReleaseStatusError("LocalCluster inventory is unavailable")
    try:
        result = subprocess.run(
            [
                "ansible", "app_servers", "-i", str(inventory),
                "-m", module, "-a", arguments, "--tree", str(destination),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        raise ReleaseStatusError("Ansible timed out while inspecting LocalCluster app servers") from error
    except (OSError, subprocess.SubprocessError) as error:
        raise ReleaseStatusError("Ansible could not inspect every LocalCluster app server") from error
    if result.returncode != 0:
        diagnostic = f"{result.stderr or ''}\n{result.stdout or ''}".casefold()
        if "permission denied" in diagnostic or "authentication failed" in diagnostic:
            reason = "SSH authentication failed while inspecting LocalCluster app servers"
        elif any(marker in diagnostic for marker in (
            "host key verification failed", "remote host identification has changed",
        )):
            reason = "SSH host verification failed while inspecting LocalCluster app servers"
        elif any(marker in diagnostic for marker in (
            "connection timed out", "timed out", "no route to host", "network is unreachable",
            "connection refused", "connection reset", "host is unreachable",
        )):
            reason = "SSH connectivity failed while inspecting LocalCluster app servers"
        else:
            reason = "Ansible could not inspect every LocalCluster app server"
        raise ReleaseStatusError(reason)
    records: list[dict[str, Any]] = []
    for path in sorted(destination.iterdir()):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ReleaseStatusError("Ansible returned malformed app server status") from error
        if not isinstance(value, dict) or int(value.get("rc", 0)) != 0:
            raise ReleaseStatusError("Ansible returned incomplete app server status")
        records.append(value)
    if not records:
        raise ReleaseStatusError("Ansible returned no app server status")
    return records


def read_remote_marker(path: str, *, required: bool) -> dict | None:
    with tempfile.TemporaryDirectory(prefix="template-release-status-stat-") as directory:
        stat_records = ansible_results(
            "ansible.builtin.stat", f"path={path} follow=false", Path(directory),
        )
    existence: list[bool] = []
    for record in stat_records:
        state = record.get("stat")
        if not isinstance(state, dict) or state.get("islnk") is True:
            raise ReleaseStatusError("LocalCluster release marker path is unsafe")
        exists = state.get("exists")
        if type(exists) is not bool:
            raise ReleaseStatusError("LocalCluster release marker status is malformed")
        existence.append(exists)
    if len(set(existence)) != 1:
        raise ReleaseStatusError("LocalCluster app servers disagree about release marker availability")
    if not existence[0]:
        if required:
            raise ReleaseStatusError("current LocalCluster release marker is missing")
        return None

    with tempfile.TemporaryDirectory(prefix="template-release-status-slurp-") as directory:
        slurp_records = ansible_results(
            "ansible.builtin.slurp", f"src={path}", Path(directory),
        )
    values: list[dict] = []
    for record in slurp_records:
        content = record.get("content")
        if not isinstance(content, str):
            raise ReleaseStatusError("Ansible returned an incomplete release marker")
        try:
            decoded = base64.b64decode(content, validate=True).decode("utf-8")
            value = json.loads(decoded)
        except (ValueError, UnicodeError, json.JSONDecodeError) as error:
            raise ReleaseStatusError("Ansible returned a malformed release marker") from error
        if not isinstance(value, dict):
            raise ReleaseStatusError("release marker is not a JSON object")
        values.append(value)
    if not values or any(value != values[0] for value in values[1:]):
        raise ReleaseStatusError("LocalCluster app servers disagree about release identity")
    return values[0]


def verify_live_identity(release: dict | None, *, repository_url: str) -> str:
    if release is None:
        return "no-current-release"
    verifier = SCRIPT_DIR / "verify-release-identity.sh"
    args = [
        "bash", str(verifier), release["image"], release["digest"],
        release["frontend_profile"], release["acceptance_profile"],
        release["source_sha"], str(release["manifest_schema_version"]),
        release["ci_run_id"], release["ci_run_attempt"], repository_url,
    ]
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False, timeout=180)
    except (OSError, subprocess.SubprocessError) as error:
        raise ReleaseStatusError("live LocalCluster identity check is unavailable") from error
    return "verified" if result.returncode == 0 else "failed"


def write_marker(path: Path, value: dict | None) -> Path | None:
    if value is None:
        return None
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def report_safe_failure(reason: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("### Release status unavailable\n\n")
            summary.write(f"Reason: {reason}\n\nProtected state was not changed.\n")
    except OSError:
        # Diagnostics must never change the status command's failure behavior.
        pass


def snapshot() -> dict:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if repository.casefold() != "Grumlebob/BlazorAutoAppTemplate".casefold():
        raise ReleaseStatusError("status workflow is bound to the Template repository")
    repository_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/") + "/" + repository
    try:
        pin_release_payload._require_shared_lock()
    except (OSError, ValueError) as error:
        raise ReleaseStatusError("shared deployment lock is not held by this status check") from error

    settings = load_settings(ROOT / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml")
    release_settings = load_release_settings(ROOT / "Deployment/Common/release.yml")
    deploy_root = settings["deploy_root"]
    current_raw = read_remote_marker(f"{deploy_root}/release.json", required=True)
    recovery_raw = read_remote_marker(f"{deploy_root}/release-state/previous.json", required=False)
    current = summarize_marker(current_raw, repository_url=repository_url, app_image=release_settings["app_image"])
    recovery = summarize_marker(recovery_raw, repository_url=repository_url, app_image=release_settings["app_image"])

    with tempfile.TemporaryDirectory(prefix="template-release-status-markers-") as directory:
        marker_root = Path(directory)
        current_path = write_marker(marker_root / "release.json", current_raw)
        recovery_path = write_marker(marker_root / "previous.json", recovery_raw)
        assert current_path is not None
        pin_root = Path(deploy_root) / "release-payloads" / repository.replace("/", "-")
        inventory = pin_release_payload.prune_local_pins(
            pin_root,
            repository=repository_url,
            current_marker_path=current_path,
            recovery_marker_path=recovery_path,
            apply=False,
            max_candidates_per_profile=3,
            max_unprotected_bytes=1_073_741_824,
        )

    protected = set(inventory.get("protected", []))
    marker_pins = inventory.get("marker_pins", {})
    current_pin = pin_state(current, protected, marker_pins.get("current"))
    recovery_pin = pin_state(recovery, protected, marker_pins.get("recovery"))
    offline_pin_restore: dict[str, Any] = {"outcome": "not-requested"}
    if os.environ.get("VERIFY_OFFLINE_PINS", "false").casefold() == "true":
        temp_root = Path(os.environ.get("RUNNER_TEMP", ""))
        offline_pin_restore = {
            "current": verify_offline_pin_restore(
                current, pin_root,
                repository_url=repository_url,
                runtime=release_settings["migration_runtime"],
                bundle_name=release_settings["migration_bundle_name"],
                payload_image_prefix=release_settings["release_payload_prefix"],
                temp_root=temp_root,
                validated_pin_key=marker_pins.get("current") if current_pin == "verified" else None,
            ),
            "recovery": verify_offline_pin_restore(
                recovery, pin_root,
                repository_url=repository_url,
                runtime=release_settings["migration_runtime"],
                bundle_name=release_settings["migration_bundle_name"],
                payload_image_prefix=release_settings["release_payload_prefix"],
                temp_root=temp_root,
                validated_pin_key=marker_pins.get("recovery") if recovery_pin == "verified" else None,
            ),
        }
    active = list_active_deployment_runs(
        repository,
        api_root=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        token=os.environ.get("GITHUB_TOKEN", ""),
    )
    pin_inventory = {
        "outcome": inventory["outcome"],
        "pins": inventory.get("pins", 0),
        "protected_bytes": inventory.get("protected_bytes", 0),
        "candidate_bytes": inventory.get("candidate_bytes", 0),
        "blocked_reason": inventory.get("blocked_reason"),
        "planned_delete_count": len(inventory.get("planned_delete", [])),
        "dry_run": inventory["dry_run"],
    }
    return {
        "schema_version": 1,
        "repository": repository,
        "target": "localcluster",
        "app_name": settings["app_name"],
        "app_servers": "consistent",
        "shared_lock": "held",
        "mutation": "none",
        "current_release": current,
        "current_pin": current_pin,
        "recovery_release": recovery,
        "recovery_pin": recovery_pin,
        "offline_pin_restore": offline_pin_restore,
        "live_identity": verify_live_identity(current, repository_url=repository_url),
        "active_deployments": active,
        "pin_inventory": pin_inventory,
    }


def main() -> int:
    try:
        result = snapshot()
    except ReleaseStatusError as error:
        report_safe_failure(str(error))
        print("Release status unavailable; protected state was not changed.", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        report_safe_failure("unexpected local inspection error; details withheld")
        print("Release status unavailable; protected state was not changed.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["live_identity"] == "failed":
        report_safe_failure("live LocalCluster identity check failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
