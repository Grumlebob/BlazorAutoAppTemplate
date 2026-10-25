from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


LIB = Path(__file__).resolve().parents[1] / "Component/lib"
sys.path.insert(0, str(LIB))
import registry_retention as retention


NOW = datetime(2026, 10, 17, 10, tzinfo=timezone.utc)
PACKAGE = "ghcr.io/example/app-release-payload"
REPOSITORY = "https://github.com/example/app"


def digest(number):
    return f"sha256:{number:064x}"


def payload(number, *, age=1, kind="final", profile="React", size=100):
    created = NOW - timedelta(days=age)
    version = retention.Version(
        PACKAGE, number, digest(number), frozenset({f"run-{number}"}), created,
        frozenset(), ((digest(number + 10000), size),), 10,
    )
    root = retention.Payload(PACKAGE, version.digest, kind, profile, number, 1, created, f"{number:040x}")
    return version, root


def fixture(entries):
    return retention.Inventory(
        REPOSITORY, tuple(value[0] for value in entries), tuple(value[1] for value in entries),
        frozenset({PACKAGE}), True,
    )


def protection(inventory, *, digests=(), tags=(), active=(), states=None, complete=True):
    run_states = {(root.run_id, root.run_attempt): "completed" for root in inventory.payloads}
    run_states.update(states or {})
    return retention.Protection(frozenset(digests), frozenset(tags), frozenset(active), run_states, complete)


