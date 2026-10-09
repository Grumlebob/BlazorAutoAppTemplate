#!/usr/bin/env bash
# Scheduled/manual LocalCluster maintenance for node-main and the cluster.
#
# Runs under the shared deployment lock, so it never overlaps a deploy from
# this or another app. Every stage removes only resources it can prove are
# unused or owned by this repository; Docker volumes are never pruned.
#
# usage: run-localcluster-maintenance.sh [--capacity-only]
#   --capacity-only  Only the runner and node-main Docker stages.
# Exit codes: 0 done, 1 failure, 2 still below the capacity reserve,
# 75 deferred (protected candidates were skipped).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPT_DIR="$(cd "$SCRIPT_DIR/../../Common/Scripts" && pwd)"
CAPACITY_ONLY=false
UNDER_LOCK=false
for argument in "$@"; do
  case "$argument" in
    --capacity-only) CAPACITY_ONLY=true ;;
    --under-lock) UNDER_LOCK=true ;;
    *) echo "unknown maintenance argument: $argument" >&2; exit 1 ;;
  esac
done

# Same lock as CD. Re-execute under it; never run the stages without it.
if [[ "$UNDER_LOCK" == false ]]; then
  export LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS="${LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS:-300}"
  exec bash "$COMMON_SCRIPT_DIR/with-deploy-lock.sh" bash "$0" --under-lock "$@"
fi
lock_dir="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-}"
lock_token="${LOCALCLUSTER_DEPLOY_LOCK_TOKEN:-}"
if [[ -z "$lock_dir" || -z "$lock_token" || "$(cat "$lock_dir/token" 2>/dev/null || true)" != "$lock_token" ]]; then
  echo "maintenance must run under with-deploy-lock.sh; the deployment lock is not held" >&2
  exit 1
fi

source "$SCRIPT_DIR/localcluster-capacity-thresholds.sh"
[[ -n "${GITHUB_WORKSPACE:-}" && -d "$GITHUB_WORKSPACE" ]] || { echo "GITHUB_WORKSPACE is required" >&2; exit 1; }
runner_root="$(cd "$GITHUB_WORKSPACE/../../.." && pwd -P)"
[[ -d "$runner_root/_work" ]] || { echo "invalid Actions runner root" >&2; exit 1; }

result=0
stage() {
  local name="$1" seconds="$2" status=0
  shift 2
  # Continue independent diagnostics/cleanup, but never mask a failure.
  timeout --signal=TERM --kill-after=30s "${seconds}s" "$@" || status=$?
  echo "maintenance-stage=$name status=$status"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    printf '| %s | %s |\n' "$name" "$status" >> "$GITHUB_STEP_SUMMARY"
  fi
  case "$status" in
    0) ;;
    75) [[ "$result" != 0 ]] || result=75 ;;
    2)
      # Only these helpers define 2 as a measured capacity shortfall.
      # Ansible/Compose also use 2, but for operational failures.
      if [[ "$name" == runner || "$name" == docker ]]; then
        [[ "$result" == 1 ]] || result=2
      else
        result=1
      fi
      ;;
    *) result=1 ;;
  esac
}

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  printf '### LocalCluster maintenance\n\n| Stage | Exit code |\n| --- | --- |\n' >> "$GITHUB_STEP_SUMMARY"
fi
stage runner 180 bash "$COMMON_SCRIPT_DIR/prune-actions-runner-residue.sh" \
  --force --runner-root "$runner_root" --min-free-mb 0 \
  --stale-version-until 168h --update-until 24h --temp-until 24h \
  --diag-until 336h --defer-if-skipped
if [[ "$CAPACITY_ONLY" == false ]]; then
  stage ci-residue 300 python3 "$SCRIPT_DIR/prune-ci-residue.py" --apply --limit 25
fi
stage docker 180 bash "$SCRIPT_DIR/prune-docker-residue.sh" \
  --force --min-free-mb "$LOCALCLUSTER_LOAD_BALANCER_MIN_FREE_MB" \
  --dangling-image-until 168h --localcluster-image-until 168h \
  --defer-if-skipped
if [[ "$CAPACITY_ONLY" == false ]]; then
  stage remote-docker 300 bash "$SCRIPT_DIR/prune-cluster-docker-residue.sh"
fi
echo "Unreferenced volumes (report only; Docker volumes are never pruned by maintenance):"
stage volume-inventory 30 docker volume ls -q --filter dangling=true
stage disk-report 30 df -Pm /opt
stage inode-report 30 df -Pi /opt
capacity_status=0
bash "$SCRIPT_DIR/check-node-main-capacity.sh" || capacity_status=$?
case "$capacity_status" in
  0)
    if [[ "$CAPACITY_ONLY" == true && "$result" == 75 ]]; then
      echo "Cleanup deferred protected candidates, but the capacity reserve is available."
      result=0
    fi
    ;;
  2) [[ "$result" == 1 ]] || result=2 ;;
  *) result=1 ;;
esac
if [[ "$result" == 75 ]]; then
  echo "::warning::Maintenance is incomplete/deferred; protected candidates were not deleted."
elif [[ "$result" != 0 ]]; then
  echo "::error::Maintenance failed; inspect stage results. No blanket volume or host-data pruning was requested."
fi
exit "$result"
