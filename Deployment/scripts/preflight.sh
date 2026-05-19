#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-deploy}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/inventory/prod/hosts.yml"
VAULT="$REPO_ROOT/Deployment/inventory/prod/vault.yml"
SSH_KEY="${SHIP_DEPLOY_KEY:-$HOME/.ssh/ship_deploy}"
SSH_PUB="${SHIP_DEPLOY_KEY_PUB:-$SSH_KEY.pub}"

fail() {
  echo "preflight failed: $*" >&2
  exit 1
}

[[ "$MODE" == "bootstrap" || "$MODE" == "deploy" ]] || fail "mode must be 'bootstrap' or 'deploy'"

command -v ansible >/dev/null 2>&1 || fail "ansible is missing. Run Deployment/scripts/install-ansible.sh."
command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing. Run Deployment/scripts/install-ansible.sh."
command -v ansible-playbook >/dev/null 2>&1 || fail "ansible-playbook is missing. Run Deployment/scripts/install-ansible.sh."
command -v ssh >/dev/null 2>&1 || fail "ssh is missing."

[[ -f "$INVENTORY" ]] || fail "missing inventory: $INVENTORY"
if grep -R "REPLACE_WITH" "$INVENTORY" >/dev/null; then
  fail "replace all REPLACE_WITH values in Deployment/inventory/prod/hosts.yml"
fi

[[ -f "$SSH_KEY" ]] || fail "missing SSH private key: $SSH_KEY"
[[ -f "$SSH_PUB" ]] || fail "missing SSH public key: $SSH_PUB"

ansible-inventory -i "$INVENTORY" --list >/dev/null

if [[ "$MODE" == "deploy" ]]; then
  command -v ansible-vault >/dev/null 2>&1 || fail "ansible-vault is missing. Run Deployment/scripts/install-ansible.sh."
  [[ -f "$VAULT" ]] || fail "missing encrypted vault: $VAULT"
fi

echo "preflight ok ($MODE)"
