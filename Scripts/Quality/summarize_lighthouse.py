#!/usr/bin/env python3
"""Summarize Lighthouse reports written by Scripts/RunLighthouse.ps1.

Prints one line per page and device with the median of its runs. With --minimum it also lists every
page and device whose median category score is below the given minimum and exits with 1.
Standard library only.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path


CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
FAILING_CATEGORIES = CATEGORIES[1:]
REPORT_SUFFIX = ".report.json"
DEFAULT_ROOT = "TestResults/Lighthouse"


def parse_minimum(text: str) -> dict[str, float]:
    """Parse "performance=90,seo=100" into category minimums (0-100)."""
    minimums: dict[str, float] = {}
    for item in text.split(","):
        category, separator, value = item.strip().partition("=")
        if not separator or category not in CATEGORIES:
            raise ValueError(f"--minimum entry '{item.strip()}' must be <category>=<score>; categories: {', '.join(CATEGORIES)}.")
        try:
            minimums[category] = float(value)
        except ValueError:
            raise ValueError(f"--minimum score for {category} is not a number: '{value}'.") from None
    return minimums


def read_reports(root: Path, prefix: str) -> tuple[dict[str, list[list[float]]], dict[str, set[str]]]:
    """Return per page/device rows [scores..., lcp s, cls, tbt ms] and the failing audits of every run."""
    runs: dict[str, list[list[float]]] = collections.defaultdict(list)
    failing: dict[str, set[str]] = collections.defaultdict(set)
    for path in sorted(root.glob(f"{prefix}*/*{REPORT_SUFFIX}")):
        report = json.loads(path.read_text(encoding="utf-8"))
        key = path.name[:-len(REPORT_SUFFIX)]
        categories, audits = report["categories"], report["audits"]
        runs[key].append(
            [categories[name]["score"] * 100 for name in CATEGORIES]
            + [audits["largest-contentful-paint"]["numericValue"] / 1000,
               audits["cumulative-layout-shift"]["numericValue"],
               audits["total-blocking-time"]["numericValue"]]
        )
        for category in FAILING_CATEGORIES:
            for ref in categories[category]["auditRefs"]:
                score = audits[ref["id"]]["score"]
                if ref["weight"] > 0 and score is not None and score < 1:
                    failing[key].add(f"{category}:{ref['id']}")
    return runs, failing


def medians(rows: list[list[float]]) -> list[float]:
    return [statistics.median(values) for values in zip(*rows)]


def summary_line(key: str, rows: list[list[float]], failing: set[str]) -> str:
    median = medians(rows)
    spread = max(row[0] for row in rows) - min(row[0] for row in rows)
    return (f"{key}: runs={len(rows)} perf={median[0]:.0f} (spread {spread:.0f}) a11y={median[1]:.0f} "
            f"bp={median[2]:.0f} seo={median[3]:.0f} lcp={median[4]:.2f}s cls={median[5]:.3f} "
            f"tbt={median[6]:.0f}ms failing={sorted(failing) or '-'}")


def below_minimum(runs: dict[str, list[list[float]]], minimums: dict[str, float]) -> list[str]:
    misses: list[str] = []
    for key, rows in sorted(runs.items()):
        median = medians(rows)
        for category, minimum in minimums.items():
            score = median[CATEGORIES.index(category)]
            if score < minimum:
                misses.append(f"{key}: {category} median {score:.0f} is below the minimum {minimum:g}")
    return misses


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prefix", help="report folder label prefix, for example p2-origin-")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--minimum", help='category minimums, for example "performance=90,seo=100"')
    args = parser.parse_args(argv)

    minimums: dict[str, float] = {}
    if args.minimum is not None:
        try:
            minimums = parse_minimum(args.minimum)
        except ValueError as error:
            parser.error(str(error))

    runs, failing = read_reports(Path(args.root), args.prefix)
    if not runs:
        print(f"No Lighthouse reports match {args.root}/{args.prefix}*/*{REPORT_SUFFIX}.", file=sys.stderr)
        return 2
    for key, rows in sorted(runs.items()):
        print(summary_line(key, rows, failing[key]))

    misses = below_minimum(runs, minimums)
    for miss in misses:
        print(miss)
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
