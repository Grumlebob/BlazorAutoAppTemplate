#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
CLOUD_LIB = REPO_ROOT / "Deployment/Cloud/Scripts/Component/lib"
sys.path.insert(0, str(CLOUD_LIB))

from cloud_settings import load_settings  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"inventory render failed: {message}")


def validate_ip(name: str, value: str, required: bool = True) -> str:
    trimmed = value.strip()
    if not trimmed:
        if required:
            fail(f"{name} is required")
        return ""
    try:
        ipaddress.ip_address(trimmed)
    except ValueError as exc:
        fail(f"{name} must be an IP address: {exc}")
    return trimmed


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_inventory(args: argparse.Namespace) -> str:
    settings = load_settings(REPO_ROOT / "Deployment/Cloud/inventory/prod/group_vars/all.yml")

    bastion_public_ip = validate_ip("bastion public IP", args.bastion_public_ip)
    app1_public_ip = validate_ip("cloud-app1 public IP", args.app1_public_ip, required=False)
    app2_public_ip = validate_ip("cloud-app2 public IP", args.app2_public_ip, required=False)
    db_public_ip = validate_ip("cloud-db public IP", args.db_public_ip, required=False)

    main_private = validate_ip("cloud-main private IP", settings["cloud_main_private_ip"])
    app1_private = validate_ip("cloud-app1 private IP", settings["cloud_app1_private_ip"])
    app2_private = validate_ip("cloud-app2 private IP", settings["cloud_app2_private_ip"])
    db_private = validate_ip("cloud-db private IP", settings["cloud_db_private_ip"])

    ssh_key_path = args.ssh_private_key_path.strip() or "~/.ssh/bookscloud_deploy"
    known_hosts_path = args.known_hosts_path.strip() or "~/.ssh/known_hosts"
    proxy_command = (
        '-o ProxyCommand="'
        f"ssh -W %h:%p -i {ssh_key_path} "
        "-o IdentitiesOnly=yes "
        "-o StrictHostKeyChecking=accept-new "
        f"-o UserKnownHostsFile={known_hosts_path} "
        f'deploy@{bastion_public_ip}" '
        "-o IdentitiesOnly=yes "
        "-o StrictHostKeyChecking=accept-new "
        f"-o UserKnownHostsFile={known_hosts_path}"
    )

    optional_app1_public = f"\n              cloud_public_ipv4: {app1_public_ip}" if app1_public_ip else ""
    optional_app2_public = f"\n              cloud_public_ipv4: {app2_public_ip}" if app2_public_ip else ""
    optional_db_public = f"\n              cloud_public_ipv4: {db_public_ip}" if db_public_ip else ""

    return f"""all:
  vars:
    ansible_user: deploy
    ansible_ssh_private_key_file: {yaml_quote(ssh_key_path)}
    ansible_python_interpreter: /usr/bin/python3
  children:
    cloud:
      children:
        load_balancer:
          vars:
            ansible_ssh_common_args: "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={known_hosts_path}"
          hosts:
            cloud-main:
              ansible_host: {bastion_public_ip}
              cloud_private_ip: {main_private}
              cloud_public_ipv4: {bastion_public_ip}
        app_servers:
          vars:
            ansible_ssh_common_args: {yaml_quote(proxy_command)}
          hosts:
            cloud-app1:
              ansible_host: {app1_private}
              cloud_private_ip: {app1_private}{optional_app1_public}
            cloud-app2:
              ansible_host: {app2_private}
              cloud_private_ip: {app2_private}{optional_app2_public}
        node_db:
          vars:
            ansible_ssh_common_args: {yaml_quote(proxy_command)}
          hosts:
            cloud-db:
              ansible_host: {db_private}
              cloud_private_ip: {db_private}{optional_db_public}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Cloud Ansible inventory.")
    parser.add_argument("--bastion-public-ip", required=True)
    parser.add_argument("--app1-public-ip", default="")
    parser.add_argument("--app2-public-ip", default="")
    parser.add_argument("--db-public-ip", default="")
    parser.add_argument("--ssh-private-key-path", default="~/.ssh/bookscloud_deploy")
    parser.add_argument("--known-hosts-path", default="~/.ssh/known_hosts")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "Deployment/Cloud/inventory/prod/hosts.yml"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_inventory(args), encoding="utf-8")
    try:
        rendered_path = output.relative_to(REPO_ROOT)
    except ValueError:
        rendered_path = output
    print(f"rendered {rendered_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
