#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

fail() {
  echo "cloud observability doctor failed: $*" >&2
  exit 1
}

run_check() {
  local label="$1"
  shift
  printf 'checking %s\n' "$label"
  "$@"
}

command -v ansible >/dev/null 2>&1 || fail "ansible is missing"
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml"

APP_NAME="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" app_name)"
DEPLOY_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" deploy_root)"
APP_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" app_port)"
OBS_ROOT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_root)"
PROMETHEUS_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_prometheus_port)"
ALERTMANAGER_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_alertmanager_port)"
LOKI_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_loki_port)"
TEMPO_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_tempo_http_port)"
GRAFANA_PORT="$(python3 "${SCRIPT_DIR}/Component/lib/read-cloud-setting.py" observability_grafana_port)"

echo "Cloud observability doctor"
echo

run_check "backend containers on cloud-main" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "cd '$OBS_ROOT' && docker compose ps --services --filter status=running | grep -E '^(prometheus|alertmanager|loki|tempo|grafana)$' | sort | paste -sd ' ' -"

run_check "agents on every Cloud node" \
  ansible cloud -i "$INVENTORY" -m ansible.builtin.shell -a \
    "cd '$OBS_ROOT/agent' && docker compose ps --services --filter status=running | grep -E '^(alloy|node-exporter)$' | sort | paste -sd ' ' -"

run_check "database exporters on cloud-db" \
  ansible node_db -i "$INVENTORY" -m ansible.builtin.shell -a \
    "cd '$DEPLOY_ROOT' && docker compose ps --services --filter status=running | grep -E '^(postgres-exporter|redis-exporter)$' | sort | paste -sd ' ' -"

run_check "backend health endpoints" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "curl -fsS http://127.0.0.1:$PROMETHEUS_PORT/-/ready >/dev/null && curl -fsS http://127.0.0.1:$ALERTMANAGER_PORT/-/healthy >/dev/null && curl -fsS http://127.0.0.1:$LOKI_PORT/ready >/dev/null && curl -fsS http://127.0.0.1:$TEMPO_PORT/ready >/dev/null && curl -fsS http://127.0.0.1:$GRAFANA_PORT/api/health >/dev/null"

run_check "Prometheus target health" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "PROMETHEUS_PORT='$PROMETHEUS_PORT' python3 - <<'PY'
import json
import sys
import time
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

