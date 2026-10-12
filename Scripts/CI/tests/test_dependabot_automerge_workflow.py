from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github" / "workflows"
AUTOMERGE_WORKFLOW = (WORKFLOW_ROOT / "auto-merge-dependabot.yml").read_text(encoding="utf-8")
CI_WORKFLOW = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")


class DependabotAutoMergeWorkflowTests(unittest.TestCase):
    def test_merge_requires_successful_dependabot_pull_request_ci(self) -> None:
        self.assertIn('workflows: ["CI"]', AUTOMERGE_WORKFLOW)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", AUTOMERGE_WORKFLOW)
        self.assertIn("github.event.workflow_run.event == 'pull_request'", AUTOMERGE_WORKFLOW)
        self.assertIn("startsWith(github.event.workflow_run.head_branch, 'dependabot/')", AUTOMERGE_WORKFLOW)
        self.assertIn('gh pr merge "$pr" --merge --auto', AUTOMERGE_WORKFLOW)
        self.assertIn('--match-head-commit "$SOURCE_SHA"', AUTOMERGE_WORKFLOW)

    def test_behind_branch_needs_no_workflow_permission_and_main_ci_runs_after_merge(self) -> None:
        self.assertNotIn("/update-branch", AUTOMERGE_WORKFLOW)
        self.assertNotIn('gh workflow run ci.yml --ref "$head_branch"', AUTOMERGE_WORKFLOW)
        self.assertIn("CLEAN|BEHIND|BLOCKED|HAS_HOOKS|UNSTABLE)", AUTOMERGE_WORKFLOW)
        self.assertIn('gh workflow run ci.yml --repo "$GH_REPO" --ref main', AUTOMERGE_WORKFLOW)
        self.assertIn("MAIN_CI_TOKEN: ${{ github.token }}", AUTOMERGE_WORKFLOW)
        self.assertIn('GH_TOKEN="$MAIN_CI_TOKEN" gh workflow run ci.yml', AUTOMERGE_WORKFLOW)
        self.assertIn('"$pull_state" == \'closed\' && "$pull_merged" == \'true\'', AUTOMERGE_WORKFLOW)
        self.assertIn("--match-head-commit \"$SOURCE_SHA\"", AUTOMERGE_WORKFLOW)
        self.assertIn("gh run list --workflow ci.yml --branch main", AUTOMERGE_WORKFLOW)
        self.assertIn("no CD workflow was dispatched", AUTOMERGE_WORKFLOW)

    def test_dependabot_merge_dispatches_ci_only_and_never_cd(self) -> None:
        self.assertNotRegex(AUTOMERGE_WORKFLOW, r"gh workflow run (?:cd-|.*deploy)")
        publish_gate = re.search(r"(?m)^    if: (.+)$", CI_WORKFLOW.split("  publish-main:\n", 1)[1])
        self.assertIsNotNone(publish_gate)
        self.assertIn("github.event_name != 'pull_request'", publish_gate.group(1))
        self.assertIn("github.ref == 'refs/heads/main'", publish_gate.group(1))


if __name__ == "__main__":
    unittest.main()
