from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
BUNDLE_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
CONTENT_REVISION_RE = re.compile(r"[0-9a-f]{16}\Z")
MAX_BUNDLE_BYTES = 1024 * 1024 * 1024


class ManifestError(ValueError):
    """Raised when release metadata or its bundle does not match the selected CI run."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest_payload(
    manifest: dict[str, Any],
    *,
    expected_repository: str,
    expected_sha: str,
    expected_ci_run_id: str,
    expected_ci_run_attempt: str,
    expected_image: str,
    expected_bundle_name: str | None = None,
    expected_frontend_profile: str | None = None,
    expected_acceptance_profile: str | None = None,
    bundle_dir: Path | None = None,
    expected_bundle_runtime: str | None = None,
    require_migration_metadata: bool = True,
    require_bundle_runtime: bool = True,
    allowed_schema_versions: tuple[int, ...] = (1, 2),
) -> str:
    """Validate common release identity plus the configured bundle or file-only schema."""
    if not isinstance(manifest, dict):
        raise ManifestError("release manifest must be an object")
    required = {
        "schema_version",
        "repository",
        "commit_sha",
        "ci_run_id",
        "attempt",
        "image_ref",
        "image_digest",
    }
    if expected_bundle_name is not None:
        required.add("bundle")
        if require_migration_metadata:
            required.update({"ordered_migration_ids", "tools"})
    if 3 in allowed_schema_versions:
        required.add("content_revision")
    missing = sorted(required.difference(manifest))
    if missing:
        raise ManifestError(f"release manifest missing fields: {missing}")

    schema_version = manifest["schema_version"]
    if type(schema_version) is not int or schema_version not in allowed_schema_versions:
        raise ManifestError(f"unsupported release manifest schema: {schema_version!r}")
    if manifest["repository"] != expected_repository:
        raise ManifestError("release manifest repository does not match this repository")
    if manifest["commit_sha"] != expected_sha:
        raise ManifestError("release manifest commit_sha does not match expected_sha")
    if str(manifest["ci_run_id"]) != expected_ci_run_id:
        raise ManifestError("release manifest ci_run_id does not match the successful CI run")
    if (
        not isinstance(manifest["attempt"], int)
        or isinstance(manifest["attempt"], bool)
        or manifest["attempt"] < 1
    ):
        raise ManifestError("release manifest attempt must be a positive integer")
    if str(manifest["attempt"]) != expected_ci_run_attempt:
        raise ManifestError("release manifest attempt does not match the successful CI attempt")
    if manifest["image_ref"] != f"{expected_image}:{expected_sha}":
        raise ManifestError("release manifest image_ref does not match the exact release")
    image_digest = manifest["image_digest"]
    if not isinstance(image_digest, str) or not DIGEST_RE.fullmatch(image_digest):
        raise ManifestError("release manifest image_digest is not a valid registry digest")

    if (expected_frontend_profile is None) != (expected_acceptance_profile is None):
        raise ManifestError("expected frontend and acceptance profiles must be supplied together")
    if schema_version == 1:
        if expected_frontend_profile is not None and (expected_frontend_profile, expected_acceptance_profile) != (
            "BlazorAuto",
            "BlazorAutoV1",
        ):
            raise ManifestError("legacy schema v1 is supported only for verified BlazorAuto releases")
        if "frontend_profile" in manifest or "acceptance_profile" in manifest:
            raise ManifestError("schema v1 cannot contain frontend/acceptance metadata; use schema v2")
    elif schema_version in (2, 3):
        if expected_frontend_profile is None:
            raise ManifestError("profile-aware release schema requires expected frontend and acceptance profiles")
        required_profiles = {"frontend_profile", "acceptance_profile"}
        missing_profiles = sorted(required_profiles.difference(manifest))
        if missing_profiles:
            raise ManifestError(f"release manifest is missing profile fields: {missing_profiles}")
        if manifest["frontend_profile"] != expected_frontend_profile:
            raise ManifestError("release manifest frontend_profile does not match the target source selection")
        if manifest["acceptance_profile"] != expected_acceptance_profile:
            raise ManifestError("release manifest acceptance_profile does not match the frontend contract")

    if expected_bundle_name is None:
        if schema_version != 3:
            raise ManifestError("file-only release manifests must use schema version 3")
        if "bundle" in manifest:
            raise ManifestError("file-only release manifest cannot contain a migration bundle")
        revision = manifest["content_revision"]
        if not isinstance(revision, str) or not CONTENT_REVISION_RE.fullmatch(revision):
            raise ManifestError("release manifest content_revision must be 16 lowercase hex characters")
        return image_digest

    if bundle_dir is None:
        raise ManifestError("bundle directory is required for a migration release manifest")
    if "ordered_migration_ids" in manifest:
        migrations = manifest["ordered_migration_ids"]
        if not isinstance(migrations, list) or not all(
            isinstance(item, str) and bool(item) for item in migrations
        ):
            raise ManifestError("release manifest ordered_migration_ids must be a list of non-empty strings")
    bundle = manifest["bundle"]
    if not isinstance(bundle, dict) or not bundle.get("file") or not bundle.get("sha256"):
        raise ManifestError("release manifest bundle metadata is incomplete")
    if require_bundle_runtime and not bundle.get("runtime"):
        raise ManifestError("release manifest bundle runtime is missing")
    bundle_file = bundle["file"]
    if (
        not isinstance(bundle_file, str)
        or "/" in bundle_file
        or "\\" in bundle_file
        or Path(bundle_file).name != bundle_file
        or bundle_file != expected_bundle_name
    ):
        raise ManifestError("release manifest bundle file is not the configured artifact file")
    bundle_sha = bundle["sha256"]
    if not isinstance(bundle_sha, str) or not BUNDLE_SHA_RE.fullmatch(bundle_sha):
        raise ManifestError("release manifest bundle sha256 is invalid")
    bundle_runtime = bundle.get("runtime")
    if "runtime" in bundle and (not isinstance(bundle_runtime, str) or not bundle_runtime):
        raise ManifestError("release manifest bundle runtime is invalid")
    if expected_bundle_runtime is not None and bundle_runtime != expected_bundle_runtime:
        raise ManifestError("release manifest bundle runtime does not match the configured runtime")
    bundle_path = bundle_dir / bundle_file
    if bundle_path.is_symlink() or not bundle_path.is_file():
        raise ManifestError(f"release manifest bundle is missing or not a regular file: {bundle_path}")
    bundle_size = bundle_path.stat().st_size
    if bundle_size <= 0 or bundle_size > MAX_BUNDLE_BYTES:
        raise ManifestError("release manifest bundle has an invalid size")
    if sha256_file(bundle_path) != bundle_sha:
        raise ManifestError("release manifest bundle SHA-256 does not match the downloaded bundle")

    if "tools" in manifest:
        tools = manifest["tools"]
        if not isinstance(tools, dict) or not isinstance(tools.get("dotnet_sdk"), str) or not tools["dotnet_sdk"]:
            raise ManifestError("release manifest tools.dotnet_sdk is missing")
    return image_digest
