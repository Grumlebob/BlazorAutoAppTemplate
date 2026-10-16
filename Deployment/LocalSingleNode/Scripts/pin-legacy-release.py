#!/usr/bin/env python3
"""Pin the exact Actions artifact named by an accepted LocalSingleNode marker."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "Deployment/Common/Scripts/Component/lib"))

import import_legacy_release_payload  # noqa: E402
import pin_release_payload  # noqa: E402
from release_manifest import sha256_file  # noqa: E402
from release_settings import load_release_settings  # noqa: E402
from release_status import ReleaseStatusError, summarize_marker  # noqa: E402


class LegacyPinOperationError(ValueError):
    """Raised when the accepted marker cannot be converted to an exact local pin."""


def _verify_offline_restore(
    *,
    pin_dir: Path,
    repository_url: str,
    summary: dict[str, Any],
    runtime: str,
    app_image: str,
    bundle_name: str | None,
    payload_image_prefix: str,
) -> None:
    """Restore only from the local pin, with GitHub artifact credentials unavailable."""
    metadata = pin_release_payload.validate(pin_dir)
    expected = {import_legacy_release_payload.MANIFEST: metadata["manifest_sha256"]}
    if metadata.get("bundle_filename") is not None:
        expected[metadata["bundle_filename"]] = metadata["bundle_sha256"]
    token = os.environ.pop("GITHUB_TOKEN", None)
    try:
        with tempfile.TemporaryDirectory(prefix="legacy-pin-offline-restore-") as temporary:
            output_dir = Path(temporary) / "payload"
            restored = pin_release_payload.restore(
                pin_dir,
                output_dir,
                repository=repository_url,
                target_sha=summary["source_sha"],
                profile=summary["frontend_profile"],
                acceptance_profile=summary["acceptance_profile"],
                runtime=runtime,
                app_image=app_image,
                bundle_name=metadata.get("bundle_filename"),
                payload_image_prefix=payload_image_prefix,
            )
            if restored.get("pin_key") != pin_dir.name:
                raise LegacyPinOperationError("offline restore returned a different local pin identity")
            for name, digest in expected.items():
                restored_file = output_dir / name
                if restored_file.is_symlink() or not restored_file.is_file() or sha256_file(restored_file) != digest:
                    raise LegacyPinOperationError("offline restore did not reproduce the pinned payload checksums")
    except LegacyPinOperationError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise LegacyPinOperationError("offline local pin restore failed") from error
    finally:
        if token is not None:
            os.environ["GITHUB_TOKEN"] = token


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LegacyPinOperationError("release marker contains a duplicate field")
        result[key] = value
    return result


def pin_marker(
    *,
    slot: str,
    app_instance: str,
    deploy_root: Path,
    repository: str,
    repository_url: str,
    app_image_base: str,
    migration_artifact_name: str,
    migration_bundle_name: str,
    payload_image_prefix: str,
    runtime: str,
    token: str,
) -> dict[str, Any]:
    pin_release_payload._require_shared_lock()
    if slot not in {"current", "recovery"} or app_instance not in {"primary", "additional"}:
        raise LegacyPinOperationError("release slot or application instance is invalid")
    marker_path = deploy_root / "release.json" if slot == "current" else deploy_root / "release-state/previous.json"
    if marker_path.is_symlink() or not marker_path.is_file():
        raise LegacyPinOperationError("selected release marker is unavailable or unsafe")
    try:
        raw_marker = json.loads(marker_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LegacyPinOperationError("selected release marker is malformed") from error
    if not isinstance(raw_marker, dict):
        raise LegacyPinOperationError("selected release marker is malformed")
    for parent in marker_path.parents:
        if parent == deploy_root.parent:
            break
        if parent.is_symlink():
            raise LegacyPinOperationError("selected release marker path contains a symlink")
    try:
        summary = summarize_marker(raw_marker, repository_url=repository_url, app_image=(
            app_image_base if app_instance == "primary" else
            app_image_base + "-" + str(raw_marker.get("frontend_profile", "BlazorAuto")).lower()
        ))
    except ReleaseStatusError as error:
        raise LegacyPinOperationError("selected release marker identity is invalid") from error
    if summary is None:
        raise LegacyPinOperationError("selected release marker is missing")

    pin_root = deploy_root / "release-payloads" / repository.replace("/", "-")
    existing_key = summary.get("release_payload_pin_key")
    if existing_key:
        pin_dir = pin_root / existing_key
        metadata = pin_release_payload.validate(pin_dir)
        if (metadata.get("repository", "").casefold() != repository_url.casefold()
                or not pin_release_payload._pin_marker_matches(raw_marker, metadata)):
            raise LegacyPinOperationError("selected marker differs from its validated local pin")
        _verify_offline_restore(
            pin_dir=pin_dir,
            repository_url=repository_url,
            summary=summary,
            runtime=runtime,
            app_image=summary["image"],
            bundle_name=metadata.get("bundle_filename"),
            payload_image_prefix=payload_image_prefix,
        )
        return {
            "schema_version": 1,
            "outcome": "already_pinned",
            "pin_key": existing_key,
            "offline_restore": "verified",
            **metadata,
        }
    if summary["payload_transport"] != "actions-artifact":
        raise LegacyPinOperationError("selected marker does not identify an unpinned legacy artifact")

    profile = summary["frontend_profile"]
    acceptance = summary["acceptance_profile"]
    if app_instance == "additional":
        expected_image = app_image_base + "-" + profile.lower()
        artifact_name = migration_artifact_name + "-" + profile.lower()
    else:
        expected_image = app_image_base
        artifact_name = migration_artifact_name
    if summary["image"] != expected_image:
        raise LegacyPinOperationError("selected marker image does not match the configured application instance")

    selector = REPO_ROOT / "Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py"
    command = [
        sys.executable, str(selector),
        "--target-sha", summary["source_sha"],
        "--expected-run-id", summary["ci_run_id"],
        "--expected-run-attempt", summary["ci_run_attempt"],
        "--read-final-payload-receipt",
        "--payload-profile", profile,
        "--payload-acceptance-profile", acceptance,
        "--payload-runtime", runtime,
        "--payload-app-image", expected_image,
        "--json",
    ]
    try:
        selected = subprocess.run(command, capture_output=True, text=True, check=False, timeout=180)
    except (OSError, subprocess.SubprocessError) as error:
        raise LegacyPinOperationError("exact successful CI provenance could not be checked") from error
    if selected.returncode != 0:
        raise LegacyPinOperationError("exact successful CI provenance could not be checked")
    try:
        selection = json.loads(selected.stdout)
    except json.JSONDecodeError as error:
        raise LegacyPinOperationError("CI selector returned malformed provenance") from error
    if not isinstance(selection, dict) or selection.get("outcome") != "legacy_artifact":
        raise LegacyPinOperationError("accepted marker does not match an exact successful legacy CI attempt")

    result = import_legacy_release_payload.import_legacy_artifact(
        selection,
        pin_root,
        repository=repository,
        repository_url=repository_url,
        token=token,
        artifact_name=artifact_name,
        profile=profile,
        acceptance_profile=acceptance,
        runtime=runtime,
        app_image=expected_image,
        bundle_name=migration_bundle_name,
        expected_image_digest=summary["digest"],
    )
    if not pin_release_payload._pin_marker_matches(raw_marker, result):
        raise LegacyPinOperationError("imported artifact differs from the accepted release marker")
    _verify_offline_restore(
        pin_dir=pin_root / result["pin_key"],
        repository_url=repository_url,
        summary=summary,
        runtime=runtime,
        app_image=expected_image,
        bundle_name=result.get("bundle_filename"),
        payload_image_prefix=payload_image_prefix,
    )
    result["offline_restore"] = "verified"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", required=True, choices=("current", "recovery"))
    args = parser.parse_args()
    try:
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        repository_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/") + "/" + repository
        instance_file = Path(os.environ["INSTANCE_EXTRA_VARS_FILE"])
        if instance_file.is_symlink() or not instance_file.is_file():
            raise LegacyPinOperationError("validated application instance settings are unavailable")
        config = json.loads(instance_file.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(config, dict):
            raise LegacyPinOperationError("validated application instance settings are malformed")
        deploy_root = Path(config.get("deploy_root", ""))
        if (not deploy_root.is_absolute() or not str(deploy_root).startswith("/opt/")
                or ".." in deploy_root.parts or config.get("app_name") != os.environ.get("APP_NAME")):
            raise LegacyPinOperationError("application instance settings do not match this deployment")
        settings = load_release_settings(REPO_ROOT / "Deployment/Common/release.yml")
        result = pin_marker(
            slot=args.slot,
            app_instance=os.environ.get("APP_INSTANCE", ""),
            deploy_root=deploy_root,
            repository=repository,
            repository_url=repository_url,
            app_image_base=settings["app_image"],
            migration_artifact_name=settings["migration_artifact_name"],
            migration_bundle_name=settings["migration_bundle_name"],
            payload_image_prefix=settings["release_payload_prefix"],
            runtime=os.environ.get("MIGRATION_RUNTIME", ""),
            token=os.environ.get("GITHUB_TOKEN", ""),
        )
    except (LegacyPinOperationError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"legacy release pin failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
