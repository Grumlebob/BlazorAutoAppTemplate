#!/usr/bin/env python3
"""Export report.json and a risk-ranked report.md from a SonarQube project (Tier 2 of the analysis).

Reads with the read-only reader token from SONAR_REPORT_TOKEN. Standard library only.
Documentation: docs/Quality/SonarQubeAnalysis.md.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


SCHEMA = "blazorautoapp.sonar-report/1"
TOKEN_ENV = "SONAR_REPORT_TOKEN"
PAGE_SIZE = 500
ISSUE_CAP = 10000
ALIGNMENT_THRESHOLD = 0.9
HTTP_RETRY_STATUS = 503
HTTP_RETRIES = 6
HTTP_RETRY_DELAY_SECONDS = 10
SOFTWARE_QUALITIES = ("MAINTAINABILITY", "RELIABILITY", "SECURITY")
SEVERITY_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "BLOCKER": 4}
RELSEC_SEVERITIES = frozenset({"BLOCKER", "HIGH", "MEDIUM"})
LEGACY_SEVERITY = {"BLOCKER": "BLOCKER", "CRITICAL": "HIGH", "MAJOR": "MEDIUM", "MINOR": "LOW", "INFO": "INFO"}
PROJECT_METRICS = (
    "ncloc", "lines", "coverage", "lines_to_cover", "uncovered_lines", "duplicated_lines_density",
    "cognitive_complexity", "violations", "software_quality_reliability_issues",
    "software_quality_security_issues", "software_quality_maintainability_issues",
    "new_violations", "new_coverage", "ncloc_language_distribution",
)
FILE_METRICS = (
    "ncloc", "cognitive_complexity", "complexity", "coverage", "lines_to_cover", "uncovered_lines",
    "duplicated_lines", "duplicated_lines_density", "violations",
)
FIXED_HOW_TO_USE = (
    "Use this report to create bounded, evidence-based work in Plans/CodeQualityImprovements.md. "
    "Read the source before classifying a finding. Review security hotspots as questions, then "
    "prioritize confirmed correctness and reliability risks, valuable low-effort work, and tested refactors."
)


class IncompleteDataError(RuntimeError):
    """Raised when an API result cannot be proven complete."""


class SonarClient:
    """Thin read-only HTTP client. All requests go through fetch_json, which tests replace."""

    def __init__(self, base_url: str, token: str, *, opener: Callable[..., Any] = urlopen,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
            raise ValueError("Sonar report API is restricted to an unauthenticated loopback URL.")
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._opener = opener
        self._sleep = sleep

    def fetch_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = urlencode(params or {})
        url = f"{self.base_url}/{path.lstrip('/')}" + (f"?{query}" if query else "")
        request = Request(url, headers={"Authorization": f"Bearer {self._token}"})
        for attempt in range(HTTP_RETRIES + 1):
            try:
                with self._opener(request, timeout=120) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                # 503 means the server is still indexing issues; wait and try again.
                if error.code != HTTP_RETRY_STATUS or attempt == HTTP_RETRIES:
                    raise
            self._sleep(HTTP_RETRY_DELAY_SECONDS)
        raise RuntimeError("unreachable")


def paginate(client: Any, path: str, params: dict[str, Any], item_key: str) -> tuple[list[dict], dict[str, str]]:
    """Fetch every reported page and fail if the API's reported total is not met."""
    items: list[dict] = []
    rule_names: dict[str, str] = {}
    page = 1
    expected_total: int | None = None
    while True:
        data = client.fetch_json(path, {**params, "ps": PAGE_SIZE, "p": page})
        batch = data.get(item_key) or []
        items.extend(batch)
        for rule in data.get("rules") or []:
            rule_names[rule["key"]] = rule.get("name", "")
        paging = data.get("paging")
        if not isinstance(paging, dict) or not isinstance(paging.get("total"), int):
            raise IncompleteDataError(f"{path} omitted a valid paging.total field.")
        total = paging["total"]
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise IncompleteDataError(f"{path} changed its reported total during pagination.")
        if not batch and len(items) < total:
            raise IncompleteDataError(f"{path} returned an empty page before all {total} items were retrieved.")
        if len(items) >= total:
            if len(items) != total:
                raise IncompleteDataError(f"{path} returned more items than its reported total.")
            return items, rule_names
        page += 1


def normalize_issue(issue: dict[str, Any], project: str) -> dict[str, Any]:
    component = normalize_component_path(issue.get("component", ""), project)
    # author is deliberately dropped: it is an email address.
    return {
        "key": issue.get("key", ""),
        "rule": issue.get("rule", ""),
        "path": component,
        "line": issue.get("line"),
        "message": sanitize_text(issue.get("message", "")),
        "effort": issue.get("effort"),
        "tags": issue.get("tags", []),
        "impacts": issue.get("impacts", []),
        "severity": issue.get("severity"),
        "type": issue.get("type"),
    }


