from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

# A skipped test must say how to opt in, such as "Set RUN_E2E=1 to run Playwright E2E tests."
OPT_IN_SKIP = re.compile(r"^Set RUN_[A-Z0-9_]+=1\b")


@dataclass(frozen=True)
class TestResultSummary:
    total: int
    passed: int
    failed: int
    skipped: int
    unexpected: dict[str, int]
    unexplained_skips: int


def _name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def summarize_results(path: Path) -> TestResultSummary:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError(f"cannot read TRX test results: {path}") from exc

    outcomes: Counter[str] = Counter()
    unexplained_skips = 0
    for result in root.iter():
        if _name(result) != "UnitTestResult":
            continue
        outcome = result.attrib.get("outcome", "").casefold()
        outcomes[outcome] += 1
        if outcome in {"notexecuted", "skipped"}:
            message = next((element.text or "" for element in result.iter() if _name(element) == "Message"), "")
            if not OPT_IN_SKIP.match(message.strip()):
                unexplained_skips += 1
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
        unexplained_skips=unexplained_skips,
    )


def validate_results(path: Path, expected_skipped: int | None = None) -> TestResultSummary:
    """Reject failures, unknown outcomes and suites where nothing passed.

    Without expected_skipped every skipped test must carry an explicit opt-in reason, so a test that was
    skipped by accident fails the suite without the suite size being pinned. With expected_skipped the
    skip count must match exactly; use 0 for suites that must run in full.
    """
    summary = summarize_results(path)
    if summary.failed or summary.unexpected:
        raise ValueError(
            f"unexpected test outcomes: failed={summary.failed}, other={summary.unexpected}"
        )
    if summary.passed == 0:
        raise ValueError(f"no test passed; total={summary.total}, skipped={summary.skipped}")
    if expected_skipped is None:
        if summary.unexplained_skips:
            raise ValueError(
                f"{summary.unexplained_skips} skipped test(s) have no explicit opt-in reason "
                "(expected a message such as 'Set RUN_E2E=1 to ...')"
            )
    elif summary.skipped != expected_skipped:
        raise ValueError(
            "skipped test count differs from the required suite: "
            f"expected skipped={expected_skipped}; "
            f"found passed={summary.passed}, skipped={summary.skipped}, total={summary.total}"
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Require passing tests, no failures and only expected skips from a TRX file.")
    parser.add_argument("trx_file", type=Path)
    parser.add_argument("--expected-skipped", type=int, default=None,
                        help="Exact skip count, such as 0. Omit it to allow only explicit opt-in skips.")
    parser.add_argument("--suite", default=".NET test suite")
    args = parser.parse_args()

    try:
        summary = validate_results(args.trx_file, args.expected_skipped)
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
