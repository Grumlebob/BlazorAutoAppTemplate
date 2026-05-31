#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOFU_DIR="$REPO_ROOT/Deployment/Cloud/infra/opentofu"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/Component/lib/cloud-env.sh"
cloud_env_bootstrap_path

fail() {
  echo "render inventory from OpenTofu failed: $*" >&2
  exit 1
}

command -v tofu >/dev/null 2>&1 || fail "tofu is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
[[ -f "$TOFU_DIR/terraform.tfstate" ]] || fail "missing OpenTofu state. Run Step 7 first."

SSH_KEY_PATH="${CLOUD_SSH_PRIVATE_KEY_PATH:-$HOME/.ssh/bookscloud_deploy}"
KNOWN_HOSTS_PATH="${CLOUD_KNOWN_HOSTS_FILE:-$HOME/.ssh/known_hosts}"

tofu_output() {
  (cd "$TOFU_DIR" && tofu output -raw "$1")
}

python3 "$SCRIPT_DIR/Component/lib/render-inventory.py" \
  --bastion-public-ip "$(tofu_output cloud_main_public_ipv4)" \
  --ssh-private-key-path "$SSH_KEY_PATH" \
  --known-hosts-path "$KNOWN_HOSTS_PATH" \
  --output "$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
