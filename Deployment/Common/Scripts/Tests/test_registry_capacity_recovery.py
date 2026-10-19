from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "verify-registry-capacity-recovery.py"
SPEC = importlib.util.spec_from_file_location("registry_capacity_recovery", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class RegistryCapacityRecoveryTests(unittest.TestCase):
    sha = "a" * 40
    repository = "example/repo"

    def setUp(self):
        self.run = dict(id=123, run_attempt=2, head_sha=self.sha, event="push", head_branch="main",
                        path=".github/workflows/ci.yml", status="completed", conclusion="failure",
                        repository={"full_name": self.repository}, head_repository={"full_name": self.repository})
        gate = dict(number=1, name=module.CAPACITY_STEP, status="completed", conclusion="failure",
                    started_at="2026-10-18T12:00:00Z", completed_at="2026-10-18T12:00:01Z")
        steps = [gate] + [dict(number=index, name=name, status="completed", conclusion="skipped")
                          for index, name in enumerate(sorted(module.PUBLICATION_STEPS), 2)]
        steps.append(dict(number=50, name="Store CI reports on this runner", status="completed", conclusion="success"))
        self.jobs = [dict(id=1, run_id=123, run_attempt=2, head_sha=self.sha, name="validate",
                          status="completed", conclusion="success"),
                     dict(id=2, run_id=123, run_attempt=2, head_sha=self.sha, name="build-test-push",
                          status="completed", conclusion="failure", steps=steps)]
        self.log = ("2026-10-18T12:00:00.1234567Z Registry retention failed closed; "
                    "no unverified deletion was attempted: payload store requires coordinated retention before publication\n")

    def verify(self, run=None, jobs=None, log=None):
        return module.verify_capacity_failure(self.run if run is None else run, self.jobs if jobs is None else jobs,
                                              self.log if log is None else log, repository=self.repository,
                                              sha=self.sha, run_id=123, attempt=2)

    def test_exact_validated_capacity_failure_authorizes_only_cleanup(self):
        result = self.verify()
        self.assertEqual(result["outcome"], "capacity_cleanup_only")
        self.assertFalse(result["release_authorized"])
        self.assertEqual(result["validated_code_sha"], self.sha)

    def test_changed_run_identity_untrusted_events_and_incomplete_jobs_fail(self):
        for key, value in (("id", 124), ("run_attempt", 3), ("head_sha", "b" * 40), ("event", "pull_request"),
                           ("head_branch", "feature"), ("path", ".github/workflows/other.yml"),
                           ("status", "in_progress"), ("conclusion", "success"), ("head_repository", None)):
            run = {**self.run, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(run=run)
        for jobs in ([], self.jobs[:1], self.jobs[1:], self.jobs + [self.jobs[0]]):
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                self.verify(jobs=jobs)
        for job_index, key, value in ((0, "conclusion", "failure"), (0, "status", "queued"),
                                      (1, "run_attempt", 3), (1, "head_sha", "b" * 40)):
            jobs = deepcopy(self.jobs)
            jobs[job_index][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(jobs=jobs)

    def test_publication_other_failure_unknown_tail_or_missing_steps_fail(self):
        for change in ("publication", "wrong_failure", "unknown_tail", "missing", "duplicate", "reordered", "cancelled"):
            jobs = deepcopy(self.jobs)
            steps = jobs[1]["steps"]
            if change == "publication":
                steps[1]["conclusion"] = "success"
            elif change == "wrong_failure":
                steps[1]["conclusion"], steps[0]["conclusion"] = "failure", "success"
            elif change == "unknown_tail":
                steps[-1]["name"] = "Unreviewed mutation"
            elif change == "missing":
                del steps[1]
            elif change == "duplicate":
                steps.append(steps[-1])
            elif change == "reordered":
                steps.reverse()
            else:
                steps[1]["conclusion"] = "cancelled"
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(jobs=jobs)

    def test_log_reason_and_step_window_are_required(self):
        for log in ("", self.log * 2, self.log.replace("12:00:00.1234567", "11:59:59"),
                    self.log.replace("12:00:00.1234567", "12:00:02"),
                    self.log.replace("payload store requires coordinated retention before publication", "HTTP 403")):
            with self.subTest(log=log), self.assertRaises(ValueError):
                self.verify(log=log)

    def test_pagination_rejects_missing_total_or_partial_inventory(self):
        for payload in ({"jobs": self.jobs}, {"jobs": self.jobs, "total_count": 3}):
            with patch.object(module.finder, "github_get", return_value=payload), self.assertRaises(ValueError):
                module.attempt_jobs(self.repository, 123, 2, "fixture-token")
        with patch.object(module.finder, "github_get", return_value={"jobs": self.jobs, "total_count": 2}):
            self.assertEqual(module.attempt_jobs(self.repository, 123, 2, "fixture-token"), self.jobs)

    def test_manual_trusted_workflow_and_explicit_effect_choice_are_required(self):
        environment = dict(GITHUB_SHA=self.sha, GITHUB_REPOSITORY=self.repository, GITHUB_TOKEN="fixture-token",
                           GITHUB_REF="refs/heads/main", GITHUB_EVENT_NAME="workflow_dispatch",
                           GITHUB_WORKFLOW_REF=self.repository + "/.github/workflows/registry-retention.yml@refs/heads/main",
                           REGISTRY_RETENTION_APPLY="true")
        for key, value in (("GITHUB_REF", "refs/heads/feature"), ("GITHUB_EVENT_NAME", "schedule"),
                           ("GITHUB_WORKFLOW_REF", "other"), ("REGISTRY_RETENTION_APPLY", "invalid"),
                           ("GIT_DIR", "/untrusted"), ("GITHUB_TOKEN", "")):
            with patch.dict(os.environ, {**environment, key: value}, clear=True), \
                    patch("sys.argv", [str(SCRIPT), "--run-id", "123", "--attempt", "2"]), \
                    patch.object(module.finder, "github_get") as api, self.assertRaises(ValueError):
                module.main()
            api.assert_not_called()

    def test_full_proof_rechecks_attempt_and_current_main(self):
        environment = dict(GITHUB_SHA=self.sha, GITHUB_REPOSITORY=self.repository, GITHUB_TOKEN="fixture-token",
                           GITHUB_REF="refs/heads/main", GITHUB_EVENT_NAME="workflow_dispatch",
                           GITHUB_WORKFLOW_REF=self.repository + "/.github/workflows/registry-retention.yml@refs/heads/main",
                           REGISTRY_RETENTION_APPLY="true")
        for changed in ("none", "attempt", "main"):
            fresh = {**self.run, "run_attempt": 3} if changed == "attempt" else self.run
            head = "b" * 40 if changed == "main" else self.sha
            with patch.dict(os.environ, environment, clear=True), \
                    patch("sys.argv", [str(SCRIPT), "--run-id", "123", "--attempt", "2"]), \
                    patch.object(module.subprocess, "check_output", side_effect=[self.sha, "false"]), \
                    patch.object(module, "attempt_jobs", return_value=self.jobs), \
                    patch.object(module, "download_job_logs", return_value=self.log), \
                    patch.object(module.finder, "github_get", side_effect=[self.run, fresh, {"sha": head}]):
                if changed == "none":
                    with patch("builtins.print") as output:
                        self.assertEqual(module.main(), 0)
                    self.assertFalse(json.loads(output.call_args.args[0])["release_authorized"])
                else:
                    with self.assertRaises(ValueError):
                        module.main()

    def test_workflow_keeps_normal_gate_and_binds_manual_recovery_inputs(self):
        import subprocess
        import tempfile
        import yaml

        workflow = yaml.safe_load((SCRIPT.parents[3] / ".github/workflows/registry-retention.yml").read_text())
        steps = [step for job in workflow["jobs"].values() for step in job["steps"]
                 if "verify-registry-capacity-recovery.py" in step.get("run", "")]
        self.assertEqual(len(steps), 1)
        step = steps[0]
        self.assertEqual(step["env"]["CAPACITY_RECOVERY_CI_RUN_ID"], "${{ inputs.capacity_recovery_ci_run_id }}")
        self.assertEqual(step["env"]["CAPACITY_RECOVERY_CI_ATTEMPT"], "${{ inputs.capacity_recovery_ci_attempt }}")
        self.assertIn("inputs.apply_registry == true", step["env"]["REGISTRY_RETENTION_APPLY"])
        for run_id, attempt, expected in (("", "", "normal"), ("123", "2", "recovery"),
                                          ("123", "", None), ("x", "2", None), ("123", "0", None)):
            with self.subTest(run_id=run_id, attempt=attempt), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                scripts = root / "Deployment/Common/Scripts"
                scripts.mkdir(parents=True)
                for filename, result in (("verify-operation-source.py", "normal"),
                                         ("verify-registry-capacity-recovery.py", "recovery")):
                    (scripts / filename).write_text("from pathlib import Path\nPath('called').write_text(" + repr(result) + ")\n")
                environment = dict(os.environ, CAPACITY_RECOVERY_CI_RUN_ID=run_id, CAPACITY_RECOVERY_CI_ATTEMPT=attempt)
                environment.update(RESERVATION_RUN_ID="", RESERVATION_ATTEMPT="")
                completed = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step["run"]],
                                           cwd=root, env=environment, capture_output=True, text=True)
                if expected is None:
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse((root / "called").exists())
                else:
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual((root / "called").read_text(), expected)

    def test_workflow_recovery_binds_exact_reservation_and_refuses_unpaired_effect_inputs(self):
        import subprocess
        import yaml

        workflow = yaml.safe_load((SCRIPT.parents[3] / ".github/workflows/registry-retention.yml").read_text())
        trigger = workflow.get("on", workflow.get(True))
        inputs = trigger["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["registry_reservation_run_id"]["type"], "string")
        self.assertEqual(inputs["registry_reservation_attempt"]["type"], "string")

        jobs = workflow["jobs"]
        status_reads = [step for job_name in ("localcluster_protection", "localsinglenode_primary",
                                               "localsinglenode_additional")
                        for step in jobs[job_name]["steps"]
                        if step.get("name", "").startswith("Read ")]
        self.assertEqual(len(status_reads), 3)
        for step in status_reads:
            self.assertIn("registry-retention-recovery.py prepare", step["run"])
            self.assertIn("with-deploy-lock.sh", step["run"])
            self.assertEqual(step["env"]["RESERVATION_RUN_ID"], "${{ inputs.registry_reservation_run_id }}")

        source_step = next(step for step in jobs["prune_registry"]["steps"]
                           if "verify-registry-capacity-recovery.py" in step.get("run", ""))
        self.assertEqual(source_step["env"]["RESERVATION_RUN_ID"], "${{ inputs.registry_reservation_run_id }}")
        prune_step = next(step for step in jobs["prune_registry"]["steps"]
                          if "registry-retention.py" in step.get("run", ""))
        self.assertIn("--reservation-id", prune_step["run"])
        self.assertIn("registry-retention-recovery.py release", prune_step["run"])
        self.assertIn("retention_status=0", prune_step["run"])
        cleanup = jobs["prune_registry"]["steps"][-1]
        self.assertEqual(cleanup["if"], "always()")
        self.assertIn("registry-retention-recovery.json", cleanup["run"])

        gate = jobs["localcluster_protection"]["steps"][0]["run"]
        base = dict(os.environ, GITHUB_REF="refs/heads/main", DEPLOY_TARGETS="localcluster,localsinglenode",
                    REGISTRY_RETENTION_APPLY="false", RESERVATION_RUN_ID="", RESERVATION_ATTEMPT="",
                    CAPACITY_RECOVERY_CI_RUN_ID="", CAPACITY_RECOVERY_CI_ATTEMPT="")
        normal = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", gate], env=base,
                                capture_output=True, text=True)
        self.assertEqual(normal.returncode, 0, normal.stderr)
        missing_effect_proof = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", gate],
            env=dict(base, REGISTRY_RETENTION_APPLY="true", RESERVATION_RUN_ID="77",
                     RESERVATION_ATTEMPT="1"), capture_output=True, text=True,
        )
        self.assertNotEqual(missing_effect_proof.returncode, 0)
        exact_effect_proof = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", gate],
            env=dict(base, REGISTRY_RETENTION_APPLY="true", RESERVATION_RUN_ID="77",
                     RESERVATION_ATTEMPT="1", CAPACITY_RECOVERY_CI_RUN_ID="66",
                     CAPACITY_RECOVERY_CI_ATTEMPT="2"), capture_output=True, text=True,
        )
        self.assertEqual(exact_effect_proof.returncode, 0, exact_effect_proof.stderr)


if __name__ == "__main__":
    unittest.main()
