from __future__ import annotations

import re
from pathlib import Path

from simple_yaml import read_simple_yaml


REQUIRED_KEYS = [
    "app_image",
    "migration_bundle_name",
    "migration_runtime",
]


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
    if app_image and not re.match(r"^ghcr\.io/[a-z0-9][a-z0-9_.-]*(/[a-z0-9][a-z0-9_.-]*)+$", app_image):
        errors.append("app_image must be a lowercase GHCR image path like ghcr.io/<owner>/<image>")

    migration_bundle_name = values.get("migration_bundle_name", "")
    if migration_bundle_name and not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", migration_bundle_name):
        errors.append("migration_bundle_name must be a filename with no spaces or slashes")

    migration_runtime = values.get("migration_runtime", "")
    if migration_runtime and not re.match(r"^linux-(x64|arm64)$", migration_runtime):
        errors.append("migration_runtime must be linux-x64 or linux-arm64")

    return errors


def apply_defaults(values: dict[str, str]) -> dict[str, str]:
    resolved = dict(values)
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
