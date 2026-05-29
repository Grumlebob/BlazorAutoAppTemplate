#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT_NAME="${CLOUD_GITHUB_ENVIRONMENT:-cloud-hetzner}"

required_secrets=(
  CLOUD_SSH_PRIVATE_KEY
  CLOUD_BASTION_HOST
  CLOUD_APP1_PUBLIC_IPV4
  CLOUD_APP2_PUBLIC_IPV4
  CLOUD_DB_PUBLIC_IPV4
  CLOUD_HETZNER_API_TOKEN
  CLOUD_TEMP_SSH_FIREWALL_ID
  CLOUD_GHCR_USERNAME
  CLOUD_GHCR_TOKEN
  CLOUD_POSTGRES_USER
  CLOUD_POSTGRES_PASSWORD
  CLOUD_POSTGRES_DB
  CLOUD_REDIS_PASSWORD
  CLOUD_CLOUDFLARE_TUNNEL_TOKEN
)

fail() {
  echo "GitHub environment check failed: $*" >&2
  exit 1
}

command -v gh >/dev/null 2>&1 || fail "gh is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."

secret_names="$(gh secret list --env "$ENVIRONMENT_NAME" --json name -q '.[].name')" \
  || fail "could not list secrets for environment ${ENVIRONMENT_NAME}"
mapfile -t existing_secrets <<< "$secret_names"

missing=()
for secret in "${required_secrets[@]}"; do
  found=0
  for existing in "${existing_secrets[@]}"; do
    if [[ "$existing" == "$secret" ]]; then
      found=1
      break
    fi
  done
  if ((found == 0)); then
    missing+=("$secret")
  fi
done

if ((${#missing[@]} > 0)); then
  printf 'missing GitHub environment secrets in %s:\n' "$ENVIRONMENT_NAME" >&2
  printf ' - %s\n' "${missing[@]}" >&2
  exit 1
fi

echo "GitHub environment check ok: ${ENVIRONMENT_NAME}"
