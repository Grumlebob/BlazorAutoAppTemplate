from __future__ import annotations

import re
from pathlib import Path

from simple_yaml import read_simple_yaml


REQUIRED_KEYS = [
    "app_image",
    "migration_bundle_name",
    "migration_runtime",
]
IMAGE_COMPONENT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?$")
PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")


def validate_app_image(app_image: str) -> str:
    parts = app_image.split("/")
    if len(parts) < 3 or parts[0] != "ghcr.io" or any(not IMAGE_COMPONENT_RE.fullmatch(part) for part in parts[1:]):
        raise ValueError("app_image must be a lowercase GHCR image path like ghcr.io/<owner>/<image>")
    return app_image


def validate_profile_name(profile: str) -> str:
    if not isinstance(profile, str) or not PROFILE_NAME_RE.fullmatch(profile) or profile in {".", ".."}:
        raise ValueError("release profile must be a short safe name without path or tag separators")
    return profile


def derive_release_payload_image(app_image: str) -> str:
    return f"{validate_app_image(app_image)}-release-payload"


def default_root() -> Path:
    return Path(__file__).resolve().parents[5]


def default_release_path(root: Path | None = None) -> Path:
    resolved_root = root or default_root()
    return resolved_root / "Deployment/Common/release.yml"


def validate(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    allowed = set(REQUIRED_KEYS)

    for key in REQUIRED_KEYS:
        if key not in values:
            errors.append(f"missing required release setting: {key}")
        elif not values[key]:
            errors.append(f"{key} must not be empty")

    for key in values:
        if key not in allowed:
            errors.append(f"unknown release setting: {key}")

    app_image = values.get("app_image", "")
    if app_image:
        try:
            validate_app_image(app_image)
        except ValueError as error:
            errors.append(str(error))

    migration_bundle_name = values.get("migration_bundle_name", "")
    if migration_bundle_name and not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", migration_bundle_name):
        errors.append("migration_bundle_name must be a filename with no spaces or slashes")

    migration_runtime = values.get("migration_runtime", "")
    if migration_runtime and not re.match(r"^linux-(x64|arm64)$", migration_runtime):
        errors.append("migration_runtime must be linux-x64 or linux-arm64")

    return errors


def apply_defaults(values: dict[str, str]) -> dict[str, str]:
    resolved = dict(values)
    app_image = resolved.get("app_image", "").strip()
    if app_image:
        try:
            resolved["release_payload_image"] = derive_release_payload_image(app_image)
        except ValueError:
            # Validation reports malformed configured paths with the source key.
            pass
    bundle = resolved.get("migration_bundle_name", "").strip()
    runtime = resolved.get("migration_runtime", "").strip()
    if bundle and runtime:
        resolved["migration_artifact_name"] = f"{bundle}-{runtime}"
    return resolved


def load_release_settings(path: Path, validate_file: bool = True) -> dict[str, str]:
    values, parse_errors = read_simple_yaml(path)
    errors = parse_errors + (validate(values) if validate_file else [])
    values = apply_defaults(values)
    if errors:
        joined = "\n".join(f" - {error}" for error in errors)
        raise ValueError(f"release settings validation failed:\n{joined}")
    return values
