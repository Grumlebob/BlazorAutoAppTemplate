#!/usr/bin/env python3
"""Resolve the repository's single persisted frontend profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SUPPORTED_PROFILES = ("BlazorAuto", "React")
ACCEPTANCE_PROFILE_BY_FRONTEND = {
    "BlazorAuto": "BlazorAutoV1",
    "React": "ReactPublicV1",
}


def resolve_frontend_profile(profile_file: Path | str, override: str | None = None) -> str:
    """Return a canonical profile from an explicit override or the tracked file."""
    if override is not None:
        raw_value = override
        source = "profile override"
    else:
        path = Path(profile_file)
        try:
            raw_value = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise ValueError(f"cannot read frontend profile file: {path}") from exc
        source = "frontend profile file"

    profile = raw_value.strip()
    if not profile:
        raise ValueError(f"{source} is empty; expected exactly BlazorAuto or React")
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"{source} must be exactly BlazorAuto or React after trimming whitespace")
    return profile


def acceptance_profile_for_frontend(frontend_profile: str) -> str:
    """Return the trusted acceptance contract paired with a frontend profile."""
    try:
        return ACCEPTANCE_PROFILE_BY_FRONTEND[frontend_profile]
    except KeyError as exc:
        raise ValueError(f"unsupported frontend profile for acceptance: {frontend_profile!r}") from exc


def main(argv: list[str] | None = None) -> int:
    repository_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-file",
        type=Path,
        default=repository_root / "frontend-profile.txt",
        help="profile file to validate (defaults to the tracked repository file)",
    )
    parser.add_argument(
        "--override",
        help="explicit temporary build-validation override; does not change the tracked file",
    )
    parser.add_argument(
        "--acceptance-profile",
        action="store_true",
        help="emit the trusted acceptance profile paired with the resolved frontend profile",
    )
    parser.add_argument(
        "--legacy-blazor-default",
        action="store_true",
        help="use BlazorAuto only when the selected profile file is missing for a legacy release",
    )
    args = parser.parse_args(argv)

    try:
        if args.legacy_blazor_default and args.override is None and not args.profile_file.exists():
            profile = "BlazorAuto"
        else:
            profile = resolve_frontend_profile(args.profile_file, args.override)
    except ValueError as exc:
        print(f"Frontend profile error: {exc}", file=sys.stderr)
        return 2

    print(acceptance_profile_for_frontend(profile) if args.acceptance_profile else profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
