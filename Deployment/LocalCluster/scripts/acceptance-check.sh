#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

PUBLIC_HOSTNAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" public_hostname)"
APP_PORT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" app_port)"
POSTGRES_PORT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" postgres_port)"
REDIS_PORT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" redis_port)"
DEPLOY_ROOT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" deploy_root)"

[[ -f "$INVENTORY" ]] || {
  echo "acceptance check failed: missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
}

echo "checking public HTTPS health"
curl -fsS "https://${PUBLIC_HOSTNAME}/health/ready"
echo

echo "checking app nodes"
ansible app_servers -i "$INVENTORY" -a "curl -fsS http://127.0.0.1:${APP_PORT}/health/ready"
ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps"

echo "checking database node"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps"

echo "checking load balancer"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a "curl -fsS -H 'Host: ${PUBLIC_HOSTNAME}' http://127.0.0.1/health/ready"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active caddy"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active cloudflared"

echo "checking app-specific data ports"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "ss -H -ltn 'sport = :${POSTGRES_PORT}' | grep -q ."
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "ss -H -ltn 'sport = :${REDIS_PORT}' | grep -q ."

echo "checking backup directory"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a \
  "if [ -d '${DEPLOY_ROOT}/backups' ]; then ls -1 '${DEPLOY_ROOT}/backups' | tail -n 5; else echo 'backup directory not present yet; it is created by migrations or manual backups'; fi"

echo
echo "acceptance check ok"
