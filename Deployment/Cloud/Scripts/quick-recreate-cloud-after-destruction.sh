#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage:
  quick-recreate-cloud-after-destruction.sh [options]

Options:
  --plan-only                         Create and review the OpenTofu plan without applying it.
  --confirm "recreate bookscloud"     Apply the OpenTofu plan without interactive confirmation.
  --run-migrations true|false         Value passed to CD - Cloud when dispatching. Default: true.
  --skip-github-env                   Do not refresh GitHub environment secrets.
  --skip-provision                    Do not run local Ansible provisioning after recreate.
  --skip-cd                           Do not dispatch CD - Cloud after recreate.
  --no-watch-cd                       Dispatch CD - Cloud, but do not wait for it to finish.

Recreates the Hetzner Cloud stack after quick-destroy-cloud.sh, refreshes generated
inventory and GitHub environment secrets, provisions the nodes, then dispatches CD - Cloud.
USAGE
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOFU_DIR="$REPO_ROOT/Deployment/Cloud/infra/opentofu"
APP_NAME="$(bash "$SCRIPT_DIR/read-cloud-setting.sh" app_name)"
CONFIRM_PHRASE="recreate ${APP_NAME}"
STATE_BACKUP_DIR="${CLOUD_STATE_BACKUP_DIR:-$HOME/.local/state/${APP_NAME}}"
SSH_PRIVATE_KEY="${CLOUD_SSH_PRIVATE_KEY_PATH:-$HOME/.ssh/bookscloud_deploy}"

PLAN_ONLY=0
CONFIRM_VALUE=""
RUN_MIGRATIONS="true"
SKIP_GITHUB_ENV=0
SKIP_PROVISION=0
SKIP_CD=0
WATCH_CD=1

fail() {
  echo "quick recreate cloud failed: $*" >&2
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
    --run-migrations)
      [[ $# -ge 2 ]] || usage
      RUN_MIGRATIONS="$2"
      [[ "$RUN_MIGRATIONS" == "true" || "$RUN_MIGRATIONS" == "false" ]] || usage
      shift 2
      ;;
    --skip-github-env)
      SKIP_GITHUB_ENV=1
      shift
      ;;
    --skip-provision)
      SKIP_PROVISION=1
      shift
      ;;
    --skip-cd)
      SKIP_CD=1
      shift
      ;;
    --no-watch-cd)
      WATCH_CD=0
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

confirm_recreate() {
  if [[ "$PLAN_ONLY" == "1" ]]; then
    echo "Plan-only mode. No Hetzner resources were created or changed."
    echo "To recreate after reviewing the plan, rerun:"
    echo "  bash ./Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh --confirm \"${CONFIRM_PHRASE}\""
    exit 0
  fi

  if [[ "$CONFIRM_VALUE" != "$CONFIRM_PHRASE" && -t 0 ]]; then
    echo
    echo "This will create billable Hetzner Cloud resources for ${APP_NAME}."
    echo "Type exactly '${CONFIRM_PHRASE}' to continue:"
    read -r CONFIRM_VALUE
  fi

  [[ "$CONFIRM_VALUE" == "$CONFIRM_PHRASE" ]] || fail "confirmation did not match '${CONFIRM_PHRASE}'. No resources were created."
}

ensure_deploy_key() {
  local key_dir
  key_dir="$(dirname "$SSH_PRIVATE_KEY")"

  install -d -m 0700 "$key_dir"

  if [[ ! -f "$SSH_PRIVATE_KEY" ]]; then
    ssh-keygen -t ed25519 -f "$SSH_PRIVATE_KEY" -C "${APP_NAME}-deploy" -N ""
  fi

  chmod 600 "$SSH_PRIVATE_KEY"

  if [[ ! -f "${SSH_PRIVATE_KEY}.pub" ]]; then
    ssh-keygen -y -f "$SSH_PRIVATE_KEY" > "${SSH_PRIVATE_KEY}.pub"
  fi

  chmod 644 "${SSH_PRIVATE_KEY}.pub"
  echo "deploy SSH key ready: ${SSH_PRIVATE_KEY}"
}

