#!/usr/bin/env python3
"""Publish validated public deployment inputs to the intended repository."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Deployment/Common/Scripts/Component/lib"))
sys.path.insert(0, str(Path(__file__).parent / "lib"))
from cloudflare_tunnel import protected_read, validate_config
from public_config import validate
from ls_settings import settings


def gh(*args, input_value=None):
    result = subprocess.run(["gh", *args], input=input_value, text=True, capture_output=True, check=False)
    if result.returncode:
        raise ValueError("GitHub operation failed; inspect authentication and repository permissions")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--connector-token-file", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--node", required=True)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
            raise ValueError("Invalid repository")
        config = validate_config(json.loads(args.config.read_text()))
        state = json.loads(protected_read(args.state))
        identity = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        if state.get("identity") != identity or state.get("pending") or not state.get("dns_id"):
            raise ValueError("Cloudflare ownership state is incomplete or belongs to another config")
        token = protected_read(args.connector_token_file).strip()
        validate(config["public_hostname"], state["tunnel_id"], config["origin_port"], token, settings())
        pages = json.loads(gh("api", f"repos/{args.repo}/actions/variables", "--paginate", "--slurp"))
        existing = {item["name"]: item["value"] for page in pages for item in page["variables"]}
        if existing.get("LOCALSINGLENODE_HOST") != args.node:
            raise ValueError("Repository deploy host differs from the requested native node")
        desired = {"LOCALSINGLENODE_PUBLIC_HOSTNAME": config["public_hostname"],
                   "LOCALSINGLENODE_PUBLIC_TUNNEL_ID": state["tunnel_id"],
                   "LOCALSINGLENODE_PUBLIC_ORIGIN_PORT": str(config["origin_port"])}
        if any(name in existing and existing[name] != value for name, value in desired.items()):
            raise ValueError("Existing public repository variables differ; inspect before replacing them")
        # gh encrypts the secret for GitHub. It is never passed in argv or stdout.
        gh("secret", "set", "LOCALSINGLENODE_PUBLIC_TUNNEL_TOKEN", "--repo", args.repo, input_value=token)
        for name, value in desired.items():
            if existing.get(name) != value:
                gh("variable", "set", name, "--repo", args.repo, "--body", value)
        print("Protected public deployment inputs configured for the verified repository and node")
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print("Public repository configuration failed; inspect protected ownership state and GitHub access.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
