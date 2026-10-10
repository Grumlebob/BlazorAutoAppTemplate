#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="$(bash "$SCRIPT_DIR/read-setting.sh" app_name)"
# The backup service takes the same lock. Wait outside the maintenance lock.
case "${1:-}" in
  --backup-now)
    requested="$(date -u +%FT%T.%NZ)"
    sudo -n systemctl start --wait "$APP_NAME-backup.service"
    APP_ROOT="$(bash "$SCRIPT_DIR/read-setting.sh" deploy_root)"
    python3 "$SCRIPT_DIR/lib/backup.py" --config "$APP_ROOT/maintenance/settings.json" --report-fresh-since "$requested"
    ;;
  "") ;;
  *) echo 'Usage: run-maintenance.sh [--backup-now]' >&2; exit 2 ;;
esac
exec bash "$SCRIPT_DIR/../../Common/Scripts/with-deploy-lock.sh"   bash "$SCRIPT_DIR/maintenance-under-lock.sh"
