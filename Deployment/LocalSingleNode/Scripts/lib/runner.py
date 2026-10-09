"""Local runner installation: preserve registrations and fail closed on foreign identity."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import urllib.request

from ls_settings import ROOT, command, settings
from platform_check import native


def install(user, repo, node, ci):
    if not native() or os.geteuid() != 0 or os.environ.get("SUDO_USER") != user:
        raise ValueError("Runner installation requires the operator's native node bootstrap")
    app = settings()["app_name"]
    url = "https://github.com/" + repo
    name = node + "-" + app
    labels = ["localsinglenode-" + app] + (["ci-" + app] if ci else [])
    directory = Path("/home/deploy/actions-runner-" + app)
    if directory.is_symlink():
        raise ValueError("Runner directory cannot be a symlink")
    if (directory / ".runner").exists():
        identity = json.loads((directory / ".runner").read_text())
        if identity.get("agentName") != name or identity.get("gitHubUrl", "").rstrip("/") != url:
            raise ValueError("Existing runner identity differs; inspect it manually. Nothing was deleted.")
        runners = json.loads(command("sudo", "-u", user, "-H", "gh", "api", f"repos/{repo}/actions/runners?per_page=100"))["runners"]
        match = [runner for runner in runners if runner["name"] == name]
        if len(match) != 1 or not set(labels).issubset({label["name"] for label in match[0]["labels"]}):
            raise ValueError("Existing runner labels differ; inspect them manually")
        service_file = directory / ".service"
        if not service_file.exists():
            subprocess.run([str(directory / "svc.sh"), "install", "deploy"], cwd=directory, check=True, timeout=60)
            subprocess.run([str(directory / "svc.sh"), "start"], cwd=directory, check=True, timeout=60)
        else:
            service = service_file.read_text().strip()
            active = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True, timeout=30)
            if active.returncode or active.stdout.strip() != "active":
                progress = directory / ".installing.json"
                if not progress.is_file() or json.loads(progress.read_text()) != {"repo": repo, "name": name}:
                    raise ValueError("Existing runner service is not active; inspect it manually")
                subprocess.run([str(directory / "svc.sh"), "start"], cwd=directory, check=True, timeout=60)
        (directory / ".installing.json").unlink(missing_ok=True)
        print("Existing matching runner registration and service retained")
        return
    if directory.exists() and any(directory.iterdir()):
        progress = directory / ".installing.json"
        if not progress.is_file() or json.loads(progress.read_text()) != {"repo": repo, "name": name}:
            raise ValueError("Unconfigured nonempty runner directory; inspect it manually")
    directory.mkdir(parents=True, exist_ok=True)
    deploy = pwd.getpwnam("deploy")
    os.chown(directory, deploy.pw_uid, deploy.pw_gid)
    (directory / ".installing.json").write_text(json.dumps({"repo": repo, "name": name}))
    pin = json.loads((ROOT / "Deployment/Common/tool-versions.json").read_text())["runner"]
    version = pin["version"]
    archive = directory / "runner.tar.gz"
    with urllib.request.urlopen(f"https://github.com/actions/runner/releases/download/v{version}/actions-runner-linux-x64-{version}.tar.gz", timeout=60) as response, archive.open("wb") as output:
        import shutil
        shutil.copyfileobj(response, output)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != pin["sha256"]:
        raise ValueError("Actions runner archive checksum mismatch")
    subprocess.run(["tar", "xzf", str(archive), "-C", str(directory), "--no-same-owner"], check=True, timeout=120)
    archive.unlink()
    subprocess.run(["chown", "-R", "deploy:deploy", str(directory)], check=True)
    subprocess.run([str(directory / "bin/installdependencies.sh")], check=True, timeout=300)
    token = command("sudo", "-u", user, "-H", "gh", "api", "-X", "POST", f"repos/{repo}/actions/runners/registration-token", "--jq", ".token")
    # Official CommandSettings reads and masks ACTIONS_RUNNER_INPUT_TOKEN.
    environment = os.environ.copy()
    environment["ACTIONS_RUNNER_INPUT_TOKEN"] = token
    try:
        subprocess.run(["sudo", "--preserve-env=ACTIONS_RUNNER_INPUT_TOKEN", "-u", "deploy", "-H", str(directory / "config.sh"), "--unattended", "--url", url, "--name", name, "--labels", ",".join(labels), "--work", "_work"], env=environment, cwd=directory, check=True, timeout=180)
    finally:
        environment.pop("ACTIONS_RUNNER_INPUT_TOKEN", None)
        token = ""
    subprocess.run([str(directory / "svc.sh"), "install", "deploy"], cwd=directory, check=True, timeout=60)
    subprocess.run([str(directory / "svc.sh"), "start"], cwd=directory, check=True, timeout=60)
    (directory / ".installing.json").unlink(missing_ok=True)
    print(f"Runner installed: {name} [{','.join(labels)}]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("user", "repo", "node"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--ci-runner", action="store_true")
    args = parser.parse_args()
    try:
        install(args.user, args.repo, args.node, args.ci_runner)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
