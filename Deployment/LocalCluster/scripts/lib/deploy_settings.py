from __future__ import annotations

import re
from pathlib import Path


REQUIRED_KEYS = [
    "app_name",
    "app_image",
    "app_port",
    "public_hostname",
    "deploy_root",
    "cloudflare_tunnel_name",
    "cloudflared_version",
    "migration_bundle_name",
]


def default_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_settings_path(root: Path | None = None) -> Path:
    resolved_root = root or default_root()
    return resolved_root / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml"


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


def valid_dns_name(value: str) -> bool:
    if len(value) > 253 or "." not in value:
        return False
    labels = value.rstrip(".").split(".")
    for label in labels:
        if not 1 <= len(label) <= 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not re.match(r"^[A-Za-z0-9-]+$", label):
            return False
    return True


def validate(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    allowed = set(REQUIRED_KEYS)

    for key in REQUIRED_KEYS:
        if key not in values:
            errors.append(f"missing required setting: {key}")
        elif not values[key]:
            errors.append(f"{key} must not be empty")

    for key in values:
        if key not in allowed:
            errors.append(f"unknown setting: {key}")

    app_name = values.get("app_name", "")
    if app_name and not re.match(r"^[a-z][a-z0-9-]{0,31}$", app_name):
        errors.append("app_name must be lowercase, start with a letter, and contain only letters, numbers, or hyphens")

    app_image = values.get("app_image", "")
    if app_image and not re.match(r"^ghcr\.io/[a-z0-9][a-z0-9_.-]*(/[a-z0-9][a-z0-9_.-]*)+$", app_image):
        errors.append("app_image must be a lowercase GHCR image path like ghcr.io/<owner>/<image>")

    app_port = values.get("app_port", "")
    if app_port:
        if not app_port.isdigit():
            errors.append("app_port must be a number")
        else:
            port = int(app_port)
            if port < 1024 or port > 65535:
                errors.append("app_port must be between 1024 and 65535")

    public_hostname = values.get("public_hostname", "")
    if public_hostname and not valid_dns_name(public_hostname):
        errors.append("public_hostname must be a DNS hostname inside your Cloudflare zone, for example ship.example.com")

    deploy_root = values.get("deploy_root", "")
    if deploy_root:
        if not deploy_root.startswith("/opt/"):
            errors.append("deploy_root must be under /opt, for example /opt/ship")
        if re.search(r"\s", deploy_root):
            errors.append("deploy_root must not contain whitespace")
        if not re.match(r"^/[A-Za-z0-9._/-]+$", deploy_root):
            errors.append("deploy_root must contain only letters, numbers, dots, underscores, hyphens, and slashes")

    tunnel_name = values.get("cloudflare_tunnel_name", "")
    if tunnel_name and not re.match(r"^[a-z][a-z0-9-]{0,63}$", tunnel_name):
        errors.append("cloudflare_tunnel_name must be lowercase, start with a letter, and contain only letters, numbers, or hyphens")

    cloudflared_version = values.get("cloudflared_version", "")
    if cloudflared_version:
        if cloudflared_version == "latest":
            errors.append("cloudflared_version must be pinned, not latest")
        elif not re.match(r"^[0-9]{4}\.[0-9]{1,2}\.[0-9]+$", cloudflared_version):
            errors.append("cloudflared_version must be an exact release like 2026.5.0")

    migration_bundle_name = values.get("migration_bundle_name", "")
    if migration_bundle_name and not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", migration_bundle_name):
        errors.append("migration_bundle_name must be a filename with no spaces or slashes")

    return errors


def load_settings(path: Path, validate_file: bool = True) -> dict[str, str]:
    values, parse_errors = read_simple_yaml(path)
    errors = parse_errors + (validate(values) if validate_file else [])
    if errors:
        joined = "\n".join(f" - {error}" for error in errors)
        raise ValueError(f"deployment settings validation failed:\n{joined}")
    return values
