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
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ReportRequest:
    project: str
    repo_root: str
    sha: str
    churn_days: int
    repository_identity: str
    frontend_profile: str
    analysis_id: str
    project_version: str
    settings_digest: str
    settings_snapshot: dict[str, Any]
    server_version: str
    run_evidence: dict[str, Any]


@dataclass(frozen=True)
class ReportCompleteness:
    complete: bool
    core_metrics: dict[str, Any]
    missing_core_metrics: list[str]
    scope_evidence: dict[str, Any]
    file_list_complete: bool
    warnings: list[str]
    path_alignment_warning: str | None


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
        _collect_rule_names(rule_names, data)
        total = require_total(data, path)
        expected_total = _validate_page_progress(path, batch, len(items), expected_total, total)
        if len(items) == expected_total:
            return items, rule_names
        page += 1


def _collect_rule_names(rule_names: dict[str, str], page: dict[str, Any]) -> None:
    for rule in page.get("rules") or []:
        rule_names[rule["key"]] = rule.get("name", "")


def _validate_page_progress(
    path: str, batch: list[dict], retrieved: int, expected_total: int | None, total: int
) -> int:
    if expected_total is not None and total != expected_total:
        raise IncompleteDataError(f"{path} changed its reported total during pagination.")
    if not batch and retrieved < total:
        raise IncompleteDataError(f"{path} returned an empty page before all {total} items were retrieved.")
    if retrieved > total:
        raise IncompleteDataError(f"{path} returned more items than its reported total.")
    return total


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
    text = re.sub(r"(?i)\b(?:bearer|basic)\s+[a-z0-9+/=_-]{12,}", "[REDACTED]", text)
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
    for quality in SOFTWARE_QUALITIES:
        batch, names = _fetch_quality_issues(client, project, base, quality)
        _merge_issue_results(issues, rule_names, batch, names)
    return list(issues.values()), rule_names


def _fetch_quality_issues(
    client: Any, project: str, base: dict[str, Any], quality: str
) -> tuple[list[dict], dict[str, str]]:
    path = "api/issues/search"
    params = {**base, "impactSoftwareQualities": quality}
    total = require_total(client.fetch_json(path, {**params, "ps": 1, "p": 1}), path)
    if total <= ISSUE_CAP:
        return paginate(client, path, params, "issues")

    rule_keys, facet_total = _issue_rule_facets(client, path, params)
    if not rule_keys or facet_total != total:
        raise IncompleteDataError(f"The {quality} issue-rule facet omitted results ({facet_total}/{total}).")

    issues: list[dict] = []
    rule_names: dict[str, str] = {}
    for rule_key in rule_keys:
        batch, names = _fetch_rule_issues(client, project, params, rule_key)
        issues.extend(batch)
        rule_names.update(names)
    return issues, rule_names


def _issue_rule_facets(
    client: Any, path: str, params: dict[str, Any]
) -> tuple[list[str], int]:
    facets = client.fetch_json(path, {**params, "ps": 1, "p": 1, "facets": "rules"})
    rule_keys: list[str] = []
    count = 0
    for facet in facets.get("facets", []):
        if facet.get("property") != "rules":
            continue
        for value in facet.get("values", []):
            value_count = int(value.get("count", 0))
            count += value_count
            if value_count > 0:
                rule_keys.append(value["val"])
    return rule_keys, count


def _fetch_rule_issues(
    client: Any, project: str, quality_params: dict[str, Any], rule_key: str
) -> tuple[list[dict], dict[str, str]]:
    path = "api/issues/search"
    params = {**quality_params, "rules": rule_key}
    total = require_total(client.fetch_json(path, {**params, "ps": 1, "p": 1}), path)
    if total <= ISSUE_CAP:
        return paginate(client, path, params, "issues")
    return _fetch_file_partitioned_rule(client, project, params, rule_key, total)


