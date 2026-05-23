#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python3 - "$REPO_ROOT" <<'PY'
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "Deployment/LocalCluster/scripts/lib"))
from deploy_settings import load_settings  # noqa: E402

API_ROOT = "https://api.cloudflare.com/client/v4"


def fail(message: str) -> None:
    raise SystemExit(f"Cloudflare tunnel check failed: {message}")


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        fail(f"set {name} first")
    return value


def api(path: str) -> object:
    token = required_env("CLOUDFLARE_API_TOKEN")
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        fail(f"Cloudflare API returned HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
    except urllib.error.URLError as exc:
        fail(f"Cloudflare API request failed: {exc}")
    envelope = json.loads(payload)
    if not envelope.get("success", False):
        fail(json.dumps(envelope.get("errors", envelope), indent=2))
    return envelope.get("result")


account_id = required_env("CLOUDFLARE_ACCOUNT_ID")
zone_id = required_env("CLOUDFLARE_ZONE_ID")
settings = load_settings(ROOT / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml", validate_file=True)
tunnel_name = settings["cloudflare_tunnel_name"]
public_hostname = settings["public_hostname"]

tunnels = api(f"/accounts/{account_id}/cfd_tunnel?{urllib.parse.urlencode({'per_page': '100'})}")
if not isinstance(tunnels, list):
    fail("unexpected tunnel list response")
tunnel = next((item for item in tunnels if isinstance(item, dict) and item.get("name") == tunnel_name and not item.get("deleted_at")), None)
if not tunnel:
    fail(f"tunnel not found: {tunnel_name}")
tunnel_id = tunnel.get("id")
if not isinstance(tunnel_id, str) or not tunnel_id:
    fail("tunnel is missing id")

config_result = api(f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations")
config = config_result.get("config") if isinstance(config_result, dict) else None
ingress = config.get("ingress") if isinstance(config, dict) else None
if not isinstance(ingress, list):
    fail("tunnel config has no ingress list")

matching_ingress = [
    entry for entry in ingress
    if isinstance(entry, dict)
    and entry.get("hostname") == public_hostname
    and entry.get("service") == "http://127.0.0.1:80"
]
if not matching_ingress:
    fail(f"ingress missing {public_hostname} -> http://127.0.0.1:80")

query = urllib.parse.urlencode({"type": "CNAME", "name": public_hostname, "per_page": "100"})
records = api(f"/zones/{zone_id}/dns_records?{query}")
if not isinstance(records, list):
    fail("unexpected DNS record list response")
expected_content = f"{tunnel_id}.cfargotunnel.com"
record = next((item for item in records if isinstance(item, dict) and item.get("name") == public_hostname), None)
if not record:
    fail(f"DNS CNAME not found: {public_hostname}")
if record.get("content") != expected_content:
    fail(f"DNS CNAME points to {record.get('content')}, expected {expected_content}")
if record.get("proxied") is not True:
    fail("DNS CNAME is not proxied")

print(f"Cloudflare tunnel ok: {tunnel_name}")
print(f"Cloudflare hostname ok: {public_hostname} -> {expected_content}")
PY
