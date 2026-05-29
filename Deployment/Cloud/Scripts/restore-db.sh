#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
usage: $0 <remote-backup-path>.sql.gz --confirm <app-name>/<database-name>

Example:
  $0 /opt/bookscloud/backups/predeploy-20260529T120000Z.sql.gz --confirm bookscloud/bookscloud
USAGE
}

if [[ "${1:-}" == "--help" || $# -eq 0 ]]; then
  usage
  exit 0
fi

[[ $# -eq 3 && "$2" == "--confirm" ]] || {
  usage >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

DEPLOY_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" deploy_root)"
BACKUP_PATH="$1"
CONFIRMATION="$3"

[[ -f "$INVENTORY" ]] || {
  echo "restore failed: missing inventory: Deployment/Cloud/inventory/prod/hosts.yml" >&2
  exit 1
}

case "$BACKUP_PATH" in
  "$DEPLOY_ROOT"/backups/*.sql.gz) ;;
  *)
    echo "restore failed: backup path must be under ${DEPLOY_ROOT}/backups and end with .sql.gz" >&2
    exit 1
    ;;
esac

ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && ./restore-db.sh '${BACKUP_PATH}' --confirm '${CONFIRMATION}'"
