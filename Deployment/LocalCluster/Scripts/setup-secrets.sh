#!/usr/bin/env bash
set -euo pipefail
umask 077

PREPARE_ONLY=false
if [[ $# -gt 0 ]]; then
  [[ $# -eq 1 && "$1" == --prepare-data-protection-only ]] || {
    echo "usage: setup-secrets.sh [--prepare-data-protection-only]" >&2
    exit 2
  }
  PREPARE_ONLY=true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EXAMPLE="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/vault.example.yml"
VAULT="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/vault.yml"

command -v ansible-vault >/dev/null 2>&1 || {
  echo "ansible-vault is missing. Run Deployment/LocalCluster/Scripts/setup-control-machine.sh first." >&2
  exit 1
}
command -v openssl >/dev/null 2>&1 || {
  echo "openssl is missing. Install OpenSSL before creating the protected Data Protection key." >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  echo "python3 is missing. Install Python 3 before creating the protected Data Protection key." >&2
  exit 1
}

[[ -f "$EXAMPLE" ]] || {
  echo "missing vault template: $EXAMPLE" >&2
  exit 1
}

if [[ "$PREPARE_ONLY" == true ]]; then
  [[ -f "$VAULT" && -n "${ANSIBLE_VAULT_PASSWORD_FILE:-}" && -f "$ANSIBLE_VAULT_PASSWORD_FILE" ]] || {
    echo "Preparation requires an existing encrypted vault and protected vault password file." >&2
    exit 1
  }
  VAULT_PASSWORD="$(cat "$ANSIBLE_VAULT_PASSWORD_FILE")"
else
  read -r -s -p "Ansible Vault password: " VAULT_PASSWORD
  echo
fi
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
KEY_DIRECTORY="$(mktemp -d)"
TMP_ENCRYPTED_VAULT="$KEY_DIRECTORY/vault.ansible"
cleanup() {
  rm -f "$PASS_FILE" "$TMP_VAULT_CONTENT" "$TMP_ENCRYPTED_VAULT"
  rm -rf "$KEY_DIRECTORY"
}
trap cleanup EXIT

chmod 600 "$PASS_FILE"
printf '%s' "$VAULT_PASSWORD" > "$PASS_FILE"
export ANSIBLE_VAULT_PASSWORD_FILE="$PASS_FILE"

if [[ -f "$VAULT" ]]; then
  echo "vault already exists: Deployment/LocalCluster/inventory/prod/vault.yml"
  ansible-vault decrypt --output "$TMP_VAULT_CONTENT" "$VAULT"
else
  cp "$EXAMPLE" "$TMP_VAULT_CONTENT"
fi

chmod 600 "$TMP_VAULT_CONTENT"
DP_STATE="$(python3 "$SCRIPT_DIR/Component/lib/data_protection_vault.py" inspect "$TMP_VAULT_CONTENT")" || {
  echo "Data Protection certificate vault entries are partial or invalid; no vault was changed." >&2
  exit 1
}

if [[ "$DP_STATE" == "generate" ]]; then
  openssl rand -hex 32 > "$KEY_DIRECTORY/password"
  chmod 600 "$KEY_DIRECTORY/password"
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
    -aes-256-cbc -pass "file:$KEY_DIRECTORY/password" \
    -out "$KEY_DIRECTORY/private-key.pem" >/dev/null 2>&1
  openssl req -x509 -sha256 -days 3650 \
    -key "$KEY_DIRECTORY/private-key.pem" -passin "file:$KEY_DIRECTORY/password" \
    -out "$KEY_DIRECTORY/public-certificate.pem" \
    -subj "/CN=GrumPlates LocalCluster Data Protection" >/dev/null 2>&1
  cat "$KEY_DIRECTORY/public-certificate.pem" "$KEY_DIRECTORY/private-key.pem" > "$KEY_DIRECTORY/certificate.pem"
  base64 < "$KEY_DIRECTORY/certificate.pem" | tr -d '\n' > "$KEY_DIRECTORY/certificate.b64"
  python3 "$SCRIPT_DIR/Component/lib/data_protection_vault.py" update \
    "$TMP_VAULT_CONTENT" "$KEY_DIRECTORY/certificate.b64" "$KEY_DIRECTORY/password"
  ansible-vault encrypt --output "$TMP_ENCRYPTED_VAULT" "$TMP_VAULT_CONTENT"
  chmod 600 "$TMP_ENCRYPTED_VAULT"
  mv -f -- "$TMP_ENCRYPTED_VAULT" "$VAULT"
  echo "generated and encrypted app Data Protection recovery key"
elif [[ ! -f "$VAULT" ]]; then
  ansible-vault encrypt --output "$VAULT" "$TMP_VAULT_CONTENT"
  chmod 600 "$VAULT"
  echo "created encrypted vault: Deployment/LocalCluster/inventory/prod/vault.yml"
fi

if [[ "$PREPARE_ONLY" != true ]]; then
  echo "opening vault now; replace every REPLACE_WITH value before saving"
  ansible-vault edit "$VAULT"
fi

echo "validating encrypted vault contents"
bash "$SCRIPT_DIR/check-vault.sh"

if [[ "$PREPARE_ONLY" == true ]]; then
  echo "Encrypted Data Protection vault preparation complete; existing credentials were preserved."
  exit 0
fi

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if printf '%s' "$VAULT_PASSWORD" | gh secret set ANSIBLE_VAULT_PASSWORD; then
    echo "GitHub repository secret set: ANSIBLE_VAULT_PASSWORD"
  else
    echo "WARN  could not set the GitHub repository secret automatically." >&2
    echo "      Set this GitHub secret manually:" >&2
    echo "      ANSIBLE_VAULT_PASSWORD=<password used for Deployment/LocalCluster/inventory/prod/vault.yml>" >&2
  fi
else
  echo "WARN  gh is missing or not authenticated; set this GitHub secret manually:"
  echo "      ANSIBLE_VAULT_PASSWORD=<password used for Deployment/LocalCluster/inventory/prod/vault.yml>"
fi
