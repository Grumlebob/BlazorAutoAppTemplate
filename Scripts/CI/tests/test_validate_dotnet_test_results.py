from __future__ import annotations

from collections import Counter
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from Scripts.CI.validate_dotnet_test_results import summarize_results, validate_results

OPT_IN = "Set RUN_E2E=1 to run Playwright E2E tests."


class DotnetTestResultValidationTests(unittest.TestCase):
    def write_trx(self, outcomes: tuple[str, ...], skip_message: str | None = OPT_IN) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "results.trx"
        result_rows = "".join(
            f'<UnitTestResult testName="case-{index}" outcome="{outcome}">'
            + (
                f"<Output><ErrorInfo><Message>{skip_message}</Message></ErrorInfo></Output>"
                if outcome == "NotExecuted" and skip_message is not None
                else ""
            )
            + "</UnitTestResult>"
            for index, outcome in enumerate(outcomes)
        )
        path.write_text(
            "<TestRun xmlns=\"http://microsoft.com/schemas/VisualStudio/TeamTest/2010\">"
            f"<Results>{result_rows}</Results></TestRun>",
            encoding="utf-8",
        )
        return path

    def test_any_number_of_passes_is_accepted_when_skips_are_explicit_opt_ins(self) -> None:
        for passed in (1, 7, 183):
            with self.subTest(passed=passed):
                path = self.write_trx(("Passed",) * passed + ("NotExecuted", "NotExecuted"))

                summary = validate_results(path)

                self.assertEqual((passed + 2, passed, 0, 2), (summary.total, summary.passed, summary.failed, summary.skipped))

    def test_a_skipped_test_without_an_opt_in_reason_fails_the_suite(self) -> None:
        for message in (None, "", "Flaky on CI", "Skipped for now"):
            with self.subTest(message=message):
                path = self.write_trx(("Passed", "NotExecuted"), skip_message=message)

                with self.assertRaisesRegex(ValueError, "no explicit opt-in reason"):
                    validate_results(path)

    def test_an_exact_skip_count_can_still_be_required(self) -> None:
        validate_results(self.write_trx(("Passed", "Passed")), expected_skipped=0)

        with self.assertRaisesRegex(ValueError, "skipped test count differs"):
            validate_results(self.write_trx(("Passed", "NotExecuted")), expected_skipped=0)
        with self.assertRaisesRegex(ValueError, "skipped test count differs"):
            validate_results(self.write_trx(("Passed", "NotExecuted")), expected_skipped=2)

    def test_fails_on_failed_or_unexpected_test_outcomes(self) -> None:
        for outcome in ("Failed", "Inconclusive"):
            with self.subTest(outcome=outcome):
                path = self.write_trx(("Passed", outcome))
                with self.assertRaisesRegex(ValueError, "unexpected test outcomes"):
                    validate_results(path)

    def test_fails_when_nothing_passed(self) -> None:
        with self.assertRaisesRegex(ValueError, "no test passed"):
            validate_results(self.write_trx(("NotExecuted",)))

    def test_fails_when_results_are_absent(self) -> None:
        path = self.write_trx(())

        with self.assertRaisesRegex(ValueError, "contains no test results"):
            summarize_results(path)


REPO_ROOT = Path(__file__).resolve().parents[3]
DOTNET = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

args = sys.argv[1:]
with open(os.environ["DOTNET_CALLS"], "a") as calls:
    calls.write(json.dumps(args) + "\n")
if args[0] != "test":
    sys.exit(0)
profile = next(value.split("=", 1)[1] for value in args if value.startswith("-p:FrontendProfile="))
cases = json.loads(os.environ["DOTNET_CASES"])[profile]
expression = args[args.index("--filter") + 1] if "--filter" in args else ""
allowed = {"", "FrontendProfile!=BlazorAuto", "FullyQualifiedName!~GrumPlates.Test.Features.Accounts",
           "FullyQualifiedName~GrumPlates.Test.Features.Accounts",
           "FullyQualifiedName!~GrumPlates.Test.Features.Accounts&FrontendProfile!=BlazorAuto",
           "FullyQualifiedName~GrumPlates.Test.Features.Accounts&FrontendProfile!=BlazorAuto"}
if expression not in allowed:
    sys.exit("Unexpected filter: " + expression)
if "FullyQualifiedName!~" in expression:
    cases = [case for case in cases if "GrumPlates.Test.Features.Accounts" not in case[0]]
elif "FullyQualifiedName~" in expression:
    cases = [case for case in cases if "GrumPlates.Test.Features.Accounts" in case[0]]
if "FrontendProfile!=BlazorAuto" in expression:
    cases = [case for case in cases if case[3] != "BlazorAuto"]
