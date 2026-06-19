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
  CLOUD_TEMP_SSH_FIREWALL_ID, or an OpenTofu state/API-resolvable temporary SSH firewall
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

: "${CLOUD_HETZNER_API_TOKEN:?CLOUD_HETZNER_API_TOKEN is required}"

PAYLOAD_FILE="$(mktemp "${RUNNER_TEMP:-/tmp}/${APP_NAME}-firewall.XXXXXX.json")"
cleanup() {
  rm -f "$PAYLOAD_FILE"
}
trap cleanup EXIT

hcloud_firewall_exists() {
  local firewall_id="$1"
  local response_file
  local http_status

  [[ -n "$firewall_id" ]] || return 1

  response_file="$(mktemp "${RUNNER_TEMP:-/tmp}/${APP_NAME}-firewall-lookup.XXXXXX.json")"
  http_status="$(curl -sS \
    -o "$response_file" \
    -w '%{http_code}' \
    -H "Authorization: Bearer ${CLOUD_HETZNER_API_TOKEN}" \
    "https://api.hetzner.cloud/v1/firewalls/${firewall_id}" || true)"

  case "$http_status" in
    200)
      rm -f "$response_file"
      return 0
      ;;
    404)
      rm -f "$response_file"
      return 1
      ;;
    *)
      echo "Hetzner firewall lookup returned HTTP ${http_status}." >&2
      python3 -m json.tool "$response_file" >&2 || cat "$response_file" >&2
      rm -f "$response_file"
      return 2
      ;;
  esac
}

read_firewall_id_from_state() {
  [[ -f "$TOFU_DIR/terraform.tfstate" ]] || return 1

  python3 - "$TOFU_DIR/terraform.tfstate" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as state_file:
    state = json.load(state_file)

output = state.get("outputs", {}).get("cloud_temp_ssh_firewall_id", {})
value = output.get("value")
if value:
    print(value)
    raise SystemExit(0)

for resource in state.get("resources", []):
    if resource.get("type") != "hcloud_firewall" or resource.get("name") != "temporary_ssh":
        continue
    for instance in resource.get("instances", []):
        value = instance.get("attributes", {}).get("id")
        if value:
            print(value)
            raise SystemExit(0)

raise SystemExit(1)
PY
}

find_firewall_id_by_api() {
  local response_file

  response_file="$(mktemp "${RUNNER_TEMP:-/tmp}/${APP_NAME}-firewalls.XXXXXX.json")"
  if ! curl -fsS \
    -H "Authorization: Bearer ${CLOUD_HETZNER_API_TOKEN}" \
    "https://api.hetzner.cloud/v1/firewalls?per_page=50" \
    -o "$response_file"; then
    rm -f "$response_file"
    return 1
  fi

  python3 - "$APP_NAME" "$response_file" <<'PY'
import json
import sys

app_name = sys.argv[1]
response_path = sys.argv[2]
expected_name = f"{app_name}-temporary-ssh"

with open(response_path, encoding="utf-8") as response_file:
    payload = json.load(response_file)

exact_matches = []
role_matches = []
for firewall in payload.get("firewalls", []):
    labels = firewall.get("labels") or {}
    firewall_id = firewall.get("id")
    if firewall_id is None:
        continue

    name_matches = firewall.get("name") == expected_name
    labels_match = (
        labels.get("app") == app_name
        and labels.get("deployment") == "cloud"
        and labels.get("managed_by") == "opentofu"
        and labels.get("role") == "temporary-ssh"
    )
    if name_matches or labels_match:
        exact_matches.append(str(firewall_id))
        continue

    legacy_role_match = (
        labels.get("deployment") == "cloud"
        and labels.get("managed_by") == "opentofu"
        and labels.get("role") == "temporary-ssh"
    )
    legacy_name_match = str(firewall.get("name", "")).endswith("-temporary-ssh")
    if legacy_role_match or legacy_name_match:
        role_matches.append(str(firewall_id))

if len(exact_matches) == 1:
    print(exact_matches[0])
    raise SystemExit(0)

if len(exact_matches) > 1:
    print(
        f"Expected one temporary SSH firewall for {app_name}, found {len(exact_matches)}.",
        file=sys.stderr,
    )
    raise SystemExit(1)

if len(role_matches) == 1:
    print(role_matches[0])
    raise SystemExit(0)

if len(role_matches) > 1:
    print(
        f"Expected one legacy temporary SSH firewall, found {len(role_matches)}.",
        file=sys.stderr,
    )

raise SystemExit(1)
PY
  local status=$?
  rm -f "$response_file"
  return "$status"
}

resolve_firewall_id() {
  local candidate

  if [[ -n "${CLOUD_TEMP_SSH_FIREWALL_ID:-}" ]]; then
    if hcloud_firewall_exists "$CLOUD_TEMP_SSH_FIREWALL_ID"; then
      return 0
    fi
    echo "Configured CLOUD_TEMP_SSH_FIREWALL_ID was not found; resolving ${APP_NAME}-temporary-ssh." >&2
  fi

  candidate="$(read_firewall_id_from_state || true)"
  if [[ -n "$candidate" ]] && hcloud_firewall_exists "$candidate"; then
    CLOUD_TEMP_SSH_FIREWALL_ID="$candidate"
    export CLOUD_TEMP_SSH_FIREWALL_ID
    echo "resolved CLOUD_TEMP_SSH_FIREWALL_ID from OpenTofu state"
    return 0
  fi

  candidate="$(find_firewall_id_by_api || true)"
  if [[ -n "$candidate" ]] && hcloud_firewall_exists "$candidate"; then
    CLOUD_TEMP_SSH_FIREWALL_ID="$candidate"
    export CLOUD_TEMP_SSH_FIREWALL_ID
    echo "resolved CLOUD_TEMP_SSH_FIREWALL_ID from Hetzner firewall name/labels"
    return 0
  fi

  return 1
}

if ! resolve_firewall_id; then
  echo "::warning::Could not resolve ${APP_NAME}-temporary-ssh; relying on existing cloud-main SSH ingress."
  exit 0
fi

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
