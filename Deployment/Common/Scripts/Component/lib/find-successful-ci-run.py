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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ci_payload_receipt import (  # noqa: E402
    ReceiptError,
    download_job_logs,
    expected_final_identity,
    receipts_from_step_log,
    select_receipt,
)


API_ROOT = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
API_VERSION = "2026-03-10"
ALLOWED_EVENTS = {"push", "workflow_dispatch"}
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
PAYLOAD_RECEIPT_STEP = "Emit immutable release payload receipt"


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
    if result.get("outcome") not in {"success", "legacy_artifact"} or not isinstance(selected, dict):
        return result
    payload_receipt = result.get("payload_receipt")
    legacy_artifact = result.get("outcome") == "legacy_artifact"
    legacy_diagnostic = result.get("diagnostic")
    direct = select_ci_run([current], target_sha, workflow_file, str(selected["id"]),
                           str(selected["run_attempt"]), repository)
    if direct["outcome"] == "no_eligible_run":
        return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Exact CI run metadata is not trusted main provenance."}
    if direct["outcome"] == "success" and legacy_artifact:
        direct["outcome"] = "legacy_artifact"
        direct["transport"] = "actions-artifact"
        direct["diagnostic"] = legacy_diagnostic
    if direct["outcome"] == "success" and isinstance(payload_receipt, dict):
        direct["payload_receipt"] = payload_receipt
    return direct



def verify_publishing_job(result: dict[str, object], jobs: object) -> dict[str, object]:
    """Overall success is insufficient when the publishing job was skipped."""
    if result.get("outcome") != "success":
        return result
    selected = result["selected"]
    if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        return {"schema_version": 1, "outcome": "invalid_provenance",
                "diagnostic": "Publishing-job metadata is malformed."}
    publishing = [job for job in jobs if job.get("name") == "build-test-push"]
    # On main, ci.yml's publish-main job is named build-test-push. Validation
    # is a separate job named validate, so it cannot substitute for publishing.
    if len(publishing) != 1:
        return {"schema_version": 1, "outcome": "invalid_provenance",
                "diagnostic": "Expected exactly one publish-main (build-test-push) job."}
    job = publishing[0]
    if (job.get("run_id") != selected["id"]
            or job.get("run_attempt") != selected["run_attempt"]
            or job.get("head_sha") != selected["head_sha"]):
        return {"schema_version": 1, "outcome": "invalid_provenance",
                "diagnostic": "Publishing job does not match the selected CI run, attempt and commit."}
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        return {"schema_version": 1, "outcome": "failed", "selected": selected,
                "diagnostic": "Selected CI attempt has no successful publish-main job."}
    return result


def verify_payload_receipt(
    result: dict[str, object],
    jobs: object,
    *,
    repository: str,
    token: str,
    profile: str,
    acceptance_profile: str | None,
    runtime: str,
    app_image: str,
) -> dict[str, object]:
    """Bind the selected final payload digest to its successful publisher step log."""
    if result.get("outcome") != "success":
        return result
    selected = result.get("selected")
    if not isinstance(selected, dict):
        return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Selected CI metadata is malformed."}
    if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Publishing-job metadata is malformed."}
    publisher_jobs = [job for job in jobs if job.get("name") == "build-test-push"]
    if len(publisher_jobs) != 1:
        return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Expected exactly one publisher job for payload receipt lookup."}
    job = publisher_jobs[0]
    if (str(job.get("run_id", "")) != str(selected.get("id", ""))
            or str(job.get("run_attempt", "")) != str(selected.get("run_attempt", ""))
            or str(job.get("head_sha", "")).lower() != str(selected.get("head_sha", "")).lower()):
        return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Publisher job identity does not match the selected CI attempt."}
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        return {"schema_version": 1, "outcome": "failed", "selected": selected,
                "diagnostic": "Selected CI attempt has no successful publisher job."}
    steps = job.get("steps")
    if not isinstance(steps, list) or any(not isinstance(step, dict) for step in steps):
        return {"schema_version": 1, "outcome": "invalid_provenance", "diagnostic": "Publisher-job step metadata is malformed."}
    if not any(step.get("name") == PAYLOAD_RECEIPT_STEP for step in steps):
        return {
            **result,
            "outcome": "legacy_artifact",
            "transport": "actions-artifact",
            "diagnostic": "The selected successful CI attempt predates immutable payload receipts.",
        }
    job_id = job.get("id", job.get("databaseId"))
    try:
        numeric_job_id = int(job_id)
        if numeric_job_id <= 0:
            raise ValueError("not positive")
        logs = download_job_logs(repository, numeric_job_id, token, api_root=API_ROOT)
        records = receipts_from_step_log(
            job,
            logs,
            step_name=PAYLOAD_RECEIPT_STEP,
            expected_job_name="build-test-push",
            expected_run_id=str(selected["id"]),
            expected_run_attempt=str(selected["run_attempt"]),
            expected_sha=str(selected["head_sha"]),
        )
        expected = expected_final_identity(
            repository=f"https://github.com/{repository}",
            commit_sha=str(selected["head_sha"]),
            run_id=str(selected["id"]),
            run_attempt=str(selected["run_attempt"]),
            profile=profile,
            acceptance_profile=acceptance_profile,
            runtime=runtime,
            app_image=app_image,
        )
        receipt = select_receipt(records, expected)
    except (KeyError, TypeError, ValueError, ReceiptError) as error:
        return {
            "schema_version": 1,
            "outcome": "invalid_provenance",
            "selected": selected,
            "diagnostic": f"Selected CI attempt has no valid final payload receipt: {error}",
        }
    return {**result, "payload_receipt": receipt}


