#!/usr/bin/env bash
set -euo pipefail
# The operator runs this command on the target. Agents never invoke it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/lib/platform_check.py"
exec python3 "$SCRIPT_DIR/lib/bootstrap.py" "$@"
