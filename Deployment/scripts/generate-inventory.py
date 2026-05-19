#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_NODES = ["node-main", "node-app1", "node-app2", "node-db"]


def parse_simple_machines_yaml(path: Path) -> dict[str, dict[str, str]]:
    nodes: dict[str, dict[str, str]] = {}
    current: str | None = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip() == "nodes:":
            continue

        node_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if node_match:
            current = node_match.group(1)
            nodes[current] = {}
            continue

        value_match = re.match(r"^    ([A-Za-z0-9_]+):\s*(.+?)\s*$", line)
        if value_match and current:
            key, value = value_match.groups()
            nodes[current][key] = value.strip().strip('"').strip("'")
            continue

        raise ValueError(f"{path}:{line_number}: unsupported line: {raw_line}")

    return nodes


def validate(nodes: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for node in REQUIRED_NODES:
        if node not in nodes:
            errors.append(f"missing node: {node}")
            continue
        for key in ["ip", "mac", "install_user"]:
            value = nodes[node].get(key, "")
            if not value:
                errors.append(f"{node}: missing {key}")
            elif value.startswith("REPLACE_WITH"):
                errors.append(f"{node}: replace placeholder {key}")
        ip = nodes[node].get("ip", "")
        if ip and not ip.startswith("REPLACE_WITH") and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
            errors.append(f"{node}: invalid IPv4 address: {ip}")
        mac = nodes[node].get("mac", "")
        if mac and not mac.startswith("REPLACE_WITH") and not re.match(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$", mac):
            errors.append(f"{node}: invalid MAC address: {mac}")
    return errors


def render_hosts(nodes: dict[str, dict[str, str]]) -> str:
    return f"""all:
  vars:
    ansible_user: deploy
    ansible_ssh_private_key_file: ~/.ssh/ship_deploy

  children:
    load_balancer:
      hosts:
        node-main:
          ansible_host: {nodes["node-main"]["ip"]}

    app_servers:
      hosts:
        node-app1:
          ansible_host: {nodes["node-app1"]["ip"]}
        node-app2:
          ansible_host: {nodes["node-app2"]["ip"]}

    node_db:
      hosts:
        node-db:
          ansible_host: {nodes["node-db"]["ip"]}
"""


def render_bootstrap_hosts(nodes: dict[str, dict[str, str]]) -> str:
    return f"""all:
  children:
    load_balancer:
      hosts:
        node-main:
          ansible_host: {nodes["node-main"]["ip"]}
          ansible_user: {nodes["node-main"]["install_user"]}

    app_servers:
      hosts:
        node-app1:
          ansible_host: {nodes["node-app1"]["ip"]}
          ansible_user: {nodes["node-app1"]["install_user"]}
        node-app2:
          ansible_host: {nodes["node-app2"]["ip"]}
          ansible_user: {nodes["node-app2"]["install_user"]}

    node_db:
      hosts:
        node-db:
          ansible_host: {nodes["node-db"]["ip"]}
          ansible_user: {nodes["node-db"]["install_user"]}
"""


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Generate Ansible production inventory from Deployment/machines.yml.")
    parser.add_argument("--machines", default=str(root / "Deployment/machines.yml"))
    parser.add_argument("--output", default=str(root / "Deployment/inventory/prod/hosts.yml"))
    parser.add_argument("--bootstrap-output", default=str(root / "Deployment/inventory/prod/bootstrap-hosts.yml"))
    args = parser.parse_args()

    machines_path = Path(args.machines)
    if not machines_path.is_absolute():
        machines_path = root / machines_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = root / output_path
    bootstrap_output_path = Path(args.bootstrap_output)
    if not bootstrap_output_path.is_absolute():
        bootstrap_output_path = root / bootstrap_output_path

    if not machines_path.exists():
        print(f"missing {machines_path}", file=sys.stderr)
        print("copy Deployment/machines.example.yml to Deployment/machines.yml and fill real values", file=sys.stderr)
        return 1

    try:
        nodes = parse_simple_machines_yaml(machines_path)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    errors = validate(nodes)
    if errors:
        for error in errors:
            print(f"invalid machines file: {error}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_hosts(nodes), encoding="utf-8")
    bootstrap_output_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_output_path.write_text(render_bootstrap_hosts(nodes), encoding="utf-8")
    print(f"generated {output_path.relative_to(root)} from {machines_path.relative_to(root)}")
    print(f"generated {bootstrap_output_path.relative_to(root)} from {machines_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
