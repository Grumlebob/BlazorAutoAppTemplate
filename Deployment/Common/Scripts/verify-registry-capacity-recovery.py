#!/usr/bin/env python3
"""Authorize only coordinated cleanup after exact-main validation and capacity failure.

This does not admit a release. Full successful exact-SHA CI remains mandatory for
publication consumers and deployment. Normal maintenance keeps its existing gate.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timedelta
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
LIB = Path(__file__).resolve().parent / "Component/lib"
sys.path.insert(0, str(LIB))
from ci_payload_receipt import download_job_logs

SPEC = importlib.util.spec_from_file_location("capacity_recovery_ci_finder", LIB / "find-successful-ci-run.py")
finder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(finder)

CAPACITY_STEP = "Check registry deletion reservation before publication"
PUBLICATION_STEPS = {
    "Build Docker image", "Docker smoke and browser smoke", "Login to GHCR",
    "Tag Docker image for release", "Push Docker image",
    "Resolve pushed image digest and write release manifest", "Publish additional frontend",
    "Emit immutable release payload receipt",
}
SAFE_TAIL = {
    "Remove this run's build tag", "Report runner capacity", "Store CI reports on this runner",
    "Post Setup .NET", "Post Checkout", "Complete job",
}
CAPACITY_ERRORS = {
    "an unresolved GHCR deletion reservation blocks payload selection",
}
LOCK_TIMEOUT = "timed out waiting for LocalCluster deployment lock: /tmp/localcluster-deploy.lockdir"
CAPACITY_SOURCE_FILES = (
    "Deployment/Common/Scripts/Component/lib/registry_retention.py",
    "Deployment/Common/Scripts/Component/lib/registry_inventory.py",
)


def timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("capacity failure timestamps are unavailable")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _verify_failed_capacity_gate(run, jobs, *, repository, sha, run_id, attempt):
    expected = {"id": run_id, "run_attempt": attempt, "head_sha": sha, "event": "push",
                "head_branch": "main", "path": ".github/workflows/ci.yml",
                "status": "completed", "conclusion": "failure"}
    if (not isinstance(run, dict) or any(run.get(key) != value for key, value in expected.items())
            or not isinstance(run.get("repository"), dict) or not isinstance(run.get("head_repository"), dict)
            or run["repository"].get("full_name") != repository
            or run["head_repository"].get("full_name") != repository):
        raise ValueError("require the exact failed main-push CI run and attempt")
    if (not isinstance(jobs, list) or not jobs or any(not isinstance(job, dict) for job in jobs)
            or any(job.get("status") != "completed" for job in jobs)
            or any(job.get("run_id") != run_id or job.get("run_attempt") != attempt
                   or job.get("head_sha") != sha for job in jobs)):
        raise ValueError("exact-attempt CI jobs are incomplete or changed")
    identities = [job.get("id") for job in jobs]
    if any(type(value) is not int or value < 1 for value in identities) or len(set(identities)) != len(identities):
        raise ValueError("CI job identities are invalid or duplicated")
    validation = [job for job in jobs if job.get("name") == "validate"]
    publishers = [job for job in jobs if job.get("name") == "build-test-push"]
    if (len(validation) != 1 or validation[0].get("conclusion") != "success"
            or len(publishers) != 1 or publishers[0].get("conclusion") != "failure"
            or any(job.get("conclusion") not in {"success", "skipped"}
                   for job in jobs if job not in publishers)):
        raise ValueError("exact-main validation must pass and only publication may fail")
    steps = publishers[0].get("steps")
    if (not isinstance(steps, list) or not steps or any(not isinstance(step, dict) for step in steps)
            or any(step.get("status") != "completed" for step in steps)):
        raise ValueError("publisher step inventory is incomplete")
    numbers = [step.get("number") for step in steps]
    names = [step.get("name") for step in steps]
    if (any(type(number) is not int or number < 1 for number in numbers)
            or numbers != sorted(set(numbers)) or any(not isinstance(name, str) for name in names)
            or len(names) != len(set(names))):
        raise ValueError("publisher steps are unordered or duplicated")
    failures = [step for step in steps if step.get("conclusion") == "failure"]
    if len(failures) != 1 or failures[0].get("name") != CAPACITY_STEP:
        raise ValueError("only the prepublication registry reservation check may fail")
    gate = failures[0]
    if not PUBLICATION_STEPS.issubset(names):
        raise ValueError("publisher publication steps are missing")
    for step in steps:
        if step is gate:
            continue
        conclusion = step.get("conclusion")
        if conclusion not in {"success", "skipped"}:
            raise ValueError("unexpected publisher step result")
        if step["name"] in PUBLICATION_STEPS and (step["number"] < gate["number"] or conclusion != "skipped"):
            raise ValueError("a publication/build step ran before capacity recovery")
        if step["number"] > gate["number"] and conclusion != "skipped" and step["name"] not in SAFE_TAIL:
            raise ValueError("unreviewed publisher activity followed capacity failure")
    return validation[0], publishers[0], gate


def _log_entries(log):
    if not isinstance(log, str):
        raise ValueError("capacity failure log is unavailable")
    for line in log.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[0].endswith("Z"):
            try:
                observed = timestamp(parts[0])
            except ValueError:
                continue
            yield observed, parts[1]


def verify_capacity_failure(run, jobs, log, *, repository, sha, run_id, attempt):
    validation, publisher, gate = _verify_failed_capacity_gate(
        run, jobs, repository=repository, sha=sha, run_id=run_id, attempt=attempt,
    )
    start, end = timestamp(gate.get("started_at")), timestamp(gate.get("completed_at"))
    if end < start:
        raise ValueError("capacity failure log window is invalid")
    matched = []
    for observed, message in _log_entries(log):
        prefix = "Registry retention failed closed; no unverified deletion was attempted: "
        if message.startswith(prefix) and message[len(prefix):] in CAPACITY_ERRORS:
            if start <= observed < end + timedelta(seconds=1):
                matched.append(message[len(prefix):])
    if len(matched) != 1:
        raise ValueError("require the exact capacity error inside the failed step's log window")
    return {"outcome": "capacity_cleanup_only", "operation_source_sha": sha,
            "validated_code_sha": sha, "ci_run_id": run_id, "ci_run_attempt": attempt,
            "validation_job_id": validation["id"], "publisher_job_id": publisher["id"],
            "capacity_error": matched[0], "release_authorized": False}


def verify_lock_blocked_failure(
    run, jobs, log, *, repository, sha, run_id, attempt, reservation_run_id, reservation_attempt,
):
    _, _, gate = _verify_failed_capacity_gate(
        run, jobs, repository=repository, sha=sha, run_id=run_id, attempt=attempt,
    )
    start, end = timestamp(gate.get("started_at")), timestamp(gate.get("completed_at"))
    if end < start:
        raise ValueError("lock failure log window is invalid")
    timed_out = []
    owners = []
    owner_pattern = re.compile(
        rf"lock owner: (?P<host>[A-Za-z0-9_.-]+):pid=(?P<pid>[1-9][0-9]*):"
        rf"repo={re.escape(repository)}:run={reservation_run_id}-{reservation_attempt}:"
        r"started=(?P<started>[0-9T:.-]+Z)"
    )
    for observed, message in _log_entries(log):
        if not start <= observed < end + timedelta(seconds=1):
            continue
        if message == LOCK_TIMEOUT:
            timed_out.append(observed)
        match = owner_pattern.fullmatch(message)
        if match:
            timestamp(match.group("started"))
            owners.append({
                "host": match.group("host"),
                "pid": int(match.group("pid")),
                "run_id": reservation_run_id,
                "run_attempt": reservation_attempt,
            })
    if len(timed_out) != 1 or len(owners) != 1:
        raise ValueError("the exact publisher gate must be blocked by the pending reservation lock")
    return {
        "outcome": "reservation_lock_blocked",
        "blocked_ci_run_id": run_id,
        "blocked_ci_run_attempt": attempt,
        "lock_owner": owners[0],
    }


def _git_show(sha, path):
    return subprocess.check_output(["git", "show", f"{sha}:{path}"], cwd=ROOT, text=True)


def _capacity_step_source(sha):
    text = _git_show(sha, ".github/workflows/ci.yml")
    marker = f"      - name: {CAPACITY_STEP}"
    starts = [match.start() for match in re.finditer(rf"^{re.escape(marker)}\r?$", text, re.MULTILINE)]
    if len(starts) != 1:
        raise ValueError("the exact CI capacity step is missing or duplicated")
    start = starts[0]
    following = re.search(r"^      - name: ", text[start + len(marker):], re.MULTILINE)
    end = start + len(marker) + following.start() if following else len(text)
    return text[start:end].rstrip()


def _capacity_calls(sha):
    source = _git_show(sha, "Deployment/Common/Scripts/registry-retention.py")
    tree = ast.parse(source)
    run_function = next((item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and item.name == "run"), None)
    if run_function is None:
        raise ValueError("registry retention capacity entry point is missing")
    guards = [ast.dump(node, include_attributes=False) for node in ast.walk(run_function)
              if isinstance(node, ast.If)
              and isinstance(node.test, ast.Attribute) and node.test.attr == "assert_clear"
              and isinstance(node.test.value, ast.Name) and node.test.value.id == "args"]
    if not guards:
        raise ValueError("registry deletion reservation guard is missing")
    return sorted(guards)


def verify_capacity_source_continuity(prior_sha, current_sha):
    if not re.fullmatch(r"[0-9a-f]{40}", prior_sha) or not re.fullmatch(r"[0-9a-f]{40}", current_sha):
        raise ValueError("capacity proof source identities are invalid")
    if subprocess.run(["git", "merge-base", "--is-ancestor", prior_sha, current_sha], cwd=ROOT,
                      check=False).returncode != 0:
        raise ValueError("the prior capacity proof is not on current main history")
    if _capacity_step_source(prior_sha) != _capacity_step_source(current_sha):
        raise ValueError("the current publisher capacity step differs from the proved step")
    if _capacity_calls(prior_sha) != _capacity_calls(current_sha):
        raise ValueError("the registry capacity check differs from the proved implementation")
    for path in CAPACITY_SOURCE_FILES:
        if _git_show(prior_sha, path) != _git_show(current_sha, path):
            raise ValueError("the registry capacity inventory or policy changed after the prior proof")


def verify_reservation_run(run, *, repository, prior_sha, run_id, attempt):
    expected = {"id": run_id, "run_attempt": attempt, "head_sha": prior_sha,
                "event": "workflow_dispatch", "head_branch": "main",
                "path": ".github/workflows/registry-retention.yml",
                "status": "completed", "conclusion": "failure"}
    if (not isinstance(run, dict) or any(run.get(key) != value for key, value in expected.items())
            or not isinstance(run.get("repository"), dict) or not isinstance(run.get("head_repository"), dict)
            or run["repository"].get("full_name") != repository
            or run["head_repository"].get("full_name") != repository):
        raise ValueError("the pending reservation must belong to its exact failed trusted workflow run")


def verify_lock_blocked_recovery(
    current_run, current_jobs, current_log, prior_run, prior_jobs, prior_log, reservation_run,
    *, repository, current_sha, current_run_id, current_attempt,
    prior_run_id, prior_attempt, reservation_run_id, reservation_attempt,
):
    prior_sha = prior_run.get("head_sha") if isinstance(prior_run, dict) else None
    blocked_sha = current_run.get("head_sha") if isinstance(current_run, dict) else None
    if not isinstance(prior_sha, str):
        raise ValueError("the prior capacity proof source SHA is unavailable")
    if not isinstance(blocked_sha, str):
        raise ValueError("the lock-blocked CI source SHA is unavailable")
    prior_result = verify_capacity_failure(
        prior_run, prior_jobs, prior_log, repository=repository, sha=prior_sha,
        run_id=prior_run_id, attempt=prior_attempt,
    )
    verify_capacity_source_continuity(prior_sha, blocked_sha)
    verify_capacity_source_continuity(blocked_sha, current_sha)
    verify_reservation_run(
        reservation_run, repository=repository, prior_sha=prior_sha,
        run_id=reservation_run_id, attempt=reservation_attempt,
    )
    blocked_result = verify_lock_blocked_failure(
        current_run, current_jobs, current_log, repository=repository, sha=blocked_sha,
        run_id=current_run_id, attempt=current_attempt,
        reservation_run_id=reservation_run_id, reservation_attempt=reservation_attempt,
    )
    prior_updated = timestamp(prior_run.get("updated_at"))
    reservation_created = timestamp(reservation_run.get("created_at"))
    current_created = timestamp(current_run.get("created_at"))
    if not prior_updated <= reservation_created <= current_created:
        raise ValueError("capacity proof, reservation owner and lock-blocked CI are out of order")
    return {
        "outcome": "capacity_cleanup_only",
        "capacity_error": prior_result["capacity_error"],
        "capacity_proof_run_id": prior_run_id,
        "capacity_proof_run_attempt": prior_attempt,
        "capacity_proof_sha": prior_sha,
        "validated_code_sha": current_sha,
        "ci_run_id": current_run_id,
        "ci_run_attempt": current_attempt,
        "reservation_run_id": reservation_run_id,
        "reservation_run_attempt": reservation_attempt,
        "lock_owner": blocked_result["lock_owner"],
        "release_authorized": False,
    }


def attempt_jobs(repo, run_id, attempt, token):
    jobs, total = [], None
    for page in range(1, 101):
        value = finder.github_get(
            f"/repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page={page}", token)
        rows, count = value.get("jobs"), value.get("total_count")
        if (not isinstance(rows, list) or len(rows) > 100 or type(count) is not int or count < 1
                or total is not None and count != total):
            raise ValueError("CI job pagination is incomplete or changed")
        total = count
        jobs.extend(rows)
        if len(rows) < 100:
            if len(jobs) != total:
                raise ValueError("CI job inventory is incomplete")
            return jobs
    raise ValueError("CI job pagination exceeds the safe bound")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument("--prior-capacity-run-id", type=int)
    parser.add_argument("--prior-capacity-attempt", type=int)
    parser.add_argument("--reservation-run-id", type=int)
    parser.add_argument("--reservation-attempt", type=int)
    args = parser.parse_args()
    sha = os.environ.get("GITHUB_SHA", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if (args.run_id < 1 or args.attempt < 1 or not re.fullmatch("[0-9a-f]{40}", sha)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not token
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or os.environ.get("GITHUB_WORKFLOW_REF") != repo + "/.github/workflows/registry-retention.yml@refs/heads/main"
            or os.environ.get("REGISTRY_RETENTION_APPLY") not in {"true", "false"}
            or os.environ.get("GIT_DIR") or os.environ.get("GIT_WORK_TREE")):
        raise ValueError("require explicit capacity recovery in the trusted manual registry workflow")
    prior_values = (args.prior_capacity_run_id, args.prior_capacity_attempt)
    reservation_values = (args.reservation_run_id, args.reservation_attempt)
    blocked_recovery = any(value is not None for value in prior_values)
    if (blocked_recovery and (any(value is None or value < 1 for value in prior_values)
                              or any(value is None or value < 1 for value in reservation_values)
                              or os.environ.get("REGISTRY_RETENTION_APPLY") != "true")
            or not blocked_recovery and any(value is not None for value in reservation_values)):
        raise ValueError("lock-blocked recovery requires paired prior capacity and exact reservation identities")
    for arguments, expected in ((["rev-parse", "HEAD"], sha), (["rev-parse", "--is-shallow-repository"], "false")):
        if subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip() != expected:
            raise ValueError("require the exact trusted main checkout with complete history")
    endpoint = f"/repos/{repo}/actions/runs/{args.run_id}"
    run = finder.github_get(endpoint, token)
    jobs = attempt_jobs(repo, args.run_id, args.attempt, token)
    publishers = [job for job in jobs if isinstance(job, dict) and job.get("name") == "build-test-push"]
    if len(publishers) != 1:
        raise ValueError("require exactly one failed publisher job")
    log = download_job_logs(repo, publishers[0].get("id"), token, api_root=finder.API_ROOT)
    if blocked_recovery:
        prior_endpoint = f"/repos/{repo}/actions/runs/{args.prior_capacity_run_id}"
        reservation_endpoint = f"/repos/{repo}/actions/runs/{args.reservation_run_id}"
        prior_run = finder.github_get(prior_endpoint, token)
        prior_jobs = attempt_jobs(repo, args.prior_capacity_run_id, args.prior_capacity_attempt, token)
        prior_publishers = [job for job in prior_jobs
                            if isinstance(job, dict) and job.get("name") == "build-test-push"]
        if len(prior_publishers) != 1:
            raise ValueError("require exactly one publisher in the prior capacity proof")
        prior_log = download_job_logs(repo, prior_publishers[0].get("id"), token, api_root=finder.API_ROOT)
        reservation_run = finder.github_get(reservation_endpoint, token)
        result = verify_lock_blocked_recovery(
            run, jobs, log, prior_run, prior_jobs, prior_log, reservation_run,
            repository=repo, current_sha=sha, current_run_id=args.run_id, current_attempt=args.attempt,
            prior_run_id=args.prior_capacity_run_id, prior_attempt=args.prior_capacity_attempt,
            reservation_run_id=args.reservation_run_id, reservation_attempt=args.reservation_attempt,
        )
    else:
        result = verify_capacity_failure(
            run, jobs, log, repository=repo, sha=sha, run_id=args.run_id, attempt=args.attempt,
        )
    fresh = finder.github_get(endpoint, token)
    keys = ("id", "run_attempt", "head_sha", "status", "conclusion", "updated_at")
    if (any(fresh.get(key) != run.get(key) for key in keys)
            or finder.github_get(f"/repos/{repo}/commits/main", token).get("sha") != sha):
        raise ValueError("main or its CI attempt changed during capacity recovery verification")
    if blocked_recovery:
        fresh_prior = finder.github_get(prior_endpoint, token)
        fresh_reservation = finder.github_get(reservation_endpoint, token)
        if (any(fresh_prior.get(key) != prior_run.get(key) for key in keys)
                or any(fresh_reservation.get(key) != reservation_run.get(key) for key in keys)):
            raise ValueError("prior capacity proof or reservation owner changed during recovery verification")
    result["apply_requested"] = os.environ["REGISTRY_RETENTION_APPLY"] == "true"
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError):
        print("Registry capacity recovery source proof failed; no cleanup was authorized.", file=sys.stderr)
        raise SystemExit(1)
