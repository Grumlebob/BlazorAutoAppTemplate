#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VAULT="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/vault.yml"

fail() {
  echo "FAIL  $*" >&2
  exit 1
}

command -v ansible-vault >/dev/null 2>&1 || fail "ansible-vault is missing. Run Deployment/LocalCluster/Scripts/setup-control-machine.sh."
command -v python3 >/dev/null 2>&1 || fail "python3 is missing. Run Deployment/LocalCluster/Scripts/setup-control-machine.sh."
[[ -f "$VAULT" ]] || fail "missing encrypted vault: Deployment/LocalCluster/inventory/prod/vault.yml"

head -n 1 "$VAULT" | grep -q '^\$ANSIBLE_VAULT;' || fail "vault.yml is not encrypted with ansible-vault"

CONTENT="$(ansible-vault view "$VAULT")" || fail "could not decrypt vault.yml"

if grep -q "REPLACE_WITH" <<< "$CONTENT"; then
  fail "vault.yml still contains REPLACE_WITH placeholders"
fi

python3 "${SCRIPT_DIR}/Component/lib/validate-vault.py" <<< "$CONTENT"

echo "OK    encrypted vault decrypts and has all required non-placeholder keys"
