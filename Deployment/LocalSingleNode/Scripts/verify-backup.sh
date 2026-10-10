#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(bash "$SCRIPT_DIR/read-setting.sh" deploy_root)"
exec python3 "$SCRIPT_DIR/lib/backup.py" --config "$APP_ROOT/maintenance/settings.json" --verify "$@"
