from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

from Scripts.Quality import sonar_report as sr


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sonar"
PROJECT = "grumplates-abc12345-BlazorAuto"
IDENTITY = "github.com/grumlebob/grumplates"
SHA = "ed87fedcaf09ab7e3c8b62303ae8b64325b30aea"
ANALYSIS_ID = "7d5ec4c9-f501-46e1-91fd-44f653016317"
PROJECT_VERSION = "20261008-ed87fedcaf09"
SETTINGS_DIGEST = "a" * 64
REPO_ROOT = "C:/fake/repo"
GEOMETRY = "GrumPlates.Client/Features/Books/Shared/BookCoverGeometry.cs"
CORE = "GrumPlates.Core/Features/Books/UseCases/GetBooks/GetBooksResponse.cs"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


ISSUE_DOC = load("issues-search.json")
ISSUES = ISSUE_DOC["issues"]
RULES = ISSUE_DOC["rules"]
TREE = load("component-tree.json")["components"]
MEASURES = load("measures-component.json")
GATE = load("qualitygate.json")
ANALYSES = load("project-analyses.json")
CHURN_TEXT = (
    "@@aaa111\n"
    f"{GEOMETRY}\n{GEOMETRY}\n{CORE}\n"
    "\n@@bbb222\n"
    f"{GEOMETRY}\n"
    "\n@@ccc333\n"
    f"{GEOMETRY}\n"
)
RUN_EVIDENCE = {
    "tests": {"frontendTests": {"status": "not-applicable"},
              "dotnet": {"passed": 190, "failed": 0, "skipped": 13, "total": 203, "result": "tests/suite.trx"}},
    "coverage": {"reactLcov": "not-applicable", "dotnet": {"valid": True, "directReportCount": 1,
                                                                  "coveredProductionSources": [GEOMETRY]}},
}


def paged(items: list, params: dict, key: str, total: int | None = None, **extra) -> dict:
    page = int(params.get("p", 1))
    size = int(params.get("ps", sr.PAGE_SIZE))
    chunk = items[(page - 1) * size: page * size]
    return {key: chunk, "paging": {"pageIndex": page, "pageSize": size,
                                  "total": len(items) if total is None else total}, **extra}


