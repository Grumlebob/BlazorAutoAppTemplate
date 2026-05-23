#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
DEPLOY_ROOT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" deploy_root)"
BACKUP_ARG="${1:-latest}"

[[ -f "$INVENTORY" ]] || {
  echo "backup verification failed: missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
}

ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a \
  "DEPLOY_ROOT=$DEPLOY_ROOT BACKUP_ARG=$BACKUP_ARG bash -lc 'set -eu; cd \"\$DEPLOY_ROOT\"; if [ \"\$BACKUP_ARG\" = latest ]; then BACKUP=\"\$(ls -1t backups/*.sql.gz 2>/dev/null | head -n 1 || true)\"; else BACKUP=\"\$BACKUP_ARG\"; fi; [ -n \"\$BACKUP\" ] || { echo \"no backup files found\" >&2; exit 1; }; [ -f \"\$BACKUP\" ] || { echo \"backup file not found: \$BACKUP\" >&2; exit 1; }; [ -s \"\$BACKUP\" ] || { echo \"backup file is empty: \$BACKUP\" >&2; exit 1; }; gzip -t \"\$BACKUP\"; preview=\"\$(gzip -dc \"\$BACKUP\" | head -n 80)\"; printf \"%s\n\" \"\$preview\" | grep -Eq \"PostgreSQL database dump|SET \" || { echo \"backup does not look like a plain SQL pg_dump: \$BACKUP\" >&2; exit 1; }; ls -lh \"\$BACKUP\"; echo \"backup verification ok: \$BACKUP\"'"
