#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def read_simple_yaml_value(path: Path, key: str) -> str:
    prefix = f"{key}:"
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or not line.startswith(prefix):
            continue
        value = line[len(prefix):].strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if not value:
            raise ValueError(f"{path}: {key} is empty")
        return value
    raise KeyError(f"{path}: missing {key}")


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Print one deployment setting from group_vars/all.yml.")
    parser.add_argument("key")
    parser.add_argument(
        "--settings",
        default=str(root / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml"),
        help="Path to the simple Ansible group vars file.",
    )
    args = parser.parse_args()

    settings_path = Path(args.settings)
    if not settings_path.is_absolute():
        settings_path = root / settings_path

    try:
        print(read_simple_yaml_value(settings_path, args.key))
    except (KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
