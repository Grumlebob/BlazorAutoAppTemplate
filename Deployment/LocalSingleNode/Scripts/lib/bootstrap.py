"""One operator-owned privileged setup, with explicit native identity checks before mutation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import subprocess
import sys
import tempfile
import time
import urllib.request

from ls_settings import ROOT, TARGET, command, settings
from machine import detect, read_yaml, valid_hostname, validate, yaml
from platform_check import native

VERSION = 1


def guard(args):
    if not native():
        raise ValueError("Native Linux required; never bootstrap Windows or WSL")
    if os.geteuid() != 0:
        raise ValueError("The operator must run the printed sudo command")
    user = os.environ.get("SUDO_USER", "")
    if not user or user in ("root", "deploy") or user != args.user or pwd.getpwnam(user).pw_uid == 0:
        raise ValueError("A real SUDO_USER matching --user is required")
    if os.environ.get("LOCALSINGLENODE_ETC") or os.environ.get("OPT_ROOT"):
        raise ValueError("Fixture paths are not permitted for privileged bootstrap")
    if not args.yes:
        raise ValueError("Use the complete operator command with --yes")
    if not valid_hostname(args.node) or not re.fullmatch(r"[A-Za-z0-9-]+", args.github_login):
        raise ValueError("Invalid node name or GitHub login")
    facts = detect()
    if args.expected_address and facts["ip"] != args.expected_address:
        raise ValueError("Detected address differs from the operator's intended target; no changes made")
    print(f"Native host: {facts['name']}; LAN address: {facts['ip']}; intended node: {args.node}", flush=True)


def run(*args, **options):
    subprocess.run(args, check=True, timeout=1200, **options)


def main():
    parser = argparse.ArgumentParser()
    for name in ("node", "user", "github-login"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--expected-address")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--ci-runner", action="store_true")
    args = parser.parse_args()
    guard(args)
    config = settings()
    # Derive origin as the install user, avoiding root's Git safe-directory state.
    origin = command("sudo", "-u", args.user, "-H", "git", "-C", str(ROOT), "remote", "get-url", "origin")
    match = re.fullmatch(r"(?:https://github.com/|git@github.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?", origin)
    if not match:
        raise ValueError("Origin must be a GitHub repository")
    repo = match[1]
    source = "https://github.com/" + repo
    import shutil
    local_gh = Path(pwd.getpwnam(args.user).pw_dir) / ".local/share/localsinglenode-tools/bin/gh"
    gh_path = str(local_gh) if local_gh.is_file() else shutil.which("gh")
    if not gh_path:
        raise ValueError("Run the agent tools step and gh auth login before bootstrap")
    gh = ["sudo", "-u", args.user, "-H", gh_path]
    # Authentication/admin checks precede privileged changes.
    if command(*gh, "api", f"repos/{repo}", "--jq", ".permissions.admin") != "true":
        raise ValueError("The install user's GitHub login needs repository admin")
    step = 0
    title = "preflight"
    def begin(number, name):
        nonlocal step, title
        step, title = number, name
        print(f"Step {number}/8: {name}", flush=True)
    try:
        begin(1, "OS packages and approved node name")
        # A failed bootstrap may have left Cloudsmith blocking all apt updates.
        run("python3", str(ROOT / "Deployment/Common/Scripts/retire-caddy-cloudsmith-source.py"))
        packages = ["git", "gh", "curl", "openssh-server", "avahi-daemon", "libnss-mdns", "python3-venv", "python3-pip", "sshpass", "iproute2", "ca-certificates"]
        for action in (["update"], ["install", "-y", "--no-install-recommends", *packages]):
            for attempt in range(3):
                try:
                    run("timeout", "--foreground", "600", "apt-get", *action, stdin=subprocess.DEVNULL, env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"})
                    break
                except subprocess.SubprocessError:
                    if attempt == 2:
                        raise
                    time.sleep(5 * (attempt + 1))
        if command("hostname") != args.node:
            run("hostnamectl", "set-hostname", args.node)
            import ipaddress
            # Ubuntu's secondary hostname loopback address, not a deployment LAN fact.
            hostname_loopback = str(ipaddress.ip_address("127.0.0.1") + 256)
            hosts = Path("/etc/hosts")
            lines = [line for line in hosts.read_text().splitlines() if not line.startswith(hostname_loopback)]
            hosts.write_text("\n".join(lines) + "\n" + hostname_loopback + " " + args.node + "\n")
        begin(2, "validated machine facts")
        directory = Path("/etc/localsinglenode")
        directory.mkdir(mode=0o755, exist_ok=True)
        override = TARGET / "machine.yml"
        facts = validate(read_yaml(override, node=True)) if override.exists() else detect(directory / "machine.yml" if (directory / "machine.yml").exists() else None)
        if facts["install_user"] != args.user or (args.expected_address and facts["ip"] != args.expected_address):
            raise ValueError("Machine override does not match approved user/address")
        machine = directory / "machine.yml"
        machine.write_text(yaml(facts))
        machine.chmod(0o644)
        begin(3, "install-user Ansible without sudoers changes")
        common = ROOT / "Deployment/Common/Scripts"
        run("sudo", "-u", args.user, "-H", "bash", str(common / "install-ansible.sh"), "--provision", "--user-only")
        ansible = Path(pwd.getpwnam(args.user).pw_dir) / ".local/share/books-ansible/current/bin/ansible-playbook"
        with tempfile.TemporaryDirectory(prefix="single-node-bootstrap-") as temp:
            inventory = Path(temp) / "hosts.yml"
            run("bash", str(TARGET / "Scripts/generate-inventory.sh"), "--machine", str(machine), "--output", str(inventory))
            extra = ["-e", "source_repo_url=" + source]
            begin(4, "prepare local runtime")
            run(str(ansible), "-i", str(inventory), "playbooks/PrepareSingleNode.yml", *extra, cwd=TARGET / "ansible")
            if args.ci_runner:
                run("usermod", "-aG", "docker", args.user)
                print("Fork CI enabled: install user has root-equivalent Docker group access; start a fresh group session for local gates")
            begin(5, "public SSH keys and conditional hardening")
            with urllib.request.urlopen(f"https://github.com/{args.github_login}.keys", timeout=30) as response:
                candidates = response.read(1_000_000).decode().splitlines()
            valid = []
            for key in candidates:
                if not key.startswith(("ssh-", "ecdsa-")):
                    continue
                candidate = Path(temp) / "public-key"
                candidate.write_text(key + "\n")
                if subprocess.run(["ssh-keygen", "-l", "-f", str(candidate)], capture_output=True, timeout=10).returncode == 0:
                    valid.append(key)
            if valid:
                user = pwd.getpwnam(args.user)
                ssh = Path(user.pw_dir) / ".ssh"
                if ssh.is_symlink():
                    raise ValueError("Install user's SSH directory is a symlink")
                ssh.mkdir(mode=0o700, exist_ok=True)
                ssh.chmod(0o700)
                os.chown(ssh, user.pw_uid, user.pw_gid)
                authorized = ssh / "authorized_keys"
                if authorized.is_symlink():
                    raise ValueError("authorized_keys is a symlink")
                previous = authorized.read_text().splitlines() if authorized.exists() else []
                authorized.write_text("\n".join(dict.fromkeys([*previous, *valid])) + "\n")
                authorized.chmod(0o600)
                os.chown(authorized, user.pw_uid, user.pw_gid)
                hardening = Path(temp) / "harden.yml"
                hardening.write_text("- hosts: all\n  become: true\n  roles: [ssh_hardening]\n")
                run(str(ansible), "-i", str(inventory), str(hardening), cwd=TARGET / "ansible")
            else:
                print("No GitHub public keys found; SSH password authentication retained")
        begin(6, "deploy Ansible and Actions prerequisites")
        # Install-user home can be 0750. Deploy receives only standalone public installers.
        import shutil
        with tempfile.TemporaryDirectory(prefix="single-node-prereqs-") as temporary:
            folder = Path(temporary)
            folder.chmod(0o755)
            for script in ("install-ansible.sh", "ensure-actions-runner-prereqs.sh"):
                shutil.copyfile(common / script, folder / script)
                (folder / script).chmod(0o755)
                run("sudo", "-u", "deploy", "-H", "bash", str(folder / script), "--provision")
        begin(7, "app-specific Actions runner")
        runner = ["bash", str(TARGET / "Scripts/install-github-runner.sh"), "--user", args.user, "--repo", repo, "--node", args.node]
        run(*runner, *(["--ci-runner"] if args.ci_runner else []))
        begin(8, "bootstrap marker and read-only doctor")
        marker = {"version": VERSION, "timestamp": datetime.now(timezone.utc).isoformat(), "node": args.node, "app": config["app_name"], "repo": repo, "ci_runner": args.ci_runner}
        marker_file = directory / "bootstrap.json"
        previous = json.loads(marker_file.read_text()) if marker_file.exists() else {}
        apps = previous.get("apps", {})
        if previous.get("app") and "apps" not in previous:
            apps[previous["app"]] = previous
        apps[config["app_name"]] = marker
        temporary = directory / "bootstrap.json.tmp"
        temporary.write_text(json.dumps({"version": VERSION, "node": args.node, "apps": apps}, indent=2) + "\n")
        temporary.chmod(0o644)
        temporary.replace(marker_file)
        run("bash", str(TARGET / "Scripts/doctor.sh"))
    except Exception:
        print(f"FAILED at step {step}: {title}", file=sys.stderr)
        print("Re-run the same operator command: sudo bash " + shlex.join([str(TARGET / "Scripts/bootstrap-node.sh"), *sys.argv[1:]]), file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        # Do not print exception commands: registration or credential arguments may be sensitive.
        print(str(error) if isinstance(error, ValueError) else "Bootstrap command failed; inspect the numbered step above", file=sys.stderr)
        sys.exit(1)
