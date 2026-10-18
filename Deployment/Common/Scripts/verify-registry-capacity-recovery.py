#!/usr/bin/env python3
"""Authorize only coordinated cleanup after exact-main validation and capacity failure.

This does not admit a release. Full successful exact-SHA CI remains mandatory for
publication consumers and deployment. Normal maintenance keeps its existing gate.
"""
from __future__ import annotations

import argparse
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

CAPACITY_STEP = "Enforce final GHCR payload capacity before any registry publication"
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
    "payload store requires coordinated retention before publication",
    "payload publication would exceed its repository byte cap",
}


def timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("capacity failure timestamps are unavailable")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def verify_capacity_failure(run, jobs, log, *, repository, sha, run_id, attempt):
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
        raise ValueError("only the prepublication capacity gate may fail")
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
    start, end = timestamp(gate.get("started_at")), timestamp(gate.get("completed_at"))
    if end < start or not isinstance(log, str):
        raise ValueError("capacity failure log window is invalid")
    matched = []
    for line in log.splitlines():
        parts = line.split(" ", 1)
        if len(parts) != 2 or not parts[0].endswith("Z"):
            continue
        prefix = "Registry retention failed closed; no unverified deletion was attempted: "
        if parts[1].startswith(prefix) and parts[1][len(prefix):] in CAPACITY_ERRORS:
            if start <= timestamp(parts[0]) < end + timedelta(seconds=1):
                matched.append(parts[1][len(prefix):])
    if len(matched) != 1:
        raise ValueError("require the exact capacity error inside the failed step's log window")
    return {"outcome": "capacity_cleanup_only", "operation_source_sha": sha,
            "validated_code_sha": sha, "ci_run_id": run_id, "ci_run_attempt": attempt,
            "validation_job_id": validation[0]["id"], "publisher_job_id": publishers[0]["id"],
            "capacity_error": matched[0], "release_authorized": False}


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
    result = verify_capacity_failure(run, jobs, log, repository=repo, sha=sha, run_id=args.run_id, attempt=args.attempt)
    fresh = finder.github_get(endpoint, token)
    keys = ("id", "run_attempt", "head_sha", "status", "conclusion", "updated_at")
    if (any(fresh.get(key) != run.get(key) for key in keys)
            or finder.github_get(f"/repos/{repo}/commits/main", token).get("sha") != sha):
        raise ValueError("main or its CI attempt changed during capacity recovery verification")
    result["apply_requested"] = os.environ["REGISTRY_RETENTION_APPLY"] == "true"
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError):
        print("Registry capacity recovery source proof failed; no cleanup was authorized.", file=sys.stderr)
        raise SystemExit(1)
