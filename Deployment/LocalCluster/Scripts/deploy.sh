#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: deploy.sh <git-sha-image-tag> [--digest sha256:<64 hex>] [--migrate <path-to-migration-bundle>]

Manual deploy from a control machine. Prefer the "CD - Deploy LocalCluster"
workflow: it deploys only commits on main with successful CI and a verified
release manifest. A manual deploy skips those provenance checks.

  --digest   Pin the app image to this registry digest (recommended; copy it
             from the CI run's release-manifest.json).
  --migrate  Run this EF migration bundle before starting app servers.

Registry credentials for a private image come from, in order: GHCR_USERNAME and
GHCR_TOKEN environment variables, an authenticated `gh` CLI, or the optional
vault_ghcr_* vault keys.
EOF
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

[[ $# -ge 1 ]] || usage

APP_VERSION="$1"
shift

EXTRA_ARGS=(-e "app_version=$APP_VERSION")

while [[ $# -gt 0 ]]; do
  case "$1" in
    --digest)
      [[ $# -ge 2 ]] || usage
      [[ "$2" =~ ^sha256:[0-9a-f]{64}$ ]] || {
        echo "--digest must be sha256:<64 lowercase hex characters>" >&2
        exit 1
      }
      EXTRA_ARGS+=(-e "release_image_digest=$2")
      shift 2
      ;;
    --migrate)
      [[ $# -ge 2 ]] || usage
      [[ -f "$2" ]] || {
        echo "migration bundle not found: $2" >&2
        exit 1
      }
      MIGRATION_BUNDLE="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
      EXTRA_ARGS+=(-e "run_migrations=true" -e "migration_bundle_local_path=$MIGRATION_BUNDLE")
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

echo "WARN  manual deploy: CI success and release-manifest checks are skipped. Prefer the CD workflow." >&2

SOURCE_REPO_URL="$(git -C "$REPO_ROOT" config --get remote.origin.url || true)"
[[ -n "$SOURCE_REPO_URL" ]] || SOURCE_REPO_URL="unknown"

EXTRA_ARGS+=(-e "source_repo_url=$SOURCE_REPO_URL")

# Pass registry credentials through a private extra-vars file, never argv.
GHCR_VARS_FILE=""
cleanup() {
  [[ -z "$GHCR_VARS_FILE" ]] || rm -f "$GHCR_VARS_FILE"
}
trap cleanup EXIT
ghcr_username="${GHCR_USERNAME:-}"
ghcr_token="${GHCR_TOKEN:-}"
if [[ -z "$ghcr_token" ]] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  ghcr_username="$(gh api user --jq .login)"
  ghcr_token="$(gh auth token)"
fi
if [[ -n "$ghcr_username" && -n "$ghcr_token" ]]; then
  GHCR_VARS_FILE="$(umask 077 && mktemp "${TMPDIR:-/tmp}/ghcr_deploy_vars.XXXXXX")"
  GHCR_USERNAME="$ghcr_username" GHCR_TOKEN="$ghcr_token" GHCR_VARS_FILE="$GHCR_VARS_FILE" python3 - <<'PY'
import json
import os

with open(os.environ["GHCR_VARS_FILE"], "w", encoding="utf-8") as output:
    json.dump({"vault_ghcr_username": os.environ["GHCR_USERNAME"], "vault_ghcr_token": os.environ["GHCR_TOKEN"]}, output)
PY
  EXTRA_ARGS+=(-e "@$GHCR_VARS_FILE")
fi

bash "$SCRIPT_DIR/preflight.sh" deploy
cd "$REPO_ROOT/Deployment/LocalCluster/ansible"

bash "${SCRIPT_DIR}/Component/with-node-main-deploy-lock.sh" \
  ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml --ask-vault-pass "${EXTRA_ARGS[@]}"
