#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
NODE_IP="$(python3 - "$SCRIPT_DIR/lib" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from machine import detect
from ls_settings import ETC
print(detect(ETC / 'localsinglenode/machine.yml')['ip'])
PY
)"
HTTP_PORT="$(bash "$SCRIPT_DIR/read-setting.sh" lan_http_port)"
python3 "$SCRIPT_DIR/lib/readiness.py" "http://$NODE_IP:$HTTP_PORT/health/ready"
pwsh -NoProfile -File "$REPO_ROOT/Scripts/Test-DeployedSite.ps1" -Address "$NODE_IP" -Port "$HTTP_PORT"
bash "$SCRIPT_DIR/public-acceptance-check.sh"
