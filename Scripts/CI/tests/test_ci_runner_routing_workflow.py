from __future__ import annotations

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]


def read_workflow(name: str) -> dict:
    return yaml.load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"),
                     Loader=yaml.BaseLoader)


CI = read_workflow("ci.yml")
SELECTOR = read_workflow("select-ci-runner.yml")
AUTOMERGE = read_workflow("auto-merge-dependabot.yml")


class CiRunnerRoutingWorkflowTests(unittest.TestCase):
    def test_validation_selection_and_fork_guard_precede_dynamic_worker_allocation(self):
        jobs = CI["jobs"]
        selected = jobs["select-validation"]
        self.assertEqual("./.github/workflows/select-ci-runner.yml", selected["uses"])
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", selected["if"])
        self.assertEqual("validation", selected["with"]["stage"])
        self.assertIn("inputs.pool || 'auto'", selected["with"]["pool"])
        self.assertIn("CI_RUNNER_ROUTING_ENABLED", selected["with"]["routing_enabled"])
        self.assertEqual("${{ secrets.CI_RUNNER_PROFILES_JSON }}",
                         selected["secrets"]["CI_RUNNER_PROFILES_JSON"])
        self.assertEqual("${{ secrets.CI_RUNNER_INVENTORY_APP_PRIVATE_KEY }}",
                         selected["secrets"]["CI_RUNNER_INVENTORY_APP_PRIVATE_KEY"])
        self.assertEqual("${{ github.repository_owner }}", selected["with"]["repository_owner"])
        self.assertEqual("${{ github.event.repository.name }}", selected["with"]["repository_name"])

        validate = jobs["validate"]
        self.assertEqual("select-validation", validate["needs"])
        self.assertIn("needs.select-validation.result == 'success'", validate["if"])
        self.assertEqual("${{ needs.select-validation.outputs.runner_label }}", validate["runs-on"][-1])
        steps = {step.get("name"): step for step in validate["steps"]}
        profile_check = steps["Verify selected CI runner profile"]
        self.assertIn("routing_enabled == 'true'", profile_check["if"])
        self.assertEqual("${{ needs.select-validation.outputs.runner_id }}",
                         profile_check["env"]["CI_RUNNER_ID"])
        self.assertIn("--config-json-env CI_RUNNER_PROFILES_JSON", profile_check["run"])
        legacy_check = steps["Verify legacy CI runner"]
        self.assertIn("routing_enabled != 'true'", legacy_check["if"])

    def test_normal_routing_requires_explicit_repository_opt_in(self):
        jobs = CI["jobs"]
        self.assertEqual(
            "${{ vars.CI_RUNNER_ROUTING_ENABLED == 'true' || (github.event_name == 'workflow_dispatch' && inputs.pool != 'auto') }}",
            jobs["select-validation"]["with"]["routing_enabled"],
        )
        self.assertEqual(
            "${{ vars.CI_RUNNER_ROUTING_ENABLED == 'true' }}",
            jobs["select-publication"]["with"]["routing_enabled"],
        )

    def test_publication_takes_a_new_main_only_selection_and_uses_only_that_output(self):
        jobs = CI["jobs"]
        selection = jobs["select-publication"]
        self.assertEqual("validate", selection["needs"])
        self.assertIn("refs/heads/main", selection["if"])
        self.assertIn("needs.validate.result == 'success'", selection["if"])
        self.assertEqual("publication", selection["with"]["stage"])
        self.assertEqual("auto", selection["with"]["pool"])

        publisher = jobs["publish-main"]
        self.assertEqual({"validate", "select-publication"}, set(publisher["needs"]))
        self.assertIn("needs.select-publication.result == 'success'", publisher["if"])
        self.assertEqual("${{ needs.select-publication.outputs.runner_label }}", publisher["runs-on"][-1])
        self.assertEqual(
            {"actions": "read", "contents": "read", "packages": "write"},
            publisher["permissions"],
        )
        for job_id, job in jobs.items():
            if job_id != "publish-main":
                self.assertNotEqual("write", job.get("permissions", {}).get("packages"), job_id)
        self.assertIn("PUBLICATION_SELECTION_RESULT", publisher["steps"][0]["env"])
        self.assertEqual("${{ needs.select-publication.outputs.runner_id }}",
                         {step.get("name"): step for step in publisher["steps"]}
                         ["Verify selected CI runner profile"]["env"]["CI_RUNNER_ID"])

    def test_desktop_routes_verify_actual_profile_roots_and_skip_native_opt_reserve(self):
        for job_id, selection in (
            ("validate", "select-validation"),
            ("publish-main", "select-publication"),
        ):
            steps = {step.get("name"): step for step in CI["jobs"][job_id]["steps"]}
            self.assertEqual(
                f"${{{{ needs.{selection}.outputs.pool != 'desktop' }}}}",
                steps["Check self-hosted runner disk"]["if"],
            )
            self.assertIn("routing_enabled == 'true'", steps["Verify selected CI runner profile"]["if"])
            self.assertIn("verify_ci_runner.py", steps["Verify selected CI runner profile"]["run"])
        verifier = (ROOT / "Scripts" / "CI" / "verify_ci_runner.py").read_text(encoding="utf-8")
        self.assertIn("inspect_capacity(profile)", verifier)

    def test_stable_always_gate_fails_for_skipped_selection_validation_or_publication(self):
        gate = CI["jobs"]["ci-result-gate"]
        self.assertIn("build-test-push", gate["name"])
        self.assertEqual({"select-validation", "validate", "select-publication", "publish-main"},
                         set(gate["needs"]))
        self.assertIn("always()", gate["if"])
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", gate["if"])
        self.assertEqual(
            "${{ vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}",
            gate["runs-on"][-1],
        )
        self.assertEqual("actions/checkout@v7", gate["steps"][0]["uses"])
        check = next(step for step in gate["steps"] if step.get("name") == "Verify every event-required CI result")
        self.assertEqual("python3 Scripts/CI/require_ci_results.py", check["run"])
        self.assertEqual("${{ needs.select-validation.result }}",
                         check["env"]["CI_VALIDATION_SELECTION_RESULT"])
        self.assertEqual("${{ needs.publish-main.result }}", check["env"]["CI_PUBLICATION_RESULT"])

    def test_reusable_selector_is_native_only_and_inventory_token_is_minimal(self):
        job = SELECTOR["jobs"]["select"]
        self.assertEqual(
            "${{ vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}",
            job["runs-on"][-1],
        )
        self.assertEqual("read", job["permissions"]["contents"])
        steps = {step.get("name"): step for step in job["steps"]}
        token = steps["Create repository-scoped runner-inventory token"]
        self.assertEqual(
            "actions/create-github-app-token@64ab729a6294000f5aa4a4bc0b73d1f32bc45510", token["uses"],
        )
        self.assertEqual("true", token["continue-on-error"])
        self.assertEqual("${{ inputs.repository_owner }}", token["with"]["owner"])
        self.assertEqual("${{ inputs.repository_name }}", token["with"]["repositories"])
        self.assertIn("repository_owner", SELECTOR["on"]["workflow_call"]["inputs"])
        self.assertIn("repository_name", SELECTOR["on"]["workflow_call"]["inputs"])
        self.assertEqual("read", token["with"]["permission-administration"])
        route = steps["Select from the fresh repository inventory"]
        self.assertIn("CI_RUNNER_INVENTORY_TOKEN", route["env"])
        self.assertNotIn("token", " ".join(job["outputs"].keys()).lower())
        legacy = steps["Keep the existing native route until cutover"]
        self.assertIn("CI_RUNNER_LABEL", legacy["run"])
        self.assertIn("[A-Za-z0-9_.-]*", legacy["run"])

    def test_canary_input_is_explicit_and_cannot_enable_non_main_publication(self):
        pool = CI["on"]["workflow_dispatch"]["inputs"]["pool"]
        self.assertEqual("choice", pool["type"])
        self.assertEqual("auto", pool["default"])
        self.assertEqual({"auto", "desktop-canary", "native-canary"}, set(pool["options"]))
        self.assertIn("refs/heads/main", CI["jobs"]["publish-main"]["if"])
        self.assertEqual(
            "${{ vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}",
            CI["jobs"]["notify-dependabot-automerge"]["runs-on"][-1],
        )
        self.assertEqual(
            "${{ vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}",
            AUTOMERGE["jobs"]["auto-merge"]["runs-on"][-1],
        )
        self.assertEqual({"write"}, set(AUTOMERGE["permissions"].values()))


if __name__ == "__main__":
    unittest.main()
