#!/usr/bin/env bash
set -euo pipefail

# Run only through the shared deployment lock. Release selection and download
# use the same lock, so cleanup cannot race with a pinned workflow workspace.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMMON="$ROOT/Deployment/Common/Scripts"
LOCK_DIR="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-}"
LOCK_TOKEN="${LOCALCLUSTER_DEPLOY_LOCK_TOKEN:-}"

if [[ -z "$LOCK_DIR" || -z "$LOCK_TOKEN" || "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" != "$LOCK_TOKEN" ]]; then
  echo "artifact retention requires the shared LocalCluster deployment lock" >&2
  exit 1
fi
[[ -n "${GITHUB_TOKEN:-}" ]] || { echo "GITHUB_TOKEN is required" >&2; exit 1; }
[[ -n "${GITHUB_REPOSITORY:-}" ]] || { echo "GITHUB_REPOSITORY is required" >&2; exit 1; }
export GH_TOKEN="$GITHUB_TOKEN"

APP_NAME="$(bash "$ROOT/Deployment/LocalCluster/Scripts/read-deploy-setting.sh" app_name)"
DEPLOY_ROOT="$(bash "$ROOT/Deployment/LocalCluster/Scripts/read-deploy-setting.sh" deploy_root)"
MIGRATION_ARTIFACT_NAME="$(bash "$COMMON/read-release-setting.sh" migration_artifact_name)"

# The live image is authoritative when a failed CD changed the nodes before a
# later workflow check failed. If any node is unavailable or disagrees, stop.
live_run_ids="$(APP_NAME="$APP_NAME" DEPLOY_ROOT="$DEPLOY_ROOT" \
  python3 "$ROOT/Deployment/LocalCluster/Scripts/Component/lib/read-live-release-ci-run-ids.py")"

protect_args=()
declare -A protected_ids=()
add_protected_id() {
  local run_id="$1"
  [[ "$run_id" =~ ^[1-9][0-9]*$ ]] || { echo "invalid protected CI run ID" >&2; exit 1; }
  [[ -n "${protected_ids[$run_id]:-}" ]] && return 0
  protected_ids[$run_id]=1
  protect_args+=(--protect-run-id "$run_id")
  echo "Protecting CI run ${run_id}"
}

while IFS= read -r run_id; do
  [[ -n "$run_id" ]] || continue
  add_protected_id "$run_id"
done <<< "$live_run_ids"

[[ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" == "$LOCK_TOKEN" ]] || {
  echo "LocalCluster lock token changed before artifact selection" >&2
  exit 1
}

bash "$COMMON/prune-actions-artifacts.sh" \
  --artifact-name "$MIGRATION_ARTIFACT_NAME" \
  --keep 2 \
  --max-unprotected-bytes 536870912 \
  --max-deletions 100 \
  --deployment-workflow-file cd-localcluster.yml \
  --deployment-workflow-file cd-localsinglenode.yml \
  "${protect_args[@]}"

# Preview under the same deployment lock; a missing or ambiguous release marker
# makes the helper fail closed before either invocation can delete a pin.
python3 "$COMMON/Component/lib/pin_release_payload.py" \
  --prune-root "$DEPLOY_ROOT/release-payloads/${GITHUB_REPOSITORY//\//-}" \
  --repository "${GITHUB_SERVER_URL%/}/${GITHUB_REPOSITORY}" \
  --current-marker "$DEPLOY_ROOT/release.json" \
  --recovery-marker "$DEPLOY_ROOT/release-state/previous.json" \
  --max-candidates-per-profile 3 \
  --max-unprotected-bytes 1073741824

python3 "$COMMON/Component/lib/pin_release_payload.py" \
  --prune-root "$DEPLOY_ROOT/release-payloads/${GITHUB_REPOSITORY//\//-}" \
  --repository "${GITHUB_SERVER_URL%/}/${GITHUB_REPOSITORY}" \
  --current-marker "$DEPLOY_ROOT/release.json" \
  --recovery-marker "$DEPLOY_ROOT/release-state/previous.json" \
  --max-candidates-per-profile 3 \
  --max-unprotected-bytes 1073741824 \
  --apply
