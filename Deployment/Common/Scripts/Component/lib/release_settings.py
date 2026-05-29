from __future__ import annotations

import re
from pathlib import Path


REQUIRED_KEYS = [
    "app_image",
    "migration_bundle_name",
    "migration_artifact_name",
]


def default_root() -> Path:
    return Path(__file__).resolve().parents[5]


def default_release_path(root: Path | None = None) -> Path:
    resolved_root = root or default_root()
    return resolved_root / "Deployment/Common/release.yml"


def read_simple_yaml(path: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    errors: list[str] = []

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", line)
        if not match:
            errors.append(f"{path}:{line_number}: unsupported setting line: {raw_line}")
            continue
        key, value = match.groups()
        if key in values:
            errors.append(f"{path}:{line_number}: duplicate setting: {key}")
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key] = value.strip()

    return values, errors


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

    migration_artifact_name = values.get("migration_artifact_name", "")
    if migration_artifact_name and not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", migration_artifact_name):
        errors.append("migration_artifact_name must be an artifact name with no spaces or slashes")

    return errors


def load_release_settings(path: Path, validate_file: bool = True) -> dict[str, str]:
    values, parse_errors = read_simple_yaml(path)
    errors = parse_errors + (validate(values) if validate_file else [])
    if errors:
        joined = "\n".join(f" - {error}" for error in errors)
        raise ValueError(f"release settings validation failed:\n{joined}")
    return values
