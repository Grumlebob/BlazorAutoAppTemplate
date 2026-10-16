"""Resolve optional releases without changing the selected frontend or primary names."""

from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts/Frontend"))
sys.path.insert(0, str(ROOT / "Deployment/Common/Scripts/Component/lib"))
from resolve_frontend_profile import acceptance_profile_for_frontend  # noqa: E402
from release_settings import derive_release_payload_image, load_release_settings  # noqa: E402


def release_plan(selected: str, additional: str, settings: dict[str, str]) -> dict[str, str]:
    acceptance_profile_for_frontend(selected)
    values = {
        "additional_profile": "",
        "additional_acceptance_profile": "",
        "additional_image": "",
        "additional_payload_image": "",
    }
    if not additional.strip():
        return values
    profiles = [value.strip() for value in additional.split(",")]
    seen = {selected}
    for profile in profiles:
        acceptance_profile_for_frontend(profile)
        if profile in seen:
            raise ValueError("additional frontend profiles must be unique and exclude the selected profile")
        seen.add(profile)
    if len(profiles) != 1:
        raise ValueError("only one additional frontend is supported")
    profile = profiles[0]
    values.update(
        additional_profile=profile,
        additional_acceptance_profile=acceptance_profile_for_frontend(profile),
        additional_image=f"{settings['app_image']}-{profile.lower()}",
        additional_payload_image=derive_release_payload_image(
            f"{settings['app_image']}-{profile.lower()}", settings.get("release_payload_prefix", "")
        ),
    )
    return values


def main() -> int:
    try:
        values = release_plan(
            os.environ["RESOLVED_FRONTEND_PROFILE"],
            os.environ.get("ADDITIONAL_FRONTEND_PROFILES", ""),
            load_release_settings(ROOT / "Deployment/Common/release.yml"),
        )
        # Only validated canonical values reach the workflow output file.
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            for key, value in values.items():
                output.write(f"{key}={value}\n")
    except (ValueError, KeyError, OSError) as error:
        print(f"Frontend release plan rejected: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
