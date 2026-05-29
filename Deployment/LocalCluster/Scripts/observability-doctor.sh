#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/LocalCluster/ansible/ansible.cfg"

fail() {
  echo "observability doctor failed: $*" >&2
  exit 1
}

run_check() {
  local label="$1"
  shift
  printf 'checking %s\n' "$label"
  "$@"
}

command -v ansible >/dev/null 2>&1 || fail "ansible is missing"
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"

APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" app_name)"
DEPLOY_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" deploy_root)"
OBS_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_root)"
PROMETHEUS_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_prometheus_port)"
LOKI_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_loki_port)"
TEMPO_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_tempo_http_port)"
GRAFANA_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-deploy-setting.py" observability_grafana_port)"

echo "LocalCluster observability doctor"
echo

run_check "backend containers on node-main" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "cd '$OBS_ROOT' && docker compose ps --services --filter status=running | grep -E '^(prometheus|loki|tempo|grafana)$' | sort | paste -sd ' ' -"

run_check "agents on every node" \
  ansible all -i "$INVENTORY" -m ansible.builtin.shell -a \
    "cd '$OBS_ROOT/agent' && docker compose ps --services --filter status=running | grep -E '^(alloy|node-exporter)$' | sort | paste -sd ' ' -"

run_check "database exporters on node-db" \
  ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a \
    "cd '$DEPLOY_ROOT' && docker compose ps --services --filter status=running | grep -E '^(postgres-exporter|redis-exporter)$' | sort | paste -sd ' ' -"

run_check "backend health endpoints" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "curl -fsS http://127.0.0.1:$PROMETHEUS_PORT/-/ready >/dev/null && curl -fsS http://127.0.0.1:$LOKI_PORT/ready >/dev/null && curl -fsS http://127.0.0.1:$TEMPO_PORT/ready >/dev/null && curl -fsS http://127.0.0.1:$GRAFANA_PORT/api/health >/dev/null"

run_check "Prometheus target health" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "PROMETHEUS_PORT='$PROMETHEUS_PORT' python3 - <<'PY'
import json
import sys
import urllib.parse
import urllib.request

base = \"http://127.0.0.1:$PROMETHEUS_PORT\"

def query(expr: str) -> list[dict]:
    url = base + \"/api/v1/query?query=\" + urllib.parse.quote(expr)
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.load(response)
    if payload.get(\"status\") != \"success\":
        raise SystemExit(f\"Prometheus query failed: {expr}\")
    return payload[\"data\"][\"result\"]

def require_up(job: str, expected: int) -> None:
    series = query('up{' + f'job=\"{job}\"' + '}')
    up = [item for item in series if item.get(\"value\", [None, \"0\"])[1] == \"1\"]
    if len(up) < expected:
        raise SystemExit(f\"job {job} has {len(up)}/{expected} targets up\")
    print(f\"OK    {job}: {len(up)} target(s) up\")

require_up(\"node-exporter\", 4)
require_up(\"alloy\", 4)
require_up(\"postgres-exporter\", 1)
require_up(\"redis-exporter\", 1)
PY"

run_check "Grafana dashboard provisioning" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "python3 - <<'PY'
import json
import urllib.request

url = 'http://127.0.0.1:$GRAFANA_PORT/api/search?query=Application%20Observability'
with urllib.request.urlopen(url, timeout=10) as response:
    dashboards = json.load(response)
if not any(item.get('uid') == 'application-observability-overview' for item in dashboards):
    raise SystemExit('Application Observability dashboard is not provisioned')
print('OK    Grafana dashboard is provisioned')
PY"

run_check "no observability containers OOMKilled" \
  ansible all -i "$INVENTORY" -m ansible.builtin.shell -a \
    "APP_NAME='$APP_NAME' bash -lc 'set -euo pipefail
ids=\$({
  docker ps --filter \"label=com.docker.compose.project=\${APP_NAME}-observability\" -q
  docker ps --filter \"label=com.docker.compose.project=\${APP_NAME}-observability-agent\" -q
} | tr \"\n\" \" \")
if [ -z \"\$ids\" ]; then
  echo \"no observability containers found\" >&2
  exit 1
fi
docker inspect --format \"{{ '{{' }}.Name{{ '}}' }} {{ '{{' }}.State.OOMKilled{{ '}}' }}\" \$ids | tee /tmp/${APP_NAME}-observability-oom.txt
if grep -q \" true$\" /tmp/${APP_NAME}-observability-oom.txt; then
  exit 1
fi
'"

if [[ -x "$REPO_ROOT/Deployment/Common/observability/scripts/check-telemetry-cardinality.sh" ]]; then
  run_check "cardinality budgets from node-main" \
    ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
      "cd '$REPO_ROOT' && bash Deployment/Common/observability/scripts/check-telemetry-cardinality.sh http://127.0.0.1:$PROMETHEUS_PORT http://127.0.0.1:$LOKI_PORT"
fi

echo
echo "observability doctor ok"
