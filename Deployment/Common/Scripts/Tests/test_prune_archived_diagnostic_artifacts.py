from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "prune-archived-diagnostic-artifacts.py"
SPEC = importlib.util.spec_from_file_location("prune_archived_diagnostic_artifacts", SCRIPT)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)


REPOSITORY = "Grumlebob/GrumPlates"
SHA = "b" * 40
ARTIFACT_SHA = "a" * 64


def row(artifact_id: int = 101) -> dict:
    return {
        "id": artifact_id,
        "name": f"dotnet-test-results-{artifact_id}-1",
        "size_in_bytes": 123,
        "digest": "sha256:" + ARTIFACT_SHA,
        "created_at": "2026-10-15T12:00:00Z",
        "workflow_run": {
            "id": artifact_id,
            "repository_id": 1,
            "head_repository_id": 1,
            "head_branch": "main",
            "head_sha": SHA,
        },
        "download_bytes": 123,
        "archive_sha256": ARTIFACT_SHA,
        "producer": {
            "id": artifact_id,
            "run_attempt": 1,
            "head_sha": SHA,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
        },
    }


def manifest(entries: list[dict] | None = None) -> dict:
    entries = entries if entries is not None else [row()]
    return {
        "schema_version": 1,
        "repository": REPOSITORY,
        "archive": {
            "name": "GrumPlates-legacy-diagnostics-20261017.zip",
            "sha256": "c" * 64,
            "artifact_count": len(entries),
            "verified_readback": True,
        },
        "artifacts": entries,
    }


def remote_artifact(expected: dict) -> dict:
    return {
        "id": expected["id"],
        "name": expected["name"],
        "size_in_bytes": expected["size_in_bytes"],
        "digest": expected["digest"],
        "created_at": expected["created_at"],
        "expired": False,
        "workflow_run": expected["workflow_run"],
    }


def remote_run(expected: dict) -> dict:
    workflow = expected["workflow_run"]
    producer = expected["producer"]
    return {
        "id": producer["id"],
        "run_attempt": producer["run_attempt"],
        "head_sha": producer["head_sha"],
        "head_branch": workflow["head_branch"],
        "status": producer["status"],
        "conclusion": producer["conclusion"],
        "event": producer["event"],
        "repository": {"id": workflow["repository_id"]},
        "head_repository": {"id": workflow["head_repository_id"]},
    }