def _fetch_file_partitioned_rule(
    client: Any, project: str, rule_params: dict[str, Any], rule_key: str, rule_total: int
) -> tuple[list[dict], dict[str, str]]:
    files, _ = paginate(client, "api/measures/component_tree", {
        "component": project, "qualifiers": "FIL", "strategy": "leaves", "metricKeys": "ncloc",
    }, "components")
    issues: list[dict] = []
    rule_names: dict[str, str] = {}
    found = 0
    for component in files:
        component_key = component.get("key")
        if not component_key:
            continue
        params = {**rule_params, "components": component_key}
        file_total = require_total(client.fetch_json("api/issues/search", {**params, "ps": 1, "p": 1}), "api/issues/search")
        if file_total > ISSUE_CAP:
            raise IncompleteDataError(f"A single file/rule issue partition exceeds {ISSUE_CAP} results.")
        if file_total == 0:
            continue
        batch, names = paginate(client, "api/issues/search", params, "issues")
        issues.extend(batch)
        rule_names.update(names)
        found += file_total
    if found != rule_total:
        raise IncompleteDataError(f"Rule '{rule_key}' file partitions omitted results ({found}/{rule_total}).")
    return issues, rule_names


def _merge_issue_results(
    issues: dict[str, dict], rule_names: dict[str, str], batch: list[dict], names: dict[str, str]
) -> None:
    for issue in batch:
        issues.setdefault(issue["key"], issue)
    rule_names.update(names)


def require_total(document: dict[str, Any], path: str) -> int:
    paging = document.get("paging")
    total = paging.get("total") if isinstance(paging, dict) else None
    if type(total) is not int or total < 0:
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
    if unit in {"min", "m"}:
        minutes = amount
    elif unit == "h":
        minutes = amount * 60
    else:
        minutes = amount * 480
    if minutes <= 120:
        return "small"
    if minutes <= 480:
        return "medium"
    return "large"


def _check_path_alignment(
    paths: Iterable[str], path_exists: Callable[[str], bool]
) -> tuple[list[str], str | None]:
    paths = list(paths)
    if not paths:
        return [], None
    missing = [path for path in paths if not path_exists(path)]
    ratio = (len(paths) - len(missing)) / len(paths)
    if ratio >= ALIGNMENT_THRESHOLD:
        return missing, None
    examples = ", ".join(missing[:5])
    message = f"Only {ratio:.0%} of component paths exist under the source root. Missing examples: {examples}"
    print(f"warning: {message}", file=sys.stderr)
    return missing, message


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
        unexpected_excluded_paths = sorted(path for path in paths if path.startswith("BlazorAutoApp.React/"))
        evidence["reactImplementationExcluded"] = not unexpected_excluded_paths
        evidence["details"] = {name: path or None for name, path in expected.items()}
        evidence["unexpectedReactFiles"] = unexpected_excluded_paths[:10]
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
    unexpected_excluded_paths = sorted(path for path in paths if path.startswith("BlazorAutoApp.Client/") or
                                       (path.startswith("BlazorAutoApp/") and path.lower().endswith((".razor", ".razor.js"))))
    evidence["blazorImplementationExcluded"] = not unexpected_excluded_paths
    evidence["details"] = dict(expected)
    evidence["apiModuleCoverage"] = coverage_value
    evidence["unexpectedBlazorFiles"] = unexpected_excluded_paths[:10]
    return evidence


