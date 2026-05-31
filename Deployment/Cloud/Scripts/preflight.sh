#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-provision}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/Component/lib/cloud-env.sh"
cloud_env_bootstrap_path

fail() {
  echo "cloud preflight failed: $*" >&2
  exit 1
}

[[ "$MODE" == "provision" || "$MODE" == "deploy" ]] || fail "mode must be 'provision' or 'deploy'"

command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
command -v ansible >/dev/null 2>&1 || fail "ansible is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
command -v ansible-playbook >/dev/null 2>&1 || fail "ansible-playbook is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
command -v ssh >/dev/null 2>&1 || fail "ssh is missing."

bash "$REPO_ROOT/Deployment/Common/Scripts/validate-common-release.sh" >/dev/null || fail "Deployment/Common/release.yml is invalid"
bash "$SCRIPT_DIR/validate-cloud-settings.sh" >/dev/null || fail "Deployment/Cloud/inventory/prod/group_vars/all.yml is invalid"

[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml. Run Deployment/Cloud/Scripts/render-inventory-from-tofu.sh."
if grep -R "REPLACE_WITH" "$INVENTORY" >/dev/null; then
  fail "replace all REPLACE_WITH values in Deployment/Cloud/inventory/prod/hosts.yml"
fi

SSH_KEY="${CLOUD_SSH_PRIVATE_KEY_PATH:-$HOME/.ssh/bookscloud_deploy}"
[[ -f "$SSH_KEY" ]] || fail "missing SSH private key: $SSH_KEY"

bash "$SCRIPT_DIR/validate-rendered-inventory.sh" >/dev/null
ansible-inventory -i "$INVENTORY" --list >/dev/null

if [[ "${SKIP_CLOUD_SSH_REACHABILITY_CHECK:-0}" != "1" ]]; then
  bash "$SCRIPT_DIR/check-ssh-reachability.sh"
fi

if [[ "$MODE" == "deploy" || "$MODE" == "provision" ]]; then
  bash "$SCRIPT_DIR/observability-capacity-check.sh"
fi

echo "cloud preflight ok ($MODE)"
