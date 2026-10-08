#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "usage: $0 <command> [args...]" >&2
  exit 1
fi

fail() {
  echo "deploy lock failed: $*" >&2
  exit 1
}

# Shared by every app deployed to this node-main. Other repositories use the
# same directory and may store extra metadata files in it.
LOCK_DIR="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-/tmp/localcluster-deploy.lockdir}"
LOCK_TIMEOUT_SECONDS="${LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS:-1800}"
LOCK_TOKEN="$(date +%s)-$$-${RANDOM:-0}"
LOCK_OWNER="$(hostname):pid=$$:repo=${GITHUB_REPOSITORY:-manual}:run=${GITHUB_RUN_ID:-none}-${GITHUB_RUN_ATTEMPT:-0}:started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOCK_ACQUIRED=0
ACTIVE_COMMAND_PID=""
PENDING_SIGNAL_STATUS=0

[[ "$LOCK_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS must be a number"
[[ "$LOCK_DIR" = /* ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_DIR must be an absolute path"
[[ -d "$(dirname "$LOCK_DIR")" ]] || fail "lock parent directory does not exist: $(dirname "$LOCK_DIR")"

# Never reclaim a lock automatically. A dead shell can leave live children,
# and another app may legitimately hold the lock for hours. Recovery is the
# manual, verified procedure in release-deploy-lock.sh.
release_lock() {
  [[ "$LOCK_ACQUIRED" == "1" ]] || return 0
  if [[ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" != "$LOCK_TOKEN" ]]; then
    echo "LocalCluster lock token changed while held; leaving $LOCK_DIR for inspection" >&2
    return 75
  fi
  local unexpected
  unexpected="$(find "$LOCK_DIR" -mindepth 1 -maxdepth 1 ! -name token ! -name owner ! -name created_epoch -print -quit)"
  if [[ -n "$unexpected" ]]; then
    echo "LocalCluster lock contains unexpected file $unexpected; leaving it for inspection" >&2
    return 75
  fi
  rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
  rmdir "$LOCK_DIR" || {
    echo "could not remove $LOCK_DIR; inspect it" >&2
    return 75
  }
  LOCK_ACQUIRED=0
}

finish() {
  local status=$?
  trap - EXIT
  local release_status=0
  release_lock || release_status=$?
  if [[ "$status" == "0" && "$release_status" != "0" ]]; then
    status=75
  fi
  exit "$status"
}
trap finish EXIT

# Keep the lock until the owned command has exited, so a cancelled job cannot
# let another deploy start while ansible-playbook is still mutating nodes.
wait_for_owned_command_then_exit() {
  local signal_status="$1"
  trap '' TERM INT
  if [[ -n "$ACTIVE_COMMAND_PID" ]]; then
    echo "termination received; waiting for owned command PID $ACTIVE_COMMAND_PID before releasing the lock" >&2
    set +e
    while kill -0 "$ACTIVE_COMMAND_PID" 2>/dev/null; do
      wait "$ACTIVE_COMMAND_PID"
    done
    set -e
  fi
  exit "$signal_status"
}

handle_signal() {
  local signal_status="$1"
  if [[ -z "$ACTIVE_COMMAND_PID" ]]; then
    [[ "$LOCK_ACQUIRED" == "1" ]] || exit "$signal_status"
    PENDING_SIGNAL_STATUS="$signal_status"
    return
  fi
  wait_for_owned_command_then_exit "$signal_status"
}
trap 'handle_signal 143' TERM
trap 'handle_signal 130' INT

deadline=$((SECONDS + LOCK_TIMEOUT_SECONDS))
echo "waiting for LocalCluster deployment lock: $LOCK_DIR"
# 0755 so other apps' runners can read the owner line when they time out.
while ! (umask 022; mkdir "$LOCK_DIR") 2>/dev/null; do
  if (( SECONDS >= deadline )); then
    echo "timed out waiting for LocalCluster deployment lock: $LOCK_DIR" >&2
    for file in owner owner.json; do
      if [[ -r "$LOCK_DIR/$file" ]]; then
        echo "lock $file: $(head -c 2000 "$LOCK_DIR/$file")" >&2
      fi
    done
    echo "Do not delete the lock by hand. Follow 'Deployment lock' in Deployment/LocalCluster/HowToDeployLocalCluster.md." >&2
    exit 1
  fi
  sleep 2
done

LOCK_ACQUIRED=1
export LOCALCLUSTER_DEPLOY_LOCK_DIR="$LOCK_DIR" LOCALCLUSTER_DEPLOY_LOCK_TOKEN="$LOCK_TOKEN"
printf '%s\n' "$LOCK_TOKEN" > "$LOCK_DIR/token"
printf '%s\n' "$LOCK_OWNER" > "$LOCK_DIR/owner"
date +%s > "$LOCK_DIR/created_epoch"
echo "LocalCluster deployment lock acquired: $LOCK_DIR"

[[ "$PENDING_SIGNAL_STATUS" == "0" ]] || exit "$PENDING_SIGNAL_STATUS"
# Explicit stdin: background commands in a non-interactive shell otherwise read /dev/null.
"$@" <&0 &
ACTIVE_COMMAND_PID=$!
command_status=0
wait "$ACTIVE_COMMAND_PID" || command_status=$?
ACTIVE_COMMAND_PID=""
[[ "$PENDING_SIGNAL_STATUS" == "0" ]] || exit "$PENDING_SIGNAL_STATUS"
exit "$command_status"
