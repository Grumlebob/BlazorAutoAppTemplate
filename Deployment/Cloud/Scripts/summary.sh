#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python3 - "$REPO_ROOT" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "Deployment/Cloud/Scripts/Component/lib"))
sys.path.insert(0, str(root / "Deployment/Common/Scripts/Component/lib"))

from cloud_settings import load_settings  # noqa: E402
from release_settings import load_release_settings  # noqa: E402


settings_path = root / "Deployment/Cloud/inventory/prod/group_vars/all.yml"
release_path = root / "Deployment/Common/release.yml"
inventory_path = root / "Deployment/Cloud/inventory/prod/hosts.yml"


def marker(value: str) -> str:
    return "BLOCKER" if value.startswith("REPLACE_WITH") or not value else "OK"


try:
    settings = load_settings(settings_path, validate_file=True)
    release_settings = load_release_settings(release_path, validate_file=True)
except ValueError as exc:
    raise SystemExit(f"cloud deployment summary failed: {exc}")

print("Cloud deployment summary")
print()
print("Release")
for key in [
    "app_image",
    "migration_bundle_name",
    "migration_runtime",
    "migration_artifact_name",
]:
    value = release_settings[key]
    print(f"  {key:<28} {value} [{marker(value)}]")

print()
print("Cloud settings")
for key in [
    "app_name",
    "public_hostname",
    "deploy_root",
    "app_port",
    "postgres_port",
    "redis_port",
    "cloudflare_tunnel_name",
    "cloudflared_version",
    "cloud_private_network_cidr",
    "cloud_main_private_ip",
    "cloud_app1_private_ip",
    "cloud_app2_private_ip",
    "cloud_db_private_ip",
    "observability_enabled",
    "observability_root",
    "observability_docker_network",
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
]:
    value = settings[key]
    print(f"  {key:<28} {value} [{marker(value)}]")

print()
print("Target nodes")
if not inventory_path.exists():
    print("  inventory not rendered yet [WAIT for Step 8]")
    print("  Step 8 creates Deployment/Cloud/inventory/prod/hosts.yml after OpenTofu apply.")
else:
    current_host: str | None = None
    hosts: list[tuple[str, str]] = []
    for raw_line in inventory_path.read_text(encoding="utf-8-sig").splitlines():
        host_match = re.match(r"^\s{8,}([A-Za-z0-9_-]+):\s*$", raw_line)
        if host_match:
            current_host = host_match.group(1)
            continue
        ip_match = re.match(r"^\s{10,}ansible_host:\s*(\S+)\s*$", raw_line)
        if current_host and ip_match:
            hosts.append((current_host, ip_match.group(1)))
            current_host = None

    if not hosts:
        print("  no hosts found in inventory")
    else:
        for host, ip in hosts:
            print(f"  {host:<12} {ip} [{marker(ip)}]")

print()
print("Ownership")
print("  OpenTofu owns Hetzner servers, network, primary IPs, and cloud firewalls.")
print("  Ansible owns host firewall rules, Docker, services, compose, and deployment.")
print("  Deployment/Common owns shared release artifact names.")
PY
