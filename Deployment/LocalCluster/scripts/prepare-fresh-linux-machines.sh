#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml"

if [[ $# -ne 0 ]]; then
  echo "usage: $0" >&2
  exit 1
fi

APP_NAME="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" app_name)"
PRIVATE_KEY="$HOME/.ssh/${APP_NAME}_deploy"
PUBLIC_KEY="$PRIVATE_KEY.pub"

bash "$SCRIPT_DIR/preflight.sh" bootstrap
cd "$REPO_ROOT/Deployment/LocalCluster/ansible"

export ANSIBLE_HOST_KEY_CHECKING=False

[[ -f "$PUBLIC_KEY" ]] || {
  echo "public key not found: $PUBLIC_KEY" >&2
  echo "run Deployment/LocalCluster/scripts/setup-control-machine.sh first" >&2
  exit 1
}
[[ -f "$PRIVATE_KEY" ]] || {
  echo "private key not found: $PRIVATE_KEY" >&2
  echo "run Deployment/LocalCluster/scripts/setup-control-machine.sh first" >&2
  exit 1
}

ansible-playbook playbooks/PrepareFreshLinuxMachine.yml \
  -i ../inventory/prod/bootstrap-hosts.yml \
  --ask-pass \
  --ask-become-pass \
  -e "deploy_public_key_file=$PUBLIC_KEY" \
  -e "deploy_private_key_file=$PRIVATE_KEY"

ansible all -m ping
ansible all -a "docker version"
ansible all -a "docker compose version"
