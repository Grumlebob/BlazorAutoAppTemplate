#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage:
  quick-destroy-cloud.sh [--plan-only]
  quick-destroy-cloud.sh --confirm "destroy bookscloud"

Destroys the OpenTofu-owned Hetzner Cloud stack so billable Cloud resources stop.

Safety:
  - requires local OpenTofu state
  - creates a state backup before destroy
  - destroys disposable Cloud app data and observability metrics/logs/traces
  - removes only the generated Cloud inventory after successful destroy
  - never deletes unmanaged Hetzner resources through the API
USAGE
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOFU_DIR="$REPO_ROOT/Deployment/Cloud/infra/opentofu"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
APP_NAME="$(bash "$SCRIPT_DIR/read-cloud-setting.sh" app_name)"
CONFIRM_PHRASE="destroy ${APP_NAME}"
STATE_BACKUP_DIR="${CLOUD_STATE_BACKUP_DIR:-$HOME/.local/state/${APP_NAME}}"

PLAN_ONLY=0
CONFIRM_VALUE=""

fail() {
  echo "quick destroy cloud failed: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan-only)
      PLAN_ONLY=1
      shift
      ;;
    --confirm)
      [[ $# -ge 2 ]] || usage
      CONFIRM_VALUE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

confirm_destroy() {
  if [[ "$PLAN_ONLY" == "1" ]]; then
    echo "Plan-only mode. No Hetzner resources were destroyed."
    echo "To destroy after reviewing the plan, rerun:"
    echo "  bash ./Deployment/Cloud/Scripts/quick-destroy-cloud.sh --confirm \"${CONFIRM_PHRASE}\""
    exit 0
  fi

  if [[ "$CONFIRM_VALUE" != "$CONFIRM_PHRASE" && -t 0 ]]; then
    echo
    echo "This will destroy the OpenTofu-owned ${APP_NAME} Hetzner Cloud stack."
    echo "Type exactly '${CONFIRM_PHRASE}' to continue:"
    read -r CONFIRM_VALUE
  fi

  [[ "$CONFIRM_VALUE" == "$CONFIRM_PHRASE" ]] || fail "confirmation did not match '${CONFIRM_PHRASE}'. No resources were destroyed."
}

backup_state() {
  local label="$1"
  local timestamp
  local destination

  [[ -f "$TOFU_DIR/terraform.tfstate" ]] || return 0

  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$STATE_BACKUP_DIR"
  chmod 700 "$STATE_BACKUP_DIR"
  destination="$STATE_BACKUP_DIR/terraform.tfstate.${label}.${timestamp}"
  cp "$TOFU_DIR/terraform.tfstate" "$destination"
  chmod 600 "$destination"
  echo "backed up OpenTofu state: ${destination}"
}

api_get() {
  local path="$1"
  curl -fsS \
    -H "Authorization: Bearer ${HCLOUD_TOKEN}" \
    "https://api.hetzner.cloud/v1/${path}"
}

print_matching_hcloud_resources() {
  local heading="$1"
  local tmpdir

  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' RETURN

  if ! api_get servers > "$tmpdir/servers.json"; then
    printf '{"servers":[]}\n' > "$tmpdir/servers.json"
    echo "warning: could not query Hetzner servers for the resource report" >&2
  fi
  if ! api_get primary_ips > "$tmpdir/primary_ips.json"; then
    printf '{"primary_ips":[]}\n' > "$tmpdir/primary_ips.json"
    echo "warning: could not query Hetzner primary_ips for the resource report" >&2
  fi
  if ! api_get floating_ips > "$tmpdir/floating_ips.json"; then
    printf '{"floating_ips":[]}\n' > "$tmpdir/floating_ips.json"
    echo "warning: could not query Hetzner floating_ips for the resource report" >&2
  fi
  if ! api_get volumes > "$tmpdir/volumes.json"; then
    printf '{"volumes":[]}\n' > "$tmpdir/volumes.json"
    echo "warning: could not query Hetzner volumes for the resource report" >&2
  fi
  if ! api_get load_balancers > "$tmpdir/load_balancers.json"; then
    printf '{"load_balancers":[]}\n' > "$tmpdir/load_balancers.json"
    echo "warning: could not query Hetzner load_balancers for the resource report" >&2
  fi

  APP_NAME="$APP_NAME" RESOURCE_DIR="$tmpdir" HEADING="$heading" python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

app_name = os.environ["APP_NAME"]
resource_dir = Path(os.environ["RESOURCE_DIR"])
heading = os.environ["HEADING"]

collections = {
    "servers": "servers",
    "primary_ips": "primary_ips",
    "floating_ips": "floating_ips",
    "volumes": "volumes",
    "load_balancers": "load_balancers",
}


def matches(resource: dict) -> bool:
    labels = resource.get("labels") or {}
    name = str(resource.get("name") or "")
    return (
        labels.get("app") == app_name
        or name.startswith(f"{app_name}-")
        or name in {"cloud-main", "cloud-app1", "cloud-app2", "cloud-db"}
    )


found: list[str] = []
for file_name, key in collections.items():
    payload = json.loads((resource_dir / f"{file_name}.json").read_text(encoding="utf-8"))
    for resource in payload.get(key, []):
        if matches(resource):
            name = resource.get("name") or resource.get("ip") or resource.get("id")
            found.append(f"  {file_name}: {name} (id {resource.get('id', 'unknown')})")

print(heading)
if found:
    print("\n".join(found))
else:
    print(f"  no Hetzner Cloud resources matching {app_name} labels or node names")
PY
}

require_command curl
require_command jq
require_command python3
require_command tofu

[[ -n "${HCLOUD_TOKEN:-}" ]] || fail "HCLOUD_TOKEN is required in this shell."
[[ -f "$TOFU_DIR/terraform.tfstate" ]] || fail "missing OpenTofu state: Deployment/Cloud/infra/opentofu/terraform.tfstate"

cd "$REPO_ROOT"
bash "$SCRIPT_DIR/check-hcloud-token.sh"

if [[ ! -f "$TOFU_DIR/terraform.tfvars" ]]; then
  echo "terraform.tfvars is missing; recreating local variables from the committed example."
  bash "$SCRIPT_DIR/prepare-opentofu-tfvars.sh"
fi

print_matching_hcloud_resources "Matching Hetzner resources before destroy:"
echo
echo "Data loss note:"
echo "  Cloud PostgreSQL/Redis data and Cloud observability metrics/logs/traces live on the servers being destroyed."
echo "  GitHub environment secrets and LocalCluster data are not destroyed by this script."
backup_state "pre-destroy"

cd "$TOFU_DIR"
tofu init -input=false
tofu validate
tofu plan -destroy -out destroy-cloud.tfplan -input=false

confirm_destroy

tofu apply -input=false destroy-cloud.tfplan
backup_state "post-destroy"
rm -f destroy-cloud.tfplan

rm -f "$INVENTORY"
echo "removed generated inventory: Deployment/Cloud/inventory/prod/hosts.yml"

print_matching_hcloud_resources "Matching Hetzner resources after destroy:"

echo
echo "Cloud destroy complete."
echo "GitHub environment secrets are intentionally left in place; recreate refreshes changed IP values."
