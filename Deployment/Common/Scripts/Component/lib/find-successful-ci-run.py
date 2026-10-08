#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import time


API_ROOT = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
API_VERSION = "2026-03-10"
ALLOWED_EVENTS = {"push", "workflow_dispatch"}
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def fail(message: str) -> None:
    raise SystemExit(f"CI gate failed: {message}")


def is_retryable_http_error(error: urllib.error.HTTPError) -> bool:
    if error.code in RETRYABLE_STATUSES:
        return True
    if error.code != 403:
        return False
    return (
        bool(error.headers.get("Retry-After"))
        or error.headers.get("X-RateLimit-Remaining") == "0"
    )


def github_get(path: str, token: str) -> dict[str, object]:
    for attempt in range(1, 5):
        request = urllib.request.Request(
            f"{API_ROOT}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": API_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            if not is_retryable_http_error(exc) or attempt == 4:
                fail(f"GitHub API returned HTTP {exc.code}: {details}")
            retry_after = exc.headers.get("Retry-After", "")
            try:
                delay = max(1, min(30, int(retry_after)))
            except ValueError:
                delay = min(30, attempt * 2)
            print(f"GitHub API returned retryable HTTP {exc.code}; retrying in {delay}s", file=sys.stderr)
            time.sleep(delay + random.uniform(0, min(1.0, delay / 4)))
        except urllib.error.URLError as exc:
            if attempt == 4:
                fail(f"GitHub API request failed: {exc}")
            delay = min(30, attempt * 2)
            print(f"GitHub API request failed transiently; retrying in {delay}s: {exc}", file=sys.stderr)
            time.sleep(delay + random.uniform(0, min(1.0, delay / 4)))
        except json.JSONDecodeError as exc:
            fail(f"GitHub API returned invalid JSON: {exc}")

    fail("GitHub API retry budget exhausted")


def select_ci_run(
    runs: list[object],
    target_sha: str,
    workflow_file: str,
    expected_run_id: str = "",
    expected_run_attempt: str = "",
    repository: str = "",
) -> dict[str, object]:
    """Select the newest eligible run, then judge its current attempt."""
    if isinstance(runs, list) and runs and all(
        isinstance(page, dict) and isinstance(page.get("workflow_runs"), list)
        for page in runs
    ):
        runs = [candidate for page in runs for candidate in page["workflow_runs"]]
    if not repository:
        fail("repository is required by the shared CI policy")
    target_sha = target_sha.lower()
    expected_run_id = str(expected_run_id).strip()
    expected_run_attempt = str(expected_run_attempt).strip()
    workflow_path = f".github/workflows/{workflow_file}"
    eligible: list[dict[str, object]] = []
    for candidate in runs:
        if not isinstance(candidate, dict):
            continue
        run = candidate
        run_sha = str(run.get("head_sha") or run.get("headSha") or "").lower()
        branch = run.get("head_branch", run.get("headBranch"))
        event_name = str(run.get("event") or "")
        pull_requests = run.get("pull_requests", run.get("pullRequests", []))
        path = str(run.get("path") or "")
        if (
            run_sha != target_sha
            or branch != "main"
            or event_name not in ALLOWED_EVENTS
            or not isinstance(pull_requests, list) or pull_requests
            or not isinstance(run.get("repository"), dict)
            or run["repository"].get("full_name", "").lower() != repository.lower()
        ):
            continue
        if path.split("@", 1)[0] != workflow_path:
            continue
        run_id = run.get("id", run.get("databaseId"))
        try:
            numeric_id = int(run_id)
            attempt = int(run.get("run_attempt", run.get("attempt", 0)))
        except (TypeError, ValueError):
            continue
        if numeric_id <= 0 or attempt < 1:
            continue
        created_at = str(run.get("created_at", run.get("createdAt")) or "")
        try:
            if not created_at.endswith("Z"):
                raise ValueError("not UTC")
            created_at = datetime.fromisoformat(created_at[:-1] + "+00:00").astimezone(timezone.utc).isoformat()
        except ValueError:
            return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Eligible CI run has an invalid UTC creation timestamp."}
        eligible.append(
            {
                "id": numeric_id,
                "run_attempt": attempt,
                "head_sha": run_sha,
                "head_branch": branch,
                "event": event_name,
                "status": str(run.get("status") or ""),
                "conclusion": run.get("conclusion"),
                "created_at": created_at,
                "html_url": run.get("html_url", run.get("url")),
                "path": path or workflow_path,
            }
        )

    if not eligible:
        return {
            "schema_version": 1,
            "outcome": "no_eligible_run",
            "diagnostic": f"No trusted main {workflow_file} run exists for {target_sha}.",
        }

    identities = {}
    for run in eligible:
        if run["id"] in identities and identities[run["id"]] != run:
            return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Paginated CI metadata changed for the same run; refresh the complete query."}
        identities[run["id"]] = run

    # GitHub emits ISO-8601 UTC timestamps. The numeric run ID breaks equal
    # creation-time ties deterministically; attempt is deliberately not a
    # cross-run recency key.
    selected = max(eligible, key=lambda run: (str(run["created_at"]), int(run["id"])))
    if expected_run_id and str(selected["id"]) != expected_run_id:
        return {
            "schema_version": 1,
            "outcome": "selected_run_changed",
            "selected": selected,
            "diagnostic": "The newest eligible CI run differs from frozen provenance.",
        }
    if expected_run_attempt and str(selected["run_attempt"]) != expected_run_attempt:
        return {
            "schema_version": 1,
            "outcome": "selected_attempt_changed",
            "selected": selected,
            "diagnostic": "The selected CI run has a different current attempt than frozen provenance.",
        }
    status = selected["status"]
    if status != "completed":
        return {
            "schema_version": 1,
            "outcome": "waiting",
            "selected": selected,
            "diagnostic": f"Newest eligible CI run {selected['id']} attempt {selected['run_attempt']} is {status or 'incomplete'}.",
        }
    if selected["conclusion"] != "success":
        return {
            "schema_version": 1,
            "outcome": "failed",
            "selected": selected,
            "diagnostic": f"Newest eligible CI run {selected['id']} attempt {selected['run_attempt']} concluded {selected['conclusion']!r}.",
        }
    return {"schema_version": 1, "outcome": "success", "selected": selected}


def verify_current_run(result: dict[str, object], current: dict[str, object], repository: str,
                       target_sha: str, workflow_file: str) -> dict[str, object]:
    """A list response never substitutes for the exact run's current attempt."""
    selected = result.get("selected")
    if result.get("outcome") != "success" or not isinstance(selected, dict):
        return result
    direct = select_ci_run([current], target_sha, workflow_file, str(selected["id"]),
                           str(selected["run_attempt"]), repository)
    if direct["outcome"] == "no_eligible_run":
        return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Exact CI run metadata is not trusted main provenance."}
    return direct


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Select the newest eligible main CI run for an immutable target.")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--target-sha", default=os.environ.get("TARGET_SHA", os.environ.get("GITHUB_SHA", "")))
    parser.add_argument("--workflow-file", default=os.environ.get("CI_WORKFLOW_FILE", "ci.yml"))
    parser.add_argument("--expected-run-id", default=os.environ.get("EXPECTED_CI_RUN_ID", ""))
    parser.add_argument("--expected-run-attempt", default=os.environ.get("EXPECTED_CI_RUN_ATTEMPT", ""))
    parser.add_argument("--runs-json-file", type=Path, help="select from previously queried workflow-run pages using the same eligibility policy")
    parser.add_argument("--current-run-json-file", type=Path, help="independently queried current run metadata for offline revalidation")
    parser.add_argument("--json", action="store_true", help="emit one structured outcome object")
    args = parser.parse_args()
    repo = args.repository.strip()
    sha = args.target_sha.strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    workflow_file = args.workflow_file.strip()
    expected_run_id = args.expected_run_id.strip()
    expected_run_attempt = args.expected_run_attempt.strip()
    if not repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        fail("repository must be owner/name")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        fail("target SHA must be a full 40-character commit")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.yml", workflow_file):
        fail("workflow file must be a repository workflow filename")
    if args.runs_json_file is None and not token:
        fail("GITHUB_TOKEN is not set")
    if expected_run_attempt and (not expected_run_attempt.isdigit() or int(expected_run_attempt) < 1):
        fail("--expected-run-attempt must be a positive integer")
    if expected_run_id and not expected_run_id.isdigit():
        fail("--expected-run-id must be numeric")

    if args.runs_json_file is not None:
        try:
            payload = json.loads(args.runs_json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"workflow-run input file is unavailable or malformed: {exc}")
        if not isinstance(payload, list) or any(
            not isinstance(page, dict) or not isinstance(page.get("workflow_runs"), list)
            for page in payload
        ):
            fail("workflow-run input must be a JSON array of paginated workflow response objects")
        runs = payload
    else:
        query = urllib.parse.urlencode(
            {
                "head_sha": sha,
                "exclude_pull_requests": "true",
                "per_page": "100",
            }
        )
        runs = []
        for page in range(1, 101):
            page_query = f"{query}&page={page}"
            payload = github_get(f"/repos/{repo}/actions/workflows/{workflow_file}/runs?{page_query}", token)
            page_runs = payload.get("workflow_runs")
            if not isinstance(page_runs, list):
                fail("unexpected workflow run response")
            runs.extend(page_runs)
            if len(page_runs) < 100:
                break
        else:
            fail("CI run history exceeds the safe pagination limit; selection is inconclusive")
    result = select_ci_run(runs, sha, workflow_file, expected_run_id, expected_run_attempt, repo)
    if result["outcome"] == "success":
        if args.current_run_json_file is not None:
            current = json.loads(args.current_run_json_file.read_text(encoding="utf-8"))
            result = verify_current_run(result, current, repo, sha, workflow_file)
        elif args.runs_json_file is None:
            current = github_get(f"/repos/{repo}/actions/runs/{result['selected']['id']}", token)
            result = verify_current_run(result, current, repo, sha, workflow_file)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    elif result["outcome"] == "success":
        selected = result["selected"]
        print(selected["id"])
        return 0
    else:
        fail(str(result.get("diagnostic", result["outcome"])))
    if result["outcome"] == "success":
        return 0
    if result["outcome"] in ("waiting", "no_eligible_run", "selected_run_changed", "selected_attempt_changed"):
        return 75
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
