from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Scripts.Quality.normalize_lcov_paths import normalize
from Scripts.Quality.validate_vitest_results import validate, validate_uncovered_source


class VitestValidationTests(unittest.TestCase):
    def test_accepts_exact_complete_suite(self) -> None:
        result = {
            "success": True,
            "numTotalTests": 31,
            "numPassedTests": 31,
            "numFailedTests": 0,
            "numPendingTests": 0,
            "numTodoTests": 0,
        }
        self.assertEqual(validate(result, 31, 0)["passed"], 31)

    def test_rejects_failed_missing_or_skipped_tests(self) -> None:
        result = {
            "success": True,
            "numTotalTests": 31,
            "numPassedTests": 30,
            "numFailedTests": 0,
            "numPendingTests": 1,
            "numTodoTests": 0,
        }
        with self.assertRaisesRegex(ValueError, "passing React tests"):
            validate(result, 31, 0)

    def test_requires_an_uncovered_real_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "BlazorAutoApp.React" / "app" / "routes.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export {}\n", encoding="utf-8")
            summary = root / "coverage-summary.json"
            summary.write_text(
                json.dumps({str(source): {"lines": {"total": 3, "covered": 0}}, "total": {}}),
                encoding="utf-8",
            )
            self.assertEqual(validate_uncovered_source(summary, source.parents[1]), "app/routes.ts")


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
