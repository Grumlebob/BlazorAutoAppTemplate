from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from Deployment.Common.Scripts.Tests.test_registry_inventory import FixtureClient, PACKAGE, REPOSITORY


SCRIPT = Path(__file__).resolve().parents[1] / "registry-inventory.py"
SPEC = importlib.util.spec_from_file_location("registry_inventory_cli", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RegistryInventoryCliTests(unittest.TestCase):
    def test_explicit_bootstrap_reference_is_reported_without_changing_release_admission(self):
        client = FixtureClient()
        reference = client.add_bootstrap()
        base = ["--repository", REPOSITORY, "--username", "fixture", "--package", PACKAGE + "=private"]
        with patch.dict(os.environ, {"GITHUB_TOKEN": "fixture"}):
            code, output, error = self.invoke(base + ["--retain-manifest", "@".join(reference)], lambda *args: client)
            duplicate, _, duplicate_error = self.invoke(base + ["--retain-manifest", "@".join(reference)] * 2, lambda *args: client)
        self.assertEqual(0, code, error)
        self.assertEqual(1, json.loads(output)["retained_manifests"])
        self.assertEqual("not-evaluated", json.loads(output)["protection"])
        self.assertEqual(1, duplicate)
        self.assertIn("duplicate", duplicate_error)

    def invoke(self, arguments, factory):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = MODULE.main(arguments, client_factory=factory)
        return code, output.getvalue(), error.getvalue()

    def test_reports_stored_bytes_without_deletion_or_disposable_classification(self):
        arguments = ["--repository", REPOSITORY, "--username", "fixture", "--package", PACKAGE + "=private"]
        with patch.dict(os.environ, {"GITHUB_TOKEN": "fixture-token-never-print"}):
            code, output, error = self.invoke(arguments, lambda username, token: FixtureClient())
        self.assertEqual(0, code, error)
        result = json.loads(output)
        self.assertEqual("none", result["mutation"])
        self.assertEqual("not-evaluated", result["protection"])
        self.assertEqual(3, result["versions"])
        self.assertGreater(result["stored"]["final_bytes"], 123)
        self.assertEqual(0, result["stored"]["staging_bytes"])
        self.assertNotIn("fixture-token-never-print", output + error)

    def test_missing_credentials_and_duplicate_package_fail_before_network_access(self):
        def forbidden(*arguments):
            raise AssertionError("Invalid request reached a network client")

        base = ["--repository", REPOSITORY, "--username", "fixture", "--package", PACKAGE + "=private"]
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GH_TOKEN": ""}):
            code, output, error = self.invoke(base, forbidden)
        self.assertEqual(1, code)
        self.assertEqual("", output)
        with patch.dict(os.environ, {"GITHUB_TOKEN": "fixture"}):
            code, _, error = self.invoke(base + ["--package", PACKAGE + "=private"], forbidden)
        self.assertEqual(1, code)
        self.assertIn("duplicate", error)


if __name__ == "__main__":
    unittest.main()