def normalize_hotspot(hotspot: dict[str, Any], project: str) -> dict[str, Any]:
    component = normalize_component_path(hotspot.get("component", ""), project)
    return {
        "key": hotspot.get("key", ""),
        "rule": hotspot.get("ruleKey", ""),
        "path": component,
        "line": hotspot.get("line"),
        "message": hotspot.get("message", ""),
        "status": hotspot.get("status"),
        "vulnerabilityProbability": hotspot.get("vulnerabilityProbability"),
    }


def normalize_component_path(component: str, project: str) -> str:
    value = str(component or "").replace("\\", "/")
    prefix = f"{project}:"
    if value.startswith(prefix):
        value = value[len(prefix):]
    if PureWindowsPath(value).is_absolute() or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return f"<outside-repository>/{Path(value).name or 'unknown'}"
    parts = [part for part in value.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return f"<outside-repository>/{Path(value).name or 'unknown'}"
    return "/".join(parts)


def sanitize_text(value: Any, secrets: Iterable[str] = ()) -> str:
    text = str(value or "")
    for secret in sorted((value for value in secrets if value), key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9+/=_-]{12,}", "[REDACTED]", text)
    text = re.sub(r"(?i)(?:[A-Z]:\\|/Users/|/home/|/root/)[^\s'\"]+", "<local-path>", text)
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[email]", text, flags=re.I)
    return text


def fetch_issues(client: Any, project: str, extra: dict[str, Any]) -> tuple[list[dict], dict[str, str]]:
    """Fetch every issue; split oversized result sets by quality, rule, then file."""
    path = "api/issues/search"
    base = {"components": project, "resolved": "false", "additionalFields": "rules", **extra}
    first = client.fetch_json(path, {**base, "ps": 1, "p": 1})
    total = require_total(first, path)
    if total <= ISSUE_CAP:
        return paginate(client, path, base, "issues")

    issues: dict[str, dict] = {}
    rule_names: dict[str, str] = {}

    def merge(batch: list[dict], names: dict[str, str]) -> None:
        for issue in batch:
            issues.setdefault(issue["key"], issue)
        rule_names.update(names)

    for quality in SOFTWARE_QUALITIES:
        quality_params = {**base, "impactSoftwareQualities": quality}
        quality_first = client.fetch_json(path, {**quality_params, "ps": 1, "p": 1})
        quality_total = require_total(quality_first, path)
        if quality_total <= ISSUE_CAP:
            merge(*paginate(client, path, quality_params, "issues"))
            continue
        facets = client.fetch_json(path, {**quality_params, "ps": 1, "p": 1, "facets": "rules"})
        rule_keys = [value["val"] for facet in facets.get("facets", []) if facet.get("property") == "rules"
                     for value in facet.get("values", []) if value.get("count", 0) > 0]
        rule_facet_total = sum(
            int(value.get("count", 0)) for facet in facets.get("facets", []) if facet.get("property") == "rules"
            for value in facet.get("values", [])
        )
        if not rule_keys or rule_facet_total != quality_total:
            raise IncompleteDataError(f"The {quality} issue-rule facet omitted results ({rule_facet_total}/{quality_total}).")
        for rule_key in rule_keys:
            rule_params = {**quality_params, "rules": rule_key}
            rule_total = require_total(client.fetch_json(path, {**rule_params, "ps": 1, "p": 1}), path)
            if rule_total <= ISSUE_CAP:
                merge(*paginate(client, path, rule_params, "issues"))
                continue
            files, _ = paginate(client, "api/measures/component_tree", {
                "component": project, "qualifiers": "FIL", "strategy": "leaves", "metricKeys": "ncloc",
            }, "components")
            found_for_rule = 0
            for component in files:
                component_key = component.get("key")
                if not component_key:
                    continue
                file_params = {**rule_params, "components": component_key}
                file_total = require_total(client.fetch_json(path, {**file_params, "ps": 1, "p": 1}), path)
                if not file_total:
                    continue
                if file_total > ISSUE_CAP:
                    raise IncompleteDataError(f"A single file/rule issue partition exceeds {ISSUE_CAP} results.")
                merge(*paginate(client, path, file_params, "issues"))
                found_for_rule += file_total
            if found_for_rule != rule_total:
                raise IncompleteDataError(f"Rule '{rule_key}' file partitions omitted results ({found_for_rule}/{rule_total}).")
    return list(issues.values()), rule_names


def require_total(document: dict[str, Any], path: str) -> int:
    paging = document.get("paging")
    total = paging.get("total") if isinstance(paging, dict) else None
    if not isinstance(total, int) or total < 0:
        raise IncompleteDataError(f"{path} omitted a valid paging.total field.")
    return total


def fetch_measures(client: Any, project: str) -> tuple[dict[str, Any], dict[str, Any]]:
    data = client.fetch_json("api/measures/component", {
        "component": project, "metricKeys": ",".join(PROJECT_METRICS), "additionalFields": "period",
    })
    values: dict[str, Any] = {metric: None for metric in PROJECT_METRICS if not metric.startswith("new_")}
    new_values: dict[str, Any] = {metric: None for metric in PROJECT_METRICS if metric.startswith("new_")}
    for measure in data.get("component", {}).get("measures", []):
        metric = measure["metric"]
        if metric.startswith("new_"):
            period = measure.get("period") or ((measure.get("periods") or [{}])[0])
            new_values[metric] = period.get("value")
        else:
            values[metric] = measure.get("value")
    return values, new_values


def fetch_analysis(client: Any, project: str, analysis_id: str) -> dict[str, Any]:
    analyses = client.fetch_json("api/project_analyses/search", {"project": project, "ps": 2}).get("analyses", [])
    current = analyses[0] if analyses else {}
    previous = analyses[1] if len(analyses) > 1 else {}
    if current.get("key") != analysis_id:
        raise IncompleteDataError("The project's latest analysis changed before report export completed.")
    return {
        "analysisId": current.get("key"), "date": current.get("date"),
        "version": current.get("projectVersion"), "revision": current.get("revision"),
        "previousDate": previous.get("date"), "previousVersion": previous.get("projectVersion"),
    }


def fetch_hotspots(client: Any, project: str) -> dict[str, Any]:
    try:
        items, _ = paginate(client, "api/hotspots/search", {"project": project}, "hotspots")
        return {
            "status": "supported-with-results" if items else "supported-empty",
            "complete": True,
            "items": [normalize_hotspot(item, project) for item in items],
            "warning": None,
        }
    except HTTPError as error:
        if error.code == 404:
            return {"status": "unsupported", "complete": True, "items": [],
                    "warning": "The pinned server does not expose the security-hotspot search API."}
        if error.code in {401, 403}:
            return {"status": "forbidden", "complete": False, "items": [],
                    "warning": f"Security-hotspot search was denied (HTTP {error.code})."}
        raise
    except URLError:
        return {"status": "unreachable", "complete": False, "items": [],
                "warning": "Security-hotspot search was unreachable; hotspot results are incomplete."}


def churn_counts(git_log_text: str) -> Counter:
    """Count commits per path. Lines starting with @@ begin a commit; a path counts once per commit."""
    counts: Counter = Counter()
    current: set[str] = set()
    for line in git_log_text.splitlines():
        if line.startswith("@@"):
            counts.update(current)
            current = set()
        elif line.strip():
            current.add(line.strip())
    counts.update(current)
    return counts


def run_git_log(repo_root: str, churn_days: int) -> str:
    result = subprocess.run(
        ["git", "-C", repo_root, "log", f"--since={churn_days}.days", "--format=@@%H", "--name-only", "--no-renames", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def uncovered_fraction(coverage: str | None, lines_to_cover: str | None) -> tuple[float, bool]:
    if lines_to_cover is not None and float(lines_to_cover) <= 0:
        return 0.0, False
    if coverage is None or lines_to_cover is None:
        return 0.5, True
    return (100 - float(coverage)) / 100, False


def risk_score(cognitive: float, commits: int, uncovered: float, relsec: int, other: int) -> float:
    return round(
        math.sqrt(cognitive) * (1 + math.log2(1 + commits)) * (1 + uncovered)
        + 10 * math.log2(1 + relsec)
        + 2 * math.log2(1 + other),
        1,
    )


def is_relsec(issue: dict[str, Any]) -> bool:
    return any(
        impact.get("softwareQuality") in {"RELIABILITY", "SECURITY"} and impact.get("severity") in RELSEC_SEVERITIES
        for impact in issue_impacts(issue)
    )


def issue_impacts(issue: dict[str, Any]) -> list[dict[str, str]]:
    impacts = issue.get("impacts") or []
    if impacts:
        return impacts
    quality = {"BUG": "RELIABILITY", "VULNERABILITY": "SECURITY", "CODE_SMELL": "MAINTAINABILITY"}.get(issue.get("type"))
    severity = LEGACY_SEVERITY.get(str(issue.get("severity", "")).upper())
    return [{"softwareQuality": quality, "severity": severity}] if quality and severity else []


def qualities_of(issue: dict[str, Any]) -> set[str]:
    return {impact["softwareQuality"] for impact in issue_impacts(issue) if impact.get("softwareQuality")}


def build_files(tree: list[dict], issues: list[dict], churn: Counter) -> list[dict[str, Any]]:
    relsec: Counter = Counter()
    other: Counter = Counter()
    for issue in issues:
        (relsec if is_relsec(issue) else other)[issue["path"]] += 1
    files = []
    for component in tree:
        path = normalize_component_path(component.get("path", ""), "")
        metrics = {measure["metric"]: measure["value"] for measure in component.get("measures", [])}
        commits = churn.get(path, 0)
        uncovered, coverage_fallback = uncovered_fraction(metrics.get("coverage"), metrics.get("lines_to_cover"))
        risk = risk_score(
            float(metrics.get("cognitive_complexity", 0) or 0),
            commits,
            uncovered,
            relsec[path],
            other[path],
        )
        files.append({
            "path": path, "language": component.get("language"), "metrics": metrics,
            "commits": commits, "risk": risk, "relsec": relsec[path], "other": other[path],
            "coverageFallbackUsedForRiskOnly": coverage_fallback,
        })
    files.sort(key=lambda f: (-f["risk"], f["path"]))
    return files


def build_rules(issues: list[dict[str, Any]], rule_names: dict[str, str]) -> list[dict[str, Any]]:
    by_rule: dict[str, list[dict]] = defaultdict(list)
    for issue in issues:
        by_rule[issue["rule"]].append(issue)
    rules = []
    for key, items in by_rule.items():
        qualities: Counter = Counter(quality for issue in items for quality in qualities_of(issue))
        rules.append({
            "key": key, "name": rule_names.get(key, ""), "count": len(items),
            "bySoftwareQuality": dict(qualities),
            "examples": [{"issueKey": i["key"], "path": i["path"], "line": i["line"],
                          "impact": sorted(qualities_of(i)), "effort": i.get("effort"), "message": i["message"]}
                         for i in items[:5]],
        })
    rules.sort(key=lambda r: (-r["count"], r["key"]))
    return rules


def suggested_effort(value: Any) -> str:
    if value is None:
        return "review"
    match = re.fullmatch(r"\s*(\d+)\s*(min|m|h|d)\s*", str(value).casefold())
    if not match:
        return "review"
    amount = int(match.group(1))
    unit = match.group(2)
    minutes = amount if unit in {"min", "m"} else amount * (60 if unit == "h" else 480)
    return "small" if minutes <= 120 else "medium" if minutes <= 480 else "large"


def alignment_warning(paths: Iterable[str], path_exists: Callable[[str], bool]) -> str | None:
    paths = list(paths)
    if not paths:
        return None
    missing = [path for path in paths if not path_exists(path)]
    ratio = (len(paths) - len(missing)) / len(paths)
    if ratio >= ALIGNMENT_THRESHOLD:
        return None
    examples = ", ".join(missing[:5])
    message = f"Only {ratio:.0%} of component paths exist under the source root. Missing examples: {examples}"
    print(f"warning: {message}", file=sys.stderr)
    return message


def build_scope_evidence(profile: str, tree: list[dict[str, Any]]) -> dict[str, Any]:
    by_path = {normalize_component_path(item.get("path", ""), ""): item for item in tree}
    paths = set(by_path)
    if profile == "BlazorAuto":
        expected = {
            "bookGeometry": "BlazorAutoApp.Client/Features/Books/Shared/BookCoverGeometry.cs",
            "bookRazor": "BlazorAutoApp.Client/Features/Books/Shared/BookCoverRenderer.razor",
            "sharedCore": next((path for path in sorted(paths) if path.startswith("BlazorAutoApp.Core/")), ""),
            "handwrittenCss": "BlazorAutoApp.Client/Styles/input.css",
        }
        evidence = {name: bool(path and path in paths) for name, path in expected.items()}
        excludedUnexpected = sorted(path for path in paths if path.startswith("BlazorAutoApp.React/"))
        evidence["reactImplementationExcluded"] = not excludedUnexpected
        evidence["details"] = {name: path or None for name, path in expected.items()}
        evidence["unexpectedReactFiles"] = excludedUnexpected[:10]
        return evidence

    catalog = "BlazorAutoApp.React/app/features/books/catalog-page.tsx"
    api_client = "BlazorAutoApp.React/app/api/client.ts"
    api_item = by_path.get(api_client, {})
    api_metrics = {measure.get("metric"): measure.get("value") for measure in api_item.get("measures", [])}
    coverage_value = api_metrics.get("coverage")
    covered_api_client = coverage_value is not None and float(coverage_value) > 0
    expected = {
        "reactComposition": "BlazorAutoApp/Frontend/FrontendComposition.React.cs",
        "openApiHosting": "BlazorAutoApp/Frontend/OpenApi/OpenApiMetadataHosting.cs",
        "catalogPage": catalog,
        "testedApiModule": api_client,
    }
    evidence = {name: path in paths for name, path in expected.items()}
    evidence["testedApiModuleHasCoverage"] = covered_api_client
    excludedUnexpected = sorted(path for path in paths if path.startswith("BlazorAutoApp.Client/") or
                                (path.startswith("BlazorAutoApp/") and path.lower().endswith((".razor", ".razor.js"))))
    evidence["blazorImplementationExcluded"] = not excludedUnexpected
    evidence["details"] = {name: path for name, path in expected.items()}
    evidence["apiModuleCoverage"] = coverage_value
    evidence["unexpectedBlazorFiles"] = excludedUnexpected[:10]
    return evidence


def build_report(
    client: Any,
    project: str,
    repo_root: str,
    sha: str,
    churn_days: int,
    git_log_text: str,
    path_exists: Callable[[str], bool] | None = None,
    *,
    repository_identity: str,
    frontend_profile: str,
    analysis_id: str,
    project_version: str,
    settings_digest: str,
    settings_snapshot: dict[str, Any],
    server_version: str,
    run_evidence: dict[str, Any],
) -> dict[str, Any]:
    if path_exists is None:
        path_exists = lambda path: os.path.exists(os.path.join(repo_root, path))  # noqa: E731

    before = fetch_analysis(client, project, analysis_id)
    if before.get("revision") != sha or before.get("version") != project_version:
        raise IncompleteDataError("The latest server analysis revision/version does not match this immutable run.")
    measures, new_measures = fetch_measures(client, project)
    gate = client.fetch_json("api/qualitygates/project_status", {"analysisId": analysis_id})
    raw_issues, rule_names = fetch_issues(client, project, {})
    raw_new, new_rule_names = fetch_issues(client, project, {"inNewCodePeriod": "true"})
    rule_names.update(new_rule_names)
    issues = [normalize_issue(issue, project) for issue in raw_issues]
    new_issues = [normalize_issue(issue, project) for issue in raw_new]
    if len({issue["key"] for issue in issues}) != len(issues):
        raise IncompleteDataError("Issue pagination produced duplicate issue keys after deduplication.")
    hotspots = fetch_hotspots(client, project)

    tree, _ = paginate(client, "api/measures/component_tree", {
        "component": project, "qualifiers": "FIL", "strategy": "leaves", "metricKeys": ",".join(FILE_METRICS),
    }, "components")
    if not tree:
        raise IncompleteDataError("SonarQube returned no indexed files for the project.")
    churn = churn_counts(git_log_text)
    normalized_tree = [{**component, "path": normalize_component_path(component.get("path", ""), project)} for component in tree]
    tree_paths = [component["path"] for component in normalized_tree]
    warning = alignment_warning(tree_paths, path_exists)
    missing_paths = [path for path in tree_paths if not path_exists(path)]
    scope = build_scope_evidence(frontend_profile, normalized_tree)
    core_metrics = {name: measures.get(name) for name in ("ncloc", "coverage", "lines_to_cover", "uncovered_lines", "duplicated_lines_density", "cognitive_complexity")}
    missing_core_metrics = [name for name in ("ncloc", "coverage", "lines_to_cover", "duplicated_lines_density", "cognitive_complexity")
                            if core_metrics.get(name) is None]
    scope_failures = [name for name, value in scope.items() if isinstance(value, bool) and not value]
    warnings = [hotspots["warning"]] if hotspots.get("warning") else []
    if warning:
        warnings.append(warning)
    if missing_paths:
        warnings.append(f"{len(missing_paths)} indexed component paths do not resolve under the audit source tree.")
    if missing_core_metrics:
        warnings.append(f"Core project measures are missing: {', '.join(missing_core_metrics)}.")
    if scope_failures:
        warnings.append(f"Profile scope evidence is incomplete: {', '.join(scope_failures)}.")
    evidence_valid, evidence_warnings = validate_run_evidence(frontend_profile, run_evidence)
    warnings.extend(evidence_warnings)
    after = fetch_analysis(client, project, analysis_id)
    if after != before:
        raise IncompleteDataError("The project analysis changed during report export; no report was attributed to this run.")
    gate_status = gate.get("projectStatus", {}).get("status")
    gate_complete = gate_status is not None
    if not gate_complete:
        warnings.append("No quality-gate status was returned for this exact analysis.")
    complete = not missing_paths and not missing_core_metrics and not scope_failures and hotspots.get("complete", False) and gate_complete and evidence_valid

    for issue in issues + new_issues:
        issue["suggestedEffort"] = suggested_effort(issue.get("effort"))

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "complete": complete,
        "generatedUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repositoryIdentity": repository_identity,
        "frontendProfile": frontend_profile,
        "projectKey": project,
        "analysisId": analysis_id,
        "sha": sha,
        "project": project,
        "projectVersion": project_version,
        "serverVersion": server_version,
        "settingsDigest": settings_digest,
        "settings": settings_snapshot,
        "runEvidence": run_evidence,
        "churnDays": churn_days,
        "analysis": before,
        "qualityGate": {"status": gate_status, "analysisId": analysis_id, "informational": True},
        "measures": measures,
        "newCodeMeasures": new_measures,
        "coreMeasureCompleteness": {"values": core_metrics, "missing": missing_core_metrics},
        "scopeEvidence": scope,
        "dataCompleteness": {
            "issues": "complete",
            "newCodeIssues": "complete",
            "fileList": "complete" if not missing_paths else "incomplete",
            "hotspots": hotspots["status"],
            "warnings": warnings,
        },
        "issues": issues,
        "newCodeIssues": new_issues,
        "hotspots": hotspots,
        "files": build_files(normalized_tree, issues, churn),
        "rules": build_rules(issues, rule_names),
    }
    if warning:
        report["pathAlignmentWarning"] = warning
    return report


def validate_run_evidence(profile: str, evidence: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if not isinstance(evidence, dict):
        return False, ["Run evidence is missing or invalid."]
    tests = evidence.get("tests") or {}
    dotnet = tests.get("dotnet") or {}
    expected_passed = 211 if profile == "BlazorAuto" else 203
    valid_dotnet = dotnet.get("passed") == expected_passed and dotnet.get("failed") == 0 and dotnet.get("skipped") == 13
    if not valid_dotnet:
        warnings.append("The approved .NET suite result counts are missing or invalid.")
    if profile == "React":
        frontend = tests.get("frontendTests") or {}
        valid_frontend = frontend.get("passed") == 31 and frontend.get("failed") == 0 and frontend.get("skipped") == 0
        if not valid_frontend:
            warnings.append("The approved React unit-test result counts are missing or invalid.")
    else:
        valid_frontend = tests.get("frontendTests") == {"status": "not-applicable"}
        if not valid_frontend:
            warnings.append("BlazorAuto run evidence must mark React unit tests as not applicable.")
    coverage = evidence.get("coverage") or {}
    dotnet_coverage = coverage.get("dotnet") or {}
    valid_coverage = dotnet_coverage.get("valid") is True and dotnet_coverage.get("directReportCount", 0) > 0
    if profile == "React":
        valid_coverage = valid_coverage and coverage.get("reactLcov") == "validated"
    if not valid_coverage:
        warnings.append("Required production coverage evidence is missing or invalid.")
    return valid_dotnet and valid_frontend and valid_coverage, warnings


def _md_cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def _location(issue: dict[str, Any]) -> str:
    return f"{issue['path']}:{issue['line']}" if issue.get("line") is not None else issue["path"]


def _is_security_or_blocker(issue: dict[str, Any]) -> bool:
    for impact in issue_impacts(issue):
        severity = impact.get("severity")
        if severity == "BLOCKER":
            return True
        if impact.get("softwareQuality") == "SECURITY" and SEVERITY_RANK.get(severity, -1) >= SEVERITY_RANK["MEDIUM"]:
            return True
    return False


def _is_reliability_medium_plus(issue: dict[str, Any]) -> bool:
    return any(
        impact.get("softwareQuality") == "RELIABILITY" and SEVERITY_RANK.get(impact.get("severity"), -1) >= SEVERITY_RANK["MEDIUM"]
        for impact in issue_impacts(issue)
    )


def _main_impact(issues: list[dict[str, Any]]) -> str:
    pairs: Counter = Counter()
    for issue in issues:
        for impact in issue_impacts(issue):
            pairs[f"{impact.get('softwareQuality')} {impact.get('severity')}"] += 1
    return pairs.most_common(1)[0][0] if pairs else "n/a"


def render_markdown(report: dict[str, Any], top_rules: int = 30, top_files: int = 40) -> str:
    measures = report["measures"]
    new_measures = report["newCodeMeasures"]
    issues = report["issues"]
    analysis = report["analysis"]
    gate = report["qualityGate"]
    evidence = report.get("runEvidence", {})
    lines: list[str] = []

    def add(*items: str) -> None:
        lines.extend(items)

    languages = measures.get("ncloc_language_distribution") or ""
    language_text = ", ".join(part.replace("=", " ") for part in languages.split(";") if part) or "n/a"
    quality_counts = {q: sum(1 for i in issues if q in qualities_of(i)) for q in SOFTWARE_QUALITIES}
    coverage = measures.get("coverage")
    coverage_denominator = measures.get("lines_to_cover")
    add(
        f"# SonarQube report: {report['projectKey']}",
        "",
        f"- Repository: `{report['repositoryIdentity']}`; profile: **{report['frontendProfile']}**",
        f"- SHA: `{report['sha'] or 'unknown'}`",
        f"- Analysis ID: `{report['analysisId']}`; revision `{analysis.get('revision') or 'n/a'}`",
        f"- Analysis: {analysis.get('date') or 'n/a'}, project version `{report.get('projectVersion') or 'n/a'}`"
        f" (previous `{analysis.get('previousVersion') or 'none'}`)",
        f"- Server: `{report.get('serverVersion') or 'n/a'}`; settings digest: `{report.get('settingsDigest') or 'n/a'}`",
        f"- Report completeness: **{'complete' if report['complete'] else 'incomplete'}**; quality gate: **{gate.get('status') or 'unavailable'}** (informational)",
        f"- ncloc: {measures.get('ncloc') or 'n/a'} ({language_text})",
        f"- Coverage: {coverage + ' %' if coverage is not None else 'n/a'} of {coverage_denominator or 'n/a'} coverable lines; duplication: "
        f"{measures.get('duplicated_lines_density') or 'n/a'} %",
        f"- Open issues by software quality: MAINTAINABILITY {quality_counts['MAINTAINABILITY']}, "
        f"RELIABILITY {quality_counts['RELIABILITY']}, SECURITY {quality_counts['SECURITY']} "
        f"(total {len(issues)})",
        f"- New issues since the previous version: {new_measures.get('new_violations') or 'n/a'} "
        f"(new-code issue list: {len(report['newCodeIssues'])})",
    )
    if report.get("pathAlignmentWarning"):
        add(f"- Warning: {report['pathAlignmentWarning']}")

    test_counts = evidence.get("tests", {})
    coverage_evidence = evidence.get("coverage", {})
    dotnet_tests = test_counts.get("dotnet") or {}
    frontend_tests = test_counts.get("frontendTests") or {}
    add(
        "",
        "## Run evidence",
        "",
        f"- .NET tests: {dotnet_tests.get('passed', 'n/a')} passed, {dotnet_tests.get('skipped', 'n/a')} expected skips; TRX `{dotnet_tests.get('result', 'n/a')}`.",
        f"- React tests: {frontend_tests.get('passed', 'n/a')} passed, {frontend_tests.get('skipped', 'n/a')} skipped; {coverage_evidence.get('reactLcov', 'not applicable')}.",
        f"- .NET coverage: {'validated' if (coverage_evidence.get('dotnet') or {}).get('valid') else 'incomplete'}; production files with hits: {len((coverage_evidence.get('dotnet') or {}).get('coveredProductionSources', []))}.",
        f"- Indexed files: {len(report['files'])}; open issues: {len(issues)}; security hotspots: {len((report['hotspots'] or {}).get('items', []))} ({(report['hotspots'] or {}).get('status', 'unavailable')}).",
    )
    for warning in report.get("dataCompleteness", {}).get("warnings", []):
        add(f"- Warning: {_md_cell(warning)}")

    add("", "## Profile scope evidence", "", "| Check | Result |", "|---|---|")
    for name, value in report.get("scopeEvidence", {}).items():
        if isinstance(value, bool):
            add(f"| {name} | {'present' if value else 'missing'} |")

    hotspot_items = (report.get("hotspots") or {}).get("items", [])
    add("", f"## Security hotspots requiring review ({len(hotspot_items)})", "")
    if hotspot_items:
        for hotspot in hotspot_items[:50]:
            add(f"- `{hotspot.get('key')}` `{hotspot.get('rule')}` `{hotspot.get('path')}:{hotspot.get('line')}`: "
                f"{_md_cell(hotspot.get('message'))} (status: {hotspot.get('status') or 'unknown'})")
        if len(hotspot_items) > 50:
            add(f"- ... {len(hotspot_items) - 50} more in report.json")
    elif (report.get("hotspots") or {}).get("status") == "supported-empty":
        add("The API returned zero open hotspots.")
    else:
        add(f"No hotspot list was returned; capability status: `{(report.get('hotspots') or {}).get('status', 'unavailable')}`.")

    security = [i for i in issues if _is_security_or_blocker(i)]
    add("", f"## Security and blocker issues ({len(security)})", "")
    if security:
        add("| Issue | Rule | Location | Effort | Message |", "|---|---|---|---|---|")
        add(*(f"| `{i['key']}` | `{i['rule']}` | `{_location(i)}` | {i.get('suggestedEffort')} | {_md_cell(i['message'])} |"
              for i in security[:50]))
        if len(security) > 50:
            add(f"- ... {len(security) - 50} more in report.json")
    else:
        add("None.")

    reliability = [i for i in issues if _is_reliability_medium_plus(i)]
    add("", f"## Reliability issues, MEDIUM and above ({len(reliability)})", "")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for issue in reliability:
        grouped[issue["rule"]].append(issue)
    reliability_lines = 0
    for rule, items in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        block = [f"### `{rule}` ({len(items)})"]
        block += [f"- `{issue['key']}` `{_location(issue)}` ({issue.get('suggestedEffort')}): {_md_cell(issue['message'])}"
                  for issue in items[:10]]
        block.append("")
        # Keep one line in reserve for the truncation marker so the section stays within 200 lines.
        if reliability_lines + len(block) + 1 > 200:
            add("- ... more in report.json")
            break
        add(*block)
        reliability_lines += len(block)

    new_issues = report["newCodeIssues"]
    add(f"## New since the previous analysis ({len(new_issues)})", "")
    for issue in new_issues[:50]:
        add(f"- `{issue['key']}` `{issue['rule']}` `{_location(issue)}` ({issue.get('suggestedEffort')}): {_md_cell(issue['message'])}")
    if len(new_issues) > 50:
        add(f"- ... {len(new_issues) - 50} more in report.json")

    add("", f"## Top {top_rules} rules", "", "| # | Rule | Name | Count | Main impact | Example |", "|---:|---|---|---:|---|---|")
    for index, rule in enumerate(report["rules"][:top_rules], start=1):
        example = rule["examples"][0] if rule["examples"] else None
        where = f"`{example['issueKey']}` `{example['path']}:{example['line']}`" if example and example.get("line") is not None else ""
        main = _main_impact([i for i in issues if i["rule"] == rule["key"]])
        add(f"| {index} | `{rule['key']}` | {_md_cell(rule['name'])} | {rule['count']} | {main} | {where} |")

    add("", f"## Risk-ranked files (top {top_files})", "",
        "| # | File | Risk | ncloc | Cognitive | Coverage | Commits | Rel/Sec | Other |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|")
    for index, file_entry in enumerate(report["files"][:top_files], start=1):
        metrics = file_entry["metrics"]
        coverage_text = f"{metrics['coverage']} %" if metrics.get("coverage") is not None else "n/a*"
        add(f"| {index} | `{file_entry['path']}` | {file_entry['risk']} | {metrics.get('ncloc', 'n/a')} | "
            f"{metrics.get('cognitive_complexity', 'n/a')} | {coverage_text} | {file_entry['commits']} | "
            f"{file_entry['relsec']} | {file_entry['other']} |")

    duplicated = sorted(
        (f for f in report["files"] if f["metrics"].get("duplicated_lines")),
        key=lambda f: (-int(f["metrics"]["duplicated_lines"]), f["path"]),
    )[:15]
    add("", "## Duplication (top 15 files by duplicated lines)", "", "| File | Duplicated lines | Density |", "|---|---:|---:|")
    for file_entry in duplicated:
        add(f"| `{file_entry['path']}` | {file_entry['metrics']['duplicated_lines']} | "
            f"{file_entry['metrics'].get('duplicated_lines_density', 'n/a')} % |")

    add("", "*Coverage marked `n/a*` uses a 0.5 uncovered fallback for risk ranking only; its measured coverage stays null.*",
        "", "## How to use this report", "", FIXED_HOW_TO_USE)
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--repository-identity", required=True)
    parser.add_argument("--frontend-profile", choices=("BlazorAuto", "React"), required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--project-version", required=True)
    parser.add_argument("--settings-digest", required=True)
    parser.add_argument("--settings-file", required=True)
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--server-version", required=True)
    parser.add_argument("--churn-days", type=int, default=180)
    parser.add_argument("--top-files", type=int, default=40)
    parser.add_argument("--top-rules", type=int, default=30)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    token = os.environ.get(TOKEN_ENV)
    if not token:
        print(f"{TOKEN_ENV} is not set. Run through Scripts/Quality/Invoke-SonarAnalysis.ps1 or export the reader token.",
              file=sys.stderr)
        return 2
    try:
        settings_snapshot = json.loads(Path(args.settings_file).read_text(encoding="utf-8"))
        run_evidence = json.loads(Path(args.evidence_json).read_text(encoding="utf-8"))
        if not isinstance(settings_snapshot, dict) or not isinstance(run_evidence, dict):
            raise ValueError("Settings snapshot and run evidence must be JSON objects.")
        if not re.fullmatch(r"[0-9a-f]{40}", args.sha):
            raise ValueError("--sha must be a full lowercase commit SHA.")
        if not re.fullmatch(r"[0-9a-f]{64}", args.settings_digest):
            raise ValueError("--settings-digest must be a SHA-256 hex digest.")
        client = SonarClient(args.base_url, token)
        git_log_text = run_git_log(args.repo_root, args.churn_days)
        report = build_report(
            client, args.project, args.repo_root, args.sha, args.churn_days, git_log_text,
            repository_identity=args.repository_identity,
            frontend_profile=args.frontend_profile,
            analysis_id=args.analysis_id,
            project_version=args.project_version,
            settings_digest=args.settings_digest,
            settings_snapshot=settings_snapshot,
            server_version=args.server_version,
            run_evidence=run_evidence,
        )

        report = sanitize_document(report, {token})
        os.makedirs(args.out_dir, exist_ok=True)
        report_path = os.path.join(args.out_dir, "report.json")
        with open(report_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        markdown = render_markdown(report, args.top_rules, args.top_files)
        with open(os.path.join(args.out_dir, "report.md"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown)
        print(f"Complete: {str(report['complete']).lower()}; issues: {len(report['issues'])} open, "
              f"{len(report['newCodeIssues'])} new code; files ranked: {len(report['files'])}")
        return 0 if report["complete"] else 1
    except (HTTPError, URLError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Sonar report export failed: {sanitize_text(error, {token})}", file=sys.stderr)
        return 1


def sanitize_document(value: Any, secrets: Iterable[str]) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_document(item, secrets) for key, item in value.items() if key.casefold() not in {"author", "email"}}
    if isinstance(value, list):
        return [sanitize_document(item, secrets) for item in value]
    if isinstance(value, str):
        return sanitize_text(value, secrets)
    return value


if __name__ == "__main__":
    sys.exit(main())
