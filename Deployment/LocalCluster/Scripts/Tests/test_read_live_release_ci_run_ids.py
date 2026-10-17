#!/usr/bin/env python3
"""Fixtures for the read-only live LocalCluster release identity check."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "Component/lib/read-live-release-ci-run-ids.py"
SPEC = importlib.util.spec_from_file_location("read_live_release_ci_run_ids", SCRIPT)
assert SPEC and SPEC.loader
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)


SOURCE = "https://github.com/example/books"
REPOSITORY = "example/books"


def host(run_id="1234", attempt="2", repository=REPOSITORY, source=SOURCE):
    labels = {
        "org.opencontainers.image.source": source,
        "localcluster.ci.repository": repository,
        "localcluster.ci.run_id": run_id,
        "localcluster.ci.run_attempt": attempt,
    }
    return {"rc": 0, "stdout": f"node-app1\tsha256:fixture\t{json.dumps(labels)}\n"}


class ValidatedLiveRunIdsTests(unittest.TestCase):
    def test_returns_exact_current_run_id_when_all_app_servers_agree(self):
        self.assertEqual(["1234"], reader.validated_run_ids([host(), host()], SOURCE, REPOSITORY))

    def test_mixed_release_identities_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "different CI release identities"):
            reader.validated_run_ids([host(), host(run_id="1235")], SOURCE, REPOSITORY)

    def test_mismatched_repository_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "different source repository"):
            reader.validated_run_ids([host(source="https://github.com/other/repo")], SOURCE, REPOSITORY)

    def test_missing_run_id_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no valid CI run ID"):
            reader.validated_run_ids([host(run_id="unknown")], SOURCE, REPOSITORY)

    def test_unreachable_host_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "could not inspect every app server"):
            reader.validated_run_ids([{"rc": 255, "stdout": ""}], SOURCE, REPOSITORY)

    def test_ansible_failure_summary_identifies_auth_failure_without_raw_message(self):
        summary = reader.ansible_failure_summary([
            ("node-app1", {"unreachable": True, "msg": "Failed to connect: Permission denied (publickey)"}),
        ])
        self.assertEqual(
            "Ansible could not inspect every app server (node-app1: SSH authentication failed)",
            summary,
        )
        self.assertNotIn("publickey", summary)

    def test_ansible_failure_summary_reports_dns_and_network_categories(self):
        summary = reader.ansible_failure_summary([
            ("node-app1", {"unreachable": True, "msg": "Could not resolve hostname"}),
            ("node-app2", {"unreachable": True, "msg": "No route to host"}),
        ])
        self.assertIn("node-app1: DNS resolution failed", summary)
        self.assertIn("node-app2: SSH network connection failed", summary)

    def test_no_running_app_server_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no app-server identity"):
            reader.validated_run_ids([], SOURCE, REPOSITORY)

    def test_remote_command_checks_app_root_and_avoids_ansible_jinja_templates(self):
        command = reader.remote_identity_command("books", "/opt/books")
        self.assertIn("test \"$root_app\" = books", command)
        self.assertIn("docker compose --env-file .compose.env ps -q web", command)
        self.assertNotIn("--format '{{", command)

    def test_unsafe_deploy_root_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "deploy_root is malformed"):
            reader.remote_identity_command("books", "/opt/books/../other")


if __name__ == "__main__":
    unittest.main()
