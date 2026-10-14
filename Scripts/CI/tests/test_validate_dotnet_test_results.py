from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Scripts.CI.validate_dotnet_test_results import summarize_results, validate_results

OPT_IN = "Set RUN_E2E=1 to run Playwright E2E tests."


class DotnetTestResultValidationTests(unittest.TestCase):
    def write_trx(self, outcomes: tuple[str, ...], skip_message: str | None = OPT_IN) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "results.trx"
        result_rows = "".join(
            f'<UnitTestResult testName="case-{index}" outcome="{outcome}">'
            + (
                f"<Output><ErrorInfo><Message>{skip_message}</Message></ErrorInfo></Output>"
                if outcome == "NotExecuted" and skip_message is not None
                else ""
            )
            + "</UnitTestResult>"
            for index, outcome in enumerate(outcomes)
        )
        path.write_text(
            "<TestRun xmlns=\"http://microsoft.com/schemas/VisualStudio/TeamTest/2010\">"
            f"<Results>{result_rows}</Results></TestRun>",
            encoding="utf-8",
        )
        return path

    def test_any_number_of_passes_is_accepted_when_skips_are_explicit_opt_ins(self) -> None:
        for passed in (1, 7, 183):
            with self.subTest(passed=passed):
                path = self.write_trx(("Passed",) * passed + ("NotExecuted", "NotExecuted"))

                summary = validate_results(path)

                self.assertEqual((passed + 2, passed, 0, 2), (summary.total, summary.passed, summary.failed, summary.skipped))

    def test_a_skipped_test_without_an_opt_in_reason_fails_the_suite(self) -> None:
        for message in (None, "", "Flaky on CI", "Skipped for now"):
            with self.subTest(message=message):
                path = self.write_trx(("Passed", "NotExecuted"), skip_message=message)

                with self.assertRaisesRegex(ValueError, "no explicit opt-in reason"):
                    validate_results(path)

    def test_an_exact_skip_count_can_still_be_required(self) -> None:
        validate_results(self.write_trx(("Passed", "Passed")), expected_skipped=0)

        with self.assertRaisesRegex(ValueError, "skipped test count differs"):
            validate_results(self.write_trx(("Passed", "NotExecuted")), expected_skipped=0)
        with self.assertRaisesRegex(ValueError, "skipped test count differs"):
            validate_results(self.write_trx(("Passed", "NotExecuted")), expected_skipped=2)

    def test_fails_on_failed_or_unexpected_test_outcomes(self) -> None:
        for outcome in ("Failed", "Inconclusive"):
            with self.subTest(outcome=outcome):
                path = self.write_trx(("Passed", outcome))
                with self.assertRaisesRegex(ValueError, "unexpected test outcomes"):
                    validate_results(path)

    def test_fails_when_nothing_passed(self) -> None:
        with self.assertRaisesRegex(ValueError, "no test passed"):
            validate_results(self.write_trx(("NotExecuted",)))

    def test_fails_when_results_are_absent(self) -> None:
        path = self.write_trx(())

        with self.assertRaisesRegex(ValueError, "contains no test results"):
            summarize_results(path)


if __name__ == "__main__":
    unittest.main()