class ManifestTests(unittest.TestCase):
    def read(self, value: dict) -> tuple[dict, ...]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return cleanup.read_manifest(path, REPOSITORY)

    def test_accepts_reviewed_readback_manifest(self) -> None:
        self.assertEqual(self.read(manifest()), (row(),))

    def test_rejects_repository_mismatch_and_unreviewed_name(self) -> None:
        wrong_repo = manifest()
        wrong_repo["repository"] = "Grumlebob/ImprovedDb"
        with self.assertRaisesRegex(cleanup.CleanupError, "schema or repository"):
            self.read(wrong_repo)

        wrong_name = manifest()
        wrong_name["artifacts"][0]["name"] = "portfolio-migrate-linux-x64"
        with self.assertRaisesRegex(cleanup.CleanupError, "identity or producer"):
            self.read(wrong_name)

    def test_rejects_duplicate_ids_and_archive_digest_mismatch(self) -> None:
        with self.assertRaisesRegex(cleanup.CleanupError, "identity or producer"):
            self.read(manifest([row(), row()]))

        wrong_digest = manifest()
        wrong_digest["artifacts"][0]["archive_sha256"] = "d" * 64
        with self.assertRaisesRegex(cleanup.CleanupError, "identity or producer"):
            self.read(wrong_digest)

    def test_reviewed_template_archive_manifest_contains_all_exact_ids(self) -> None:
        root = Path(__file__).resolve().parents[4]
        manifest_path = root / "Plans/ZeroCostDiagnosticArchiveManifest-20261017.json"
        rows = cleanup.read_manifest(manifest_path, REPOSITORY)
        self.assertEqual(len(rows), 244)
        manifest_value = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest_value["archive"]["sha256"],
            "f3abb05e99c62e535fa4c69e05ca19f97e218d268f4532a7e8a6f0913dfcd005",
        )

    def test_rejects_batch_larger_than_fixed_cap(self) -> None:
        with self.assertRaisesRegex(cleanup.CleanupError, "between 1 and 100"):
            cleanup.cleanup_archived((), repository=REPOSITORY, token="token", max_items=101)


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entry = row()
        self.calls: list[tuple[str, str]] = []
        self.deleted = False

        def api(_root: str, method: str, path: str, _token: str, *, missing: bool = False):
            self.calls.append((method, path))
            if method == "DELETE":
                self.deleted = True
                return {}
            if "/actions/runs/" in path:
                return remote_run(self.entry)
            if self.deleted:
                return None
            return remote_artifact(self.entry)

        self.api = api
        self.lock = mock.patch.object(cleanup, "require_shared_lock")
        self.lock.start()
        self.addCleanup(self.lock.stop)

    def test_dry_run_verifies_exact_artifact_and_producer_without_delete(self) -> None:
        with mock.patch.object(cleanup, "github_request", side_effect=self.api):
            result = cleanup.cleanup_archived((self.entry,), repository=REPOSITORY, token="token")
        self.assertEqual(result, {"examined": 1, "candidates": 1, "deleted": 0, "already_absent": 0, "expired": 0})
        self.assertFalse(self.deleted)
        self.assertEqual([method for method, _ in self.calls], ["GET", "GET"])

    def test_apply_sends_one_delete_then_requires_exact_id_404(self) -> None:
        with mock.patch.object(cleanup, "github_request", side_effect=self.api):
            result = cleanup.cleanup_archived((self.entry,), repository=REPOSITORY, token="token", apply=True)
        self.assertEqual(result["deleted"], 1)
        self.assertEqual([method for method, _ in self.calls], ["GET", "GET", "GET", "DELETE", "GET"])
        self.assertEqual(sum(method == "DELETE" for method, _ in self.calls), 1)

    def test_identity_mismatch_stops_before_delete(self) -> None:
        def mismatched(*args, **kwargs):
            value = self.api(*args, **kwargs)
            if args[1] == "GET" and "/actions/artifacts/" in args[2]:
                value["name"] = "react-test-results-102-1"
            return value

        with mock.patch.object(cleanup, "github_request", side_effect=mismatched):
            with self.assertRaisesRegex(cleanup.CleanupError, "changed from its reviewed"):
                cleanup.cleanup_archived((self.entry,), repository=REPOSITORY, token="token", apply=True)
        self.assertFalse(self.deleted)

    def test_exact_404_is_idempotent(self) -> None:
        with mock.patch.object(cleanup, "github_request", return_value=None):
            result = cleanup.cleanup_archived((self.entry,), repository=REPOSITORY, token="token", apply=True)
        self.assertEqual(result["already_absent"], 1)
        self.assertEqual(result["deleted"], 0)

    def test_held_lock_is_required_before_github_access(self) -> None:
        with mock.patch.object(cleanup, "require_shared_lock", side_effect=cleanup.CleanupError("no lock")):
            with mock.patch.object(cleanup, "github_request") as request:
                with self.assertRaisesRegex(cleanup.CleanupError, "no lock"):
                    cleanup.cleanup_archived((self.entry,), repository=REPOSITORY, token="token")
        request.assert_not_called()

    def test_uncertain_delete_is_not_retried(self) -> None:
        with mock.patch.object(cleanup.urllib.request, "urlopen", side_effect=urllib.error.URLError("timeout")) as send:
            with self.assertRaisesRegex(cleanup.CleanupError, "no retry was sent"):
                cleanup.github_request("https://api.github.com", "DELETE", "/repos/test/repo/actions/artifacts/1", "token")
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
