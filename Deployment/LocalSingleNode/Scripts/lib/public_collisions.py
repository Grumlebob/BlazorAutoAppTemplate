"""Reject foreign public connector resources and listening sockets."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from ls_settings import ETC, command, settings

PUBLIC_EXEC_BASE = Path("/usr/local/libexec")


def check(source, host, tunnel, port, version):
    config = settings()
    app = config["app_name"]
    state = ETC / app / "public.json"
    labels = host.split(".") if isinstance(host, str) else []
    if (not isinstance(source, str) or not source
            or not isinstance(host, str) or len(host) > 253 or host != host.lower() or len(labels) < 2
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)):
        raise ValueError("Public repository identity or hostname is invalid")
    try:
        valid_tunnel_id = str(uuid.UUID(tunnel)) == tunnel
    except (ValueError, TypeError, AttributeError):
        valid_tunnel_id = False
    if not valid_tunnel_id or type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Public tunnel ID or origin port is invalid")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]{4}\.[0-9]+\.[0-9]+", version):
        raise ValueError("Public connector version is invalid")
    owned = False
    previous = {}
    if state.is_symlink():
        raise ValueError("Public ownership state cannot be a symlink")
    if state.exists():
        state_info = state.lstat()
        if (not stat.S_ISREG(state_info.st_mode)
                or (os.geteuid() == 0 and state_info.st_uid != 0)
                or state_info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
            raise ValueError("Public ownership state must be a protected regular file")
        previous = json.loads(state.read_text())
        if not isinstance(previous, dict) or not isinstance(previous.get("source_repo_url"), str):
            raise ValueError("Public ownership state has an unexpected format")
        owned = previous["source_repo_url"].casefold() == source.casefold() and all(
            previous.get(key) == value for key, value in {
                "hostname": host, "tunnel_id": tunnel, "origin_port": port,
            }.items()
        )
        if not owned:
            raise ValueError("Public deployment identity differs; inspect before replacing it")
    owned_version = owned and previous.get("cloudflared_version") == version
    site = ETC / "caddy/sites" / (app + "-public.caddy")
    unit = ETC / "systemd/system" / ("cloudflared-" + app + ".service")
    token = ETC / app / "cloudflare-token"
    app_exec_dir = PUBLIC_EXEC_BASE / ("cloudflared-" + app)
    version_exec_dir = app_exec_dir / version
    executable = version_exec_dir / "cloudflared"
    for path in (Path("/usr/local"), PUBLIC_EXEC_BASE):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError("Public connector executable parent is not a real directory")
        if path == Path("/usr/local") and not path.exists():
            raise ValueError("Shared public connector executable parent is not traversable")
        if path.exists():
            info = path.stat()
            if os.geteuid() == 0 and info.st_uid != 0:
                raise ValueError("Shared public connector executable parent is not root-owned")
            if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise ValueError("Shared public connector executable parent is writable by non-root users")
            if path == PUBLIC_EXEC_BASE and not (info.st_mode & stat.S_IXOTH):
                raise ValueError("Shared public connector executable parent is not traversable")
    if app_exec_dir.is_symlink() or (app_exec_dir.exists() and not owned):
        raise ValueError("Public connector path exists without verified ownership")
    for path in (version_exec_dir, executable, site, unit, token):
        path_owned = owned_version if path in (version_exec_dir, executable) else owned
        if path.is_symlink() or (path.exists() and not path_owned):
            raise ValueError("Public connector path exists without verified ownership")
    if token.exists():
        token_info = token.lstat()
        if (not stat.S_ISREG(token_info.st_mode)
                or (os.geteuid() == 0 and token_info.st_uid != 0)
                or stat.S_IMODE(token_info.st_mode) != 0o600):
            raise ValueError("Public connector token must be a root-owned mode-0600 regular file")
    for path in (app_exec_dir, version_exec_dir, executable, site, unit):
        if not path.exists():
            continue
        info = path.lstat()
        is_directory = path in (app_exec_dir, version_exec_dir)
        if ((is_directory and not stat.S_ISDIR(info.st_mode))
                or (not is_directory and not stat.S_ISREG(info.st_mode))):
            raise ValueError("Public connector owned path has an unexpected file type")
        if os.geteuid() == 0 and info.st_uid != 0:
            raise ValueError("Public connector owned path is not root-owned")
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("Public connector owned path is writable by non-root users")
    for path in (app_exec_dir, version_exec_dir):
        if path.exists() and not path.is_dir():
            raise ValueError("Public connector directory has an unexpected type")
    if executable.exists() and not executable.is_file():
        raise ValueError("Public connector executable has an unexpected type")
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
    parser.add_argument("--cloudflared-version", required=True)
    args = parser.parse_args()
    try:
        check(args.source_repo_url, args.hostname, args.tunnel_id, args.port, args.cloudflared_version)
    except (ValueError, OSError, KeyError):
        print("Public connector ownership or listener conflict; inspect before mutation.", file=sys.stderr)
        sys.exit(1)
