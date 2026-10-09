#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "validate_release_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_release_manifest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bundle_dir = self.root / "migrations"
        self.bundle_dir.mkdir()
        self.bundle = self.bundle_dir / "books-migrate"
        self.bundle.write_bytes(b"validated migration bundle")
        self.digest = "sha256:" + "a" * 64
        self.manifest = {
            "schema_version": 1,
            "repository": "https://github.com/grumlebob/BlazorAutoAppTemplate",
            "commit_sha": "1" * 40,
            "ci_run_id": 123,
            "attempt": 1,
            "image_ref": "ghcr.io/grumlebob/books:" + "1" * 40,
            "image_digest": self.digest,
            "ordered_migration_ids": ["20260922000000_Initial"],
            "bundle": {
                "file": self.bundle.name,
                "sha256": hashlib.sha256(self.bundle.read_bytes()).hexdigest(),
                "runtime": "linux-x64",
            },
            "tools": {"dotnet_sdk": "10.0.301"},
        }
        self.registry = {"Descriptor": {"digest": self.digest}}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self) -> str:
        return MODULE.validate_manifest(
            self.manifest,
            expected_repository="https://github.com/grumlebob/BlazorAutoAppTemplate",
            expected_sha="1" * 40,
            expected_ci_run_id="123",
            expected_ci_run_attempt="1",
            expected_image="ghcr.io/grumlebob/books",
            expected_bundle_name=self.bundle.name,
            bundle_dir=self.bundle_dir,
            registry_payload=self.registry,
        )

    def test_valid_contract(self) -> None:
        self.assertEqual(self.validate(), self.digest)

    def test_accepts_docker_verbose_list_response(self) -> None:
        self.registry = [{"Descriptor": {"digest": self.digest}}]
        self.assertEqual(self.validate(), self.digest)

    def test_accepts_local_docker_image_inspect_repo_digests(self) -> None:
        self.registry = {
            "RepoDigests": [f"ghcr.io/grumlebob/books@{self.digest}"],
        }
        self.assertEqual(self.validate(), self.digest)

    def test_rejects_bundle_traversal(self) -> None:
        self.manifest["bundle"]["file"] = "../outside"
        with self.assertRaises(MODULE.ManifestError):
            self.validate()

    def test_rejects_bundle_checksum_mismatch(self) -> None:
        self.manifest["bundle"]["sha256"] = "b" * 64
        with self.assertRaises(MODULE.ManifestError):
            self.validate()

    def test_rejects_registry_digest_mismatch(self) -> None:
        self.registry["Descriptor"]["digest"] = "sha256:" + "c" * 64
        with self.assertRaises(MODULE.ManifestError):
            self.validate()

    def test_rejects_incomplete_manifest(self) -> None:
        del self.manifest["ordered_migration_ids"]
        with self.assertRaises(MODULE.ManifestError):
            self.validate()

    def test_rejects_wrong_ci_attempt(self) -> None:
        with self.assertRaises(MODULE.ManifestError):
            MODULE.validate_manifest(
                self.manifest,
                expected_repository="https://github.com/Grumlebob/BlazorAutoAppTemplate",
                expected_sha="1" * 40,
                expected_ci_run_id="123",
                expected_ci_run_attempt="2",
                expected_image="ghcr.io/grumlebob/books",
                expected_bundle_name="books-migrate",
                bundle_dir=self.bundle_dir,
                registry_payload={"Descriptor": {"digest": "sha256:" + "a" * 64}},
            )


if __name__ == "__main__":
    unittest.main()
