from __future__ import annotations

import ipaddress
import re
import sys
from pathlib import Path

COMMON_LIB = Path(__file__).resolve().parents[5] / "Deployment/Common/Scripts/Component/lib"
sys.path.insert(0, str(COMMON_LIB))

from simple_yaml import read_simple_yaml  # noqa: E402


REQUIRED_KEYS = [
    "app_name",
    "app_port",
    "postgres_port",
    "redis_port",
    "public_hostname",
    "deploy_root",
    "cloudflare_tunnel_name",
    "cloudflared_version",
    "cloud_private_network_cidr",
    "cloud_main_private_ip",
    "cloud_app1_private_ip",
    "cloud_app2_private_ip",
    "cloud_db_private_ip",
]


def default_root() -> Path:
    return Path(__file__).resolve().parents[5]


def default_settings_path(root: Path | None = None) -> Path:
    resolved_root = root or default_root()
    return resolved_root / "Deployment/Cloud/inventory/prod/group_vars/all.yml"


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

    ports: dict[str, int] = {}
    for key in ["app_port", "postgres_port", "redis_port"]:
        port_value = values.get(key, "")
        if port_value:
            if not port_value.isdigit():
                errors.append(f"{key} must be a number")
                continue
            port = int(port_value)
            ports[key] = port
            if port < 1024 or port > 65535:
                errors.append(f"{key} must be between 1024 and 65535")

    seen_ports: dict[int, str] = {}
    for key, port in ports.items():
        previous_key = seen_ports.get(port)
        if previous_key:
            errors.append(f"{key} must not reuse {previous_key} ({port})")
        else:
            seen_ports[port] = key

    public_hostname = values.get("public_hostname", "")
    if public_hostname and not valid_dns_name(public_hostname):
        errors.append("public_hostname must be a DNS hostname inside your Cloudflare zone")

    deploy_root = values.get("deploy_root", "")
    if deploy_root:
        if not deploy_root.startswith("/opt/"):
            errors.append("deploy_root must be under /opt, for example /opt/bookscloud")
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
            errors.append("cloudflared_version must be an exact release like 2026.5.2")

    network_value = values.get("cloud_private_network_cidr", "")
    network: ipaddress.IPv4Network | None = None
    if network_value:
        try:
            parsed_network = ipaddress.ip_network(network_value, strict=True)
            if not isinstance(parsed_network, ipaddress.IPv4Network):
                errors.append("cloud_private_network_cidr must be an IPv4 CIDR")
            else:
                network = parsed_network
        except ValueError as exc:
            errors.append(f"cloud_private_network_cidr is invalid: {exc}")

    private_ips: dict[str, ipaddress.IPv4Address] = {}
    for key in [
        "cloud_main_private_ip",
        "cloud_app1_private_ip",
        "cloud_app2_private_ip",
        "cloud_db_private_ip",
    ]:
        value = values.get(key, "")
        if not value:
            continue
        try:
            address = ipaddress.ip_address(value)
            if not isinstance(address, ipaddress.IPv4Address):
                errors.append(f"{key} must be an IPv4 address")
                continue
            private_ips[key] = address
            if network and address not in network:
                errors.append(f"{key} must be inside {network}")
        except ValueError as exc:
            errors.append(f"{key} is invalid: {exc}")

    seen_ips: dict[ipaddress.IPv4Address, str] = {}
    for key, address in private_ips.items():
        previous_key = seen_ips.get(address)
        if previous_key:
            errors.append(f"{key} must not reuse {previous_key} ({address})")
        else:
            seen_ips[address] = key

    return errors


def load_settings(path: Path, validate_file: bool = True) -> dict[str, str]:
    values, parse_errors = read_simple_yaml(path)
    errors = parse_errors + (validate(values) if validate_file else [])
    if errors:
        joined = "\n".join(f" - {error}" for error in errors)
        raise ValueError(f"cloud settings validation failed:\n{joined}")
    return values
