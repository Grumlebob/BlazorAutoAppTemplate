#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LABEL="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" runner_label)"
RUNNER_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" runner_name)"

fail() {
  echo "GitHub runner check failed: $*" >&2
  exit 1
}

command -v gh >/dev/null 2>&1 || fail "gh is missing"
gh auth status >/dev/null 2>&1 || fail "gh is not authenticated"

REPO_NAME="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
RUNNERS_JSON="$(gh api "repos/${REPO_NAME}/actions/runners?per_page=100")"

RUNNERS_JSON="$RUNNERS_JSON" python3 - "$RUNNER_NAME" "$RUNNER_LABEL" <<'PY'
from __future__ import annotations

import json
import os
import sys


runner_name = sys.argv[1]
runner_label = sys.argv[2]
payload = json.loads(os.environ["RUNNERS_JSON"])
required = {"self-hosted", "localcluster", runner_label.lower()}

matches: list[dict[str, object]] = []
for runner in payload.get("runners", []):
    labels = {str(label.get("name", "")).lower() for label in runner.get("labels", [])}
    if runner.get("name") == runner_name or required.issubset(labels):
        matches.append(runner)

if not matches:
    raise SystemExit(f"no self-hosted runner found with expected label {runner_label}")

online_match: dict[str, object] | None = None
for runner in matches:
    labels = {str(label.get("name", "")).lower() for label in runner.get("labels", [])}
    custom_labels = {
        str(label.get("name", "")).lower()
        for label in runner.get("labels", [])
        if str(label.get("type", "")).lower() == "custom"
    }
    missing = sorted(required - labels)
    if missing:
        raise SystemExit(f"runner {runner.get('name')} is missing labels: {', '.join(missing)}")
    unexpected_custom = sorted(custom_labels - {"localcluster", runner_label.lower()})
    if unexpected_custom:
        raise SystemExit(
            f"runner {runner.get('name')} has unexpected custom labels: {', '.join(unexpected_custom)}; rerun install-github-runner.sh"
        )
    if runner.get("status") == "online":
        online_match = runner
        break

if online_match is None:
    statuses = ", ".join(f"{runner.get('name')}={runner.get('status')}" for runner in matches)
    raise SystemExit(f"no matching runner is online: {statuses}")

print(f"GitHub runner ok: {online_match.get('name')} [{runner_label}]")
PY
