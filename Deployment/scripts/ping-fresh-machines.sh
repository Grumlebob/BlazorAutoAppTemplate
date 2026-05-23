#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/inventory/prod/bootstrap-hosts.yml"

INSTALL_USER="${1:-}"

bash "$SCRIPT_DIR/preflight.sh" bootstrap
cd "$REPO_ROOT/Deployment/ansible"

export ANSIBLE_HOST_KEY_CHECKING=False

if [[ -f "$BOOTSTRAP_INVENTORY" ]]; then
  ansible all -i ../inventory/prod/bootstrap-hosts.yml --ask-pass --ask-become-pass -m ping
elif [[ -n "$INSTALL_USER" ]]; then
  ansible all -i ../inventory/prod/hosts.yml -u "$INSTALL_USER" --ask-pass --ask-become-pass -m ping
elif [[ -t 0 ]]; then
  read -r -p "Linux Mint install username: " INSTALL_USER
  ansible all -i ../inventory/prod/hosts.yml -u "$INSTALL_USER" --ask-pass --ask-become-pass -m ping
else
  echo "usage: $0 [linux-mint-install-user]" >&2
  echo "or run Deployment/scripts/generate-inventory.sh to create bootstrap-hosts.yml" >&2
  exit 1
fi
