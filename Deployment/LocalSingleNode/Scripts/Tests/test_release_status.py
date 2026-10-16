from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "release-status.py"
sys.path.insert(0, str(SCRIPT.parent / "lib"))
sys.path.insert(0, str(SCRIPT.parents[3] / "Deployment/Common/Scripts/Component/lib"))
sys.path.insert(0, str(SCRIPT.parents[3] / "Scripts/Frontend"))

import importlib.util

spec = importlib.util.spec_from_file_location("single_node_release_status", SCRIPT)
assert spec is not None and spec.loader is not None
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


class LocalSingleNodeReleaseStatusTests(TestCase):
    def marker(self, *, sha: str, pin: str, run_id: str) -> dict:
        return {
            "sha": sha,
            "source_sha": sha,
            "source_repo_url": "https://github.com/Grumlebob/BlazorAutoAppTemplate",
            "image": "ghcr.io/grumlebob/books",
            "digest": "sha256:" + run_id[-1] * 64,
            "frontend_profile": "BlazorAuto",
            "acceptance_profile": "BlazorAutoV1",
            "manifest_schema_version": 2,
            "ci_run_id": run_id,
            "ci_run_attempt": "1",
            "payload_transport": "ghcr-container",
            "release_payload_pin_key": pin,
        }

    def test_snapshot_reports_current_recovery_pins_and_active_runs_without_mutation(self):
        pin_current = "ghcr-" + "a" * 64 + "-" + "b" * 64
        pin_recovery = "ghcr-" + "c" * 64 + "-" + "d" * 64
        config = {"app_name": "books"}
        current = self.marker(sha="1" * 40, pin=pin_current, run_id="12341")
        recovery = self.marker(sha="2" * 40, pin=pin_recovery, run_id="12342")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release.json").write_text(json.dumps(current), encoding="utf-8")
            (root / "release-state").mkdir()
            (root / "release-state/previous.json").write_text(json.dumps(recovery), encoding="utf-8")
            inventory = {
                "outcome": "consistent", "pins": 2, "protected": [pin_current, pin_recovery],
                "protected_bytes": 100, "candidate_bytes": 20, "planned_delete": [],
                "blocked_reason": None, "dry_run": True,
            }
            with patch.object(status.pin_release_payload, "_require_shared_lock"), \
                    patch.object(status.pin_release_payload, "prune_local_pins", return_value=inventory), \
                    patch.object(status, "list_active_deployment_runs", return_value=[{"run_id": "77"}]), \
                    patch.object(status, "verify_live_identity", return_value="verified"), \
                    patch.dict("os.environ", {"APP_INSTANCE": "primary"}, clear=False):
                result = status.snapshot(
                    config, root, repository="Grumlebob/BlazorAutoAppTemplate",
                    repository_url="https://github.com/Grumlebob/BlazorAutoAppTemplate",
                    app_image="ghcr.io/grumlebob/books",
                )

        self.assertEqual(result["current_pin"], "verified")
        self.assertEqual(result["recovery_pin"], "verified")
        self.assertEqual(result["active_deployments"], [{"run_id": "77"}])
        self.assertEqual(result["mutation"], "none")
        self.assertTrue(result["pin_inventory"]["dry_run"])

    def test_marker_rejects_symlink(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            marker = root / "release.json"
            marker.symlink_to(target)
            with self.assertRaises(status.ReleaseStatusError):
                status.marker(marker)

