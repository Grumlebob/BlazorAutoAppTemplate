from __future__ import annotations

import contextlib
import io
import os
import unittest
from unittest.mock import patch

from Scripts.CI import require_ci_results as gate


def valid(*, event="pull_request", ref="refs/pull/17/merge", **changes):
    results = dict(validation_selection="success", validation="success",
                   publication_selection="skipped", publication="skipped")
    if event in {"push", "workflow_dispatch"} and ref == "refs/heads/main":
        results.update(publication_selection="success", publication="success")
    results.update(changes)
    gate.validate_required_results(event_name=event, ref=ref, **results)


class RequiredResultTests(unittest.TestCase):
    def test_pull_request_and_non_main_canary_require_validation_only(self):
        valid()
        valid(event="workflow_dispatch", ref="refs/heads/desktop-canary")

    def test_main_push_and_main_dispatch_require_fresh_publication_selection_and_publish(self):
        valid(event="push", ref="refs/heads/main")
        valid(event="workflow_dispatch", ref="refs/heads/main")

    def test_every_required_selection_or_validation_failure_fails(self):
        for field in ("validation_selection", "validation"):
            for result in ("failure", "cancelled", "skipped", "neutral"):
                with self.subTest(field=field, result=result), self.assertRaises(gate.RequiredResultError):
                    valid(**{field: result})

    def test_main_publication_selection_and_publication_must_both_succeed(self):
        for field in ("publication_selection", "publication"):
            for result in ("failure", "cancelled", "skipped", "neutral"):
                with self.subTest(field=field, result=result), self.assertRaises(gate.RequiredResultError):
                    valid(event="push", ref="refs/heads/main", **{field: result})

    def test_publication_must_stay_skipped_for_pull_requests_and_canaries(self):
        for event, ref in (("pull_request", "refs/pull/17/merge"),
                           ("workflow_dispatch", "refs/heads/desktop-canary")):
            for field in ("publication_selection", "publication"):
                with self.subTest(event=event, field=field), self.assertRaises(gate.RequiredResultError):
                    valid(event=event, ref=ref, **{field: "success"})

    def test_unexpected_event_or_ref_fails_closed(self):
        for event, ref in (("push", "refs/heads/feature"), ("pull_request", "refs/heads/main"),
                           ("workflow_run", "refs/heads/main"), ("workflow_dispatch", "")):
            with self.subTest(event=event, ref=ref), self.assertRaises(gate.RequiredResultError):
                valid(event=event, ref=ref)

    def test_cli_passes_and_fails_without_echoing_environment_values(self):
        base = dict(CI_EVENT_NAME="pull_request", CI_REF="refs/pull/17/merge",
                    CI_VALIDATION_SELECTION_RESULT="success", CI_VALIDATION_RESULT="success",
                    CI_PUBLICATION_SELECTION_RESULT="skipped", CI_PUBLICATION_RESULT="skipped")
        output, errors = io.StringIO(), io.StringIO()
        with (patch.dict(os.environ, base, clear=True), contextlib.redirect_stdout(output),
              contextlib.redirect_stderr(errors)):
            self.assertEqual(0, gate.main())
        self.assertIn("passed", output.getvalue())
        self.assertEqual("", errors.getvalue())

        output, errors = io.StringIO(), io.StringIO()
        with (patch.dict(os.environ, base | dict(CI_VALIDATION_SELECTION_RESULT="failure"), clear=True),
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
            self.assertEqual(1, gate.main())
        self.assertEqual("", output.getvalue())
        self.assertIn("Required CI result gate failed", errors.getvalue())
        self.assertNotIn("refs/pull/17/merge", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
