"""Read-only native node diagnostics; never repair state implicitly."""
import argparse
import json
import shutil
import sys

from ls_settings import ETC, command, read_yaml, settings
from platform_check import native


def runner_active(app):
    # The install user cannot traverse deploy's private home. systemd exposes
    # service state and ownership without granting access to runner credentials.
    output = command("systemctl", "show", "--property=Id,ActiveState,User,WorkingDirectory", "actions.runner.*")
    services = [dict(line.split("=", 1) for line in block.splitlines() if "=" in line) for block in output.split("\n\n")]
    matching = [service for service in services if service.get("WorkingDirectory") == f"/home/deploy/actions-runner-{app}" and service.get("Id", "").startswith("actions.runner.")]
    return len(matching) == 1 and matching[0].get("ActiveState") == "active" and matching[0].get("User") == "deploy"


def mdns_resolves_lan(machine):
    # NSS may return only a Docker bridge address on a multihomed host. Ask
    # Avahi on the interface that actually owns the recorded deployment IPv4.
    interfaces = json.loads(command("ip", "-j", "-4", "address", "show"))
    for interface in interfaces:
        if not any(address.get("local") == machine["ip"] for address in interface.get("addr_info", [])):
            continue
        index = interface["ifindex"]
        name = machine["name"] + ".local"
        response = json.loads(command(
            "busctl", "--timeout=10s", "--json=short", "call",
            "org.freedesktop.Avahi", "/", "org.freedesktop.Avahi.Server",
            "ResolveHostName", "iisiu", str(index), "0", name, "0", "0",
        ))
        if not isinstance(response, dict):
            return False
        data = response.get("data", [])
        # Avahi's protocol value 0 means IPv4 for both query and result.
        return (
            response.get("type") == "iisisu" and isinstance(data, list) and len(data) == 6
            and data[0] == index and data[1] == 0 and data[3] == 0
            and isinstance(data[2], str) and data[2].casefold() == name.casefold() and data[4] == machine["ip"]
        )
    return False


def check():
    config = settings()
    values = []
    def record(name, test):
        try:
            success = bool(test())
        except (ValueError, OSError, KeyError):
            success = False
        values.append({"name": name, "pass": success})
    record("native-linux", native)
    if not values[0]["pass"]:
        return values
    machine = read_yaml(ETC / "localsinglenode/machine.yml", node=True)
    record("runner", lambda: runner_active(config["app_name"]))
    record("docker-group", lambda: "docker" in command("id", "-nG", "deploy").split())
    # UFW's world-readable rule file avoids a sudo probe in this read-only command.
    record("firewall", lambda: "ENABLED=yes" in (ETC / "ufw/ufw.conf").read_text())
    record("caddy", lambda: command("systemctl", "is-active", "caddy") == "active")
    secret = ETC / config["app_name"] / "secrets.yml"
    record("secret-mode", lambda: not secret.is_symlink() and secret.stat().st_mode & 0o777 == 0o600)
    record("disk-20GiB", lambda: shutil.disk_usage("/opt").free >= 20 * 1024 ** 3)
    record("mdns", lambda: mdns_resolves_lan(machine))
    return values


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        values = check()
        print(json.dumps(values) if args.json else "\n".join(("PASS " if item["pass"] else "FAIL ") + item["name"] for item in values))
        sys.exit(0 if all(item["pass"] for item in values) else 1)
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
