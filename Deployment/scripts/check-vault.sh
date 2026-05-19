#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VAULT="$REPO_ROOT/Deployment/inventory/prod/vault.yml"

fail() {
  echo "FAIL  $*" >&2
  exit 1
}

command -v ansible-vault >/dev/null 2>&1 || fail "ansible-vault is missing. Run Deployment/scripts/setup-control-machine.sh."
[[ -f "$VAULT" ]] || fail "missing encrypted vault: Deployment/inventory/prod/vault.yml"

head -n 1 "$VAULT" | grep -q '^\$ANSIBLE_VAULT;' || fail "vault.yml is not encrypted with ansible-vault"

CONTENT="$(ansible-vault view "$VAULT")" || fail "could not decrypt vault.yml"

if grep -q "REPLACE_WITH" <<< "$CONTENT"; then
  fail "vault.yml still contains REPLACE_WITH placeholders"
fi

REQUIRED_KEYS=(
  vault_postgres_user
  vault_postgres_password
  vault_postgres_db
  vault_redis_password
  vault_ghcr_username
  vault_ghcr_token
  vault_cloudflare_tunnel_token
)

for key in "${REQUIRED_KEYS[@]}"; do
  line="$(grep -E "^[[:space:]]*$key:" <<< "$CONTENT" || true)"
  [[ -n "$line" ]] || fail "vault.yml is missing required key: $key"
  grep -Eq "^[[:space:]]*$key:[[:space:]]*$" <<< "$line" && fail "vault.yml has empty value for: $key"
done

echo "OK    encrypted vault decrypts and has all required non-placeholder keys"
