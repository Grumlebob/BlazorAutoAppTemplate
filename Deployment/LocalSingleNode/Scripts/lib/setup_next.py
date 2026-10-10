"""Perform the next authorized unprivileged action, never the operator's root step."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from ls_settings import ROOT, TARGET, settings
from platform_check import native
from setup_status import command, gh, gh_binary, state_path, status


def save(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", required=True)
    parser.add_argument("--expected-address")
    parser.add_argument("--action", required=True, choices=("repo", "tools", "fork", "ci", "variables", "runner", "deploy", "verify"))
    args = parser.parse_args()
    if not native():
        raise ValueError("Agent node setup requires the explicitly intended native Linux PC")
    state, _ = status(args.node, args.expected_address)
    if state["actor"] != "agent" or state["step"] != args.action:
        raise ValueError("Requested action differs from the next read-only setup step")
    repo = state["repo"]
    config = settings()
    sha = command("git", "-C", str(ROOT), "rev-parse", "origin/main")
    record_path = state_path(args.node)
    record = json.loads(record_path.read_text()) if record_path.exists() else {}
    if args.action == "repo":
        run("git", "-C", str(ROOT), "fetch", "origin")
        run("git", "-C", str(ROOT), "switch", "main")
        run("git", "-C", str(ROOT), "merge", "--ff-only", "origin/main")
    elif args.action == "tools":
        run("bash", str(TARGET / "Scripts/install-agent-tools.sh"))
    elif args.action == "fork":
        print("Follow docs/HowToForkThisRepo.md now. Keep the current valid app slug unless the user requests a rename. Change the Common app_image owner to this repository owner through a PR. Run the complete local gate, require exact-head build-test-push, squash-merge and wait for main validate and publishing before returning to setup-status. Do not push directly to main. If local gate tools are missing, install user-local SDK/tools; the operator bootstrap with --ci-runner must explicitly provide Docker group access and a fresh group session first.")
    elif args.action == "variables":
        variables = {value["name"]: value["value"] for value in json.loads(gh("api", f"repos/{repo}/actions/variables?per_page=100"))["variables"]}
        targets = [value.strip() for value in variables.get("DEPLOY_TARGETS", "").split(',') if value.strip()]
        if "localsinglenode" not in targets:
            targets.append("localsinglenode")
        values = {"DEPLOY_TARGETS": ",".join(targets), "LOCALSINGLENODE_HOST": args.node, "LOCALSINGLENODE_RUNNER_LABEL": "localsinglenode-" + config["app_name"]}
        if state["ci_runner"]:
            values.update(CI_RUNNER_LABEL="ci-" + config["app_name"], CI_RUNNER_HOST=args.node)
        for name, value in values.items():
            gh("variable", "set", name, "--repo", repo, "--body", value)
            print(f"Repository variable set: {name}")
    elif args.action == "runner":
        for attempt in range(11):
            runners = json.loads(gh("api", f"repos/{repo}/actions/runners?per_page=100"))["runners"]
            if any(runner["name"] == args.node + "-" + config["app_name"] and runner["status"] == "online" and "localsinglenode-" + config["app_name"] in {label["name"] for label in runner["labels"]} for runner in runners):
                print("Runner online with the required app label")
                return
            if attempt < 10:
                time.sleep(30)
        raise ValueError("Runner did not appear within 5 minutes. Operator: run sudo systemctl status 'actions.runner.*' and inspect the service log")
    elif args.action == "ci":
        runs = json.loads(gh("run", "list", "--repo", repo, "--workflow", "ci.yml", "--commit", sha, "--event", "push", "--json", "databaseId,status,conclusion", "--limit", "100"))
        if not runs:
            raise ValueError("No main push CI run exists; dispatch cannot replace release provenance")
        active = [value for value in runs if value["status"] != "completed"]
        selected = active[0] if active else runs[0]
        run_id = str(selected["databaseId"])
        if not active:
            gh("run", "rerun", run_id, "--repo", repo)
        print("Watching existing main push CI run " + run_id, flush=True)
        run(gh_binary(), "run", "watch", run_id, "--repo", repo, "--interval", "60", "--exit-status")
    elif args.action == "deploy":
        runs = json.loads(gh("run", "list", "--repo", repo, "--workflow", "cd-localsinglenode.yml", "--event", "workflow_dispatch", "--json", "databaseId,status,conclusion,displayTitle,createdAt", "--limit", "100"))
        matching = [value for value in runs if value["displayTitle"] == "CD LocalSingleNode @ " + sha]
        if matching:
            selected = matching[0]
            run_id = str(selected["databaseId"])
            record.update(sha=sha, run_id=run_id, dispatch_pending=False)
            save(record_path, record)
            if selected["status"] == "completed" and selected["conclusion"] != "success":
                raise ValueError("Existing matching CD failed. Record its logs and fix through a PR; never dispatch a blind retry")
        else:
            if record.get("sha") == sha and record.get("dispatch_pending"):
                raise ValueError("Unresolved recorded dispatch; inspect Actions before any new dispatch")
            started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            record.update(sha=sha, dispatch_pending=True, dispatch_started=started, run_id=None)
            save(record_path, record)
            gh("workflow", "run", "cd-localsinglenode.yml", "--repo", repo, "--ref", "main", "-f", "target_sha=" + sha, "-f", "run_migrations=true")
            run_id = None
            for _ in range(10):
                time.sleep(30)
                recent = json.loads(gh("run", "list", "--repo", repo, "--workflow", "cd-localsinglenode.yml", "--event", "workflow_dispatch", "--json", "databaseId,displayTitle,createdAt", "--limit", "100"))
                matching = [value for value in recent if value["displayTitle"] == "CD LocalSingleNode @ " + sha and datetime.fromisoformat(value["createdAt"].replace("Z", "+00:00")) >= datetime.fromisoformat(started)]
                if len(matching) == 1:
                    run_id = str(matching[0]["databaseId"])
                    break
            if not run_id:
                raise ValueError("Dispatch recorded; run ID unresolved. Inspect Actions without dispatching again")
            record.update(run_id=run_id, dispatch_pending=False)
            save(record_path, record)
        print(f"CD run recorded before watching: https://github.com/{repo}/actions/runs/{run_id}", flush=True)
        run(gh_binary(), "run", "watch", run_id, "--repo", repo, "--interval", "60", "--exit-status")
    elif args.action == "verify":
        run("pwsh", "-NoProfile", "-File", str(ROOT / "Scripts/Test-DeployedSite.ps1"), "-Address", state["facts"]["ip"], "-Port", str(config["lan_http_port"]))
        record.update(verified_sha=sha, verified_address=state["facts"]["ip"], verified_port=config["lan_http_port"])
        save(record_path, record)
        print("Node acceptance passed. Main PC must run its own independent LAN check.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(str(error) if isinstance(error, ValueError) else "Agent step failed; inspect the preceding named action", file=sys.stderr)
        sys.exit(1)
