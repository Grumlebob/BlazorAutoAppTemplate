from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "pin-legacy-release.py"
REPO_ROOT = SCRIPT.parents[3]
sys_path = str(REPO_ROOT / "Deployment/Common/Scripts/Component/lib")
sys.path.insert(0, sys_path)
spec = importlib.util.spec_from_file_location("pin_legacy_release", SCRIPT)
assert spec is not None and spec.loader is not None
operation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operation)


class PinLegacyReleaseTests(TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.deploy_root = Path(self.temp.name)
        self.marker = {
            "sha": "a" * 40,
            "source_sha": "a" * 40,
            "source_repo_url": "https://github.com/Grumlebob/BlazorAutoAppTemplate",
            "image": "ghcr.io/grumlebob/books",
            "digest": "sha256:" + "b" * 64,
            "frontend_profile": "React",
            "acceptance_profile": "ReactPublicV1",
            "manifest_schema_version": 2,
            "ci_run_id": "12345",
            "ci_run_attempt": "2",
            "payload_transport": "actions-artifact",
        }
        self.marker_path = self.deploy_root / "release.json"
        self.marker_path.write_text(json.dumps(self.marker), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _metadata(self, key: str = "legacy-987-" + "c" * 64) -> dict:
        return {
            "schema_version": 1,
            "transport": "actions-artifact",
            "repository": "https://github.com/Grumlebob/BlazorAutoAppTemplate",
            "target_sha": self.marker["source_sha"],
            "run_id": self.marker["ci_run_id"],
            "run_attempt": self.marker["ci_run_attempt"],
            "profile": self.marker["frontend_profile"],
            "acceptance_profile": self.marker["acceptance_profile"],
            "runtime": "linux-x64",
            "app_image": self.marker["image"],
            "image_digest": self.marker["digest"],
            "manifest_schema_version": self.marker["manifest_schema_version"],
            "pin_key": key,
            "artifact_id": "987",
            "artifact_digest": "sha256:" + "c" * 64,
            "manifest_sha256": "d" * 64,
            "bundle_filename": "books-migrate",
            "bundle_sha256": "e" * 64,
        }

    def test_imports_exact_accepted_attempt_and_leaves_marker_unchanged(self) -> None:
        before = self.marker_path.read_bytes()
        selected = subprocess.CompletedProcess([], 0, json.dumps({
            "outcome": "legacy_artifact",
            "selected": {"id": 12345, "run_attempt": 2, "head_sha": self.marker["source_sha"]},
        }), "")
        metadata = self._metadata()
        expected_metadata = metadata.copy()
        with patch.object(operation.subprocess, "run", return_value=selected) as selector, \
                patch.object(operation.pin_release_payload, "_require_shared_lock", return_value=(self.deploy_root, "token")), \
                patch.object(operation.import_legacy_release_payload, "import_legacy_artifact", return_value=metadata) as importer, \
                patch.object(operation, "_verify_offline_restore") as offline_restore:
            result = operation.pin_marker(
                slot="current",
                app_instance="primary",
                deploy_root=self.deploy_root,
                repository="Grumlebob/BlazorAutoAppTemplate",
                repository_url="https://github.com/Grumlebob/BlazorAutoAppTemplate",
                app_image_base="ghcr.io/grumlebob/books",
                migration_artifact_name="books-migrate-linux-x64",
                migration_bundle_name="books-migrate",
                payload_image_prefix="private-",
                runtime="linux-x64",
                token="fixture-token",
            )
        self.assertEqual({key: value for key, value in result.items() if key != "offline_restore"}, expected_metadata)
        self.assertEqual(result["offline_restore"], "verified")
        offline_restore.assert_called_once()
        self.assertEqual(self.marker_path.read_bytes(), before)
        self.assertEqual(selector.call_args.args[0][selector.call_args.args[0].index("--expected-run-id") + 1], "12345")
        self.assertEqual(importer.call_args.kwargs["expected_image_digest"], self.marker["digest"])
        self.assertEqual(importer.call_args.kwargs["artifact_name"], "books-migrate-linux-x64")

    def test_rejects_marker_for_another_ci_attempt(self) -> None:
        selected = subprocess.CompletedProcess([], 0, json.dumps({"outcome": "success", "selected": {}}), "")
        with patch.object(operation.subprocess, "run", return_value=selected), \
                patch.object(operation.pin_release_payload, "_require_shared_lock", return_value=(self.deploy_root, "token")), \
                patch.object(operation.import_legacy_release_payload, "import_legacy_artifact") as importer:
            with self.assertRaisesRegex(operation.LegacyPinOperationError, "does not match"):
                operation.pin_marker(
                    slot="current", app_instance="primary", deploy_root=self.deploy_root,
                    repository="Grumlebob/BlazorAutoAppTemplate",
                    repository_url="https://github.com/Grumlebob/BlazorAutoAppTemplate",
                    app_image_base="ghcr.io/grumlebob/books",
                    migration_artifact_name="books-migrate-linux-x64",
                    migration_bundle_name="books-migrate", payload_image_prefix="private-",
                    runtime="linux-x64", token="fixture-token",
                )
        importer.assert_not_called()

    def test_offline_restore_uses_local_pin_without_github_token(self) -> None:
        pin_dir = self.deploy_root / ("legacy-987-" + "c" * 64)
        metadata = {
            "manifest_sha256": "d" * 64,
            "bundle_filename": "books-migrate",
            "bundle_sha256": "e" * 64,
        }
        observed = {"token_absent": False}

        def restore_local(_pin_dir: Path, output_dir: Path, **kwargs: str) -> dict:
            observed["token_absent"] = "GITHUB_TOKEN" not in os.environ
            output_dir.mkdir()
            (output_dir / "release-manifest.json").write_bytes(b"manifest")
            (output_dir / "books-migrate").write_bytes(b"bundle")
            return {"pin_key": pin_dir.name}

        with patch.dict(os.environ, {"GITHUB_TOKEN": "fixture-token"}), \
                patch.object(operation.pin_release_payload, "validate", return_value=metadata), \
                patch.object(operation.pin_release_payload, "restore", side_effect=restore_local) as restore, \
                patch.object(operation, "sha256_file", side_effect=lambda path: metadata[
                    "manifest_sha256" if Path(path).name == "release-manifest.json" else "bundle_sha256"
                ]):
            operation._verify_offline_restore(
                pin_dir=pin_dir,
                repository_url="https://github.com/Grumlebob/BlazorAutoAppTemplate",
                summary={
                    "source_sha": self.marker["source_sha"],
                    "frontend_profile": "React",
                    "acceptance_profile": "ReactPublicV1",
                },
                runtime="linux-x64",
                app_image="ghcr.io/grumlebob/books-react",
                bundle_name="books-migrate",
                payload_image_prefix="private-",
            )
            token_restored = os.environ.get("GITHUB_TOKEN") == "fixture-token"

        self.assertTrue(observed["token_absent"])
        self.assertTrue(token_restored)
        restore.assert_called_once()

    def test_workflow_is_read_only_except_for_locked_local_pin_creation(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/pin-localsinglenode-legacy-release.yml").read_text(encoding="utf-8")
        self.assertIn("actions: read\n  contents: read", workflow)
        self.assertNotIn("packages:", workflow)
        self.assertIn("with-deploy-lock.sh", workflow)
        self.assertIn("pin-legacy-release.py", workflow)
        self.assertIn("Offline restore:", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    import unittest

    unittest.main()
