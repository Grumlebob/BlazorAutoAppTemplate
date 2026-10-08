#!/usr/bin/env bash
set -euo pipefail

# Behaviour tests for Component/with-deploy-lock.sh and release-deploy-lock.sh.
# They only use temporary lock directories, never the real node-main lock.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_WRAPPER="$SCRIPT_DIR/../Component/with-deploy-lock.sh"
RELEASE_TOOL="$SCRIPT_DIR/../release-deploy-lock.sh"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/test-with-deploy-lock.XXXXXX")"
trap 'rm -rf -- "$WORK_DIR"' EXIT

export LOCALCLUSTER_DEPLOY_LOCK_DIR="$WORK_DIR/localcluster-deploy.lockdir"
LOCK_DIR="$LOCALCLUSTER_DEPLOY_LOCK_DIR"

failures=0
pass() { echo "ok   - $1"; }
fail_test() { echo "FAIL - $1" >&2; failures=$((failures + 1)); }

reset_lock() {
  rm -rf -- "$LOCK_DIR"
}

seed_foreign_lock() {
  mkdir "$LOCK_DIR"
  printf '%s\n' "foreign-token" > "$LOCK_DIR/token"
  printf '%s\n' "other-host:pid=4242:repo=other/app:run=1-1:started=2026-01-01T00:00:00Z" > "$LOCK_DIR/owner"
  echo $(( $(date +%s) - 36000 )) > "$LOCK_DIR/created_epoch"
}

# 1. Lock is acquired, the command runs, the lock is removed, exit codes propagate.
reset_lock
if output="$(bash "$LOCK_WRAPPER" bash -c 'test -d "$LOCALCLUSTER_DEPLOY_LOCK_DIR" && echo inside' 2>&1)" \
  && grep -Fq inside <<<"$output" && [[ ! -e "$LOCK_DIR" ]]; then
  pass "command runs under the lock and the lock is released"
else
  fail_test "command runs under the lock and the lock is released: $output"
fi

reset_lock
set +e
bash "$LOCK_WRAPPER" bash -c 'exit 7' >/dev/null 2>&1
status=$?
set -e
if [[ "$status" == "7" && ! -e "$LOCK_DIR" ]]; then
  pass "non-zero command exit code propagates and the lock is released"
else
  fail_test "non-zero command exit code propagates (got $status)"
fi

# 2. A ten-hour-old lock owned by someone else is never reclaimed.
reset_lock
seed_foreign_lock
set +e
output="$(LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS=2 bash "$LOCK_WRAPPER" true 2>&1)"
status=$?
set -e
if [[ "$status" == "1" && "$(cat "$LOCK_DIR/token")" == "foreign-token" ]] \
  && grep -Fq "lock owner: other-host:pid=4242" <<<"$output"; then
  pass "old foreign lock is not reclaimed and its owner is reported"
else
  fail_test "old foreign lock is not reclaimed (status $status): $output"
fi

# 3. Another app's lock format (extra metadata file) is left untouched.
reset_lock
seed_foreign_lock
printf '{"owner":"other"}\n' > "$LOCK_DIR/owner.json"
set +e
LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS=2 bash "$LOCK_WRAPPER" true >/dev/null 2>&1
set -e
if [[ -f "$LOCK_DIR/owner.json" && -f "$LOCK_DIR/token" ]]; then
  pass "foreign lock metadata is left untouched"
else
  fail_test "foreign lock metadata is left untouched"
fi

# 4. On SIGTERM the wrapper keeps the lock until the owned command exits.
reset_lock
marker="$WORK_DIR/child-finished"
bash "$LOCK_WRAPPER" bash -c "trap '' TERM; sleep 3; touch '$marker'" >/dev/null 2>&1 &
wrapper_pid=$!
for _ in $(seq 1 50); do
  [[ -f "$LOCK_DIR/token" ]] && break
  sleep 0.1
done
kill -TERM "$wrapper_pid"
sleep 1
if [[ -d "$LOCK_DIR" && ! -f "$marker" ]]; then
  held_during_child=true
else
  held_during_child=false
fi
set +e
wait "$wrapper_pid"
status=$?
set -e
if [[ "$held_during_child" == "true" && -f "$marker" && ! -e "$LOCK_DIR" && "$status" == "143" ]]; then
  pass "termination waits for the owned command before releasing the lock"
else
  fail_test "termination waits for the owned command (held=$held_during_child status=$status)"
fi

# 5. release-deploy-lock.sh refuses unsafe releases and allows a verified one.
reset_lock
seed_foreign_lock
if bash "$RELEASE_TOOL" --release --token wrong-token >/dev/null 2>&1; then
  fail_test "release with a wrong token is refused"
else
  pass "release with a wrong token is refused"
fi
if bash "$RELEASE_TOOL" --release --token foreign-token >/dev/null 2>&1; then
  fail_test "release of another host's lock needs --owner-host-checked"
else
  pass "release of another host's lock needs --owner-host-checked"
fi
printf '{}\n' > "$LOCK_DIR/owner.json"
if bash "$RELEASE_TOOL" --release --token foreign-token --owner-host-checked >/dev/null 2>&1; then
  fail_test "release of another app's lock format is refused"
else
  pass "release of another app's lock format is refused"
fi
rm -f "$LOCK_DIR/owner.json"

reset_lock
mkdir "$LOCK_DIR"
printf '%s\n' "live-token" > "$LOCK_DIR/token"
printf '%s\n' "$(hostname):pid=$$:repo=test:run=1-1:started=now" > "$LOCK_DIR/owner"
if bash "$RELEASE_TOOL" --release --token live-token >/dev/null 2>&1; then
  fail_test "release while the owner process is alive is refused"
else
  pass "release while the owner process is alive is refused"
fi

reset_lock
mkdir "$LOCK_DIR"
printf '%s\n' "dead-token" > "$LOCK_DIR/token"
bash -c 'exit 0' &
dead_pid=$!
wait "$dead_pid"
printf '%s\n' "$(hostname):pid=$dead_pid:repo=test:run=1-1:started=now" > "$LOCK_DIR/owner"
if pgrep -u "$(id -u)" -f ansible-playbook >/dev/null 2>&1; then
  echo "skip - verified release (an ansible-playbook process runs for this user)"
elif bash "$RELEASE_TOOL" --release --token dead-token >/dev/null 2>&1 && [[ ! -e "$LOCK_DIR" ]]; then
  pass "verified release of an abandoned lock succeeds"
else
  fail_test "verified release of an abandoned lock succeeds"
fi

if bash "$RELEASE_TOOL" --inspect | grep -Fq "deployment lock is free"; then
  pass "inspect reports a free lock"
else
  fail_test "inspect reports a free lock"
fi

if [[ "$failures" -ne 0 ]]; then
  echo "$failures deploy lock test(s) failed" >&2
  exit 1
fi
echo "deploy lock tests passed"
