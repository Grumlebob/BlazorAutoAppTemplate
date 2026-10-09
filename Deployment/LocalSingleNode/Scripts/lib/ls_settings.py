"""Validated, dependency-free settings for native single-node deployment."""
from __future__ import annotations

import ast
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "Deployment/LocalSingleNode"
ETC = Path(os.environ.get("LOCALSINGLENODE_ETC", "/etc"))


def command(*args: str, timeout: int = 30) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError(f"{Path(args[0]).name} failed (exit {result.returncode})")
    return result.stdout.strip()


def scalar(value: str):
    value = value.strip()
    if value.startswith(("'", '"')):
        return ast.literal_eval(value)
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"[0-9]+", value):
        return int(value)
    if value.startswith("[") and value.endswith("]"):
        return [scalar(item) for item in value[1:-1].split(",") if item.strip()]
    return value


def read_yaml(path: Path, node: bool = False) -> dict:
    """Accept documented scalar/list settings; reject ambiguous YAML constructs."""
    values = {}
    header = not node
    list_key = None
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        # Facts and settings cannot contain '#' in their validated values.
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or line == "---":
            continue
        if node and line == "node:" and not header:
            header = True
            continue
        pattern = r"^  ([a-z_][a-z0-9_]*):\s*(.*?)\s*$" if node else r"^([a-z_][a-z0-9_]*):\s*(.*?)\s*$"
        match = re.fullmatch(pattern, line)
        if match and header:
            key, value = match.groups()
            if key in values:
                raise ValueError(f"{path.name}:{number}: duplicate key {key}")
            list_key = key if not value else None
            values[key] = [] if list_key else scalar(value)
        elif not node and list_key and re.fullmatch(r"  - .+", line):
            values[list_key].append(scalar(line[4:]))
        else:
            raise ValueError(f"{path.name}:{number}: unsupported YAML structure")
    if not header:
        raise ValueError(f"{path.name}: missing node mapping")
    return values


def settings(path: Path | None = None) -> dict:
    values = read_yaml(path or TARGET / "inventory/group_vars/all.yml")
    required = {"app_name", "app_port", "postgres_port", "redis_port", "deploy_root", "docker_subnet",
                "lan_http_port", "lan_hostnames", "backup_root", "backup_keep_days", "observability_enabled"}
    if set(values) != required:
        raise ValueError("single-node settings have missing or unknown keys")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", str(values["app_name"])):
        raise ValueError("app_name must be a lowercase app slug")
    ports = [values[key] for key in ("app_port", "postgres_port", "redis_port", "lan_http_port")]
    if any(type(port) is not int or not 1 <= port <= 65535 for port in ports) or len(set(ports)) != 4:
        raise ValueError("service ports must be distinct integers from 1 through 65535")
    for key in ("deploy_root", "backup_root"):
        value = str(values[key])
        if not re.fullmatch(r"/opt/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", value):
            raise ValueError(f"{key} must name a directory below /opt")
    if values["deploy_root"] == values["backup_root"]:
        raise ValueError("backup_root must differ from deploy_root")
    network = ipaddress.ip_network(str(values["docker_subnet"]), strict=True)
    if network.version != 4 or not network.is_private or network.is_loopback:
        raise ValueError("docker_subnet must be a private IPv4 network")
    names = values["lan_hostnames"]
    if not isinstance(names, list) or any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}", str(name)) for name in names):
        raise ValueError("lan_hostnames must be a list of DNS names")
    if type(values["backup_keep_days"]) is not int or values["backup_keep_days"] < 1:
        raise ValueError("backup_keep_days must be a positive integer")
    if values["observability_enabled"] is not False:
        raise ValueError("single-node observability must be disabled")
    return values


def print_setting(key: str) -> None:
    values = settings()
    if key not in values:
        raise ValueError(f"unknown single-node setting: {key}")
    value = values[key]
    print(json.dumps(value) if isinstance(value, (list, bool)) else value)
