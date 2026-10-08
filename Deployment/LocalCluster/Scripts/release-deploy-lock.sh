#!/usr/bin/env bash
set -euo pipefail

# Inspect or manually release the shared LocalCluster deployment lock on
# node-main. Run it on node-main. The lock is never released automatically.

usage() {
  cat >&2 <<'USAGE'
usage:
  release-deploy-lock.sh --inspect
  release-deploy-lock.sh --release --token <exact token> [--owner-host-checked]

--inspect             print the lock contents and whether the owner process is alive
--release             remove the lock, only when it is provably abandoned:
                        * --token matches the lock's token file exactly
                        * the lock holds only token/owner/created_epoch
                          (another app's lock format must use that app's tool)
                        * no ansible-playbook process runs for this user
                        * the owner process is gone; when the owner ran on another
                          host (a manual deploy from a control machine), check that
                          host yourself and pass --owner-host-checked
USAGE
  exit 2
}

LOCK_DIR="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-/tmp/localcluster-deploy.lockdir}"
MODE=""
TOKEN=""
OWNER_HOST_CHECKED=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --inspect) MODE="inspect"; shift ;;
    --release) MODE="release"; shift ;;
    --token)
      [[ $# -ge 2 ]] || usage
      TOKEN="$2"
      shift 2
      ;;
    --owner-host-checked) OWNER_HOST_CHECKED=true; shift ;;
    -h|--help) usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

[[ -n "$MODE" ]] || usage
[[ "$LOCK_DIR" = /* ]] || { echo "LOCALCLUSTER_DEPLOY_LOCK_DIR must be an absolute path" >&2; exit 1; }

if [[ ! -e "$LOCK_DIR" ]]; then
  echo "deployment lock is free: $LOCK_DIR"
  exit 0
fi

owner_line="$(head -c 2000 "$LOCK_DIR/owner" 2>/dev/null || true)"
owner_host="${owner_line%%:*}"
owner_pid=""
if [[ "$owner_line" =~ :pid=([0-9]+): ]]; then
  owner_pid="${BASH_REMATCH[1]}"
fi

owner_state="unknown"
if [[ -n "$owner_host" && "$owner_host" == "$(hostname)" && -n "$owner_pid" ]]; then
  if kill -0 "$owner_pid" 2>/dev/null; then
    owner_state="alive"
  else
    owner_state="gone"
  fi
elif [[ -n "$owner_host" ]]; then
  owner_state="other-host"
fi

echo "deployment lock: $LOCK_DIR"
find "$LOCK_DIR" -mindepth 1 -maxdepth 1 -print0 | while IFS= read -r -d '' file; do
  echo "--- $(basename "$file")"
  head -c 2000 "$file" 2>/dev/null || echo "(unreadable)"
  echo
done
echo "owner host: ${owner_host:-unknown}"
echo "owner pid: ${owner_pid:-unknown}"
echo "owner process: $owner_state"

[[ "$MODE" == "release" ]] || exit 0

refuse() {
  echo "refusing to release the deployment lock: $*" >&2
  exit 1
}

[[ -n "$TOKEN" ]] || refuse "--token is required"
[[ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" == "$TOKEN" ]] || refuse "token does not match $LOCK_DIR/token"

unexpected="$(find "$LOCK_DIR" -mindepth 1 -maxdepth 1 ! -name token ! -name owner ! -name created_epoch -print -quit)"
[[ -z "$unexpected" ]] || refuse "lock contains $unexpected; it belongs to another app's lock format, use that app's recovery tool"

if pgrep -u "$(id -u)" -f ansible-playbook >/dev/null 2>&1; then
  refuse "an ansible-playbook process is running for $(id -un)"
fi

case "$owner_state" in
  gone) ;;
  alive) refuse "owner process $owner_pid is still running" ;;
  other-host)
    [[ "$OWNER_HOST_CHECKED" == "true" ]] || refuse "owner ran on $owner_host; confirm no deploy runs there, then pass --owner-host-checked"
    ;;
  *) refuse "owner line is missing or unparseable: ${owner_line:-<empty>}" ;;
esac

rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
rmdir "$LOCK_DIR"
echo "deployment lock released: $LOCK_DIR"
