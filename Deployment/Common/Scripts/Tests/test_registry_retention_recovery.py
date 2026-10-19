from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
LIB = ROOT / "Deployment/Common/Scripts/Component/lib"
sys.path.insert(0, str(LIB))
SCRIPT = ROOT / "Deployment/Common/Scripts/registry-retention-recovery.py"
SPEC = importlib.util.spec_from_file_location("registry_retention_recovery", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RECOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECOVERY)

from registry_retention import Inventory, Payload, Protection, RetentionError, Version  # noqa: E402


REPOSITORY = "example/repo"
REPOSITORY_URL = "https://github.com/" + REPOSITORY
PACKAGE = "ghcr.io/example/app-release-payload"
LOCK_TOKEN = "1792400000-12345-23456"
OWNER_RUN_ID = 77
OWNER_ATTEMPT = 1


class RegistryRetentionRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.lock = self.root / "shared-lock"
        self.lock.mkdir()
        self.runner_temp = self.root / "runner-temp"
        self.runner_temp.mkdir()
        self.record = self.runner_temp / "reservation.json"
        (self.lock / "token").write_text(LOCK_TOKEN, encoding="ascii")
        (self.lock / "owner").write_text(
            f"{socket.gethostname()}:pid=987654321:repo={REPOSITORY}:run={OWNER_RUN_ID}-{OWNER_ATTEMPT}:"
            "started=2026-10-19T10:00:00Z\n",
            encoding="utf-8",
        )
        (self.lock / "created_epoch").write_text("1792400000\n", encoding="ascii")
        self.now = datetime.now(timezone.utc)
        self.version = Version(
            PACKAGE, 123, "sha256:" + "a" * 64, frozenset({"run-1"}),
            self.now - timedelta(days=20), frozenset(), (), 100,
        )
        self.inventory = Inventory(
            REPOSITORY_URL,
            (self.version,),
            (Payload(PACKAGE, self.version.digest, "final", "React", 1, 1,
                    self.version.created, "b" * 40),),
            frozenset({PACKAGE}), True,
        )
        self.protection = Protection(frozenset(), frozenset(), frozenset(), {(1, 1): "completed"}, True)
        self.environment = mock.patch.dict(os.environ, {
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_RUN_ID": "88",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_SHA": "c" * 40,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_WORKFLOW_REF": REPOSITORY + "/.github/workflows/registry-retention.yml@refs/heads/main",
            "GITHUB_TOKEN": "fixture-token",
            "RUNNER_TEMP": str(self.runner_temp),
            "LOCALCLUSTER_DEPLOY_LOCK_DIR": str(self.lock),
            "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": LOCK_TOKEN,
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.guard = RECOVERY.registry_lock_guard.SharedLockGuard(
            repository=REPOSITORY_URL,
            reservation_id=f"run-{OWNER_RUN_ID}-{OWNER_ATTEMPT}",
            inventory=self.inventory,
            refresh_protection=lambda: self.protection,
            controller_scope_complete=True,
            now=lambda: self.now,
        )
        self.guard.reserve((self.version,))
        self.guard.delete_requested(f"run-{OWNER_RUN_ID}-{OWNER_ATTEMPT}", self.version)

    @contextmanager
    def _trusted_owner(self):
        with mock.patch.object(RECOVERY, "_verify_owner_run"), \
                mock.patch.object(RECOVERY, "_pid_is_alive", return_value=False), \
                mock.patch.object(RECOVERY, "_assert_no_owned_work"):
            yield

    def _prepare_record(self):
        with self._trusted_owner():
            return RECOVERY.prepare(
                owner_run_id=OWNER_RUN_ID, owner_attempt=OWNER_ATTEMPT, record=str(self.record),
            )

    def _finish_journal(self):
        reservation = f"run-{OWNER_RUN_ID}-{OWNER_ATTEMPT}"
        self.guard.absent(reservation, self.version, 404)

    def _release(self, *, ids):
        with self._trusted_owner(), \
                mock.patch.object(RECOVERY, "_existing_version_ids", return_value=ids) as inventory:
            result = RECOVERY.release(
                owner_run_id=OWNER_RUN_ID, owner_attempt=OWNER_ATTEMPT, record=str(self.record),
            )
        return result, inventory

    def test_prepare_refuses_unknown_files_and_live_owner_without_changing_them(self):
        unknown = self.lock / "foreign-owner-data"
        unknown.write_text("preserve", encoding="utf-8")
        with self._trusted_owner():
            with self.assertRaises(RetentionError):
                RECOVERY.prepare(owner_run_id=OWNER_RUN_ID, owner_attempt=OWNER_ATTEMPT)
        self.assertEqual(unknown.read_text(encoding="utf-8"), "preserve")
        unknown.unlink()

        with mock.patch.object(RECOVERY, "_verify_owner_run"), \
                mock.patch.object(RECOVERY, "_pid_is_alive", return_value=True), \
                mock.patch.object(RECOVERY, "_assert_no_owned_work"):
            with self.assertRaises(RetentionError):
                RECOVERY.prepare(owner_run_id=OWNER_RUN_ID, owner_attempt=OWNER_ATTEMPT)
        self.assertTrue((self.lock / RECOVERY.JOURNAL).exists())

    def test_release_refuses_pending_journal_and_present_exact_versions(self):
        self._prepare_record()
        with self._trusted_owner():
            with self.assertRaisesRegex(RetentionError, "unresolved candidate states"):
                RECOVERY.release(owner_run_id=OWNER_RUN_ID, owner_attempt=OWNER_ATTEMPT, record=str(self.record))
        self.assertTrue(self.lock.exists())

        self._finish_journal()
        self.assertTrue((self.lock / RECOVERY.JOURNAL).exists())
        with self.assertRaisesRegex(RetentionError, "versions remain present"):
            self._release(ids={self.version.version_id})
        self.assertTrue(self.lock.exists())

    def test_release_removes_only_verified_common_lock_files_after_exact_absence(self):
        self._prepare_record()
        self._finish_journal()
        result, inventory = self._release(ids=set())
        self.assertEqual(result["outcome"], "reservation_reconciled")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["confirmed_absent"], 1)
        self.assertEqual(result["mutation"], "lock-release-only")
        self.assertFalse(self.lock.exists())
        self.assertFalse(self.record.exists())
        inventory.assert_called_once_with(PACKAGE, "fixture-token")

    def test_release_rejects_tampered_record_before_package_query(self):
        self._prepare_record()
        self._finish_journal()
        state = json.loads(self.record.read_text(encoding="utf-8"))
        state["candidates"][0]["version_id"] += 1
        self.record.write_text(json.dumps(state), encoding="utf-8")
        with self._trusted_owner(), \
                mock.patch.object(RECOVERY, "_existing_version_ids") as inventory:
            with self.assertRaisesRegex(RetentionError, "lock changed"):
                RECOVERY.release(
                    owner_run_id=OWNER_RUN_ID, owner_attempt=OWNER_ATTEMPT, record=str(self.record),
                )
        inventory.assert_not_called()
        self.assertTrue(self.lock.exists())

    def test_record_must_be_inside_runner_temp_and_cannot_be_a_symlink(self):
        with self.assertRaises(RetentionError):
            RECOVERY._record_path(str(self.root / "outside.json"))
        target = self.runner_temp / "target.json"
        target.write_text("{}", encoding="utf-8")
        link = self.runner_temp / "link.json"
        link.symlink_to(target)
        with self.assertRaises(RetentionError):
            RECOVERY._read_regular(RECOVERY._record_path(str(link)), limit=1024)


if __name__ == "__main__":
    unittest.main()
