#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python3 - "$REPO_ROOT" <<'PY'
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(sys.argv[1])
API_ROOT = "https://api.cloudflare.com/client/v4"


def fail(message: str) -> None:
    raise SystemExit(f"Cloudflare tunnel setup failed: {message}")


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        fail(f"set {name} first")
    return value


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
            fail(f"{path}: {key} is empty")
        return value
    fail(f"{path}: missing {key}")


def api(method: str, path: str, body: dict[str, object] | None = None) -> object:
    token = required_env("CLOUDFLARE_API_TOKEN")
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        fail(f"Cloudflare API returned HTTP {exc.code}: {details}")
    except urllib.error.URLError as exc:
        fail(f"Cloudflare API request failed: {exc}")

    try:
        envelope = json.loads(payload)
    except json.JSONDecodeError:
        fail(f"Cloudflare API returned non-JSON response: {payload}")

    if not envelope.get("success", False):
        fail(json.dumps(envelope.get("errors", envelope), indent=2))
    return envelope.get("result")


def find_tunnel(account_id: str, tunnel_name: str) -> dict[str, object] | None:
    query = urllib.parse.urlencode({"per_page": "100"})
    result = api("GET", f"/accounts/{account_id}/cfd_tunnel?{query}")
    if not isinstance(result, list):
        fail("unexpected tunnel list response")
    for tunnel in result:
        if isinstance(tunnel, dict) and tunnel.get("name") == tunnel_name and not tunnel.get("deleted_at"):
            return tunnel
    return None


def ensure_tunnel(account_id: str, tunnel_name: str) -> dict[str, object]:
    tunnel = find_tunnel(account_id, tunnel_name)
    if tunnel is None:
        secret = base64.b64encode(os.urandom(32)).decode("ascii")
        result = api(
            "POST",
            f"/accounts/{account_id}/cfd_tunnel",
            {
                "name": tunnel_name,
                "config_src": "cloudflare",
                "tunnel_secret": secret,
            },
        )
        if not isinstance(result, dict):
            fail("unexpected tunnel create response")
        tunnel = result

    config_src = tunnel.get("config_src")
    remote_config = tunnel.get("remote_config")
    if config_src == "local" or remote_config is False:
        fail(f"tunnel {tunnel_name} is not remotely managed")
    return tunnel


def ensure_tunnel_config(account_id: str, tunnel_id: str, public_hostname: str) -> None:
    api(
        "PUT",
        f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
        {
            "config": {
                "ingress": [
                    {
                        "hostname": public_hostname,
                        "service": "http://127.0.0.1:80",
                    },
                    {
                        "service": "http_status:404",
                    },
                ],
            },
        },
    )


def find_dns_record(zone_id: str, public_hostname: str) -> dict[str, object] | None:
    query = urllib.parse.urlencode({"type": "CNAME", "name": public_hostname, "per_page": "100"})
    result = api("GET", f"/zones/{zone_id}/dns_records?{query}")
    if not isinstance(result, list):
        fail("unexpected DNS record list response")
    for record in result:
        if isinstance(record, dict) and record.get("name") == public_hostname:
            return record
    return None


def ensure_dns_record(zone_id: str, public_hostname: str, tunnel_id: str) -> None:
    body = {
        "type": "CNAME",
        "name": public_hostname,
        "content": f"{tunnel_id}.cfargotunnel.com",
        "ttl": 1,
        "proxied": True,
    }
    record = find_dns_record(zone_id, public_hostname)
    if record is None:
        api("POST", f"/zones/{zone_id}/dns_records", body)
    else:
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            fail("existing DNS record is missing id")
        api("PATCH", f"/zones/{zone_id}/dns_records/{record_id}", body)


def get_tunnel_token(account_id: str, tunnel_id: str) -> str:
    result = api("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token")
    if not isinstance(result, str) or not result:
        fail("unexpected tunnel token response")
    return result


def main() -> int:
    account_id = required_env("CLOUDFLARE_ACCOUNT_ID")
    zone_id = required_env("CLOUDFLARE_ZONE_ID")

    settings = ROOT / "Deployment/LocalCluster/inventory/prod/group_vars/all.yml"
    tunnel_name = os.environ.get("CLOUDFLARE_TUNNEL_NAME", "").strip() or read_simple_yaml_value(
        settings, "cloudflare_tunnel_name"
    )
    public_hostname = os.environ.get("PUBLIC_HOSTNAME", "").strip() or read_simple_yaml_value(
        settings, "public_hostname"
    )

    tunnel = ensure_tunnel(account_id, tunnel_name)
    tunnel_id = tunnel.get("id")
    if not isinstance(tunnel_id, str) or not tunnel_id:
        fail("tunnel response is missing id")

    ensure_tunnel_config(account_id, tunnel_id, public_hostname)
    ensure_dns_record(zone_id, public_hostname, tunnel_id)
    tunnel_token = get_tunnel_token(account_id, tunnel_id)

    print(f"Cloudflare tunnel ready: {tunnel_name}")
    print(f"Public hostname ready: {public_hostname}")
    print()
    print("Paste this into Deployment/LocalCluster/inventory/prod/vault.yml:")
    print(f'vault_cloudflare_tunnel_token: "{tunnel_token}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
