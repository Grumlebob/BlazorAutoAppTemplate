"""Validate the canonical Microsoft coverage XML reports used by SonarQube."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PureWindowsPath
import sys
import uuid
import xml.etree.ElementTree as ET
from typing import Any


def normalized_source(value: str, repo_root: Path) -> tuple[str, bool]:
    source = value.strip().replace("\\", "/")
    if source.startswith("file://"):
        source = source[7:]
    if len(source) > 2 and source[0] == "/" and source[2] == ":":
        source = source[1:]

    if PureWindowsPath(source).is_absolute() or source.startswith("/"):
        candidate = Path(source)
    else:
        candidate = repo_root / source
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return f"<outside-repository>/{Path(source).name}", False
    return relative, resolved.is_file()


def is_ignored_source(value: str) -> bool:
    source = value.strip().replace("\\", "/").casefold()
    parts = source.split("/")
    name = parts[-1]
    return (
        source.startswith("/_/src/")
        or any(part in {"bin", "obj"} for part in parts)
        or name.endswith((".g.cs", ".generated.cs", ".designer.cs"))
    )


def _coverage_reports(tests_directory: Path) -> list[Path]:
    reports = sorted(path for path in tests_directory.glob("*/*.xml") if path.is_file())
    if not reports:
        raise ValueError("No direct GUID-child Microsoft coverage XML report was produced.")
    for report in reports:
        try:
            uuid.UUID(report.parent.name)
        except ValueError as error:
            raise ValueError(f"Coverage report is not in a GUID child directory: {report.name}") from error
    return reports


def _modules_from_report(report: Path) -> list[ET.Element]:
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValueError(f"Cannot parse coverage XML: {report.name}") from error
    if root.tag.rsplit("}", 1)[-1] != "results":
        raise ValueError(f"Unexpected coverage XML root in {report.name}.")
    modules = root.find("modules")
    found = modules.findall("module") if modules is not None else []
    if not found:
        raise ValueError(f"Coverage XML has no module data: {report.name}.")
    return found


def _module_line_counts(module: ET.Element, report_name: str) -> tuple[str, int, int]:
    name = module.get("name") or ""
    if not name:
        raise ValueError(f"Coverage module has no assembly name in {report_name}.")
    covered = _integer(module.get("lines_covered"), "lines_covered", report_name)
    missed = _integer(module.get("lines_not_covered"), "lines_not_covered", report_name)
    return name, covered, missed


def _source_mapping(
    module: ET.Element, repo_root: Path, report_name: str
) -> tuple[dict[str, str], set[str], int]:
    source_map: dict[str, str] = {}
    ignored_source_ids: set[str] = set()
    source_count = 0
    sources = module.find("source_files")
    if sources is None:
        return source_map, ignored_source_ids, source_count

    for source_file in sources.findall("source_file"):
        source_id = source_file.get("id")
        source_path = source_file.get("path")
        if source_id is None or source_path is None:
            raise ValueError(f"Coverage source mapping is incomplete in {report_name}.")
        if is_ignored_source(source_path):
            ignored_source_ids.add(source_id)
            continue
        relative, exists = normalized_source(source_path, repo_root)
        if not exists:
            raise ValueError(f"Coverage source does not resolve to a repository file: {relative}")
        source_count += 1
        source_map[source_id] = relative
    return source_map, ignored_source_ids, source_count


def _covered_sources(
    module: ET.Element, source_map: dict[str, str], ignored_source_ids: set[str], report_name: str
) -> set[str]:
    covered: set[str] = set()
    functions = module.find("functions")
    if functions is None:
        return covered

    for function in functions.findall("function"):
        ranges = function.find("ranges")
        if ranges is None:
            continue
        for line_range in ranges.findall("range"):
            source_id = line_range.get("source_id")
            if source_id in ignored_source_ids:
                continue
            if source_id not in source_map:
                raise ValueError(f"Coverage range references an unknown source id in {report_name}.")
            if line_range.get("covered", "").casefold() == "yes":
                covered.add(source_map[source_id])
    return covered


def _production_modules(modules_by_name: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    return {
        name: counts
        for name, counts in modules_by_name.items()
        if not name.casefold().endswith(".test.dll")
    }


def validate_reports(tests_directory: Path, repo_root: Path, profile: str) -> dict[str, Any]:
    if profile not in {"BlazorAuto", "React"}:
        raise ValueError(f"Unsupported frontend profile: {profile}")

    reports = _coverage_reports(tests_directory)
    modules_by_name: dict[str, dict[str, int]] = {}
    covered_sources: set[str] = set()
    source_count = 0
    for report in reports:
        for module in _modules_from_report(report):
            name, covered, missed = _module_line_counts(module, report.name)
            record = modules_by_name.setdefault(name, {"coveredLines": 0, "uncoveredLines": 0})
            record["coveredLines"] += covered
            record["uncoveredLines"] += missed
            source_map, ignored_ids, count = _source_mapping(module, repo_root, report.name)
            source_count += count
            covered_sources.update(_covered_sources(module, source_map, ignored_ids, report.name))

    production = _production_modules(modules_by_name)
    if not production:
        raise ValueError("Coverage report contains no production assemblies.")
    if not any(counts["coveredLines"] > 0 for counts in production.values()):
        raise ValueError("Coverage report has no covered production source lines.")

    expected_root = "BlazorAutoApp.Client/" if profile == "BlazorAuto" else "BlazorAutoApp/"
    expected_sources = sorted(source for source in covered_sources if source.startswith(expected_root))
    if not expected_sources:
        raise ValueError(f"Coverage contains no covered source in the {profile} production composition.")
    return {
        "valid": True,
        "reportCount": len(reports),
        "sourceFileCount": source_count,
        "coveredProductionSources": expected_sources,
        "productionModules": production,
    }


def _integer(value: str | None, field: str, report_name: str) -> int:
    try:
        result = int(value or "")
    except ValueError as error:
        raise ValueError(f"Invalid {field} in coverage report {report_name}.") from error
    if result < 0:
        raise ValueError(f"Negative {field} in coverage report {report_name}.")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests-directory", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--frontend-profile", choices=("BlazorAuto", "React"), required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        result = validate_reports(args.tests_directory, args.repo_root, args.frontend_profile)
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"valid": True, "reportCount": result["reportCount"], "sourceFileCount": result["sourceFileCount"]}, sort_keys=True))
        return 0
    except (OSError, ValueError) as error:
        print(f"Invalid .NET coverage result: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
