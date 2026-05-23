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
sys.path.insert(0, str(root / "Deployment/LocalCluster/scripts/lib"))

from deploy_settings import load_settings  # noqa: E402


settings_path = root / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml"
inventory_path = root / "Deployment/LocalCluster/inventory/prod/hosts.yml"


def marker(value: str) -> str:
    return "BLOCKER" if value.startswith("REPLACE_WITH") or not value else "OK"


try:
    settings = load_settings(settings_path, validate_file=True)
except ValueError as exc:
    raise SystemExit(f"deployment summary failed: {exc}")

print("LocalCluster deployment summary")
print()
print("Settings")
for key in [
    "app_name",
    "app_image",
    "public_hostname",
    "deploy_root",
    "app_port",
    "postgres_port",
    "redis_port",
    "cloudflare_tunnel_name",
    "cloudflared_version",
    "migration_bundle_name",
    "runner_name",
    "runner_label",
]:
    value = settings[key]
    print(f"  {key:<24} {value} [{marker(value)}]")

print()
print("Target nodes")
if not inventory_path.exists():
    print("  inventory missing: Deployment/LocalCluster/inventory/prod/hosts.yml")
    raise SystemExit(0)

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
print("Derived paths")
print(f"  deploy ssh key          ~/.ssh/{settings['app_name']}_deploy")
print(f"  runner directory        /opt/actions-runner-{settings['app_name']}")
print(f"  app marker              /etc/localcluster/apps/{settings['app_name']}.env")
PY
