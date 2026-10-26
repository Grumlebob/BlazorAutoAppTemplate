#!/usr/bin/env python3
"""Fixtures for the shared newest-eligible CI selection policy."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import urllib.error
import email.message
import unittest
from unittest.mock import patch

LIB = pathlib.Path(__file__).resolve().parents[1] / "Component" / "lib"
sys.path.insert(0, str(LIB))
import ci_payload_receipt as RECEIPTS  # noqa: E402


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


    def test_main_ci_dispatch_is_release_provenance_but_nonmain_dispatch_is_not(self) -> None:
        main_dispatch = self.select([run(9, "2026-09-24T11:00:00Z", event="workflow_dispatch")])
        self.assertEqual(main_dispatch["outcome"], "success")
        self.assertEqual(main_dispatch["selected"]["event"], "workflow_dispatch")
        nonmain_dispatch = self.select([
            run(10, "2026-09-24T12:00:00Z", event="workflow_dispatch", branch="feature/test"),
        ])
        self.assertEqual(nonmain_dispatch["outcome"], "no_eligible_run")

    def publishing_job(self, **overrides) -> dict[str, object]:
        job = {"name": "build-test-push", "run_id": 9, "run_attempt": 1,
               "head_sha": self.target, "status": "completed", "conclusion": "success", "steps": []}
        job.update(overrides)
        return job

    def verify_jobs(self, jobs) -> dict[str, object]:
        result = self.select([run(9, "2026-09-24T11:00:00Z")])
        return MODULE.verify_publishing_job(result, jobs)

    def verify_payload_jobs(self, jobs) -> dict[str, object]:
        selection = self.select([run(9, "2026-09-24T11:00:00Z")])
        return MODULE.verify_payload_receipt(
            selection, jobs, repository="owner/repo", token="test-token",
            profile="BlazorAuto", acceptance_profile="BlazorAutoV1",
            runtime="linux-x64", app_image="ghcr.io/grumlebob/books",
        )

    def test_explicit_publisher_receipt_wins_over_result_gate_in_either_order(self) -> None:
        publisher = self.publishing_job(name="publish-main", id=44, steps=[
            {"name": MODULE.PAYLOAD_RECEIPT_STEP, "status": "completed", "conclusion": "success"}
        ])
        gate = self.publishing_job(id=88, steps=[{"name": "Verify every event-required CI result"}])
        for jobs in ([publisher, gate], [gate, publisher]):
            with self.subTest(order=[job["name"] for job in jobs]):
                self.assertEqual(self.verify_jobs(jobs)["outcome"], "success")
                with (
                    patch.object(MODULE, "download_job_logs", return_value="publisher logs") as fetch_logs,
                    patch.object(MODULE, "receipts_from_step_log", return_value=[{"kind": "final"}]) as read_receipts,
                    patch.object(MODULE, "select_receipt", return_value={"kind": "final"}),
                ):
                    result = self.verify_payload_jobs(jobs)
                self.assertEqual(result["outcome"], "success")
                fetch_logs.assert_called_once_with("owner/repo", 44, "test-token", api_root=MODULE.API_ROOT)
                self.assertIs(read_receipts.call_args.args[0], publisher)
                self.assertEqual(read_receipts.call_args.kwargs["expected_job_name"], "publish-main")

    def test_failed_modern_publisher_cannot_use_successful_result_gate(self) -> None:
        gate = self.publishing_job(id=88, steps=[{"name": "Verify every event-required CI result"}])
        for conclusion in ("failure", "skipped", "cancelled"):
            with self.subTest(conclusion=conclusion):
                publisher = self.publishing_job(name="publish-main", id=44, conclusion=conclusion)
                self.assertEqual(self.verify_jobs([gate, publisher])["outcome"], "failed")
                with patch.object(MODULE, "download_job_logs") as fetch_logs:
                    result = self.verify_payload_jobs([gate, publisher])
                self.assertEqual(result["outcome"], "failed")
                fetch_logs.assert_not_called()

    def test_modern_publisher_identity_duplicates_and_missing_receipt_fail_closed(self) -> None:
        publisher = self.publishing_job(name="publish-main", id=44)
        wrong_identity = self.publishing_job(name="publish-main", head_sha="b" * 40)
        duplicate = self.publishing_job(name="publish-main", id=45)
        for jobs in ([wrong_identity], [publisher, duplicate], [self.publishing_job(name="publish-main", steps="bad")]):
            with self.subTest(jobs=jobs):
                self.assertEqual(self.verify_jobs(jobs)["outcome"], "invalid_provenance")
                self.assertEqual(self.verify_payload_jobs(jobs)["outcome"], "invalid_provenance")
        self.assertEqual(self.verify_payload_jobs([publisher])["outcome"], "invalid_provenance")

    def test_result_gate_alone_cannot_substitute_for_legacy_publisher(self) -> None:
        gate = self.publishing_job(steps=[{"name": "Verify every event-required CI result"}])
        self.assertEqual(self.verify_jobs([gate])["outcome"], "invalid_provenance")
        self.assertEqual(self.verify_payload_jobs([gate])["outcome"], "invalid_provenance")

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


    def test_final_payload_selection_requires_receipt_from_exact_publisher_step(self) -> None:
        bundle_sha = "b" * 64
        manifest_sha = "a" * 64
        app_image = "ghcr.io/grumlebob/books"
        payload_image = "ghcr.io/grumlebob/books-release-payload"
        payload_digest = "sha256:" + "d" * 64
        identity = RECEIPTS.ReleasePayloadIdentity(
            repository="https://github.com/owner/repo",
            commit_sha=self.target,
            run_id="9",
            run_attempt="1",
            profile="BlazorAuto",
            acceptance_profile="BlazorAutoV1",
            runtime="linux-x64",
            app_image=app_image,
            app_image_digest="sha256:" + "c" * 64,
            bundle_filename="books-migrate",
            manifest_sha256=manifest_sha,
            bundle_sha256=bundle_sha,
        )
        published = {
            "kind": "final",
            "payload_image": payload_image,
            "payload_tag": "run-9-attempt-1-kind-final-profile-blazorauto",
            "payload_digest": payload_digest,
            "payload_ref": f"{payload_image}@{payload_digest}",
            "repository": identity.repository,
            "commit_sha": identity.commit_sha,
            "run_id": identity.run_id,
            "run_attempt": identity.run_attempt,
            "profile": identity.profile,
            "acceptance_profile": identity.acceptance_profile,
            "runtime": identity.runtime,
            "content_sha256": RECEIPTS.content_checksum({
                "release-manifest.json": manifest_sha,
                "books-migrate": bundle_sha,
            }),
            "manifest_sha256": manifest_sha,
            "bundle_filename": "books-migrate",
            "bundle_sha256": bundle_sha,
            "app_image": app_image,
            "app_image_digest": identity.app_image_digest,
        }
        line = RECEIPTS.format_receipt_line(RECEIPTS.final_receipt(identity, published))
        log_text = (
            f"2026-10-15T10:00:00Z {RECEIPTS.RECEIPT_COMMAND_MARKER}\n"
            f"2026-10-15T10:00:01Z {line}\n"
        )
        job = self.publishing_job(id=44, steps=[
            {
                "name": MODULE.PAYLOAD_RECEIPT_STEP,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-10-15T10:00:00Z",
                "completed_at": "2026-10-15T10:00:05Z",
            }
        ])
        selection = self.select([run(9, "2026-09-24T11:00:00Z")])
        with patch.object(MODULE, "download_job_logs", return_value=log_text) as fetch_logs:
            result = MODULE.verify_payload_receipt(
                selection,
                [job],
                repository="owner/repo",
                token="test-token",
                profile="BlazorAuto",
                acceptance_profile="BlazorAutoV1",
                runtime="linux-x64",
                app_image=app_image,
            )
            legacy = MODULE.verify_payload_receipt(
                selection,
                [job],
                repository="owner/repo",
                token="test-token",
                profile="BlazorAuto",
                acceptance_profile="BlazorAutoV1",
                runtime="linux-x64",
                app_image=app_image,
                payload_image_prefix="private-",
            )
            wrong_image = MODULE.verify_payload_receipt(
                selection,
                [job],
                repository="owner/repo",
                token="test-token",
                profile="BlazorAuto",
                acceptance_profile="BlazorAutoV1",
                runtime="linux-x64",
                app_image="ghcr.io/grumlebob/other-books",
                payload_image_prefix="private-",
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["payload_receipt"]["payload_digest"], payload_digest)
        rechecked = MODULE.verify_current_run(
            result, run(9, "2026-09-24T11:00:00Z"), "owner/repo", self.target, self.workflow
        )
        self.assertEqual(rechecked["payload_receipt"]["payload_digest"], payload_digest)
        self.assertEqual(legacy["outcome"], "legacy_artifact")
        self.assertEqual(legacy["transport"], "actions-artifact")
        legacy_rechecked = MODULE.verify_current_run(
            legacy, run(9, "2026-09-24T11:00:00Z"), "owner/repo", self.target, self.workflow
        )
        self.assertEqual(legacy_rechecked["outcome"], "legacy_artifact")
        self.assertEqual(legacy_rechecked["transport"], "actions-artifact")
        self.assertEqual(wrong_image["outcome"], "invalid_provenance")
        self.assertEqual(fetch_logs.call_count, 3)
        fetch_logs.assert_called_with("owner/repo", 44, "test-token", api_root=MODULE.API_ROOT)

    def test_payload_receipt_lookup_rejects_missing_or_expired_receipts(self) -> None:
        selection = self.select([run(9, "2026-09-24T11:00:00Z")])
        job = self.publishing_job(id=44, steps=[
            {
                "name": MODULE.PAYLOAD_RECEIPT_STEP,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-10-15T10:00:00Z",
                "completed_at": "2026-10-15T10:00:05Z",
            }
        ])
        with patch.object(MODULE, "download_job_logs", return_value="ordinary logs"):
            result = MODULE.verify_payload_receipt(
                selection,
                [job],
                repository="owner/repo",
                token="test-token",
                profile="BlazorAuto",
                acceptance_profile="BlazorAutoV1",
                runtime="linux-x64",
                app_image="ghcr.io/grumlebob/books",
            )
        self.assertEqual(result["outcome"], "invalid_provenance")
        self.assertIn("no valid final payload receipt", result["diagnostic"])

        with patch.object(MODULE, "download_job_logs", side_effect=RECEIPTS.ReceiptError("HTTP 404")):
            expired = MODULE.verify_payload_receipt(
                selection,
                [job],
                repository="owner/repo",
                token="test-token",
                profile="BlazorAuto",
                acceptance_profile="BlazorAutoV1",
                runtime="linux-x64",
                app_image="ghcr.io/grumlebob/books",
            )
        self.assertEqual(expired["outcome"], "invalid_provenance")
        self.assertIn("HTTP 404", expired["diagnostic"])

    def test_template_legacy_attempt_uses_actions_artifact_transport(self) -> None:
        selection = self.select([run(9, "2026-09-24T11:00:00Z")])
        job = self.publishing_job(id=44, steps=[])
        with patch.object(MODULE, "download_job_logs") as fetch_logs:
            result = MODULE.verify_payload_receipt(
                selection, [job], repository="owner/repo", token="test-token",
                profile="Template", acceptance_profile=None, runtime="linux-x64",
                app_image="ghcr.io/grumlebob/template",
            )
        self.assertEqual(result["outcome"], "legacy_artifact")
        self.assertEqual(result["transport"], "actions-artifact")
        rechecked = MODULE.verify_current_run(
            result, run(9, "2026-09-24T11:00:00Z"), "owner/repo", self.target, self.workflow
        )
        self.assertEqual(rechecked["outcome"], "legacy_artifact")
        self.assertEqual(rechecked["transport"], "actions-artifact")
        fetch_logs.assert_not_called()


if __name__ == "__main__":
    unittest.main()
