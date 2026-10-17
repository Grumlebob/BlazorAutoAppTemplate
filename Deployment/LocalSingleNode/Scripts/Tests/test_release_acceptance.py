import json
import sys
import tempfile
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
from read_release_acceptance import resolve_ci_run_id, resolve_release_acceptance


class ReleaseAcceptanceTests(unittest.TestCase):
    def resolve(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return resolve_release_acceptance(path)

    def test_schema_one_without_profile_fields_is_legacy_blazor(self):
        self.assertEqual(("BlazorAuto", "BlazorAutoV1"), self.resolve({"manifest_schema_version": 1}))

    def test_schema_one_with_explicit_blazor_pair_is_accepted(self):
        self.assertEqual(
            ("BlazorAuto", "BlazorAutoV1"),
            self.resolve({
                "manifest_schema_version": 1,
                "frontend_profile": "BlazorAuto",
                "acceptance_profile": "BlazorAutoV1",
            }),
        )

    def test_schema_one_cannot_select_react(self):
        with self.assertRaisesRegex(ValueError, "schema-v1"):
            self.resolve({
                "manifest_schema_version": 1,
                "frontend_profile": "React",
                "acceptance_profile": "ReactPublicV1",
            })

    def test_schema_one_null_profile_fields_are_not_treated_as_legacy_absence(self):
        with self.assertRaisesRegex(ValueError, "schema-v1"):
            self.resolve({
                "manifest_schema_version": 1,
                "frontend_profile": None,
                "acceptance_profile": None,
            })

    def test_schema_two_accepts_both_matching_pairs(self):
        for frontend, acceptance in (
            ("BlazorAuto", "BlazorAutoV1"),
            ("React", "ReactPublicV1"),
        ):
            with self.subTest(frontend=frontend):
                self.assertEqual(
                    (frontend, acceptance),
                    self.resolve({
                        "manifest_schema_version": 2,
                        "frontend_profile": frontend,
                        "acceptance_profile": acceptance,
                    }),
                )

    def test_schema_two_rejects_missing_unknown_and_mismatched_identity(self):
        invalid = (
            {"manifest_schema_version": 2},
            {"manifest_schema_version": 2, "frontend_profile": "React"},
            {
                "manifest_schema_version": 2,
                "frontend_profile": "React",
                "acceptance_profile": "BlazorAutoV1",
            },
            {
                "manifest_schema_version": 2,
                "frontend_profile": "BlazorAuto",
                "acceptance_profile": "ReactPublicV1",
            },
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.resolve(value)

    def test_unknown_schema_and_non_object_markers_fail_closed(self):
        for value in (
            {"manifest_schema_version": True},
            {"manifest_schema_version": 3},
            [],
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.resolve(value)

    def test_accepted_marker_exposes_exact_ci_run_and_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.json"
            path.write_text(json.dumps({
                "manifest_schema_version": 2,
                "sha": "a" * 40,
                "source_sha": "a" * 40,
                "source_repo_url": "https://github.com/example/books",
                "ci_run_id": "123456",
                "ci_run_attempt": "2",
            }), encoding="utf-8")
            self.assertEqual("123456", resolve_ci_run_id(path, "https://github.com/example/books"))

    def test_current_and_recovery_markers_expose_their_exact_ci_runs(self):
        marker = {
            "manifest_schema_version": 2,
            "sha": "a" * 40,
            "source_sha": "a" * 40,
            "source_repo_url": "https://github.com/example/books",
            "ci_run_attempt": "1",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recovery_dir = root / "release-state"
            recovery_dir.mkdir()
            for relative_path, run_id in (
                ("release.json", "123456"),
                ("release-state/previous.json", "654321"),
            ):
                path = root / relative_path
                path.write_text(json.dumps({**marker, "ci_run_id": run_id}), encoding="utf-8")
                with self.subTest(marker=relative_path):
                    self.assertEqual(run_id, resolve_ci_run_id(path, "https://github.com/example/books"))

    def test_missing_or_foreign_ci_identity_fails_closed(self):
        valid = {
            "manifest_schema_version": 2,
            "sha": "a" * 40,
            "source_sha": "a" * 40,
            "source_repo_url": "https://github.com/example/books",
            "ci_run_id": "123456",
            "ci_run_attempt": "2",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.json"
            for field, value, message in (
                ("ci_run_id", "0", "CI run ID"),
                ("ci_run_attempt", "0", "CI run attempt"),
                ("sha", "b" * 40, "source SHA"),
                ("source_repo_url", "https://github.com/other/repo", "different source repository"),
            ):
                path.write_text(json.dumps({**valid, field: value}), encoding="utf-8")
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                    resolve_ci_run_id(path, "https://github.com/example/books")


if __name__ == "__main__":
    unittest.main()
