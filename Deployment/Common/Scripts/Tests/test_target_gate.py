"""Execute each workflow's first target gate without a runner or network."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]


class TargetGateTests(unittest.TestCase):
    def gates(self):
        workflows = sorted(set((ROOT / ".github/workflows").glob("cd-*.yml")) |
                           set((ROOT / ".github/workflows").glob("*-maintenance.yml")))
        self.assertTrue(workflows)
        for workflow in workflows:
            text = workflow.read_text()
            jobs = re.split(r"(?m)^    steps:\n", text)[1:]
            self.assertTrue(jobs, workflow.name)
            for index, steps in enumerate(jobs):
                first = re.split(r"(?m)^      - name: ", steps)[1]
                self.assertTrue(first.startswith("Require this deployment target to be enabled\n"))
                self.assertIn("DEPLOY_TARGETS: ${{ vars.DEPLOY_TARGETS }}", first)
                target = re.search(r"(?m)^          TARGET: ([a-z]+)$", first)
                self.assertIsNotNone(target)
                script = first.split("        run: |\n", 1)[1]
                script = "\n".join(line[10:] for line in script.splitlines() if line.startswith("          "))
                yield f"{workflow.name}:{index}", target.group(1), script

    def check(self, targets, enabled, uppercase=False, target_override=None):
        for name, target, script in self.gates():
            target = target_override or target
            with self.subTest(gate=name, targets=targets):
                value = targets.replace("TARGET", target)
                if uppercase:
                    value = value.upper()
                result = subprocess.run(["bash", "-euo", "pipefail", "-c", script],
                                        env={**os.environ, "TARGET": target, "DEPLOY_TARGETS": value},
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0 if enabled else 1, result.stdout + result.stderr)
                if not enabled:
                    self.assertIn(f"Deployment target '{target}' is not enabled", result.stdout)
                    self.assertIn("DEPLOY_TARGETS repository variable", result.stdout)

    def test_exact_target(self):
        self.check("TARGET", True)

    def test_comma_list(self):
        self.check("another,TARGET,other", True)

    def test_ascii_spaces(self):
        self.check(" another , TARGET , other ", True)

    def test_empty(self):
        self.check("", False)

    def test_suffix(self):
        self.check("TARGETx", False)

    def test_prefix(self):
        self.check("xTARGET", False)

    def test_unrelated(self):
        self.check("another,other", False)

    def test_case_sensitive(self):
        self.check("TARGET", False, uppercase=True)

    def test_single_node_target_uses_exact_matches(self):
        for value, enabled in (("localcluster", False), ("localsinglenode,cloud", True),
                               ("localsinglenodex", False), ("", False),
                               (" localcluster , localsinglenode ", True)):
            self.check(value, enabled, target_override="localsinglenode")


class CiRunnerProfileTests(unittest.TestCase):
    def profiles(self):
        count = 0
        for name in ("ci.yml", "auto-merge-dependabot.yml"):
            text = (ROOT / ".github/workflows" / name).read_text()
            self.assertEqual(text.count("runs-on:"), text.count("vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books'"))
            for match in re.finditer(r"(?ms)^      - name: Verify CI runner\n.*?(?=^      - name: |\Z)", text):
                count += 1
                body = match.group(0)
                self.assertIn("CI_RUNNER_HOST: ${{ vars.CI_RUNNER_HOST }}", body)
                self.assertIn('${CI_RUNNER_HOST:?Set the CI_RUNNER_HOST repository variable', body)
                self.assertIn('test "$(hostname)" = "$CI_RUNNER_HOST"', body)
                script = body.split("        run: |\n", 1)[1]
                yield name, "\n".join(line[10:] for line in script.splitlines() if line.startswith("          "))
        self.assertEqual(count, 4)

    def check_host(self, expected, actual, succeeds):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in (("hostname", '#!/bin/sh\nprintf "%s\\n" "$FIXTURE_HOST"\n'),
                                  ("docker", '#!/bin/sh\nprintf "%s\\n" linux\n')):
                stub = root / name
                stub.write_text(content)
                stub.chmod(0o755)
            for name, script in self.profiles():
                with self.subTest(workflow=name, expected=expected, actual=actual):
                    result = subprocess.run(["bash", "-euo", "pipefail", "-c", script],
                                            env={**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"],
                                                 "CI_RUNNER_HOST": expected, "FIXTURE_HOST": actual,
                                                 "RUNNER_OS": "Linux", "GITHUB_WORKSPACE": directory},
                                            capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)

    def test_configured_host(self):
        self.check_host("runner-a", "runner-a", True)

    def test_fork_host(self):
        self.check_host("runner-b", "runner-b", True)

    def test_wrong_host(self):
        self.check_host("runner-b", "runner-a", False)

    def test_empty_host(self):
        self.check_host("", "runner-b", False)


if __name__ == "__main__":
    unittest.main()
