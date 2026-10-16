#!/usr/bin/env python3
"""Add a newly generated Data Protection key to a decrypted Ansible vault."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

FIELDS = (
    "vault_data_protection_certificate_base64",
    "vault_data_protection_certificate_password",
)


def read_values(path: Path) -> tuple[str, dict[str, str | None]]:
    content = path.read_text(encoding="utf-8")
    values: dict[str, str | None] = {key: None for key in FIELDS}
    for line in content.splitlines():
        match = re.fullmatch(r"([a-z0-9_]+):\s*(.*?)\s*", line)
        if match and match.group(1) in values:
            key, value = match.groups()
            if values[key] is not None:
                raise ValueError("duplicate Data Protection vault entry")
            values[key] = value.strip().strip("\"'")
    return content, values


def inspect(path: Path) -> int:
    _, values = read_values(path)
    items = list(values.values())
    if all(value and not value.startswith("REPLACE_WITH") for value in items):
        print("keep")
        return 0
    if all(value is None or not value or value.startswith("REPLACE_WITH") for value in items):
        print("generate")
        return 0
    raise ValueError("partial Data Protection vault entries")


def update(path: Path, certificate_path: Path, password_path: Path) -> None:
    content, previous = read_values(path)
    items = list(previous.values())
    if not all(value is None or not value or value.startswith("REPLACE_WITH") for value in items):
        raise ValueError("existing Data Protection vault values cannot be replaced")
    values = {
        FIELDS[0]: certificate_path.read_text(encoding="ascii").strip(),
        FIELDS[1]: password_path.read_text(encoding="ascii").strip(),
    }
    if not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", values[FIELDS[0]]) or not re.fullmatch(r"[A-Fa-f0-9]{64}", values[FIELDS[1]]):
        raise ValueError("generated Data Protection vault values are invalid")
    for key, value in values.items():
        pattern = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
        line = f"{key}: {value}"
        content = pattern.sub(lambda _: line, content) if pattern.search(content) else content.rstrip() + "\n" + line + "\n"
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("content", type=Path)
    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("content", type=Path)
    update_parser.add_argument("certificate", type=Path)
    update_parser.add_argument("password", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "inspect":
            return inspect(args.content)
        update(args.content, args.certificate, args.password)
        return 0
    except (OSError, ValueError):
        print("Data Protection vault entries are partial or invalid.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
