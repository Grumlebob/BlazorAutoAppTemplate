#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
LIB="$REPO_ROOT/Deployment/Cloud/Scripts/Component/lib/cloud-env.sh"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cloud-account-env.XXXXXX")"
trap 'rm -rf -- "$TEMP_ROOT"' EXIT

cat > "$TEMP_ROOT/.env.cloud" <<'EOF'
CLOUD_ACCOUNTS_EMAIL_PASSWORD=' spaces $dollar #hash = "double" '
EOF

export REPO_ROOT="$TEMP_ROOT"
export CLOUD_ENV_QUIET=1
# shellcheck disable=SC1090
. "$LIB"

expected=$' spaces $dollar #hash = "double" '
export CLOUD_ACCOUNTS_EMAIL_PASSWORD='process environment wins'
cloud_env_load_missing_var CLOUD_ACCOUNTS_EMAIL_PASSWORD
[[ "$CLOUD_ACCOUNTS_EMAIL_PASSWORD" == 'process environment wins' ]] || {
  echo "Cloud account env loader replaced an existing process value" >&2
  exit 1
}

unset CLOUD_ACCOUNTS_EMAIL_PASSWORD
cloud_env_load_missing_var CLOUD_ACCOUNTS_EMAIL_PASSWORD
[[ "$CLOUD_ACCOUNTS_EMAIL_PASSWORD" == "$expected" ]] || {
  echo "Cloud account env loader did not preserve the synthetic quoted value" >&2
  exit 1
}

echo "Cloud account env loader fixture passed"
