#!/usr/bin/env python3
"""Fail the stable required CI check unless every event-required job succeeded."""
from __future__ import annotations

import os
import re
import sys


class RequiredResultError(ValueError):
    pass


def validate_required_results(*, event_name: str, ref: str, validation_selection: str,
                              validation: str, publication_selection: str, publication: str) -> None:
    """Validate the required dependency results for a PR, main run, or canary."""
    if event_name == "pull_request":
        if not re.fullmatch(r"refs/pull/[1-9][0-9]*/merge", ref):
            raise RequiredResultError("pull request ref is invalid")
        requires_publication = False
    elif event_name == "push":
        if ref != "refs/heads/main":
            raise RequiredResultError("push result gate only accepts main")
        requires_publication = True
    elif event_name == "workflow_dispatch":
        if not re.fullmatch(r"refs/heads/[A-Za-z0-9_./-]+", ref):
            raise RequiredResultError("dispatch ref is invalid")
        requires_publication = ref == "refs/heads/main"
    else:
        raise RequiredResultError("event is outside the CI result-gate contract")

    if validation_selection != "success":
        raise RequiredResultError("validation runner selection did not succeed")
    if validation != "success":
        raise RequiredResultError("validation did not succeed")
    if requires_publication:
        if publication_selection != "success":
            raise RequiredResultError("publication runner selection did not succeed")
        if publication != "success":
            raise RequiredResultError("publication did not succeed")
    elif publication_selection != "skipped" or publication != "skipped":
        raise RequiredResultError("publication must remain skipped outside main")


def main() -> int:
    try:
        validate_required_results(
            event_name=os.environ["CI_EVENT_NAME"],
            ref=os.environ["CI_REF"],
            validation_selection=os.environ["CI_VALIDATION_SELECTION_RESULT"],
            validation=os.environ["CI_VALIDATION_RESULT"],
            publication_selection=os.environ["CI_PUBLICATION_SELECTION_RESULT"],
            publication=os.environ["CI_PUBLICATION_RESULT"],
        )
    except (KeyError, RequiredResultError):
        print("Required CI result gate failed; a required job did not succeed or an unexpected job ran.",
              file=sys.stderr)
        return 1
    print("Required CI result gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
