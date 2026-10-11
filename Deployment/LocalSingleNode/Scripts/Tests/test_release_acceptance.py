import json
import sys
import tempfile
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
from read_release_acceptance import resolve_release_acceptance


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


if __name__ == "__main__":
    unittest.main()
