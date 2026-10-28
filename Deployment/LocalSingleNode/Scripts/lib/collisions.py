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


def _check_owned_paths(
    config: dict, source: str, opt: Path, etc: Path
) -> tuple[bool, Path]:
    """Validate app ownership and ensure configured app paths are safe to adopt."""
    app = config["app_name"]
    deploy = opt / str(Path(config["deploy_root"]).relative_to("/opt"))
    backup = opt / str(Path(config["backup_root"]).relative_to("/opt"))
    marker = etc / f"localsinglenode/apps/{app}.json"
    owned = False
    if marker.exists():
        identity = json.loads(marker.read_text())
        recorded_source = identity.get("source_repo_url")
        owned = (
            isinstance(recorded_source, str)
            and recorded_source.casefold() == source.casefold()
            and identity.get("deploy_root") == config["deploy_root"]
            and identity.get("backup_root") == config["backup_root"]
        )
        if not owned:
            raise ValueError("Single-node app marker belongs to a different repository or root")

    for directory in (deploy, backup):
        if directory.is_symlink():
            raise ValueError("App directories cannot be symlinks")
        if directory.exists() and any(directory.iterdir()) and not owned:
            raise ValueError(f"Unowned nonempty directory: {directory}")
    secrets = etc / app
    if secrets.is_symlink() or (secrets.exists() and any(secrets.iterdir()) and not owned):
        raise ValueError("Unowned or symlinked runtime secret directory")
    return owned, deploy


def _check_machine_subnet(etc: Path, subnet: ipaddress.IPv4Network) -> None:
    machine = etc / "localsinglenode/machine.yml"
    if machine.exists() and subnet.overlaps(
        ipaddress.ip_network(read_yaml(machine, node=True)["lan_cidr"])
    ):
        raise ValueError("Docker subnet overlaps the deployment LAN")


def _port_collision_reason(published: str, requested: set[int]) -> str | None:
    """Classify one Compose host-port binding without changing its error wording."""
    if published.isdigit() and int(published) in requested:
        return "Port collision"
    if "-" in published:
        first, last = published.split("-", 1)
        if first.isdigit() and last.isdigit() and any(
            int(first) <= port <= int(last) for port in requested
        ):
            return "Port range collision"
    return None


def _check_compose_port_conflicts(
    services: dict, requested: set[int], compose_file: Path
) -> None:
    for service in services.values():
        for binding in service.get("ports", []):
            published = str(binding.get("published", ""))
            reason = _port_collision_reason(published, requested)
            if reason:
                raise ValueError(f"{reason} with {compose_file}")


def _check_compose_network_conflicts(
    networks: dict, subnet: ipaddress.IPv4Network, compose_file: Path
) -> None:
    for network in networks.values():
        for value in network.get("ipam", {}).get("config", []):
            if value.get("subnet") and subnet.overlaps(ipaddress.ip_network(value["subnet"])):
                raise ValueError(f"Docker subnet collision with {compose_file}")


def _check_compose_conflicts(
    opt: Path, deploy: Path, requested: set[int], subnet: ipaddress.IPv4Network, owned: bool
) -> None:
    """Inspect every foreign Compose project for host-port and subnet conflicts."""
    for path in opt.glob("*/docker-compose.yml"):
        if path.parent == deploy and owned:
            continue
        # Deployed apps keep Compose interpolation values in .compose.env; without it,
        # `config` fails on required variables such as DATA_PROTECTION_CERT_HOST_PATH.
        compose_env = path.parent / ".compose.env"
        env_file = ["--env-file", str(compose_env)] if compose_env.is_file() else []
        result = json.loads(
            command(
                "docker",
                "compose",
                "--project-directory",
                str(path.parent),
                *env_file,
                "-f",
                str(path),
                "config",
                "--format",
                "json",
            )
        )
        _check_compose_port_conflicts(result.get("services", {}), requested, path)
        _check_compose_network_conflicts(result.get("networks", {}), subnet, path)


