#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

fail() {
  echo "cloud observability resource report failed: $*" >&2
  exit 1
}

command -v ansible >/dev/null 2>&1 || fail "ansible is missing"
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml"

APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" app_name)"
OBS_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_root)"

echo "Cloud observability resource report"
echo "timestamp_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

ansible cloud -i "$INVENTORY" -m ansible.builtin.shell -a \
  "APP_NAME='$APP_NAME' OBS_ROOT='$OBS_ROOT' bash -lc 'set -euo pipefail
echo \"node=\$(hostname)\"
awk \"/MemTotal/ {printf \\\"  mem_total_mib=%d\\\\n\\\", \\\$2/1024} /MemAvailable/ {printf \\\"  mem_available_mib=%d\\\\n\\\", \\\$2/1024}\" /proc/meminfo
df -Pm /opt | awk \"NR==2 {printf \\\"  opt_free_mib=%s opt_used_pct=%s\\\\n\\\", \\\$4, \\\$5}\"
if command -v docker >/dev/null 2>&1; then
  echo \"  docker_containers:\"
  ids=\$({
    docker ps --filter \"label=com.docker.compose.project=\${APP_NAME}-observability\" -q
    docker ps --filter \"label=com.docker.compose.project=\${APP_NAME}-observability-agent\" -q
  } | tr \"\n\" \" \")
  if [ -n \"\$ids\" ]; then
    docker stats --no-stream --format \"    {{ '{{' }}.Name{{ '}}' }} CPU={{ '{{' }}.CPUPerc{{ '}}' }} MEM={{ '{{' }}.MemUsage{{ '}}' }}\" \$ids
    docker inspect --format \"    {{ '{{' }}.Name{{ '}}' }} OOMKilled={{ '{{' }}.State.OOMKilled{{ '}}' }}\" \$ids
  else
    echo \"    no observability containers running\"
  fi
else
  echo \"  docker unavailable\"
fi
'"
