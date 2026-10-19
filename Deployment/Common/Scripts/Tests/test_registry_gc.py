from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


LIB = Path(__file__).resolve().parents[1] / "Component/lib"
sys.path.insert(0, str(LIB))
import registry_gc as gc
from registry_retention import RetentionError, Version


VERSION = Version(
    "ghcr.io/example/app-release-payload", 123, "sha256:" + "a" * 64,
    frozenset({"run-1-attempt-1-kind-final-profile-react"}), datetime(2026, 10, 1, tzinfo=timezone.utc),
    frozenset(), (), 100,
)


class FixtureGuard:
    def __init__(self):
        self.events = []
        self.reserved = None
        self.state = "empty"
        self.protected = False
        self.fail_check = False

    def reserve(self, candidates):
        self.events.append("reserve")
        if self.protected or (self.reserved is not None and self.reserved != candidates):
            raise RetentionError("candidate is protected or owned by a different reservation")
        self.reserved = candidates
        if self.state == "empty":
            self.state = "reserved"
        return "fixture-reservation"

    def check(self, reservation_id, candidate):
        self.events.append("check")
        if self.fail_check or reservation_id != "fixture-reservation" or candidate not in self.reserved:
            raise RetentionError("reservation ownership or lock changed")

    def delete_requested(self, reservation_id, candidate):
        self.events.append("delete-requested")
        self.state = "delete_requested"

    def absent(self, reservation_id, candidate, api_status):
        if api_status != 404:
            raise AssertionError("Absence must use an exact-version 404")
        self.events.append("absent")
        self.state = "absent"

    def complete(self, reservation_id):
        if self.state != "absent":
            raise AssertionError("An unresolved reservation cannot complete")
        self.events.append("complete")
        self.state = "complete"


class FixtureRegistry:
    def __init__(self, guard):
        self.guard = guard
        self.present = True
        self.interrupt_after_delete = False
        self.still_present = False
        self.delete_calls = 0
        self.metadata = {"id": VERSION.version_id, "name": VERSION.digest, "created_at": VERSION.created.isoformat(),
                         "metadata": {"container": {"tags": sorted(VERSION.tags)}}}

    def version(self, package, version_id):
        if (package, version_id) != (VERSION.package, VERSION.version_id):
            raise AssertionError("Only the exact reserved version may be queried")
        return deepcopy(self.metadata) if self.present else None

    def delete_version(self, package, version_id):
        if self.guard.state != "delete_requested":
            raise AssertionError("DELETE preceded persisted deletion intent")
        self.delete_calls += 1
        self.present = self.still_present
        if self.interrupt_after_delete:
            self.interrupt_after_delete = False
            raise TimeoutError("fixture response lost after remote deletion")


class RegistryDeletionTests(unittest.TestCase):
    def test_rechecks_immutable_identity_and_records_exact_404_before_completion(self):
        guard = FixtureGuard()
        registry = FixtureRegistry(guard)
        receipts = gc.apply_deletions((VERSION,), registry=registry, guard=guard)
        self.assertEqual(1, registry.delete_calls)
        self.assertEqual(404, receipts[0]["api_status"])
        self.assertEqual(VERSION.digest, receipts[0]["digest"])
        self.assertEqual(["reserve", "check", "check", "delete-requested", "check", "absent", "complete"], guard.events)

    def test_interrupted_request_resumes_exact_reservation_without_a_second_delete(self):
        guard = FixtureGuard()
        registry = FixtureRegistry(guard)
        registry.interrupt_after_delete = True
        with self.assertRaises(gc.DeletionUncertain):
            gc.apply_deletions((VERSION,), registry=registry, guard=guard)
        self.assertEqual("delete_requested", guard.state)
        gc.apply_deletions((VERSION,), registry=registry, guard=guard)
        self.assertEqual(1, registry.delete_calls)
        self.assertEqual("complete", guard.state)

    def test_recovery_can_keep_absence_journal_until_shared_lock_release(self):
        guard = FixtureGuard()
        registry = FixtureRegistry(guard)
        receipts = gc.apply_deletions(
            (VERSION,), registry=registry, guard=guard, complete_reservation=False,
        )
        self.assertEqual(404, receipts[0]["api_status"])
        self.assertEqual("absent", guard.state)
        self.assertNotIn("complete", guard.events)

    def test_changed_tags_digest_created_time_or_version_id_prevent_delete(self):
        changes = [
            {"name": "sha256:" + "b" * 64}, {"id": 124}, {"created_at": "2026-10-02T00:00:00Z"},
            {"metadata": {"container": {"tags": ["a-new-alias"]}}},
        ]
        for change in changes:
            guard = FixtureGuard()
            registry = FixtureRegistry(guard)
            registry.metadata.update(change)
            with self.subTest(change=change), self.assertRaises(RetentionError):
                gc.apply_deletions((VERSION,), registry=registry, guard=guard)
            self.assertEqual(0, registry.delete_calls)
            self.assertEqual("reserved", guard.state)

    def test_lost_coordination_or_new_protection_cannot_authorize_delete(self):
        for attribute in ("protected", "fail_check"):
            guard = FixtureGuard()
            registry = FixtureRegistry(guard)
            setattr(guard, attribute, True)
            with self.subTest(attribute=attribute), self.assertRaises(RetentionError):
                gc.apply_deletions((VERSION,), registry=registry, guard=guard)
            self.assertEqual(0, registry.delete_calls)

    def test_present_after_delete_cannot_be_reported_as_success(self):
        guard = FixtureGuard()
        registry = FixtureRegistry(guard)
        registry.still_present = True
        with self.assertRaises(gc.DeletionUncertain):
            gc.apply_deletions((VERSION,), registry=registry, guard=guard)
        self.assertEqual("delete_requested", guard.state)
        self.assertNotIn("absent", guard.events)

    def test_duplicate_batch_is_rejected_before_reservation(self):
        guard = FixtureGuard()
        registry = FixtureRegistry(guard)
        with self.assertRaises(RetentionError):
            gc.apply_deletions((VERSION, VERSION), registry=registry, guard=guard)
        self.assertEqual([], guard.events)
        self.assertEqual(0, registry.delete_calls)


if __name__ == "__main__":
    unittest.main()
