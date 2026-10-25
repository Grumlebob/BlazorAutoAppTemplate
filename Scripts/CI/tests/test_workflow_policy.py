from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "workflow_policy.py"
STORE = Path(__file__).resolve().parents[1] / "ci_report_store.py"
SPEC = importlib.util.spec_from_file_location("workflow_policy", SCRIPT)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = policy
SPEC.loader.exec_module(policy)


class WorkflowPolicyTests(unittest.TestCase):
    def _audit(self, workflows: dict[str, str], store_source: str | None = None):
        with tempfile.TemporaryDirectory(prefix="workflow-policy-") as temporary:
            root = Path(temporary)
            for relative, source in workflows.items():
                path = root / ".github" / "workflows" / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
            store_path = root / "Scripts" / "CI" / "ci_report_store.py"
            store_path.parent.mkdir(parents=True, exist_ok=True)
            store_path.write_text(store_source or STORE.read_text(encoding="utf-8"), encoding="utf-8")
            return policy.audit_repository(root)

    def test_rejects_external_reusable_workflow(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  call:
    uses: external/repo/.github/workflows/reusable.yml@main
"""})

        self.assertTrue(any("external reusable workflow is not inspectable" in str(item) for item in findings))

    def test_detects_composite_upload_reached_through_local_workflow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-policy-") as temporary:
            root = Path(temporary)
            workflows = {
                "main.yml": """name: main
jobs:
  call:
    uses: ./.github/workflows/reusable.yml
""",
                "reusable.yml": """name: reusable
jobs:
  publish:
    runs-on: [self-hosted, linux]
    steps:
      - uses: ./.github/actions/nested-publish
""",
            }
            for relative, source in workflows.items():
                path = root / ".github" / "workflows" / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
            action = root / ".github" / "actions" / "nested-publish" / "action.yml"
            action.parent.mkdir(parents=True)
            action.write_text("""name: nested publish
runs:
  using: composite
  steps:
    - uses: actions/upload-artifact@v4
""", encoding="utf-8")
            store_path = root / "Scripts" / "CI" / "ci_report_store.py"
            store_path.parent.mkdir(parents=True)
            store_path.write_text(STORE.read_text(encoding="utf-8"), encoding="utf-8")

            findings = policy.audit_repository(root)

        self.assertTrue(any("routine cloud artifact upload is forbidden" in str(item) for item in findings))
        self.assertTrue(any(".github/actions/nested-publish/action.yml" in str(item) for item in findings))

    def test_detects_direct_upload_and_allows_legacy_download_reader(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps:
      - run: gh run download 123
      - uses: actions/upload-artifact/merge@v4
"""})

        self.assertTrue(any("routine cloud artifact upload is forbidden" in str(item) for item in findings))
        self.assertFalse(any("download" in str(item).lower() for item in findings))

    def test_generic_report_store_workflow_must_pass_repository(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps:
      - run: python3 Scripts/CI/ci_report_store.py save --run-id 123 --attempt 1
"""})

        self.assertTrue(any("must pass --repository explicitly" in str(item) for item in findings))

    def test_rejects_each_supported_cloud_cache_path(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps:
      - uses: actions/cache@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: 10.0.x
          cache: true
      - uses: docker/build-push-action@v6
        with:
          cache-to: type=gha
      - run: docker buildx build --cache-to type=gha .
"""})
        messages = [str(item) for item in findings]

        self.assertTrue(any("GitHub Actions cache action is forbidden" in message for message in messages))
        self.assertTrue(any("implicit dependency cache is forbidden for actions/setup-node" in message for message in messages))
        self.assertTrue(any("implicit dependency cache is forbidden for actions/setup-dotnet" in message for message in messages))
        self.assertTrue(any("Docker build cache must not use type=gha" in message for message in messages))
        self.assertTrue(any("workflow shell step uses GitHub Actions cache backend type=gha" in message for message in messages))

    def test_detects_implicit_cache_and_invalid_hosted_runner(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: ubuntu-24.04-4xlarge
    steps:
      - uses: actions/setup-go@v5
        with:
          go-version: '1.24'
"""})

        messages = [str(item) for item in findings]
        self.assertTrue(any("must target self-hosted runners" in message for message in messages))
        self.assertTrue(any("hosted runner labels are forbidden" in message for message in messages))
        self.assertTrue(any("setup-go Actions cache must be disabled" in message for message in messages))

    def test_allows_only_public_hosted_codeql_exception(self) -> None:
        valid = self._audit({"codeql.yml": """name: CodeQL
jobs:
  analyze:
    if: ${{ !github.event.repository.private }}
    runs-on: ubuntu-latest
    steps:
      - run: echo scan
"""})
        invalid = self._audit({"codeql.yml": """name: CodeQL
jobs:
  analyze:
    if: ${{ always() || !github.event.repository.private }}
    runs-on: ubuntu-latest
    steps:
      - run: echo scan
"""})

        self.assertFalse(any("hosted CodeQL job" in str(item) for item in valid))
        self.assertTrue(any("hosted CodeQL job must skip private repository clones" in str(item) for item in invalid))

    def test_runner_group_name_does_not_count_as_a_self_hosted_label(self) -> None:
        for runner in ("{group: self-hosted}", "{group: self-hosted, labels: linux}"):
            with self.subTest(runner=runner):
                findings = self._audit({"ci.yml": f"""name: ci
jobs:
  validate:
    runs-on: {runner}
    steps: []
"""})
                self.assertTrue(any("must target self-hosted runners" in str(item)
                                    or "inspectable runner" in str(item) for item in findings))

    def test_runner_group_can_constrain_explicit_self_hosted_labels(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on:
      group: application-runners
      labels: [self-hosted, linux]
    steps: []
"""})
        self.assertEqual(findings, [])

    def test_setup_node_requires_automatic_package_manager_cache_to_be_disabled(self) -> None:
        for cache in (None, "true", "''", "${{ inputs.enable_cache }}"):
            with self.subTest(cache=cache):
                setting = "" if cache is None else f"          package-manager-cache: {cache}\n"
                findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps:
      - uses: actions/setup-node@v7
        with:
          node-version: 24
