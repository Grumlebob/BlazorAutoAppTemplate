#!/usr/bin/env python3
"""Publish an immutable final payload and emit its run-bound CI receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LIB = REPOSITORY_ROOT / "Deployment" / "Common" / "Scripts" / "Component" / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from ci_payload_receipt import ReceiptError, final_receipt, format_receipt_line  # noqa: E402
from registry_payload import (  # noqa: E402
    PayloadError,
    ReleasePayloadIdentity,
    publish_release_payload,
)
from release_manifest import sha256_file  # noqa: E402


def emit_payload_receipt(
    *,
    manifest_path: Path,
    bundle_path: Path | None,
    repository: str,
    commit_sha: str,
    run_id: str,
    run_attempt: str,
    profile: str,
    acceptance_profile: str | None,
    runtime: str,
    app_image: str,
    payload_image: str,
    payload_image_prefix: str = "",
) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PayloadError("release manifest is missing or invalid JSON") from error
    if not isinstance(manifest, dict):
        raise PayloadError("release manifest must be an object")
    image_digest = manifest.get("image_digest")
    if not isinstance(image_digest, str):
        raise PayloadError("release manifest application image digest is missing")
    bundle_filename = bundle_path.name if bundle_path is not None else None
    identity = ReleasePayloadIdentity(
        repository=repository,
        commit_sha=commit_sha,
        run_id=run_id,
        run_attempt=run_attempt,
        profile=profile,
        acceptance_profile=acceptance_profile,
        runtime=runtime,
        app_image=app_image,
        app_image_digest=image_digest,
        bundle_filename=bundle_filename,
        manifest_sha256=sha256_file(manifest_path),
        bundle_sha256=sha256_file(bundle_path) if bundle_path is not None else None,
        payload_image_prefix=payload_image_prefix,
    )
    if identity.payload_image != payload_image:
        raise PayloadError("configured release payload image does not match the derived application package")
    published = publish_release_payload(identity, manifest_path, bundle_path)
    return final_receipt(identity, published)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--acceptance-profile")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--app-image", required=True)
    parser.add_argument("--payload-image", required=True)
    parser.add_argument("--payload-image-prefix", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        receipt = emit_payload_receipt(
            manifest_path=args.manifest,
            bundle_path=args.bundle,
            repository=args.repository,
            commit_sha=args.commit_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            profile=args.profile,
            acceptance_profile=args.acceptance_profile,
            runtime=args.runtime,
            app_image=args.app_image,
            payload_image=args.payload_image,
            payload_image_prefix=args.payload_image_prefix,
        )
        print(format_receipt_line(receipt), flush=True)
    except (OSError, PayloadError, ReceiptError, ValueError) as error:
        print(f"release payload publication failed: {error}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