set_tfvars_ssh_public_key_path() {
  python3 - "$TOFU_DIR/terraform.tfvars" "${SSH_PRIVATE_KEY}.pub" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
public_key_path = sys.argv[2]
content = path.read_text(encoding="utf-8")
replacement = f"ssh_public_key_path = {json.dumps(public_key_path)}"
updated, count = re.subn(
    r'^ssh_public_key_path\s*=\s*"[^"]*"',
    replacement,
    content,
    flags=re.MULTILINE,
)
if count != 1:
    raise SystemExit("expected exactly one ssh_public_key_path assignment in terraform.tfvars")
path.write_text(updated, encoding="utf-8")
PY
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

find_dispatched_run_id() {
  local earliest_epoch="$1"
  local json

  json="$(gh run list \
    --workflow "CD - Cloud" \
    --branch main \
    --event workflow_dispatch \
    --limit 10 \
    --json databaseId,createdAt,url,status,conclusion)"

  JSON_PAYLOAD="$json" EARLIEST_EPOCH="$earliest_epoch" python3 - <<'PY'
from __future__ import annotations

from datetime import datetime
import json
import os

payload = json.loads(os.environ["JSON_PAYLOAD"])
earliest = int(os.environ["EARLIEST_EPOCH"]) - 5

for run in payload:
    created_at = run.get("createdAt")
    if not created_at:
        continue
    created_epoch = int(datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp())
    if created_epoch >= earliest:
        print(run["databaseId"])
        raise SystemExit
PY
}

dispatch_cloud_cd() {
  local dispatch_epoch
  local run_id

  require_command gh

  gh auth status >/dev/null 2>&1 || fail "gh is not authenticated. Run gh auth login."

  dispatch_epoch="$(date -u +%s)"
  gh workflow run "CD - Cloud" --ref main -f "run_migrations=${RUN_MIGRATIONS}"

  run_id=""
  for _ in $(seq 1 20); do
    run_id="$(find_dispatched_run_id "$dispatch_epoch")"
    if [[ -n "$run_id" ]]; then
      break
    fi
    sleep 3
  done

  [[ -n "$run_id" ]] || fail "CD - Cloud was dispatched, but the run id could not be found."

  echo "CD - Cloud dispatched: run ${run_id}"

  if [[ "$WATCH_CD" == "1" ]]; then
    gh run watch "$run_id" --exit-status
  else
    gh run view "$run_id" --web
  fi
}

require_command bash
require_command curl
require_command git
require_command jq
require_command openssl
require_command python3
require_command ssh-keygen
require_command tofu
if [[ "$SKIP_GITHUB_ENV" == "0" || "$SKIP_CD" == "0" ]]; then
  require_command gh
  gh auth status >/dev/null 2>&1 || fail "gh is not authenticated. Run gh auth login."
fi
if [[ "$SKIP_PROVISION" == "0" ]]; then
  require_command ansible
  require_command ansible-inventory
  require_command ansible-playbook
  require_command ssh
fi

cd "$REPO_ROOT"
bash "$REPO_ROOT/Deployment/Common/Scripts/validate-common-release.sh" >/dev/null
bash "$SCRIPT_DIR/validate-cloud-settings.sh" >/dev/null
[[ -n "${HCLOUD_TOKEN:-}" ]] || fail "HCLOUD_TOKEN is required in this shell."
bash "$SCRIPT_DIR/check-hcloud-token.sh"

ensure_deploy_key
bash "$SCRIPT_DIR/prepare-opentofu-tfvars.sh"
set_tfvars_ssh_public_key_path

cd "$TOFU_DIR"
tofu init -input=false
tofu fmt -check versions.tf variables.tf locals.tf main.tf firewalls.tf outputs.tf
tofu validate
tofu plan -out cloud.tfplan -input=false

confirm_recreate

tofu apply -input=false cloud.tfplan
rm -f cloud.tfplan
backup_state "post-recreate"

cd "$REPO_ROOT"
bash "$SCRIPT_DIR/render-inventory-from-tofu.sh"
bash "$SCRIPT_DIR/validate-rendered-inventory.sh"
bash "$SCRIPT_DIR/reset-cloud-known-hosts.sh"

if [[ "$SKIP_GITHUB_ENV" == "0" ]]; then
  bash "$SCRIPT_DIR/configure-github-environment.sh"
else
  echo "skipped GitHub environment refresh"
fi

if [[ "$SKIP_PROVISION" == "0" ]]; then
  bash "$SCRIPT_DIR/provision.sh"
else
  echo "skipped local provisioning"
fi

if [[ "$SKIP_CD" == "0" ]]; then
  dispatch_cloud_cd
else
  echo "skipped CD - Cloud dispatch"
  echo "To deploy later:"
  echo "  gh workflow run \"CD - Cloud\" --ref main -f run_migrations=${RUN_MIGRATIONS}"
fi

echo
echo "Cloud recreate flow complete."
