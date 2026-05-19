#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <linux-mint-install-user> [path-to-ship_deploy.pub]" >&2
  exit 1
fi

INSTALL_USER="$1"
PUBLIC_KEY="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

bash "$SCRIPT_DIR/preflight.sh" bootstrap
cd "$REPO_ROOT/Deployment/ansible"

ARGS=(-u "$INSTALL_USER" --ask-pass --ask-become-pass)
if [[ -n "$PUBLIC_KEY" ]]; then
  [[ -f "$PUBLIC_KEY" ]] || {
    echo "public key not found: $PUBLIC_KEY" >&2
    exit 1
  }
  ARGS+=(-e "deploy_public_key_file=$PUBLIC_KEY")
fi

ansible-playbook playbooks/PrepareFreshLinuxMachine.yml "${ARGS[@]}"

ansible all -m ping
ansible all -a "docker version"
ansible all -a "docker compose version"
