from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch


SCRIPT = Path(__file__).resolve().parents[1] / "migration_staging_artifact.py"
SPEC = importlib.util.spec_from_file_location("migration_staging_artifact", SCRIPT)
assert SPEC and SPEC.loader
staging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(staging)
FIXTURE = Path(__file__).parent / "fixtures" / "dotnet-ef-migration-list.json"


class MigrationStagingArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="blazorautoapp-migration-staging-")
        self.root = Path(self.temp.name)
        self.bundle_name = "blazorautoapp-migrations-linux-x64"
        self.bundle_bytes = b"verified fixture migration bundle"
        self.bundle = self.root / self.bundle_name
        self.bundle.write_bytes(self.bundle_bytes)
        self.context = {
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": "Grumlebob/BlazorAutoAppTemplate",
            "GITHUB_SHA": "a" * 40,
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_ATTEMPT": "2",
        }
        self.provenance = {
            "schema_version": 1,
            "repository": "https://github.com/Grumlebob/BlazorAutoAppTemplate",
            "source_sha": self.context["GITHUB_SHA"],
            "run_id": self.context["GITHUB_RUN_ID"],
            "run_attempt": self.context["GITHUB_RUN_ATTEMPT"],
            "bundle_filename": self.bundle_name,
            "runtime": "net10.0",
            "dotnet_sdk_version": "10.0.303",
            "ordered_migration_ids": ["20260525172002_InitialTemplateSchema", "20260526083400_UserOwnedBooks"],
            "bundle_sha256": hashlib.sha256(self.bundle_bytes).hexdigest(),
        }
        self.provenance_path = self.root / staging.PROVENANCE_FILENAME
        self.write_provenance()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_provenance(self) -> None:
        self.provenance_path.write_text(json.dumps(self.provenance, indent=2), encoding="utf-8")

    def validate(self, *, env=None, directory=None) -> dict[str, object]:
        return staging.validate_staging_artifact(
            directory or self.root,
            self.bundle_name,
            "net10.0",
            self.context if env is None else env,
        )

    def test_observed_dotnet_ef_fixture_is_strict_and_ordered(self) -> None:
        migration_ids = staging.parse_migration_list(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(len(migration_ids), 3)
        self.assertEqual(migration_ids[0], "20260525172002_InitialTemplateSchema")
        self.assertEqual(migration_ids[-1], "20260528104203_NormalizeBooksForAuthorBooks")
        self.assertEqual(migration_ids[1], "20260526083400_UserOwnedBooks")

    def test_rejects_unknown_root_and_row_shapes(self) -> None:
        for output in (
            '{"migrations": []}',
            "null",

            '[{"id":"one","name":"one","safeName":"one","applied":null,"extra":1}]',
            '[{"name":"one","safeName":"one","applied":null}]',
            '[1]',
            '[{"id":"one","name":"one","safeName":"one","applied":"unknown"}]',
        ):
            with self.subTest(output=output):
                with self.assertRaises(staging.StagingArtifactError):
                    staging.parse_migration_list(output)

    def test_rejects_missing_empty_or_duplicate_migration_id(self) -> None:
        base = {"id": "one", "name": "one", "safeName": "one", "applied": None}
        with self.assertRaises(staging.StagingArtifactError):
            staging.parse_migration_list(json.dumps([dict(base, id="")]))
        with self.assertRaises(staging.StagingArtifactError):
            staging.parse_migration_list(json.dumps([dict(base, id="   ")]))
        with self.assertRaises(staging.StagingArtifactError):
            staging.parse_migration_list(json.dumps([base, base]))

    def test_create_records_exact_command_context_sdk_and_hash(self) -> None:
        migration_output = FIXTURE.read_text(encoding="utf-8")
        responses = iter(
            [
                type("Completed", (), {"stdout": migration_output})(),
                type("Completed", (), {"stdout": "10.0.303\n"})(),
            ]
        )
        self.provenance_path.unlink()
        with patch.object(staging.subprocess, "run", side_effect=lambda *args, **kwargs: next(responses)) as run:
            result = staging.create_staging_artifact(
                self.root,
                self.bundle_name,
                "net10.0",
                Path(__file__).resolve().parents[3],
                self.context,
            )
        expected_command = [
            "dotnet", "ef", "migrations", "list", "--no-connect", "--json", "--no-color",
            "--no-build", "--project", "BlazorAutoApp/BlazorAutoApp.csproj",
            "--startup-project", "BlazorAutoApp/BlazorAutoApp.csproj", "--configuration", "Release",
        ]
        self.assertEqual(run.call_args_list, [
            call(expected_command, cwd=Path(__file__).resolve().parents[3], check=True, capture_output=True, text=True),
            call(["dotnet", "--version"], cwd=Path(__file__).resolve().parents[3], check=True, capture_output=True, text=True),
        ])
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["run_id"], "12345")
        self.assertEqual(result["run_attempt"], "2")
        self.assertEqual(result["dotnet_sdk_version"], "10.0.303")
        self.assertEqual(result["bundle_sha256"], hashlib.sha256(self.bundle_bytes).hexdigest())
        saved = json.loads(self.provenance_path.read_text(encoding="utf-8"))
        self.assertEqual(saved, result)
        self.assertEqual(set(saved), staging.PROVENANCE_KEYS)

    def test_create_rejects_missing_bundle_and_unknown_migration_json(self) -> None:
        self.bundle.unlink()
        with self.assertRaises(staging.StagingArtifactError):
            staging.create_staging_artifact(self.root, self.bundle_name, "net10.0", self.root, self.context)
        self.bundle.write_bytes(self.bundle_bytes)
        with patch.object(staging.subprocess, "run", return_value=type("Completed", (), {"stdout": '{"items": []}'})()):
            with self.assertRaises(staging.StagingArtifactError):
                staging.create_staging_artifact(self.root, self.bundle_name, "net10.0", self.root, self.context)

    def test_accepts_exact_two_file_staging_envelope(self) -> None:
        result = self.validate()
        self.assertEqual(result["ordered_migration_ids"], self.provenance["ordered_migration_ids"])

    def test_rejects_extra_or_missing_provenance_keys(self) -> None:
        self.provenance["unexpected"] = "value"
        self.write_provenance()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()
        del self.provenance["unexpected"]
        del self.provenance["runtime"]
        self.write_provenance()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()

    def test_rejects_boolean_or_unsupported_schema_version(self) -> None:
        for value in (True, 2, "1"):
            with self.subTest(value=value):
                self.provenance["schema_version"] = value
                self.write_provenance()
                with self.assertRaises(staging.StagingArtifactError):
                    self.validate()

    def test_rejects_duplicate_json_keys(self) -> None:
        raw = json.dumps(self.provenance)
        self.provenance_path.write_text(raw[:-1] + ',"runtime":"net10.0"}', encoding="utf-8")
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()

    def test_rejects_wrong_context_or_release_setting(self) -> None:
        cases = (
            ("repository", "https://github.com/other/repo"),
            ("source_sha", "b" * 40),
            ("run_id", "999"),
            ("run_attempt", "1"),
            ("bundle_filename", "other-bundle"),
            ("runtime", "linux-x64"),
        )
        for key, value in cases:
            with self.subTest(key=key):
                self.provenance[key] = value
                self.write_provenance()
                with self.assertRaises(staging.StagingArtifactError):
                    self.validate()
                self.provenance[key] = {
                    "repository": "https://github.com/Grumlebob/BlazorAutoAppTemplate",
                    "source_sha": self.context["GITHUB_SHA"],
                    "run_id": "12345",
                    "run_attempt": "2",
                    "bundle_filename": self.bundle_name,
                    "runtime": "net10.0",
                }[key]

    def test_rejects_malformed_sdk_version_and_identity_types(self) -> None:
        self.provenance["dotnet_sdk_version"] = "10.0"
        self.write_provenance()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()
        self.provenance["dotnet_sdk_version"] = "10.0.303"
        self.provenance["run_id"] = 12345
        self.write_provenance()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()

    def test_rejects_non_array_or_invalid_migration_ids(self) -> None:
        for value in (
            "migration",
            ["one", ""],
            ["one", "  "],
            ["one", 2],
            ["one", "one"],
        ):
            with self.subTest(value=value):
                self.provenance["ordered_migration_ids"] = value
                self.write_provenance()
                with self.assertRaises(staging.StagingArtifactError):
                    self.validate()
        self.provenance["ordered_migration_ids"] = []

    def test_rejects_malformed_or_mismatched_bundle_hash(self) -> None:
        self.provenance["bundle_sha256"] = "A" * 64
        self.write_provenance()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()
        self.provenance["bundle_sha256"] = "0" * 64
        self.write_provenance()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()

    def test_rejects_missing_or_extra_root_entries(self) -> None:
        self.bundle.unlink()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()
        self.bundle.write_bytes(self.bundle_bytes)
        extra = self.root / "extra.txt"
        extra.write_text("extra", encoding="utf-8")
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()
        extra.unlink()
        (self.root / "extra-directory").mkdir()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()

    def test_rejects_non_regular_required_files(self) -> None:
        self.bundle.unlink()
        self.bundle.mkdir()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()
        self.bundle.rmdir()
        try:
            self.bundle.symlink_to(self.root / "outside")
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlink creation unavailable: {error}")
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()

    def test_rejects_symlinked_provenance_and_directory(self) -> None:
        self.provenance_path.unlink()
        try:
            self.provenance_path.symlink_to(self.bundle)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlink creation unavailable: {error}")
        with self.assertRaises(staging.StagingArtifactError):
            self.validate()
        with self.assertRaises(staging.StagingArtifactError):
            self.validate(directory=self.root / "missing")

    def test_rejects_unsafe_bundle_filename_and_provenance_collision(self) -> None:
        for name in ("../bundle", "folder/bundle", "folder\\bundle", "migration-provenance.json", ""):
            with self.subTest(name=name):
                with self.assertRaises(staging.StagingArtifactError):
                    staging.validate_staging_artifact(self.root, name, "net10.0", self.context)


if __name__ == "__main__":
    unittest.main()