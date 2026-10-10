"""Read-only setup state machine. Only next-step performs agent-authorized actions."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid

from bootstrap import VERSION
from ls_settings import ETC, ROOT, TARGET, command, read_yaml, settings
from machine import detect, valid_hostname, validate
from platform_check import native


def gh_binary():
    return shutil.which("gh") or str(Path.home() / ".local/share/localsinglenode-tools/bin/gh")


def gh(*args):
    return command(gh_binary(), *args)


def repository():
    origin = command("git", "-C", str(ROOT), "remote", "get-url", "origin")
    match = re.fullmatch(r"(?:https://github.com/|git@github.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?", origin)
    if not match:
        raise ValueError("origin must identify a GitHub repository")
    return match[1]


def state_path(node):
    import hashlib
    key = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
    return Path.home() / ".local/share/localsinglenode-setup" / key / (node + ".json")


def choose(checks, node, app, facts, repo, ci_runner):
    done = []
    next_command = shlex.join(["bash", str(TARGET / "Scripts/setup-next-step.sh"), "--node", node, "--action"])
    order = ["platform", "repo", "tools", "gh", "machine"]
    # A one-PC fork needs the runner before its customization PR can pass CI.
    if checks.get("ci_capacity"):
        order += ["fork", "ci"]
    order += ["root", "variables", "runner"]
    if not checks.get("ci_capacity"):
        order += ["fork", "ci"]
    order += ["deploy", "verify"]
    for step in order:
        if checks[step]:
            done.append(step)
            continue
        actor, summary, action, message = "agent", "Complete " + step, next_command + " " + step, ""
        if step == "platform":
            actor, action, message = "human", "", "Move setup to the intended native Linux deployment PC. Windows and WSL are unsupported."
        elif step == "repo" and checks.get("repo_human"):
            actor, action, message = "human", "", "Commit or remove your local changes, or resolve the divergent main branch. Preserve other work."
        elif step == "gh":
            actor = "human"
            action = shlex.join([gh_binary(), "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web"])
            message = "Authenticate using an account with admin permission on this repository. Never send a password or token to the agent."
        elif step == "machine":
            actor, action, message = "human", "", checks.get("machine_error") or "Connect this PC to the LAN and inspect its IPv4 default route."
        elif step == "root":
            actor = "human"
            action = shlex.join(["sudo", "bash", str(TARGET / "Scripts/bootstrap-node.sh"), "--node", node, "--user", facts["install_user"], "--github-login", checks["login"], "--expected-address", facts["ip"], "--yes"] + (["--ci-runner"] if ci_runner else []))
            message = f"Native host: {facts['name']}; detected LAN address: {facts['ip']}. Confirm this is the intended deployment PC, then run this one command yourself."
        elif step == "ci" and checks.get("ci_missing"):
            actor, action, message = "human", "", "No main push CI run exists. Create the fork's initial main push through the repository's normal import/PR process; workflow_dispatch cannot supply release provenance."
        elif step == "deploy" and checks.get("deploy_ambiguous"):
            actor, action, message = "human", "", "A deployment dispatch was recorded but its run ID is unresolved. Inspect Actions; do not dispatch again."
        return {"step": step, "actor": actor, "summary": summary, "command": action, "human_message": message, "done": done, "ci_runner": ci_runner, "repo": repo, "facts": facts}, 20 if actor == "human" else 10
    port = settings()["lan_http_port"]
    url = checks.get("public_url") or f"http://{facts['ip']}:{port}/"
    return {"step": "done", "actor": "none", "summary": "Setup complete: " + url, "command": "", "human_message": "Run independent acceptance from the main PC; public setup also requires real browser verification. Keep a fixed DHCP reservation.", "done": done, "repo": repo, "facts": facts}, 0


def status(node, expected_address=None):
    checks = {key: False for key in ("platform", "repo", "tools", "gh", "machine", "fork", "ci", "root", "variables", "runner", "deploy", "verify")}
    facts, repo, app, ci_runner = {}, "", "", False
    checks["platform"] = native()
    if not checks["platform"]:
        return choose(checks, node, app, facts, repo, ci_runner)
    config = settings()
    app = config["app_name"]
    repo = repository()
    dirty = bool(command("git", "-C", str(ROOT), "status", "--porcelain"))
    branch = command("git", "-C", str(ROOT), "branch", "--show-current")
    head = command("git", "-C", str(ROOT), "rev-parse", "HEAD")
    main = command("git", "-C", str(ROOT), "rev-parse", "origin/main")
    checks["repo"] = not dirty and branch == "main" and head == main
    ancestry = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", "main", "origin/main"], capture_output=True, check=False)
    checks["repo_human"] = dirty or ancestry.returncode != 0
    if not checks["repo"]:
        return choose(checks, node, app, facts, repo, ci_runner)
    checks["tools"] = Path(gh_binary()).is_file() if '/' in gh_binary() else bool(shutil.which(gh_binary()))
    if not checks["tools"]:
        return choose(checks, node, app, facts, repo, ci_runner)
    try:
        gh("auth", "status")
        checks["gh"] = gh("api", f"repos/{repo}", "--jq", ".permissions.admin") == "true"
    except ValueError:
        checks["gh"] = False
    if not checks["gh"]:
        return choose(checks, node, app, facts, repo, ci_runner)
    checks["login"] = gh("api", "user", "--jq", ".login")
    try:
        previous = ETC / "localsinglenode/machine.yml"
        override = TARGET / "machine.yml"
        facts = validate(read_yaml(override, node=True)) if override.exists() else detect(previous if previous.exists() else None)
        if expected_address and facts["ip"] != expected_address:
            raise ValueError("Detected address differs from the operator-provided target; stop before bootstrap")
        checks["machine"] = True
    except (ValueError, OSError) as error:
        checks["machine"] = False
        checks["machine_error"] = str(error)
    if not checks["machine"]:
        return choose(checks, node, app, facts, repo, ci_runner)
    variables = {value["name"]: value["value"] for value in json.loads(gh("api", f"repos/{repo}/actions/variables?per_page=100"))["variables"]}
    runners = json.loads(gh("api", f"repos/{repo}/actions/runners?per_page=100"))["runners"]
    ci_label = variables.get("CI_RUNNER_LABEL") or variables.get("LOCALCLUSTER_RUNNER_LABEL") or "localcluster-books"
    checks["ci_capacity"] = any(runner["status"] == "online" and ci_label in {label["name"] for label in runner["labels"]} for runner in runners)
    marker_path = ETC / "localsinglenode/bootstrap.json"
    host_marker = json.loads(marker_path.read_text()) if marker_path.exists() else {}
    marker = host_marker.get("apps", {}).get(app, host_marker)
    # An offline existing CI runner is not permission to move CI to this node.
    ci_registered = any(ci_label in {label["name"] for label in runner["labels"]} for runner in runners)
    ci_runner = bool(marker.get("ci_runner")) or not ci_registered
    checks["root"] = marker.get("version") == VERSION and marker.get("node") == node and marker.get("app") == app and marker.get("repo") == repo
    if checks["root"]:
        checks["root"] = subprocess.run(["bash", str(TARGET / "Scripts/doctor.sh"), "--json"], capture_output=True, check=False).returncode == 0
    targets = [value.strip() for value in variables.get("DEPLOY_TARGETS", "").split(',')]
    checks["variables"] = "localsinglenode" in targets and variables.get("LOCALSINGLENODE_HOST") == node and (not ci_runner or (variables.get("CI_RUNNER_LABEL") == "ci-" + app and variables.get("CI_RUNNER_HOST") == node))
    checks["runner"] = any(runner["name"] == node + "-" + app and runner["status"] == "online" and "localsinglenode-" + app in {label["name"] for label in runner["labels"]} for runner in runners)
    release = read_yaml(ROOT / "Deployment/Common/release.yml")
    checks["fork"] = release["app_image"].split('/')[1].lower() == repo.split('/')[0].lower()
    ci_runs = json.loads(gh("run", "list", "--repo", repo, "--workflow", "ci.yml", "--commit", main, "--event", "push", "--json", "databaseId,status,conclusion", "--limit", "100"))
    checks["ci_missing"] = not ci_runs
    for run in ci_runs:
        if run["status"] == "completed" and run["conclusion"] == "success":
            jobs = json.loads(gh("run", "view", str(run["databaseId"]), "--repo", repo, "--json", "jobs"))["jobs"]
            checks["ci"] = all(any(job["name"] == name and job["conclusion"] == "success" for job in jobs) for name in ("validate", "build-test-push"))
            if checks["ci"]:
                break
    deploy_runs = json.loads(gh("run", "list", "--repo", repo, "--workflow", "cd-localsinglenode.yml", "--event", "workflow_dispatch", "--json", "databaseId,status,conclusion,displayTitle", "--limit", "100"))
    checks["deploy"] = any(run["status"] == "completed" and run["conclusion"] == "success" and run["displayTitle"] == "CD LocalSingleNode @ " + main for run in deploy_runs)
    public_host = variables.get("LOCALSINGLENODE_PUBLIC_HOSTNAME", "")
    public_state = ETC / app / "public.json"
    if public_host:
        public_port = int(variables.get("LOCALSINGLENODE_PUBLIC_ORIGIN_PORT") or "8085")
        public_id = variables.get("LOCALSINGLENODE_PUBLIC_TUNNEL_ID", "")
        labels = public_host.split(".")
        valid_host = len(public_host) <= 253 and public_host == public_host.lower() and len(labels) >= 2 and all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
        )
        try:
            valid_tunnel_id = str(uuid.UUID(public_id)) == public_id
        except (ValueError, TypeError, AttributeError):
            valid_tunnel_id = False
        if not valid_host or not valid_tunnel_id:
            raise ValueError("Invalid public deployment repository variables")
        checks["public_url"] = "https://" + public_host + "/"
        public = json.loads(public_state.read_text()) if public_state.exists() else {}
        checks["deploy"] = checks["deploy"] and public.get("hostname") == public_host and public.get("tunnel_id") == public_id and public.get("origin_port") == public_port
    elif public_state.exists():
        raise ValueError("Published node has missing public repository variables; restore them or follow explicit removal")
    record_path = state_path(node)
    record = json.loads(record_path.read_text()) if record_path.exists() else {}
    checks["deploy_ambiguous"] = record.get("sha") == main and bool(record.get("dispatch_pending")) and not record.get("run_id")
    checks["verify"] = record.get("verified_sha") == main and record.get("verified_address") == facts["ip"] and record.get("verified_port") == config["lan_http_port"] and record.get("verified_public", "") == checks.get("public_url", "")
    return choose(checks, node, app, facts, repo, ci_runner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", required=True)
    parser.add_argument("--expected-address")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if not valid_hostname(args.node):
            raise ValueError("Invalid node name")
        result, code = status(args.node, args.expected_address)
        print(json.dumps(result) if args.json else "\n".join(result[key] for key in ("summary", "human_message", "command") if result[key]))
        sys.exit(code)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({"step": "error", "actor": "human", "summary": str(error), "command": "", "human_message": "Inspect the failed read-only check", "done": []}))
        sys.exit(1)
