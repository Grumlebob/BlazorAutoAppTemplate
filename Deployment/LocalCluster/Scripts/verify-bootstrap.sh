#!/usr/bin/env bash
set -euo pipefail

if command -v realpath >/dev/null 2>&1; then
  SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
else
  SCRIPT_PATH="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
fi
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"

for required_file in \
  "$SCRIPT_DIR/status.sh" \
  "$SCRIPT_DIR/preflight.sh" \
  "${SCRIPT_DIR}/Component/ping-fresh-machines.sh"; do
  if [[ ! -f "$required_file" ]]; then
    echo "bootstrap verification failed: missing required script: $required_file" >&2
    echo "Resolved verify-bootstrap.sh path: $SCRIPT_PATH" >&2
    echo "Resolved scripts directory: $SCRIPT_DIR" >&2
    echo "Current directory: $(pwd)" >&2
    echo "This usually means the repository checkout is stale or incomplete." >&2
    echo "From the repository root on the control machine, run: git pull --ff-only" >&2
    echo "If this is not a full repository checkout, clone the repository again before running verify-bootstrap.sh." >&2
    exit 1
  fi
done

bash "$SCRIPT_DIR/status.sh" bootstrap
bash "${SCRIPT_DIR}/Component/ping-fresh-machines.sh"

echo
echo "bootstrap verification ok"