""" + setting})
                self.assertTrue(any("automatic npm cache" in str(item) for item in findings))

    def test_setup_node_allows_explicitly_disabled_automatic_cache(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps:
      - uses: actions/setup-node@v7
        with:
          node-version: 24
          package-manager-cache: false
"""})
        self.assertEqual(findings, [])

    def test_codeql_init_requires_explicit_overlay_cache_disablement(self) -> None:
        for mode in (None, "overlay", "overlay-base", "invalid", "${{ inputs.overlay_mode }}"):
            with self.subTest(mode=mode):
                environment = "" if mode is None else f"        env:\n          CODEQL_OVERLAY_DATABASE_MODE: {mode}\n"
                findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps:
      - uses: github/codeql-action/init@v4
""" + environment})
                self.assertTrue(any("CodeQL overlay cache" in str(item) for item in findings))

    def test_codeql_init_allows_full_scans_without_overlay_caching(self) -> None:
        findings = self._audit({"codeql.yml": """name: CodeQL
jobs:
  analyze:
    if: ${{ !github.event.repository.private }}
    runs-on: ubuntu-latest
    steps:
      - uses: github/codeql-action/init@v4
        env:
          CODEQL_OVERLAY_DATABASE_MODE: none
"""})
        self.assertEqual(findings, [])

    def test_shared_registry_queue_rejects_pending_request_replacement(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  publish-main:
    runs-on: [self-hosted, linux]
    concurrency:
      group: payload-publication
      cancel-in-progress: false
    steps: []
""", "retention.yml": """name: retention
concurrency:
  group: PAYLOAD-PUBLICATION
  cancel-in-progress: false
jobs:
  prune:
    runs-on: [self-hosted, linux]
    steps: []
"""})
        violations = [item for item in findings if "must preserve pending requests" in str(item)]
        self.assertEqual(len(violations), 2)

    def test_shared_registry_queue_allows_bounded_pending_requests(self) -> None:
        findings = self._audit({"ci.yml": """name: ci
jobs:
  publish-main:
    runs-on: [self-hosted, linux]
    concurrency:
      group: payload-publication
      queue: max
      cancel-in-progress: false
    steps: []
"""})
        self.assertEqual(findings, [])

    def test_report_store_policy_detects_missing_retention_and_repository_ownership(self) -> None:
        source = STORE.read_text(encoding="utf-8")
        source = source.replace(
            "SUCCESS_RETENTION = timedelta(days=3)",
            "DEFAULT_MAX_BYTES = 1024 * 1024 * 1024\nSUCCESS_RETENTION = timedelta(days=3)",
        )
        source = source.replace("FAILURE_RETENTION = timedelta(days=7)", "FAILURE_RETENTION = timedelta(days=30)")
        source = source.replace('"schema_version", "repository", "run_id", "attempt", "job", "status",',
                                '"schema_version", "run_id", "attempt", "job", "status",')
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps: []
"""}, source)
        messages = [str(item) for item in findings]

        self.assertTrue(any("FAILURE_RETENTION must retain reports for 7 days" in message for message in messages))
        self.assertTrue(any("local report manifest must validate repository, run, and attempt ownership" in message for message in messages))
        self.assertTrue(any("local report store must not impose a byte-size ceiling" in message for message in messages))

    def test_accepts_fixed_repository_report_store_without_cli_repository_flag(self) -> None:
        static_store = '''from datetime import timedelta
from pathlib import Path

REPOSITORY = "Example/Project"
SUCCESS_RETENTION = timedelta(days=3)
FAILURE_RETENTION = timedelta(days=7)

def _validate_identity(run_id, attempt):
    pass

def default_root():
    return Path.home() / ".local" / "state" / "reports" / "Project"

def _read_manifest(entry):
    required = {"repository", "run_id", "attempt"}
    if set(value) != required or value.get("repository") != REPOSITORY:
        return None
    _validate_identity(value["run_id"], value["attempt"])

def save_report(*, run_id, attempt):
    _validate_identity(run_id, attempt)
    return {"repository": REPOSITORY}
'''
        findings = self._audit({"ci.yml": """name: ci
jobs:
  validate:
    runs-on: [self-hosted, linux]
    steps:
      - run: python3 Scripts/CI/ci_report_store.py save --run-id "$RUN_ID" --attempt "$ATTEMPT"
"""}, static_store)

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
