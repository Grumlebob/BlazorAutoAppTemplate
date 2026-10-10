"""Reject foreign public connector resources and listening sockets."""
import argparse
import json
from pathlib import Path
import re
import sys

from ls_settings import ETC, command, settings


def check(source, host, tunnel, port):
    config = settings()
    app = config["app_name"]
    state = ETC / app / "public.json"
    owned = False
    if state.is_symlink():
        raise ValueError("Public ownership state cannot be a symlink")
    if state.exists():
        previous = json.loads(state.read_text())
        owned = previous.get("source_repo_url", "").casefold() == source.casefold() and all(
            previous.get(key) == value for key, value in {
                "hostname": host, "tunnel_id": tunnel, "origin_port": port,
            }.items()
        )
        if not owned:
            raise ValueError("Public deployment identity differs; inspect before replacing it")
    site = ETC / "caddy/sites" / (app + "-public.caddy")
    unit = ETC / "systemd/system" / ("cloudflared-" + app + ".service")
    token = ETC / app / "cloudflare-token"
    for path in (site, unit, token):
        if path.is_symlink() or (path.exists() and not owned):
            raise ValueError("Public connector path exists without verified ownership")
    for path in (ETC / "caddy/sites").glob("*.caddy"):
        if path == site and owned:
            continue
        text = path.read_text()
        if re.search(rf":{port}(?![0-9])", text) or host in text:
            raise ValueError("Public hostname or listener conflicts with another Caddy site")
    for line in command("ss", "-ltnp").splitlines()[1:]:
        fields = line.split()
        if len(fields) > 3 and fields[3].rsplit(":", 1)[-1] == str(port):
            if not (owned and fields[3] == f"127.0.0.1:{port}" and '"caddy"' in line):
                raise ValueError("Public origin port has a foreign or non-loopback listener")
    print("Public connector ownership and listener checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo-url", required=True)
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--tunnel-id", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    try:
        check(args.source_repo_url, args.hostname, args.tunnel_id, args.port)
    except (ValueError, OSError, KeyError):
        print("Public connector ownership or listener conflict; inspect before mutation.", file=sys.stderr)
        sys.exit(1)
