#!/usr/bin/env python3
from __future__ import annotations

import re
import sys


REQUIRED_KEYS = [
    "vault_postgres_user",
    "vault_postgres_password",
    "vault_postgres_db",
    "vault_redis_password",
    "vault_ghcr_username",
    "vault_ghcr_token",
    "vault_cloudflare_tunnel_token",
]

DOTENV_SAFE_PASSWORD = re.compile(r"^[A-Za-z0-9._@%+-]{16,128}$")


def parse_simple_yaml(text: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    errors: list[str] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", raw_line)
        if not match:
            errors.append(f"line {line_number}: unsupported vault line: {raw_line}")
            continue

        key, value = match.groups()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        if key in values:
            errors.append(f"duplicate key: {key}")
            continue
        values[key] = value.strip()

    return values, errors


def validate(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    allowed = set(REQUIRED_KEYS)

    for key in REQUIRED_KEYS:
        if key not in values:
            errors.append(f"vault.yml is missing required key: {key}")
        elif not values[key]:
            errors.append(f"vault.yml has empty value for: {key}")

    for key in values:
        if key not in allowed:
            errors.append(f"vault.yml has unknown key: {key}")

    postgres_user = values.get("vault_postgres_user", "")
    if postgres_user and not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$", postgres_user):
        errors.append("vault_postgres_user must contain only letters, numbers, and underscores, and must not start with a number")

    postgres_db = values.get("vault_postgres_db", "")
    if postgres_db and not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$", postgres_db):
        errors.append("vault_postgres_db must contain only letters, numbers, and underscores, and must not start with a number")

    for key in ["vault_postgres_password", "vault_redis_password"]:
        value = values.get(key, "")
        if value and not DOTENV_SAFE_PASSWORD.match(value):
            errors.append(
                f"{key} must be 16-128 characters using only letters, numbers, dot, underscore, at, percent, plus, or hyphen"
            )

    ghcr_username = values.get("vault_ghcr_username", "")
    if ghcr_username and not re.match(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$", ghcr_username):
        errors.append("vault_ghcr_username must look like a GitHub username")

    ghcr_token = values.get("vault_ghcr_token", "")
    if ghcr_token and not re.match(r"^[A-Za-z0-9_]{20,255}$", ghcr_token):
        errors.append("vault_ghcr_token must look like a GitHub package token and must not contain shell metacharacters")

    tunnel_token = values.get("vault_cloudflare_tunnel_token", "")
    if tunnel_token and not re.match(r"^eyJ[A-Za-z0-9_.-]{100,5000}$", tunnel_token):
        errors.append("vault_cloudflare_tunnel_token must look like the long eyJ... Cloudflare tunnel token")

    return errors


def main() -> int:
    values, parse_errors = parse_simple_yaml(sys.stdin.read())
    errors = parse_errors + validate(values)
    if errors:
        print("vault validation failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
