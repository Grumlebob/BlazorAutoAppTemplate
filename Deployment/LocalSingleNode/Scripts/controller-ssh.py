"""Pair an authenticated controller with an existing native node without sudo."""
import argparse
import base64
import getpass
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ls_settings import read_yaml  # noqa: E402
from machine import validate, valid_hostname  # noqa: E402


class PairingError(ValueError):
    """A safe, actionable pairing failure suitable for a sanitized report."""


def run(*args, input_text=None):
    result = subprocess.run(args, input=input_text, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise PairingError(f"{Path(args[0]).name} failed; inspect access locally without publishing connection details")
    return result.stdout.strip()


def public_key(value):
    fields = value.strip().split()
    if len(fields) != 2 or fields[0] != "ssh-ed25519":
        raise PairingError("Expected one Ed25519 public key without a comment")
    try:
        blob = base64.b64decode(fields[1], validate=True)
    except ValueError as error:
        raise PairingError("Invalid public key encoding") from error
    prefix = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
    if len(blob) != len(prefix) + 32 or not blob.startswith(prefix):
        raise PairingError("Invalid Ed25519 public key")
    return " ".join(fields)


def variable_name(controller, suffix):
    return "LOCALSINGLENODE_SSH_" + controller.upper().replace("-", "_") + "_" + suffix


def get_variable(repo, name):
    return run("gh", "variable", "get", name, "--repo", repo)


def set_variable(repo, name, value):
    # Values travel through stdin, never command arguments or terminal output.
    run("gh", "variable", "set", name, "--repo", repo, input_text=value)


def ordinary(path):
    if path.is_symlink():
        raise PairingError("Refusing a symlink in SSH configuration")
    if path.exists() and not path.is_file():
        raise PairingError("Expected an ordinary SSH configuration file")


def private_directory(path):
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise PairingError("Refusing an unsafe SSH directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        if path.stat().st_uid != os.getuid():
            raise PairingError("SSH directory belongs to another user")
        path.chmod(0o700)


def write_private(path, text):
    ordinary(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                     dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(text)
    try:
        protect_file(temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def protect_file(path):
    if os.name == "nt":
        owner = run("whoami")
        run("icacls", str(path), "/inheritance:r", "/remove", "*S-1-3-4", "/grant:r", owner + ":(F)")
    else:
        path.chmod(0o600)


def paths(repo, controller):
    identity = hashlib.sha256((repo.lower() + ":" + controller).encode()).hexdigest()[:16]
    directory = Path.home() / ".ssh" / "localsinglenode"
    private_directory(directory.parent)
    private_directory(directory)
    return directory, identity


def controller_key(repo, controller, create=False):
    directory, identity = paths(repo, controller)
    key = directory / (identity + "_ed25519")
    ordinary(key)
    ordinary(key.with_suffix(".pub"))
    if not key.exists():
        if not create:
            raise PairingError("Run prepare on this controller first")
        if key.with_suffix(".pub").exists():
            raise PairingError("Public key exists without its private key; inspect locally")
        run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "", "-f", str(key))
    protect_file(key)
    value = public_key(run("ssh-keygen", "-y", "-P", "", "-f", str(key)))
    return key, value


def prepare(args):
    _, key = controller_key(args.repo, args.controller, create=True)
    set_variable(args.repo, variable_name(args.controller, "PUBLIC_KEY"), key)
    print("Controller public key published. Run authorize on the existing native node.")


def authorize_key(directory, key):
    private_directory(directory)
    authorized = directory / "authorized_keys"
    ordinary(authorized)
    previous = authorized.read_text() if authorized.exists() else ""
    # Never bypass restrictions by appending an unrestricted copy of the same key.
    present = False
    for line in previous.splitlines():
        fields = line.split()
        if fields[:2] == key.split():
            present = True
        elif not line.lstrip().startswith("#") and key in line:
            raise PairingError("Controller key already has restrictions; inspect them locally before pairing")
    if not present:
        write_private(authorized, previous + ("\n" if previous and not previous.endswith("\n") else "") + key + "\n")
    authorized.chmod(0o600)


def authorize(args):
    # Imports stay here: the controller also runs on Windows, where pwd is absent.
    from platform_check import native
    if not native() or os.geteuid() == 0:
        raise PairingError("Run authorize as the original install user on the native Linux node, without sudo")
    facts = validate(read_yaml(Path("/etc/localsinglenode/machine.yml"), node=True))
    if getpass.getuser() != facts["install_user"]:
        raise PairingError("Authorize must run as the recorded install user")
    if get_variable(args.repo, "LOCALSINGLENODE_HOST") != facts["name"]:
        raise PairingError("Repository target differs from this native node")
    key = public_key(get_variable(args.repo, variable_name(args.controller, "PUBLIC_KEY")))
    host_key = public_key(" ".join(Path("/etc/ssh/ssh_host_ed25519_key.pub").read_text().split()[:2]))
    authorize_key(Path.home() / ".ssh", key)
    record = {"version": 1, "hostname": facts["name"], "address": facts["ip"],
              "user": facts["install_user"], "host_key": host_key, "controller_key": key}
    set_variable(args.repo, variable_name(args.controller, "CONNECTION"), json.dumps(record))
    print("Controller key authorized. Verified node connection record published. No sudo or service changes used.")


def connection(args, key):
    record = json.loads(get_variable(args.repo, variable_name(args.controller, "CONNECTION")))
    expected = {"version", "hostname", "address", "user", "host_key", "controller_key"}
    if set(record) != expected or record["version"] != 1:
        raise PairingError("Invalid SSH connection record")
    if not valid_hostname(record["hostname"]) or record["hostname"] != get_variable(args.repo, "LOCALSINGLENODE_HOST"):
        raise PairingError("Connection record differs from repository target")
    address = ipaddress.IPv4Address(record["address"])
    if not address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified or address.is_multicast:
        raise PairingError("Expected a private LAN IPv4 address")
    if not isinstance(record["user"], str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", record["user"]) or record["user"] in ("root", "deploy"):
        raise PairingError("Expected the original install user")
    record["host_key"] = public_key(record["host_key"])
    if public_key(record["controller_key"]) != key:
        raise PairingError("Node authorized a different controller key")
    return record


def configure(args):
    key_path, key = controller_key(args.repo, args.controller)
    record = connection(args, key)
    directory, identity = paths(args.repo, args.controller)
    config = directory / (identity + ".conf")
    known = directory / (identity + "_known_hosts")
    trust_name = "localsinglenode-" + identity
    trust = trust_name + " " + record["host_key"] + "\n"
    ordinary(known)
    if known.exists() and known.read_text() != trust:
        raise PairingError("Node host key changed; verify the replacement on the native node before updating local trust")
    ordinary(config)
    if config.exists() and not config.read_text().startswith("Host " + args.alias + "\n"):
        raise PairingError("This controller record already uses another alias")
    main = directory.parent / "config"
    ordinary(main)
    previous = main.read_text() if main.exists() else ""
    include = 'Include "' + config.as_posix() + '"'
    if include not in previous.splitlines():
        # Refuse an explicit alias already owned by another SSH configuration.
        effective = run("ssh", "-G", args.alias)
        hostname = next((line.split(maxsplit=1)[1] for line in effective.splitlines() if line.startswith("hostname ")), "")
        explicit = re.search(r"(?mi)^\s*Host\s+.*(?<!\S)" + re.escape(args.alias) + r"(?=\s|$)", previous)
        if explicit or hostname != args.alias:
            raise PairingError("SSH alias is already configured; choose a new alias")
    text = (f"Host {args.alias}\n    HostName {record['address']}\n    User {record['user']}\n"
            f'    IdentityFile "{key_path.as_posix()}"\n    IdentitiesOnly yes\n'
            f'    UserKnownHostsFile "{known.as_posix()}"\n    HostKeyAlias {trust_name}\n'
            "    StrictHostKeyChecking yes\n    BatchMode yes\n    ConnectTimeout 10\n"
            "    ServerAliveInterval 30\n    ServerAliveCountMax 3\n    ForwardAgent no\nHost *\n")
    write_private(known, trust)
    write_private(config, text)
    if include not in previous.splitlines():
        write_private(main, include + "\n" + previous)
    verify(args, record)
    print("Persistent SSH alias verified. Host trust and controller identity are pinned; password prompts are disabled.")


def verify(args, record):
    probe = "import json,os,socket;print(json.dumps({'hostname':socket.gethostname(),'user':__import__('getpass').getuser(),'uid':os.getuid()}))"
    result = json.loads(run("ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                            args.alias, "python3 -c " + shlex.quote(probe)))
    if result.get("hostname") != record["hostname"] or result.get("user") != record["user"] or result.get("uid") == 0:
        raise PairingError("Remote hostname or login differs from the verified connection record")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "authorize", "configure"))
    parser.add_argument("--repo", required=True)
    parser.add_argument("--controller", required=True, help="Unique controller name within this repository")
    parser.add_argument("--alias", help="Reusable local SSH alias; required for configure")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("Use OWNER/REPOSITORY")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", args.controller):
        parser.error("Use a lowercase controller name with letters, digits and hyphens")
    if args.action == "configure" and (not args.alias or not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", args.alias)):
        parser.error("configure requires a lowercase SSH alias")
    {"prepare": prepare, "authorize": authorize, "configure": configure}[args.action](args)


if __name__ == "__main__":
    try:
        main()
    except PairingError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError):
        # Do not expose raw subprocess errors, API bodies, paths or target identities.
        print("SSH onboarding failed. Check the current step's prerequisites locally; keep diagnostics private.", file=sys.stderr)
        sys.exit(1)
