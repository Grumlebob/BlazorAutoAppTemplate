from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "release-status.py"
REPO_ROOT = SCRIPT.parents[3]
sys.path.insert(0, str(SCRIPT.parent / "Component" / "lib"))
sys.path.insert(0, str(SCRIPT.parents[3] / "Deployment/Common/Scripts/Component/lib"))
sys.path.insert(0, str(SCRIPT.parents[3] / "Scripts/Frontend"))

import importlib.util

spec = importlib.util.spec_from_file_location("local_cluster_release_status", SCRIPT)
assert spec is not None and spec.loader is not None
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


class LocalClusterReleaseStatusTests(TestCase):
    def test_release_status_workflow_uses_the_tracked_runner_settings_reader(self):
        reader = "Deployment/LocalCluster/Scripts/Component/lib/read-deploy-setting.py"
        self.assertTrue((REPO_ROOT / reader).is_file())
        workflow = (REPO_ROOT / ".github/workflows/release-status.yml").read_text(encoding="utf-8")
        self.assertIn(f"python3 {reader} runner_name", workflow)

    def test_reports_controlled_failure_reason_to_workflow_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_path = Path(temp_dir) / "summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}):
                with patch.object(
                    status,
                    "snapshot",
                    side_effect=status.ReleaseStatusError("Ansible could not inspect every LocalCluster app server"),
                ):
                    with redirect_stderr(io.StringIO()):
                        self.assertEqual(status.main(), 1)
            summary = summary_path.read_text(encoding="utf-8")
        self.assertIn("Reason: Ansible could not inspect every LocalCluster app server", summary)
        self.assertIn("Protected state was not changed.", summary)

    def test_withholds_unexpected_exception_details_from_workflow_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_path = Path(temp_dir) / "summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}):
                with patch.object(status, "snapshot", side_effect=OSError("credential=secret")):
                    with redirect_stderr(io.StringIO()):
                        self.assertEqual(status.main(), 1)
            summary = summary_path.read_text(encoding="utf-8")
        self.assertIn("Reason: unexpected local inspection error; details withheld", summary)
        self.assertNotIn("credential", summary)

    def test_summarizes_ansible_authentication_and_connectivity_failures(self):
        failures = (
            ("Permission denied (publickey).", "SSH authentication failed while inspecting LocalCluster app servers"),
            ("Connection timed out", "SSH connectivity or host verification failed while inspecting LocalCluster app servers"),
        )
        for diagnostic, expected in failures:
            with self.subTest(diagnostic=diagnostic), tempfile.TemporaryDirectory() as temp_dir:
                result = subprocess.CompletedProcess(args=["ansible"], returncode=2, stdout="", stderr=diagnostic)
                with patch.object(status.subprocess, "run", return_value=result):
                    with self.assertRaises(status.ReleaseStatusError) as error:
                        status.ansible_results("ansible.builtin.stat", "path=/opt/books/release.json", Path(temp_dir))
                self.assertEqual(str(error.exception), expected)

    def test_reads_one_consistent_marker_from_every_app_server(self):
        marker = {
            "source_repo_url": "https://github.com/Grumlebob/BlazorAutoAppTemplate",
            "source_sha": "a" * 40,
            "ci_run_id": "12345",
        }
        encoded = base64.b64encode(json.dumps(marker).encode("utf-8")).decode("ascii")
        stats = [
            {"stat": {"exists": True, "islnk": False}},
            {"stat": {"exists": True, "islnk": False}},
        ]
        slurps = [{"content": encoded}, {"content": encoded}]
        with patch.object(status, "ansible_results", side_effect=[stats, slurps]):
            result = status.read_remote_marker("/opt/books/release.json", required=True)
        self.assertEqual(result, marker)

    def test_missing_optional_marker_is_allowed_only_when_every_app_server_agrees(self):
        missing = [
            {"stat": {"exists": False, "islnk": False}},
            {"stat": {"exists": False, "islnk": False}},
        ]
        with patch.object(status, "ansible_results", return_value=missing):
            self.assertIsNone(status.read_remote_marker("/opt/books/release-state/previous.json", required=False))
            with self.assertRaises(status.ReleaseStatusError):
                status.read_remote_marker("/opt/books/release.json", required=True)

    def test_rejects_symlinked_or_disagreeing_release_markers(self):
        symlink = [{"stat": {"exists": True, "islnk": True}}]
        mixed = [
            {"stat": {"exists": True, "islnk": False}},
            {"stat": {"exists": False, "islnk": False}},
        ]
        for records in (symlink, mixed):
            with self.subTest(records=records), patch.object(status, "ansible_results", return_value=records):
                with self.assertRaises(status.ReleaseStatusError):
                    status.read_remote_marker("/opt/books/release-state/previous.json", required=False)

    def test_rejects_different_marker_bytes_across_app_servers(self):
        markers = [
            {"source_sha": "a" * 40},
            {"source_sha": "b" * 40},
        ]
        encoded = [base64.b64encode(json.dumps(marker).encode("utf-8")).decode("ascii") for marker in markers]
        with patch.object(status, "ansible_results", side_effect=[
            [{"stat": {"exists": True, "islnk": False}}, {"stat": {"exists": True, "islnk": False}}],
            [{"content": encoded[0]}, {"content": encoded[1]}],
        ]):
            with self.assertRaises(status.ReleaseStatusError):
                status.read_remote_marker("/opt/books/release.json", required=True)

