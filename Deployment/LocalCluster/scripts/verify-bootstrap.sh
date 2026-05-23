#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/status.sh" bootstrap
bash "$SCRIPT_DIR/preflight.sh" bootstrap
bash "$SCRIPT_DIR/support/ping-fresh-machines.sh"

echo
echo "bootstrap verification ok"
