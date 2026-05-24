#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <git-sha-image-tag> [--migrate <path-to-migration-bundle>]" >&2
  exit 1
}

[[ $# -ge 1 ]] || usage

APP_VERSION="$1"
shift

EXTRA_ARGS=(-e "app_version=$APP_VERSION")

if [[ $# -gt 0 ]]; then
  [[ "$1" == "--migrate" && $# -eq 2 ]] || usage
  [[ -f "$2" ]] || {
    echo "migration bundle not found: $2" >&2
    exit 1
  }
  MIGRATION_BUNDLE="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
  EXTRA_ARGS+=(-e "run_migrations=true" -e "migration_bundle_local_path=$MIGRATION_BUNDLE")
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SOURCE_REPO_URL="$(git -C "$REPO_ROOT" config --get remote.origin.url || true)"
[[ -n "$SOURCE_REPO_URL" ]] || SOURCE_REPO_URL="unknown"

EXTRA_ARGS+=(-e "source_repo_url=$SOURCE_REPO_URL")

bash "$SCRIPT_DIR/preflight.sh" deploy
cd "$REPO_ROOT/Deployment/LocalCluster/ansible"

bash "${SCRIPT_DIR}/Component/with-node-main-deploy-lock.sh" \
  ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml --ask-vault-pass "${EXTRA_ARGS[@]}"
