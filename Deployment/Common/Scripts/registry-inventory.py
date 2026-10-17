#!/usr/bin/env python3
"""Inspect exact payload-store bytes without selecting or deleting anything."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent / "Component/lib"))
from registry_inventory import RegistryClient, collect_inventory  # noqa: E402
from registry_retention import RetentionError, inventory_usage  # noqa: E402


def main(argv=None, *, client_factory=RegistryClient) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--username", default=os.environ.get("GITHUB_ACTOR", ""))
    parser.add_argument("--package", action="append", required=True,
                        help="Exact configured payload image and expected visibility: ghcr.io/owner/app-release-payload=private")
    args = parser.parse_args(argv)
    try:
        packages = {}
        for value in args.package:
            if value.count("=") != 1:
                raise RetentionError("package requires an exact image and expected visibility")
            image, visibility = value.split("=", 1)
            if image in packages:
                raise RetentionError("configured package list contains a duplicate")
            packages[image] = visibility
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
        if not args.repository or not args.username or not token:
            raise RetentionError("repository, username and an existing workflow token are required")
        inventory, states = collect_inventory(args.repository, packages, client_factory(args.username, token))
        result = {
            "schema_version": 1, "observed_utc": datetime.now(timezone.utc).isoformat(),
            "repository": args.repository, "packages": packages, "versions": len(inventory.versions),
            "payload_roots": len(inventory.payloads), "verified_ci_attempts": len(states),
            "stored": inventory_usage(inventory), "protection": "not-evaluated", "mutation": "none",
        }
        print(json.dumps(result, sort_keys=True))
        return 0
    except RetentionError as error:
        print(f"Registry inventory unavailable; no mutation was attempted: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
