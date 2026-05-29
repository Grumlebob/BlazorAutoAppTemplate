#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-deploy}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml"
VAULT="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/vault.yml"

fail() {
  echo "preflight failed: $*" >&2
  exit 1
}

[[ "$MODE" == "bootstrap" || "$MODE" == "deploy" ]] || fail "mode must be 'bootstrap' or 'deploy'"

command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
command -v ansible >/dev/null 2>&1 || fail "ansible is missing. Run Deployment/LocalCluster/Scripts/setup-control-machine.sh."
command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing. Run Deployment/LocalCluster/Scripts/setup-control-machine.sh."
command -v ansible-playbook >/dev/null 2>&1 || fail "ansible-playbook is missing. Run Deployment/LocalCluster/Scripts/setup-control-machine.sh."
command -v ssh >/dev/null 2>&1 || fail "ssh is missing."

python3 "${SCRIPT_DIR}/Component/lib/validate-deploy-settings.py" >/dev/null || fail "Deployment/LocalCluster/inventory/prod/group_vars/all.yml is invalid"
bash "$REPO_ROOT/Deployment/Common/Scripts/validate-common-release.sh" >/dev/null || fail "Deployment/Common/release.yml is invalid"

APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_name)"
SSH_KEY="$HOME/.ssh/${APP_NAME}_deploy"
SSH_PUB="$SSH_KEY.pub"

[[ -f "$INVENTORY" ]] || fail "missing inventory: $INVENTORY"
if grep -R "REPLACE_WITH" "$INVENTORY" >/dev/null; then
  fail "replace all REPLACE_WITH values in Deployment/LocalCluster/inventory/prod/hosts.yml"
fi

[[ -f "$SSH_KEY" ]] || fail "missing SSH private key: $SSH_KEY"
[[ -f "$SSH_PUB" ]] || fail "missing SSH public key: $SSH_PUB"

ansible-inventory -i "$INVENTORY" --list >/dev/null

if [[ "$MODE" == "bootstrap" ]]; then
  [[ -f "$BOOTSTRAP_INVENTORY" ]] || fail "missing bootstrap inventory: $BOOTSTRAP_INVENTORY. Run Deployment/LocalCluster/Scripts/generate-inventory.sh."
  if grep -R "REPLACE_WITH" "$BOOTSTRAP_INVENTORY" >/dev/null; then
    fail "replace all REPLACE_WITH values in Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml"
  fi
  ansible-inventory -i "$BOOTSTRAP_INVENTORY" --list >/dev/null
fi

if [[ "$MODE" == "deploy" ]]; then
  command -v ansible-vault >/dev/null 2>&1 || fail "ansible-vault is missing. Run Deployment/LocalCluster/Scripts/setup-control-machine.sh."
  [[ -f "$VAULT" ]] || fail "missing encrypted vault: $VAULT"
  bash "$SCRIPT_DIR/check-vault.sh"
  bash "$SCRIPT_DIR/check-port-collisions.sh"
  bash "$SCRIPT_DIR/validate-side-by-side.sh"
fi

echo "preflight ok ($MODE)"
