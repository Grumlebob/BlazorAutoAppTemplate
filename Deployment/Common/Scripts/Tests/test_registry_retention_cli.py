from __future__ import annotations

from argparse import Namespace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
LIB = ROOT / "Deployment/Common/Scripts/Component/lib"
sys.path.insert(0, str(LIB))
SCRIPT = ROOT / "Deployment/Common/Scripts/registry-retention.py"
SPEC = importlib.util.spec_from_file_location("registry_retention_cli", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)

from registry_retention import Inventory, Payload, RetentionError, Version  # noqa: E402


REPOSITORY = "Grumlebob/BlazorAutoAppTemplate"
PACKAGE = "ghcr.io/grumlebob/private-books-release-payload"
NOW = datetime.now(timezone.utc)


def make_inventory(ages=(30, 3, 2, 1), sizes=None):
    sizes = sizes or [200] * len(ages)
    versions, payloads, states = [], [], {}
    for run_id, (age, size) in enumerate(zip(ages, sizes, strict=True), start=1):
        created = NOW - timedelta(days=age)
        digest = "sha256:" + f"{run_id:064x}"
        version = Version(
            PACKAGE, 100 + run_id, digest,
            frozenset({f"run-{run_id}-attempt-1-kind-final-profile-react"}),
            created, frozenset(), (("sha256:" + f"{run_id + 100:064x}", size),), 10,
        )
        payload = Payload(PACKAGE, digest, "final", "React", run_id, 1, created, f"{run_id:040x}")
        versions.append(version)
        payloads.append(payload)
        states[(run_id, 1)] = "completed"
    return Inventory("https://github.com/" + REPOSITORY, tuple(versions), tuple(payloads), frozenset({PACKAGE}), True), states


def snapshot(target: str, instance: str, consumers=(), references=()):
    return json.dumps({
        "schema_version": 1, "target": target, "instance": instance, "complete": True,
        "consumers": list(consumers), "registry_payload_references": list(references),
    }, separators=(",", ":"))


class FakeGuard:
    def __init__(self, **kwargs):
        self.refresh_protection = kwargs["refresh_protection"]
        self.scope = kwargs["controller_scope_complete"]

    def reserve(self, candidates):
        return "run-77-1"

    def check(self, reservation_id, candidate):
        self.refresh_protection()

    def delete_requested(self, reservation_id, candidate):
        return None

    def absent(self, reservation_id, candidate, api_status):
        return None

    def complete(self, reservation_id):
        return None


class RegistryRetentionCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.lock = Path(temporary.name)

    def args(self, inventory=None, *, apply=True, admission_kind=None, reserved_bytes=None, protections=None):
        return Namespace(
            repository=REPOSITORY, username="runner", package=[PACKAGE + "=private"],
            retain_manifest=[], protection_json=protections or [
                snapshot("localcluster", "cluster"), snapshot("localsinglenode", "primary"),
            ], require_additional=False, reservation_id="run-77-1", max_deletions=100,
            admission_kind=admission_kind, reserved_bytes=reserved_bytes, assert_clear=False, apply=apply,
        )

    def test_required_targets_and_optional_instance_must_be_explicitly_complete(self):
        with self.assertRaises(RetentionError):
            CLI._parse_protections([snapshot("localsinglenode", "primary")], require_additional=False)
        values = [snapshot("localcluster", "cluster"), snapshot("localsinglenode", "primary")]
        with self.assertRaises(RetentionError):
            CLI._parse_protections(values, require_additional=True)

    def test_admission_counts_all_current_payloads_and_never_uses_planned_deletion(self):
        inventory, states = make_inventory(ages=(30,), sizes=(CLI.FINAL_BYTES - 10,))
        args = self.args(apply=False, admission_kind="final", reserved_bytes=20)
        with (mock.patch.object(CLI, "_validate_workflow_scope"),
              mock.patch.dict("os.environ", {"GITHUB_TOKEN": "fixture"}),
              mock.patch.object(CLI.shared_deploy_lock, "require_shared_lock", return_value=(self.lock, "fixture-token")),
              mock.patch.object(CLI, "collect_inventory", return_value=(inventory, states)),
              mock.patch.object(CLI.registry_gc, "apply_deletions") as delete):
            with self.assertRaises(RetentionError):
                CLI.run(args, client_factory=lambda *unused: object())
        delete.assert_not_called()

    def test_apply_reinventories_after_exact_404_before_finishing(self):
        initial, states = make_inventory()
        deleted = initial.versions[0]
        fresh = Inventory(
            initial.repository,
            tuple(item for item in initial.versions if item.version_id != deleted.version_id),
            tuple(item for item in initial.payloads if item.digest != deleted.digest),
            initial.owned_packages, True,
        )
        events = []
        def inventory(*args, **kwargs):
            events.append("inventory")
            return (initial, states) if len(events) == 1 else (fresh, {key: value for key, value in states.items() if key[0] != 1})
        def apply(candidates, **kwargs):
            events.append("exact-404")
            return ({"reservation_id": "run-77-1", "package": deleted.package,
                     "version_id": deleted.version_id, "digest": deleted.digest, "api_status": 404},)
        with (mock.patch.object(CLI, "_validate_workflow_scope"),
              mock.patch.dict("os.environ", {"GITHUB_TOKEN": "fixture"}),
              mock.patch.object(CLI.shared_deploy_lock, "require_shared_lock", return_value=(self.lock, "fixture-token")),
              mock.patch.object(CLI, "collect_inventory", side_effect=inventory),
              mock.patch.object(CLI.registry_gc, "apply_deletions", side_effect=apply),
              mock.patch.object(CLI, "list_active_deployment_runs", return_value=[])):
            result = CLI.run(
                self.args(), client_factory=lambda *unused: object(), guard_factory=FakeGuard,
                active_runs_provider=lambda *args, **kwargs: [],
            )
        self.assertEqual(result["outcome"], "applied")
        self.assertEqual(result["verified_absent_versions"], 1)
        self.assertLess(events.index("exact-404"), events.index("inventory", 1))

    def test_snapshot_references_keep_exact_current_and_recovery_payloads(self):
        inventory, states = make_inventory()
        current, recovery = inventory.payloads[1], inventory.payloads[2]
        consumer = lambda item: {"run_id": item.run_id, "run_attempt": item.run_attempt, "target_sha": item.commit_sha}
        reference = lambda item: {
            "package": item.package, "digest": item.digest, "run_id": item.run_id,
            "run_attempt": item.run_attempt, "source_sha": item.commit_sha,
        }
        protections = [
            snapshot("localcluster", "cluster", [consumer(current)], [reference(current)]),
            snapshot("localsinglenode", "primary", [consumer(recovery)], [reference(recovery)]),
        ]
        parsed = CLI._parse_protections(protections, require_additional=False)
        result = CLI._protection(parsed, states, inventory, repository=REPOSITORY, token="fixture",
                                 active_runs_provider=lambda *args, **kwargs: [])
        self.assertEqual(result.digests, {(current.package, current.digest), (recovery.package, recovery.digest)})
        self.assertEqual(result.active_consumers, {(current.run_id, 1), (recovery.run_id, 1)})

    def test_preview_reports_exact_candidate_ids_without_mutation(self):
        inventory, states = make_inventory()
        candidate = inventory.versions[0]
        with (mock.patch.dict("os.environ", {"GITHUB_TOKEN": "fixture"}),
              mock.patch.object(CLI.shared_deploy_lock, "require_shared_lock", return_value=(self.lock, "fixture-token")),
              mock.patch.object(CLI, "collect_inventory", return_value=(inventory, states)),
              mock.patch.object(CLI.registry_gc, "apply_deletions") as delete):
            result = CLI.run(
                self.args(apply=False), client_factory=lambda *unused: object(),
                active_runs_provider=lambda *args, **kwargs: [],
            )

        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["candidate_versions"], 1)
        self.assertEqual(result["preview_candidates"], [{
            "package": candidate.package,
            "version_id": candidate.version_id,
            "digest": candidate.digest,
            "tags": sorted(candidate.tags),
            "created": candidate.created.isoformat(),
        }])
        delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
