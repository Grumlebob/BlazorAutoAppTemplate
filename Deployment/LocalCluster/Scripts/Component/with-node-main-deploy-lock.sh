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
LOCK_TOKEN="$(date +%s)-$$-${RANDOM:-0}"
LOCK_OWNER="$(hostname):pid=$$:repo=manual:node-main=$NODE_MAIN_IP:started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOCK_ACQUIRED=0

[[ "$LOCK_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS must be a number"
[[ "$LOCK_DIR" = /* ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_DIR must be an absolute path"

SSH_TARGET="deploy@$NODE_MAIN_IP"
# Strict host-key checking: a reused LAN IP must not be trusted on first sight.
# Seed known_hosts as described in Deployment/LocalCluster/HowToDeployLocalCluster.md.
SSH_ARGS=(-i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes "$SSH_TARGET")

remote_env() {
  local lock_dir_q lock_token_q lock_owner_q
  lock_dir_q="$(printf '%q' "$LOCK_DIR")"
  lock_token_q="$(printf '%q' "$LOCK_TOKEN")"
  lock_owner_q="$(printf '%q' "$LOCK_OWNER")"
  ssh "${SSH_ARGS[@]}" "LOCK_DIR=$lock_dir_q LOCK_TOKEN=$lock_token_q LOCK_OWNER=$lock_owner_q bash -s"
}

try_acquire_lock() {
  remote_env <<'REMOTE'
set -eu
parent="$(dirname "$LOCK_DIR")"
[ -d "$parent" ] || { echo "remote lock parent directory does not exist: $parent" >&2; exit 2; }
(umask 022; mkdir "$LOCK_DIR") 2>/dev/null || exit 1
printf '%s\n' "$LOCK_TOKEN" > "$LOCK_DIR/token"
printf '%s\n' "$LOCK_OWNER" > "$LOCK_DIR/owner"
date +%s > "$LOCK_DIR/created_epoch"
REMOTE
}

print_lock_owner() {
  remote_env <<'REMOTE' || true
set -eu
for file in owner owner.json; do
  if [ -r "$LOCK_DIR/$file" ]; then
    printf 'lock %s: %s\n' "$file" "$(head -c 2000 "$LOCK_DIR/$file")"
  fi
done
REMOTE
}

# Never reclaim a lock automatically, by age or otherwise. Release only our own
# token, and leave any lock containing another app's metadata for inspection.
release_lock() {
  if [[ "$LOCK_ACQUIRED" == "1" ]]; then
    remote_env <<'REMOTE' || echo "could not release the node-main lock; inspect it with release-deploy-lock.sh --inspect" >&2
set -eu
if [ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" != "$LOCK_TOKEN" ]; then
  echo "node-main lock token changed while held; leaving $LOCK_DIR for inspection" >&2
  exit 75
fi
unexpected="$(find "$LOCK_DIR" -mindepth 1 -maxdepth 1 ! -name token ! -name owner ! -name created_epoch -print -quit)"
if [ -n "$unexpected" ]; then
  echo "node-main lock contains unexpected file $unexpected; leaving it for inspection" >&2
  exit 75
fi
rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
rmdir "$LOCK_DIR"
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

  if (( SECONDS >= deadline )); then
    echo "timed out waiting for LocalCluster deployment lock on node-main: $LOCK_DIR" >&2
    print_lock_owner >&2
    echo "Do not delete the lock by hand. Follow 'Deployment lock' in Deployment/LocalCluster/HowToDeployLocalCluster.md." >&2
    exit 1
  fi

  sleep 2
done

echo "LocalCluster deployment lock acquired on node-main: $LOCK_DIR"
# Foreground on purpose: manual deploys use --ask-vault-pass and need the terminal.
"$@"