def _evaluate_report_completeness(
    request: ReportRequest,
    measures: dict[str, Any],
    tree: list[dict[str, Any]],
    hotspots: dict[str, Any],
    gate: dict[str, Any],
    path_exists: Callable[[str], bool],
) -> ReportCompleteness:
    paths = [component["path"] for component in tree]
    missing_paths, path_alignment_warning = _check_path_alignment(paths, path_exists)
    scope_evidence = build_scope_evidence(request.frontend_profile, tree)
    core_metrics = {
        name: measures.get(name)
        for name in ("ncloc", "coverage", "lines_to_cover", "uncovered_lines", "duplicated_lines_density", "cognitive_complexity")
    }
    missing_core_metrics = [
        name for name in ("ncloc", "coverage", "lines_to_cover", "duplicated_lines_density", "cognitive_complexity")
        if core_metrics[name] is None
    ]
    scope_failures = [name for name, value in scope_evidence.items() if isinstance(value, bool) and not value]
    evidence_valid, evidence_warnings = validate_run_evidence(request.frontend_profile, request.run_evidence)
    gate_status = (gate.get("projectStatus") or {}).get("status")
    warnings = [hotspots["warning"]] if hotspots.get("warning") else []
    if path_alignment_warning:
        warnings.append(path_alignment_warning)
    if missing_paths:
        warnings.append(f"{len(missing_paths)} indexed component paths do not resolve under the audit source tree.")
    if missing_core_metrics:
        warnings.append(f"Core project measures are missing: {', '.join(missing_core_metrics)}.")
    if scope_failures:
        warnings.append(f"Profile scope evidence is incomplete: {', '.join(scope_failures)}.")
    warnings.extend(evidence_warnings)
    if gate_status is None:
        warnings.append("No quality-gate status was returned for this exact analysis.")
    complete = (
        not missing_paths
        and not missing_core_metrics
        and not scope_failures
        and hotspots.get("complete", False)
        and gate_status is not None
        and evidence_valid
    )
    return ReportCompleteness(
        complete=complete,
        core_metrics=core_metrics,
        missing_core_metrics=missing_core_metrics,
        scope_evidence=scope_evidence,
        file_list_complete=not missing_paths,
        warnings=warnings,
        path_alignment_warning=path_alignment_warning,
    )


def build_report(
    client: Any,
    request: ReportRequest,
    git_log_text: str,
    path_exists: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    if path_exists is None:
        path_exists = lambda path: os.path.exists(os.path.join(request.repo_root, path))  # noqa: E731

    before = fetch_analysis(client, request.project, request.analysis_id)
    if before.get("revision") != request.sha or before.get("version") != request.project_version:
        raise IncompleteDataError("The latest server analysis revision/version does not match this immutable run.")
    measures, new_measures = fetch_measures(client, request.project)
    gate = client.fetch_json("api/qualitygates/project_status", {"analysisId": request.analysis_id})
    raw_issues, rule_names = fetch_issues(client, request.project, {})
    raw_new, new_rule_names = fetch_issues(client, request.project, {"inNewCodePeriod": "true"})
    rule_names.update(new_rule_names)
    issues = [normalize_issue(issue, request.project) for issue in raw_issues]
    new_issues = [normalize_issue(issue, request.project) for issue in raw_new]
    if len({issue["key"] for issue in issues}) != len(issues):
        raise IncompleteDataError("Issue pagination produced duplicate issue keys after deduplication.")
    hotspots = fetch_hotspots(client, request.project)

    tree, _ = paginate(client, "api/measures/component_tree", {
        "component": request.project, "qualifiers": "FIL", "strategy": "leaves", "metricKeys": ",".join(FILE_METRICS),
    }, "components")
    if not tree:
        raise IncompleteDataError("SonarQube returned no indexed files for the project.")
    churn = churn_counts(git_log_text)
    normalized_tree = [{**component, "path": normalize_component_path(component.get("path", ""), request.project)} for component in tree]
    completeness = _evaluate_report_completeness(request, measures, normalized_tree, hotspots, gate, path_exists)
    after = fetch_analysis(client, request.project, request.analysis_id)
    if after != before:
        raise IncompleteDataError("The project analysis changed during report export; no report was attributed to this run.")
    gate_status = (gate.get("projectStatus") or {}).get("status")

    for issue in issues + new_issues:
        issue["suggestedEffort"] = suggested_effort(issue.get("effort"))

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "complete": completeness.complete,
        "generatedUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repositoryIdentity": request.repository_identity,
        "frontendProfile": request.frontend_profile,
        "projectKey": request.project,
        "analysisId": request.analysis_id,
        "sha": request.sha,
        "project": request.project,
        "projectVersion": request.project_version,
        "serverVersion": request.server_version,
        "settingsDigest": request.settings_digest,
        "settings": request.settings_snapshot,
        "runEvidence": request.run_evidence,
        "churnDays": request.churn_days,
        "analysis": before,
        "qualityGate": {"status": gate_status, "analysisId": request.analysis_id, "informational": True},
        "measures": measures,
        "newCodeMeasures": new_measures,
        "coreMeasureCompleteness": {"values": completeness.core_metrics, "missing": completeness.missing_core_metrics},
        "scopeEvidence": completeness.scope_evidence,
        "dataCompleteness": {
            "issues": "complete",
            "newCodeIssues": "complete",
            "fileList": "complete" if completeness.file_list_complete else "incomplete",
            "hotspots": hotspots["status"],
            "warnings": completeness.warnings,
        },
        "issues": issues,
        "newCodeIssues": new_issues,
        "hotspots": hotspots,
        "files": build_files(normalized_tree, issues, churn),
        "rules": build_rules(issues, rule_names),
    }
    if completeness.path_alignment_warning:
        report["pathAlignmentWarning"] = completeness.path_alignment_warning
    return report


