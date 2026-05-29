#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_settings import default_release_path, default_root, load_release_settings, read_simple_yaml


LOCALCLUSTER_COMPAT_KEYS = [
    "app_image",
    "migration_bundle_name",
]


def main() -> int:
    root = default_root()
    parser = argparse.ArgumentParser(description="Validate shared deployment release settings.")
    parser.add_argument(
        "--settings",
        default=str(default_release_path(root)),
        help="Path to Deployment/Common/release.yml.",
    )
    parser.add_argument(
        "--localcluster-settings",
        default=str(root / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml"),
        help="Optional LocalCluster group_vars/all.yml compatibility file.",
    )
    args = parser.parse_args()

    settings_path = Path(args.settings)
    if not settings_path.is_absolute():
        settings_path = root / settings_path

    localcluster_path = Path(args.localcluster_settings)
    if not localcluster_path.is_absolute():
        localcluster_path = root / localcluster_path

    try:
        release = load_release_settings(settings_path, validate_file=True)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    errors: list[str] = []
    if localcluster_path.exists():
        localcluster_values, parse_errors = read_simple_yaml(localcluster_path)
        errors.extend(parse_errors)
        for key in LOCALCLUSTER_COMPAT_KEYS:
            localcluster_value = localcluster_values.get(key)
            if localcluster_value is not None and localcluster_value != release[key]:
                errors.append(
                    f"{localcluster_path}: {key}={localcluster_value!r} does not match "
                    f"{settings_path}: {key}={release[key]!r}"
                )

    if errors:
        joined = "\n".join(f" - {error}" for error in errors)
        print(f"common release validation failed:\n{joined}", file=sys.stderr)
        return 1

    print(f"common release settings ok: {settings_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
