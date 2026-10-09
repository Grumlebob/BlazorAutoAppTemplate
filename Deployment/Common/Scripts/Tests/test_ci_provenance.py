#!/usr/bin/env python3
"""Fixtures for the shared newest-eligible CI selection policy."""

from __future__ import annotations

import importlib.util
import pathlib
import urllib.error
import email.message
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "Component/lib/find-successful-ci-run.py"
SPEC = importlib.util.spec_from_file_location("find_successful_ci_run", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def run(run_id: int, created: str, *, event: str = "push", branch: str = "main",
        status: str = "completed", conclusion: str | None = "success",
        attempt: int = 1, sha: str = "a" * 40,
        path: str = ".github/workflows/ci.yml@refs/heads/main",
        pull_requests: list[object] | None = None) -> dict[str, object]:
    return {
        "repository": {"full_name": "owner/repo"},
        "id": run_id,
        "run_attempt": attempt,
        "head_sha": sha,
        "head_branch": branch,
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "created_at": created,
        "path": path,
        "pull_requests": pull_requests or [],
        "html_url": f"https://github.example/actions/runs/{run_id}",
    }


class CiSelectionTests(unittest.TestCase):
    target = "a" * 40
    workflow = "ci.yml"

    def select(self, runs: list[object], expected_id: str = "", expected_attempt: str = "") -> dict[str, object]:
        return MODULE.select_ci_run(runs, self.target, self.workflow, expected_id, expected_attempt, "owner/repo")

    def test_newest_success_is_selected_by_created_time_then_run_id(self) -> None:
        result = self.select([
            run(8, "2026-09-24T10:00:00Z"),
            run(9, "2026-09-24T11:00:00Z"),
            run(10, "2026-09-24T11:00:00Z"),
        ])
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["selected"]["id"], 10)

    def test_paged_github_cli_responses_use_the_same_selection_policy(self) -> None:
        result = self.select([
            {"workflow_runs": [run(8, "2026-09-24T10:00:00Z")]},
            {"workflow_runs": [run(9, "2026-09-24T11:00:00Z", status="in_progress", conclusion=None)]},
        ])
        self.assertEqual(result["outcome"], "waiting")
        self.assertEqual(result["selected"]["id"], 9)

    def test_latest_in_progress_run_waits_even_when_older_run_succeeded(self) -> None:
        result = self.select([
            run(8, "2026-09-24T10:00:00Z"),
            run(9, "2026-09-24T11:00:00Z", status="in_progress", conclusion=None),
        ])
        self.assertEqual(result["outcome"], "waiting")
        self.assertEqual(result["selected"]["id"], 9)

    def test_latest_failed_run_is_not_hidden_by_an_older_success(self) -> None:
        result = self.select([
            run(8, "2026-09-24T10:00:00Z"),
            run(9, "2026-09-24T11:00:00Z", conclusion="failure"),
        ])
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["selected"]["id"], 9)

    def test_pull_request_events_and_non_main_or_missing_branches_are_ineligible(self) -> None:
        result = self.select([
            run(1, "2026-09-24T10:00:00Z", event="pull_request", branch="refs/pull/4/merge"),
            run(2, "2026-09-24T11:00:00Z", event="push", branch="feature/test"),
            run(3, "2026-09-24T12:00:00Z", event="workflow_dispatch", branch=None),
        ])
        self.assertEqual(result["outcome"], "no_eligible_run")

    def test_wrong_workflow_path_and_target_sha_are_ineligible(self) -> None:
        result = self.select([
            run(1, "2026-09-24T10:00:00Z", path=".github/workflows/cd-localcluster.yml@refs/heads/main"),
            run(2, "2026-09-24T11:00:00Z", sha="b" * 40),
            run(3, "2026-09-24T12:00:00Z", path=""),
        ])
        self.assertEqual(result["outcome"], "no_eligible_run")

    def test_only_rate_limited_forbidden_responses_are_retryable(self) -> None:
        denied_headers = email.message.Message()
        denied = urllib.error.HTTPError("https://github.example", 403, "denied", denied_headers, None)
        self.assertFalse(MODULE.is_retryable_http_error(denied))

        rate_limited_headers = email.message.Message()
        rate_limited_headers["Retry-After"] = "4"
        rate_limited = urllib.error.HTTPError("https://github.example", 403, "rate limited", rate_limited_headers, None)
        self.assertTrue(MODULE.is_retryable_http_error(rate_limited))

    def test_foreign_repository_and_missing_metadata_are_ineligible(self) -> None:
        candidate = run(9, "2026-09-24T11:00:00Z")
        candidate["repository"] = {"full_name": "foreign/repo"}
        self.assertEqual(self.select([candidate])["outcome"], "no_eligible_run")
        del candidate["repository"]
        self.assertEqual(self.select([candidate])["outcome"], "no_eligible_run")

    def test_malformed_timestamp_does_not_fall_back_to_older_success(self) -> None:
        self.assertEqual(self.select([run(8, "2026-09-24T10:00:00Z"), run(9, "yesterday")])["outcome"], "invalid_provenance")

    def test_direct_run_recheck_rejects_rerun_after_list_query(self) -> None:
        selected = self.select([run(9, "2026-09-24T11:00:00Z")])
        current = run(9, "2026-09-24T11:00:00Z", attempt=2, status="queued", conclusion=None)
        self.assertEqual(MODULE.verify_current_run(selected, current, "owner/repo", self.target, self.workflow)["outcome"], "selected_attempt_changed")
        current = run(9, "2026-09-24T11:00:00Z", conclusion="failure")
        self.assertEqual(MODULE.verify_current_run(selected, current, "owner/repo", self.target, self.workflow)["outcome"], "failed")

    def test_changed_paginated_identity_fails_closed(self) -> None:
        self.assertEqual(self.select([run(9, "2026-09-24T11:00:00Z"), run(9, "2026-09-24T11:00:00Z", attempt=2)])["outcome"], "invalid_provenance")

    def test_new_run_invalidates_frozen_run_and_attempt(self) -> None:
        runs = [run(8, "2026-09-24T10:00:00Z"), run(9, "2026-09-24T11:00:00Z", attempt=2)]
        self.assertEqual(self.select(runs, "8")["outcome"], "selected_run_changed")
        self.assertEqual(self.select([runs[1]], "9", "1")["outcome"], "selected_attempt_changed")
        self.assertEqual(self.select([runs[1]], "9", "2")["outcome"], "success")


    def test_main_dispatch_is_not_release_provenance(self) -> None:
        self.assertEqual(self.select([run(9, "2026-09-24T11:00:00Z", event="workflow_dispatch")])["outcome"], "no_eligible_run")

    def publishing_job(self, **overrides) -> dict[str, object]:
        job = {"name": "build-test-push", "run_id": 9, "run_attempt": 1,
               "head_sha": self.target, "status": "completed", "conclusion": "success"}
        job.update(overrides)
        return job

    def verify_jobs(self, jobs) -> dict[str, object]:
        result = self.select([run(9, "2026-09-24T11:00:00Z")])
        return MODULE.verify_publishing_job(result, jobs)

    def test_successful_publishing_job_is_required(self) -> None:
        self.assertEqual(self.verify_jobs([self.publishing_job()])["outcome"], "success")
        for conclusion in ("skipped", "failure", "cancelled", None):
            with self.subTest(conclusion=conclusion):
                self.assertEqual(self.verify_jobs([self.publishing_job(conclusion=conclusion)])["outcome"], "failed")

    def test_missing_duplicate_and_malformed_publishing_jobs_fail_closed(self) -> None:
        for jobs in ([], [self.publishing_job(name="validate")],
                     [self.publishing_job(), self.publishing_job()], None, [None]):
            with self.subTest(jobs=jobs):
                self.assertEqual(self.verify_jobs(jobs)["outcome"], "invalid_provenance")

    def test_publishing_job_identity_is_bound_to_selected_run_attempt_and_sha(self) -> None:
        for values in ({"run_id": 8}, {"run_attempt": 2}, {"head_sha": "b" * 40}):
            with self.subTest(values=values):
                self.assertEqual(self.verify_jobs([self.publishing_job(**values)])["outcome"], "invalid_provenance")


if __name__ == "__main__":
    unittest.main()
