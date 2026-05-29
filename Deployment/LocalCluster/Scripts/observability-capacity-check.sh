#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/LocalCluster/ansible/ansible.cfg"

fail() {
  echo "observability capacity check failed: $*" >&2
  exit 1
}

command -v ansible >/dev/null 2>&1 || fail "ansible is missing"
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"

APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_name)"
OBS_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_root)"
OBS_ENABLED="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_enabled 2>/dev/null || echo false)"

if [[ "$OBS_ENABLED" != "true" ]]; then
  echo "observability capacity check skipped: observability_enabled is not true"
  exit 0
fi

check_group() {
  local group="$1"
  local fresh_mb="$2"
  local rerun_mb="$3"
  local disk_mb="$4"

  ansible "$group" -i "$INVENTORY" -m ansible.builtin.shell -a \
    "APP_NAME='$APP_NAME' OBS_ROOT='$OBS_ROOT' FRESH_MB='$fresh_mb' RERUN_MB='$rerun_mb' DISK_MB='$disk_mb' bash -lc 'set -euo pipefail
mem_total_mb=\$(awk \"/MemTotal/ {printf \\\"%d\\\", \\\$2/1024}\" /proc/meminfo)
mem_available_mb=\$(awk \"/MemAvailable/ {printf \\\"%d\\\", \\\$2/1024}\" /proc/meminfo)
compose_projects=\$(
  {
    docker ps --filter \"label=com.docker.compose.project=\${APP_NAME}-observability\" -q 2>/dev/null
    docker ps --filter \"label=com.docker.compose.project=\${APP_NAME}-observability-agent\" -q 2>/dev/null
  } | wc -l
)
additional_mb=\$FRESH_MB
if [ \"\$compose_projects\" -gt 0 ]; then
  additional_mb=\$RERUN_MB
fi
required_after_mb=\$((mem_total_mb / 4))
required_now_mb=\$((additional_mb + required_after_mb))
if [ \"\$mem_available_mb\" -lt \"\$required_now_mb\" ]; then
  echo \"available memory \${mem_available_mb}MiB is below required \${required_now_mb}MiB for observability plus 25 percent headroom\" >&2
  exit 1
fi
disk_available_mb=\$(df -Pm /opt | awk \"NR==2 {print \\\$4}\")
if [ \"\$disk_available_mb\" -lt \"\$DISK_MB\" ]; then
  echo \"/opt free disk \${disk_available_mb}MiB is below required \${DISK_MB}MiB\" >&2
  exit 1
fi
printf \"OK    %s has %sMiB available memory and %sMiB free /opt disk\\n\" \"\$(hostname)\" \"\$mem_available_mb\" \"\$disk_available_mb\"
'"
}

echo "checking LocalCluster observability capacity"
check_group load_balancer 2304 384 20480
check_group app_servers 384 128 2048
check_group node_db 768 192 4096

echo "observability capacity check ok"
