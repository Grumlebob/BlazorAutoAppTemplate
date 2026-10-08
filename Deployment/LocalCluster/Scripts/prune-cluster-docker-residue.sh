#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
DOCKER_PRUNE_SCRIPT="$SCRIPT_DIR/prune-docker-residue.sh"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/LocalCluster/ansible/ansible.cfg"

source "$SCRIPT_DIR/localcluster-capacity-thresholds.sh"

APP_SERVERS_MIN_FREE_MB="$LOCALCLUSTER_APP_SERVERS_MIN_FREE_MB"
NODE_DB_MIN_FREE_MB="$LOCALCLUSTER_NODE_DB_MIN_FREE_MB"
REMOTE_SCRIPT=""
REMOTE_SCRIPT_INSTALLED="false"

usage() {
  cat >&2 <<USAGE
usage: prune-cluster-docker-residue.sh [options]

Copies prune-docker-residue.sh to non-runner LocalCluster nodes and runs safe
Docker cleanup there before deployment preflight.

Options:
  --app-servers-min-free-mb <mb>  Required free /opt space on app servers. Default: ${LOCALCLUSTER_APP_SERVERS_MIN_FREE_MB}.
  --node-db-min-free-mb <mb>      Required free /opt space on node-db. Default: ${LOCALCLUSTER_NODE_DB_MIN_FREE_MB}.
  --help, -h                      Show this help.
USAGE
}

fail() {
  echo "cluster Docker cleanup failed: $*" >&2
  exit 1
}

shell_quote() {
  printf "'%s'" "${1//\'/\'\\\'\'}"
}

run_ansible() {
  ANSIBLE_TIMEOUT="${ANSIBLE_TIMEOUT:-30}" ansible "$@" -i "$INVENTORY"
}

# Ansible connects with strict host-key checking. Every inventory host must
# already be in known_hosts (seed and verify them before the first deploy, see
# docs/HowToForkThisRepo.md). An unknown key is a trust decision for the
# operator, so stop with its fingerprint instead of accepting it.
require_trusted_inventory_hosts() {
  local known_hosts="$HOME/.ssh/known_hosts"
  local inventory_json inventory_hosts inventory_host host host_keyscan

  command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing"
  command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
  command -v ssh-keygen >/dev/null 2>&1 || fail "ssh-keygen is missing"

  bash "$SCRIPT_DIR/validate-inventory-dns.sh" "$INVENTORY"

  inventory_json="$(ansible-inventory -i "$INVENTORY" --list)" \
    || fail "could not render inventory: $INVENTORY"
  inventory_hosts="$(python3 -c 'import json, sys
inventory = json.load(sys.stdin)
hostvars = inventory.get("_meta", {}).get("hostvars", {})
for host in sorted(hostvars):
    values = hostvars[host]
    target = str(values.get("ansible_host") or host).strip()
    if target:
        print(f"{host}\t{target}")' <<< "$inventory_json")" \
    || fail "could not parse inventory: $INVENTORY"
  [[ -n "$inventory_hosts" ]] || fail "inventory contains no hosts: $INVENTORY"

  while IFS=$'\t' read -r inventory_host host; do
    [[ -n "$inventory_host" && -n "$host" ]] || continue
    if [[ -f "$known_hosts" ]] && ssh-keygen -F "$host" -f "$known_hosts" >/dev/null 2>&1; then
      continue
    fi
    host_keyscan="$(ssh-keyscan -T 10 "$host" 2>/dev/null || true)"
    echo "missing trusted SSH host key for $inventory_host ($host). Verify this fingerprint on the machine's console, then add it to $known_hosts:" >&2
    [[ -z "$host_keyscan" ]] || printf '%s\n' "$host_keyscan" | ssh-keygen -lf - >&2 || true
    fail "refusing to connect to $host without a trusted SSH host key"
  done <<< "$inventory_hosts"
}

