#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

LOCAL_PORT="${1:-3000}"
GRAFANA_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_grafana_port)"
APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_name)"

[[ -f "$INVENTORY" ]] || {
  echo "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
}

if [[ -n "${CONTROLPC_SSH_TARGET:-}" ]]; then
  echo "Opening Grafana tunnel through ControlPC: http://127.0.0.1:${LOCAL_PORT}"
  echo "Press Ctrl+C to close the tunnel."
  exec ssh -N -L "${LOCAL_PORT}:127.0.0.1:${GRAFANA_PORT}" "$CONTROLPC_SSH_TARGET"
fi

NODE_MAIN_HOST="$(python3 - "$INVENTORY" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r"node-main:\s*\n\s*ansible_host:\s*([^\s]+)", text)
if not match:
    raise SystemExit("could not find node-main ansible_host in inventory")
print(match.group(1))
PY
)"

ANSIBLE_USER="$(python3 - "$INVENTORY" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r"ansible_user:\s*([^\s]+)", text)
print(match.group(1) if match else "deploy")
PY
)"

SSH_KEY="$HOME/.ssh/${APP_NAME}_deploy"
[[ -f "$SSH_KEY" ]] || {
  echo "missing SSH key: $SSH_KEY" >&2
  exit 1
}

echo "Opening Grafana tunnel: http://127.0.0.1:${LOCAL_PORT}"
echo "Press Ctrl+C to close the tunnel."
exec ssh -i "$SSH_KEY" -N -L "${LOCAL_PORT}:127.0.0.1:${GRAFANA_PORT}" "${ANSIBLE_USER}@${NODE_MAIN_HOST}"
