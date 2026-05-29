#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage:
  set-temporary-ssh-firewall.sh allow <cidr>
  set-temporary-ssh-firewall.sh clear

Required environment:
  CLOUD_HETZNER_API_TOKEN
  CLOUD_TEMP_SSH_FIREWALL_ID
USAGE
  exit 1
}

[[ $# -ge 1 ]] || usage
ACTION="$1"
CIDR="${2:-}"

: "${CLOUD_HETZNER_API_TOKEN:?CLOUD_HETZNER_API_TOKEN is required}"
: "${CLOUD_TEMP_SSH_FIREWALL_ID:?CLOUD_TEMP_SSH_FIREWALL_ID is required}"

PAYLOAD_FILE="$(mktemp "${RUNNER_TEMP:-/tmp}/bookscloud-firewall.XXXXXX.json")"
cleanup() {
  rm -f "$PAYLOAD_FILE"
}
trap cleanup EXIT

case "$ACTION" in
  allow)
    [[ -n "$CIDR" ]] || usage
    python3 - "$CIDR" > "$PAYLOAD_FILE" <<'PY'
import json
import sys

cidr = sys.argv[1]
payload = {
    "rules": [
        {
            "direction": "in",
            "protocol": "tcp",
            "port": "22",
            "source_ips": [cidr],
            "description": "Temporary GitHub runner SSH to cloud-main",
        }
    ]
}
print(json.dumps(payload))
PY
    ;;
  clear)
    printf '{"rules":[]}\n' > "$PAYLOAD_FILE"
    ;;
  *)
    usage
    ;;
esac

curl -fsS \
  -X POST \
  -H "Authorization: Bearer ${CLOUD_HETZNER_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data-binary "@${PAYLOAD_FILE}" \
  "https://api.hetzner.cloud/v1/firewalls/${CLOUD_TEMP_SSH_FIREWALL_ID}/actions/set_rules" \
  >/dev/null

if [[ "$ACTION" == "allow" ]]; then
  sleep 10
fi
