#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

fail() {
  echo "port collision check failed: $*" >&2
  exit 1
}

[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"
command -v ansible >/dev/null 2>&1 || fail "ansible is missing"

APP_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_port)"
POSTGRES_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" postgres_port)"
REDIS_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" redis_port)"
DEPLOY_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" deploy_root)"
APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_name)"
OBSERVABILITY_ENABLED="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_enabled 2>/dev/null || echo false)"

check_group_port_root() {
  local group="$1"
  local label="$2"
  local port="$3"
  local root="$4"

  ansible "$group" -i "$INVENTORY" -m ansible.builtin.shell -a \
    "APP_NAME=$APP_NAME PORT=$port DEPLOY_ROOT=$root LABEL=$label bash -lc 'set -eu; if [ -f \"\$DEPLOY_ROOT/.env\" ]; then root_app=\"\$(sed -n \"s/^APP_NAME=//p\" \"\$DEPLOY_ROOT/.env\" | tail -n 1)\"; if [ -n \"\$root_app\" ] && [ \"\$root_app\" != \"\$APP_NAME\" ]; then echo \"\$DEPLOY_ROOT belongs to app \$root_app, not \$APP_NAME\" >&2; exit 1; fi; fi; root_has_compose=0; if [ -d \"\$DEPLOY_ROOT\" ] && cd \"\$DEPLOY_ROOT\" && docker compose ps -q 2>/dev/null | grep -q .; then root_has_compose=1; fi; if [ -d \"\$DEPLOY_ROOT/agent\" ] && cd \"\$DEPLOY_ROOT/agent\" && docker compose ps -q 2>/dev/null | grep -q .; then root_has_compose=1; fi; if ss -H -ltn \"sport = :\$PORT\" | grep -q .; then if [ \"\$root_has_compose\" = 1 ]; then echo \"\$LABEL port \$PORT is already used by this deployment root\"; else echo \"\$LABEL port \$PORT is already listening; choose another side-by-side port or stop the conflicting service\" >&2; exit 1; fi; else echo \"\$LABEL port \$PORT is available\"; fi'"
}

check_group_port() {
  check_group_port_root "$1" "$2" "$3" "$DEPLOY_ROOT"
}

check_group_port app_servers app "$APP_PORT"
check_group_port node_db postgres "$POSTGRES_PORT"
check_group_port node_db redis "$REDIS_PORT"

if [[ "$OBSERVABILITY_ENABLED" == "true" ]]; then
  OBS_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_root)"
  check_obs_port() {
    check_group_port_root "$1" "$2" "$3" "$OBS_ROOT"
  }

  check_obs_port load_balancer observability-grafana "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_grafana_port)"
  check_obs_port load_balancer observability-prometheus "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_prometheus_port)"
  check_obs_port load_balancer observability-loki "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_loki_port)"
  check_obs_port load_balancer observability-tempo-http "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_tempo_http_port)"
  check_obs_port load_balancer observability-tempo-otlp-grpc "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_tempo_otlp_grpc_port)"
  check_obs_port load_balancer observability-tempo-otlp-http "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_tempo_otlp_http_port)"
  check_obs_port all observability-alloy "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_alloy_http_port)"
  check_obs_port all observability-node-exporter "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_node_exporter_port)"
  check_group_port node_db observability-postgres-exporter "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_postgres_exporter_port)"
  check_group_port node_db observability-redis-exporter "$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_redis_exporter_port)"
fi

echo "port collision check ok"
