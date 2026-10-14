from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from Scripts.Quality.summarize_lighthouse import main, parse_minimum


def write_report(root: Path, label: str, name: str, performance: float, accessibility: float = 1.0) -> None:
    folder = root / label
    folder.mkdir(parents=True, exist_ok=True)
    refs = [{"id": "audit", "weight": 1}]
    report = {
        "categories": {
            "performance": {"score": performance},
            "accessibility": {"score": accessibility, "auditRefs": refs},
            "best-practices": {"score": 1.0, "auditRefs": refs},
            "seo": {"score": 1.0, "auditRefs": refs},
        },
        "audits": {
            "audit": {"score": 1},
            "largest-contentful-paint": {"numericValue": 2000},
            "cumulative-layout-shift": {"numericValue": 0.01},
            "total-blocking-time": {"numericValue": 10},
        },
    }
    (folder / f"{name}.report.json").write_text(json.dumps(report), encoding="utf-8")


def run_main(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exit_request:
            code = int(exit_request.code)
    return code, out.getvalue(), err.getvalue()


class SummarizeLighthouseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def write_three_runs(self, performance: tuple[float, float, float]) -> None:
        for index, score in enumerate(performance, start=1):
            write_report(self.root, f"run-{index}-20260101", "home-mobile", score)

    def test_prints_the_median_of_the_runs_for_each_page_and_device(self) -> None:
        self.write_three_runs((0.90, 0.96, 0.92))
        write_report(self.root, "run-1-20260101", "home-desktop", 1.0)

        code, out, _ = run_main(["run-", "--root", str(self.root)])

        self.assertEqual(code, 0)
        self.assertIn("home-mobile: runs=3 perf=92 (spread 6)", out)
        self.assertIn("home-desktop: runs=1 perf=100", out)

    def test_other_labels_are_not_mixed_in(self) -> None:
        self.write_three_runs((0.90, 0.90, 0.90))
        write_report(self.root, "other-1-20260101", "home-mobile", 0.10)

        _, out, _ = run_main(["run-", "--root", str(self.root)])

        self.assertIn("perf=90", out)

    def test_minimum_passes_when_every_median_meets_it(self) -> None:
        self.write_three_runs((0.90, 0.95, 0.99))

        code, out, _ = run_main(["run-", "--root", str(self.root), "--minimum", "performance=95,accessibility=100"])

        self.assertEqual(code, 0)
        self.assertNotIn("below the minimum", out)

    def test_minimum_fails_and_names_the_page_and_category_below_it(self) -> None:
        self.write_three_runs((0.90, 0.95, 0.99))
        write_report(self.root, "run-1-20260101", "technologies-mobile", 0.99, accessibility=0.9)

        code, out, _ = run_main(["run-", "--root", str(self.root), "--minimum", "performance=96,accessibility=100"])

        self.assertEqual(code, 1)
        self.assertIn("home-mobile: performance median 95 is below the minimum 96", out)
        self.assertIn("technologies-mobile: accessibility median 90 is below the minimum 100", out)
        self.assertNotIn("technologies-mobile: performance", out)

    def test_unknown_minimum_category_is_an_error(self) -> None:
        self.write_three_runs((0.90, 0.95, 0.99))

        code, out, err = run_main(["run-", "--root", str(self.root), "--minimum", "speed=90"])

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("speed=90", err)
        with self.assertRaises(ValueError):
            parse_minimum("performance=fast")

    def test_no_matching_reports_is_an_error_not_a_pass(self) -> None:
        self.write_three_runs((0.90, 0.95, 0.99))

        code, out, err = run_main(["missing-", "--root", str(self.root), "--minimum", "performance=0"])

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("No Lighthouse reports match", err)


if __name__ == "__main__":
    unittest.main()
