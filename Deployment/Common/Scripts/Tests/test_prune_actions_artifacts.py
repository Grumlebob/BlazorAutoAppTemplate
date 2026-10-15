#!/usr/bin/env python3
"""Retention selection and exact deletion checks; no GitHub calls."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "Component/lib/prune-actions-artifacts.py"
SPEC = importlib.util.spec_from_file_location("prune_actions_artifacts", SCRIPT)
assert SPEC and SPEC.loader
prune = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prune)


def artifact(artifact_id: int, run_id: int | None, day: int, *, size: int = 10, head_sha: str | None = None) -> dict:
    item = {
        "id": artifact_id,
        "name": "release-payload",
        "created_at": f"2026-10-{day:02d}T00:00:00Z",
        "size_in_bytes": size,
        "expired": False,
    }
    if run_id is not None:
        item["workflow_run"] = {"id": run_id, "head_sha": head_sha or f"{artifact_id:040x}"}
    return item


class SelectDeletionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifacts = [artifact(index, 1000 + index, index) for index in range(1, 7)]

    def selection(self, artifacts=None, *, keep=2, protected=(), active_producers=(), active_shas=(), cap=512, limit=100):
        return prune.select_deletions(
            self.artifacts if artifacts is None else artifacts,
            keep,
            set(protected),
            set(active_producers),
            set(active_shas),
            cap,
            limit,
        )

    def ids(self, items: list[dict]) -> list[int]:
        return [item["id"] for item in items]

    def test_keeps_newest_two_unprotected_and_deletes_oldest_first(self) -> None:
        delete, protected, protected_bytes, floor_bytes = self.selection()
        self.assertEqual([1, 2, 3, 4], self.ids(delete))
        self.assertEqual([], protected)
        self.assertEqual(0, protected_bytes)
        self.assertEqual(20, floor_bytes)

    def test_persisted_and_active_producer_runs_are_never_deleted(self) -> None:
        delete, protected, *_ = self.selection(protected={1001}, active_producers={1003})
        self.assertEqual([2, 4], self.ids(delete))
        self.assertEqual([1, 3], self.ids(protected))

    def test_active_deployment_target_sha_protects_every_matching_artifact(self) -> None:
        shared_sha = "a" * 40
        artifacts = [artifact(1, 11, 1, head_sha=shared_sha), artifact(2, 12, 2), artifact(3, 13, 3)]
        delete, protected, *_ = self.selection(artifacts, keep=1, active_shas={shared_sha})
        self.assertEqual([2], self.ids(delete))
        self.assertEqual([1], self.ids(protected))

    def test_protected_bytes_over_cap_blocks_all_deletions(self) -> None:
        delete, protected, protected_bytes, _ = self.selection(protected={1001}, cap=9)
        self.assertEqual([], delete)
        self.assertEqual([1], self.ids(protected))
        self.assertEqual(10, protected_bytes)

    def test_oldest_batch_is_bounded(self) -> None:
        delete, *_ = self.selection(limit=2)
        self.assertEqual([1, 2], self.ids(delete))

    def test_expired_artifacts_are_not_selected_for_deletion(self) -> None:
        artifacts = self.artifacts + [{**artifact(99, 1999, 0), "expired": True}]
        delete, *_ = self.selection(artifacts)
        self.assertNotIn(99, self.ids(delete))

    def test_missing_workflow_identity_fails_closed(self) -> None:
        with self.assertRaisesRegex(SystemExit, "no workflow identity"):
            self.selection([artifact(99, None, 0)])

    def test_invalid_producer_sha_fails_closed(self) -> None:
        malformed = artifact(99, 1999, 0)
        malformed["workflow_run"]["head_sha"] = "short"
        with self.assertRaisesRegex(SystemExit, "no verifiable producer SHA"):
            self.selection([malformed])

    def test_duplicate_artifact_ids_fail_closed(self) -> None:
        with self.assertRaisesRegex(SystemExit, "repeats ID"):
            self.selection([artifact(1, 11, 1), artifact(1, 12, 2)])


class LockTests(unittest.TestCase):
    def test_lock_token_must_be_present_and_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "lock"
            lock.mkdir()
            (lock / "token").write_text("expected\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {
                "LOCALCLUSTER_DEPLOY_LOCK_DIR": str(lock),
                "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": "expected",
            }, clear=True):
                prune.require_deploy_lock()
            with mock.patch.dict(os.environ, {
                "LOCALCLUSTER_DEPLOY_LOCK_DIR": str(lock),
                "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": "stale",
            }, clear=True):
                with self.assertRaisesRegex(SystemExit, "token is absent or changed"):
                    prune.require_deploy_lock()

    def test_unlocked_pruner_is_rejected(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "shared deployment lock is required"):
                prune.require_deploy_lock()


class DeploymentReferenceTests(unittest.TestCase):
    def test_active_and_two_newest_successful_targets_are_protected(self):
        calls = []
        live_target = "a" * 40
        newest_target = "b" * 40
        recovery_target = "c" * 40
        historical_target = "d" * 40

        def runs(api_root, repo, token, workflow_file, status, *, max_runs=None):
            calls.append((workflow_file, status))
            if workflow_file == "cd-localcluster.yml" and status == "success":
                return [
                    {"display_title": f"CD LocalCluster @ {newest_target}"},
                    {"display_title": f"CD LocalCluster @ {newest_target}"},
                    {"display_title": f"CD LocalCluster @ {recovery_target}"},
                    {"display_title": f"CD LocalCluster @ {historical_target}"},
                ]
            if workflow_file == "cd-localsinglenode.yml" and status == "in_progress":
                return [{"display_title": f"CD LocalSingleNode @ {live_target}"}]
            return []

        with mock.patch.object(prune, "list_workflow_runs", side_effect=runs):
            shas = prune.list_deployment_shas(
                "https://api.example", "owner/repo", "token", ["cd-localcluster.yml", "cd-localsinglenode.yml"]
            )
        self.assertEqual({live_target, newest_target, recovery_target}, shas)
        self.assertIn(("cd-localcluster.yml", "success"), calls)
        self.assertNotIn(("cd-localcluster.yml", "completed"), calls)
        self.assertIn(("cd-localsinglenode.yml", "in_progress"), calls)
        self.assertTrue(all(any(observed == active for _, observed in calls) for active in prune.ACTIVE_STATUSES))

    def test_ambiguous_recent_success_history_fails_closed(self):
        target = "a" * 40

        def runs(api_root, repo, token, workflow_file, status, *, max_runs=None):
            if status == "success":
                return [{"display_title": f"CD LocalCluster @ {target}"}] * 100
            return []

        with mock.patch.object(prune, "list_workflow_runs", side_effect=runs):
            with self.assertRaisesRegex(SystemExit, "do not identify two unique target SHAs"):
                prune.list_deployment_shas("https://api.example", "owner/repo", "token", ["cd.yml"])

    def test_unknown_deployment_target_fails_closed(self):
        with mock.patch.object(prune, "list_workflow_runs", return_value=[{"display_title": "Deploy target unknown"}]):
            with self.assertRaisesRegex(SystemExit, "no verifiable target SHA"):
                prune.list_deployment_shas("https://api.example", "owner/repo", "token", ["cd.yml"])


class MainDeletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.lock = Path(self.directory.name) / "lock"
        self.lock.mkdir()
        (self.lock / "token").write_text("test-token\n", encoding="utf-8")
        self.environment = {
            "LOCALCLUSTER_DEPLOY_LOCK_DIR": str(self.lock),
            "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": "test-token",
        }
        self.artifacts = [artifact(1, 11, 1), artifact(2, 12, 2), artifact(3, 13, 3)]
        self.argv = [
            "prune-actions-artifacts.py",
            "--artifact-name", "release-payload",
            "--repo", "owner/repository",
            "--token", "fixture-token",
            "--deployment-workflow-file", "cd.yml",
        ]

    def tearDown(self) -> None:
        self.directory.cleanup()

    def patches(self):
        return (
            mock.patch.object(prune, "list_artifacts", return_value=self.artifacts),
            mock.patch.object(prune, "list_active_producer_run_ids", return_value=set()),
            mock.patch.object(prune, "list_deployment_shas", return_value=set()),
        )

    def test_delete_requires_rechecked_identity_and_exact_404_receipt(self) -> None:
        calls = []

        def request(api_root, method, path, token, **kwargs):
            calls.append((method, path))
            if method == "GET" and path.endswith("/1"):
                if len(calls) == 1:
                    return self.artifacts[0]
                return None
            if method == "DELETE":
                return {}
            raise AssertionError((method, path))

        with mock.patch.object(sys, "argv", self.argv), mock.patch.dict(os.environ, self.environment, clear=True), \
                self.patches()[0], self.patches()[1], self.patches()[2], mock.patch.object(prune, "github_request", side_effect=request), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, prune.main())
        self.assertEqual([
            ("GET", "/repos/owner/repository/actions/artifacts/1"),
            ("DELETE", "/repos/owner/repository/actions/artifacts/1"),
            ("GET", "/repos/owner/repository/actions/artifacts/1"),
        ], calls)

    def test_changed_identity_stops_before_delete(self) -> None:
        calls = []

        def request(api_root, method, path, token, **kwargs):
            calls.append(method)
            changed = dict(self.artifacts[0], size_in_bytes=999)
            return changed

        with mock.patch.object(sys, "argv", self.argv), mock.patch.dict(os.environ, self.environment, clear=True), \
                self.patches()[0], self.patches()[1], self.patches()[2], mock.patch.object(prune, "github_request", side_effect=request), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(SystemExit, "identity changed"):
            prune.main()
        self.assertEqual(["GET"], calls)


if __name__ == "__main__":
    unittest.main()
