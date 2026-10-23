#!/usr/bin/env bash
# Serialise the packaged browser and Docker smoke stages across repositories on one host.
#
# Two repositories' CI share the 7 GB node. When one repository's Chromium or Docker smoke stage overlaps the
# other's, navigations fail (ERR_NETWORK_CHANGED, 45-second action timeouts). This lock is separate from the
# deployment lock: it is held only while one CI browser or smoke command runs, and deployments and maintenance
# never take it. flock releases it when the holding process exits, so a crashed job cannot leave it held.
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "usage: $0 <command> [args...]" >&2
  exit 1
fi

fail() {
  echo "browser lock failed: $*" >&2
  exit 1
}

LOCK_FILE="${LOCALSINGLENODE_BROWSER_LOCK_FILE:-/tmp/localsinglenode-ci-browser.lock}"
LOCK_TIMEOUT_SECONDS="${LOCALSINGLENODE_BROWSER_LOCK_TIMEOUT_SECONDS:-3600}"

[[ "$LOCK_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALSINGLENODE_BROWSER_LOCK_TIMEOUT_SECONDS must be a number"
[[ "$LOCK_FILE" = /* ]] || fail "LOCALSINGLENODE_BROWSER_LOCK_FILE must be an absolute path"
command -v flock >/dev/null 2>&1 || fail "flock (util-linux) is required"

exec 9>>"$LOCK_FILE" || fail "cannot open $LOCK_FILE"
echo "waiting for the node browser lock: $LOCK_FILE"
if ! flock --timeout "$LOCK_TIMEOUT_SECONDS" 9; then
  fail "timed out after ${LOCK_TIMEOUT_SECONDS}s; another repository's browser or Docker smoke stage holds $LOCK_FILE. Do not delete the lock file."
fi
# Informational owner line for whoever inspects a stuck lock. flock, not this file, decides ownership.
printf '%s\n' "repo=${GITHUB_REPOSITORY:-manual} run=${GITHUB_RUN_ID:-none}-${GITHUB_RUN_ATTEMPT:-0} started=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCK_FILE.owner" || true
echo "node browser lock acquired: $LOCK_FILE"
# The command must not inherit the lock descriptor: a background process it leaves behind would keep the node locked.
"$@" 9>&-
