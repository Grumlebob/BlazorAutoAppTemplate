#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


API_ROOT = "https://api.github.com"


def fail(message: str) -> None:
    raise SystemExit(f"CI gate failed: {message}")


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        fail(f"{name} is not set")
    return value


def github_get(path: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        fail(f"GitHub API returned HTTP {exc.code}: {details}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API request failed: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"GitHub API returned invalid JSON: {exc}")


def main() -> int:
    repo = required_env("GITHUB_REPOSITORY")
    sha = required_env("GITHUB_SHA")
    token = required_env("GITHUB_TOKEN")
    workflow_file = os.environ.get("CI_WORKFLOW_FILE", "ci.yml")

    query = urllib.parse.urlencode(
        {
            "head_sha": sha,
            "exclude_pull_requests": "true",
            "per_page": "50",
        }
    )
    payload = github_get(f"/repos/{repo}/actions/workflows/{workflow_file}/runs?{query}", token)
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        fail("unexpected workflow run response")

    matching_runs = [
        run
        for run in runs
        if isinstance(run, dict)
        and run.get("head_sha") == sha
        and run.get("event") != "pull_request"
    ]
    successful_runs = [
        run
        for run in matching_runs
        if run.get("status") == "completed" and run.get("conclusion") == "success"
    ]
    if successful_runs:
        print(successful_runs[0]["id"])
        return 0

    if matching_runs:
        summaries = []
        for run in matching_runs[:5]:
            summaries.append(
                f"id={run.get('id')} status={run.get('status')} conclusion={run.get('conclusion')}"
            )
        fail(f"no successful {workflow_file} run found for {sha}; seen: {', '.join(summaries)}")

    fail(f"no {workflow_file} run found for {sha}")


if __name__ == "__main__":
    raise SystemExit(main())