def target_diagnostics() -> str:
    with urllib.request.urlopen(base + \"/api/v1/targets\", timeout=10) as response:
        payload = json.load(response)
    lines = []
    for target in payload.get(\"data\", {}).get(\"activeTargets\", []):
        labels = target.get(\"labels\", {})
        job = labels.get(\"job\", \"unknown\")
        instance = labels.get(\"instance\", \"unknown\")
        health = target.get(\"health\", \"unknown\")
        error = target.get(\"lastError\", \"\")
        lines.append(f\"{job} {instance} health={health} error={error}\")
    return \"\n\".join(sorted(lines))

def count_up(job: str) -> int:
    series = query('up{' + f'job=\"{job}\"' + '}')
    up = [item for item in series if item.get(\"value\", [None, \"0\"])[1] == \"1\"]
    return len(up)

expected = {
    \"node-exporter\": 4,
    \"alloy\": 4,
    \"postgres-exporter\": 1,
    \"redis-exporter\": 1,
}

deadline = time.monotonic() + 120
while True:
    observed = {job: count_up(job) for job in expected}
    missing = [f\"{job} {observed[job]}/{want}\" for job, want in expected.items() if observed[job] < want]
    if not missing:
        for job, count in observed.items():
            print(f\"OK    {job}: {count} target(s) up\")
        break
    if time.monotonic() >= deadline:
        print(target_diagnostics(), file=sys.stderr)
        raise SystemExit(\"Prometheus targets not healthy: \" + \", \".join(missing))
    print(\"WAIT  Prometheus targets warming up: \" + \", \".join(missing))
    time.sleep(5)
PY"

run_check "generate Cloud app telemetry" \
  ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a \
    "APP_PORT='$APP_PORT' bash -lc 'set -euo pipefail
for _attempt in \$(seq 1 6); do
  curl -fsS \"http://127.0.0.1:\${APP_PORT}/\" >/dev/null
  sleep 1
done
'"

run_check "Cloud app telemetry labels and versions" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "APP_NAME='$APP_NAME' PROMETHEUS_PORT='$PROMETHEUS_PORT' python3 - <<'PY'
import json
import os
import sys
import time
import urllib.parse
import urllib.request

base = 'http://127.0.0.1:' + '$PROMETHEUS_PORT'
app_name = os.environ['APP_NAME']
expected_nodes = {'cloud-app1', 'cloud-app2'}
expected_job = 'books/' + app_name

def query(expr: str) -> list[dict]:
    url = base + '/api/v1/query?query=' + urllib.parse.quote(expr)
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.load(response)
    if payload.get('status') != 'success':
        raise SystemExit(f'Prometheus query failed: {expr}')
    return payload.get('data', {}).get('result', [])

def app_target_info() -> list[dict]:
    result = query(
        'count by (job, service_name, instance, host_name, deployment_target, service_version) '
        '(target_info{deployment_target=\"cloud\"})'
    )
    app_result = []
    for item in result:
        metric = item.get('metric', {})
        job = metric.get('job', '')
        service_name = metric.get('service_name', '')
        if job == expected_job or job.endswith('/' + app_name) or service_name == app_name:
            app_result.append(item)
    return app_result

deadline = time.monotonic() + 180
last_result: list[dict] = []
while True:
    last_result = app_target_info()
    versions = {}
    for item in last_result:
        metric = item.get('metric', {})
        node = metric.get('host_name', '')
        version = metric.get('service_version', '')
        if node:
            versions[node] = version
    missing = expected_nodes - set(versions)
    missing_versions = sorted(node for node, version in versions.items() if node in expected_nodes and not version)
    if not missing and not missing_versions:
        labels = [f'{node}={versions[node]}' for node in sorted(expected_nodes)]
        print('OK    cloud app telemetry versions: ' + ', '.join(labels))
        break
    if time.monotonic() >= deadline:
        print('app target_info diagnostics:', file=sys.stderr)
        for item in last_result:
            print(json.dumps(item.get('metric', {}), sort_keys=True), file=sys.stderr)
        problems = []
        if missing:
            problems.append('missing host_name label(s): ' + ', '.join(sorted(missing)))
        if missing_versions:
            problems.append('missing service_version label(s): ' + ', '.join(missing_versions))
        raise SystemExit('cloud app telemetry labels incomplete: ' + '; '.join(problems))
    problems = []
    if missing:
        problems.append('missing host_name label(s): ' + ', '.join(sorted(missing)))
    if missing_versions:
        problems.append('missing service_version label(s): ' + ', '.join(missing_versions))
    print('WAIT  Cloud app telemetry warming up; ' + '; '.join(problems))
    time.sleep(5)
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

run_check "Prometheus is connected to Alertmanager" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "PROMETHEUS_PORT='$PROMETHEUS_PORT' python3 - <<'PY'
import json
import urllib.request

url = 'http://127.0.0.1:$PROMETHEUS_PORT/api/v1/alertmanagers'
with urllib.request.urlopen(url, timeout=10) as response:
    payload = json.load(response)
active = payload.get('data', {}).get('activeAlertmanagers', [])
if not active:
    raise SystemExit('Prometheus has no active Alertmanager connection')
print('OK    active Alertmanager connection(s): ' + str(len(active)))
PY"

run_check "no observability containers OOMKilled" \
  ansible cloud -i "$INVENTORY" -m ansible.builtin.shell -a \
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

run_check "cardinality budgets from cloud-main" \
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
    "PROMETHEUS_PORT='$PROMETHEUS_PORT' LOKI_PORT='$LOKI_PORT' python3 - <<'PY'
import json
import time
import urllib.parse
import urllib.request

prometheus_url = 'http://127.0.0.1:' + '$PROMETHEUS_PORT'
loki_url = 'http://127.0.0.1:' + '$LOKI_PORT'
series_limit = 25000
stream_limit = 300

with urllib.request.urlopen(prometheus_url + '/api/v1/status/tsdb', timeout=10) as response:
    prometheus_payload = json.load(response)
series = int(prometheus_payload['data']['headStats']['numSeries'])
if series > series_limit:
    raise SystemExit(f'Prometheus active series {series} exceeds limit {series_limit}')
print(f'OK    Prometheus active series: {series} <= {series_limit}')

start_ns = int((time.time() - 900) * 1_000_000_000)
query = urllib.parse.urlencode({
    'match[]': '{deployment_target=\"cloud\"}',
    'start': str(start_ns),
})
with urllib.request.urlopen(loki_url + '/loki/api/v1/series?' + query, timeout=10) as response:
    loki_payload = json.load(response)
streams = len(loki_payload.get('data', []))
if streams > stream_limit:
    raise SystemExit(f'Loki stream count {streams} exceeds limit {stream_limit}')
print(f'OK    Loki stream count: {streams} <= {stream_limit}')
PY"

echo
echo "cloud observability doctor ok"
