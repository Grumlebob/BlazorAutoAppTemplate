#!/usr/bin/env python3
"""Resolve trusted acceptance profiles from this app's deployed release marker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "Scripts" / "Frontend"))

from resolve_frontend_profile import (  # noqa: E402
    ACCEPTANCE_PROFILE_BY_FRONTEND,
    SUPPORTED_PROFILES,
)


def resolve_release_acceptance(path: Path) -> tuple[str, str]:
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read deployed release marker: {path}") from exc
    if not isinstance(release, dict):
        raise ValueError("deployed release marker must be a JSON object")

    schema = release.get("manifest_schema_version", 1)
    if type(schema) is not int or schema not in (1, 2):
        raise ValueError("deployed release marker has an unsupported manifest schema")

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_file", type=Path)
    args = parser.parse_args()
    try:
        frontend, acceptance = resolve_release_acceptance(args.release_file)
    except ValueError as exc:
        print(f"Release acceptance error: {exc}", file=sys.stderr)
        return 2
    print(frontend)
    print(acceptance)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
