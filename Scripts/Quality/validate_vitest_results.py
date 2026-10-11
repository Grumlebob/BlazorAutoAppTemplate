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


def validate_react_source_coverage(path: Path, react_root: Path) -> dict[str, int | float]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Coverage summary must be a JSON object.")
    root = react_root.resolve()
    files: dict[str, dict[str, int]] = {}
    for source, summary in document.items():
        if source == "total" or not isinstance(summary, dict):
            continue
        candidate = Path(source)
        if not candidate.is_absolute():
            normalized = source.replace("\\", "/")
            if normalized.startswith("BlazorAutoApp.React/"):
                candidate = react_root.parent / normalized
            else:
                candidate = react_root / normalized
        resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            continue
        if (
            not relative.startswith("app/")
            or relative.startswith("app/test/")
            or relative.startswith("app/api/generated/")
            or relative.endswith((".test.ts", ".test.tsx", ".d.ts", ".typecheck.ts"))
        ):
            continue
        if resolved.suffix not in {".ts", ".tsx"} or not resolved.is_file():
            raise ValueError(f"Coverage source does not resolve to a React application file: {relative}")
        lines = summary.get("lines") or {}
        total = lines.get("total")
        covered = lines.get("covered")
        if not isinstance(total, int) or not isinstance(covered, int) or total < 0 or covered < 0 or covered > total:
            raise ValueError(f"Coverage summary has invalid line counts for React source: {relative}")
        files[relative] = {"total": total, "covered": covered}

    expected_files = {
        source.relative_to(root).as_posix()
        for source in (root / "app").rglob("*")
        if source.is_file()
        and source.suffix in {".ts", ".tsx"}
        and not source.relative_to(root).as_posix().startswith(("app/test/", "app/api/generated/"))
        and not source.name.endswith((".test.ts", ".test.tsx", ".d.ts", ".typecheck.ts"))
    }
    missing = sorted(expected_files - files.keys())
    if missing:
        raise ValueError(f"Coverage summary omits React application source: {missing[0]}")
    if not files:
        raise ValueError("Coverage summary includes no React application source files.")

    total_lines = sum(source["total"] for source in files.values())
    covered_lines = sum(source["covered"] for source in files.values())
    if total_lines <= 0 or covered_lines <= 0:
        raise ValueError("Coverage summary contains no covered React application lines.")
    return {
        "fileCount": len(files),
        "coveredLines": covered_lines,
        "totalLines": total_lines,
        "linePercentage": round(covered_lines * 100 / total_lines, 2),
    }


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
            summary["coverage"] = validate_react_source_coverage(args.coverage_summary, args.react_root)
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Invalid Vitest result: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
