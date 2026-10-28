#!/usr/bin/env python3
"""Normalize React LCOV source paths to repository-root paths."""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.parse
from pathlib import Path


def source_path(value: str, repo_root: Path, source_root: Path) -> str:
    decoded = urllib.parse.unquote(value.strip()).replace("\\", "/")
    if decoded.startswith("file://"):
        decoded = urllib.parse.unquote(decoded[len("file://") :])
    if re.match(r"^/[A-Za-z]:/", decoded):
        decoded = decoded[1:]

    repo = repo_root.resolve()
    source = source_root.resolve()
    if re.match(r"^[A-Za-z]:/", decoded) or decoded.startswith("/"):
        candidate = Path(decoded)
    elif decoded.startswith("GrumPlates.React/"):
        candidate = repo / Path(decoded)
    else:
        candidate = source / Path(decoded)
    resolved = candidate.resolve(strict=True)
    try:
        relative = resolved.relative_to(repo).as_posix()
    except ValueError as error:
        raise ValueError(f"LCOV source escapes the repository: {value}") from error
    if not resolved.is_file():
        raise ValueError(f"LCOV source is not a file: {value}")
    return relative


def normalize(text: str, repo_root: Path, source_root: Path) -> str:
    output: list[str] = []
    sources: set[str] = set()
    record_has_source = False
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line
        if line.startswith("SF:"):
            path = source_path(line[3:], repo_root, source_root)
            if path in sources:
                raise ValueError(f"Duplicate normalized LCOV source at line {line_number}: {path}")
            sources.add(path)
            record_has_source = True
            line = f"SF:{path}"
        elif line == "end_of_record":
            if not record_has_source:
                raise ValueError(f"LCOV record at line {line_number} has no source file.")
            record_has_source = False
        output.append(line)
    if record_has_source:
        raise ValueError("LCOV ends before end_of_record.")
    if not sources:
        raise ValueError("LCOV report contains no source records.")
    return "\n".join(output) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        content = normalize(args.input.read_text(encoding="utf-8-sig"), args.repo_root, args.source_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8", newline="\n")
        print(f"Normalized {sum(line.startswith('SF:') for line in content.splitlines())} LCOV source paths.")
        return 0
    except (OSError, ValueError) as error:
        print(f"Invalid LCOV report: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
