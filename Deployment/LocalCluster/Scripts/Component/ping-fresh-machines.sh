#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd -P "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../../.." && pwd)"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml"

if [[ $# -ne 0 ]]; then
  echo "usage: $0" >&2
  exit 1
fi

[[ -f "$SCRIPTS_DIR/preflight.sh" ]] || {
  echo "fresh-machine ping failed: missing required script: $SCRIPTS_DIR/preflight.sh" >&2
  echo "Resolved Component script directory: $SCRIPT_DIR" >&2
  echo "Resolved scripts directory: $SCRIPTS_DIR" >&2
  exit 1
}

bash "$SCRIPTS_DIR/preflight.sh" bootstrap
cd "$REPO_ROOT/Deployment/LocalCluster/ansible"

export ANSIBLE_HOST_KEY_CHECKING=False

ansible all -i "$BOOTSTRAP_INVENTORY" --ask-pass --ask-become-pass -m ping
