"""Validate optional public deployment inputs before any native mutation."""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
import uuid

from ls_settings import settings

PINNED_VERSION = "2026.10.0"
PINNED_CHECKSUM = "sha256:d33ff2d14475178d2012c2c56beba87389ac5ded27649519f198a7d3134a99db"


def validate(hostname, tunnel_id, port, token, config):
    if not hostname and not tunnel_id and not token:
        return {"public_enabled": False}
    labels = hostname.split(".")
    if len(hostname) > 253 or len(labels) < 2 or hostname != hostname.lower() or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
    ):
        raise ValueError("Invalid public hostname")
    if str(uuid.UUID(tunnel_id)) != tunnel_id:
        raise ValueError("Invalid tunnel UUID")
    if type(port) is not int or not 1024 <= port <= 65535 or port in {
        config[key] for key in ("app_port", "postgres_port", "redis_port", "lan_http_port")
    }:
        raise ValueError("Public origin port must be distinct from app, database, Redis and LAN ports")
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]{32,}", token):
        raise ValueError("Missing or invalid connector token")
    try:
        claims = json.loads(base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True))
        if claims.get("t") != tunnel_id or not re.fullmatch(r"[0-9a-f]{32}", str(claims.get("a", ""))) or not claims.get("s"):
            raise ValueError("Connector token does not match the configured tunnel")
    except (ValueError, TypeError, UnicodeDecodeError):
        raise ValueError("Connector token does not match the configured tunnel") from None
    return {"public_enabled": True, "public_hostname": hostname, "public_tunnel_id": tunnel_id,
            "public_origin_port": port, "public_cloudflared_version": PINNED_VERSION,
            "public_cloudflared_checksum": PINNED_CHECKSUM, "vault_public_tunnel_token": token}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        values = validate(
            os.environ.get("PUBLIC_HOSTNAME", ""), os.environ.get("PUBLIC_TUNNEL_ID", ""),
            int(os.environ.get("PUBLIC_ORIGIN_PORT") or "8085"),
            os.environ.get("PUBLIC_TUNNEL_TOKEN", "").strip(), settings(),
        )
        # O_EXCL/O_NOFOLLOW rejects existing and symlink paths before writing secrets.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump(values, handle)
            handle.write("\n")
        print("Validated public configuration: " + ("enabled" if values["public_enabled"] else "disabled"))
    except (ValueError, OSError, TypeError):
        print("Invalid public deployment inputs or unsafe output path; no credentials were printed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
