#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXAMPLE="$REPO_ROOT/Deployment/inventory/prod/vault.example.yml"
VAULT="$REPO_ROOT/Deployment/inventory/prod/vault.yml"

command -v ansible-vault >/dev/null 2>&1 || {
  echo "ansible-vault is missing. Run Deployment/scripts/install-ansible.sh." >&2
  exit 1
}

[[ -f "$EXAMPLE" ]] || {
  echo "missing vault template: $EXAMPLE" >&2
  exit 1
}

if [[ -f "$VAULT" ]]; then
  echo "vault already exists: $VAULT" >&2
  echo "use: ansible-vault edit Deployment/inventory/prod/vault.yml" >&2
  exit 1
fi

TMP="$(mktemp)"
cleanup() {
  rm -f "$TMP"
}
trap cleanup EXIT

cp "$EXAMPLE" "$TMP"
ansible-vault encrypt --output "$VAULT" "$TMP"

echo "created encrypted vault: Deployment/inventory/prod/vault.yml"
echo "opening vault now; replace every REPLACE_WITH value before saving"
ansible-vault edit "$VAULT"
echo "validating encrypted vault contents"
bash "$SCRIPT_DIR/check-vault.sh"
