#!/usr/bin/env python3
"""Validate the immutable CI release contract consumed by LocalCluster CD."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

repository_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repository_root / "Scripts" / "Frontend"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "Component" / "lib"))
from release_manifest import ManifestError, validate_manifest_payload
from resolve_frontend_profile import acceptance_profile_for_frontend  # noqa: E402


DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
FRONTEND_PROFILE_LABEL = "com.grumplates.frontend-profile"
ACCEPTANCE_PROFILE_LABEL = "com.grumplates.acceptance-profile"
REVISION_LABEL = "org.opencontainers.image.revision"


def registry_digest(payload: Any, expected_image: str | None = None) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("RepoDigests"), list):
        repo_digests = payload["RepoDigests"]
    elif isinstance(payload, list) and all(isinstance(item, str) for item in payload):
        repo_digests = payload
    else:
        repo_digests = None
    if repo_digests is not None:
        prefix = f"{expected_image}@" if expected_image else None
        matches = [
            value.split("@", 1)[1]
            for value in repo_digests
            if isinstance(value, str)
            and "@" in value
            and (prefix is None or value.startswith(prefix))
        ]
        if len(matches) == 1 and DIGEST_RE.fullmatch(matches[0]):
            return matches[0]
        raise ManifestError("docker image inspect did not return one valid repository digest")

    entries = payload if isinstance(payload, list) else [payload]
    digest = ""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        descriptor = entry.get("Descriptor")
        if isinstance(descriptor, dict) and descriptor.get("digest"):
            digest = str(descriptor["digest"])
            break
        manifests = entry.get("manifests")
        if isinstance(manifests, list) and len(manifests) == 1 and isinstance(manifests[0], dict):
            digest = str(manifests[0].get("digest") or "")
            if digest:
                break
        if isinstance(manifests, list):
            for item in manifests:
                if not isinstance(item, dict):
                    continue
                platform = item.get("platform")
                if isinstance(platform, dict) and platform.get("architecture") == "amd64":
                    digest = str(item.get("digest") or "")
                    break
            if digest:
                break
    if not DIGEST_RE.fullmatch(digest):
        raise ManifestError("registry response did not contain a valid sha256 digest")
    return digest


def validate_manifest(
    manifest: dict[str, Any],
    *,
    expected_repository: str,
    expected_sha: str,
    expected_ci_run_id: str,
    expected_ci_run_attempt: str,
    expected_image: str,
    expected_bundle_name: str,
    expected_frontend_profile: str,
    expected_acceptance_profile: str,
    bundle_dir: Path,
    registry_payload: Any,
    image_labels: Any,
    expected_bundle_runtime: str | None = None,
) -> str:
    try:
        mapped_acceptance_profile = acceptance_profile_for_frontend(expected_frontend_profile)
    except ValueError as error:
        raise ManifestError(str(error)) from error
    if mapped_acceptance_profile != expected_acceptance_profile:
        raise ManifestError("expected acceptance profile does not match the selected frontend profile")
    image_digest = validate_manifest_payload(
        manifest,
        expected_repository=expected_repository,
        expected_sha=expected_sha,
        expected_ci_run_id=expected_ci_run_id,
        expected_ci_run_attempt=expected_ci_run_attempt,
        expected_image=expected_image,
        expected_bundle_name=expected_bundle_name,
        expected_frontend_profile=expected_frontend_profile,
        expected_acceptance_profile=expected_acceptance_profile,
        bundle_dir=bundle_dir,
        expected_bundle_runtime=expected_bundle_runtime,
    )
    schema_version = manifest["schema_version"]
    if registry_digest(registry_payload, expected_image=expected_image) != image_digest:
        raise ManifestError("registry digest does not match the release manifest")

    if not isinstance(image_labels, dict):
        raise ManifestError("image labels must be an object")
    expected_ci_repository = expected_repository.removeprefix("https://github.com/")
    if expected_ci_repository == expected_repository or "/" not in expected_ci_repository:
        raise ManifestError("expected repository must be a GitHub repository URL")
    common_labels = {
        "org.opencontainers.image.source": expected_repository,
        "localcluster.ci.repository": expected_ci_repository,
        "localcluster.ci.run_id": expected_ci_run_id,
        "localcluster.ci.run_attempt": expected_ci_run_attempt,
    }
    for key, expected in common_labels.items():
        if image_labels.get(key) != expected:
            raise ManifestError(f"image label {key!r} does not match the verified CI release")
    profile_labels = {
        FRONTEND_PROFILE_LABEL: expected_frontend_profile,
        ACCEPTANCE_PROFILE_LABEL: expected_acceptance_profile,
        REVISION_LABEL: expected_sha,
    }
    if schema_version == 2:
        for key, expected in profile_labels.items():
            if image_labels.get(key) != expected:
                raise ManifestError(f"image label {key!r} does not match the release manifest")
    else:
        for key, expected in profile_labels.items():
            if key in image_labels and image_labels[key] != expected:
                raise ManifestError(f"legacy image label {key!r} conflicts with the Blazor release")

    return image_digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry-json", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-ci-run-id", required=True)
    parser.add_argument("--expected-ci-run-attempt", required=True)
    parser.add_argument("--expected-image", required=True)
    parser.add_argument("--expected-bundle-name", required=True)
    parser.add_argument("--expected-frontend-profile", required=True)
    parser.add_argument("--expected-acceptance-profile", required=True)
    parser.add_argument("--expected-bundle-runtime")
    parser.add_argument("--image-labels-json", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        registry_payload = json.loads(args.registry_json.read_text(encoding="utf-8"))
        image_labels = json.loads(args.image_labels_json.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not isinstance(registry_payload, (dict, list)):
            raise ManifestError("manifest must be an object and registry response must be an object or list")
        digest = validate_manifest(
            manifest,
            expected_repository=args.expected_repository,
            expected_sha=args.expected_sha,
            expected_ci_run_id=args.expected_ci_run_id,
            expected_ci_run_attempt=args.expected_ci_run_attempt,
            expected_image=args.expected_image,
            expected_bundle_name=args.expected_bundle_name,
            expected_frontend_profile=args.expected_frontend_profile,
            expected_acceptance_profile=args.expected_acceptance_profile,
            bundle_dir=args.bundle_dir,
            registry_payload=registry_payload,
            image_labels=image_labels,
            expected_bundle_runtime=args.expected_bundle_runtime,
        )
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"release manifest validation failed: {exc}", flush=True)
        return 1
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
