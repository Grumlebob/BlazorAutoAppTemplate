#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "usage: $0 <command> [args...]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

fail() {
  echo "node-main deploy lock failed: $*" >&2
  exit 1
}

command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing"
command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
command -v ssh >/dev/null 2>&1 || fail "ssh is missing"
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"

APP_NAME="$(python3 "${SCRIPT_DIR}/lib/read-deploy-setting.py" app_name)"
SSH_KEY="$HOME/.ssh/${APP_NAME}_deploy"
[[ -f "$SSH_KEY" ]] || fail "missing SSH private key: $SSH_KEY"

NODE_MAIN_IP="$(ansible-inventory -i "$INVENTORY" --host node-main | python3 -c 'import json, sys; print(json.load(sys.stdin).get("ansible_host", ""))')"
[[ -n "$NODE_MAIN_IP" && "$NODE_MAIN_IP" != REPLACE_WITH* ]] || fail "node-main ansible_host is missing or still a placeholder"

LOCK_DIR="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-/tmp/localcluster-deploy.lockdir}"
LOCK_TIMEOUT_SECONDS="${LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS:-1800}"
LOCK_STALE_SECONDS="${LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS:-14400}"
LOCK_TOKEN="$(date +%s)-$$-${RANDOM:-0}"
LOCK_OWNER="$(hostname):pid=$$:node-main=$NODE_MAIN_IP:started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOCK_ACQUIRED=0

[[ "$LOCK_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS must be a number"
[[ "$LOCK_STALE_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS must be a number"
[[ "$LOCK_DIR" = /* ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_DIR must be an absolute path"

SSH_TARGET="deploy@$NODE_MAIN_IP"
SSH_ARGS=(-i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$SSH_TARGET")

remote_env() {
  local lock_dir_q lock_token_q lock_owner_q lock_stale_q
  lock_dir_q="$(printf '%q' "$LOCK_DIR")"
  lock_token_q="$(printf '%q' "$LOCK_TOKEN")"
  lock_owner_q="$(printf '%q' "$LOCK_OWNER")"
  lock_stale_q="$(printf '%q' "$LOCK_STALE_SECONDS")"
  ssh "${SSH_ARGS[@]}" "LOCK_DIR=$lock_dir_q LOCK_TOKEN=$lock_token_q LOCK_OWNER=$lock_owner_q LOCK_STALE_SECONDS=$lock_stale_q bash -s"
}

try_acquire_lock() {
  remote_env <<'REMOTE'
set -eu
parent="$(dirname "$LOCK_DIR")"
[ -d "$parent" ] || { echo "remote lock parent directory does not exist: $parent" >&2; exit 2; }
mkdir "$LOCK_DIR" 2>/dev/null || exit 1
printf '%s\n' "$LOCK_TOKEN" > "$LOCK_DIR/token"
printf '%s\n' "$LOCK_OWNER" > "$LOCK_DIR/owner"
date +%s > "$LOCK_DIR/created_epoch"
REMOTE
}

cleanup_stale_lock() {
  remote_env <<'REMOTE'
set -eu
[ -d "$LOCK_DIR" ] || exit 0
created_epoch="$(cat "$LOCK_DIR/created_epoch" 2>/dev/null || true)"
case "$created_epoch" in
  ''|*[!0-9]*) exit 0 ;;
esac
now="$(date +%s)"
age=$((now - created_epoch))
if [ "$age" -gt "$LOCK_STALE_SECONDS" ]; then
  echo "removing stale LocalCluster deployment lock: $LOCK_DIR" >&2
  rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
  rmdir "$LOCK_DIR" 2>/dev/null || true
fi
REMOTE
}

print_lock_owner() {
  remote_env <<'REMOTE' || true
set -eu
cat "$LOCK_DIR/owner" 2>/dev/null || true
REMOTE
}

release_lock() {
  if [[ "$LOCK_ACQUIRED" == "1" ]]; then
    remote_env <<'REMOTE' || true
set -eu
if [ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" = "$LOCK_TOKEN" ]; then
  rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
  rmdir "$LOCK_DIR" 2>/dev/null || true
fi
REMOTE
  fi
}

trap release_lock EXIT

deadline=$((SECONDS + LOCK_TIMEOUT_SECONDS))
echo "waiting for LocalCluster deployment lock on node-main ($NODE_MAIN_IP): $LOCK_DIR"
while true; do
  set +e
  try_acquire_lock
  acquire_rc=$?
  set -e

  if [[ "$acquire_rc" == "0" ]]; then
    LOCK_ACQUIRED=1
    break
  fi

  [[ "$acquire_rc" == "1" ]] || exit "$acquire_rc"
  cleanup_stale_lock

  if (( SECONDS >= deadline )); then
    echo "timed out waiting for LocalCluster deployment lock on node-main: $LOCK_DIR" >&2
    owner="$(print_lock_owner)"
    if [[ -n "$owner" ]]; then
      echo "current lock owner: $owner" >&2
    fi
    exit 1
  fi

  sleep 2
done

echo "LocalCluster deployment lock acquired on node-main: $LOCK_DIR"
"$@"
