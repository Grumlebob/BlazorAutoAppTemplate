#!/usr/bin/env python3
"""Summarize SonarAnalyzer SARIF output from `dotnet build -p:RunSonarAnalyzers=true`.

Tier 1 of the on-demand code-quality analysis (docs/Quality/SonarQubeAnalysis.md).
Writes summary.json and summary.md next to each other. Standard library only.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


SCHEMA = "blazorautoapp.sonar-quick-summary/1"
TEST_SARIF_NAME = "BlazorAutoApp.Test.sarif"
HIGH_SIGNAL_RULES = frozenset(
    {
        "S108", "S1244", "S1854", "S2583", "S2589", "S6444", "S6580", "S3871", "S2259",
        "S4487", "S1172", "S1144", "S2068", "S4830", "S2245", "S3877", "S6966", "CA2016",
    }
)
HIGH_SIGNAL_LISTING_LIMIT = 150
FAMILIES = ("sonar", "dotnet", "style", "other")
EXAMPLES_PER_RULE = 5


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    message: str
    scope: str
    project: str


def to_repo_relative(uri: str, repo_root: str) -> str:
    p = uri
    if p.startswith("file://"):
        p = urllib.parse.unquote(p[len("file://"):])     # '/C:/x/y' or '/home/x/y'
    if re.match(r"^/[A-Za-z]:", p):
        p = p[1:]                                         # 'C:/x/y'
    p = p.replace("\\", "/")
    root = repo_root.replace("\\", "/").rstrip("/") + "/"
    if p.lower().startswith(root.lower()):
        return p[len(root):]                              # keep original casing
    if not os.path.isabs(p) and not re.match(r"^[A-Za-z]:/", p):
        return p
    return "<outside-repository>/" + os.path.basename(p)


def scope_of(path: str, sarif_name: str) -> str:
    if sarif_name == TEST_SARIF_NAME or path.startswith("BlazorAutoApp.Test/"):
        return "test"
    # Padding with "/" lets a root-level Migrations or obj folder match too.
    padded = "/" + path
    if "/Migrations/" in padded or "/obj/" in padded or path.endswith((".g.cs", ".Designer.cs")):
        return "generated"
    return "production"


def family_of(rule_id: str) -> str:
    if re.match(r"^S\d+$", rule_id):
        return "sonar"
    if rule_id.startswith(("CA", "SYSLIB")):
        return "dotnet"
    if rule_id.startswith("IDE"):
        return "style"
    return "other"


def describe(rule: dict[str, Any]) -> str:
    short = (rule.get("shortDescription") or {}).get("text")
    if short:
        return short
    return (rule.get("fullDescription") or {}).get("text", "")


def _finding_key(finding: Finding) -> tuple[str, str, int, str]:
    return finding.rule, finding.path, finding.line, finding.message


def _finding_from_result(result: dict[str, Any], sarif_name: str, repo_root: str) -> Finding | None:
    if result.get("suppressions"):
        return None
    locations = result.get("locations") or [{}]
    physical = locations[0].get("physicalLocation") or {}
    uri = (physical.get("artifactLocation") or {}).get("uri", "")
    path = to_repo_relative(uri, repo_root)
    line = int((physical.get("region") or {}).get("startLine", 0))
    return Finding(
        result.get("ruleId", ""),
        path,
        line,
        (result.get("message") or {}).get("text", ""),
        scope_of(path, sarif_name),
        sarif_name[: -len(".sarif")],
    )


def _findings_from_run(run: dict[str, Any], sarif_name: str, repo_root: str) -> list[Finding]:
    findings = []
    for result in run.get("results", []):
        finding = _finding_from_result(result, sarif_name, repo_root)
        if finding is not None:
            findings.append(finding)
    return findings


def _descriptions_from_run(run: dict[str, Any]) -> dict[str, str]:
    driver = (run.get("tool") or {}).get("driver") or {}
    return {
        rule.get("id", ""): describe(rule)
        for rule in driver.get("rules", [])
        if rule.get("id", "")
    }


def read_findings(sarif_dir: str, repo_root: str) -> tuple[list[Finding], dict[str, str]]:
    seen: set[tuple[str, str, int, str]] = set()
    findings: list[Finding] = []
    descriptions: dict[str, str] = {}
    for sarif_path in sorted(glob.glob(os.path.join(sarif_dir, "*.sarif"))):
        sarif_name = os.path.basename(sarif_path)
        with open(sarif_path, encoding="utf-8-sig") as handle:
            document = json.load(handle)
        for run in document.get("runs", []):
            for rule_id, description in _descriptions_from_run(run).items():
                descriptions.setdefault(rule_id, description)
            for finding in _findings_from_run(run, sarif_name, repo_root):
                key = _finding_key(finding)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(finding)
    findings.sort(key=lambda f: (f.path, f.line, f.rule))
    return findings, descriptions


def build_summary(
    findings: list[Finding],
    descriptions: dict[str, str],
    repository_identity: str,
    profile: str,
    sha: str | None,
    dirty: bool,
    configuration: str,
    configuration_digest: str,
    analyzer_version: str,
    run_id: str,
    include_tests: bool,
) -> dict[str, Any]:
    production = [f for f in findings if f.scope == "production"]
    tests = [f for f in findings if f.scope == "test"]
    generated = [f for f in findings if f.scope == "generated"]
    listed = production + (tests if include_tests else [])

    family_counts = collections.Counter(family_of(f.rule) for f in production)
    project_counts = collections.Counter(f.project for f in production)

    rule_entries: dict[str, dict[str, Any]] = {}
    for finding in findings:
        if finding.scope == "generated":
            continue
        entry = rule_entries.setdefault(
            finding.rule, {"id": finding.rule, "family": family_of(finding.rule),
                           "description": descriptions.get(finding.rule, ""),
                           "production": 0, "test": 0, "examples": []}
        )
        if finding.scope == "production":
            entry["production"] += 1
            if len(entry["examples"]) < EXAMPLES_PER_RULE:
                entry["examples"].append({"path": finding.path, "line": finding.line, "message": finding.message})
        else:
            entry["test"] += 1
    rules = sorted(rule_entries.values(), key=lambda r: (-r["production"], r["id"]))

    file_rules: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for finding in production:
        file_rules[finding.path][finding.rule] += 1
    files = [
        {"path": path, "production": sum(counter.values()), "rules": dict(counter.most_common())}
        for path, counter in file_rules.items()
    ]
    files.sort(key=lambda f: (-f["production"], f["path"]))

    return {
        "schema": SCHEMA,
        "repositoryIdentity": repository_identity,
        "frontendProfile": profile,
        "generatedUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runId": run_id,
        "sha": sha,
        "dirty": dirty,
        "configuration": configuration,
        "configurationDigest": configuration_digest,
        "analyzerVersion": analyzer_version,
        "totals": {
            "production": len(production),
            "test": len(tests),
            "generated": len(generated),
            "byFamily": {family: family_counts.get(family, 0) for family in FAMILIES},
        },
        "byProject": dict(project_counts.most_common()),
        "rules": rules,
        "files": files,
        "findings": [
            {"rule": f.rule, "path": f.path, "line": f.line, "message": f.message,
             "scope": f.scope, "project": f.project}
            for f in listed
        ],
    }


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(summary: dict[str, Any], top_rules: int, top_files: int, include_tests: bool) -> str:
    totals = summary["totals"]
    families = totals["byFamily"]
    lines = [
        "# SonarAnalyzer C# summary",
        "",
        f"- Repository: `{summary['repositoryIdentity']}`",
        f"- Frontend profile: `{summary['frontendProfile']}`",
        f"- SHA: `{summary['sha'] or 'unknown'}`",
        f"- Dirty source: `{str(summary['dirty']).lower()}`",
        f"- Configuration: `{summary['configuration']}`",
        f"- Configuration digest: `{summary['configurationDigest']}`",
        f"- SonarAnalyzer.CSharp: `{summary['analyzerVersion']}`",
        f"- Run ID: `{summary['runId']}`",
        f"- Generated (UTC): {summary['generatedUtc']}",
        f"- Production findings: **{totals['production']}** "
        f"(by family: sonar {families['sonar']}, dotnet {families['dotnet']}, "
        f"style {families['style']}, other {families['other']})",
        f"- Test findings: {totals['test']}; generated findings (counted, not listed): {totals['generated']}",
        "",
        f"## Top {top_rules} rules (production)",
        "",
        "| # | Rule | Count | Description | Example |",
        "|---:|---|---:|---|---|",
    ]
    production_rules = [r for r in summary["rules"] if r["production"] > 0][:top_rules]
    for index, rule in enumerate(production_rules, start=1):
        example = rule["examples"][0] if rule["examples"] else None
        where = f"`{example['path']}:{example['line']}`" if example else ""
        lines.append(f"| {index} | `{rule['id']}` | {rule['production']} | {_cell(rule['description'])} | {where} |")

    lines += ["", f"## Top {top_files} files (production)", "", "| # | File | Findings | Top rules |", "|---:|---|---:|---|"]
    for index, file_entry in enumerate(summary["files"][:top_files], start=1):
        top = ", ".join(f"`{rule}` {count}" for rule, count in list(file_entry["rules"].items())[:3])
        lines.append(f"| {index} | `{file_entry['path']}` | {file_entry['production']} | {top} |")

    high_signal = [
        f for f in summary["findings"] if f["scope"] == "production" and f["rule"] in HIGH_SIGNAL_RULES
    ]
    lines += ["", f"## High-signal findings ({len(high_signal)})", ""]
    for finding in high_signal[:HIGH_SIGNAL_LISTING_LIMIT]:
        lines.append(f"- `{finding['rule']}` `{finding['path']}:{finding['line']}`: {_cell(finding['message'])}")
    if len(high_signal) > HIGH_SIGNAL_LISTING_LIMIT:
        lines.append(f"- ... {len(high_signal) - HIGH_SIGNAL_LISTING_LIMIT} more in summary.json")

    if include_tests:
        test_rules = [r for r in summary["rules"] if r["test"] > 0]
        test_rules.sort(key=lambda r: (-r["test"], r["id"]))
        lines += ["", "## Test findings (top 10 rules)", "", "| Rule | Count |", "|---|---:|"]
        for rule in test_rules[:10]:
            lines.append(f"| `{rule['id']}` | {rule['test']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sarif-dir", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--repository-identity", required=True)
    parser.add_argument("--frontend-profile", choices=("BlazorAuto", "React"), required=True)
    parser.add_argument("--sha")
    parser.add_argument("--dirty", action="store_true")
    parser.add_argument("--configuration", choices=("Debug", "Release"), default="Release")
    parser.add_argument("--configuration-digest", required=True)
    parser.add_argument("--analyzer-version", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--top-rules", type=int, default=40)
    parser.add_argument("--top-files", type=int, default=25)
    args = parser.parse_args(argv)

    if not glob.glob(os.path.join(args.sarif_dir, "*.sarif")):
        print(f"No *.sarif files in {args.sarif_dir}", file=sys.stderr)
        return 2

    try:
        findings, descriptions = read_findings(args.sarif_dir, args.repo_root)
    except (OSError, TypeError, ValueError) as error:
        print(f"Could not read SARIF findings: {error}", file=sys.stderr)
        return 2
    summary = build_summary(
        findings,
        descriptions,
        args.repository_identity,
        args.frontend_profile,
        args.sha,
        args.dirty,
        args.configuration,
        args.configuration_digest,
        args.analyzer_version,
        args.run_id,
        args.include_tests,
    )
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    markdown = render_markdown(summary, args.top_rules, args.top_files, args.include_tests)
    with open(os.path.join(args.out_dir, "summary.md"), "w", encoding="utf-8") as handle:
        handle.write(markdown)

    print(f"Production findings: {summary['totals']['production']} (test {summary['totals']['test']}, "
          f"generated {summary['totals']['generated']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
