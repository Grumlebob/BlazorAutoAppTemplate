"""Write a profile-specific manifest from the verified staging bundle and pushed image."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Mapping

from migration_staging_artifact import validate_staging_artifact

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Scripts/Frontend"))
from resolve_frontend_profile import acceptance_profile_for_frontend  # noqa: E402


def write_manifest(directory: Path, digests: object, labels: object, env: Mapping[str, str]) -> dict:
    profile = env["FRONTEND_PROFILE"]
    if acceptance_profile_for_frontend(profile) != env["FRONTEND_ACCEPTANCE_PROFILE"]:
        raise ValueError("release acceptance profile does not match frontend")
    if not isinstance(digests, list) or not isinstance(labels, dict):
        raise ValueError("docker image inspect must return RepoDigests and image labels")
    image_prefix = f"{env['APP_IMAGE']}@"
    matches = [value.split("@", 1)[1] for value in digests
               if isinstance(value, str) and value.startswith(image_prefix)]
    if len(matches) != 1 or not re.fullmatch(r"sha256:[0-9a-f]{64}", matches[0]):
        raise ValueError("expected exactly one pushed registry digest for the configured image")
    digest = matches[0]
    expected_labels = {
        "org.opencontainers.image.source": f"{env['GITHUB_SERVER_URL']}/{env['GITHUB_REPOSITORY']}",
        "org.opencontainers.image.revision": env["GITHUB_SHA"],
        "com.blazorautoapp.frontend-profile": profile,
        "com.blazorautoapp.acceptance-profile": env["FRONTEND_ACCEPTANCE_PROFILE"],
        "localcluster.ci.repository": env["GITHUB_REPOSITORY"],
        "localcluster.ci.owner": "ci-build",
        "localcluster.ci.run_id": env["GITHUB_RUN_ID"],
        "localcluster.ci.run_attempt": env["GITHUB_RUN_ATTEMPT"],
    }
    for key, expected in expected_labels.items():
        if labels.get(key) != expected:
            raise ValueError(f"pushed image label {key!r} does not match release metadata")
    # Validate the exact allowlist and source/run/runtime/hash again before writing.
    staging = validate_staging_artifact(directory, env["MIGRATION_BUNDLE_NAME"], env["MIGRATION_RUNTIME"], env)
    bundle_bytes = (directory / env["MIGRATION_BUNDLE_NAME"]).read_bytes()
    bundle_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
    if not bundle_bytes or bundle_sha256 != staging["bundle_sha256"]:
        raise ValueError("verified migration bundle changed before manifest creation")
    manifest = {
        "schema_version": 2,
        "repository": f"{env['GITHUB_SERVER_URL']}/{env['GITHUB_REPOSITORY']}",
        "commit_sha": env["GITHUB_SHA"],
        "frontend_profile": profile,
        "acceptance_profile": env["FRONTEND_ACCEPTANCE_PROFILE"],
        "ci_run_id": int(env["GITHUB_RUN_ID"]),
        "attempt": int(env["GITHUB_RUN_ATTEMPT"]),
        "image_ref": f"{env['APP_IMAGE']}:{env['GITHUB_SHA']}",
        "image_digest": digest,
        "ordered_migration_ids": staging["ordered_migration_ids"],
        "bundle": {"file": staging["bundle_filename"], "sha256": bundle_sha256, "runtime": staging["runtime"]},
        "tools": {"dotnet_sdk": staging["dotnet_sdk_version"]},
    }
    output = directory / "release-manifest.json"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--digests", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = write_manifest(args.directory, json.loads(args.digests.read_text(encoding="utf-8")),
                                  json.loads(args.labels.read_text(encoding="utf-8")), os.environ)
    except (ValueError, KeyError, OSError) as error:
        print(f"Release manifest rejected: {error}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
