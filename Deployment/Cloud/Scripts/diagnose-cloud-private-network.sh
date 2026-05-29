#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"

fail() {
  echo "Cloud private-network diagnosis failed: $*" >&2
  exit 1
}

command -v ansible >/dev/null 2>&1 || fail "ansible is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml. Run Step 8 first."

export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

app1_ip="$("$SCRIPT_DIR/read-cloud-setting.sh" cloud_app1_private_ip)"
app2_ip="$("$SCRIPT_DIR/read-cloud-setting.sh" cloud_app2_private_ip)"
db_ip="$("$SCRIPT_DIR/read-cloud-setting.sh" cloud_db_private_ip)"

remote_script=$(cat <<EOF
set -u

echo "cloud-main IPv4 addresses:"
ip -br -4 addr || true

echo
echo "cloud-main routes:"
ip route || true

echo
for target in "$app1_ip" "$app2_ip" "$db_ip"; do
  echo "testing tcp/22 from cloud-main to \${target}"
  if timeout 4 bash -lc "cat < /dev/null > /dev/tcp/\${target}/22"; then
    echo "OK \${target}:22"
  else
    echo "FAIL \${target}:22"
  fi
done
EOF
)

ansible load_balancer -i "$INVENTORY" \
  -m ansible.builtin.shell \
  -a "$remote_script" \
  -e ansible_shell_executable=/bin/bash
