#!/usr/bin/env python3
"""Publish validated public deployment inputs to the intended repository."""
import argparse
import hashlib
import importlib.util
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


def additional_configuration(path, config, state):
    spec = importlib.util.spec_from_file_location("app_instance", Path(__file__).parent / "resolve-app-instance.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from resolve_frontend_profile import resolve_frontend_profile
    payload = json.loads(protected_read(path), object_pairs_hook=module.unique_object)
    if not isinstance(payload, dict):
        raise ValueError("Additional instance configuration must be an object")
    selected = resolve_frontend_profile(ROOT / "frontend-profile.txt")
    public = {"hostname": config["public_hostname"], "tunnel_id": state["tunnel_id"], "origin_port": config["origin_port"]}
    if payload.get("public") and payload["public"] != public:
        raise ValueError("Existing additional public configuration differs")
    payload["public"] = public
    candidate, _, _ = module.validate_additional(payload, settings(ROOT / "Deployment/LocalSingleNode/inventory/group_vars/all.yml"), selected)
    return payload, candidate


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
    parser.add_argument("--environment", help="protected additional-app environment; requires --instance-config-file")
    parser.add_argument("--instance-config-file", type=Path, help="protected additional instance JSON")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
            raise ValueError("Invalid repository")
        if bool(args.environment) != bool(args.instance_config_file):
            raise ValueError("Additional public setup requires both environment and instance configuration")
        if args.environment and not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", args.environment):
            raise ValueError("Invalid additional environment")
        config = validate_config(json.loads(args.config.read_text()))
        state = json.loads(protected_read(args.state))
        if not isinstance(state, dict):
            raise ValueError("Cloudflare ownership state is invalid")
        identity = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        if state.get("identity") != identity or state.get("pending") or not state.get("dns_id"):
            raise ValueError("Cloudflare ownership state is incomplete or belongs to another config")
        token = protected_read(args.connector_token_file).strip()
        payload, candidate = additional_configuration(args.instance_config_file, config, state) if args.environment else (None, settings())
        validate(config["public_hostname"], state["tunnel_id"], config["origin_port"], token,
                 candidate, expected_account_id=config["account_id"])
        pages = json.loads(gh("api", f"repos/{args.repo}/actions/variables", "--paginate", "--slurp"))
        existing = {item["name"]: item["value"] for page in pages for item in page["variables"]}
        if existing.get("LOCALSINGLENODE_HOST") != args.node:
            raise ValueError("Repository deploy host differs from the requested native node")
        environment_args = []
        if args.environment:
            configured_environment = existing.get("LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT", "")
            primary_environment = existing.get("LOCALSINGLENODE_ENVIRONMENT", "localsinglenode")
            if configured_environment != args.environment or args.environment.casefold() == primary_environment.casefold():
                raise ValueError("Additional environment must match the configured distinct repository environment")
            environment_args = ["--env", args.environment]
            entries = json.loads(gh("variable", "list", "--repo", args.repo, *environment_args, "--json", "name,value"))
            existing = {item["name"]: item["value"] for item in entries}
        desired = {"LOCALSINGLENODE_PUBLIC_HOSTNAME": config["public_hostname"],
                   "LOCALSINGLENODE_PUBLIC_TUNNEL_ID": state["tunnel_id"],
                   "LOCALSINGLENODE_PUBLIC_ORIGIN_PORT": str(config["origin_port"])}
        if any(name in existing and existing[name] != value for name, value in desired.items()):
            raise ValueError("Existing public repository variables differ; inspect before replacing them")
        # gh encrypts the secret for GitHub. It is never passed in argv or stdout.
        gh("secret", "set", "LOCALSINGLENODE_PUBLIC_TUNNEL_TOKEN", "--repo", args.repo, *environment_args, input_value=token)
        if payload is not None:
            gh("secret", "set", "LOCALSINGLENODE_APP_INSTANCE", "--repo", args.repo, *environment_args,
               input_value=json.dumps(payload, sort_keys=True))
        for name, value in desired.items():
            if existing.get(name) != value:
                gh("variable", "set", name, "--repo", args.repo, *environment_args, "--body", value)
        print("Protected public deployment inputs configured for the verified repository and node")
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, SyntaxError):
        print("Public repository configuration failed; inspect protected ownership state and GitHub access.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
