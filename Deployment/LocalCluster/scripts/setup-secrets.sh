#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EXAMPLE="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/vault.example.yml"
VAULT="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/vault.yml"

command -v ansible-vault >/dev/null 2>&1 || {
  echo "ansible-vault is missing. Run Deployment/LocalCluster/scripts/setup-control-machine.sh first." >&2
  exit 1
}

[[ -f "$EXAMPLE" ]] || {
  echo "missing vault template: $EXAMPLE" >&2
  exit 1
}

read -r -s -p "Ansible Vault password: " VAULT_PASSWORD
echo
[[ -n "$VAULT_PASSWORD" ]] || {
  echo "vault password cannot be empty" >&2
  exit 1
}

if [[ ! -f "$VAULT" ]]; then
  read -r -s -p "Confirm Ansible Vault password: " VAULT_PASSWORD_CONFIRM
  echo
  [[ "$VAULT_PASSWORD" == "$VAULT_PASSWORD_CONFIRM" ]] || {
    echo "vault passwords did not match" >&2
    exit 1
  }
fi

PASS_FILE="$(mktemp)"
TMP_VAULT_CONTENT="$(mktemp)"
cleanup() {
  rm -f "$PASS_FILE" "$TMP_VAULT_CONTENT"
}
trap cleanup EXIT

chmod 600 "$PASS_FILE"
printf '%s' "$VAULT_PASSWORD" > "$PASS_FILE"
export ANSIBLE_VAULT_PASSWORD_FILE="$PASS_FILE"

if [[ -f "$VAULT" ]]; then
  echo "vault already exists: Deployment/LocalCluster/inventory/prod/vault.yml"
else
  cp "$EXAMPLE" "$TMP_VAULT_CONTENT"
  ansible-vault encrypt --output "$VAULT" "$TMP_VAULT_CONTENT"
  echo "created encrypted vault: Deployment/LocalCluster/inventory/prod/vault.yml"
fi

echo "opening vault now; replace every REPLACE_WITH value before saving"
ansible-vault edit "$VAULT"

echo "validating encrypted vault contents"
bash "$SCRIPT_DIR/check-vault.sh"

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  printf '%s' "$VAULT_PASSWORD" | gh secret set ANSIBLE_VAULT_PASSWORD --body-file -
  echo "GitHub repository secret set: ANSIBLE_VAULT_PASSWORD"
else
  echo "WARN  gh is missing or not authenticated; set this GitHub secret manually:"
  echo "      ANSIBLE_VAULT_PASSWORD=<password used for Deployment/LocalCluster/inventory/prod/vault.yml>"
fi
