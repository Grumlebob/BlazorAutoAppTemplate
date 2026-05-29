#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
KNOWN_HOSTS="${CLOUD_KNOWN_HOSTS_FILE:-$HOME/.ssh/known_hosts}"

fail() {
  echo "Cloud known_hosts reset failed: $*" >&2
  exit 1
}

command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
command -v ssh-keygen >/dev/null 2>&1 || fail "ssh-keygen is missing."
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml. Run Step 8 first."

export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

if [[ ! -f "$KNOWN_HOSTS" ]]; then
  echo "No known_hosts file found at $KNOWN_HOSTS; nothing to reset."
  exit 0
fi

mapfile -t CLOUD_HOSTS < <(
  ansible-inventory -i "$INVENTORY" --list |
    python3 -c '
import json
import sys

data = json.load(sys.stdin)
values = set()
for hostvars in data.get("_meta", {}).get("hostvars", {}).values():
    for key in ("ansible_host", "cloud_private_ip", "cloud_public_ipv4"):
        value = hostvars.get(key)
        if value:
            values.add(str(value))

for value in sorted(values):
    print(value)
'
)

if [[ "${#CLOUD_HOSTS[@]}" -eq 0 ]]; then
  fail "no Cloud hosts were found in inventory."
fi

echo "Removing old SSH host keys for Cloud inventory addresses from $KNOWN_HOSTS"
for host in "${CLOUD_HOSTS[@]}"; do
  echo "  $host"
  ssh-keygen -R "$host" -f "$KNOWN_HOSTS" >/dev/null 2>&1 || true
done

echo "Cloud known_hosts reset ok"
