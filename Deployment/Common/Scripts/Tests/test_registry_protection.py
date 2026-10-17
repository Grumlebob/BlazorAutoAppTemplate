from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "registry-protection.py"
SPEC = importlib.util.spec_from_file_location("registry_protection_cli", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


class RegistryProtectionTests(unittest.TestCase):
    def status(self):
        return {
            "schema_version": 1,
            "target": "localcluster",
            "shared_lock": "held",
            "mutation": "none",
            "live_identity": "verified",
            "current_release": {
                "source_sha": "a" * 40, "ci_run_id": "123", "ci_run_attempt": "2",
                "payload_transport": "ghcr-container", "release_payload_pin_key": "ghcr-key",
            },
            "recovery_release": {
                "source_sha": "b" * 40, "ci_run_id": "456", "ci_run_attempt": "1",
                "payload_transport": "actions-artifact", "release_payload_pin_key": None,
            },
            "registry_payload_references": [{
                "payload_image": "ghcr.io/example/books-release-payload",
                "payload_digest": "sha256:" + "c" * 64,
                "ci_run_id": "123", "ci_run_attempt": "2", "source_sha": "a" * 40,
            }],
        }

    def test_extracts_current_and_recovery_consumer_attempts_and_exact_registry_digest(self):
        result = CLI.protection(self.status(), target="localcluster", instance="cluster")
        self.assertEqual(result["consumers"], [
            {"run_id": 123, "run_attempt": 2, "target_sha": "a" * 40},
            {"run_id": 456, "run_attempt": 1, "target_sha": "b" * 40},
        ])
        self.assertEqual(result["registry_payload_references"][0]["digest"], "sha256:" + "c" * 64)
        self.assertTrue(result["complete"])

    def test_missing_registry_pin_for_ghcr_current_marker_fails_closed(self):
        value = self.status()
        value["registry_payload_references"] = []
        with self.assertRaises(CLI.ProtectionError):
            CLI.protection(value, target="localcluster", instance="cluster")

    def test_unverified_live_identity_or_wrong_target_fails_closed(self):
        value = self.status()
        value["live_identity"] = "failed"
        with self.assertRaises(CLI.ProtectionError):
            CLI.protection(value, target="localcluster", instance="cluster")
        with self.assertRaises(CLI.ProtectionError):
            CLI.protection(self.status(), target="localsinglenode", instance="cluster")


if __name__ == "__main__":
    unittest.main()
