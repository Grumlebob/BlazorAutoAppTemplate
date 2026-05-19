#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
CERT_PATH = ROOT / "docker" / "https" / "aspnetapp.pfx"

REQUIRED_KEYS = [
    "App__Url",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "Database__Host",
    "Database__Port",
    "Database__Name",
    "Database__Username",
    "Database__Password",
    "Redis__Configuration",
    "Storage__HullImages__RootPath",
    "ACCEPT_EULA",
    "SEQ_FIRSTRUN_ADMINPASSWORD",
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


def main() -> int:
    print("local development status")
    print()

    if ENV_EXAMPLE_PATH.exists():
        ok(".env.example exists")
    else:
        fail(".env.example missing")

    if ENV_PATH.exists():
        ok(".env exists")
        values = parse_env(ENV_PATH)
        for key in REQUIRED_KEYS:
            value = values.get(key)
            if value is None:
                fail(f".env missing {key}")
            elif value.startswith("REPLACE_WITH") or value == "INJECT_THIS_IN_ORDER_TO_RUN":
                fail(f".env has placeholder value for {key}")
            elif value == "" and key not in {"SENDGRID_API_KEY", "SENDGRID_FROM_EMAIL", "Authentication__Google__ClientId", "Authentication__Google__ClientSecret"}:
                fail(f".env has empty required value for {key}")
        if values.get("ACCEPT_EULA") == "Y":
            ok("Seq EULA accepted for local container")
        else:
            fail("ACCEPT_EULA must be Y for local Seq")
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
    else:
        fail("dotnet command missing")

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
