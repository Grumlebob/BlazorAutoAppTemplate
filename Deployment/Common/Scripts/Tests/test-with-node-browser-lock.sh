#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$SCRIPT_DIR/with-node-browser-lock.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export LOCALSINGLENODE_BROWSER_LOCK_FILE="$TMP/browser.lock"

fail() {
  echo "test-with-node-browser-lock: $*" >&2
  exit 1
}

# The wrapper returns the command's exit status unchanged.
set +e
bash "$WRAPPER" bash -c 'exit 7'
status=$?
set -e
[[ "$status" == 7 ]] || fail "expected the command's exit 7, got $status"

# A holder keeps the lock while a second caller with a short timeout gives up with a clear message.
bash "$WRAPPER" bash -c "touch '$TMP/held'; sleep 4" &
holder=$!
for _ in $(seq 1 100); do
  [[ -e "$TMP/held" ]] && break
  sleep 0.1
done
[[ -e "$TMP/held" ]] || fail "the holder never acquired the lock"
set +e
LOCALSINGLENODE_BROWSER_LOCK_TIMEOUT_SECONDS=1 bash "$WRAPPER" true 2>"$TMP/err"
status=$?
set -e
[[ "$status" == 1 ]] || fail "expected a timeout (exit 1) while the lock is held, got $status"
grep -q "timed out after 1s" "$TMP/err" || fail "the timeout message is missing"
wait "$holder" || fail "the holder should finish normally"

# Once the holder has exited, the lock is free again.
bash "$WRAPPER" true

# The command does not inherit the lock descriptor, so nothing it leaves behind can keep the node locked.
bash "$WRAPPER" bash -c '[[ ! -e /proc/self/fd/9 ]]' || fail "the command inherited the lock descriptor"

# Without a command the wrapper refuses to run.
set +e
bash "$WRAPPER" 2>/dev/null
status=$?
set -e
[[ "$status" == 1 ]] || fail "expected usage exit 1 without a command, got $status"

echo "node browser lock: all checks passed"
