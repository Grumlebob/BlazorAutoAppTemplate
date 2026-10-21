from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


LIB = Path(__file__).resolve().parents[1] / "Component/lib"
sys.path.insert(0, str(LIB))
import registry_lock_guard as guard_module
import registry_gc
from registry_retention import Inventory, Payload, Protection, RetentionError, Version


NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
CREATED = datetime(2026, 10, 1, tzinfo=timezone.utc)
PACKAGE = "ghcr.io/example/app-release-payload"
REPO = "https://github.com/example/app"
VERSION = Version(PACKAGE, 123, "sha256:" + "a" * 64, frozenset({"run-1"}), CREATED, frozenset(), (), 100)
PAYLOAD = Payload(PACKAGE, VERSION.digest, "final", "React", 1, 1, CREATED, "b" * 40)
INVENTORY = Inventory(REPO, (VERSION,), (PAYLOAD,), frozenset({PACKAGE}), True)


class SharedRegistryGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.lock = Path(self.temporary.name) / "lock"
        self.lock.mkdir()
        (self.lock / "token").write_text("fixture-token", encoding="utf-8")
        self.environment = patch.dict(os.environ, {"LOCALCLUSTER_DEPLOY_LOCK_DIR": str(self.lock), "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": "fixture-token"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.protected = frozenset()

    def guard(self, reservation="fixture-operation", scope=True):
        return guard_module.SharedLockGuard(
            repository=REPO, reservation_id=reservation, inventory=INVENTORY,
            refresh_protection=lambda: Protection(self.protected, frozenset(), frozenset(), {(1, 1): "completed"}, True),
            controller_scope_complete=scope, now=lambda: NOW,
        )

    def test_reservation_blocks_selection_until_exact_absence_is_reconciled(self):
        guard = self.guard()
        reservation = guard.reserve((VERSION,))
        with self.assertRaises(RetentionError):
            guard_module.assert_selection_available(PACKAGE, VERSION.digest, repository=REPO)
        guard.delete_requested(reservation, VERSION)
        with self.assertRaises(RetentionError):
            guard.complete(reservation)
        guard.absent(reservation, VERSION, 404)
        guard.complete(reservation)
        self.assertFalse((self.lock / guard_module.JOURNAL).exists())
        self.assertTrue((self.lock / "token").exists())
        guard_module.assert_selection_available(PACKAGE, VERSION.digest, repository=REPO)

    def test_new_guard_instance_can_resume_only_the_same_persisted_immutable_batch(self):
        original = self.guard()
        reservation = original.reserve((VERSION,))
        original.delete_requested(reservation, VERSION)
        resumed = self.guard()
        self.assertEqual(reservation, resumed.reserve((VERSION,)))
        resumed.absent(reservation, VERSION, 404)
        resumed.complete(reservation)
        self.assertTrue((self.lock / "token").exists())

    def test_resumption_loads_original_inventory_when_remote_parent_has_already_disappeared(self):
        original = self.guard()
        reservation = original.reserve((VERSION,))
        original.delete_requested(reservation, VERSION)
        resumed = guard_module.SharedLockGuard(
            repository=REPO, reservation_id=reservation, inventory=None,
            refresh_protection=original.refresh_protection, controller_scope_complete=True, now=lambda: NOW,
        )
        self.assertEqual((VERSION,), resumed.reserved_candidates())
        self.assertEqual(reservation, resumed.reserve(resumed.reserved_candidates()))
        resumed.absent(reservation, VERSION, 404)
        resumed.complete(reservation)

    def test_another_operation_cannot_take_over_or_clear_the_reservation(self):
        original = self.guard()
        original.reserve((VERSION,))
        before = (self.lock / guard_module.JOURNAL).read_bytes()
        with self.assertRaises(RetentionError):
            self.guard("another-operation").reserve((VERSION,))
        self.assertEqual(before, (self.lock / guard_module.JOURNAL).read_bytes())

    def test_new_protection_or_changed_lock_token_prevents_further_mutation(self):
        guard = self.guard()
        reservation = guard.reserve((VERSION,))
        self.protected = frozenset({(PACKAGE, VERSION.digest)})
        with self.assertRaises(RetentionError):
            guard.delete_requested(reservation, VERSION)
        self.protected = frozenset()
        (self.lock / "token").write_text("different-owner", encoding="utf-8")
        with self.assertRaises((RetentionError, ValueError)):
            guard.absent(reservation, VERSION, 404)

    def batch(self, count):
        versions = tuple(replace(VERSION, version_id=1000 + index, digest=f"sha256:{index + 1:064x}",
                                 tags=frozenset({f"run-{1000 + index}"})) for index in range(count))
        payloads = tuple(replace(PAYLOAD, digest=version.digest, run_id=version.version_id) for version in versions)
        namespace = Version(PACKAGE, 9999, "sha256:" + "e" * 64, frozenset({"namespace"}), CREATED,
                            frozenset(), (), 10)
        namespace = replace(namespace, blobs=(("sha256:" + "f" * 64, 1),))
        inventory = replace(INVENTORY, versions=versions + (namespace,), payloads=payloads,
                            retained_manifests=frozenset({(PACKAGE, namespace.digest)}))
        self.refresh_count = 0

        def refresh():
            self.refresh_count += 1
            return Protection(self.protected, frozenset(), frozenset(),
                              {(version.version_id, 1): "completed" for version in versions}, True)

        guard = guard_module.SharedLockGuard(
            repository=REPO, reservation_id="batch-operation", inventory=inventory,
            refresh_protection=refresh, controller_scope_complete=True, now=lambda: NOW,
        )
        owner = self

        class Registry:
            def __init__(self):
                self.present = {version.version_id: version for version in versions}
                self.reads = 0
                self.deletes = []
                self.after_read = lambda: None
                self.after_delete = lambda: None

            def version(self, package, version_id):
                owner.assertEqual(PACKAGE, package)
                self.reads += 1
                version = self.present.get(version_id)
                self.after_read()
                return None if version is None else {
                    "id": version.version_id, "name": version.digest, "created_at": version.created.isoformat(),
                    "metadata": {"container": {"tags": sorted(version.tags)}},
                }

            def delete_version(self, package, version_id):
                journal = json.loads(guard.path.read_text(encoding="utf-8"))
                owner.assertEqual("delete_requested", journal["candidates"][guard_module.key(self.present[version_id])]["state"])
                self.deletes.append(version_id)
                del self.present[version_id]
                self.after_delete()

        return versions, guard, Registry()

    def test_full_batch_refreshes_once_per_delete_and_keeps_local_lock_checks(self):
        versions, guard, registry = self.batch(100)
        with patch.object(guard_module, "require_shared_lock", wraps=guard_module.require_shared_lock) as local_lock:
            receipts = registry_gc.apply_deletions(versions, registry=registry, guard=guard)
        self.assertEqual(100, len(receipts))
        self.assertEqual(101, self.refresh_count)  # Reservation plus every DELETE boundary.
        self.assertEqual(200, registry.reads)
        self.assertEqual(100, len(registry.deletes))
        self.assertGreater(local_lock.call_count, 400)
        # Five CD status queries per refresh, two exact GETs and one DELETE per version.
        self.assertEqual(805, self.refresh_count * 5 + registry.reads + len(registry.deletes))
        self.assertFalse(guard.path.exists())

    def test_protection_appearing_during_metadata_read_blocks_delete(self):
        versions, guard, registry = self.batch(1)
        registry.after_read = lambda: setattr(self, "protected", frozenset({(PACKAGE, versions[0].digest)}))
        with self.assertRaises(RetentionError):
            registry_gc.apply_deletions(versions, registry=registry, guard=guard)
        self.assertEqual([], registry.deletes)
        self.assertTrue(guard.path.exists())

    def test_recorded_absence_does_not_refresh_but_next_delete_rechecks_protection(self):
        versions, guard, registry = self.batch(2)
        registry.after_delete = lambda: setattr(self, "protected", frozenset((PACKAGE, version.digest) for version in versions))
        with self.assertRaises(RetentionError):
            registry_gc.apply_deletions(versions, registry=registry, guard=guard)
        self.assertEqual([versions[0].version_id], registry.deletes)
        journal = json.loads(guard.path.read_text(encoding="utf-8"))
        self.assertEqual("absent", journal["candidates"][guard_module.key(versions[0])]["state"])
        self.assertEqual("reserved", journal["candidates"][guard_module.key(versions[1])]["state"])
        before = guard.path.read_bytes()
        with self.assertRaises(RetentionError):
            guard.absent("batch-operation", replace(versions[0], digest="sha256:" + "f" * 64), 404)
        self.assertEqual(before, guard.path.read_bytes())

    def test_unknown_controller_scope_and_corrupted_journal_fail_closed(self):
        with self.assertRaises(RetentionError):
            self.guard(scope=False)
        guard = self.guard()
        guard.reserve((VERSION,))
        journal_path = self.lock / guard_module.JOURNAL
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        entry = next(iter(journal["candidates"].values()))
        entry["identity"]["digest"] = "sha256:" + "c" * 64
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
        with self.assertRaises(RetentionError):
            self.guard().reserve((VERSION,))
        with self.assertRaises(RetentionError):
            guard_module.assert_selection_available(PACKAGE, VERSION.digest, repository=REPO)

    def test_registry_guard_requires_lock_without_importing_pin_module(self):
        with patch.dict(os.environ, {"LOCALCLUSTER_DEPLOY_LOCK_DIR": "", "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": ""}):
            with self.assertRaises(RetentionError):
                self.guard()

    @unittest.skipUnless(os.name == "posix", "shared deployment wrapper requires Linux")
    def test_real_process_lock_excludes_selection_while_a_registry_reservation_is_active(self):
        wrapper = LIB.parents[1] / "with-deploy-lock.sh"
        lock = Path(self.temporary.name) / "process-lock"
        ready = Path(self.temporary.name) / "holder-ready"
        environment = dict(os.environ, LOCALCLUSTER_DEPLOY_LOCK_DIR=str(lock), LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS="0")
        code = (
            "from pathlib import Path; import sys; "
            "from Deployment.Common.Scripts.Tests.test_registry_lock_guard import *; "
            "g=guard_module.SharedLockGuard(repository=REPO,reservation_id='process-owner',inventory=INVENTORY,"
            "refresh_protection=lambda: Protection(frozenset(),frozenset(),frozenset(),{(1,1):'completed'},True),"
            "controller_scope_complete=True,now=lambda:NOW); "
            f"r=g.reserve((VERSION,)); Path({str(ready)!r}).write_text('ready'); "
            "sys.stdin.readline(); g.absent(r,VERSION,404); g.complete(r)"
        )
        holder = subprocess.Popen(["bash", str(wrapper), sys.executable, "-c", code],
                                  env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while not ready.exists() and holder.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists(), "Owned holder did not reach its reservation barrier")
            contender = subprocess.run(["bash", str(wrapper), sys.executable, "-c", "raise SystemExit(0)"],
                                       env=environment, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(0, contender.returncode)
            self.assertIn("timed out waiting", contender.stdout + contender.stderr)
        finally:
            output, error = holder.communicate("finish\n", timeout=10)
        self.assertEqual(0, holder.returncode, output + error)
        self.assertFalse(lock.exists())

    @unittest.skipUnless(os.name == "posix", "shared deployment wrapper requires Linux")
    def test_crashed_process_leaves_exact_journal_and_lock_for_verified_resumption(self):
        wrapper = LIB.parents[1] / "with-deploy-lock.sh"
        lock = Path(self.temporary.name) / "crash-lock"
        environment = dict(os.environ, LOCALCLUSTER_DEPLOY_LOCK_DIR=str(lock), LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS="0")
        code = (
            "from Deployment.Common.Scripts.Tests.test_registry_lock_guard import *; "
            "g=guard_module.SharedLockGuard(repository=REPO,reservation_id='crashed-owner',inventory=INVENTORY,"
            "refresh_protection=lambda: Protection(frozenset(),frozenset(),frozenset(),{(1,1):'completed'},True),"
            "controller_scope_complete=True,now=lambda:NOW); "
            "r=g.reserve((VERSION,)); g.delete_requested(r,VERSION); raise SystemExit(7)"
        )
        owned = subprocess.run(["bash", str(wrapper), sys.executable, "-c", code], env=environment,
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(7, owned.returncode, owned.stdout + owned.stderr)
        self.assertTrue((lock / guard_module.JOURNAL).is_file())
        self.assertTrue((lock / "token").is_file())
        self.assertIn("leaving it for inspection", owned.stdout + owned.stderr)
        # The owned subprocess is verified terminal. Resume only its exact test
        # reservation; production recovery must likewise verify the owner.
        environment["LOCALCLUSTER_DEPLOY_LOCK_TOKEN"] = (lock / "token").read_text(encoding="utf-8").strip()
        resume = code.rsplit("r=g.reserve", 1)[0] + "r=g.reserve((VERSION,)); g.absent(r,VERSION,404); g.complete(r)"
        resumed = subprocess.run([sys.executable, "-c", resume], env=environment,
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(0, resumed.returncode, resumed.stdout + resumed.stderr)
        self.assertFalse((lock / guard_module.JOURNAL).exists())
        self.assertTrue((lock / "token").exists(), "The guard must never remove or take over the shared lock")


if __name__ == "__main__":
    unittest.main()
