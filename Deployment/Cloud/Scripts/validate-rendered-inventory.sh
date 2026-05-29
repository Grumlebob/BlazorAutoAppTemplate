#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

command -v ansible-inventory >/dev/null 2>&1 || {
  echo "Cloud inventory validation failed: ansible-inventory is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh." >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  echo "Cloud inventory validation failed: python3 is missing." >&2
  exit 1
}

export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"
python3 "$SCRIPT_DIR/Component/lib/validate-rendered-inventory.py" \
  --inventory "$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
