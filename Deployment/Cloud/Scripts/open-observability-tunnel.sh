#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"

GRAFANA_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_grafana_port)"
SSH_KEY="${CLOUD_SSH_PRIVATE_KEY_PATH:-$HOME/.ssh/bookscloud_deploy}"

fail() {
  echo "open Cloud observability tunnel failed: $*" >&2
  exit 1
}

command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml"
[[ -f "$SSH_KEY" ]] || fail "missing SSH key: $SSH_KEY"

BASTION_HOST="$(ansible-inventory -i "$INVENTORY" --host cloud-main | python3 -c 'import json, sys; payload = json.load(sys.stdin); print(payload.get("cloud_public_ipv4", "") or payload.get("ansible_host", ""))' 2>/dev/null || true)"
if [[ -z "$BASTION_HOST" ]]; then
  BASTION_HOST="$(grep -A4 'cloud-main:' "$INVENTORY" | awk '/ansible_host:/ {print $2; exit}')"
fi
[[ -n "$BASTION_HOST" ]] || fail "could not read cloud-main public address from inventory"

cat <<EOF
Opening Cloud Grafana tunnel.

Browse to:
  http://127.0.0.1:${GRAFANA_PORT}

Leave this command running while you use Grafana. Press Ctrl+C to close it.
EOF

ssh \
  -i "$SSH_KEY" \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=accept-new \
  -L "127.0.0.1:${GRAFANA_PORT}:127.0.0.1:${GRAFANA_PORT}" \
  "deploy@${BASTION_HOST}"
