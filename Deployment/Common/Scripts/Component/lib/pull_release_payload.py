#!/usr/bin/env python3
"""Validate a selected CI receipt, then pull its immutable GHCR payload."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

LIB = Path(__file__).resolve().parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import ci_payload_receipt  # noqa: E402
import registry_payload  # noqa: E402


def _read_selection(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise registry_payload.PayloadError("CI selection JSON is unavailable or malformed") from error
    if not isinstance(value, dict) or value.get("outcome") != "success":
        raise registry_payload.PayloadError("CI selection does not contain a verified GHCR payload receipt")
    selected = value.get("selected")
    if not isinstance(selected, dict):
        raise registry_payload.PayloadError("CI selection is missing exact run metadata")
    receipt = ci_payload_receipt.validate_receipt(value.get("payload_receipt"))
    if receipt.get("kind") != "final":
        raise registry_payload.PayloadError("selected payload receipt is not a final release")
    return {"selected": selected, "receipt": receipt}


def resolve_identity(
    selection: dict[str, Any],
    *,
    repository: str,
    profile: str,
    acceptance_profile: str | None,
    runtime: str,
    app_image: str,
    bundle_name: str | None,
    payload_image_prefix: str = "",
) -> tuple[registry_payload.ReleasePayloadIdentity, str]:
    selected = selection["selected"]
    receipt = selection["receipt"]
    try:
        commit_sha = str(selected["head_sha"]).lower()
        run_id = str(selected["id"])
        run_attempt = str(selected["run_attempt"])
        expected = ci_payload_receipt.expected_final_identity(
            repository=repository,
            commit_sha=commit_sha,
            run_id=run_id,
            run_attempt=run_attempt,
            profile=profile,
            acceptance_profile=acceptance_profile,
            runtime=runtime,
            app_image=app_image,
            payload_image_prefix=payload_image_prefix,
        )
    except (KeyError, TypeError, ValueError, ci_payload_receipt.ReceiptError) as error:
        raise registry_payload.PayloadError("expected release identity is malformed") from error
    for key, expected_value in expected.items():
        if receipt.get(key) != expected_value:
            raise registry_payload.PayloadError(f"payload receipt {key} differs from the expected release")
    if receipt.get("acceptance_profile") != acceptance_profile:
        raise registry_payload.PayloadError("payload receipt acceptance profile differs from the expected release")
    receipt_bundle_name = receipt.get("bundle_filename")
    if receipt_bundle_name != bundle_name:
        raise registry_payload.PayloadError("payload receipt bundle filename differs from release settings")

    identity = registry_payload.ReleasePayloadIdentity(
        repository=repository,
        commit_sha=commit_sha,
        run_id=run_id,
        run_attempt=run_attempt,
        profile=profile,
        acceptance_profile=acceptance_profile,
        runtime=runtime,
        app_image=app_image,
        app_image_digest=receipt["app_image_digest"],
        bundle_filename=receipt_bundle_name,
        manifest_sha256=receipt["manifest_sha256"],
        bundle_sha256=receipt.get("bundle_sha256"),
        payload_image_prefix=payload_image_prefix,
    )
    if receipt["payload_image"] != identity.payload_image:
        raise registry_payload.PayloadError("payload receipt image does not match the derived release image")
    return identity, receipt["payload_digest"]


def _pull_with_isolated_login(
    identity: registry_payload.ReleasePayloadIdentity,
    payload_digest: str,
    output_dir: Path,
    *,
    registry_username: str | None,
    token_file: Path | None,
) -> dict[str, Path]:
    if (registry_username is None) != (token_file is None):
        raise registry_payload.PayloadError("registry username and token file must be provided together")
    previous_config = os.environ.get("DOCKER_CONFIG")
    try:
        if token_file is None:
            return registry_payload.pull_and_extract_release_payload(identity, payload_digest, output_dir)
        try:
            token = token_file.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as error:
            raise registry_payload.PayloadError("temporary registry credential is unavailable") from error
        if not token or any(character.isspace() for character in token):
            raise registry_payload.PayloadError("temporary registry credential is malformed")
        with tempfile.TemporaryDirectory(prefix="release-payload-docker-config-") as docker_config:
            environment = os.environ.copy()
            environment["DOCKER_CONFIG"] = docker_config
            try:
                login = subprocess.run(
                    ["docker", "login", "ghcr.io", "--username", registry_username, "--password-stdin"],
                    input=token + "\n",
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=environment,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise registry_payload.PayloadError("temporary GHCR login failed") from error
            if login.returncode != 0:
                raise registry_payload.PayloadError("temporary GHCR login failed")
            if previous_config is None:
                os.environ.pop("DOCKER_CONFIG", None)
            else:
                os.environ["DOCKER_CONFIG"] = previous_config
            os.environ["DOCKER_CONFIG"] = docker_config
            return registry_payload.pull_and_extract_release_payload(identity, payload_digest, output_dir)
    finally:
        if previous_config is None:
            os.environ.pop("DOCKER_CONFIG", None)
        else:
            os.environ["DOCKER_CONFIG"] = previous_config


def pull_from_selection(
    selection_path: Path,
    output_dir: Path,
    *,
    repository: str,
    profile: str,
    acceptance_profile: str | None,
    runtime: str,
    app_image: str,
    bundle_name: str | None,
    payload_image_prefix: str = "",
    registry_username: str | None = None,
    token_file: Path | None = None,
) -> dict[str, Any]:
    selection = _read_selection(selection_path)
    receipt = selection["receipt"]
    identity, digest = resolve_identity(
        selection,
        repository=repository,
        profile=profile,
        acceptance_profile=acceptance_profile,
        runtime=runtime,
        app_image=app_image,
        bundle_name=bundle_name,
        payload_image_prefix=payload_image_prefix,
    )
    files = _pull_with_isolated_login(
        identity,
        digest,
        output_dir,
        registry_username=registry_username,
        token_file=token_file,
    )
    return {
        "schema_version": 1,
        "transport": "ghcr-container",
        "repository": identity.repository,
        "target_sha": identity.commit_sha,
        "run_id": identity.run_id,
        "run_attempt": identity.run_attempt,
        "profile": identity.profile,
        "acceptance_profile": identity.acceptance_profile,
        "runtime": identity.runtime,
        "payload_image": identity.payload_image,
        "payload_digest": digest,
        "payload_ref": f"{identity.payload_image}@{digest}",
        "manifest_sha256": identity.manifest_sha256,
        "bundle_filename": identity.bundle_filename,
        "bundle_sha256": identity.bundle_sha256,
        "content_sha256": receipt["content_sha256"],
        "app_image": identity.app_image,
        "image_digest": identity.app_image_digest,
        "manifest_path": str(files["manifest"]),
        "bundle_path": str(files["bundle"]) if "bundle" in files else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--acceptance-profile", default="")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--app-image", required=True)
    parser.add_argument("--payload-image-prefix", default="")
    parser.add_argument("--bundle-name", default="")
    parser.add_argument("--registry-username")
    parser.add_argument("--token-file", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = pull_from_selection(
            args.selection_file,
            args.output_dir,
            repository=args.repository,
            profile=args.profile,
            acceptance_profile=args.acceptance_profile or None,
            runtime=args.runtime,
            app_image=args.app_image,
            bundle_name=args.bundle_name or None,
            payload_image_prefix=args.payload_image_prefix,
            registry_username=args.registry_username,
            token_file=args.token_file,
        )
    except (OSError, registry_payload.PayloadError, ci_payload_receipt.ReceiptError, ValueError) as error:
        print(f"release payload pull failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
