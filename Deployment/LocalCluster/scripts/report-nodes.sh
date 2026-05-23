#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

[[ -f "$INVENTORY" ]] || {
  echo "node report failed: missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
}

ansible all -i "$INVENTORY" -m ansible.builtin.shell -a '
set +e
docker_version="$(docker --version 2>/dev/null | grep -m 1 "^Docker version" || true)"
compose_version="$(docker compose version 2>/dev/null | grep -m 1 "^Docker Compose version" || true)"
memory_summary="$(free -h 2>/dev/null | awk "/^Mem:/ {print \$2 \" total, \" \$7 \" available\"}" || true)"
disk_summary="$(df -h / 2>/dev/null | awk "NR==2 {print \$4 \" available of \" \$2}" || true)"
ufw_status="$(sudo -n ufw status 2>/dev/null | head -n 1 || true)"
listening_ports="$(ss -H -ltn 2>/dev/null | awk "{print \$4}" | sed "s/.*://" | sort -n | uniq | paste -sd, - || true)"
[ -n "$docker_version" ] || docker_version=missing
[ -n "$compose_version" ] || compose_version=missing
[ -n "$memory_summary" ] || memory_summary=unknown
[ -n "$disk_summary" ] || disk_summary=unknown
[ -n "$ufw_status" ] || ufw_status=unknown
[ -n "$listening_ports" ] || listening_ports=unknown
echo "node=$(hostname)"
echo "os=$(if [ -r /etc/os-release ]; then . /etc/os-release && echo "$PRETTY_NAME"; else echo unknown; fi)"
echo "arch=$(uname -m 2>/dev/null || echo unknown)"
echo "cpu_count=$(nproc 2>/dev/null || echo unknown)"
echo "memory=$memory_summary"
echo "disk_root=$disk_summary"
echo "docker=$docker_version"
echo "compose=$compose_version"
echo "ufw=$ufw_status"
echo "services=$(systemctl is-active caddy 2>/dev/null || echo caddy-unknown),$(systemctl is-active cloudflared 2>/dev/null || echo cloudflared-unknown)"
echo "listening_ports=$listening_ports"
'