root = ET.Element("TestRun")
results = ET.SubElement(root, "Results")
for identity, outcome, message, trait in cases:
    result = ET.SubElement(results, "UnitTestResult", testName=identity, outcome=outcome)
    if message:
        ET.SubElement(ET.SubElement(ET.SubElement(result, "Output"), "ErrorInfo"), "Message").text = message
destination = Path(args[args.index("--results-directory") + 1])
destination.mkdir(parents=True, exist_ok=True)
name = args[args.index("--logger") + 1].split("LogFileName=", 1)[1]
ET.ElementTree(root).write(destination / name, encoding="utf-8")
'''

ACCOUNT = "GrumPlates.Test.Features.Accounts.CookieTests.Login"
NORMAL = "Template.Features.Example.Tests.Save"
PROFILES = ("BlazorAuto", "React")


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires Linux/WSL bash")
class FrontendValidationPartitionTests(unittest.TestCase):
    def run_gate(self, cases):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        executable = root / "dotnet"
        executable.write_text(DOTNET, encoding="utf-8")
        executable.chmod(0o755)
        calls = root / "calls.jsonl"
        results = root / "results"
        process = subprocess.run(
            ["bash", str(REPO_ROOT / "Scripts/CI/validate-frontend-profiles.sh"), str(results)],
            env=dict(os.environ, PATH=f"{root}{os.pathsep}{os.environ['PATH']}",
                     DOTNET_CASES=json.dumps(cases), DOTNET_CALLS=str(calls)),
            capture_output=True, text=True, check=False,
        )
        return process, [json.loads(line) for line in calls.read_text().splitlines()], results

    def good_cases(self):
        cases = [(NORMAL, "Passed", "", ""), (ACCOUNT + "(rememberMe: false)", "Passed", "", ""),
                 (ACCOUNT + "(rememberMe: true)", "Passed", "", ""),
                 ("GrumPlates.Test.E2E.Features.Accounts.IdentityE2ETests.Login", "NotExecuted", OPT_IN, ""),
                 (NORMAL + ".BlazorAssets", "Passed", "", "BlazorAuto"),
                 (ACCOUNT + ".BlazorAssets", "Passed", "", "BlazorAuto")]
        return {profile: list(cases) for profile in PROFILES}

    def test_each_profile_executes_each_eligible_case_once_and_retains_react_trait_filter(self):
        cases = self.good_cases()
        process, calls, results = self.run_gate(cases)
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        self.assertEqual(["restore", "build", "test", "test"] * 2, [call[0] for call in calls])
        for profile in PROFILES:
            expected = Counter(case[0] for case in cases[profile] if profile != "React" or case[3] != "BlazorAuto")
            selected = Counter(result.attrib["testName"] for report in (results / profile).rglob("*.trx")
                               for result in ET.parse(report).iter("UnitTestResult"))
            self.assertEqual(expected, selected, profile)
        for call in (call for call in calls if call[0] == "test"):
            self.assertIn("--no-build", call)
            self.assertIn("--no-restore", call)
            if "-p:FrontendProfile=React" in call:
                self.assertIn("&FrontendProfile!=BlazorAuto", call[call.index("--filter") + 1])

    def test_missing_accounts_in_either_profile_fails(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                cases = self.good_cases()
                cases[profile] = [(NORMAL, "Passed", "", "")]
                process, _, _ = self.run_gate(cases)
                self.assertNotEqual(0, process.returncode)
                self.assertIn("contains no test results", process.stderr)

    def test_account_skips_and_failures_fail_for_each_profile(self):
        for profile in PROFILES:
            for outcome, message in (("NotExecuted", OPT_IN), ("Failed", "")):
                with self.subTest(profile=profile, outcome=outcome):
                    cases = self.good_cases()
                    cases[profile].append((ACCOUNT + ".Other", outcome, message, ""))
                    process, _, _ = self.run_gate(cases)
                    self.assertNotEqual(0, process.returncode)
                    self.assertIn("expected skipped=0" if outcome == "NotExecuted" else "unexpected test outcomes", process.stderr)

    def test_zero_discovery_and_unexplained_non_account_skips_fail(self):
        for cases in (
            {profile: [] for profile in PROFILES},
            {profile: [(NORMAL, "NotExecuted", "Flaky", ""), (ACCOUNT, "Passed", "", "")] for profile in PROFILES},
        ):
            process, calls, _ = self.run_gate(cases)
            self.assertNotEqual(0, process.returncode)
            self.assertEqual(1, sum(call[0] == "test" for call in calls))


if __name__ == "__main__":
    unittest.main()
