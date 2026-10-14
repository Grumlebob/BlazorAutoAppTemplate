#!/usr/bin/env python3
"""Validate the React unit-test result and optional coverage summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def validate(document: dict[str, Any], expected_skipped: int = 0) -> dict[str, int]:
    """Require a successful run with no failures and the expected skips; the suite size is not pinned."""
    if not isinstance(document, dict):
        raise ValueError("Vitest JSON report must be a JSON object.")
    fields = {
        "total": document.get("numTotalTests"),
        "passed": document.get("numPassedTests"),
        "failed": document.get("numFailedTests"),
        "pending": document.get("numPendingTests"),
        "todo": document.get("numTodoTests"),
    }
    if any(type(value) is not int or value < 0 for value in fields.values()):
        raise ValueError("Vitest JSON report is missing valid test-count fields.")
    if document.get("success") is not True:
        raise ValueError("Vitest JSON report does not mark the suite successful.")
    if fields["failed"] != 0:
        raise ValueError(f"Expected zero failed React tests; found {fields['failed']}.")
    skipped = fields["pending"] + fields["todo"]
    if skipped != expected_skipped:
        raise ValueError(f"Expected {expected_skipped} skipped React tests; found {skipped}.")
    if fields["total"] != fields["passed"] + fields["failed"] + fields["pending"] + fields["todo"]:
        raise ValueError("Vitest test-count fields do not add up to the reported total.")
    if fields["total"] == 0 or fields["passed"] == 0:
        raise ValueError("Vitest report contains no passing tests.")
    return fields


def validate_react_source_coverage(path: Path, react_root: Path) -> dict[str, int | float]:
    document = _read_coverage_document(path)
    root = react_root.resolve()
    files: dict[str, dict[str, int]] = {}
    for source, summary in document.items():
        if source == "total" or not isinstance(summary, dict):
            continue
        resolved = _resolve_coverage_source(source, react_root)
        relative = _react_source_relative_path(resolved, root)
        if relative is None:
            continue
        if not _is_covered_application_source(relative):
            continue
        if resolved.suffix not in {".ts", ".tsx"} or not resolved.is_file():
            raise ValueError(f"Coverage source does not resolve to a React application file: {relative}")
        total, covered = _react_line_counts(summary, relative)
        files[relative] = {"total": total, "covered": covered}

    expected_files = _react_application_sources(root)
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


def _read_coverage_document(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Coverage summary must be a JSON object.")
    return document


def _resolve_coverage_source(source: str, react_root: Path) -> Path:
    candidate = Path(source)
    if candidate.is_absolute():
        return candidate.resolve()
    normalized = source.replace("\\", "/")
    base = react_root.parent if normalized.startswith("BlazorAutoApp.React/") else react_root
    return (base / normalized).resolve()


def _react_source_relative_path(resolved: Path, root: Path) -> str | None:
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return None


def _is_covered_application_source(relative: str) -> bool:
    return (
        relative.startswith("app/")
        and not relative.startswith(("app/test/", "app/api/generated/"))
        and not relative.endswith((".test.ts", ".test.tsx", ".d.ts", ".typecheck.ts"))
    )


def _react_line_counts(summary: dict[str, Any], relative: str) -> tuple[int, int]:
    lines = summary.get("lines") or {}
    total = lines.get("total") if isinstance(lines, dict) else None
    covered = lines.get("covered") if isinstance(lines, dict) else None
    if type(total) is not int or type(covered) is not int or total < 0 or covered < 0 or covered > total:
        raise ValueError(f"Coverage summary has invalid line counts for React source: {relative}")
    return total, covered


def _react_application_sources(root: Path) -> set[str]:
    sources: set[str] = set()
    for source in (root / "app").rglob("*"):
        if not source.is_file() or source.suffix not in {".ts", ".tsx"}:
            continue
        relative = source.relative_to(root).as_posix()
        if _is_covered_application_source(relative):
            sources.add(relative)
    return sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--expected-skipped", type=int, default=0)
    parser.add_argument("--coverage-summary", type=Path)
    parser.add_argument("--react-root", type=Path)
    args = parser.parse_args(argv)

    try:
        document = json.loads(args.report.read_text(encoding="utf-8"))
        counts = validate(document, args.expected_skipped)
        summary: dict[str, Any] = {"tests": counts, "coverage": "not-checked"}
        if args.coverage_summary:
            if not args.react_root:
                raise ValueError("--react-root is required with --coverage-summary.")
            summary["coverage"] = validate_react_source_coverage(args.coverage_summary, args.react_root)
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, TypeError, ValueError) as error:
        print(f"Invalid Vitest result: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
