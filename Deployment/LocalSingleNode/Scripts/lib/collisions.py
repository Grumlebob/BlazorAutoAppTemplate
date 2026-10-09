"""Fail closed before adopting host directories, listeners or shared Caddy configuration."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys

from ls_settings import ETC, ROOT, command, read_yaml, settings


def caddy_root():
    path = ETC / "caddy/Caddyfile"
    if not path.exists():
        return
    if path.read_bytes() == (ROOT / "Deployment/Common/caddy/Caddyfile").read_bytes():
        return
    # A fresh package installation has its unmodified packaged configuration.
    expected = hashlib.md5(path.read_bytes()).hexdigest()
    entries = command("dpkg-query", "-W", "-f=${Conffiles}", "caddy")
    if any(line.split()[:2] == ["/etc/caddy/Caddyfile", expected] for line in entries.splitlines()):
        return
    raise ValueError("Foreign /etc/caddy/Caddyfile: inspect it before single-node setup")


def check(source, bootstrap=False):
    config = settings()
    app = config["app_name"]
    opt = Path(os.environ.get("OPT_ROOT", "/opt"))
    deploy = opt / str(Path(config["deploy_root"]).relative_to("/opt"))
    backup = opt / str(Path(config["backup_root"]).relative_to("/opt"))
    marker = ETC / f"localsinglenode/apps/{app}.json"
    owned = False
    if marker.exists():
        identity = json.loads(marker.read_text())
        owned = identity.get("source_repo_url") == source and identity.get("deploy_root") == config["deploy_root"] and identity.get("backup_root") == config["backup_root"]
        if not owned:
            raise ValueError("Single-node app marker belongs to a different repository or root")
    for directory in (deploy, backup):
        if directory.is_symlink():
            raise ValueError("App directories cannot be symlinks")
        if directory.exists() and any(directory.iterdir()) and not owned:
            raise ValueError(f"Unowned nonempty directory: {directory}")
    secrets = ETC / app
    if secrets.is_symlink() or (secrets.exists() and any(secrets.iterdir()) and not owned):
        raise ValueError("Unowned or symlinked runtime secret directory")
    caddy_root()
    requested = {config[key] for key in ("app_port", "postgres_port", "redis_port", "lan_http_port")}
    subnet = ipaddress.ip_network(config["docker_subnet"])
    machine = ETC / "localsinglenode/machine.yml"
    if machine.exists() and subnet.overlaps(ipaddress.ip_network(read_yaml(machine, node=True)["lan_cidr"])):
        raise ValueError("Docker subnet overlaps the deployment LAN")
    for path in opt.glob("*/docker-compose.yml"):
        if path.parent == deploy and owned:
            continue
        result = json.loads(command("docker", "compose", "--project-directory", str(path.parent), "-f", str(path), "config", "--format", "json"))
        for service in result.get("services", {}).values():
            for binding in service.get("ports", []):
                published = str(binding.get("published", ""))
                if published.isdigit() and int(published) in requested:
                    raise ValueError(f"Port collision with {path}")
                if "-" in published:
                    first, last = published.split("-", 1)
                    if first.isdigit() and last.isdigit() and any(int(first) <= port <= int(last) for port in requested):
                        raise ValueError(f"Port range collision with {path}")
        for network in result.get("networks", {}).values():
            for value in network.get("ipam", {}).get("config", []):
                if value.get("subnet") and subnet.overlaps(ipaddress.ip_network(value["subnet"])):
                    raise ValueError(f"Docker subnet collision with {path}")
    for path in (ETC / "caddy/sites").glob("*.caddy"):
        if path.name == f"{app}.caddy" and owned:
            continue
        text = path.read_text()
        for port in requested:
            if re.search(rf":{port}(?![0-9])", text) or (port == 80 and re.search(r"http://[^,\s:{]+(?:[,\s{]|$)", text)):
                raise ValueError(f"Port collision with Caddy site {path.name}")
    own_ports = set()
    if not bootstrap:
        ids = command("docker", "ps", "-q").splitlines()
        containers = json.loads(command("docker", "inspect", *ids)) if ids else []
        for container in containers:
            labels = container.get("Config", {}).get("Labels", {}) or {}
            if owned and labels.get("com.docker.compose.project") == app and labels.get("localsinglenode.app") == app:
                for bindings in (container.get("NetworkSettings", {}).get("Ports", {}) or {}).values():
                    for binding in bindings or []:
                        if binding["HostIp"] == "127.0.0.1":
                            own_ports.add(int(binding["HostPort"]))
        network_ids = command("docker", "network", "ls", "-q").splitlines()
        networks = json.loads(command("docker", "network", "inspect", *network_ids)) if network_ids else []
        for network in networks:
            if owned and network.get("Labels", {}).get("com.docker.compose.project") == app:
                continue
            for value in network.get("IPAM", {}).get("Config", []):
                if value.get("Subnet") and ':' not in value["Subnet"] and subnet.overlaps(ipaddress.ip_network(value["Subnet"])):
                    raise ValueError("Docker subnet overlaps a foreign runtime network")
    listeners = command("ss", "-ltnp")
    for line in listeners.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 4:
            continue
        local = fields[3]
        port_text = local.rsplit(":", 1)[-1]
        if not port_text.isdigit() or int(port_text) not in requested:
            continue
        port = int(port_text)
        if port in own_ports and local.startswith("127.0.0.1:") and '"docker-proxy"' in line:
            continue
        if port == config["lan_http_port"] and '"caddy"' in line and (owned or bootstrap):
            continue
        raise ValueError(f"Unowned listening socket on requested port {port}")
    print("Port, subnet, directory and Caddy ownership checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo-url", required=True)
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    try:
        check(args.source_repo_url, args.bootstrap)
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
