#!/usr/bin/env python3
"""Validate the immutable CI release contract consumed by LocalCluster CD."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


class ManifestError(ValueError):
    """Raised when a release manifest or registry response is unsafe/incompatible."""


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
    bundle_dir: Path,
    registry_payload: Any,
) -> str:
    required = {
        "schema_version",
        "repository",
        "commit_sha",
        "ci_run_id",
        "attempt",
        "image_ref",
        "image_digest",
        "ordered_migration_ids",
        "bundle",
        "tools",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise ManifestError(f"release manifest missing fields: {missing}")
    if manifest["schema_version"] != 1:
        raise ManifestError(f"unsupported release manifest schema: {manifest['schema_version']!r}")
    if manifest["repository"] != expected_repository:
        raise ManifestError("release manifest repository does not match this repository")
    if manifest["commit_sha"] != expected_sha:
        raise ManifestError("release manifest commit_sha does not match expected_sha")
    if str(manifest["ci_run_id"]) != expected_ci_run_id:
        raise ManifestError("release manifest ci_run_id does not match the successful CI run")
    if not isinstance(manifest["attempt"], int) or manifest["attempt"] < 1:
        raise ManifestError("release manifest attempt must be a positive integer")
    if str(manifest["attempt"]) != expected_ci_run_attempt:
        raise ManifestError("release manifest attempt does not match the successful CI attempt")
    if manifest["image_ref"] != f"{expected_image}:{expected_sha}":
        raise ManifestError("release manifest image_ref does not match the exact release")
    image_digest = manifest["image_digest"]
    if not isinstance(image_digest, str) or not DIGEST_RE.fullmatch(image_digest):
        raise ManifestError("release manifest image_digest is not a valid registry digest")
    if registry_digest(registry_payload, expected_image=expected_image) != image_digest:
        raise ManifestError("registry digest does not match the release manifest")

    migrations = manifest["ordered_migration_ids"]
    if not isinstance(migrations, list) or not all(
        isinstance(item, str) and bool(item) for item in migrations
    ):
        raise ManifestError("release manifest ordered_migration_ids must be a list of non-empty strings")

    bundle = manifest["bundle"]
    if not isinstance(bundle, dict) or not bundle.get("file") or not bundle.get("sha256") or not bundle.get("runtime"):
        raise ManifestError("release manifest bundle metadata is incomplete")
    bundle_file = str(bundle["file"])
    if Path(bundle_file).name != bundle_file or bundle_file != expected_bundle_name:
        raise ManifestError("release manifest bundle file is not the configured artifact file")
    bundle_sha = str(bundle["sha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", bundle_sha):
        raise ManifestError("release manifest bundle sha256 is invalid")
    bundle_path = bundle_dir / bundle_file
    if not bundle_path.is_file():
        raise ManifestError(f"release manifest bundle is missing: {bundle_path}")
    actual_sha = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    if actual_sha != bundle_sha:
        raise ManifestError("release manifest bundle SHA-256 does not match the downloaded bundle")

    tools = manifest["tools"]
    if not isinstance(tools, dict) or not isinstance(tools.get("dotnet_sdk"), str) or not tools["dotnet_sdk"]:
        raise ManifestError("release manifest tools.dotnet_sdk is missing")
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        registry_payload = json.loads(args.registry_json.read_text(encoding="utf-8"))
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
            bundle_dir=args.bundle_dir,
            registry_payload=registry_payload,
        )
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"release manifest validation failed: {exc}", flush=True)
        return 1
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
