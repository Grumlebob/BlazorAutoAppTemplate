#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/../ensure-actions-runner-prereqs.sh"
TEST_BASH="$BASH"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir "$TMP_ROOT/bin"
export MUTATION_LOG="$TMP_ROOT/mutations"
: > "$MUTATION_LOG"
cat > "$TMP_ROOT/bin/python3" <<'SH'
#!/bin/bash
[[ "$*" == '-m venv --help' ]] || exit 99
exit "${PYTHON_VENV_STATUS:-0}"
SH
cat > "$TMP_ROOT/bin/docker" <<'SH'
#!/bin/bash
[[ "$*" == info ]] || exit 99
exit "${DOCKER_CHECK_STATUS:-0}"
SH
cat > "$TMP_ROOT/bin/pwsh" <<'SH'
#!/bin/bash
printf '%s\n' '7.6.6'
SH
cat > "$TMP_ROOT/bin/shellcheck" <<'SH'
#!/bin/bash
exit 0
SH
for command in sudo apt-get dpkg curl; do
  cat > "$TMP_ROOT/bin/$command" <<'SH'
#!/bin/bash
printf '%s\n' "$0 $*" >> "$MUTATION_LOG"
exit 99
SH
done
chmod +x "$TMP_ROOT/bin/"*
run_case() {
  local expected="$1" status=0
  shift
  PATH="$TMP_ROOT/bin" "$TEST_BASH" "$SCRIPT" "$@" > "$TMP_ROOT/output" 2>&1 || status=$?
  [[ "$status" == "$expected" ]] || { cat "$TMP_ROOT/output" >&2; echo "expected $expected, got $status" >&2; exit 1; }
  [[ ! -s "$MUTATION_LOG" ]] || { cat "$MUTATION_LOG" >&2; echo "prerequisite check mutated the host" >&2; exit 1; }
}
run_case 0 --check
run_case 0 --provision
PYTHON_VENV_STATUS=1 run_case 1 --check
DOCKER_CHECK_STATUS=1 run_case 1 --check
for command in shellcheck pwsh python3 docker; do
  mv "$TMP_ROOT/bin/$command" "$TMP_ROOT/$command"
  run_case 1 --check
  mv "$TMP_ROOT/$command" "$TMP_ROOT/bin/$command"
done
run_case 2 --invalid
echo "runner prerequisite check-only, missing-tool and idempotent fixtures passed"