def get_attempt_jobs(repo: str, run_id: int, attempt: int, token: str) -> list[object]:
    jobs = []
    for page in range(1, 101):
        payload = github_get(
            f"/repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page={page}", token)
        page_jobs = payload.get("jobs")
        if not isinstance(page_jobs, list):
            fail("unexpected workflow jobs response")
        jobs.extend(page_jobs)
        if len(page_jobs) < 100:
            return jobs
    fail("CI job history exceeds the safe pagination limit")


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
    parser.add_argument("--jobs-json-file", type=Path, help="exact-attempt jobs response for offline publishing verification")
    parser.add_argument("--token-file", type=Path, help="read GitHub API credentials from a protected temporary file")
    parser.add_argument("--read-final-payload-receipt", action="store_true",
                        help="read the final payload digest from the exact successful publisher-step log")
    parser.add_argument("--payload-profile", help="expected release frontend profile")
    parser.add_argument("--payload-acceptance-profile", help="expected release acceptance profile")
    parser.add_argument("--payload-runtime", help="expected migration bundle runtime")
    parser.add_argument("--payload-app-image", help="expected application image path from release settings")
    parser.add_argument("--json", action="store_true", help="emit one structured outcome object")
    args = parser.parse_args()
    repo = args.repository.strip()
    sha = args.target_sha.strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if args.token_file is not None:
        try:
            file_token = args.token_file.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as error:
            fail(f"GitHub token file is unavailable: {error}")
        if not file_token or (token and token != file_token):
            fail("GitHub token file is empty or conflicts with GITHUB_TOKEN")
        token = file_token
    workflow_file = args.workflow_file.strip()
    expected_run_id = args.expected_run_id.strip()
    expected_run_attempt = args.expected_run_attempt.strip()
    receipt_options = (args.payload_profile, args.payload_acceptance_profile, args.payload_runtime, args.payload_app_image)
    if args.read_final_payload_receipt:
        if not all(receipt_options):
            fail("final payload receipt lookup requires --payload-profile, --payload-runtime, and --payload-app-image")
        if not args.json:
            fail("final payload receipt lookup requires --json so the selected digest is preserved")
        if not token:
            fail("GITHUB_TOKEN is required to read the exact publisher job logs")
        if any(path is not None for path in (args.runs_json_file, args.current_run_json_file, args.jobs_json_file)):
            fail("final payload receipt lookup requires fresh authenticated run and job metadata")
    elif any(receipt_options):
        fail("payload receipt identity options require --read-final-payload-receipt")
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
    if result["outcome"] == "success":
        if args.jobs_json_file is not None:
            try:
                payload = json.loads(args.jobs_json_file.read_text(encoding="utf-8"))
                jobs = payload.get("jobs") if isinstance(payload, dict) else payload
            except (OSError, json.JSONDecodeError) as exc:
                fail(f"workflow-job input is unavailable or malformed: {exc}")
        elif args.runs_json_file is not None:
            fail("offline CI provenance requires --jobs-json-file")
        else:
            selected = result["selected"]
            jobs = get_attempt_jobs(repo, selected["id"], selected["run_attempt"], token)
        result = verify_publishing_job(result, jobs)
        if result["outcome"] == "success" and args.read_final_payload_receipt:
            result = verify_payload_receipt(
                result,
                jobs,
                repository=repo,
                token=token,
                profile=args.payload_profile,
                acceptance_profile=args.payload_acceptance_profile,
                runtime=args.payload_runtime,
                app_image=args.payload_app_image,
            )
        # A rerun beginning during job or receipt verification invalidates frozen evidence.
        if result["outcome"] in {"success", "legacy_artifact"} and args.runs_json_file is None:
            current = github_get(f"/repos/{repo}/actions/runs/{result['selected']['id']}", token)
            result = verify_current_run(result, current, repo, sha, workflow_file)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    elif result["outcome"] in {"success", "legacy_artifact"}:
        selected = result["selected"]
        print(selected["id"])
        return 0
    else:
        fail(str(result.get("diagnostic", result["outcome"])))
    if result["outcome"] in {"success", "legacy_artifact"}:
        return 0
    if result["outcome"] in ("waiting", "no_eligible_run", "selected_run_changed", "selected_attempt_changed"):
        return 75
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
