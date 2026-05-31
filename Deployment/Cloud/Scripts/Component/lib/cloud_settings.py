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
    "cloud_private_gateway_ip",
    "cloud_main_private_ip",
    "cloud_app1_private_ip",
    "cloud_app2_private_ip",
    "cloud_db_private_ip",
]

OPTIONAL_KEYS = [
    "observability_enabled",
    "observability_root",
    "observability_docker_network",
    "observability_trace_sample_ratio",
    "observability_grafana_port",
    "observability_alertmanager_port",
    "observability_prometheus_port",
    "observability_loki_port",
    "observability_tempo_http_port",
    "observability_tempo_otlp_grpc_port",
    "observability_tempo_otlp_http_port",
    "observability_alloy_http_port",
    "observability_node_exporter_port",
    "observability_postgres_exporter_port",
    "observability_redis_exporter_port",
    "observability_prometheus_retention_time",
    "observability_prometheus_retention_size",
    "observability_loki_retention_period",
    "observability_tempo_retention_period",
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
    allowed = set(REQUIRED_KEYS + OPTIONAL_KEYS)

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

    observability_enabled = values.get("observability_enabled", "")
    if observability_enabled and observability_enabled.lower() not in ["true", "false"]:
        errors.append("observability_enabled must be true or false")

    observability_root = values.get("observability_root", "")
    if observability_root:
        if not observability_root.startswith("/opt/"):
            errors.append("observability_root must be under /opt, for example /opt/bookscloud-observability")
        if re.search(r"\s", observability_root):
            errors.append("observability_root must not contain whitespace")
        if not re.match(r"^/[A-Za-z0-9._/-]+$", observability_root):
            errors.append("observability_root must contain only letters, numbers, dots, underscores, hyphens, and slashes")

    observability_network = values.get("observability_docker_network", "")
    if observability_network and not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$", observability_network):
        errors.append("observability_docker_network must be a valid Docker network name")

    trace_sample_ratio = values.get("observability_trace_sample_ratio", "")
    if trace_sample_ratio:
        try:
            ratio = float(trace_sample_ratio)
            if ratio < 0 or ratio > 1:
                errors.append("observability_trace_sample_ratio must be between 0 and 1")
        except ValueError:
            errors.append("observability_trace_sample_ratio must be a decimal number between 0 and 1")

    observability_port_keys = [
        "observability_grafana_port",
        "observability_alertmanager_port",
        "observability_prometheus_port",
        "observability_loki_port",
        "observability_tempo_http_port",
        "observability_tempo_otlp_grpc_port",
        "observability_tempo_otlp_http_port",
        "observability_alloy_http_port",
        "observability_node_exporter_port",
        "observability_postgres_exporter_port",
        "observability_redis_exporter_port",
    ]
    for key in observability_port_keys:
        port_value = values.get(key, "")
        if not port_value:
            continue
        if not port_value.isdigit():
            errors.append(f"{key} must be a number")
            continue
        port = int(port_value)
        if port < 1024 or port > 65535:
            errors.append(f"{key} must be between 1024 and 65535")
        previous_key = seen_ports.get(port)
        if previous_key:
            errors.append(f"{key} must not reuse {previous_key} ({port})")
        else:
            seen_ports[port] = key

    for key in [
        "observability_prometheus_retention_time",
        "observability_loki_retention_period",
        "observability_tempo_retention_period",
    ]:
        value = values.get(key, "")
        if value and not re.match(r"^[0-9]+[hdwmy]$", value):
            errors.append(f"{key} must look like 24h, 7d, 4w, 12m, or 1y")

    retention_size = values.get("observability_prometheus_retention_size", "")
    if retention_size and not re.match(r"^[0-9]+(MB|GB)$", retention_size):
        errors.append("observability_prometheus_retention_size must look like 512MB or 4GB")

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
        "cloud_private_gateway_ip",
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
        if key == "cloud_private_gateway_ip":
            continue
        previous_key = seen_ips.get(address)
        if previous_key:
            errors.append(f"{key} must not reuse {previous_key} ({address})")
        else:
            seen_ips[address] = key

    gateway_address = private_ips.get("cloud_private_gateway_ip")
    main_address = private_ips.get("cloud_main_private_ip")
    if gateway_address and main_address and gateway_address != main_address:
        errors.append("cloud_private_gateway_ip must match cloud_main_private_ip")

    return errors


def load_settings(path: Path, validate_file: bool = True) -> dict[str, str]:
    values, parse_errors = read_simple_yaml(path)
    errors = parse_errors + (validate(values) if validate_file else [])
    if errors:
        joined = "\n".join(f" - {error}" for error in errors)
        raise ValueError(f"cloud settings validation failed:\n{joined}")
    return values
