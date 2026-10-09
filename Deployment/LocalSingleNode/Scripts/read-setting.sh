#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "$SCRIPT_DIR/lib" "$@" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from ls_settings import print_setting
if len(sys.argv) != 3:
    raise SystemExit("Usage: read-setting.sh <key>")
try:
    print_setting(sys.argv[2])
except (ValueError, OSError) as error:
    raise SystemExit(str(error))
PY
