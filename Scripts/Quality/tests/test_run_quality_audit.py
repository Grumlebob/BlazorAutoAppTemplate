"""Regression checks for audit scope, failure reporting, and container cleanup."""

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from Scripts.Quality import run_quality_audit as audit
from Scripts.Quality import qlty_audit


class QualityAuditTests(unittest.TestCase):
    def test_qlty_clears_git_overrides_and_disables_telemetry(self):
        with patch.dict(os.environ, {"GIT_DIR": "private-worktree", "GIT_WORK_TREE": "private-source",
                                     "git_config_count": "1", "QLTY_TELEMETRY": "on"}):
            environment = qlty_audit.analysis_environment()
        self.assertFalse(any(key.upper().startswith("GIT_") for key in environment))
        self.assertEqual(environment["QLTY_TELEMETRY"], "off")

    def test_snapshot_uses_tracked_working_files_and_excludes_untracked_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            repo, snapshot = root / "repo", root / "snapshot"
            repo.mkdir()
            snapshot.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "source.cs").write_text("original", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "source.cs"], check=True)
            (repo / "source.cs").write_text("working change", encoding="utf-8")
            (repo / ".env").write_text("private local value", encoding="utf-8")
            result = audit.snapshot_source(repo, snapshot)
            self.assertEqual(result["trackedFilesCopied"], 1)
            self.assertEqual((snapshot / "source.cs").read_text(), "working change")
            self.assertFalse((snapshot / ".env").exists())

    def test_web_targets_reject_ambiguous_or_sensitive_urls(self):
        for target in (None, "file:///tmp/a", "https://user:pass@example.org",
                       "http://127.0.0.1:8080", "https://example.org/?token=x"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                audit.validate_target("zap", target)
        audit.validate_target("sitespeed", "http://host.docker.internal:8080/")

    def test_image_target_requires_immutable_digest(self):
        for target in ("image:latest", "image@sha256:abc", "--help@sha256:" + "a" * 64):
            with self.subTest(target=target), self.assertRaises(ValueError):
                audit.validate_target("trivy-image", target)
        audit.validate_target("trivy-image", "registry.example/app@sha256:" + "a" * 64)

    def test_missing_malformed_reports_and_scanner_errors_never_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = Path(temporary)
            with self.assertRaises(ValueError):
                audit.read_results("trivy-source", reports, 0)
            (reports / "trivy.json").write_text("{}")
            with self.assertRaises(ValueError):
                audit.read_results("trivy-source", reports, 0)
            (reports / "trivy.json").write_text("not JSON")
            with self.assertRaises(ValueError):
                audit.read_results("trivy-source", reports, 0)
            (reports / "zap.json").write_text(json.dumps({"site": [{"alerts": []}]}))
            with self.assertRaises(ValueError):
                audit.read_results("zap", reports, 3)

    def test_findings_are_informational_but_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = Path(temporary)
            (reports / "trivy.json").write_text(json.dumps({
                "SchemaVersion": 2, "ArtifactName": "/src", "Results": [{
                    "Vulnerabilities": [{"Severity": "CRITICAL"}],
                    "Secrets": [{"Severity": "HIGH"}],
                }],
            }))
            result = audit.read_results("trivy-source", reports, 0)
            self.assertEqual(result["findings"], {"Secrets:HIGH": 1, "Vulnerabilities:CRITICAL": 1})
            (reports / "zap.json").write_text(json.dumps({"site": [{"alerts": [
                {"riskdesc": "Medium (High)"},
            ]}]}))
            for code in (0, 1, 2):
                self.assertEqual(audit.read_results("zap", reports, code)["alerts"], {"Medium (High)": 1})

    def test_timeout_records_failure_and_removes_only_its_container(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary).resolve()
            args = argparse.Namespace(tool="zap", repo_root=repo, target="http://fixture:8080/",
                                      network=None, timeout_minutes=1)
            calls = []

            def docker(command, **kwargs):
                calls.append(command)
                if command[:2] == ["docker", "run"]:
                    raise subprocess.TimeoutExpired(command, 60)
                return subprocess.CompletedProcess(command, 0)

            with patch.object(audit, "git", side_effect=[b"a" * 40, b""]), \
                    patch.object(audit.subprocess, "run", side_effect=docker), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.run_audit(args), 1)
            summary = json.loads(next(repo.glob("TestResults/QualityTools/*/summary.json")).read_text())
            self.assertEqual(summary["status"], "timeout")
            run = next(command for command in calls if command[:2] == ["docker", "run"])
            owned_name = run[run.index("--name") + 1]
            cleanup = [command for command in calls if command[:2] == ["docker", "rm"]]
            self.assertTrue(cleanup)
            self.assertTrue(all(command == ["docker", "rm", "--force", owned_name] for command in cleanup))

    def test_cleanup_distinguishes_already_removed_container_from_daemon_failure(self):
        with patch.object(audit.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 1, stderr="Error response from daemon: No such container: quality-audit-test")):
            audit.remove_container("quality-audit-test")
        with patch.object(audit.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 1, stderr="Cannot connect to the Docker daemon")), self.assertRaises(ValueError):
            audit.remove_container("quality-audit-test")

    def test_qlty_archive_hash_is_required_before_writing_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive, binary = Path(temporary) / "qlty.zip", Path(temporary) / "qlty.exe"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("qlty.exe", b"verified binary")
            with self.assertRaises(ValueError):
                qlty_audit.extract_binary(archive, "0" * 64, binary)
            self.assertFalse(binary.exists())

    def test_qlty_extraction_copies_only_the_expected_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, binary = root / "qlty.zip", root / "qlty.exe"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("qlty.exe", b"verified binary")
                package.writestr("../unexpected.txt", b"must not be extracted")
            qlty_audit.extract_binary(archive, hashlib.sha256(archive.read_bytes()).hexdigest(), binary)
            self.assertEqual(binary.read_bytes(), b"verified binary")
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["qlty.exe", "qlty.zip"])

    def test_qlty_rejects_invalid_sarif_and_accepts_explicit_zero_findings(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "qlty.sarif"
            for invalid in ({}, {"version": "2.1.0", "runs": []},
                            {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "other"}}, "results": []}]}):
                report.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    qlty_audit.summarize_sarif(report)
            report.write_text(json.dumps({"version": "2.1.0", "runs": [
                {"tool": {"driver": {"name": "qlty"}}, "results": []},
            ]}))
            self.assertEqual(qlty_audit.summarize_sarif(report)["reportedLocations"], 0)

    def test_qlty_counts_mirrored_duplication_locations_as_one_group(self):
        def location(path):
            return {"physicalLocation": {"artifactLocation": {"uri": path}, "region": {"startLine": 1, "endLine": 20}}}

        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "qlty.sarif"
            report.write_text(json.dumps({"version": "2.1.0", "runs": [
                {"tool": {"driver": {"name": "qlty"}}, "results": [
                    {"ruleId": "qlty:similar-code", "locations": [location("a.cs")], "relatedLocations": [location("b.cs")]},
                    {"ruleId": "qlty:similar-code", "locations": [location("b.cs")], "relatedLocations": [location("a.cs")]},
                ]},
            ]}))
            result = qlty_audit.summarize_sarif(report)
            self.assertEqual(result["reportedLocations"], 2)
            self.assertEqual(result["duplicationGroups"], 1)


if __name__ == "__main__":
    unittest.main()
