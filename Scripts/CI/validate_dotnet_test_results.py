from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class TestResultSummary:
    total: int
    passed: int
    failed: int
    skipped: int
    unexpected: dict[str, int]


def summarize_results(path: Path) -> TestResultSummary:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError(f"cannot read TRX test results: {path}") from exc

    outcomes = Counter(
        result.attrib.get("outcome", "").casefold()
        for result in root.iter()
        if result.tag.rsplit("}", 1)[-1] == "UnitTestResult"
    )
    total = sum(outcomes.values())
    if total == 0:
        raise ValueError("TRX file contains no test results")

    known = {"passed", "failed", "notexecuted", "skipped"}
    return TestResultSummary(
        total=total,
        passed=outcomes["passed"],
        failed=outcomes["failed"],
        skipped=outcomes["notexecuted"] + outcomes["skipped"],
        unexpected={outcome: count for outcome, count in outcomes.items() if outcome not in known},
    )


def validate_results(path: Path, expected_passed: int, expected_skipped: int) -> TestResultSummary:
    summary = summarize_results(path)
    if summary.failed or summary.unexpected:
        raise ValueError(
            f"unexpected test outcomes: failed={summary.failed}, other={summary.unexpected}"
        )
    if summary.passed != expected_passed or summary.skipped != expected_skipped:
        raise ValueError(
            "test counts differ from the required suite: "
            f"expected passed={expected_passed}, skipped={expected_skipped}; "
            f"found passed={summary.passed}, skipped={summary.skipped}, total={summary.total}"
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Require exact passing and skip counts from a TRX file.")
    parser.add_argument("trx_file", type=Path)
    parser.add_argument("--expected-passed", type=int, required=True)
    parser.add_argument("--expected-skipped", type=int, required=True)
    parser.add_argument("--suite", default=".NET test suite")
    args = parser.parse_args()

    try:
        summary = validate_results(args.trx_file, args.expected_passed, args.expected_skipped)
    except ValueError as exc:
        print(f"{args.suite}: {exc}", file=sys.stderr)
        return 1

    print(
        f"{args.suite}: {summary.passed} passed, {summary.skipped} expected skips, "
        f"{summary.total} total"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
