#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

DEPLOY_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" deploy_root)"

[[ -f "$INVENTORY" ]] || {
  echo "backup failed: missing inventory: Deployment/Cloud/inventory/prod/hosts.yml" >&2
  exit 1
}

ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && ./backup-db.sh"
