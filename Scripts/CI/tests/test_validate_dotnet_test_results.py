from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Scripts.CI.validate_dotnet_test_results import summarize_results, validate_results


class DotnetTestResultValidationTests(unittest.TestCase):
    def write_trx(self, outcomes: tuple[str, ...]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "results.trx"
        result_rows = "".join(
            f'<UnitTestResult testName="case-{index}" outcome="{outcome}" />'
            for index, outcome in enumerate(outcomes)
        )
        path.write_text(
            "<TestRun xmlns=\"http://microsoft.com/schemas/VisualStudio/TeamTest/2010\">"
            f"<Results>{result_rows}</Results></TestRun>",
            encoding="utf-8",
        )
        return path

    def test_passes_exact_required_counts_with_xunit_skip_outcomes(self) -> None:
        path = self.write_trx(("Passed", "Passed", "NotExecuted"))

        summary = validate_results(path, expected_passed=2, expected_skipped=1)

        self.assertEqual((3, 2, 0, 1), (summary.total, summary.passed, summary.failed, summary.skipped))

    def test_fails_when_required_tests_are_missing_or_skips_increase(self) -> None:
        path = self.write_trx(("Passed", "NotExecuted"))

        with self.assertRaisesRegex(ValueError, "test counts differ"):
            validate_results(path, expected_passed=2, expected_skipped=0)

    def test_without_a_pinned_pass_count_any_positive_number_passes(self) -> None:
        for passed in (1, 7):
            with self.subTest(passed=passed):
                path = self.write_trx(("Passed",) * passed + ("NotExecuted",))

                summary = validate_results(path, expected_passed=None, expected_skipped=1)

                self.assertEqual(passed, summary.passed)

    def test_without_a_pinned_pass_count_failures_empty_passes_and_skip_drift_still_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "unexpected test outcomes"):
            validate_results(self.write_trx(("Passed", "Failed")), expected_passed=None, expected_skipped=0)
        with self.assertRaisesRegex(ValueError, "test counts differ"):
            validate_results(self.write_trx(("NotExecuted",)), expected_passed=None, expected_skipped=1)
        with self.assertRaisesRegex(ValueError, "test counts differ"):
            validate_results(self.write_trx(("Passed", "NotExecuted")), expected_passed=None, expected_skipped=2)

    def test_fails_on_failed_or_unexpected_test_outcomes(self) -> None:
        for outcome in ("Failed", "Inconclusive"):
            with self.subTest(outcome=outcome):
                path = self.write_trx(("Passed", outcome))
                with self.assertRaisesRegex(ValueError, "unexpected test outcomes"):
                    validate_results(path, expected_passed=1, expected_skipped=0)

    def test_fails_when_results_are_absent(self) -> None:
        path = self.write_trx(())

        with self.assertRaisesRegex(ValueError, "contains no test results"):
            summarize_results(path)


if __name__ == "__main__":
    unittest.main()