class RegistryRetentionTests(unittest.TestCase):
    def test_keeps_three_recent_final_candidates_per_profile_and_expires_old_candidates(self):
        inventory = fixture([
            payload(1, age=0), payload(2, age=1), payload(3, age=2), payload(4, age=3),
            payload(5, age=8), payload(6, age=1, profile="BlazorAuto"),
        ])
        plan = retention.plan_retention(inventory, protection(inventory), now=NOW)
        self.assertEqual({4, 5}, {item.version_id for item in plan.delete})
        self.assertEqual(440, plan.final_bytes_after)

    def test_staging_waits_twenty_four_hours_and_preserves_active_consumers(self):
        inventory = fixture([
            payload(1, age=2, kind="staging"), payload(2, age=2, kind="harness"),
            payload(3, age=0.5, kind="harness"), payload(4, age=2, kind="staging"),
        ])
        references = protection(inventory, active={(2, 1)}, states={(4, 1): "in_progress"})
        plan = retention.plan_retention(inventory, references, now=NOW)
        self.assertEqual([1], [item.version_id for item in plan.delete])
        self.assertEqual(220, plan.protected_bytes)
        self.assertEqual(110, plan.transfer_bytes_after)

    def test_exact_protected_digest_and_alias_preserve_all_referencing_tags(self):
        first, first_root = payload(1, age=20)
        first = replace(first, tags=frozenset({"release", "recovery", "run-1"}))
        inventory = fixture([(first, first_root), payload(2, age=20), payload(3, age=20)])
        references = protection(inventory, digests={(PACKAGE, digest(2))}, tags={(PACKAGE, "recovery")})
        plan = retention.plan_retention(inventory, references, now=NOW)
        self.assertEqual([3], [item.version_id for item in plan.delete])
        self.assertEqual(220, plan.protected_bytes)

    def test_large_protected_payload_does_not_block_publication_measurement_or_safe_retention(self):
        inventory = fixture([payload(1, age=20, size=10 * 1024**3), payload(2, age=20)])
        references = protection(inventory, digests={(PACKAGE, digest(1))})
        plan = retention.plan_retention(inventory, references, now=NOW)
        observation = retention.publication_observation(inventory, kind="final", incoming_bundle_bytes=1)
        self.assertEqual([2], [item.version_id for item in plan.delete])
        self.assertGreater(observation["observed_final_payload_bytes"], 8 * 1024**3)
        self.assertFalse(observation["byte_limit_enforced"])

    def test_final_byte_size_does_not_override_count_and_age_retention(self):
        inventory = fixture([payload(number, age=number, size=4 * 1024**3) for number in range(1, 5)])
        plan = retention.plan_retention(inventory, protection(inventory), now=NOW)
        self.assertEqual({4}, {item.version_id for item in plan.delete})
        self.assertGreater(plan.final_bytes_after, 8 * 1024**3)

    def test_large_young_transfer_payload_does_not_block_publication_measurement(self):
        inventory = fixture([payload(1, age=0.1, kind="staging", size=3 * 1024**3)])
        plan = retention.plan_retention(inventory, protection(inventory), now=NOW)
        observation = retention.publication_observation(inventory, kind="staging", incoming_bundle_bytes=1)
        self.assertEqual((), plan.delete)
        self.assertEqual(3 * 1024**3 + 10, observation["observed_transfer_payload_bytes"])

    def test_publication_observation_reports_current_usage_without_counting_planned_deletion(self):
        inventory = fixture([payload(1, age=20, size=10 * 1024**3), payload(2, age=1)])
        plan = retention.plan_retention(inventory, protection(inventory), now=NOW)
        observation = retention.publication_observation(inventory, kind="final", incoming_bundle_bytes=500)
        actual = retention.inventory_usage(inventory)
        self.assertEqual([1], [item.version_id for item in plan.delete])
        self.assertEqual(actual["total_bytes"], observation["observed_total_payload_bytes"])
        self.assertEqual(500, observation["estimated_incoming_bundle_bytes"])

    def test_shared_manifest_is_not_deleted_while_a_retained_root_uses_it(self):
        old, old_root = payload(1, age=20)
        current, current_root = payload(2, age=1)
        child, _ = payload(3, age=20)
        old = replace(old, children=frozenset({child.digest}), blobs=())
        current = replace(current, children=frozenset({child.digest}), blobs=())
        child = replace(child, tags=frozenset())
        inventory = replace(fixture([(old, old_root), (current, current_root)]), versions=(old, current, child))
        plan = retention.plan_retention(inventory, protection(inventory), now=NOW)
        self.assertEqual([1], [item.version_id for item in plan.delete])
        self.assertEqual(120, plan.final_bytes_after)

    def test_protected_parent_preserves_untagged_children_and_counts_shared_blobs_once(self):
        parent, root = payload(1, age=20)
        child, _ = payload(2, age=20)
        sibling, _ = payload(3, age=20)
        parent = replace(parent, children=frozenset({child.digest, sibling.digest}), blobs=())
        sibling = replace(sibling, blobs=child.blobs, tags=frozenset())
        child = replace(child, tags=frozenset())
        inventory = replace(fixture([(parent, root)]), versions=(parent, child, sibling))
        plan = retention.plan_retention(inventory, protection(inventory, digests={(PACKAGE, parent.digest)}), now=NOW)
        self.assertEqual((), plan.delete)
        self.assertEqual(130, plan.protected_bytes)

    def test_batch_limit_preserves_complete_manifest_groups_and_deletes_parent_first(self):
        parent, root = payload(1, age=20)
        child, _ = payload(2, age=20)
        parent = replace(parent, children=frozenset({child.digest}), blobs=())
        child = replace(child, tags=frozenset())
        inventory = replace(fixture([(parent, root)]), versions=(parent, child))
        deferred = retention.plan_retention(inventory, protection(inventory), now=NOW, max_deletions=1)
        self.assertEqual((), deferred.delete)
        self.assertEqual(1, deferred.deferred_groups)
        applied = retention.plan_retention(inventory, protection(inventory), now=NOW, max_deletions=2)
        self.assertEqual([1, 2], [item.version_id for item in applied.delete])

    def test_missing_protection_producer_state_or_protected_reference_fails_closed(self):
        inventory = fixture([payload(1, age=20)])
        references = [
            protection(inventory, complete=False),
            protection(inventory, states={(1, 1): "unknown"}),
            protection(inventory, digests={(PACKAGE, digest(999))}),
            protection(inventory, tags={(PACKAGE, "missing")}),
        ]
        for reference in references:
            with self.subTest(reference=reference), self.assertRaises(retention.RetentionError):
                retention.plan_retention(inventory, reference, now=NOW)

    def test_unknown_or_duplicate_versions_incomplete_graph_and_foreign_package_fail_closed(self):
        first, root = payload(1, age=20)
        unknown, _ = payload(2, age=20)
        inventory = fixture([(first, root)])
        invalid = [
            replace(inventory, complete=False),
            replace(inventory, versions=(first, unknown)),
            replace(inventory, versions=(first, first)),
            replace(inventory, versions=(replace(first, children=frozenset({digest(999)})),)),
            replace(inventory, versions=(replace(first, package="ghcr.io/foreign/app-release-payload"),)),
            replace(inventory, versions=(replace(first, created=NOW + timedelta(hours=1)),)),
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(retention.RetentionError):
                retention.plan_retention(value, protection(inventory), now=NOW)

    def test_cyclic_manifest_graph_and_conflicting_content_sizes_fail_closed(self):
        first, root = payload(1, age=20)
        cyclic = replace(fixture([(first, root)]), versions=(replace(first, children=frozenset({first.digest})),))
        with self.assertRaises(retention.RetentionError):
            retention.plan_retention(cyclic, protection(cyclic), now=NOW)
        second, second_root = payload(2, age=20)
        second = replace(second, blobs=((first.blobs[0][0], 99),))
        inconsistent = fixture([(first, root), (second, second_root)])
        with self.assertRaises(retention.RetentionError):
            retention.plan_retention(inconsistent, protection(inconsistent), now=NOW)


if __name__ == "__main__":
    unittest.main()
