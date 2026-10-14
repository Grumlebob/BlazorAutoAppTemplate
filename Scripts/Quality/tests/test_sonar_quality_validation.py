from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Scripts.Quality.normalize_lcov_paths import normalize
from Scripts.Quality.validate_vitest_results import validate, validate_react_source_coverage


class VitestValidationTests(unittest.TestCase):
    def test_accepts_a_complete_suite_of_any_size(self) -> None:
        for count in (1, 31, 120):
            with self.subTest(count=count):
                result = {
                    "success": True,
                    "numTotalTests": count,
                    "numPassedTests": count,
                    "numFailedTests": 0,
                    "numPendingTests": 0,
                    "numTodoTests": 0,
                }
                self.assertEqual(validate(result)["passed"], count)

    def test_rejects_failed_skipped_or_empty_suites(self) -> None:
        base = {"success": True, "numTotalTests": 31, "numPassedTests": 31,
                "numFailedTests": 0, "numPendingTests": 0, "numTodoTests": 0}
        skipped = {**base, "numPassedTests": 30, "numPendingTests": 1}
        with self.assertRaisesRegex(ValueError, "skipped React tests"):
            validate(skipped)
        failed = {**base, "numPassedTests": 30, "numFailedTests": 1}
        with self.assertRaisesRegex(ValueError, "zero failed"):
            validate(failed)
        empty = {**base, "numTotalTests": 0, "numPassedTests": 0}
        with self.assertRaisesRegex(ValueError, "no passing tests"):
            validate(empty)

    def test_rejects_boolean_test_counts(self) -> None:
        result = {
            "success": True,
            "numTotalTests": 1,
            "numPassedTests": True,
            "numFailedTests": 0,
            "numPendingTests": 0,
            "numTodoTests": 0,
        }
        with self.assertRaisesRegex(ValueError, "valid test-count fields"):
            validate(result)

    def test_rejects_non_object_test_report(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON object"):
            validate([])

    def test_validates_all_react_sources_when_none_is_fully_uncovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react_root = root / "BlazorAutoApp.React"
            first = react_root / "app" / "routes.ts"
            second = react_root / "app" / "components" / "Card.tsx"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("export {}\n", encoding="utf-8")
            second.write_text("export {}\n", encoding="utf-8")
            summary = root / "coverage-summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "app/routes.ts": {"lines": {"total": 3, "covered": 2}},
                        "BlazorAutoApp.React/app/components/Card.tsx": {"lines": {"total": 2, "covered": 1}},
                        "total": {"lines": {"total": 5, "covered": 3}},
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                validate_react_source_coverage(summary, react_root),
                {"fileCount": 2, "coveredLines": 3, "totalLines": 5, "linePercentage": 60.0},
            )

    def test_coverage_requires_every_react_application_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react_root = root / "BlazorAutoApp.React"
            first = react_root / "app" / "routes.ts"
            second = react_root / "app" / "components" / "Card.tsx"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("export {}\n", encoding="utf-8")
            second.write_text("export {}\n", encoding="utf-8")
            summary = root / "coverage-summary.json"
            summary.write_text(
                json.dumps({"app/routes.ts": {"lines": {"total": 3, "covered": 1}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "omits React application source"):
                validate_react_source_coverage(summary, react_root)

    def test_coverage_requires_at_least_one_covered_react_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react_root = root / "BlazorAutoApp.React"
            source = react_root / "app" / "routes.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export {}\n", encoding="utf-8")
            summary = root / "coverage-summary.json"
            summary.write_text(
                json.dumps({"app/routes.ts": {"lines": {"total": 3, "covered": 0}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "no covered React application lines"):
                validate_react_source_coverage(summary, react_root)

    def test_coverage_rejects_boolean_line_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react_root = root / "BlazorAutoApp.React"
            source = react_root / "app" / "routes.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export {}\n", encoding="utf-8")
            summary = root / "coverage-summary.json"
            summary.write_text(
                json.dumps({"app/routes.ts": {"lines": {"total": 1, "covered": True}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "invalid line counts"):
                validate_react_source_coverage(summary, react_root)


class LcovNormalizationTests(unittest.TestCase):
    def test_normalizes_paths_with_spaces_and_windows_separators(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react = root / "BlazorAutoApp.React"
            source = react / "app" / "space dir" / "file.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export const value = 1\n", encoding="utf-8")
            content = "TN:\nSF:app\\space%20dir\\file.ts\nDA:1,1\nend_of_record\n"
            self.assertEqual(
                normalize(content, root, react),
                "TN:\nSF:BlazorAutoApp.React/app/space dir/file.ts\nDA:1,1\nend_of_record\n",
            )

    def test_keeps_repository_root_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react = root / "BlazorAutoApp.React"
            source = react / "app" / "client.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export {}\n", encoding="utf-8")
            content = f"SF:{source.as_posix()}\nDA:1,1\nend_of_record\n"
            self.assertIn("SF:BlazorAutoApp.React/app/client.ts", normalize(content, root, react))

    def test_rejects_unresolved_and_outside_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react = root / "BlazorAutoApp.React"
            react.mkdir()
            outside = root.parent / f"{root.name}-outside.ts"
            outside.write_text("export {}\n", encoding="utf-8")
            try:
                with self.assertRaisesRegex(ValueError, "escapes the repository"):
                    normalize("SF:../../" + outside.name + "\nDA:1,1\nend_of_record\n", root, react)
            finally:
                outside.unlink(missing_ok=True)
            with self.assertRaisesRegex(FileNotFoundError, "No such file|cannot find"):
                normalize("SF:app/missing.ts\nDA:1,1\nend_of_record\n", root, react)

    def test_rejects_duplicate_source_and_incomplete_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            react = root / "BlazorAutoApp.React"
            source = react / "app" / "client.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export {}\n", encoding="utf-8")
            duplicate = "\n".join(
                ["SF:app/client.ts", "DA:1,1", "end_of_record", "SF:app/client.ts", "DA:1,1", "end_of_record"]
            )
            with self.assertRaisesRegex(ValueError, "Duplicate normalized"):
                normalize(duplicate, root, react)
            with self.assertRaisesRegex(ValueError, "no source file"):
                normalize("DA:1,1\nend_of_record\n", root, react)
            with self.assertRaisesRegex(ValueError, "before end_of_record"):
                normalize("SF:app/client.ts\nDA:1,1\n", root, react)


if __name__ == "__main__":
    unittest.main()
