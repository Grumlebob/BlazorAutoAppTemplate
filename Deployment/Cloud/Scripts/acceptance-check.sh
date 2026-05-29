#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

fail() {
  echo "cloud acceptance check failed: $*" >&2
  exit 1
}

hostvar() {
  local host="$1"
  local key="$2"
  ansible-inventory -i "$INVENTORY" --host "$host" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$key"
}

wait_for_public_health() {
  local url="$1"

  for _ in {1..60}; do
    if curl -fsS "$url"; then
      echo
      return 0
    fi
    sleep 2
  done

  echo "public HTTPS health still failed after 120 seconds: $url" >&2
  curl -fSv "$url"
}

check_public_port_closed() {
  local host="$1"
  local port="$2"
  local label="$3"

  if [[ -z "$host" ]]; then
    echo "skipping public port check for $label because no public IP is recorded in inventory"
    return 0
  fi

  if timeout 5 bash -c ":</dev/tcp/${host}/${port}" 2>/dev/null; then
    fail "public ${label} is reachable on ${host}:${port}"
  fi

  echo "public ${label} is closed on ${host}:${port}"
}

[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml"

APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" app_name)"
PUBLIC_HOSTNAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" public_hostname)"
APP_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" app_port)"
POSTGRES_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" postgres_port)"
REDIS_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" redis_port)"
DEPLOY_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" deploy_root)"

APP1_PRIVATE="$(hostvar cloud-app1 cloud_private_ip)"
APP2_PRIVATE="$(hostvar cloud-app2 cloud_private_ip)"
DB_PRIVATE="$(hostvar cloud-db cloud_private_ip)"
APP1_PUBLIC="$(hostvar cloud-app1 cloud_public_ipv4)"
APP2_PUBLIC="$(hostvar cloud-app2 cloud_public_ipv4)"
DB_PUBLIC="$(hostvar cloud-db cloud_public_ipv4)"

echo "checking SSH reachability"
ansible cloud -i "$INVENTORY" -m ansible.builtin.ping

echo "checking app nodes"
ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "curl -fsS http://127.0.0.1:${APP_PORT}/health/ready"
ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps"
ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps --services --filter status=running | grep -Fx web"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a "curl -fsS http://${APP1_PRIVATE}:${APP_PORT}/health/ready"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a "curl -fsS http://${APP2_PRIVATE}:${APP_PORT}/health/ready"

echo "checking database node"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps --services --filter status=running | grep -Fx postgres"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && docker compose ps --services --filter status=running | grep -Fx redis"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && set -a && . ./.env && set +a && docker compose exec -T postgres pg_isready -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\""
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "cd ${DEPLOY_ROOT} && set -a && . ./.env && set +a && REDISCLI_AUTH=\"\$REDIS_PASSWORD\" docker compose exec -T -e REDISCLI_AUTH redis redis-cli ping | grep -Fx PONG"

echo "checking Caddy and cloudflared on ${PUBLIC_HOSTNAME}"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a "APP_NAME=${APP_NAME} PUBLIC_HOSTNAME=${PUBLIC_HOSTNAME} bash -lc 'set -u; for attempt in \$(seq 1 60); do if curl -fsS -H \"Host: \$PUBLIC_HOSTNAME\" http://127.0.0.1/health/ready; then exit 0; fi; sleep 2; done; echo \"local Caddy health still failed after 120 seconds for \$PUBLIC_HOSTNAME\" >&2; sed -n \"1,120p\" \"/etc/caddy/sites/\${APP_NAME}.caddy\" >&2 || true; journalctl -u caddy --no-pager -n 80 >&2 || true; curl -fSv -H \"Host: \$PUBLIC_HOSTNAME\" http://127.0.0.1/health/ready'"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active caddy"
ansible load_balancer -i "$INVENTORY" -a "systemctl is-active cloudflared"

echo "checking private-network deny rules"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a "if timeout 5 bash -lc '</dev/tcp/${DB_PRIVATE}/${POSTGRES_PORT}' 2>/dev/null; then echo 'cloud-main reached PostgreSQL unexpectedly' >&2; exit 1; fi"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a "if timeout 5 bash -lc '</dev/tcp/${DB_PRIVATE}/${REDIS_PORT}' 2>/dev/null; then echo 'cloud-main reached Redis unexpectedly' >&2; exit 1; fi"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "if timeout 5 bash -lc '</dev/tcp/${APP1_PRIVATE}/${APP_PORT}' 2>/dev/null; then echo 'cloud-db reached cloud-app1 unexpectedly' >&2; exit 1; fi"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a "if timeout 5 bash -lc '</dev/tcp/${APP2_PRIVATE}/${APP_PORT}' 2>/dev/null; then echo 'cloud-db reached cloud-app2 unexpectedly' >&2; exit 1; fi"

echo "checking public service ports are closed"
check_public_port_closed "$APP1_PUBLIC" "$APP_PORT" "cloud-app1 app port"
check_public_port_closed "$APP2_PUBLIC" "$APP_PORT" "cloud-app2 app port"
check_public_port_closed "$DB_PUBLIC" "$POSTGRES_PORT" "cloud-db PostgreSQL port"
check_public_port_closed "$DB_PUBLIC" "$REDIS_PORT" "cloud-db Redis port"

echo "checking backup directory"
ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a \
  "if [ -d '${DEPLOY_ROOT}/backups' ]; then ls -1 '${DEPLOY_ROOT}/backups' | tail -n 5; else echo 'backup directory not present yet; it is created by migrations or manual backups'; fi"

echo "checking public HTTPS health: https://${PUBLIC_HOSTNAME}/health/ready"
wait_for_public_health "https://${PUBLIC_HOSTNAME}/health/ready"
curl -fsS "https://${PUBLIC_HOSTNAME}/" >/dev/null

echo
echo "cloud acceptance check ok"
