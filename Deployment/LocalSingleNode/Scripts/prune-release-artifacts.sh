#!/usr/bin/env bash
set -euo pipefail

# The workflow resolves and validates the selected app instance before calling
# this script. Keep the accepted marker read and artifact cleanup under the
# same host lock used by LocalSingleNode and LocalCluster release selection.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMMON="$ROOT/Deployment/Common/Scripts"
LOCK_DIR="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-}"
LOCK_TOKEN="${LOCALCLUSTER_DEPLOY_LOCK_TOKEN:-}"
INSTANCE_FILE="${INSTANCE_EXTRA_VARS_FILE:-}"
RUNNER_TEMP_DIR="${RUNNER_TEMP:-}"

if [[ -z "$LOCK_DIR" || -z "$LOCK_TOKEN" || "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" != "$LOCK_TOKEN" ]]; then
  echo "artifact retention requires the shared LocalSingleNode deployment lock" >&2
  exit 1
fi
[[ -n "${GITHUB_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" ]] || {
  echo "GITHUB_TOKEN and GITHUB_REPOSITORY are required" >&2
  exit 1
}
[[ -n "$RUNNER_TEMP_DIR" && "$INSTANCE_FILE" == "$RUNNER_TEMP_DIR"/* && -f "$INSTANCE_FILE" ]] || {
  echo "validated app-instance settings are unavailable" >&2
  exit 1
}
[[ -n "${MIGRATION_ARTIFACT_NAME:-}" ]] || { echo "MIGRATION_ARTIFACT_NAME is required" >&2; exit 1; }
export GH_TOKEN="$GITHUB_TOKEN"

cleanup() {
  rm -f -- "$INSTANCE_FILE"
  if [[ -n "${LOCALSINGLENODE_SETTINGS_FILE:-}" ]]; then
    rm -f -- "$LOCALSINGLENODE_SETTINGS_FILE"
  fi
}
trap cleanup EXIT

identity="$(python3 - "$INSTANCE_FILE" <<'PY'
import json
import re
import sys

values = json.load(open(sys.argv[1], encoding="utf-8"))
app = values.get("app_name")
root = values.get("deploy_root")
if not isinstance(app, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", app):
    raise SystemExit("validated app identity is malformed")
if not isinstance(root, str) or not re.fullmatch(r"/opt/[A-Za-z0-9_./-]+", root) or ".." in root.split("/"):
    raise SystemExit("validated deployment root is malformed")
print(app)
print(root)
PY
)"
mapfile -t identity_fields <<< "$identity"
[[ "${#identity_fields[@]}" == 2 ]] || { echo "validated app identity is malformed" >&2; exit 1; }
deploy_root="${identity_fields[1]}"
source_repo_url="${GITHUB_SERVER_URL%/}/${GITHUB_REPOSITORY}"
live_run_id="$(python3 "$SCRIPT_DIR/lib/read_release_acceptance.py" \
  --ci-run-id --expected-source-repo-url "$source_repo_url" "$deploy_root/release.json")"
[[ "$live_run_id" =~ ^[1-9][0-9]*$ ]] || { echo "accepted release CI run ID is invalid" >&2; exit 1; }
[[ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" == "$LOCK_TOKEN" ]] || {
  echo "LocalSingleNode lock token changed before artifact selection" >&2
  exit 1
}

# The shared pruner also pins live targets and the two newest successful target
# SHAs from both deployment workflows; this exact CI run covers failed deploys.
bash "$COMMON/prune-actions-artifacts.sh" \
  --artifact-name "$MIGRATION_ARTIFACT_NAME" \
  --keep 2 \
  --max-unprotected-bytes 536870912 \
  --max-deletions 100 \
  --deployment-workflow-file cd-localcluster.yml \
  --deployment-workflow-file cd-localsinglenode.yml \
  --protect-run-id "$live_run_id"

# Preview under the same deployment lock; a missing or ambiguous release marker
# makes the helper fail closed before either invocation can delete a pin.
python3 "$COMMON/Component/lib/pin_release_payload.py" \
  --prune-root "$deploy_root/release-payloads/${GITHUB_REPOSITORY//\//-}" \
  --repository "$source_repo_url" \
  --current-marker "$deploy_root/release.json" \
  --recovery-marker "$deploy_root/release-state/previous.json" \
  --max-candidates-per-profile 3 \
  --max-unprotected-bytes 1073741824

python3 "$COMMON/Component/lib/pin_release_payload.py" \
  --prune-root "$deploy_root/release-payloads/${GITHUB_REPOSITORY//\//-}" \
  --repository "$source_repo_url" \
  --current-marker "$deploy_root/release.json" \
  --recovery-marker "$deploy_root/release-state/previous.json" \
  --max-candidates-per-profile 3 \
  --max-unprotected-bytes 1073741824 \
  --apply
