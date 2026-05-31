#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOFU_DIR="$REPO_ROOT/Deployment/Cloud/infra/opentofu"
APP_NAME="$(bash "$SCRIPT_DIR/read-cloud-setting.sh" app_name)"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/Component/lib/cloud-env.sh"
cloud_env_bootstrap_path

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

cloud_env_load_hcloud_token
if [[ -z "${CLOUD_HETZNER_API_TOKEN:-}" && -n "${HCLOUD_TOKEN:-}" ]]; then
  export CLOUD_HETZNER_API_TOKEN="$HCLOUD_TOKEN"
  echo "using HCLOUD_TOKEN as CLOUD_HETZNER_API_TOKEN"
fi

if [[ -z "${CLOUD_TEMP_SSH_FIREWALL_ID:-}" && -f "$TOFU_DIR/terraform.tfstate" ]] && command -v tofu >/dev/null 2>&1; then
  CLOUD_TEMP_SSH_FIREWALL_ID="$(cd "$TOFU_DIR" && tofu output -raw cloud_temp_ssh_firewall_id 2>/dev/null || true)"
  if [[ -n "$CLOUD_TEMP_SSH_FIREWALL_ID" ]]; then
    export CLOUD_TEMP_SSH_FIREWALL_ID
    echo "loaded CLOUD_TEMP_SSH_FIREWALL_ID from OpenTofu state"
  fi
fi

: "${CLOUD_HETZNER_API_TOKEN:?CLOUD_HETZNER_API_TOKEN is required}"
: "${CLOUD_TEMP_SSH_FIREWALL_ID:?CLOUD_TEMP_SSH_FIREWALL_ID is required}"

PAYLOAD_FILE="$(mktemp "${RUNNER_TEMP:-/tmp}/${APP_NAME}-firewall.XXXXXX.json")"
cleanup() {
  rm -f "$PAYLOAD_FILE"
}
trap cleanup EXIT

wait_for_action() {
  local action_id="$1"
  local timeout_seconds="${HCLOUD_ACTION_WAIT_SECONDS:-120}"
  local deadline=$((SECONDS + timeout_seconds))
  local response
  local status

  while ((SECONDS < deadline)); do
    response="$(curl -fsS \
      -H "Authorization: Bearer ${CLOUD_HETZNER_API_TOKEN}" \
      "https://api.hetzner.cloud/v1/actions/${action_id}")"
    status="$(python3 -c 'import json, sys; print(json.load(sys.stdin).get("action", {}).get("status", ""))' <<< "$response")"

    case "$status" in
      success)
        return 0
        ;;
      error)
        echo "Hetzner firewall action ${action_id} failed:" >&2
        python3 -m json.tool <<< "$response" >&2 || printf '%s\n' "$response" >&2
        return 1
        ;;
      running|"")
        sleep 2
        ;;
      *)
        echo "Hetzner firewall action ${action_id} has unexpected status: ${status}" >&2
        sleep 2
        ;;
    esac
  done

  echo "timed out waiting for Hetzner firewall action ${action_id}" >&2
  return 1
}

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

RESPONSE="$(curl -fsS \
  -X POST \
  -H "Authorization: Bearer ${CLOUD_HETZNER_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data-binary "@${PAYLOAD_FILE}" \
  "https://api.hetzner.cloud/v1/firewalls/${CLOUD_TEMP_SSH_FIREWALL_ID}/actions/set_rules")"

mapfile -t ACTION_IDS < <(python3 -c '
import json
import sys

payload = json.load(sys.stdin)
ids = []
if isinstance(payload.get("action"), dict) and payload["action"].get("id") is not None:
    ids.append(str(payload["action"]["id"]))
for action in payload.get("actions", []):
    if isinstance(action, dict) and action.get("id") is not None:
        ids.append(str(action["id"]))
print("\n".join(ids))
' <<< "$RESPONSE")

if ((${#ACTION_IDS[@]} == 0)); then
  echo "Hetzner firewall update did not return an action id:" >&2
  python3 -m json.tool <<< "$RESPONSE" >&2 || printf '%s\n' "$RESPONSE" >&2
  exit 1
fi

for action_id in "${ACTION_IDS[@]}"; do
  wait_for_action "$action_id"
done

if [[ "$ACTION" == "allow" ]]; then
  # Give SSH connection tracking a short propagation buffer after the API action is complete.
  sleep 3
fi
