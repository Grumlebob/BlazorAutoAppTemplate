#!/usr/bin/env python3
"""Exercise the actual runner identity probe without SSH or runner mutation."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "install-github-runner.sh"
PROBE = SOURCE.read_text().split('RUNNER_STATE="$(ssh', 1)[1].split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
REPO = "https://github.com/example/template"
NAME = "fixture-books"


class RunnerIdentityTests(unittest.TestCase):
    def probe(self, content):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".runner").write_text(content)
            result = subprocess.run(
                [sys.executable, "-c", PROBE], text=True, capture_output=True,
                env=dict(os.environ, RUNNER_DIR=directory, EXPECTED_REPO_URL=REPO, EXPECTED_RUNNER_NAME=NAME),
                check=True,
            )
            return result.stdout.strip()

    def test_complete_identity_is_reused(self):
        self.assertEqual("ok", self.probe(json.dumps({"agentName": NAME, "gitHubUrl": REPO})))
        self.assertEqual("ok", self.probe(json.dumps({"agentName": NAME, "serverUrl": REPO + "/"})))

    def test_missing_or_malformed_identity_is_rejected(self):
        for content in ("not JSON", "[]", "null", "{}", json.dumps({"agentName": NAME}), json.dumps({"gitHubUrl": REPO})):
            with self.subTest(content=content):
                self.assertEqual("broken", self.probe(content))

    def test_foreign_runner_identity_is_rejected(self):
        self.assertEqual("wrong-name", self.probe(json.dumps({"agentName": "other", "gitHubUrl": REPO})))
        self.assertEqual("wrong-repo", self.probe(json.dumps({"agentName": NAME, "gitHubUrl": "https://github.com/example/other"})))


if __name__ == "__main__":
    unittest.main()