def _check_caddy_sites(
    etc: Path, app: str, source: str, requested: set[int], owned: bool
) -> None:
    """Reject foreign Caddy sites that claim an app's requested port."""
    for path in (etc / "caddy/sites").glob("*.caddy"):
        if path.name == f"{app}.caddy" and owned:
            continue
        if path.name == f"{app}-public.caddy" and owned:
            public_state = etc / app / "public.json"
            if public_state.exists() and not public_state.is_symlink():
                public_source = json.loads(public_state.read_text()).get("source_repo_url", "")
                if public_source.casefold() == source.casefold():
                    continue
            raise ValueError("Public Caddy site has no matching repository ownership")
        text = path.read_text()
        for port in requested:
            if re.search(rf":{port}(?![0-9])", text) or (
                port == 80 and re.search(r"http://[^,\s:{]+(?:[,\s{]|$)", text)
            ):
                raise ValueError(f"Port collision with Caddy site {path.name}")


def _owned_container_ports(app: str, owned: bool) -> set[int]:
    """Return loopback ports published by the repository's owned containers."""
    ids = command("docker", "ps", "-q").splitlines()
    containers = json.loads(command("docker", "inspect", *ids)) if ids else []
    own_ports = set()
    for container in containers:
        labels = container.get("Config", {}).get("Labels", {}) or {}
        if (
            owned
            and labels.get("com.docker.compose.project") == app
            and labels.get("localsinglenode.app") == app
        ):
            for bindings in (container.get("NetworkSettings", {}).get("Ports", {}) or {}).values():
                for binding in bindings or []:
                    if binding["HostIp"] == "127.0.0.1":
                        own_ports.add(int(binding["HostPort"]))
    return own_ports


def _check_runtime_network_conflicts(
    app: str, owned: bool, subnet: ipaddress.IPv4Network
) -> None:
    """Reject foreign Docker networks that overlap the configured app subnet."""
    network_ids = command("docker", "network", "ls", "-q").splitlines()
    networks = json.loads(command("docker", "network", "inspect", *network_ids)) if network_ids else []
    for network in networks:
        if owned and (network.get("Labels") or {}).get("com.docker.compose.project") == app:
            continue
        for value in (network.get("IPAM") or {}).get("Config") or []:
            if value.get("Subnet") and ":" not in value["Subnet"] and subnet.overlaps(
                ipaddress.ip_network(value["Subnet"])
            ):
                raise ValueError("Docker subnet overlaps a foreign runtime network")


def _check_listeners(
    lines: list[str],
    requested: set[int],
    own_ports: set[int],
    lan_http_port: int,
    owned: bool,
    bootstrap: bool,
) -> None:
    """Allow only owned loopback containers and the owned LAN Caddy listener."""
    for line in lines[1:]:
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
        if port == lan_http_port and '"caddy"' in line and (owned or bootstrap):
            continue
        raise ValueError(f"Unowned listening socket on requested port {port}")


def check(source, bootstrap=False, settings_file=None):
    config = settings(settings_file) if settings_file is not None else settings()
    app = config["app_name"]
    opt = Path(os.environ.get("OPT_ROOT", "/opt"))
    owned, deploy = _check_owned_paths(config, source, opt, ETC)
    caddy_root()
    requested = {config[key] for key in ("app_port", "postgres_port", "redis_port", "lan_http_port")}
    subnet = ipaddress.ip_network(config["docker_subnet"])
    _check_machine_subnet(ETC, subnet)
    _check_compose_conflicts(opt, deploy, requested, subnet, owned)
    _check_caddy_sites(ETC, app, source, requested, owned)
    own_ports = set()
    if not bootstrap:
        own_ports = _owned_container_ports(app, owned)
        _check_runtime_network_conflicts(app, owned, subnet)
    _check_listeners(
        command("ss", "-ltnp").splitlines(),
        requested,
        own_ports,
        config["lan_http_port"],
        owned,
        bootstrap,
    )
    print("Port, subnet, directory and Caddy ownership checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo-url", required=True)
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--settings-file", type=Path)
    args = parser.parse_args()
    try:
        check(args.source_repo_url, args.bootstrap, args.settings_file)
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
