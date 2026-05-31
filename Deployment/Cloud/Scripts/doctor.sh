#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOFU_DIR="$REPO_ROOT/Deployment/Cloud/infra/opentofu"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
ENVIRONMENT_NAME="${CLOUD_GITHUB_ENVIRONMENT:-cloud-hetzner}"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/Component/lib/cloud-env.sh"
cloud_env_bootstrap_path

cd "$REPO_ROOT"

status_line() {
  local status="$1"
  local area="$2"
  local detail="$3"
  printf '%-8s %-18s %s\n' "$status" "$area" "$detail"
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

find_gh() {
  if has_command gh; then
    command -v gh
    return 0
  fi
  if has_command gh.exe; then
    command -v gh.exe
    return 0
  fi
  if [[ -x "/mnt/c/Program Files/GitHub CLI/gh.exe" ]]; then
    printf '%s\n' "/mnt/c/Program Files/GitHub CLI/gh.exe"
    return 0
  fi
  return 1
}

run_quiet() {
  "$@" >/dev/null 2>&1
}

setting() {
  python3 "$SCRIPT_DIR/Component/lib/read-cloud-setting.py" "$1" 2>/dev/null || true
}

short_sha() {
  local value="$1"
  if [[ ${#value} -ge 7 ]]; then
    printf '%s' "${value:0:7}"
  else
    printf '%s' "$value"
  fi
}

report_run() {
  local workflow="$1"
  local area="$2"
  local current_head="$3"

  local gh_bin="${GH_BIN:-}"

  if [[ -z "$gh_bin" ]]; then
    echo "ACTION|gh is missing; run setup-currentpc-tools.sh to report GitHub run state"
    return
  fi

  if ! "$gh_bin" auth status >/dev/null 2>&1; then
    echo "ACTION|gh is installed but not authenticated; run gh auth login"
    return
  fi

  local json
  if ! json="$("$gh_bin" run list --workflow "$workflow" --branch main --limit 1 --json databaseId,status,conclusion,headSha,createdAt,url 2>/dev/null)"; then
    echo "BLOCKER|could not read latest GitHub run for ${workflow}"
    return
  fi

  JSON_PAYLOAD="$json" CURRENT_HEAD="$current_head" WORKFLOW_NAME="$workflow" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["JSON_PAYLOAD"])
current_head = os.environ["CURRENT_HEAD"]
workflow = os.environ["WORKFLOW_NAME"]

if not payload:
    print(f"ACTION|no {workflow} runs found on main")
    raise SystemExit

run = payload[0]
run_id = run.get("databaseId", "unknown")
status = run.get("status", "unknown")
conclusion = run.get("conclusion") or "none"
head = run.get("headSha") or ""
head_short = head[:7] if head else "unknown"
url = run.get("url") or ""

prefix = "OK" if status == "completed" and conclusion == "success" else "BLOCKER"
detail = f"{workflow} run {run_id} {status}/{conclusion} at {head_short}"
if head and current_head and head != current_head:
    prefix = "WARN" if prefix == "OK" else prefix
    detail += f" (current HEAD is {current_head[:7]})"
if url:
    detail += f" {url}"
print(f"{prefix}|{detail}")
PY
}

report_github_run() {
  local workflow="$1"
  local area="$2"
  local current_head="$3"
  local output
  output="$(report_run "$workflow" "$area" "$current_head")"
  local status="${output%%|*}"
  local detail="${output#*|}"
  status_line "$status" "$area" "$detail"
}

public_probe() {
  local public_hostname="$1"
  if [[ -z "$public_hostname" ]]; then
    status_line "BLOCKER" "Public health" "public hostname could not be read"
    return
  fi

  local headers_file
  headers_file="$(mktemp)"
  trap 'rm -f "$headers_file"' RETURN

  local http_code
  local curl_rc=0
  http_code="$(curl -sS -D "$headers_file" -o /dev/null -w '%{http_code}' --max-time 15 "https://${public_hostname}/health/ready")" || curl_rc=$?

  if [[ "$curl_rc" -eq 0 && "$http_code" =~ ^[23][0-9][0-9]$ ]]; then
    status_line "OK" "Public health" "https://${public_hostname}/health/ready returned ${http_code}"
    return
  fi

  if grep -iq '^server:[[:space:]]*cloudflare' "$headers_file" && grep -iq '^cf-mitigated:[[:space:]]*challenge' "$headers_file"; then
    status_line "ACTION" "Public health" "Cloudflare challenged /health/ready from this machine; check Cloudflare security settings or verify in a browser"
    return
  fi

  status_line "BLOCKER" "Public health" "https://${public_hostname}/health/ready failed with curl=${curl_rc}, http=${http_code}"
}

check_github_environment() {
  local gh_bin="$1"
  local secrets_json

  secrets_json="$("$gh_bin" secret list --env "$ENVIRONMENT_NAME" --json name 2>/dev/null)" || return 1

  JSON_PAYLOAD="$secrets_json" python3 - <<'PY'
import json
import os
import sys

required = {
    "CLOUD_SSH_PRIVATE_KEY",
    "CLOUD_BASTION_HOST",
    "CLOUD_HETZNER_API_TOKEN",
    "CLOUD_TEMP_SSH_FIREWALL_ID",
    "CLOUD_GHCR_USERNAME",
    "CLOUD_GHCR_TOKEN",
    "CLOUD_POSTGRES_USER",
    "CLOUD_POSTGRES_PASSWORD",
    "CLOUD_POSTGRES_DB",
    "CLOUD_REDIS_PASSWORD",
    "CLOUD_CLOUDFLARE_TUNNEL_TOKEN",
}
payload = json.loads(os.environ["JSON_PAYLOAD"])
existing = {item.get("name") for item in payload if isinstance(item, dict)}
missing = sorted(required - existing)
if missing:
    print("\n".join(missing), file=sys.stderr)
    raise SystemExit(1)
PY
}

report_hcloud_resources() {
  local app_name="$1"
  local tmpdir
  local spec
  local name
  local path
  local url
  local failed=0
  local report

  if [[ -z "$app_name" ]]; then
    status_line "ACTION" "Hetzner billables" "app_name could not be read"
    return
  fi

  CLOUD_ENV_QUIET=1 cloud_env_load_hcloud_token
  if [[ -z "${HCLOUD_TOKEN:-}" ]]; then
    status_line "INFO" "Hetzner billables" "HCLOUD_TOKEN is not set; add .env.cloud to report matching resources"
    return
  fi

  if ! has_command curl || ! has_command python3; then
    status_line "ACTION" "Hetzner billables" "curl/python3 missing; run setup-currentpc-tools.sh"
    return
  fi

  tmpdir="$(mktemp -d)"
  for spec in \
    "servers|servers" \
    "primary_ips|primary_ips" \
    "floating_ips|floating_ips" \
    "volumes|volumes" \
    "load_balancers|load_balancers" \
    "images|images?type=snapshot"; do
    name="${spec%%|*}"
    path="${spec#*|}"
    if [[ "$path" == *\?* ]]; then
      url="https://api.hetzner.cloud/v1/${path}&per_page=50"
    else
      url="https://api.hetzner.cloud/v1/${path}?per_page=50"
    fi

    if ! curl -fsS -H "Authorization: Bearer ${HCLOUD_TOKEN}" "$url" > "$tmpdir/${name}.json"; then
      failed=1
      break
    fi
  done

  if ((failed)); then
    rm -rf "$tmpdir"
    status_line "ACTION" "Hetzner billables" "could not query Hetzner API; check HCLOUD_TOKEN"
    return
  fi

  report="$(APP_NAME="$app_name" RESOURCE_DIR="$tmpdir" python3 - <<'PY'
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path

app_name = os.environ["APP_NAME"]
resource_dir = Path(os.environ["RESOURCE_DIR"])
collections = {
    "servers": "servers",
    "primary_ips": "primary_ips",
    "floating_ips": "floating_ips",
    "volumes": "volumes",
    "load_balancers": "load_balancers",
    "images": "images",
}
node_names = {"cloud-main", "cloud-app1", "cloud-app2", "cloud-db"}


def matches(resource: dict) -> bool:
    labels = resource.get("labels") or {}
    name = str(resource.get("name") or "")
    return labels.get("app") == app_name or name.startswith(f"{app_name}-") or name in node_names


found: list[tuple[str, str, object]] = []
for file_name, key in collections.items():
    payload = json.loads((resource_dir / f"{file_name}.json").read_text(encoding="utf-8"))
    for resource in payload.get(key, []):
        if matches(resource):
            display = resource.get("name") or resource.get("ip") or resource.get("id")
            found.append((file_name, str(display), resource.get("id", "unknown")))

if found:
    counts = Counter(kind for kind, _, _ in found)
    summary = ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
    print(f"{len(found)} matching resources ({summary})")
    for kind, display, resource_id in found[:12]:
        print(f"  {kind}: {display} (id {resource_id})")
PY
)"
  rm -rf "$tmpdir"

  if [[ -n "$report" ]]; then
    status_line "WARN" "Hetzner billables" "$(head -n 1 <<< "$report")"
    tail -n +2 <<< "$report" | sed 's/^/                           /'
  else
    status_line "OK" "Hetzner billables" "no matching servers, IPs, volumes, load balancers, or snapshots found"
  fi
}

echo "Cloud deployment doctor"
echo

current_head="$(git rev-parse HEAD 2>/dev/null || true)"
public_hostname="$(setting public_hostname)"
GH_BIN="$(find_gh || true)"

if [[ -f Deployment/Cloud/HowToDeployCloud.md && -f Deployment/Common/release.yml ]] \
  && run_quiet bash ./Deployment/Common/Scripts/validate-common-release.sh; then
  status_line "OK" "Repo" "Cloud guide and shared release settings are present"
else
  status_line "BLOCKER" "Repo" "Cloud guide or shared release settings need attention"
fi

if SKIP_GH_AUTH_CHECK=1 bash ./Deployment/Cloud/Scripts/check-currentpc-tools.sh >/dev/null 2>&1; then
  status_line "OK" "CurrentPC tools" "required local tools are installed"
else
  status_line "ACTION" "CurrentPC tools" "run: bash ./Deployment/Cloud/Scripts/setup-currentpc-tools.sh"
fi

if run_quiet bash ./Deployment/Cloud/Scripts/validate-cloud-settings.sh; then
  status_line "OK" "Cloud settings" "group_vars/all.yml is valid"
else
  status_line "BLOCKER" "Cloud settings" "run validate-cloud-settings.sh and fix reported values"
fi

if [[ -f "$TOFU_DIR/terraform.tfstate" ]]; then
  status_line "OK" "OpenTofu state" "local state exists at Deployment/Cloud/infra/opentofu/terraform.tfstate"
else
  status_line "WAIT" "OpenTofu state" "run Step 7 apply before provisioning or GitHub secret configuration"
fi

report_hcloud_resources "$(setting app_name)"

if [[ -f "$INVENTORY" ]]; then
  if ! has_command ansible-inventory; then
    status_line "ACTION" "Inventory" "hosts.yml exists, but ansible-inventory is missing; run setup-currentpc-tools.sh to validate it"
  elif run_quiet bash ./Deployment/Cloud/Scripts/validate-rendered-inventory.sh; then
    status_line "OK" "Inventory" "rendered inventory exists and validates"
  else
    status_line "BLOCKER" "Inventory" "rerender and validate Deployment/Cloud/inventory/prod/hosts.yml"
  fi
else
  status_line "WAIT" "Inventory" "run render-inventory-from-tofu.sh after OpenTofu apply"
fi

if [[ -n "$GH_BIN" ]] && "$GH_BIN" auth status >/dev/null 2>&1; then
  if check_github_environment "$GH_BIN"; then
    status_line "OK" "GitHub env" "${ENVIRONMENT_NAME} contains required secrets"
  else
    status_line "BLOCKER" "GitHub env" "run configure-github-environment.sh, then check-github-environment.sh"
  fi
else
  status_line "ACTION" "GitHub env" "gh is missing or not authenticated; run setup-currentpc-tools.sh or gh auth login"
fi

GH_BIN="$GH_BIN" report_github_run "CI" "Latest CI" "$current_head"
GH_BIN="$GH_BIN" report_github_run "CD - Cloud" "Latest Cloud CD" "$current_head"

if has_command curl; then
  public_probe "$public_hostname"
else
  status_line "ACTION" "Public health" "curl is missing; run setup-currentpc-tools.sh"
fi

if [[ "${CLOUD_DOCTOR_RUN_ACCEPTANCE:-0}" == "1" ]]; then
  if bash ./Deployment/Cloud/Scripts/acceptance-check.sh; then
    status_line "OK" "Acceptance" "acceptance-check.sh passed"
  else
    status_line "BLOCKER" "Acceptance" "acceptance-check.sh failed"
  fi
else
  status_line "INFO" "Acceptance" "set CLOUD_DOCTOR_RUN_ACCEPTANCE=1 to run full Ansible acceptance"
fi
