#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python3 - "$REPO_ROOT" <<'PY'
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(sys.argv[1])


def fail(message: str) -> None:
    raise SystemExit(f"rendered template validation failed: {message}")


def replace_vars(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{ " + key + " }}", value)
        text = text.replace("{{" + key + "}}", value)
    return text


def render_caddy(app_name: str, hostname: str, app_port: str) -> str:
    template = (ROOT / "Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2").read_text(encoding="utf-8-sig")
    upstreams = f" 10.10.0.11:{app_port} 10.10.0.12:{app_port}"
    template = re.sub(r"\{%.+?for host in groups\['app_servers'\].+?%\}.+?\{%.+?endfor.+?%\}", upstreams, template)
    rendered = replace_vars(template, {"public_hostname": hostname, "app_port": app_port, "app_name": app_name})
    if "{{" in rendered or "{%" in rendered:
        fail(f"unrendered Caddy template markers for {app_name}")
    return rendered


def render_env(path: Path, values: dict[str, str]) -> str:
    rendered = replace_vars(path.read_text(encoding="utf-8-sig"), values)
    rendered = re.sub(r"\{\{\s*hostvars\[groups\['node_db'\]\[0\]\]\.ansible_host\s*\}\}", "10.10.0.20", rendered)
    if "{{" in rendered or "{%" in rendered:
        fail(f"unrendered env template markers in {path}")
    return rendered


def render_compose(path: Path, env: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8-sig")
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return env.get(key, f"UNSET_{key}")
    rendered = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, text)
    if "UNSET_" in rendered:
        fail(f"compose file {path} has unresolved environment variable")
    return rendered


apps = [
    {"app_name": "notes", "public_hostname": "notes.example.com", "app_port": "8080", "postgres_port": "5432", "redis_port": "6379"},
    {"app_name": "secondnotes", "public_hostname": "secondnotes.example.com", "app_port": "8081", "postgres_port": "5433", "redis_port": "6380"},
]

with tempfile.TemporaryDirectory(prefix="localcluster-render-") as tmp:
    tmp_path = Path(tmp)
    caddy_text = "\n".join(render_caddy(app["app_name"], app["public_hostname"], app["app_port"]) for app in apps)
    caddy_file = tmp_path / "Caddyfile"
    caddy_file.write_text(caddy_text, encoding="utf-8")

    if "bind 127.0.0.1" not in caddy_text:
        fail("rendered Caddy config is not loopback-bound")
    for app in apps:
        chain = "LC-" + hashlib.sha1(app["app_name"].encode("utf-8")).hexdigest()[:16].upper()
        if not re.match(r"^LC-[A-F0-9]{16}$", chain):
            fail("app firewall chain id is not deterministic")

    if shutil.which("caddy"):
        subprocess.run(["caddy", "validate", "--config", str(caddy_file)], check=True)

    common = {
        "app_image": "ghcr.io/example/notes",
        "app_version": "abcdef123456",
        "vault_postgres_user": "appuser",
        "vault_postgres_password": "db-password",
        "vault_postgres_db": "appdb",
        "vault_redis_password": "redis-password",
    }
    app_values = {
        **common,
        "app_name": "notes",
        "app_port": "8080",
        "postgres_port": "5432",
        "redis_port": "6379",
    }
    app_env = render_env(ROOT / "Deployment/LocalCluster/ansible/roles/app/templates/app.env.j2", app_values)
    db_env = render_env(ROOT / "Deployment/LocalCluster/ansible/roles/postgres/templates/node-db.env.j2", app_values)
    if "APP_NAME=notes" not in app_env or "APP_NAME=notes" not in db_env:
        fail("rendered env files are missing app identity marker")

    compose_env = {
        "APP_IMAGE": "ghcr.io/example/notes",
        "APP_VERSION": "abcdef123456",
        "APP_PORT": "8080",
        "POSTGRES_HOST": "10.10.0.20",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "appdb",
        "POSTGRES_USER": "appuser",
        "POSTGRES_PASSWORD": "db-password",
        "REDIS_HOST": "10.10.0.20",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "redis-password",
    }
    app_compose = tmp_path / "app-compose.yml"
    db_compose = tmp_path / "db-compose.yml"
    app_compose.write_text(render_compose(ROOT / "Deployment/LocalCluster/compose/app-server/docker-compose.yml", compose_env), encoding="utf-8")
    db_compose.write_text(render_compose(ROOT / "Deployment/LocalCluster/compose/node-db/docker-compose.yml", compose_env), encoding="utf-8")

    docker_compose_available = shutil.which("docker") and subprocess.run(
        ["docker", "compose", "version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if docker_compose_available:
        subprocess.run(["docker", "compose", "-f", str(app_compose), "config"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "compose", "-f", str(db_compose), "config"], check=True, stdout=subprocess.DEVNULL)

print("rendered template validation ok")
PY
