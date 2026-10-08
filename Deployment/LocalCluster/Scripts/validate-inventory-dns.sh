#!/usr/bin/env bash
set -euo pipefail

# Optional check that each inventory host name resolves to its inventory IP.
# It catches a stale hosts.yml after a router hands out new addresses. It runs
# only when group_vars/all.yml sets inventory_dns_suffix (for example "home"
# when the router publishes node-main.home); otherwise it is skipped.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="${1:-$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml}"

fail() {
  echo "inventory DNS validation failed: $*" >&2
  exit 1
}

DNS_SUFFIX="$(python3 "$SCRIPT_DIR/Component/lib/read-deploy-setting.py" inventory_dns_suffix)"
DNS_SUFFIX="${DNS_SUFFIX#.}"
if [[ -z "$DNS_SUFFIX" ]]; then
  echo "inventory DNS validation skipped (inventory_dns_suffix is empty)"
  exit 0
fi

command -v ansible-inventory >/dev/null 2>&1 || fail "ansible-inventory is missing"
command -v getent >/dev/null 2>&1 || fail "getent is missing"
[[ -f "$INVENTORY" ]] || fail "missing inventory: $INVENTORY"

inventory_json="$(ansible-inventory -i "$INVENTORY" --list)" \
  || fail "could not render inventory: $INVENTORY"
inventory_hosts="$(python3 -c 'import json, sys
inventory = json.load(sys.stdin)
hostvars = inventory.get("_meta", {}).get("hostvars", {})
for host in sorted(hostvars):
    print("{}\t{}".format(host, str(hostvars[host].get("ansible_host", "")).strip()))' <<< "$inventory_json")" \
  || fail "could not parse inventory: $INVENTORY"
[[ -n "$inventory_hosts" ]] || fail "inventory contains no hosts: $INVENTORY"

while IFS=$'\t' read -r host expected_ip; do
  [[ -n "$host" ]] || continue
  [[ -n "$expected_ip" && "$expected_ip" != REPLACE_WITH* ]] \
    || fail "$host has no concrete ansible_host in $INVENTORY"

  dns_name="${host}.${DNS_SUFFIX}"
  resolved_ips="$(getent ahostsv4 "$dns_name" | awk '{ print $1 }' | sort -u)"
  [[ -n "$resolved_ips" ]] || fail "$dns_name did not resolve"
  printf '%s\n' "$resolved_ips" | grep -Fqx -- "$expected_ip" \
    || fail "$host expects $expected_ip but $dns_name resolves to: $resolved_ips. Regenerate hosts.yml from machines.yml."

  echo "OK    $host $dns_name $expected_ip"
done <<< "$inventory_hosts"