cleanup_remote_script() {
  [[ "$REMOTE_SCRIPT_INSTALLED" == "true" && -n "$REMOTE_SCRIPT" && -f "$INVENTORY" ]] || return 0
  command -v ansible >/dev/null 2>&1 || return 0

  run_ansible app_servers -m ansible.builtin.file -a \
    "path=$REMOTE_SCRIPT state=absent" >/dev/null || true
  run_ansible node_db -m ansible.builtin.file -a \
    "path=$REMOTE_SCRIPT state=absent" >/dev/null || true
}
trap cleanup_remote_script EXIT

prune_group() {
  local group="$1"
  local min_free_mb="$2"
  local app_image_q app_version_q remote_script_q remote_command

  app_image_q="$(shell_quote "$APP_IMAGE")"
  app_version_q="$(shell_quote "${APP_VERSION:-}")"
  remote_script_q="$(shell_quote "$REMOTE_SCRIPT")"
  remote_command="APP_IMAGE=$app_image_q APP_VERSION=$app_version_q bash $remote_script_q"
  remote_command+=" --force --min-free-mb $min_free_mb"
  remote_command+=" --dangling-image-until 168h"
  remote_command+=" --localcluster-image-until 168h --low-disk-localcluster-image-until 0h"
  remote_command+=" --builder-until 48h --low-disk-builder-until 0h --defer-if-skipped"

  echo "Pruning Docker residue on ${group}; required /opt free space: ${min_free_mb}MiB"
  run_ansible "$group" -m ansible.builtin.copy -a \
    "src=$DOCKER_PRUNE_SCRIPT dest=$REMOTE_SCRIPT mode=0750"
  REMOTE_SCRIPT_INSTALLED="true"
  run_ansible "$group" -m ansible.builtin.shell -a "$remote_command"
  if run_ansible "$group" -m ansible.builtin.file -a \
    "path=$REMOTE_SCRIPT state=absent" >/dev/null; then
    REMOTE_SCRIPT_INSTALLED="false"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-servers-min-free-mb)
      [[ $# -ge 2 ]] || fail "--app-servers-min-free-mb requires a value"
      APP_SERVERS_MIN_FREE_MB="$2"
      shift 2
      ;;
    --node-db-min-free-mb)
      [[ $# -ge 2 ]] || fail "--node-db-min-free-mb requires a value"
      NODE_DB_MIN_FREE_MB="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

[[ "$APP_SERVERS_MIN_FREE_MB" =~ ^[0-9]+$ ]] || fail "--app-servers-min-free-mb must be an integer"
[[ "$NODE_DB_MIN_FREE_MB" =~ ^[0-9]+$ ]] || fail "--node-db-min-free-mb must be an integer"
[[ -f "$INVENTORY" ]] || fail "missing inventory: $INVENTORY"
[[ -f "$DOCKER_PRUNE_SCRIPT" ]] || fail "missing Docker cleanup script: $DOCKER_PRUNE_SCRIPT"
command -v ansible >/dev/null 2>&1 || fail "ansible is missing"

APP_IMAGE="${APP_IMAGE:-$(bash "$REPO_ROOT/Deployment/Common/Scripts/read-release-setting.sh" app_image)}"
APP_VERSION="${APP_VERSION:-${GITHUB_SHA:-}}"
APP_NAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_name)"
REMOTE_SCRIPT="/tmp/${APP_NAME}-prune-docker-residue-${GITHUB_RUN_ID:-$$}-${GITHUB_RUN_ATTEMPT:-1}.sh"
[[ -n "$APP_IMAGE" ]] || fail "APP_IMAGE is required"
[[ -n "$APP_NAME" ]] || fail "APP_NAME is required"

require_trusted_inventory_hosts
prune_group app_servers "$APP_SERVERS_MIN_FREE_MB"
prune_group node_db "$NODE_DB_MIN_FREE_MB"

echo "cluster Docker cleanup complete."
