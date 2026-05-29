#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
CLOUD_LIB = REPO_ROOT / "Deployment/Cloud/Scripts/Component/lib"
sys.path.insert(0, str(CLOUD_LIB))

from cloud_settings import load_settings  # noqa: E402


EXPECTED_HOSTS = {
    "cloud-main": ("load_balancer", "cloud_main_private_ip", "public"),
    "cloud-app1": ("app_servers", "cloud_app1_private_ip", "private"),
    "cloud-app2": ("app_servers", "cloud_app2_private_ip", "private"),
    "cloud-db": ("node_db", "cloud_db_private_ip", "private"),
}


def fail(message: str) -> None:
    raise SystemExit(f"Cloud inventory validation failed: {message}")


def run_ansible_inventory(inventory_path: Path) -> dict[str, object]:
    result = subprocess.run(
        ["ansible-inventory", "-i", str(inventory_path), "--list"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        fail(f"ansible-inventory failed: {details}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"ansible-inventory returned invalid JSON: {exc}")
    if not isinstance(payload, dict):
        fail("ansible-inventory returned an unexpected payload")
    return payload


def group_hosts(payload: dict[str, object], group_name: str) -> set[str]:
    group = payload.get(group_name)
    if not isinstance(group, dict):
        fail(f"missing inventory group: {group_name}")
    hosts = group.get("hosts")
    if not isinstance(hosts, list):
        fail(f"group {group_name} has no hosts list")
    return {host for host in hosts if isinstance(host, str)}


def hostvars(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    meta = payload.get("_meta")
    if not isinstance(meta, dict):
        fail("missing _meta in inventory")
    values = meta.get("hostvars")
    if not isinstance(values, dict):
        fail("missing _meta.hostvars in inventory")
    return {
        host: vars_
        for host, vars_ in values.items()
        if isinstance(host, str) and isinstance(vars_, dict)
    }


def require_text(vars_: dict[str, object], host: str, key: str) -> str:
    value = vars_.get(key)
    if not isinstance(value, str) or not value:
        fail(f"{host} is missing {key}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate rendered Cloud Ansible inventory.")
    parser.add_argument(
        "--inventory",
        default=str(REPO_ROOT / "Deployment/Cloud/inventory/prod/hosts.yml"),
    )
    args = parser.parse_args()

    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        fail(f"missing inventory: {inventory_path.relative_to(REPO_ROOT)}. Run Step 8 first.")

    settings = load_settings(REPO_ROOT / "Deployment/Cloud/inventory/prod/group_vars/all.yml")
    payload = run_ansible_inventory(inventory_path)
    vars_by_host = hostvars(payload)

    bastion_vars = vars_by_host.get("cloud-main")
    if not isinstance(bastion_vars, dict):
        fail("cloud-main is missing from hostvars")
    bastion_public_ip = require_text(bastion_vars, "cloud-main", "ansible_host")

    rows: list[tuple[str, str, str, str, str]] = []
    for host, (group_name, private_setting_key, expected_route) in EXPECTED_HOSTS.items():
        hosts = group_hosts(payload, group_name)
        if host not in hosts:
            fail(f"{host} is not in expected group {group_name}")
        vars_ = vars_by_host.get(host)
        if not isinstance(vars_, dict):
            fail(f"{host} is missing from hostvars")

        ansible_host = require_text(vars_, host, "ansible_host")
        private_ip = require_text(vars_, host, "cloud_private_ip")
        expected_private_ip = settings[private_setting_key]
        if private_ip != expected_private_ip:
            fail(f"{host} private IP is {private_ip}, expected {expected_private_ip}")

        public_ip = require_text(vars_, host, "cloud_public_ipv4")
        ssh_args = str(vars_.get("ansible_ssh_common_args", ""))

        if expected_route == "public":
            if ansible_host != public_ip:
                fail(f"{host} should use public ansible_host {public_ip}, got {ansible_host}")
            if "ProxyJump" in ssh_args or "ProxyCommand" in ssh_args:
                fail(f"{host} should not use a SSH proxy")
            route = "direct public SSH"
        else:
            if ansible_host != private_ip:
                fail(f"{host} should use private ansible_host {private_ip}, got {ansible_host}")
            if "ProxyJump" in ssh_args:
                fail(f"{host} uses ProxyJump; rerender inventory so the bastion leg gets the explicit deploy key")
            if "ProxyCommand=" not in ssh_args:
                fail(f"{host} should use ProxyCommand through cloud-main")
            if f"deploy@{bastion_public_ip}" not in ssh_args:
                fail(f"{host} ProxyCommand should target deploy@{bastion_public_ip}")
            if "-i " not in ssh_args or "IdentitiesOnly=yes" not in ssh_args:
                fail(f"{host} ProxyCommand should pass the deploy identity file explicitly")
            route = f"via cloud-main ({bastion_public_ip})"

        rows.append((host, ansible_host, private_ip, public_ip, route))

    print("Cloud inventory validation ok")
    print()
    print(f"{'host':<12} {'ansible_host':<15} {'private_ip':<15} {'public_ipv4':<15} route")
    for host, ansible_host, private_ip, public_ip, route in rows:
        print(f"{host:<12} {ansible_host:<15} {private_ip:<15} {public_ip:<15} {route}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
