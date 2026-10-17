from __future__ import annotations

import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "prune-release-artifacts.sh"


class ReleaseArtifactProtectionTests(unittest.TestCase):
    def test_pruner_protects_current_and_recovery_ci_runs(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn('"$deploy_root/release.json")', source)
        self.assertIn('"$deploy_root/release-state/previous.json")', source)
        self.assertIn('--protect-run-id "$live_run_id"', source)
        self.assertIn('--protect-run-id "$recovery_run_id"', source)
        self.assertEqual(2, source.count("--protect-run-id"))


if __name__ == "__main__":
    unittest.main()
