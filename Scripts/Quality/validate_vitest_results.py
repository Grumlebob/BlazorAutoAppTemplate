#!/usr/bin/env python3
"""Validate the React unit-test result and optional coverage summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def validate(document: dict[str, Any], expected_passed: int, expected_skipped: int) -> dict[str, int]:
    fields = {
        "total": document.get("numTotalTests"),
        "passed": document.get("numPassedTests"),
        "failed": document.get("numFailedTests"),
        "pending": document.get("numPendingTests"),
        "todo": document.get("numTodoTests"),
    }
    if any(not isinstance(value, int) or value < 0 for value in fields.values()):
        raise ValueError("Vitest JSON report is missing valid test-count fields.")
    if document.get("success") is not True:
        raise ValueError("Vitest JSON report does not mark the suite successful.")
    if fields["passed"] != expected_passed:
        raise ValueError(f"Expected {expected_passed} passing React tests; found {fields['passed']}.")
    if fields["failed"] != 0:
        raise ValueError(f"Expected zero failed React tests; found {fields['failed']}.")
    skipped = fields["pending"] + fields["todo"]
    if skipped != expected_skipped:
        raise ValueError(f"Expected {expected_skipped} skipped React tests; found {skipped}.")
    if fields["total"] != fields["passed"] + fields["failed"] + fields["pending"] + fields["todo"]:
        raise ValueError("Vitest test-count fields do not add up to the reported total.")
    if fields["total"] == 0:
        raise ValueError("Vitest report contains no tests.")
    return fields


def validate_uncovered_source(path: Path, react_root: Path) -> str:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Coverage summary must be a JSON object.")
    for source, summary in document.items():
        if source == "total" or not isinstance(summary, dict):
            continue
        resolved = Path(source).resolve()
        try:
            relative = resolved.relative_to(react_root.resolve()).as_posix()
        except ValueError:
            continue
        if not relative.startswith("app/") or relative.endswith((".test.ts", ".test.tsx", ".d.ts", ".typecheck.ts")):
            continue
        lines = summary.get("lines") or {}
        if lines.get("total", 0) > 0 and lines.get("covered", 0) == 0:
            return relative
    raise ValueError("Coverage summary omits every real React source file with zero covered lines.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--expected-passed", type=int, default=31)
    parser.add_argument("--expected-skipped", type=int, default=0)
    parser.add_argument("--coverage-summary", type=Path)
    parser.add_argument("--react-root", type=Path)
    args = parser.parse_args(argv)

    try:
        document = json.loads(args.report.read_text(encoding="utf-8"))
        counts = validate(document, args.expected_passed, args.expected_skipped)
        summary: dict[str, Any] = {"tests": counts, "coverage": "not-checked"}
        if args.coverage_summary:
            if not args.react_root:
                raise ValueError("--react-root is required with --coverage-summary.")
            summary["uncoveredSource"] = validate_uncovered_source(args.coverage_summary, args.react_root)
            summary["coverage"] = "validated"
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Invalid Vitest result: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
