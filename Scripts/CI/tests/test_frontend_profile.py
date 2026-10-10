from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RESOLVER_PATH = REPOSITORY_ROOT / "Scripts" / "Frontend" / "resolve_frontend_profile.py"
SPEC = importlib.util.spec_from_file_location("resolve_frontend_profile", RESOLVER_PATH)
assert SPEC and SPEC.loader
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)


class FrontendProfileResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.profile_file = Path(self.temp.name) / "frontend-profile.txt"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_tracked_default_profile_resolves_to_blazor_auto(self) -> None:
        self.assertEqual(resolver.resolve_frontend_profile(REPOSITORY_ROOT / "frontend-profile.txt"), "BlazorAuto")

    def test_file_value_is_trimmed(self) -> None:
        self.profile_file.write_text(" \tReact \r\n", encoding="utf-8")

        self.assertEqual(resolver.resolve_frontend_profile(self.profile_file), "React")

    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot read frontend profile file"):
            resolver.resolve_frontend_profile(self.profile_file)

    def test_empty_file_is_rejected(self) -> None:
        self.profile_file.write_text(" \r\n\t", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "is empty"):
            resolver.resolve_frontend_profile(self.profile_file)

    def test_unknown_or_multiple_values_are_rejected(self) -> None:
        for value in ("react\n", "BlazorAuto\nReact\n"):
            with self.subTest(value=value):
                self.profile_file.write_text(value, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "must be exactly"):
                    resolver.resolve_frontend_profile(self.profile_file)

    def test_explicit_override_is_trimmed_and_does_not_require_a_file(self) -> None:
        self.assertEqual(resolver.resolve_frontend_profile(self.profile_file, " React "), "React")

    def test_invalid_override_is_rejected(self) -> None:
        self.profile_file.write_text("BlazorAuto", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "must be exactly"):
            resolver.resolve_frontend_profile(self.profile_file, "react")

    def test_cli_emits_only_the_canonical_profile(self) -> None:
        self.profile_file.write_text("BlazorAuto\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(RESOLVER_PATH), "--profile-file", str(self.profile_file), "--override", " React "],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "React\n")
        self.assertEqual(result.stderr, "")


class MsBuildFrontendProfileTests(unittest.TestCase):
    def run_profile_target(
        self,
        profile_content: str | None,
        *,
        override: str | None = None,
        environment_profile: tuple[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="frontend-profile-msbuild-") as directory:
            project_root = Path(directory)
            shutil.copy2(REPOSITORY_ROOT / "Directory.Build.props", project_root / "Directory.Build.props")
            shutil.copy2(REPOSITORY_ROOT / "Directory.Build.targets", project_root / "Directory.Build.targets")
            if profile_content is not None:
                (project_root / "frontend-profile.txt").write_text(profile_content, encoding="utf-8")
            project_file = project_root / "ProfileProbe.csproj"
            project_file.write_text(
                '<Project Sdk="Microsoft.NET.Sdk">'
                "<PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup>"
                "</Project>",
                encoding="utf-8",
            )

            command = ["dotnet", "msbuild", str(project_file), "-nologo", "-target:ValidateFrontendProfile"]
            if override is not None:
                command.append(f"-property:FrontendProfile={override}")
            environment = os.environ.copy()
            environment.pop("FrontendProfile", None)
            if environment_profile is not None:
                environment[environment_profile[0]] = environment_profile[1]
            return subprocess.run(
                command,
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

    def test_msbuild_accepts_react_from_the_profile_file(self) -> None:
        result = self.run_profile_target(" React \n")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_msbuild_rejects_missing_file(self) -> None:
        result = self.run_profile_target(None)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or empty", result.stdout + result.stderr)

    def test_msbuild_rejects_empty_and_invalid_files(self) -> None:
        for content, message in ((" \n", "missing or empty"), ("react\n", "Invalid frontend profile")):
            with self.subTest(content=content):
                result = self.run_profile_target(content)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stdout + result.stderr)

    def test_explicit_msbuild_override_is_validated(self) -> None:
        result = self.run_profile_target("BlazorAuto\n", override="React")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_msbuild_does_not_select_from_environment(self) -> None:
        for variable_name in ("FrontendProfile", "FRONTENDPROFILE", "frontendprofile"):
            with self.subTest(variable_name=variable_name):
                result = self.run_profile_target("BlazorAuto\n", environment_profile=(variable_name, "React"))

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("environment variable is not supported", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
