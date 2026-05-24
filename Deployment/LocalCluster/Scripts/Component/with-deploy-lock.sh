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

LOCK_DIR="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-/tmp/localcluster-deploy.lockdir}"
LOCK_TIMEOUT_SECONDS="${LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS:-1800}"
LOCK_STALE_SECONDS="${LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS:-14400}"
LOCK_TOKEN="$(date +%s)-$$-${RANDOM:-0}"
LOCK_OWNER="$(hostname):pid=$$:started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOCK_ACQUIRED=0

[[ "$LOCK_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS must be a number"
[[ "$LOCK_STALE_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS must be a number"
[[ "$LOCK_DIR" = /* ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_DIR must be an absolute path"
[[ -d "$(dirname "$LOCK_DIR")" ]] || fail "lock parent directory does not exist: $(dirname "$LOCK_DIR")"

cleanup_stale_lock() {
  [[ -d "$LOCK_DIR" ]] || return 0

  local created_epoch now age
  created_epoch="$(cat "$LOCK_DIR/created_epoch" 2>/dev/null || true)"
  [[ "$created_epoch" =~ ^[0-9]+$ ]] || return 0

  now="$(date +%s)"
  age=$((now - created_epoch))
  if (( age > LOCK_STALE_SECONDS )); then
    echo "removing stale LocalCluster deployment lock: $LOCK_DIR" >&2
    rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
    rmdir "$LOCK_DIR" 2>/dev/null || true
  fi
}

release_lock() {
  if [[ "$LOCK_ACQUIRED" == "1" ]]; then
    if [[ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" == "$LOCK_TOKEN" ]]; then
      rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
      rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
  fi
}

trap release_lock EXIT

deadline=$((SECONDS + LOCK_TIMEOUT_SECONDS))
echo "waiting for LocalCluster deployment lock: $LOCK_DIR"
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
  cleanup_stale_lock
  if (( SECONDS >= deadline )); then
    echo "timed out waiting for LocalCluster deployment lock: $LOCK_DIR" >&2
    if [[ -f "$LOCK_DIR/owner" ]]; then
      echo "current lock owner: $(cat "$LOCK_DIR/owner")" >&2
    fi
    exit 1
  fi
  sleep 2
done

LOCK_ACQUIRED=1
printf '%s\n' "$LOCK_TOKEN" > "$LOCK_DIR/token"
printf '%s\n' "$LOCK_OWNER" > "$LOCK_DIR/owner"
date +%s > "$LOCK_DIR/created_epoch"
echo "LocalCluster deployment lock acquired: $LOCK_DIR"

"$@"
