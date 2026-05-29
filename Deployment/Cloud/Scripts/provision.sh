#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

bash "$SCRIPT_DIR/preflight.sh" provision

cd "$REPO_ROOT/Deployment/Cloud/ansible"
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/provision.yml
