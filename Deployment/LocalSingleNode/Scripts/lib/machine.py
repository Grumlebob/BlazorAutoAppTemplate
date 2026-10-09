"""Validate and detect native node facts without changing the host."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import sys

from ls_settings import command, read_yaml


def validate(values, on_node=True):
    if set(values) != {"name", "ip", "lan_cidr", "install_user"}:
        raise ValueError("machine needs name, ip, lan_cidr and install_user")
    if any("REPLACE_WITH_" in str(value) for value in values.values()):
        raise ValueError("replace every machine placeholder")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", str(values["name"])):
        raise ValueError("invalid node hostname")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", str(values["install_user"])) or values["install_user"] in ("root", "deploy"):
        raise ValueError("install_user must be the original unprivileged Linux user")
    address = ipaddress.ip_address(str(values["ip"]))
    network = ipaddress.ip_network(str(values["lan_cidr"]), strict=True)
    if address.version != 4 or network.version != 4 or address not in network:
        raise ValueError("node IPv4 must belong to its LAN CIDR")
    if address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified:
        raise ValueError("node address must be a usable LAN IPv4")
    if address in (network.network_address, network.broadcast_address):
        raise ValueError("node address cannot be a network or broadcast address")
    if on_node and values["name"] != command("hostname"):
        raise ValueError("node name differs from hostname")
    return values


def detect(previous=None):
    routes = command("ip", "-4", "-o", "route", "show", "default").splitlines()
    if not routes:
        raise ValueError("connect this PC to the LAN: no IPv4 default route")
    fields = routes[0].split()
    if "dev" not in fields:
        raise ValueError("default route has no interface")
    device = fields[fields.index("dev") + 1]
    addresses = command("ip", "-4", "-o", "address", "show", "dev", device, "scope", "global").splitlines()
    if not addresses:
        raise ValueError("default-route interface has no IPv4 address")
    fields = addresses[0].split()
    address = ipaddress.ip_interface(fields[fields.index("inet") + 1])
    recorded = read_yaml(previous, node=True) if previous else {}
    user = recorded["install_user"] if previous else os.environ.get("SUDO_USER") or command("id", "-un")
    if recorded and recorded.get("ip") != str(address.ip):
        print("Warning: detected LAN address changed; using live address " + str(address.ip), file=sys.stderr)
    return validate({"name": command("hostname"), "ip": str(address.ip), "lan_cidr": str(address.network), "install_user": user})


def yaml(values):
    return "node:\n" + "".join(f"  {key}: {value}\n" for key, value in values.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("validate", "detect", "inventory"))
    parser.add_argument("file", nargs="?")
    parser.add_argument("--not-on-node", action="store_true")
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--machine", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "validate":
        validate(read_yaml(Path(args.file), node=True), not args.not_on_node)
        print("Machine facts valid")
        return
    if args.action == "detect":
        text = yaml(detect(args.previous))
    else:
        if not args.machine or not args.output:
            parser.error("inventory requires --machine and --output")
        values = validate(read_yaml(args.machine, node=True))
        group = command("id", "-gn", values["install_user"])
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", group):
            raise ValueError("invalid install user group")
        text = "all:\n  hosts:\n    " + values["name"] + ":\n      ansible_connection: local\n      ansible_python_interpreter: /usr/bin/python3\n"
        for key in ("ip", "lan_cidr", "install_user"):
            text += f"      {'node_ip' if key == 'ip' else key}: {values[key]}\n"
        text += f"      install_group: {group}\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
