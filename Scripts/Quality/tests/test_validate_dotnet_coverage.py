from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import uuid

from Scripts.Quality.validate_dotnet_coverage import validate_reports


class DotnetCoverageValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.tests = self.root / "tests"
        self.repo.mkdir()
        self.tests.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_report(self, source: str, assembly: str = "BlazorAutoApp.Client.dll", covered: int = 2) -> Path:
        source_path = self.repo / source
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("// fixture\n", encoding="utf-8")
        directory = self.tests / str(uuid.uuid4())
        directory.mkdir()
        report = directory / "coverage.xml"
        report.write_text(
            """<results><modules>
              <module name="{assembly}" lines_covered="{covered}" lines_not_covered="3">
                <functions><function><ranges>
                  <range source_id="1" start_line="1" end_line="1" covered="yes" />
                </ranges></function></functions>
                <source_files><source_file id="1" path="{source}" /></source_files>
              </module>
            </modules></results>""".format(assembly=assembly, source=source_path.as_posix(), covered=covered),
            encoding="utf-8",
        )
        return report

    def test_accepts_profile_coverage_from_direct_guid_child(self) -> None:
        self.write_report("BlazorAutoApp.Client/Components/Books/Book.razor.cs")
        result = validate_reports(self.tests, self.repo, "BlazorAuto")
        self.assertTrue(result["valid"])
        self.assertEqual(result["reportCount"], 1)
        self.assertEqual(result["coveredProductionSources"], ["BlazorAutoApp.Client/Components/Books/Book.razor.cs"])

    def test_accepts_react_host_coverage(self) -> None:
        self.write_report("BlazorAutoApp/Hosting/OpenApiMetadataHosting.cs", "BlazorAutoApp.dll")
        self.assertTrue(validate_reports(self.tests, self.repo, "React")["valid"])

    def test_ignores_deeper_duplicate_collector_copy(self) -> None:
        self.write_report("BlazorAutoApp.Client/Components/Books/Book.cs")
        deeper = self.tests / next(self.tests.iterdir()).name / "In"
        deeper.mkdir()
        (deeper / "coverage.xml").write_text("<broken>", encoding="utf-8")
        self.assertEqual(validate_reports(self.tests, self.repo, "BlazorAuto")["reportCount"], 1)

    def test_rejects_unresolved_source(self) -> None:
        report = self.write_report("BlazorAutoApp.Client/Book.cs")
        report.write_text(
            report.read_text(encoding="utf-8").replace(self.repo.as_posix(), (self.root / "missing").as_posix()),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            validate_reports(self.tests, self.repo, "BlazorAuto")

    def test_rejects_zero_production_coverage(self) -> None:
        self.write_report("BlazorAutoApp.Client/Book.cs", covered=0)
        with self.assertRaisesRegex(ValueError, "no covered production"):
            validate_reports(self.tests, self.repo, "BlazorAuto")

    def test_rejects_non_guid_report_directory(self) -> None:
        self.write_report("BlazorAutoApp.Client/Book.cs")
        report = next(self.tests.glob("*/*.xml"))
        renamed = self.tests / "not-a-guid" / report.name
        renamed.parent.mkdir()
        report.rename(renamed)
        with self.assertRaisesRegex(ValueError, "GUID child"):
            validate_reports(self.tests, self.repo, "BlazorAuto")


if __name__ == "__main__":
    unittest.main()
