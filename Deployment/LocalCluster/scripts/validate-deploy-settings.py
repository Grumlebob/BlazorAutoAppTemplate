#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deploy_settings import load_settings


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Validate Deployment/LocalCluster inventory group_vars/all.yml.")
    parser.add_argument(
        "--settings",
        default=str(root / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml"),
        help="Path to the deployment settings file.",
    )
    args = parser.parse_args()

    settings_path = Path(args.settings)
    if not settings_path.is_absolute():
        settings_path = root / settings_path

    if not settings_path.exists():
        print(f"deployment settings validation failed: missing {settings_path}", file=sys.stderr)
        return 1

    try:
        load_settings(settings_path, validate_file=True)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    print("OK    deployment settings are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
