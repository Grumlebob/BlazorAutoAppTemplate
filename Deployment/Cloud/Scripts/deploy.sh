#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <git-sha-image-tag> [--migrate <path-to-migration-bundle>]" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

[[ $# -ge 1 ]] || usage

APP_VERSION="$1"
shift
RUN_MIGRATIONS="false"
MIGRATION_BUNDLE_LOCAL_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --migrate)
      [[ $# -ge 2 ]] || usage
      [[ -f "$2" ]] || {
        echo "migration bundle not found: $2" >&2
        exit 1
      }
      MIGRATION_BUNDLE_LOCAL_PATH="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
      RUN_MIGRATIONS="true"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "missing required environment variable: $name" >&2
    exit 1
  fi
}

require_env CLOUD_GHCR_USERNAME
require_env CLOUD_GHCR_TOKEN
require_env CLOUD_POSTGRES_USER
require_env CLOUD_POSTGRES_PASSWORD
require_env CLOUD_POSTGRES_DB
require_env CLOUD_REDIS_PASSWORD
require_env CLOUD_CLOUDFLARE_TUNNEL_TOKEN

SOURCE_REPO_URL="${SOURCE_REPO_URL:-$(git -C "$REPO_ROOT" config --get remote.origin.url || true)}"
[[ -n "$SOURCE_REPO_URL" ]] || SOURCE_REPO_URL="unknown"

EXTRA_VARS_FILE="$(mktemp "${RUNNER_TEMP:-/tmp}/bookscloud-extra-vars.XXXXXX.json")"
cleanup() {
  rm -f "$EXTRA_VARS_FILE"
}
trap cleanup EXIT

APP_VERSION="$APP_VERSION" \
RUN_MIGRATIONS="$RUN_MIGRATIONS" \
MIGRATION_BUNDLE_LOCAL_PATH="$MIGRATION_BUNDLE_LOCAL_PATH" \
SOURCE_REPO_URL="$SOURCE_REPO_URL" \
python3 - "$EXTRA_VARS_FILE" <<'PY'
import json
import os
import sys


def env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


payload = {
    "app_version": env("APP_VERSION"),
    "source_repo_url": env("SOURCE_REPO_URL"),
    "run_migrations": os.environ.get("RUN_MIGRATIONS") == "true",
    "cloud_ghcr_username": env("CLOUD_GHCR_USERNAME"),
    "cloud_ghcr_token": env("CLOUD_GHCR_TOKEN"),
    "cloud_postgres_user": env("CLOUD_POSTGRES_USER"),
    "cloud_postgres_password": env("CLOUD_POSTGRES_PASSWORD"),
    "cloud_postgres_db": env("CLOUD_POSTGRES_DB"),
    "cloud_redis_password": env("CLOUD_REDIS_PASSWORD"),
    "cloud_cloudflare_tunnel_token": env("CLOUD_CLOUDFLARE_TUNNEL_TOKEN"),
}

migration_bundle = os.environ.get("MIGRATION_BUNDLE_LOCAL_PATH", "")
if payload["run_migrations"]:
    if not migration_bundle:
        raise SystemExit("MIGRATION_BUNDLE_LOCAL_PATH is required when RUN_MIGRATIONS=true")
    payload["migration_bundle_local_path"] = migration_bundle

with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY

chmod 0600 "$EXTRA_VARS_FILE"

bash "$SCRIPT_DIR/preflight.sh" deploy
cd "$REPO_ROOT/Deployment/Cloud/ansible"
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/deploy.yml -e "@$EXTRA_VARS_FILE"
