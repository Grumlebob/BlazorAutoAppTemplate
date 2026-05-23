#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml"

if [[ $# -ne 0 ]]; then
  echo "usage: $0" >&2
  exit 1
fi

bash "$SCRIPT_DIR/preflight.sh" bootstrap
cd "$REPO_ROOT/Deployment/LocalCluster/ansible"

export ANSIBLE_HOST_KEY_CHECKING=False

ansible all -i ../inventory/prod/bootstrap-hosts.yml --ask-pass --ask-become-pass -m ping
