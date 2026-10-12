from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from Scripts.Quality.summarize_sarif import (
    HIGH_SIGNAL_RULES,
    SCHEMA,
    family_of,
    main,
    read_findings,
    scope_of,
    to_repo_relative,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sarif"
FAKE_ROOT = "C:/fake/repo"


def run_main(extra: list[str], out_dir: str, sarif_dir: Path = FIXTURES) -> tuple[int, str]:
    argv = [
        "--sarif-dir", str(sarif_dir), "--repo-root", FAKE_ROOT, "--out-dir", out_dir,
        "--repository-identity", "github.com/example/blazorautoapptemplate",
        "--frontend-profile", "React", "--configuration", "Release",
        "--configuration-digest", "a" * 64,
        "--analyzer-version", "10.35.0.4138", "--run-id", "fixture-run", *extra,
    ]
    output = StringIO()
    with redirect_stdout(output):
        code = main(argv)
    return code, output.getvalue()


class ToRepoRelativeTests(unittest.TestCase):
    def test_windows_file_uri_becomes_repo_relative(self) -> None:
        self.assertEqual(
            to_repo_relative("file:///C:/fake/repo/BlazorAutoApp.Core/Features/Books/UseCases/GetBook/GetBookRequest.cs", "C:\\fake\\repo"),
            "BlazorAutoApp.Core/Features/Books/UseCases/GetBook/GetBookRequest.cs",
        )

    def test_posix_file_uri_becomes_repo_relative(self) -> None:
        self.assertEqual(
            to_repo_relative("file:///home/runner/work/BlazorAutoAppTemplate/BlazorAutoApp/Program.cs", "/home/runner/work/BlazorAutoAppTemplate"),
            "BlazorAutoApp/Program.cs",
        )

    def test_original_casing_of_the_relative_path_is_preserved(self) -> None:
        self.assertEqual(
            to_repo_relative("file:///C:/Fake/Repo/BlazorAutoApp.Core/Features/Books/UseCases/GetBooks/GetBooksResponse.cs", "C:/fake/repo"),
            "BlazorAutoApp.Core/Features/Books/UseCases/GetBooks/GetBooksResponse.cs",
        )

    def test_percent_encoding_is_decoded(self) -> None:
        self.assertEqual(
            to_repo_relative("file:///C:/fake/repo/BlazorAutoApp.Core/Features/Books/My%20Folder/Z.cs", FAKE_ROOT),
            "BlazorAutoApp.Core/Features/Books/My Folder/Z.cs",
        )

    def test_path_outside_the_repo_stays_absolute(self) -> None:
        self.assertEqual(to_repo_relative("file:///D:/elsewhere/Y.cs", FAKE_ROOT), "<outside-repository>/Y.cs")


class ClassificationTests(unittest.TestCase):
    def test_family_mapping(self) -> None:
        self.assertEqual(family_of("S108"), "sonar")
        self.assertEqual(family_of("CA1822"), "dotnet")
        self.assertEqual(family_of("SYSLIB1045"), "dotnet")
        self.assertEqual(family_of("IDE0005"), "style")
        self.assertEqual(family_of("XYZ123"), "other")

    def test_scope_mapping(self) -> None:
        self.assertEqual(scope_of("BlazorAutoApp.Core/Features/Books/X.cs", "BlazorAutoApp.Core.sarif"), "production")
        self.assertEqual(scope_of("BlazorAutoApp/Migrations/20240101_Init.cs", "BlazorAutoApp.sarif"), "generated")
        self.assertEqual(scope_of("BlazorAutoApp/obj/Debug/Gen.g.cs", "BlazorAutoApp.sarif"), "generated")
        self.assertEqual(scope_of("BlazorAutoApp/Views/Page.Designer.cs", "BlazorAutoApp.sarif"), "generated")
        self.assertEqual(scope_of("BlazorAutoApp.Test/FooTests.cs", "BlazorAutoApp.sarif"), "test")
        self.assertEqual(scope_of("Anything.cs", "BlazorAutoApp.Test.sarif"), "test")


class ReadFindingsTests(unittest.TestCase):
    def test_duplicates_and_suppressed_results_are_dropped(self) -> None:
        findings, _ = read_findings(str(FIXTURES), FAKE_ROOT)
        s108 = [f for f in findings if f.rule == "S108" and f.path == "BlazorAutoApp.Core/Features/Books/UseCases/GetBook/GetBookRequest.cs"]
        self.assertEqual(len(s108), 1)
        self.assertEqual(s108[0].line, 12)

    def test_missing_region_counts_as_line_zero(self) -> None:
        findings, _ = read_findings(str(FIXTURES), FAKE_ROOT)
        ide = next(f for f in findings if f.rule == "IDE0005")
        self.assertEqual(ide.line, 0)

    def test_rule_description_falls_back_to_full_description(self) -> None:
        _, descriptions = read_findings(str(FIXTURES), FAKE_ROOT)
        self.assertEqual(descriptions["CA1822"], "Mark members as static")
        self.assertEqual(descriptions["S108"], "Nested blocks of code should not be left empty")

    def test_first_rule_description_wins_across_sarif_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for name, description in (("A.sarif", "first"), ("B.sarif", "second")):
                document = {"runs": [{"tool": {"driver": {"rules": [
                    {"id": "S1234", "shortDescription": {"text": description}},
                ]}}, "results": []}]}
                Path(directory, name).write_text(json.dumps(document), encoding="utf-8")
            _, descriptions = read_findings(directory, FAKE_ROOT)
        self.assertEqual(descriptions["S1234"], "first")


class SummaryOutputTests(unittest.TestCase):
    def test_empty_directory_exits_with_two(self) -> None:
        with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as out:
            code, _ = run_main([], out, Path(empty))
        self.assertEqual(code, 2)

    def test_summary_json_totals_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            code, _ = run_main(["--sha", "abc1234"], out)
            summary = json.loads(Path(out, "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(summary["schema"], SCHEMA)
        self.assertEqual(summary["repositoryIdentity"], "github.com/example/blazorautoapptemplate")
        self.assertEqual(summary["frontendProfile"], "React")
        self.assertEqual(summary["sha"], "abc1234")
        self.assertFalse(summary["dirty"])
        self.assertEqual(summary["configuration"], "Release")
        self.assertEqual(summary["configurationDigest"], "a" * 64)
        self.assertEqual(summary["analyzerVersion"], "10.35.0.4138")
        self.assertEqual(summary["runId"], "fixture-run")
        self.assertEqual(summary["totals"]["production"], 4)
        self.assertEqual(summary["totals"]["generated"], 1)
        self.assertEqual(summary["totals"]["test"], 1)  # the S2699 result in BlazorAutoApp.Test.sarif
        self.assertEqual(summary["totals"]["byFamily"], {"sonar": 1, "dotnet": 2, "style": 1, "other": 0})

    def test_generated_findings_are_counted_but_not_listed(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            run_main([], out)
            summary = json.loads(Path(out, "summary.json").read_text(encoding="utf-8"))
        self.assertFalse(any("Migrations" in f["path"] for f in summary["findings"]))
        self.assertFalse(any("Migrations" in f["path"] for f in summary["files"]))

    def test_include_tests_changes_findings_but_not_totals(self) -> None:
        with tempfile.TemporaryDirectory() as without, tempfile.TemporaryDirectory() as with_tests:
            run_main([], without)
            run_main(["--include-tests"], with_tests)
            plain = json.loads(Path(without, "summary.json").read_text(encoding="utf-8"))
            tested = json.loads(Path(with_tests, "summary.json").read_text(encoding="utf-8"))
        self.assertNotIn("S2699", [f["rule"] for f in plain["findings"]])
        self.assertIn("S2699", [f["rule"] for f in tested["findings"]])
        self.assertEqual(plain["totals"]["test"], 1)
        self.assertEqual(tested["totals"]["test"], 1)

    def test_rules_sorted_by_production_count_and_capped_examples(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            run_main([], out)
            summary = json.loads(Path(out, "summary.json").read_text(encoding="utf-8"))
        production_counts = [rule["production"] for rule in summary["rules"]]
        self.assertEqual(production_counts, sorted(production_counts, reverse=True))
        for rule in summary["rules"]:
            self.assertLessEqual(len(rule["examples"]), 5)

    def test_summary_markdown_lists_high_signal_s108(self) -> None:
        self.assertIn("S108", HIGH_SIGNAL_RULES)
        with tempfile.TemporaryDirectory() as out:
            run_main([], out)
            markdown = Path(out, "summary.md").read_text(encoding="utf-8")
        self.assertIn("High-signal findings", markdown)
        self.assertIn("`BlazorAutoApp.Core/Features/Books/UseCases/GetBook/GetBookRequest.cs:12`", markdown)


if __name__ == "__main__":
    unittest.main()
