#!/usr/bin/env python3
"""Extract only verified release payload references from a read-only status snapshot."""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import re
import sys
from pathlib import Path


SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
PACKAGE = re.compile(r"ghcr\.io/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9._/-]*-release-payload\Z")
POSITIVE = re.compile(r"[1-9][0-9]{0,19}\Z")


class ProtectionError(ValueError):
    pass


def protection(status: object, *, target: str, instance: str) -> dict:
    if not isinstance(status, dict) or type(status.get("schema_version")) is not int or status["schema_version"] != 1:
        raise ProtectionError("release status schema is unavailable")
    if (status.get("target") != target or status.get("shared_lock") != "held"
            or status.get("mutation") != "none" or status.get("live_identity") != "verified"):
        raise ProtectionError("release status does not prove a verified read-only target")

    consumers = []
    for slot in ("current_release", "recovery_release"):
        marker = status.get(slot)
        if marker is None and slot == "recovery_release":
            continue
        if not isinstance(marker, dict):
            raise ProtectionError(f"{slot} is unavailable")
        run_id, attempt, source_sha = marker.get("ci_run_id"), marker.get("ci_run_attempt"), marker.get("source_sha")
        if (not isinstance(run_id, str) or not POSITIVE.fullmatch(run_id)
                or not isinstance(attempt, str) or not POSITIVE.fullmatch(attempt)
                or not isinstance(source_sha, str) or not SHA.fullmatch(source_sha)):
            raise ProtectionError(f"{slot} producer identity is malformed")
        consumers.append({"run_id": int(run_id), "run_attempt": int(attempt), "target_sha": source_sha})

    references = status.get("registry_payload_references")
    if not isinstance(references, list) or len(references) > 2:
        raise ProtectionError("verified registry release references are unavailable")
    normalized = []
    for reference in references:
        if (not isinstance(reference, dict)
                or set(reference) != {"payload_image", "payload_digest", "ci_run_id", "ci_run_attempt", "source_sha"}
                or not isinstance(reference.get("payload_image"), str) or not PACKAGE.fullmatch(reference["payload_image"])
                or not isinstance(reference.get("payload_digest"), str) or not DIGEST.fullmatch(reference["payload_digest"])
                or not isinstance(reference.get("ci_run_id"), str) or not POSITIVE.fullmatch(reference["ci_run_id"])
                or not isinstance(reference.get("ci_run_attempt"), str) or not POSITIVE.fullmatch(reference["ci_run_attempt"])
                or not isinstance(reference.get("source_sha"), str) or not SHA.fullmatch(reference["source_sha"])):
            raise ProtectionError("a verified registry release reference is malformed")
        normalized.append({
            "package": reference["payload_image"], "digest": reference["payload_digest"],
            "run_id": int(reference["ci_run_id"]), "run_attempt": int(reference["ci_run_attempt"]),
            "source_sha": reference["source_sha"],
        })
    required_refs = {
        (marker["ci_run_id"], marker["ci_run_attempt"])
        for slot in ("current_release", "recovery_release")
        if isinstance((marker := status.get(slot)), dict)
        and (marker.get("payload_transport") == "ghcr-container"
             or (marker.get("payload_transport") == "local-pin"
                 and str(marker.get("release_payload_pin_key", "")).startswith("ghcr-")))
    }
    actual_refs = {(str(item["run_id"]), str(item["run_attempt"])) for item in normalized}
    if not required_refs.issubset(actual_refs):
        raise ProtectionError("a GHCR-backed current or recovery marker has no verified immutable payload reference")
    consumer_sources = {(str(item["run_id"]), str(item["run_attempt"])): item["target_sha"] for item in consumers}
    if any(consumer_sources.get((str(item["run_id"]), str(item["run_attempt"]))) != item["source_sha"]
           for item in normalized):
        raise ProtectionError("a registry payload reference differs from its protected release marker")

    return {
        "schema_version": 1,
        "target": target,
        "instance": instance,
        "complete": True,
        "consumers": consumers,
        "registry_payload_references": normalized,
    }


def format_output(value: dict, *, github_output: bool) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if not github_output:
        return "protection=" + serialized
    encoded = base64.b64encode(gzip.compress(serialized.encode("utf-8"), mtime=0)).decode("ascii")
    return "protection_gzip_b64=" + encoded


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-json", type=Path, required=True)
    parser.add_argument("--target", choices=("localcluster", "localsinglenode"), required=True)
    parser.add_argument("--instance", choices=("cluster", "primary", "additional"), required=True)
    parser.add_argument("--github-output", action="store_true",
                        help="Emit the validated protection snapshot as gzip-compressed base64 for a cross-job GitHub output")
    args = parser.parse_args(argv)
    try:
        if args.status_json.is_symlink() or not args.status_json.is_file() or args.status_json.stat().st_size > 1024 * 1024:
            raise ProtectionError("release status file is unsafe or exceeds its bound")
        status = json.loads(args.status_json.read_text(encoding="utf-8"))
        value = protection(status, target=args.target, instance=args.instance)
        print(format_output(value, github_output=args.github_output))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ProtectionError) as error:
        print(f"Release protection is incomplete; registry deletion is blocked: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
