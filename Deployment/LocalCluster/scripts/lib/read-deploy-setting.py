#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deploy_settings import default_root, load_settings


def main() -> int:
    root = default_root()
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
        settings = load_settings(settings_path, validate_file=True)
        print(settings[args.key])
    except (KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
