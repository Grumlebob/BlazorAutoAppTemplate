#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <git-sha-image-tag> [--migrate <path-to-migration-bundle>] [--reset-db <app-name>/<database-name>] [--reset-node-db-volumes <app-name>/postgres18-redis8-reset]" >&2
  exit 1
}

[[ $# -ge 1 ]] || usage

APP_VERSION="$1"
shift

EXTRA_ARGS=(-e "app_version=$APP_VERSION")
RUN_MIGRATIONS=false
RESET_DATABASE=false
RESET_NODE_DB_VOLUMES=false
RESET_CONFIRMATION=""
RESET_NODE_DB_VOLUMES_CONFIRMATION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --migrate)
      [[ $# -ge 2 ]] || usage
      [[ -f "$2" ]] || {
        echo "migration bundle not found: $2" >&2
        exit 1
      }
      MIGRATION_BUNDLE="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
      EXTRA_ARGS+=(-e "run_migrations=true" -e "migration_bundle_local_path=$MIGRATION_BUNDLE")
      RUN_MIGRATIONS=true
      shift 2
      ;;
    --reset-db)
      [[ $# -ge 2 ]] || usage
      RESET_CONFIRMATION="$2"
      RESET_DATABASE=true
      shift 2
      ;;
    --reset-node-db-volumes)
      [[ $# -ge 2 ]] || usage
      RESET_NODE_DB_VOLUMES_CONFIRMATION="$2"
      RESET_NODE_DB_VOLUMES=true
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

if [[ "$RESET_DATABASE" == true && "$RUN_MIGRATIONS" != true ]]; then
  echo "--reset-db must be used with --migrate so the fresh database is immediately migrated" >&2
  exit 1
fi

if [[ "$RESET_NODE_DB_VOLUMES" == true && "$RUN_MIGRATIONS" != true ]]; then
  echo "--reset-node-db-volumes must be used with --migrate so the fresh database is immediately migrated" >&2
  exit 1
fi

if [[ "$RESET_NODE_DB_VOLUMES" == true ]]; then
  if [[ "$RESET_DATABASE" == true ]]; then
    echo "--reset-node-db-volumes is set; --reset-db will be ignored." >&2
  fi
  EXTRA_ARGS+=(
    -e "reset_node_db_volumes=true"
    -e "reset_node_db_volumes_confirmation=$RESET_NODE_DB_VOLUMES_CONFIRMATION"
  )
elif [[ "$RESET_DATABASE" == true ]]; then
  EXTRA_ARGS+=(-e "reset_database=true" -e "reset_database_confirmation=$RESET_CONFIRMATION")
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
