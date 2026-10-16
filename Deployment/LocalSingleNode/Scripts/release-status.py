#!/usr/bin/env python3
"""Read the selected LocalSingleNode release, local pins and active CD runs."""

from __future__ import annotations

import getpass
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
TARGET = SCRIPT_DIR.parent
ROOT = TARGET.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT_DIR / "lib"))
sys.path.insert(0, str(ROOT / "Deployment/Common/Scripts/Component/lib"))

import pin_release_payload  # noqa: E402
from platform_check import native  # noqa: E402
from release_settings import load_release_settings  # noqa: E402
from release_status import ReleaseStatusError, list_active_deployment_runs, pin_state, summarize_marker  # noqa: E402


def load_instance_module():
    spec = importlib.util.spec_from_file_location("app_instance", SCRIPT_DIR / "resolve-app-instance.py")
    if spec is None or spec.loader is None:
        raise ReleaseStatusError("application instance validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def marker(path: Path) -> dict | None:
    if path.is_symlink():
        raise ReleaseStatusError("release marker is a symlink")
    if not path.exists():
        return None
    if not path.is_file():
        raise ReleaseStatusError("release marker is not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseStatusError("release marker is unreadable or malformed") from error
    if not isinstance(value, dict):
        raise ReleaseStatusError("release marker is not a JSON object")
    return value


def runtime_inputs() -> tuple[dict, Path, str, str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if repository.casefold() != "Grumlebob/BlazorAutoAppTemplate".casefold():
        raise ReleaseStatusError("status workflow is bound to the Template repository")
    expected_host = os.environ.get("LOCALSINGLENODE_HOST", "")
    if (not native() or os.geteuid() == 0 or getpass.getuser() != "deploy"
            or not expected_host or socket.gethostname().casefold() != expected_host.casefold()):
        raise ReleaseStatusError("status requires the protected native LocalSingleNode runner")

    runner_temp = Path(os.environ.get("RUNNER_TEMP", "")).resolve()
    instance_file = Path(os.environ.get("INSTANCE_EXTRA_VARS_FILE", ""))
    if not instance_file.is_file() or instance_file.is_symlink():
        raise ReleaseStatusError("resolved application identity is unavailable")
    instance_file = instance_file.resolve()
    try:
        if os.path.commonpath((str(runner_temp), str(instance_file))) != str(runner_temp):
            raise ReleaseStatusError("resolved application identity is outside runner scratch storage")
        config = json.loads(instance_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ReleaseStatusError("resolved application identity is unreadable") from error
    if not isinstance(config, dict):
        raise ReleaseStatusError("resolved application identity is malformed")

    app_name = os.environ.get("APP_NAME", "")
    app_image = os.environ.get("APP_IMAGE", "")
    deploy_root = config.get("deploy_root")
    if (config.get("app_name") != app_name or config.get("app_image") != app_image
            or not isinstance(deploy_root, str) or not deploy_root.startswith("/opt/")
            or ".." in deploy_root.split("/") or not Path(deploy_root).is_absolute()):
        raise ReleaseStatusError("resolved application identity does not match deployment settings")

    source = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/") + "/" + repository
    load_release_settings(ROOT / "Deployment/Common/release.yml")
    load_instance_module().verify_owned(config, source)
    return config, Path(deploy_root), repository, source, app_image


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
        result = subprocess.run(args, capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise ReleaseStatusError("live LocalSingleNode identity check is unavailable") from error
    return "verified" if result.returncode == 0 else "failed"


def snapshot(config: dict, deploy_root: Path, *, repository: str, repository_url: str, app_image: str) -> dict:
    try:
        pin_release_payload._require_shared_lock()
    except (OSError, ValueError) as error:
        raise ReleaseStatusError("shared deployment lock is not held by this status check") from error

    current_path = deploy_root / "release.json"
    recovery_path = deploy_root / "release-state/previous.json"
    current_raw = marker(current_path)
    recovery_raw = marker(recovery_path)
    current = summarize_marker(current_raw, repository_url=repository_url, app_image=app_image)
    recovery = summarize_marker(recovery_raw, repository_url=repository_url, app_image=app_image)

    pin_root = deploy_root / "release-payloads" / repository.replace("/", "-")
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
    current_pin = pin_state(current, protected)
    recovery_pin = pin_state(recovery, protected)
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
        "target": "localsinglenode",
        "app_instance": os.environ.get("APP_INSTANCE", "primary"),
        "app_name": config["app_name"],
        "node_identity": "verified",
        "shared_lock": "held",
        "mutation": "none",
        "current_release": current,
        "current_pin": current_pin,
        "recovery_release": recovery,
        "recovery_pin": recovery_pin,
        "live_identity": verify_live_identity(current, repository_url=repository_url),
        "active_deployments": active,
        "pin_inventory": pin_inventory,
    }


def main() -> int:
    try:
        config, deploy_root, repository, repository_url, app_image = runtime_inputs()
        result = snapshot(
            config, deploy_root, repository=repository,
            repository_url=repository_url, app_image=app_image,
        )
    except (ReleaseStatusError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print("Release status unavailable; protected state was not changed.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["live_identity"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

