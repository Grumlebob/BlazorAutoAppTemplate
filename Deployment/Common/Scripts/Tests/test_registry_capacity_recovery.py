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

    def test_exact_reservation_lock_timeout_is_bound_to_owner_and_gate_window(self):
        current_sha = "b" * 40
        current_run = {**self.run, "id": 456, "run_attempt": 1, "head_sha": current_sha,
                       "created_at": "2026-10-19T13:00:00Z"}
        jobs = deepcopy(self.jobs)
        for job in jobs:
            job.update(run_id=456, run_attempt=1, head_sha=current_sha)
        gate = jobs[1]["steps"][0]
        gate.update(started_at="2026-10-19T13:00:00Z", completed_at="2026-10-19T13:00:02Z")
        log = (
            "2026-10-19T13:00:00.1234567Z " + module.LOCK_TIMEOUT + "\n"
            "2026-10-19T13:00:01.1234567Z lock owner: node-demo:pid=372862:repo=example/repo:"
            "run=789-1:started=2026-10-19T12:00:00Z\n"
        )
        result = module.verify_lock_blocked_failure(
            current_run, jobs, log, repository=self.repository, sha=current_sha, run_id=456, attempt=1,
            reservation_run_id=789, reservation_attempt=1,
        )
        self.assertEqual(result["outcome"], "reservation_lock_blocked")
        self.assertEqual(result["lock_owner"], {"host": "node-demo", "pid": 372862,
                                                 "run_id": 789, "run_attempt": 1})

        bad_logs = (
            log.replace("run=789-1", "run=790-1"),
            log.replace(module.LOCK_TIMEOUT, "timed out waiting for another lock"),
            log + log,
            log.replace("13:00:01.1234567", "12:59:59.1234567"),
        )
        for bad_log in bad_logs:
            with self.subTest(log=bad_log), self.assertRaises(ValueError):
                module.verify_lock_blocked_failure(
                    current_run, jobs, bad_log, repository=self.repository, sha=current_sha,
                    run_id=456, attempt=1, reservation_run_id=789, reservation_attempt=1,
                )
        bad_jobs = deepcopy(jobs)
        bad_jobs[1]["steps"][1]["conclusion"] = "success"
        with self.assertRaises(ValueError):
            module.verify_lock_blocked_failure(
                current_run, bad_jobs, log, repository=self.repository, sha=current_sha, run_id=456, attempt=1,
                reservation_run_id=789, reservation_attempt=1,
            )

    def test_lock_blocked_recovery_pairs_prior_capacity_proof_and_exact_reservation(self):
        blocked_sha = "b" * 40
        current_sha = "c" * 40
        current_run = {**self.run, "id": 456, "run_attempt": 1, "head_sha": blocked_sha,
                       "created_at": "2026-10-19T13:00:00Z"}
        current_jobs = deepcopy(self.jobs)
        for job in current_jobs:
            job.update(run_id=456, run_attempt=1, head_sha=blocked_sha)
        gate = current_jobs[1]["steps"][0]
        gate.update(started_at="2026-10-19T13:00:00Z", completed_at="2026-10-19T13:00:02Z")
        current_log = (
            "2026-10-19T13:00:00.1234567Z " + module.LOCK_TIMEOUT + "\n"
            "2026-10-19T13:00:01.1234567Z lock owner: node-demo:pid=372862:repo=example/repo:"
            "run=789-1:started=2026-10-19T12:00:00Z\n"
        )
        prior_run = {**self.run, "updated_at": "2026-10-19T11:00:02Z"}
        reservation_run = {
            "id": 789, "run_attempt": 1, "head_sha": self.sha, "event": "workflow_dispatch",
            "head_branch": "main", "path": ".github/workflows/registry-retention.yml",
            "status": "completed", "conclusion": "failure", "created_at": "2026-10-19T11:00:03Z",
            "repository": {"full_name": self.repository}, "head_repository": {"full_name": self.repository},
        }
        with patch.object(module, "verify_capacity_source_continuity") as continuity:
            result = module.verify_lock_blocked_recovery(
                current_run, current_jobs, current_log, prior_run, self.jobs, self.log, reservation_run,
                repository=self.repository, current_sha=current_sha, current_run_id=456, current_attempt=1,
                prior_run_id=123, prior_attempt=2, reservation_run_id=789, reservation_attempt=1,
            )
            self.assertEqual([entry.args for entry in continuity.call_args_list],
                             [(self.sha, blocked_sha), (blocked_sha, current_sha)])
        self.assertEqual(result["outcome"], "capacity_cleanup_only")
        self.assertEqual(result["capacity_proof_run_id"], 123)
        self.assertEqual(result["ci_run_id"], 456)
        self.assertEqual(result["reservation_run_id"], 789)
        self.assertFalse(result["release_authorized"])

        with patch.object(module, "verify_capacity_source_continuity"):
            with self.assertRaises(ValueError):
                module.verify_lock_blocked_recovery(
                    current_run, current_jobs, current_log, prior_run, self.jobs, self.log,
                    {**reservation_run, "head_sha": "c" * 40},
                    repository=self.repository, current_sha=current_sha, current_run_id=456, current_attempt=1,
                    prior_run_id=123, prior_attempt=2, reservation_run_id=789, reservation_attempt=1,
                )

    def test_reservation_run_matches_github_api_path_without_ref_suffix(self):
        run = {
            "id": 789, "run_attempt": 1, "head_sha": self.sha, "event": "workflow_dispatch",
            "head_branch": "main", "path": ".github/workflows/registry-retention.yml",
            "status": "completed", "conclusion": "failure",
            "repository": {"full_name": self.repository}, "head_repository": {"full_name": self.repository},
        }
        module.verify_reservation_run(
            run, repository=self.repository, prior_sha=self.sha, run_id=789, attempt=1,
        )
        for path in (".github/workflows/registry-retention.yml@refs/heads/main",
                     ".github/workflows/other.yml"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "exact failed trusted workflow run"):
                module.verify_reservation_run(
                    {**run, "path": path}, repository=self.repository, prior_sha=self.sha, run_id=789, attempt=1,
                )

    def test_capacity_source_continuity_requires_the_same_gate_and_policy(self):
        old_ci = ("jobs:\n  build-test-push:\n    steps:\n      - name: " + module.CAPACITY_STEP
                  + "\n        run: python3 registry-retention.py --admission-kind final\n      - name: Next\n")
        old_wrapper = (
            "from registry_retention import ACTIVE\n\n"
            "def run(args):\n    require_publication_capacity(plan, **admission)\n"
        )
        old_files = {
            "old": {
                ".github/workflows/ci.yml": old_ci,
                "Deployment/Common/Scripts/registry-retention.py": old_wrapper,
                **{path: "same policy\n" for path in module.CAPACITY_SOURCE_FILES},
            },
            "new": {
                ".github/workflows/ci.yml": old_ci.replace("jobs:\n", "name: CI\njobs:\n"),
                "Deployment/Common/Scripts/registry-retention.py": old_wrapper.replace("ACTIVE", "ACTIVE, TERMINAL"),
                **{path: "same policy\n" for path in module.CAPACITY_SOURCE_FILES},
            },
        }

        def show(sha, path):
            return old_files["old" if sha == self.sha else "new"][path]

        with patch.object(module, "_git_show", side_effect=show), \
                patch.object(module.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()):
            module.verify_capacity_source_continuity(self.sha, "b" * 40)

        changed = deepcopy(old_files)
        changed["new"][".github/workflows/ci.yml"] = old_ci.replace("registry-retention.py", "other.py")

        def show_changed(sha, path):
            return changed["old" if sha == self.sha else "new"][path]

        with patch.object(module, "_git_show", side_effect=show_changed), \
                patch.object(module.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()), \
                self.assertRaises(ValueError):
            module.verify_capacity_source_continuity(self.sha, "b" * 40)

        changed["new"][".github/workflows/ci.yml"] = old_ci
        changed["new"]["Deployment/Common/Scripts/registry-retention.py"] = (
            "def run(args):\n    require_other_policy(plan, **admission)\n"
        )
        with patch.object(module, "_git_show", side_effect=show_changed), \
                patch.object(module.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()), \
                self.assertRaises(ValueError):
            module.verify_capacity_source_continuity(self.sha, "b" * 40)

        changed["new"]["Deployment/Common/Scripts/registry-retention.py"] = old_wrapper
        changed["new"][module.CAPACITY_SOURCE_FILES[0]] = "changed policy\n"
        with patch.object(module, "_git_show", side_effect=show_changed), \
                patch.object(module.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()), \
                self.assertRaises(ValueError):
            module.verify_capacity_source_continuity(self.sha, "b" * 40)

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

    def test_full_lock_blocked_proof_rechecks_all_three_runs_and_current_main(self):
        blocked_sha = "b" * 40
        current_sha = "c" * 40
        current_run = {**self.run, "id": 456, "run_attempt": 1, "head_sha": blocked_sha,
                       "created_at": "2026-10-19T13:00:00Z"}
        current_jobs = deepcopy(self.jobs)
        for job in current_jobs:
            job.update(run_id=456, run_attempt=1, head_sha=blocked_sha)
        current_jobs[1]["steps"][0].update(started_at="2026-10-19T13:00:00Z",
                                           completed_at="2026-10-19T13:00:02Z")
        current_log = (
            "2026-10-19T13:00:00.1234567Z " + module.LOCK_TIMEOUT + "\n"
            "2026-10-19T13:00:01.1234567Z lock owner: node-demo:pid=372862:repo=example/repo:"
            "run=789-1:started=2026-10-19T12:00:00Z\n"
        )
        prior_run = {**self.run, "updated_at": "2026-10-19T11:00:02Z"}
        reservation_run = {
            "id": 789, "run_attempt": 1, "head_sha": self.sha, "event": "workflow_dispatch",
            "head_branch": "main", "path": ".github/workflows/registry-retention.yml",
            "status": "completed", "conclusion": "failure", "created_at": "2026-10-19T11:00:03Z",
            "repository": {"full_name": self.repository}, "head_repository": {"full_name": self.repository},
        }
        environment = dict(
            GITHUB_SHA=current_sha, GITHUB_REPOSITORY=self.repository, GITHUB_TOKEN="fixture-token",
            GITHUB_REF="refs/heads/main", GITHUB_EVENT_NAME="workflow_dispatch",
            GITHUB_WORKFLOW_REF=self.repository + "/.github/workflows/registry-retention.yml@refs/heads/main",
            REGISTRY_RETENTION_APPLY="true",
        )
        paths = [
            "/repos/example/repo/actions/runs/456", "/repos/example/repo/actions/runs/123",
            "/repos/example/repo/actions/runs/789", "/repos/example/repo/actions/runs/456",
            "/repos/example/repo/commits/main", "/repos/example/repo/actions/runs/123",
            "/repos/example/repo/actions/runs/789",
        ]
        responses = [current_run, prior_run, reservation_run, current_run, {"sha": current_sha},
                     prior_run, reservation_run]
        with patch.dict(os.environ, environment, clear=True), \
                patch("sys.argv", [str(SCRIPT), "--run-id", "456", "--attempt", "1",
                                    "--prior-capacity-run-id", "123", "--prior-capacity-attempt", "2",
                                    "--reservation-run-id", "789", "--reservation-attempt", "1"]), \
                patch.object(module.subprocess, "check_output", side_effect=[current_sha, "false"]), \
                patch.object(module, "attempt_jobs", side_effect=[current_jobs, self.jobs]), \
                patch.object(module, "download_job_logs", side_effect=[current_log, self.log]), \
                patch.object(module, "verify_capacity_source_continuity"), \
                patch.object(module.finder, "github_get", side_effect=responses) as api:
            with patch("builtins.print") as output:
                self.assertEqual(module.main(), 0)
            self.assertEqual(len(api.call_args_list), len(paths))
            self.assertEqual([call.args[0] for call in api.call_args_list], paths)
            result = json.loads(output.call_args.args[0])
            self.assertEqual(result["capacity_proof_run_id"], 123)
            self.assertEqual(result["ci_run_id"], 456)
            self.assertEqual(result["reservation_run_id"], 789)
            self.assertTrue(result["apply_requested"])

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
        self.assertEqual(step["env"]["PRIOR_CAPACITY_CI_RUN_ID"], "${{ inputs.prior_capacity_ci_run_id }}")
        self.assertEqual(step["env"]["PRIOR_CAPACITY_CI_ATTEMPT"], "${{ inputs.prior_capacity_ci_attempt }}")
        self.assertIn("inputs.apply_registry == true", step["env"]["REGISTRY_RETENTION_APPLY"])
        for run_id, attempt, expected in (("", "", "normal"), ("123", "2", "recovery"),
                                          ("123", "", None), ("x", "2", None), ("123", "0", None)):
            with self.subTest(run_id=run_id, attempt=attempt), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                scripts = root / "Deployment/Common/Scripts"
                scripts.mkdir(parents=True)
                for filename, result in (("verify-operation-source.py", "normal"),
                                         ("verify-registry-capacity-recovery.py", "recovery")):
                    (scripts / filename).write_text(
                        "from pathlib import Path\nimport json\nimport sys\nPath('called').write_text(" + repr(result) + ")\n"
                        "Path('args').write_text(json.dumps(sys.argv[1:]))\n"
                    )
                environment = dict(os.environ, CAPACITY_RECOVERY_CI_RUN_ID=run_id, CAPACITY_RECOVERY_CI_ATTEMPT=attempt)
                environment.update(RESERVATION_RUN_ID="", RESERVATION_ATTEMPT="", PRIOR_CAPACITY_CI_RUN_ID="",
                                   PRIOR_CAPACITY_CI_ATTEMPT="")
                completed = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step["run"]],
                                           cwd=root, env=environment, capture_output=True, text=True)
                if expected is None:
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse((root / "called").exists())
                else:
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual((root / "called").read_text(), expected)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "Deployment/Common/Scripts"
            scripts.mkdir(parents=True)
            (scripts / "verify-registry-capacity-recovery.py").write_text(
                "from pathlib import Path\nimport json\nimport sys\nPath('args').write_text(json.dumps(sys.argv[1:]))\n"
            )
            environment = dict(
                os.environ, CAPACITY_RECOVERY_CI_RUN_ID="456", CAPACITY_RECOVERY_CI_ATTEMPT="1",
                PRIOR_CAPACITY_CI_RUN_ID="123", PRIOR_CAPACITY_CI_ATTEMPT="2",
                RESERVATION_RUN_ID="789", RESERVATION_ATTEMPT="3", REGISTRY_RETENTION_APPLY="true",
            )
            completed = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step["run"]],
                                       cwd=root, env=environment, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            arguments = json.loads((root / "args").read_text())
            self.assertEqual(arguments, [
                "--run-id", "456", "--attempt", "1", "--prior-capacity-run-id", "123",
                "--prior-capacity-attempt", "2", "--reservation-run-id", "789", "--reservation-attempt", "3",
            ])

    def test_workflow_recovery_binds_exact_reservation_and_refuses_unpaired_effect_inputs(self):
        import subprocess
        import yaml

        workflow = yaml.safe_load((SCRIPT.parents[3] / ".github/workflows/registry-retention.yml").read_text())
        trigger = workflow.get("on", workflow.get(True))
        inputs = trigger["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["prior_capacity_ci_run_id"]["type"], "string")
        self.assertEqual(inputs["prior_capacity_ci_attempt"]["type"], "string")
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

        for job_name in ("localcluster_protection", "localsinglenode_primary", "localsinglenode_additional"):
            gate = jobs[job_name]["steps"][0]
            self.assertEqual(gate["env"]["PRIOR_CAPACITY_CI_RUN_ID"], "${{ inputs.prior_capacity_ci_run_id }}")
            self.assertEqual(gate["env"]["PRIOR_CAPACITY_CI_ATTEMPT"], "${{ inputs.prior_capacity_ci_attempt }}")

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
                    CAPACITY_RECOVERY_CI_RUN_ID="", CAPACITY_RECOVERY_CI_ATTEMPT="",
                    PRIOR_CAPACITY_CI_RUN_ID="", PRIOR_CAPACITY_CI_ATTEMPT="")
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
        incomplete_prior_proof = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", gate],
            env=dict(base, REGISTRY_RETENTION_APPLY="true", RESERVATION_RUN_ID="77",
                     RESERVATION_ATTEMPT="1", CAPACITY_RECOVERY_CI_RUN_ID="66",
                     CAPACITY_RECOVERY_CI_ATTEMPT="2", PRIOR_CAPACITY_CI_RUN_ID="55"),
            capture_output=True, text=True,
        )
        self.assertNotEqual(incomplete_prior_proof.returncode, 0)
        exact_prior_proof = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", gate],
            env=dict(base, REGISTRY_RETENTION_APPLY="true", RESERVATION_RUN_ID="77",
                     RESERVATION_ATTEMPT="1", CAPACITY_RECOVERY_CI_RUN_ID="66",
                     CAPACITY_RECOVERY_CI_ATTEMPT="2", PRIOR_CAPACITY_CI_RUN_ID="55",
                     PRIOR_CAPACITY_CI_ATTEMPT="1"), capture_output=True, text=True,
        )
        self.assertEqual(exact_prior_proof.returncode, 0, exact_prior_proof.stderr)


if __name__ == "__main__":
    unittest.main()
