#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
APP_NAME="$(bash "$SCRIPT_DIR/read-setting.sh" app_name)"
PUBLIC_URL="$(python3 - "$SCRIPT_DIR/lib" "$APP_NAME" <<'PY'
import json
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
from ls_settings import ETC
path = ETC / sys.argv[2] / "public.json"
if path.exists():
    data = json.loads(path.read_text())
    print("https://" + data["hostname"])
PY
)"
if [[ -z "$PUBLIC_URL" ]]; then
  echo 'Public acceptance: disabled for this LAN-only deployment'
  exit 0
fi
python3 "$SCRIPT_DIR/lib/readiness.py" "$PUBLIC_URL/health/ready"
exec pwsh -NoProfile -File "$REPO_ROOT/Scripts/Test-DeployedSite.ps1" -BaseUrl "$PUBLIC_URL"
