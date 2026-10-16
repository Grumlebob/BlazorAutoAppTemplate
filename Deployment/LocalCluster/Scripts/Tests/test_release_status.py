from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
from unittest import TestCase
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "release-status.py"
sys.path.insert(0, str(SCRIPT.parent / "Component" / "lib"))
sys.path.insert(0, str(SCRIPT.parents[3] / "Deployment/Common/Scripts/Component/lib"))
sys.path.insert(0, str(SCRIPT.parents[3] / "Scripts/Frontend"))

import importlib.util

spec = importlib.util.spec_from_file_location("local_cluster_release_status", SCRIPT)
assert spec is not None and spec.loader is not None
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


class LocalClusterReleaseStatusTests(TestCase):
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

