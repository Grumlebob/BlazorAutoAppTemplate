"""Read-only native node diagnostics; never repair state implicitly."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from ls_settings import ETC, command, read_yaml, settings
from platform_check import native


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
    service_file = Path(f"/home/deploy/actions-runner-{config['app_name']}/.service")
    record("runner", lambda: command("systemctl", "is-active", service_file.read_text().strip()) == "active")
    record("docker-group", lambda: "docker" in command("id", "-nG", "deploy").split())
    # UFW's world-readable rule file avoids a sudo probe in this read-only command.
    record("firewall", lambda: "ENABLED=yes" in (ETC / "ufw/ufw.conf").read_text())
    record("caddy", lambda: command("systemctl", "is-active", "caddy") == "active")
    secret = ETC / config["app_name"] / "secrets.yml"
    record("secret-mode", lambda: not secret.is_symlink() and secret.stat().st_mode & 0o777 == 0o600)
    record("disk-20GiB", lambda: shutil.disk_usage("/opt").free >= 20 * 1024 ** 3)
    record("mdns", lambda: machine["ip"] in command("getent", "ahostsv4", machine["name"] + ".local"))
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
