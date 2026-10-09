#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../../.." && pwd)"
SCRIPT="$REPO_ROOT/Deployment/Common/Scripts/prune-actions-runner-residue.sh"
TMP_ROOT="$(mktemp -d)"
DRY_RUN_LOG="$TMP_ROOT/dry-run.log"
APPLY_LOG="$TMP_ROOT/apply.log"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

fail() {
  echo "test failed: $*" >&2
  exit 1
}

assert_exists() {
  [[ -e "$1" || -L "$1" ]] || fail "expected path to exist: $1"
}

assert_missing() {
  [[ ! -e "$1" && ! -L "$1" ]] || fail "expected path to be removed: $1"
}

create_fixture() {
  local runner="$TMP_ROOT/actions-runner-sample"
  mkdir -p \
    "$runner/bin.2.334.0" \
    "$runner/bin.2.335.1" \
    "$runner/externals.2.334.0" \
    "$runner/externals.2.335.1" \
    "$runner/_work/_update" \
    "$runner/_work/_temp" \
    "$runner/_work/SampleApp/SampleApp" \
    "$runner/_diag"
  ln -s bin.2.335.1 "$runner/bin"
  ln -s externals.2.335.1 "$runner/externals"
  printf 'keep\n' > "$runner/_work/SampleApp/SampleApp/keep.txt"
  printf 'old temp\n' > "$runner/_work/_temp/old.tmp"
  printf 'old log\n' > "$runner/_diag/old.log"
  printf 'keep current bin\n' > "$runner/bin.2.335.1/keep.txt"
  printf 'remove stale bin\n' > "$runner/bin.2.334.0/remove.txt"
  printf 'keep current externals\n' > "$runner/externals.2.335.1/keep.txt"
  printf 'remove stale externals\n' > "$runner/externals.2.334.0/remove.txt"
  touch -d '10 days ago' \
    "$runner/bin.2.334.0" \
    "$runner/bin.2.335.1" \
    "$runner/externals.2.334.0" \
    "$runner/externals.2.335.1" \
    "$runner/_work/_update" \
    "$runner/_work/_temp/old.tmp"
  touch -d '20 days ago' \
    "$runner/_diag/old.log"
}

create_fixture

bash "$SCRIPT" \
  --dry-run \
  --force \
  --opt-root "$TMP_ROOT" \
  --all-localcluster-runners \
  --min-free-mb 0 \
  --stale-version-until 168h \
  --update-until 24h \
  --temp-until 24h \
  --diag-until 336h >"$DRY_RUN_LOG"

assert_exists "$TMP_ROOT/actions-runner-sample/bin.2.334.0"
assert_exists "$TMP_ROOT/actions-runner-sample/externals.2.334.0"
assert_exists "$TMP_ROOT/actions-runner-sample/_work/_update"
assert_exists "$TMP_ROOT/actions-runner-sample/_work/_temp/old.tmp"
assert_exists "$TMP_ROOT/actions-runner-sample/_diag/old.log"

bash "$SCRIPT" \
  --force \
  --defer-if-skipped \
  --opt-root "$TMP_ROOT" \
  --all-localcluster-runners \
  --min-free-mb 0 \
  --stale-version-until 168h \
  --update-until 24h \
  --temp-until 24h \
  --diag-until 336h >"$APPLY_LOG"

assert_missing "$TMP_ROOT/actions-runner-sample/bin.2.334.0"
assert_missing "$TMP_ROOT/actions-runner-sample/externals.2.334.0"
assert_missing "$TMP_ROOT/actions-runner-sample/_work/_update"
assert_missing "$TMP_ROOT/actions-runner-sample/_work/_temp/old.tmp"
assert_missing "$TMP_ROOT/actions-runner-sample/_diag/old.log"
assert_exists "$TMP_ROOT/actions-runner-sample/bin"
assert_exists "$TMP_ROOT/actions-runner-sample/externals"
assert_exists "$TMP_ROOT/actions-runner-sample/bin.2.335.1/keep.txt"
assert_exists "$TMP_ROOT/actions-runner-sample/externals.2.335.1/keep.txt"
assert_exists "$TMP_ROOT/actions-runner-sample/_work/SampleApp/SampleApp/keep.txt"
grep -Fq 'skip: protected current runner path:' "$APPLY_LOG" \
  || fail "expected old current runner versions to be retained without deferral"

# An active stale candidate must be reported as a safe deferral when the
# caller opts into the result-code contract, and must remain untouched.
mkdir -p "$TMP_ROOT/actions-runner-sample/_work/_update"
touch -d '10 days ago' "$TMP_ROOT/actions-runner-sample/_work/_update"
bash -c "cd '$TMP_ROOT/actions-runner-sample/_work/_update' && sleep 30" &
active_pid=$!
set +e
bash "$SCRIPT" \
  --force \
  --opt-root "$TMP_ROOT" \
  --all-localcluster-runners \
  --defer-if-skipped \
  --min-free-mb 0 \
  --stale-version-until 168h \
  --update-until 24h \
  --temp-until 24h \
  --diag-until 336h >"$TMP_ROOT/deferred.log" 2>&1
deferred_status=$?
set -e
kill "$active_pid" 2>/dev/null || true
wait "$active_pid" 2>/dev/null || true
[[ "$deferred_status" -eq 75 ]] || { cat "$TMP_ROOT/deferred.log" >&2; fail "expected active runner residue to return 75, got $deferred_status"; }
assert_exists "$TMP_ROOT/actions-runner-sample/_work/_update"

# Common helpers select an explicit app without reaching into target settings.
bash "$SCRIPT" --dry-run --force --opt-root "$TMP_ROOT" --app-name sample --min-free-mb 0 > "$TMP_ROOT/app-selection.log" 2>&1
grep -Fq "$TMP_ROOT/actions-runner-sample" "$TMP_ROOT/app-selection.log" || fail "app runner was not selected"
status=0
bash "$SCRIPT" --dry-run --force --opt-root "$TMP_ROOT" --app-name 'invalid/name' > "$TMP_ROOT/invalid-app.log" 2>&1 || status=$?
[[ "$status" -eq 1 ]] || fail "invalid app name was accepted"
status=0
bash "$SCRIPT" --dry-run --force --opt-root "$TMP_ROOT" > "$TMP_ROOT/no-selection.log" 2>&1 || status=$?
[[ "$status" -eq 1 ]] || fail "missing runner selection was accepted"
echo "prune-actions-runner-residue fixture test passed"
