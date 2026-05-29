#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOFU_DIR="$REPO_ROOT/Deployment/Cloud/infra/opentofu"
ENVIRONMENT_NAME="${CLOUD_GITHUB_ENVIRONMENT:-cloud-hetzner}"
SSH_PRIVATE_KEY="${CLOUD_SSH_PRIVATE_KEY_PATH:-$HOME/.ssh/bookscloud_deploy}"

fail() {
  echo "configure GitHub environment failed: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
}

require_command gh
require_command openssl
require_command tofu

[[ -f "$SSH_PRIVATE_KEY" ]] || fail "missing SSH private key: $SSH_PRIVATE_KEY"
[[ -f "$TOFU_DIR/terraform.tfstate" ]] || fail "missing OpenTofu state. Run Step 7 first."
[[ -n "${HCLOUD_TOKEN:-}" ]] || fail "HCLOUD_TOKEN is required"

cd "$REPO_ROOT"

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
gh api --method PUT "repos/${REPO}/environments/${ENVIRONMENT_NAME}" >/dev/null

secret_exists() {
  local name="$1"
  gh secret list --env "$ENVIRONMENT_NAME" --json name -q '.[].name' | grep -Fxq "$name"
}

set_secret_body() {
  local name="$1"
  local body="$2"
  gh secret set "$name" --env "$ENVIRONMENT_NAME" --body "$body" >/dev/null
  echo "set ${name}"
}

set_secret_file() {
  local name="$1"
  local file="$2"
  gh secret set "$name" --env "$ENVIRONMENT_NAME" < "$file" >/dev/null
  echo "set ${name}"
}

set_secret_if_missing_body() {
  local name="$1"
  local body="$2"
  if secret_exists "$name"; then
    echo "kept existing ${name}"
  else
    set_secret_body "$name" "$body"
  fi
}

set_secret_interactive_if_missing() {
  local name="$1"
  local env_name="$2"
  local help_text="${3:-}"
  local value="${!env_name:-}"

  if [[ -n "$value" ]]; then
    set_secret_body "$name" "$value"
    return
  fi

  if secret_exists "$name"; then
    echo "kept existing ${name}"
    return
  fi

  echo "Enter ${name} for GitHub environment ${ENVIRONMENT_NAME}."
  if [[ -n "$help_text" ]]; then
    printf '%s\n' "$help_text"
  fi
  gh secret set "$name" --env "$ENVIRONMENT_NAME"
}

tofu_output() {
  (cd "$TOFU_DIR" && tofu output -raw "$1")
}

set_secret_file CLOUD_SSH_PRIVATE_KEY "$SSH_PRIVATE_KEY"
set_secret_body CLOUD_BASTION_HOST "$(tofu_output cloud_main_public_ipv4)"
set_secret_body CLOUD_APP1_PUBLIC_IPV4 "$(tofu_output cloud_app1_public_ipv4)"
set_secret_body CLOUD_APP2_PUBLIC_IPV4 "$(tofu_output cloud_app2_public_ipv4)"
set_secret_body CLOUD_DB_PUBLIC_IPV4 "$(tofu_output cloud_db_public_ipv4)"
set_secret_body CLOUD_HETZNER_API_TOKEN "$HCLOUD_TOKEN"
set_secret_body CLOUD_TEMP_SSH_FIREWALL_ID "$(tofu_output cloud_temp_ssh_firewall_id)"

if [[ "${ROTATE_CLOUD_DATA_SECRETS:-0}" == "1" ]]; then
  set_secret_body CLOUD_POSTGRES_USER "${CLOUD_POSTGRES_USER:-bookscloud_app}"
  set_secret_body CLOUD_POSTGRES_DB "${CLOUD_POSTGRES_DB:-bookscloud}"
  set_secret_body CLOUD_POSTGRES_PASSWORD "${CLOUD_POSTGRES_PASSWORD:-$(openssl rand -base64 36 | tr -d '\n')}"
  set_secret_body CLOUD_REDIS_PASSWORD "${CLOUD_REDIS_PASSWORD:-$(openssl rand -base64 36 | tr -d '\n')}"
else
  set_secret_if_missing_body CLOUD_POSTGRES_USER "${CLOUD_POSTGRES_USER:-bookscloud_app}"
  set_secret_if_missing_body CLOUD_POSTGRES_DB "${CLOUD_POSTGRES_DB:-bookscloud}"
  set_secret_if_missing_body CLOUD_POSTGRES_PASSWORD "${CLOUD_POSTGRES_PASSWORD:-$(openssl rand -base64 36 | tr -d '\n')}"
  set_secret_if_missing_body CLOUD_REDIS_PASSWORD "${CLOUD_REDIS_PASSWORD:-$(openssl rand -base64 36 | tr -d '\n')}"
fi

set_secret_interactive_if_missing \
  CLOUD_GHCR_USERNAME \
  CLOUD_GHCR_USERNAME \
  "Paste the GitHub username that owns the GHCR read token, for example Grumlebob. This is not your email."
set_secret_interactive_if_missing \
  CLOUD_GHCR_TOKEN \
  CLOUD_GHCR_TOKEN \
  "Paste a GitHub personal access token (classic) with read:packages access to ghcr.io/grumlebob/books. This is not the Hetzner token, not the Cloudflare token, and not your GitHub password."
set_secret_interactive_if_missing \
  CLOUD_CLOUDFLARE_TUNNEL_TOKEN \
  CLOUD_CLOUDFLARE_TUNNEL_TOKEN \
  "Paste the long token value from the Cloudflare cloudflared install command copied in Step 9."

echo "GitHub environment configured: ${ENVIRONMENT_NAME}"