class FakeClient:
    def __init__(self, routes: dict) -> None:
        self.routes = routes
        self.calls: list[tuple[str, dict]] = []

    def fetch_json(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        self.calls.append((path, params))
        route = self.routes[path]
        if isinstance(route, BaseException):
            raise route
        return route(params) if callable(route) else route


def standard_routes(hotspots=None, analyses=None, tree=None) -> dict:
    return {
        "api/measures/component": MEASURES,
        "api/qualitygates/project_status": GATE,
        "api/project_analyses/search": analyses or ANALYSES,
        "api/issues/search": lambda params: paged(
            [] if params.get("inNewCodePeriod") else ISSUE_DOC["issues"], params, "issues",
            rules=[] if params.get("inNewCodePeriod") else RULES),
        "api/hotspots/search": hotspots or (lambda params: {"hotspots": [], "paging": {"total": 0}}),
        "api/measures/component_tree": tree or (lambda params: paged(TREE, params, "components")),
    }


def report_request(profile: str, run_evidence: dict) -> sr.ReportRequest:
    return sr.ReportRequest(
        project=PROJECT,
        repo_root=REPO_ROOT,
        sha=SHA,
        churn_days=180,
        repository_identity=IDENTITY,
        frontend_profile=profile,
        analysis_id=ANALYSIS_ID,
        project_version=PROJECT_VERSION,
        settings_digest=SETTINGS_DIGEST,
        settings_snapshot={"hostPort": 9200},
        server_version="26.9.0.129388",
        run_evidence=run_evidence,
    )


def build_standard_report(routes: dict | None = None, path_exists=None, profile: str = "BlazorAuto") -> dict:
    run_evidence = RUN_EVIDENCE
    if profile == "React":
        run_evidence = {
            "tests": {"frontendTests": {"passed": 31, "failed": 0, "skipped": 0, "total": 31},
                      "dotnet": {"passed": 182, "failed": 0, "skipped": 13, "total": 195, "result": "tests/suite.trx"}},
            "coverage": {"reactLcov": "validated", "dotnet": {"valid": True, "directReportCount": 1,
                                                                        "coveredProductionSources": [GEOMETRY]}},
        }
    return sr.build_report(
        FakeClient(routes or standard_routes()), report_request(profile, run_evidence), CHURN_TEXT,
        path_exists=path_exists or (lambda path: True),
    )


class RiskAndClassificationTests(unittest.TestCase):
    def test_risk_formula_handles_missing_and_zero_coverable_lines(self) -> None:
        self.assertEqual(sr.uncovered_fraction(None, None), (0.5, True))
        self.assertEqual(sr.uncovered_fraction(None, "0"), (0.0, False))
        self.assertEqual(sr.uncovered_fraction("80", "100"), (0.2, False))
        self.assertEqual(sr.risk_score(16, 0, 0.5, 0, 0), 6.0)
        self.assertEqual(sr.risk_score(0, 7, 0.0, 1, 0), 10.0)

    def test_multi_impact_and_legacy_issues_count_once_per_quality(self) -> None:
        self.assertTrue(sr.is_relsec(ISSUES[0]))
        legacy = {"type": "VULNERABILITY", "severity": "CRITICAL", "impacts": []}
        self.assertTrue(sr.is_relsec(legacy))
        self.assertEqual(sr.qualities_of(legacy), {"SECURITY"})
        report = build_standard_report()
        self.assertEqual(len(report["issues"]), 3)
        self.assertEqual(report["rules"][0]["count"], 1)

    def test_file_risk_uses_churn_coverage_and_unique_issue_counts(self) -> None:
        report = build_standard_report()
        files = {entry["path"]: entry for entry in report["files"]}
        geometry = files[GEOMETRY]
        self.assertEqual(geometry["commits"], 3)
        self.assertEqual(geometry["relsec"], 1)
        self.assertEqual(geometry["other"], 1)
        self.assertEqual(geometry["risk"], sr.risk_score(478, 3, 0.415, 1, 1))
        core = files[CORE]
        self.assertEqual(core["commits"], 1)
        self.assertEqual(core["relsec"], 1)
        self.assertEqual(core["other"], 0)

    def test_missing_file_coverage_stays_null_and_marks_risk_fallback(self) -> None:
        python_file = {"path": "Scripts/Quality/example.py", "measures": [
            {"metric": "cognitive_complexity", "value": "16"}]}
        built = sr.build_files([python_file], [], sr.Counter())
        self.assertIsNone(built[0]["metrics"].get("coverage"))
        self.assertTrue(built[0]["coverageFallbackUsedForRiskOnly"])

    def test_files_sort_deterministically(self) -> None:
        report = build_standard_report()
        ordered = [(-entry["risk"], entry["path"]) for entry in report["files"]]
        self.assertEqual(ordered, sorted(ordered))


class PaginationTests(unittest.TestCase):
    def test_pagination_fetches_every_page(self) -> None:
        client = FakeClient({"api/issues/search": lambda params: paged(ISSUES, params, "issues", rules=RULES)})
        with mock.patch.object(sr, "PAGE_SIZE", 2):
            found, _ = sr.paginate(client, "api/issues/search", {}, "issues")
        self.assertEqual(len(found), 3)
        self.assertEqual([params["p"] for path, params in client.calls], [1, 2])

    def test_incomplete_page_set_fails_instead_of_returning_partial_data(self) -> None:
        def route(params: dict) -> dict:
            return {"issues": ISSUE_DOC["issues"][:1] if params.get("p") == 1 else [],
                    "paging": {"total": 3}}
        client = FakeClient({"api/issues/search": route})
        with mock.patch.object(sr, "PAGE_SIZE", 1):
            with self.assertRaisesRegex(sr.IncompleteDataError, "empty page"):
                sr.paginate(client, "api/issues/search", {}, "issues")

    def test_over_cap_issues_split_by_quality_rule_and_dedupe_impacts(self) -> None:
        issues = ISSUE_DOC["issues"]
        per_quality = {"MAINTAINABILITY": [issues[0], issues[2]],
                       "RELIABILITY": [issues[0], issues[1]], "SECURITY": [issues[0]]}
        by_rule = {quality: {issue["rule"]: [item for item in values if item["rule"] == issue["rule"]]
                             for issue in values} for quality, values in per_quality.items()}

        def route(params: dict) -> dict:
            quality = params.get("impactSoftwareQualities")
            selected = per_quality.get(quality, issues)
            if params.get("facets") == "rules":
                counts = {}
                for item in selected:
                    counts[item["rule"]] = counts.get(item["rule"], 0) + 1
                return {"facets": [{"property": "rules", "values": [{"val": k, "count": v} for k, v in counts.items()]}],
                        "paging": {"total": len(selected)}}
            if params.get("rules"):
                selected = by_rule.get(quality, {}).get(params["rules"], [])
            return paged(selected, params, "issues", rules=RULES)

        client = FakeClient({"api/issues/search": route})
        with mock.patch.object(sr, "ISSUE_CAP", 1):
            found, _ = sr.fetch_issues(client, PROJECT, {})
        self.assertEqual({item["key"] for item in found}, {item["key"] for item in issues})
        self.assertTrue(any(params.get("facets") == "rules" for _, params in client.calls))

    def test_oversized_rule_splits_by_component_and_checks_counts(self) -> None:
        issue_a = {**ISSUES[0], "key": "a", "component": f"{PROJECT}:GrumPlates.Client/A.cs"}
        issue_b = {**ISSUES[0], "key": "b", "component": f"{PROJECT}:GrumPlates.Client/B.cs"}
        items = [issue_a, issue_b]
        file_tree = [{"key": f"{PROJECT}:GrumPlates.Client/A.cs"}, {"key": f"{PROJECT}:GrumPlates.Client/B.cs"}]

        def issue_route(params: dict) -> dict:
            quality = params.get("impactSoftwareQualities")
            selected = items if quality in {None, "MAINTAINABILITY"} else []
            component = params.get("components")
            if component and component != PROJECT:
                selected = [item for item in selected if item["component"] == component]
            if params.get("facets") == "rules":
                return {"facets": [{"property": "rules", "values": [{"val": "csharpsquid:S6709", "count": 2}]}],
                        "paging": {"total": 2}}
            if params.get("rules"):
                selected = [item for item in selected if item["rule"] == params["rules"]]
            return paged(selected, params, "issues", rules=RULES)

        client = FakeClient({
            "api/issues/search": issue_route,
            "api/measures/component_tree": lambda params: paged(file_tree, params, "components"),
        })
        with mock.patch.object(sr, "ISSUE_CAP", 1):
            found, _ = sr.fetch_issues(client, PROJECT, {})
        self.assertEqual({item["key"] for item in found}, {"a", "b"})
        split_components = {params.get("components") for _, params in client.calls
                           if params.get("ps") == 500 and params.get("components") and params.get("components") != PROJECT}
        self.assertEqual(split_components, {issue_a["component"], issue_b["component"]})


class ReportCompletenessTests(unittest.TestCase):
    def test_report_binds_schema_run_scope_gate_and_metadata_to_exact_analysis(self) -> None:
        client = FakeClient(standard_routes())
        report = sr.build_report(
            client, report_request("BlazorAuto", RUN_EVIDENCE), CHURN_TEXT,
            path_exists=lambda path: True,
        )
        self.assertTrue(report["complete"])
        self.assertEqual(report["schema"], "grumplates.sonar-report/1")
        self.assertEqual(report["repositoryIdentity"], IDENTITY)
        self.assertEqual(report["frontendProfile"], "BlazorAuto")
        self.assertEqual(report["analysisId"], ANALYSIS_ID)
        self.assertEqual(report["qualityGate"], {"status": "OK", "analysisId": ANALYSIS_ID, "informational": True})
        self.assertTrue(all(report["scopeEvidence"][name] for name in ("bookGeometry", "bookRazor", "sharedCore", "handwrittenCss", "reactImplementationExcluded")))
        self.assertIn(("api/qualitygates/project_status", {"analysisId": ANALYSIS_ID}), client.calls)

    def test_latest_analysis_change_during_export_aborts(self) -> None:
        calls = 0
        def analyses(params: dict) -> dict:
            nonlocal calls
            calls += 1
            if calls == 1:
                return ANALYSES
            changed = json.loads(json.dumps(ANALYSES))
            changed["analyses"][0]["revision"] = "0" * 40
            return changed
        routes = standard_routes(analyses=analyses)
        with self.assertRaisesRegex(sr.IncompleteDataError, "analysis changed"):
            build_standard_report(routes)

    def test_report_incomplete_when_path_or_profile_evidence_is_missing(self) -> None:
        report = build_standard_report(path_exists=lambda path: path != GEOMETRY)
        self.assertFalse(report["complete"])
        self.assertEqual(report["dataCompleteness"]["fileList"], "incomplete")

    def test_core_metric_absence_is_not_reported_as_zero(self) -> None:
        measures = json.loads(json.dumps(MEASURES))
        measures["component"]["measures"] = [m for m in measures["component"]["measures"] if m["metric"] != "coverage"]
        report = build_standard_report({**standard_routes(), "api/measures/component": measures})
        self.assertFalse(report["complete"])
        self.assertIsNone(report["measures"]["coverage"])
        self.assertIn("coverage", report["coreMeasureCompleteness"]["missing"])

    def test_react_scope_and_lcov_evidence(self) -> None:
        react_tree = [
            {"key": f"{PROJECT}:GrumPlates/Frontend/FrontendComposition.React.cs", "path": "GrumPlates/Frontend/FrontendComposition.React.cs", "measures": []},
            {"key": f"{PROJECT}:GrumPlates/Frontend/OpenApi/OpenApiMetadataHosting.cs", "path": "GrumPlates/Frontend/OpenApi/OpenApiMetadataHosting.cs", "measures": []},
            {"key": f"{PROJECT}:GrumPlates.React/app/features/books/catalog-page.tsx", "path": "GrumPlates.React/app/features/books/catalog-page.tsx", "measures": []},
            {"key": f"{PROJECT}:GrumPlates.React/app/api/client.ts", "path": "GrumPlates.React/app/api/client.ts", "measures": [{"metric": "coverage", "value": "75.0"}]},
        ]
        report = build_standard_report(standard_routes(tree=lambda params: paged(react_tree, params, "components")), profile="React")
        self.assertTrue(report["complete"])
        self.assertTrue(report["scopeEvidence"]["testedApiModuleHasCoverage"])
        self.assertTrue(report["scopeEvidence"]["blazorImplementationExcluded"])

    def test_quality_ratings_are_exported_and_rendered_as_letters(self) -> None:
        client = FakeClient(standard_routes())
        report = sr.build_report(client, report_request("BlazorAuto", RUN_EVIDENCE), CHURN_TEXT, path_exists=lambda path: True)
        requested = next(params for path, params in client.calls
                         if path == "api/measures/component")["metricKeys"].split(",")
        for metric in ("software_quality_maintainability_rating", "software_quality_reliability_rating",
                       "software_quality_security_rating"):
            self.assertIn(metric, requested)
        self.assertEqual(report["measures"]["software_quality_security_rating"], "4.0")
        self.assertIn("Ratings: maintainability A, reliability C, security D", sr.render_markdown(report))

    def test_missing_or_unusable_rating_renders_as_not_available(self) -> None:
        self.assertEqual([sr.rating_letter(value) for value in ("1.0", "2.0", "5.0", 3)], ["A", "B", "E", "C"])
        for value in (None, "", "n/a", "0.0", "6.0"):
            with self.subTest(value=value):
                self.assertEqual(sr.rating_letter(value), "n/a")

    def test_run_evidence_rejects_boolean_test_counts(self) -> None:
        evidence = json.loads(json.dumps(RUN_EVIDENCE))
        evidence["tests"]["dotnet"]["passed"] = True
        valid, warnings = sr.validate_run_evidence("BlazorAuto", evidence)
        self.assertFalse(valid)
        self.assertIn("The approved .NET suite result counts are missing or invalid.", warnings)

    def test_run_evidence_does_not_pin_dotnet_test_counts(self) -> None:
        for passed, skipped in ((1, 0), (183, 13), (400, 40)):
            with self.subTest(passed=passed, skipped=skipped):
                evidence = json.loads(json.dumps(RUN_EVIDENCE))
                evidence["tests"]["dotnet"].update({"passed": passed, "skipped": skipped, "total": passed + skipped})
                valid, warnings = sr.validate_run_evidence("BlazorAuto", evidence)
                self.assertTrue(valid, warnings)
        for field, value in (("passed", 0), ("failed", 1)):
            with self.subTest(field=field):
                evidence = json.loads(json.dumps(RUN_EVIDENCE))
                evidence["tests"]["dotnet"][field] = value
                valid, warnings = sr.validate_run_evidence("BlazorAuto", evidence)
                self.assertFalse(valid)
                self.assertIn("The approved .NET suite result counts are missing or invalid.", warnings)

    def test_invalid_nested_run_evidence_still_renders_incomplete_report(self) -> None:
        evidence = {"tests": None, "coverage": "invalid"}
        report = sr.build_report(
            FakeClient(standard_routes()), report_request("BlazorAuto", evidence), CHURN_TEXT,
            path_exists=lambda path: True,
        )
        self.assertFalse(report["complete"])
        self.assertIn("n/a passed", sr.render_markdown(report))


class HotspotAndSanitizationTests(unittest.TestCase):
    def test_hotspot_capability_states_are_not_conflated(self) -> None:
        unsupported = sr.fetch_hotspots(FakeClient({"api/hotspots/search": HTTPError("http://x", 404, "Not Found", None, None)}), PROJECT)
        forbidden = sr.fetch_hotspots(FakeClient({"api/hotspots/search": HTTPError("http://x", 403, "Denied", None, None)}), PROJECT)
        unavailable = sr.fetch_hotspots(FakeClient({"api/hotspots/search": URLError("offline")}), PROJECT)
        self.assertEqual(unsupported["status"], "unsupported")
        self.assertTrue(unsupported["complete"])
        self.assertEqual(forbidden["status"], "forbidden")
        self.assertFalse(forbidden["complete"])
        self.assertEqual(unavailable["status"], "unreachable")
        self.assertFalse(unavailable["complete"])
        busy_client = FakeClient({"api/hotspots/search": HTTPError("http://x", 503, "Busy", None, None)})
        with self.assertRaises(HTTPError):
            sr.fetch_hotspots(busy_client, PROJECT)

    def test_authors_paths_and_token_sentinels_are_sanitized(self) -> None:
        issue = sr.normalize_issue({**ISSUES[0], "message": r"At C:\Users\private\secret.cs contact me@example.invalid token sentinel-value"}, PROJECT)
        clean = sr.sanitize_document(issue, {"sentinel-value"})
        encoded = json.dumps(clean)
        self.assertNotIn("reviewer@example.invalid", encoded)
        self.assertNotIn("me@example.invalid", encoded)
        self.assertNotIn("C:\\Users\\private", encoded)
        self.assertNotIn("sentinel-value", encoded)

    def test_hotspot_and_permission_empty_results_are_explicit(self) -> None:
        result = sr.fetch_hotspots(FakeClient({"api/hotspots/search": lambda params: {"hotspots": [], "paging": {"total": 0}}}), PROJECT)
        self.assertEqual(result["status"], "supported-empty")
        self.assertEqual(result["items"], [])


class ClientAndCliTests(unittest.TestCase):
    def test_client_rejects_non_loopback_servers(self) -> None:
        with self.assertRaisesRegex(ValueError, "loopback"):
            sr.SonarClient("https://sonar.example.test", "token")

    def test_cli_missing_token_exits_with_two(self) -> None:
        arguments = ["--base-url", "http://127.0.0.1:9200", "--project", PROJECT,
                     "--repo-root", REPO_ROOT, "--out-dir", "unused", "--repository-identity", IDENTITY,
                     "--frontend-profile", "BlazorAuto", "--sha", SHA, "--analysis-id", ANALYSIS_ID,
                     "--project-version", PROJECT_VERSION, "--settings-digest", SETTINGS_DIGEST,
                     "--settings-file", "unused", "--evidence-json", "unused", "--server-version", "26.9"]
        with mock.patch.dict(os.environ, {}, clear=True):
            with redirect_stderr(io.StringIO()) as stderr:
                code = sr.main(arguments)
        self.assertEqual(code, 2)
        self.assertIn(sr.TOKEN_ENV, stderr.getvalue())

    def test_retries_503_then_succeeds(self) -> None:
        import io as io_module
        from unittest import mock as mock_module

        responses = [HTTPError("http://x", 503, "busy", None, None), io_module.BytesIO(b'{"ok": true}')]

        class Response(io_module.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *exc): return False

        def opener(request, timeout):
            item = responses.pop(0)
            if isinstance(item, Exception): raise item
            return Response(item.getvalue())

        sleeps: list[float] = []
        client = sr.SonarClient("http://127.0.0.1:9200", "token", opener=opener, sleep=sleeps.append)
        self.assertEqual(client.fetch_json("api/system/status"), {"ok": True})
        self.assertEqual(sleeps, [sr.HTTP_RETRY_DELAY_SECONDS])


class MarkdownTests(unittest.TestCase):
    def test_markdown_contains_identity_completeness_and_exact_issue_keys(self) -> None:
        report = build_standard_report()
        markdown = sr.render_markdown(report)
        self.assertIn(IDENTITY, markdown)
        self.assertIn(ANALYSIS_ID, markdown)
        self.assertIn("informational", markdown)
        self.assertIn(ISSUES[0]["key"], markdown)
        self.assertIn("Profile scope evidence", markdown)
        self.assertIn("Security hotspots requiring review", markdown)

    def test_markdown_sections_are_bounded_and_ordered(self) -> None:
        report = build_standard_report()
        headings = [line for line in sr.render_markdown(report).splitlines() if line.startswith("## ")]
        self.assertEqual(headings, [
            "## Run evidence", "## Profile scope evidence", "## Security hotspots requiring review (0)",
            "## Security and blocker issues (0)", "## Reliability issues, MEDIUM and above (2)",
            "## New since the previous analysis (0)", "## Top 30 rules", "## Risk-ranked files (top 40)",
            "## Duplication (top 15 files by duplicated lines)", "## How to use this report",
        ])

    def test_issue_lists_are_bounded(self) -> None:
        report = build_standard_report()
        report["issues"] = [dict(report["issues"][0], key=f"issue-{index}",
                                 impacts=[{"softwareQuality": "SECURITY", "severity": "HIGH"}])
                             for index in range(100)]
        report["newCodeIssues"] = [dict(report["issues"][0], key=f"new-{index}") for index in range(60)]
        markdown = sr.render_markdown(report)
        security = markdown.split("## Security and blocker issues")[1].split("## Reliability")[0]
        self.assertEqual(len([line for line in security.splitlines() if line.startswith("| `issue-")]), 50)
        new_section = markdown.split("## New since the previous analysis")[1].split("## Top")[0]
        self.assertEqual(len([line for line in new_section.splitlines() if line.startswith("- `new-")]), 50)


if __name__ == "__main__":
    unittest.main()
