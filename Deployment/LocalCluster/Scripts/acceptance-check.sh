#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/LocalCluster/ansible/ansible.cfg"

APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_name)"
PUBLIC_HOSTNAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" public_hostname)"
APP_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_port)"
POSTGRES_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" postgres_port)"
REDIS_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" redis_port)"
DEPLOY_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" deploy_root)"

[[ -f "$INVENTORY" ]] || {
  echo "acceptance check failed: missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
}

wait_for_public_health() {
  local url="$1"
  local attempt

  for attempt in $(seq 1 60); do
    if curl -fsS "$url"; then
      echo
      return 0
    fi
    sleep 2
  done

  echo "public HTTPS health still failed after 120 seconds: $url" >&2
  curl -fSv "$url"
}

echo "checking app nodes"
ansible app_servers -i "$INVENTORY" -a "curl -fsS http://127.0.0.1:${APP_PORT}/health/ready"
ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps"
ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps --services --filter status=running | grep -qx web"

echo "checking database node"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && set -a && . ./.env && set +a && docker compose ps --services --filter status=running | grep -qx postgres && docker compose ps --services --filter status=running | grep -qx redis && docker compose exec -T postgres pg_isready -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" && docker compose exec -T redis redis-cli -a \"\$REDIS_PASSWORD\" ping | grep -qx PONG"

echo "checking load balancer for ${PUBLIC_HOSTNAME}"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a "APP_NAME=${APP_NAME} PUBLIC_HOSTNAME=${PUBLIC_HOSTNAME} bash -lc 'set -u; for attempt in \$(seq 1 60); do if curl -fsS -H \"Host: \$PUBLIC_HOSTNAME\" http://127.0.0.1/health/ready; then exit 0; fi; sleep 2; done; echo \"local Caddy health still failed after 120 seconds for \$PUBLIC_HOSTNAME\" >&2; echo \"rendered Caddy app site:\" >&2; sed -n \"1,120p\" \"/etc/caddy/sites/\${APP_NAME}.caddy\" >&2 || true; echo \"recent Caddy logs:\" >&2; journalctl -u caddy --no-pager -n 80 >&2 || true; curl -fSv -H \"Host: \$PUBLIC_HOSTNAME\" http://127.0.0.1/health/ready'"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active caddy"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active cloudflared"

echo "checking app-specific data ports"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "ss -H -ltn 'sport = :${POSTGRES_PORT}' | grep -q ."
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "ss -H -ltn 'sport = :${REDIS_PORT}' | grep -q ."

echo "checking backup directory"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a \
  "if [ -d '${DEPLOY_ROOT}/backups' ]; then ls -1 '${DEPLOY_ROOT}/backups' | tail -n 5; else echo 'backup directory not present yet; it is created by migrations or manual backups'; fi"

echo "checking public HTTPS health: https://${PUBLIC_HOSTNAME}/health/ready"
wait_for_public_health "https://${PUBLIC_HOSTNAME}/health/ready"

echo
echo "acceptance check ok"
