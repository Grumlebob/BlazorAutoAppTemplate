#!/usr/bin/env python3
"""Resolve trusted acceptance profiles from this app's deployed release marker."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "Scripts" / "Frontend"))

from resolve_frontend_profile import (  # noqa: E402
    ACCEPTANCE_PROFILE_BY_FRONTEND,
    SUPPORTED_PROFILES,
)


def read_release_marker(path: Path) -> dict:
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read deployed release marker: {path}") from exc
    if not isinstance(release, dict):
        raise ValueError("deployed release marker must be a JSON object")
    schema = release.get("manifest_schema_version", 1)
    if type(schema) is not int or schema not in (1, 2):
        raise ValueError("deployed release marker has an unsupported manifest schema")
    return release


def resolve_release_acceptance(path: Path) -> tuple[str, str]:
    release = read_release_marker(path)
    schema = release.get("manifest_schema_version", 1)

    frontend = release.get("frontend_profile")
    acceptance = release.get("acceptance_profile")
    if schema == 1:
        if "frontend_profile" not in release and "acceptance_profile" not in release:
            return "BlazorAuto", "BlazorAutoV1"
        if frontend == "BlazorAuto" and acceptance == "BlazorAutoV1":
            return frontend, acceptance
        raise ValueError("schema-v1 releases are accepted only as BlazorAuto/BlazorAutoV1")

    if frontend not in SUPPORTED_PROFILES:
        raise ValueError("schema-v2 release marker has an unsupported frontend profile")
    expected = ACCEPTANCE_PROFILE_BY_FRONTEND[frontend]
    if acceptance != expected:
        raise ValueError("schema-v2 frontend and acceptance profiles do not match")
    return frontend, acceptance


def resolve_ci_run_id(path: Path, expected_source_repo_url: str = "") -> str:
    """Return the exact CI run that produced the accepted single-node release."""
    release = read_release_marker(path)
    source_sha = release.get("source_sha")
    deployed_sha = release.get("sha")
    if (not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha)
            or deployed_sha != source_sha):
        raise ValueError("deployed release marker has no valid source SHA")
    if expected_source_repo_url:
        recorded_source = release.get("source_repo_url")
        if (not isinstance(recorded_source, str)
                or recorded_source.casefold() != expected_source_repo_url.casefold()):
            raise ValueError("deployed release marker belongs to a different source repository")
    run_id = release.get("ci_run_id")
    run_attempt = release.get("ci_run_attempt")
    if not isinstance(run_id, str) or not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ValueError("deployed release marker has no valid CI run ID")
    if not isinstance(run_attempt, str) or not re.fullmatch(r"[1-9][0-9]*", run_attempt):
        raise ValueError("deployed release marker has no valid CI run attempt")
    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_file", type=Path)
    parser.add_argument("--ci-run-id", action="store_true", help="print the exact accepted CI run ID")
    parser.add_argument("--expected-source-repo-url", default="", help="require the marker to belong to this repository")
    args = parser.parse_args()
    try:
        if args.ci_run_id:
            print(resolve_ci_run_id(args.release_file, args.expected_source_repo_url))
            return 0
        frontend, acceptance = resolve_release_acceptance(args.release_file)
    except ValueError as exc:
        print(f"Release acceptance error: {exc}", file=sys.stderr)
        return 2
    print(frontend)
    print(acceptance)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
