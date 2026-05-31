#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/Component/lib/cloud-env.sh"
cloud_env_bootstrap_path

fail() {
  echo "render inventory from environment failed: $*" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
: "${CLOUD_BASTION_HOST:?CLOUD_BASTION_HOST is required}"

SSH_KEY_PATH="${CLOUD_SSH_PRIVATE_KEY_PATH:-$HOME/.ssh/bookscloud_deploy}"
KNOWN_HOSTS_PATH="${CLOUD_KNOWN_HOSTS_FILE:-$HOME/.ssh/known_hosts}"

python3 "$SCRIPT_DIR/Component/lib/render-inventory.py" \
  --bastion-public-ip "$CLOUD_BASTION_HOST" \
  --ssh-private-key-path "$SSH_KEY_PATH" \
  --known-hosts-path "$KNOWN_HOSTS_PATH" \
  --output "$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
