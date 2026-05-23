#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/inventory/prod/hosts.yml"

PUBLIC_HOSTNAME="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" public_hostname)"
APP_PORT="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" app_port)"
DEPLOY_ROOT="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" deploy_root)"

[[ -f "$INVENTORY" ]] || {
  echo "deployment verification failed: missing inventory: Deployment/inventory/prod/hosts.yml" >&2
  exit 1
}

echo "checking public health"
curl -fsS "https://${PUBLIC_HOSTNAME}/health/ready"
echo

echo "checking app nodes"
ansible app_servers -i "$INVENTORY" -a "curl -fsS http://localhost:${APP_PORT}/health/ready"
ansible app_servers -i "$INVENTORY" -a "cd ${DEPLOY_ROOT} && docker compose ps"

echo "checking database node"
ansible node_db -i "$INVENTORY" -a "cd ${DEPLOY_ROOT} && docker compose ps"

echo "checking load balancer"
ansible load_balancer -i "$INVENTORY" -a "curl -fsS http://localhost/health/ready"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active caddy"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active cloudflared"

echo
echo "deployment verification ok"
