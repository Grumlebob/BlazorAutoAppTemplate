#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_settings import default_release_path, default_root, load_release_settings


def main() -> int:
    root = default_root()
    parser = argparse.ArgumentParser(description="Print one shared deployment release setting.")
    parser.add_argument("key")
    parser.add_argument(
        "--settings",
        default=str(default_release_path(root)),
        help="Path to Deployment/Common/release.yml.",
    )
    args = parser.parse_args()

    settings_path = Path(args.settings)
    if not settings_path.is_absolute():
        settings_path = root / settings_path

    try:
        settings = load_release_settings(settings_path, validate_file=True)
        print(settings[args.key])
    except (KeyError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