def _has_test_counts(value: Any, passed: int, skipped: int) -> bool:
    return (
        isinstance(value, dict)
        and type(value.get("passed")) is int
        and type(value.get("failed")) is int
        and type(value.get("skipped")) is int
        and value["passed"] == passed
        and value["failed"] == 0
        and value["skipped"] == skipped
    )


def _frontend_evidence_valid(profile: str, tests: dict[str, Any]) -> bool:
    if profile == "React":
        return _has_test_counts(tests.get("frontendTests"), 31, 0)
    return tests.get("frontendTests") == {"status": "not-applicable"}


def _coverage_evidence_valid(profile: str, evidence: dict[str, Any]) -> bool:
    coverage = evidence.get("coverage")
    if not isinstance(coverage, dict):
        return False
    dotnet = coverage.get("dotnet")
    if not isinstance(dotnet, dict) or dotnet.get("valid") is not True:
        return False
    direct_reports = dotnet.get("directReportCount")
    if type(direct_reports) is not int or direct_reports <= 0:
        return False
    return profile != "React" or coverage.get("reactLcov") == "validated"


def validate_run_evidence(profile: str, evidence: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if not isinstance(evidence, dict):
        return False, ["Run evidence is missing or invalid."]
    if profile not in {"BlazorAuto", "React"}:
        return False, [f"Unsupported frontend profile: {profile}."]
    tests = evidence.get("tests")
    if not isinstance(tests, dict):
        tests = {}
    expected_passed = 190 if profile == "BlazorAuto" else 182
    valid_dotnet = _has_test_counts(tests.get("dotnet"), expected_passed, 13)
    if not valid_dotnet:
        warnings.append("The approved .NET suite result counts are missing or invalid.")
    valid_frontend = _frontend_evidence_valid(profile, tests)
    if not valid_frontend:
        if profile == "React":
            warnings.append("The approved React unit-test result counts are missing or invalid.")
        else:
            warnings.append("BlazorAuto run evidence must mark React unit tests as not applicable.")
    valid_coverage = _coverage_evidence_valid(profile, evidence)
    if not valid_coverage:
        warnings.append("Required production coverage evidence is missing or invalid.")
    return valid_dotnet and valid_frontend and valid_coverage, warnings


def _md_cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _render_report_overview(report: dict[str, Any]) -> list[str]:
    measures = report["measures"]
    new_measures = report["newCodeMeasures"]
    issues = report["issues"]
    analysis = report["analysis"]
    gate = report["qualityGate"]
    evidence = _mapping(report.get("runEvidence"))
    lines: list[str] = []
    languages = measures.get("ncloc_language_distribution") or ""
    language_text = ", ".join(part.replace("=", " ") for part in languages.split(";") if part) or "n/a"
    quality_counts = {q: sum(1 for i in issues if q in qualities_of(i)) for q in SOFTWARE_QUALITIES}
    coverage = measures.get("coverage")
    coverage_denominator = measures.get("lines_to_cover")
    lines.extend((
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
    ))
    if report.get("pathAlignmentWarning"):
        lines.append(f"- Warning: {report['pathAlignmentWarning']}")

    test_counts = _mapping(evidence.get("tests"))
    coverage_evidence = _mapping(evidence.get("coverage"))
    dotnet_tests = _mapping(test_counts.get("dotnet"))
    frontend_tests = _mapping(test_counts.get("frontendTests"))
    dotnet_coverage = _mapping(coverage_evidence.get("dotnet"))
    hotspot_data = _mapping(report.get("hotspots"))
    lines.extend((
        "",
        "## Run evidence",
        "",
        f"- .NET tests: {dotnet_tests.get('passed', 'n/a')} passed, {dotnet_tests.get('skipped', 'n/a')} expected skips; TRX `{dotnet_tests.get('result', 'n/a')}`.",
        f"- React tests: {frontend_tests.get('passed', 'n/a')} passed, {frontend_tests.get('skipped', 'n/a')} skipped; {coverage_evidence.get('reactLcov', 'not applicable')}.",
        f"- .NET coverage: {'validated' if dotnet_coverage.get('valid') else 'incomplete'}; production files with hits: {len(dotnet_coverage.get('coveredProductionSources', []))}.",
        f"- Indexed files: {len(report['files'])}; open issues: {len(issues)}; security hotspots: {len(hotspot_data.get('items', []))} ({hotspot_data.get('status', 'unavailable')}).",
    ))
    for warning in _mapping(report.get("dataCompleteness")).get("warnings", []):
        lines.append(f"- Warning: {_md_cell(warning)}")

    lines.extend(("", "## Profile scope evidence", "", "| Check | Result |", "|---|---|"))
    for name, value in report.get("scopeEvidence", {}).items():
        if isinstance(value, bool):
            lines.append(f"| {name} | {'present' if value else 'missing'} |")
    return lines


def _render_hotspots(report: dict[str, Any]) -> list[str]:
    hotspot_data = _mapping(report.get("hotspots"))
    hotspot_items = hotspot_data.get("items", [])
    lines = ["", f"## Security hotspots requiring review ({len(hotspot_items)})", ""]
    if hotspot_items:
        for hotspot in hotspot_items[:50]:
            lines.append(f"- `{hotspot.get('key')}` `{hotspot.get('rule')}` `{hotspot.get('path')}:{hotspot.get('line')}`: "
                         f"{_md_cell(hotspot.get('message'))} (status: {hotspot.get('status') or 'unknown'})")
        if len(hotspot_items) > 50:
            lines.append(f"- ... {len(hotspot_items) - 50} more in report.json")
    elif hotspot_data.get("status") == "supported-empty":
        lines.append("The API returned zero open hotspots.")
    else:
        status = hotspot_data.get("status", "unavailable")
        lines.append(f"No hotspot list was returned; capability status: `{status}`.")
    return lines


def _render_security_issues(issues: list[dict[str, Any]]) -> list[str]:
    security = [i for i in issues if _is_security_or_blocker(i)]
    lines = ["", f"## Security and blocker issues ({len(security)})", ""]
    if security:
        lines.extend(("| Issue | Rule | Location | Effort | Message |", "|---|---|---|---|---|"))
        lines.extend(f"| `{i['key']}` | `{i['rule']}` | `{_location(i)}` | {i.get('suggestedEffort')} | {_md_cell(i['message'])} |"
                     for i in security[:50])
        if len(security) > 50:
            lines.append(f"- ... {len(security) - 50} more in report.json")
    else:
        lines.append("None.")
    return lines


def _render_reliability_issues(issues: list[dict[str, Any]]) -> list[str]:
    reliability = [i for i in issues if _is_reliability_medium_plus(i)]
    lines = ["", f"## Reliability issues, MEDIUM and above ({len(reliability)})", ""]
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
            lines.append("- ... more in report.json")
            break
        lines.extend(block)
        reliability_lines += len(block)
    return lines


def _render_new_issues(new_issues: list[dict[str, Any]]) -> list[str]:
    lines = [f"## New since the previous analysis ({len(new_issues)})", ""]
    for issue in new_issues[:50]:
        lines.append(f"- `{issue['key']}` `{issue['rule']}` `{_location(issue)}` ({issue.get('suggestedEffort')}): {_md_cell(issue['message'])}")
    if len(new_issues) > 50:
        lines.append(f"- ... {len(new_issues) - 50} more in report.json")
    return lines


def _render_rules(report: dict[str, Any], top_rules: int) -> list[str]:
    issues = report["issues"]
    lines = ["", f"## Top {top_rules} rules", "", "| # | Rule | Name | Count | Main impact | Example |", "|---:|---|---|---:|---|---|"]
    for index, rule in enumerate(report["rules"][:top_rules], start=1):
        example = rule["examples"][0] if rule["examples"] else None
        where = f"`{example['issueKey']}` `{example['path']}:{example['line']}`" if example and example.get("line") is not None else ""
        main = _main_impact([i for i in issues if i["rule"] == rule["key"]])
        lines.append(f"| {index} | `{rule['key']}` | {_md_cell(rule['name'])} | {rule['count']} | {main} | {where} |")
    return lines


def _render_risk_files(report: dict[str, Any], top_files: int) -> list[str]:
    lines = ["", f"## Risk-ranked files (top {top_files})", "",
             "| # | File | Risk | ncloc | Cognitive | Coverage | Commits | Rel/Sec | Other |",
             "|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for index, file_entry in enumerate(report["files"][:top_files], start=1):
        metrics = file_entry["metrics"]
        coverage_text = f"{metrics['coverage']} %" if metrics.get("coverage") is not None else "n/a*"
        lines.append(f"| {index} | `{file_entry['path']}` | {file_entry['risk']} | {metrics.get('ncloc', 'n/a')} | "
                     f"{metrics.get('cognitive_complexity', 'n/a')} | {coverage_text} | {file_entry['commits']} | "
                     f"{file_entry['relsec']} | {file_entry['other']} |")
    return lines


def _render_duplication(report: dict[str, Any]) -> list[str]:
    duplicated = sorted(
        (f for f in report["files"] if f["metrics"].get("duplicated_lines")),
        key=lambda f: (-int(f["metrics"]["duplicated_lines"]), f["path"]),
    )[:15]
    lines = ["", "## Duplication (top 15 files by duplicated lines)", "", "| File | Duplicated lines | Density |", "|---|---:|---:|"]
    for file_entry in duplicated:
        lines.append(f"| `{file_entry['path']}` | {file_entry['metrics']['duplicated_lines']} | "
                     f"{file_entry['metrics'].get('duplicated_lines_density', 'n/a')} % |")
    lines.extend(("", "*Coverage marked `n/a*` uses a 0.5 uncovered fallback for risk ranking only; its measured coverage stays null.*",
                  "", "## How to use this report", "", FIXED_HOW_TO_USE))
    return lines


def render_markdown(report: dict[str, Any], top_rules: int = 30, top_files: int = 40) -> str:
    lines = _render_report_overview(report)
    lines.extend(_render_hotspots(report))
    lines.extend(_render_security_issues(report["issues"]))
    lines.extend(_render_reliability_issues(report["issues"]))
    lines.extend(_render_new_issues(report["newCodeIssues"]))
    lines.extend(_render_rules(report, top_rules))
    lines.extend(_render_risk_files(report, top_files))
    lines.extend(_render_duplication(report))
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
        request = ReportRequest(
            project=args.project,
            repo_root=args.repo_root,
            sha=args.sha,
            churn_days=args.churn_days,
            repository_identity=args.repository_identity,
            frontend_profile=args.frontend_profile,
            analysis_id=args.analysis_id,
            project_version=args.project_version,
            settings_digest=args.settings_digest,
            settings_snapshot=settings_snapshot,
            server_version=args.server_version,
            run_evidence=run_evidence,
        )
        report = build_report(
            client, request, git_log_text,
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
    except (OSError, ValueError, RuntimeError) as error:
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
