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

try:
    from jinja2 import Environment, StrictUndefined
except ImportError as exc:  # pragma: no cover - exercised in CI if dependency is missing
    raise SystemExit("rendered template validation failed: python package jinja2 is required") from exc


ROOT = Path(sys.argv[1])
JINJA = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


def ansible_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


JINJA.filters["bool"] = ansible_bool


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
    rendered = re.sub(r"\{\{\s*hostvars\[groups\['load_balancer'\]\[0\]\]\.ansible_host\s*\}\}", "10.10.0.10", rendered)
    rendered = re.sub(r"\{\{\s*hostvars\[inventory_hostname\]\.ansible_host\s*\}\}", "10.10.0.20", rendered)
    rendered = re.sub(r"\{\{\s*inventory_hostname\s*\}\}", values["inventory_hostname"], rendered)
    rendered = re.sub(r"\{\{\s*\(observability_enabled\s*\|\s*default\(false\)\s*\|\s*bool\)\s*\|\s*lower\s*\}\}", values["observability_enabled"], rendered)
    rendered = re.sub(r"\{\{\s*observability_trace_sample_ratio\s*\|\s*default\('0\.25'\)\s*\}\}", values["observability_trace_sample_ratio"], rendered)
    rendered = re.sub(r"\{\{\s*observability_postgres_exporter_port\s*\|\s*default\(9187\)\s*\}\}", values["observability_postgres_exporter_port"], rendered)
    rendered = re.sub(r"\{\{\s*observability_redis_exporter_port\s*\|\s*default\(9121\)\s*\}\}", values["observability_redis_exporter_port"], rendered)
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


def render_jinja(path: Path, context: dict[str, object]) -> str:
    template = JINJA.from_string(path.read_text(encoding="utf-8-sig"))
    rendered = template.render(**context)
    if "{{" in rendered or "{%" in rendered:
        fail(f"unrendered template markers in {path}")
    return rendered


def command_available(command: str) -> bool:
    return shutil.which(command) is not None


