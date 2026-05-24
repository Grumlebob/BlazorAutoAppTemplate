#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for required_file in \
  "$SCRIPT_DIR/status.sh" \
  "$SCRIPT_DIR/preflight.sh" \
  "$SCRIPT_DIR/support/ping-fresh-machines.sh"; do
  if [[ ! -f "$required_file" ]]; then
    echo "bootstrap verification failed: missing required script: $required_file" >&2
    echo "This usually means the repository checkout is stale or incomplete." >&2
    echo "From the repository root on the control machine, run: git pull --ff-only" >&2
    echo "If this is not a full repository checkout, clone the repository again before running verify-bootstrap.sh." >&2
    exit 1
  fi
done

bash "$SCRIPT_DIR/status.sh" bootstrap
bash "$SCRIPT_DIR/preflight.sh" bootstrap
bash "$SCRIPT_DIR/support/ping-fresh-machines.sh"

echo
echo "bootstrap verification ok"
