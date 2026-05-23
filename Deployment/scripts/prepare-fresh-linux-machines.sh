#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/inventory/prod/bootstrap-hosts.yml"

if [[ $# -gt 1 ]]; then
  echo "usage: $0 [linux-mint-install-user]" >&2
  exit 1
fi

INSTALL_USER="${1:-}"
APP_NAME="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" app_name)"
PRIVATE_KEY="$HOME/.ssh/${APP_NAME}_deploy"
PUBLIC_KEY="$PRIVATE_KEY.pub"

bash "$SCRIPT_DIR/preflight.sh" bootstrap
cd "$REPO_ROOT/Deployment/ansible"

export ANSIBLE_HOST_KEY_CHECKING=False

ARGS=(--ask-pass --ask-become-pass)
if [[ -f "$BOOTSTRAP_INVENTORY" ]]; then
  ARGS+=(-i ../inventory/prod/bootstrap-hosts.yml)
elif [[ -n "$INSTALL_USER" ]]; then
  ARGS+=(-u "$INSTALL_USER")
elif [[ -t 0 ]]; then
  read -r -p "Linux Mint install username: " INSTALL_USER
  ARGS+=(-u "$INSTALL_USER")
else
  echo "usage: $0 [linux-mint-install-user]" >&2
  echo "or run Deployment/scripts/generate-inventory.sh to create bootstrap-hosts.yml" >&2
  exit 1
fi
[[ -f "$PUBLIC_KEY" ]] || {
  echo "public key not found: $PUBLIC_KEY" >&2
  echo "run Deployment/scripts/setup-control-machine.sh first" >&2
  exit 1
}
[[ -f "$PRIVATE_KEY" ]] || {
  echo "private key not found: $PRIVATE_KEY" >&2
  echo "run Deployment/scripts/setup-control-machine.sh first" >&2
  exit 1
}
ARGS+=(-e "deploy_public_key_file=$PUBLIC_KEY")
ARGS+=(-e "deploy_private_key_file=$PRIVATE_KEY")

ansible-playbook playbooks/PrepareFreshLinuxMachine.yml "${ARGS[@]}"

ansible all -m ping
ansible all -a "docker version"
ansible all -a "docker compose version"