def command_succeeds(command: list[str]) -> bool:
    return subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def check_prometheus_config(config_path: Path) -> None:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        pass
    else:
        try:
            yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"rendered Prometheus config is not valid YAML: {exc}")

    if command_available("promtool"):
        subprocess.run(
            ["promtool", "check", "config", str(config_path)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return

    if docker_available:
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--entrypoint",
                "promtool",
                "-v",
                f"{config_path.parent}:/etc/prometheus:ro",
                "prom/prometheus:v3.4.1",
                "check",
                "config",
                "/etc/prometheus/prometheus.yml",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )


docker_available = command_available("docker") and command_succeeds(["docker", "version"])

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
        "inventory_hostname": "node-app1",
        "vault_postgres_user": "appuser",
        "vault_postgres_password": "db-password",
        "vault_postgres_db": "appdb",
        "vault_redis_password": "redis-password",
        "observability_enabled": "true",
        "observability_docker_network": "notes_observability",
        "observability_trace_sample_ratio": "0.25",
        "observability_postgres_exporter_port": "9187",
        "observability_redis_exporter_port": "9121",
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
    if "APP_NODE_NAME=node-app1" not in app_env:
        fail("rendered app env is missing stable app node name")
    if "COMPOSE_PROJECT_NAME=notes" not in app_env or "COMPOSE_PROJECT_NAME=notes" not in db_env:
        fail("rendered env files are missing explicit Compose project names")

    compose_env = {
        "APP_IMAGE": "ghcr.io/example/notes",
        "APP_VERSION": "abcdef123456",
        "APP_NODE_NAME": "node-app1",
        "APP_NAME": "notes",
        "APP_PORT": "8080",
        "FORWARDED_HEADERS_KNOWN_PROXY": "10.10.0.10",
        "POSTGRES_HOST": "10.10.0.20",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "appdb",
        "POSTGRES_USER": "appuser",
        "POSTGRES_PASSWORD": "db-password",
        "REDIS_HOST": "10.10.0.20",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "redis-password",
        "OBSERVABILITY_ENABLED": "true",
        "OBSERVABILITY_OTLP_ENDPOINT": "http://alloy:4317",
        "OBSERVABILITY_OTLP_PROTOCOL": "Grpc",
        "OBSERVABILITY_TRACE_SAMPLE_RATIO": "0.25",
        "OBSERVABILITY_DEPLOYMENT_TARGET": "localcluster",
        "OBSERVABILITY_DOCKER_NETWORK": "notes_observability",
        "NODE_HOST": "10.10.0.20",
        "OBSERVABILITY_POSTGRES_EXPORTER_PORT": "9187",
        "OBSERVABILITY_REDIS_EXPORTER_PORT": "9121",
    }
    app_compose = tmp_path / "app-compose.yml"
    db_compose = tmp_path / "db-compose.yml"
    app_compose.write_text(render_compose(ROOT / "Deployment/LocalCluster/compose/app-server/docker-compose.yml", compose_env), encoding="utf-8")
    if "hostname: node-app1" not in app_compose.read_text(encoding="utf-8"):
        fail("rendered app compose is missing stable container hostname")
    db_compose_text = render_compose(ROOT / "Deployment/LocalCluster/compose/node-db/docker-compose.yml", compose_env)
    db_compose.write_text(db_compose_text, encoding="utf-8")
    for required in [
        "postgres:18.4-alpine3.23",
        "postgres_data:/var/lib/postgresql",
        "redis:8.8.0-alpine3.23",
        "prometheuscommunity/postgres-exporter:v0.17.1",
        "oliver006/redis_exporter:v1.73.0",
    ]:
        if required not in db_compose_text:
            fail(f"rendered node-db compose is missing {required}")

    docker_compose_available = docker_available and command_succeeds(["docker", "compose", "version"])
    if docker_compose_available:
        subprocess.run(["docker", "compose", "-f", str(app_compose), "config"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "compose", "-f", str(db_compose), "config"], check=True, stdout=subprocess.DEVNULL)

    groups = {
        "all": ["node-main", "node-app1", "node-app2", "node-db"],
        "load_balancer": ["node-main"],
        "app_servers": ["node-app1", "node-app2"],
        "node_db": ["node-db"],
    }
    hostvars = {
        "node-main": {"ansible_host": "10.10.0.10"},
        "node-app1": {"ansible_host": "10.10.0.11"},
        "node-app2": {"ansible_host": "10.10.0.12"},
        "node-db": {"ansible_host": "10.10.0.20"},
    }
    observability_context = {
        "app_name": "notes",
        "groups": groups,
        "hostvars": hostvars,
        "observability_docker_network": "notes_observability",
        "observability_grafana_port": "3000",
        "observability_prometheus_port": "9090",
        "observability_loki_port": "3100",
        "observability_tempo_http_port": "3200",
        "observability_tempo_otlp_grpc_port": "4317",
        "observability_tempo_otlp_http_port": "4318",
        "observability_alloy_http_port": "12345",
        "observability_node_exporter_port": "9100",
        "observability_postgres_exporter_port": "9187",
        "observability_redis_exporter_port": "9121",
        "observability_prometheus_retention_time": "7d",
        "observability_prometheus_retention_size": "6GB",
        "observability_loki_retention_period": "7d",
        "observability_tempo_retention_period": "24h",
    }
    backend_context = {**observability_context, "inventory_hostname": "node-main"}
    agent_context = {**observability_context, "inventory_hostname": "node-app1"}
    node_main_agent_context = {**observability_context, "inventory_hostname": "node-main"}

    backend_root = tmp_path / "observability-backend"
    agent_root = tmp_path / "observability-agent"
    for path in [
        backend_root / "prometheus" / "rules",
        backend_root / "loki",
        backend_root / "tempo",
        backend_root / "grafana" / "provisioning",
        backend_root / "grafana" / "dashboards",
        agent_root,
    ]:
        path.mkdir(parents=True, exist_ok=True)

    backend_template_root = ROOT / "Deployment/LocalCluster/ansible/roles/observability_backend/templates"
    agent_template_root = ROOT / "Deployment/LocalCluster/ansible/roles/observability_agent/templates"
    for rule_file in (ROOT / "Deployment/Common/observability/prometheus/rules").glob("*.yml"):
        shutil.copy2(rule_file, backend_root / "prometheus" / "rules" / rule_file.name)
    (backend_root / ".env").write_text(render_jinja(backend_template_root / "backend.env.j2", backend_context), encoding="utf-8")
    (backend_root / "docker-compose.yml").write_text(render_jinja(backend_template_root / "docker-compose.yml.j2", backend_context), encoding="utf-8")
    prometheus_config = backend_root / "prometheus" / "prometheus.yml"
    prometheus_config.write_text(render_jinja(backend_template_root / "prometheus.yml.j2", backend_context), encoding="utf-8")
    check_prometheus_config(prometheus_config)
    (backend_root / "loki" / "loki.yml").write_text(render_jinja(backend_template_root / "loki.yml.j2", backend_context), encoding="utf-8")
    (backend_root / "tempo" / "tempo.yml").write_text(render_jinja(backend_template_root / "tempo.yml.j2", backend_context), encoding="utf-8")
    (agent_root / ".env").write_text(render_jinja(agent_template_root / "agent.env.j2", agent_context), encoding="utf-8")
    (agent_root / "docker-compose.yml").write_text(render_jinja(agent_template_root / "docker-compose.yml.j2", agent_context), encoding="utf-8")
    app_agent_config = render_jinja(agent_template_root / "config.alloy.j2", agent_context)
    main_agent_config = render_jinja(agent_template_root / "config.alloy.j2", node_main_agent_context)
    if "http://10.10.0.10:9090/api/v1/write" not in app_agent_config:
        fail("app-node Alloy config does not forward metrics to node-main Prometheus")
    if "http://prometheus:9090/api/v1/write" not in main_agent_config:
        fail("node-main Alloy config does not use the local backend network")

    firewall_template = ROOT / "Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2"
    for host in groups["all"]:
        firewall_context = {
            **observability_context,
            "inventory_hostname": host,
            "observability_enabled": True,
            "app_port": "8080",
            "postgres_port": "5432",
            "redis_port": "6379",
        }
        rendered_firewall = render_jinja(firewall_template, firewall_context)
        expected_origin_dst = f"--ctorigdst {hostvars[host]['ansible_host']}"
        if expected_origin_dst not in rendered_firewall:
            fail(f"rendered Docker published-port firewall for {host} is not scoped to its local node IP")
        firewall_script = tmp_path / f"{host}-docker-user-firewall.sh"
        firewall_script.write_text(rendered_firewall, encoding="utf-8")
        if command_available("bash"):
            subprocess.run(["bash", "-n", str(firewall_script)], check=True)

    if docker_compose_available:
        subprocess.run(["docker", "compose", "-f", str(backend_root / "docker-compose.yml"), "config"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "compose", "-f", str(agent_root / "docker-compose.yml"), "config"], check=True, stdout=subprocess.DEVNULL)

print("rendered template validation ok")
PY
