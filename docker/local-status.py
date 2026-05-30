#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
CERT_PATH = ROOT / "docker" / "https" / "aspnetapp.pfx"
GLOBAL_JSON_PATH = ROOT / "global.json"

REQUIRED_KEYS = [
    "App__Url",
    "App__Name",
    "APP_HTTPS_HOST_PORT",
    "POSTGRES_HOST_PORT",
    "REDIS_HOST_PORT",
    "REDIS_INSIGHT_HOST_PORT",
    "GRAFANA_HOST_PORT",
    "ALERTMANAGER_HOST_PORT",
    "PROMETHEUS_HOST_PORT",
    "LOKI_HOST_PORT",
    "TEMPO_HOST_PORT",
    "ALLOY_HOST_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "Database__Host",
    "Database__Port",
    "Database__Name",
    "Database__Username",
    "Database__Password",
    "Redis__Configuration",
    "Observability__OpenTelemetry__Enabled",
    "Observability__OpenTelemetry__Endpoint",
    "Observability__OpenTelemetry__Protocol",
    "Observability__OpenTelemetry__TraceSampleRatio",
    "OBSERVABILITY_ENABLED",
    "OBSERVABILITY_OTLP_ENDPOINT",
    "OBSERVABILITY_OTLP_PROTOCOL",
    "OBSERVABILITY_TRACE_SAMPLE_RATIO",
]

PORTS = [
    ("app HTTPS", "APP_HTTPS_HOST_PORT", 7186),
    ("app HTTP", None, 5025),
    ("PostgreSQL", "POSTGRES_HOST_PORT", 5432),
    ("Redis", "REDIS_HOST_PORT", 6379),
    ("Redis Insight", "REDIS_INSIGHT_HOST_PORT", 5540),
    ("Grafana", "GRAFANA_HOST_PORT", 3000),
    ("Alertmanager", "ALERTMANAGER_HOST_PORT", 9093),
    ("Prometheus", "PROMETHEUS_HOST_PORT", 9090),
    ("Loki", "LOKI_HOST_PORT", 3100),
    ("Tempo", "TEMPO_HOST_PORT", 3200),
    ("Alloy", "ALLOY_HOST_PORT", 12345),
]


failures: list[str] = []
warnings: list[str] = []


def ok(message: str) -> None:
    print(f"OK    {message}")


def warn(message: str) -> None:
    warnings.append(message)
    print(f"WARN  {message}")


def fail(message: str) -> None:
    failures.append(message)
    print(f"FAIL  {message}")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"{path.name}:{line_number}: expected KEY=value")
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_check(command: list[str], description: str) -> None:
    try:
        subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ok(description)
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail(description)


def check_command_version(command: str, args: list[str], description: str) -> None:
    executable = shutil.which(command)
    if executable is None:
        fail(f"{description} missing")
        return
    try:
        version = subprocess.run(
            [executable, *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip().splitlines()[0]
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        fail(f"{description} version check failed")
        return
    ok(f"{description} available: {version}")


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def configured_port(values: dict[str, str], key: str | None, default: int) -> int:
    if key is None:
        return default

    raw_value = values.get(key)
    if not raw_value:
        return default

    try:
        port = int(raw_value)
    except ValueError:
        fail(f".env has non-numeric {key}: {raw_value}")
        return default

    if not 0 < port < 65536:
        fail(f".env has out-of-range {key}: {raw_value}")
        return default

    return port


def check_ports(values: dict[str, str]) -> None:
    for label, key, default in PORTS:
        port = configured_port(values, key, default)
        if port_is_open(port):
            warn(f"{label} port {port} is already listening on 127.0.0.1")
        else:
            ok(f"{label} port {port} is free on 127.0.0.1")


def check_dotnet_sdk_version() -> None:
    if not GLOBAL_JSON_PATH.exists():
        warn("global.json missing; dotnet SDK version is not pinned")
        return

    try:
        required_version = json.loads(GLOBAL_JSON_PATH.read_text(encoding="utf-8"))["sdk"]["version"]
    except (json.JSONDecodeError, KeyError):
        fail("global.json does not contain sdk.version")
        return

    try:
        actual_version = subprocess.run(
            ["dotnet", "--version"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail("dotnet SDK version check failed")
        return

    required_major = required_version.split(".", 1)[0]
    actual_major = actual_version.split(".", 1)[0]
    if actual_major != required_major:
        fail(f"dotnet SDK major version is {actual_version}; expected {required_version} from global.json")
        return

    ok(f"dotnet SDK {actual_version} satisfies global.json {required_version}")


def check_node_version() -> None:
    executable = shutil.which("node")
    if executable is None:
        fail("Node.js missing")
        return

    try:
        version = subprocess.run(
            [executable, "--version"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip().splitlines()[0]
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        fail("Node.js version check failed")
        return

    major_text = version.removeprefix("v").split(".", 1)[0]
    try:
        major = int(major_text)
    except ValueError:
        warn(f"Node.js available but version could not be parsed: {version}")
        return

    if major < 20:
        fail(f"Node.js {version} is too old; use Node.js 20 or newer")
    elif major < 24:
        warn(f"Node.js available: {version}; CI uses Node.js 24 LTS")
    else:
        ok(f"Node.js available: {version}")


def main() -> int:
    print("local development status")
    print()

    if ENV_EXAMPLE_PATH.exists():
        ok(".env.example exists")
    else:
        fail(".env.example missing")

    values: dict[str, str] = {}

    if ENV_PATH.exists():
        ok(".env exists")
        values = parse_env(ENV_PATH)
        for key in REQUIRED_KEYS:
            value = values.get(key)
            if value is None:
                fail(f".env missing {key}")
            elif value.startswith("REPLACE_WITH") or value == "INJECT_THIS_IN_ORDER_TO_RUN":
                fail(f".env has placeholder value for {key}")
            elif value == "" and key not in {"Authentication__Google__ClientId", "Authentication__Google__ClientSecret"}:
                fail(f".env has empty required value for {key}")
    else:
        fail(".env missing; copy .env.example to .env")

    if CERT_PATH.exists():
        ok("HTTPS dev certificate exported")
    else:
        warn("HTTPS dev certificate missing; run pwsh -File ./docker/create-dev-cert.ps1")

    if command_exists("docker"):
        ok("docker command available")
        run_check(["docker", "compose", "config", "--quiet"], "docker compose config is valid")
    else:
        fail("docker command missing")

    if command_exists("dotnet"):
        ok("dotnet command available")
        check_dotnet_sdk_version()
    else:
        fail("dotnet command missing")

    check_node_version()
    check_command_version("npm", ["--version"], "npm")
    check_ports(values)

    if (ROOT / "Deployment" / "LocalCluster" / "HowToDeployLocalCluster.md").exists():
        ok("LocalCluster deployment guide exists")
    else:
        fail("LocalCluster deployment guide missing")

    print()
    if failures:
        print(f"local status failed with {len(failures)} blocking issue(s)")
        return 1
    if warnings:
        print(f"local status ok with {len(warnings)} warning(s)")
        return 0
    print("local status ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
