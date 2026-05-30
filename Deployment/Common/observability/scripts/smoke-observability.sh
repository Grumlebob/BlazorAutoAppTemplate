#!/usr/bin/env bash
set -euo pipefail

APP_URL="${APP_URL:-https://localhost:7186}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"
LOKI_URL="${LOKI_URL:-http://localhost:3100}"
TEMPO_URL="${TEMPO_URL:-http://localhost:3200}"
DEPLOYMENT_TARGET="${DEPLOYMENT_TARGET:-local}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-180}"
PROMETHEUS_SERIES_LIMIT="${PROMETHEUS_SERIES_LIMIT:-10000}"
LOKI_STREAM_LIMIT="${LOKI_STREAM_LIMIT:-100}"
CHECK_DOCKER_OOM="${CHECK_DOCKER_OOM:-true}"

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

ok() {
  printf 'OK    %s\n' "$*"
}

require() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

find_docker() {
  if command_exists docker && docker version >/dev/null 2>&1; then
    printf 'docker'
    return 0
  fi

  if command_exists docker.exe && docker.exe version >/dev/null 2>&1; then
    printf 'docker.exe'
    return 0
  fi

  return 1
}

urlencode() {
  python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$1"
}

json_query_count() {
  python3 -c 'import json, sys; print(len(json.load(sys.stdin).get("data", {}).get("result", [])))'
}

wait_until() {
  local description="$1"
  shift

  local deadline=$((SECONDS + TIMEOUT_SECONDS))
  local last_output=""

  while ((SECONDS < deadline)); do
    if last_output="$("$@" 2>&1)"; then
      ok "$description"
      return 0
    fi
    sleep 3
  done

  printf '%s\n' "$last_output" >&2
  fail "$description did not pass before timeout"
}

probe_app() {
  curl -kfsS "$APP_URL" >/dev/null
}

probe_grafana() {
  curl -fsS "$GRAFANA_URL/api/health" |
    python3 -c 'import json, sys; payload=json.load(sys.stdin); raise SystemExit(0 if payload.get("database") == "ok" else 1)'
}

probe_alertmanager() {
  curl -fsS "$ALERTMANAGER_URL/-/healthy" >/dev/null
}

probe_prometheus_app_metrics() {
  local queries=(
    'sum(http_server_request_duration_seconds_count)'
    'sum(http_server_request_duration_milliseconds_count)'
    'sum(http_server_request_duration_count)'
  )
  local query
  local encoded
  local count

  for query in "${queries[@]}"; do
    encoded="$(urlencode "$query")"
    count="$(curl -fsS "$PROMETHEUS_URL/api/v1/query?query=$encoded" | json_query_count)"
    if ((count > 0)); then
      return 0
    fi
  done

  return 1
}

probe_prometheus_alertmanager() {
  curl -fsS "$PROMETHEUS_URL/api/v1/alertmanagers" |
    python3 -c 'import json, sys; payload=json.load(sys.stdin); raise SystemExit(0 if payload.get("data", {}).get("activeAlertmanagers") else 1)'
}

probe_prometheus_app_instances() {
  local query

  query='target_info{deployment_target="'$DEPLOYMENT_TARGET'"}'
  curl -fsS "$PROMETHEUS_URL/api/v1/query?query=$(urlencode "$query")" |
    python3 -c '
import json
import sys

payload = json.load(sys.stdin)
results = payload.get("data", {}).get("result", [])
app_instances = [
    item.get("metric", {})
    for item in results
    if item.get("metric", {}).get("service_version")
]
if not app_instances:
    raise SystemExit(1)

labels = [
    "{}={}".format(metric.get("instance", "unknown"), metric.get("service_version", "unknown"))
    for metric in app_instances
]
print("app instance versions: " + ", ".join(sorted(labels)))
'
}

probe_loki_logs() {
  local start_ns
  start_ns="$(python3 - <<'PY'
import time
print(int((time.time() - 900) * 1_000_000_000))
PY
)"

  curl -fsG \
    --data-urlencode 'query={service="web"}' \
    --data-urlencode "start=$start_ns" \
    --data-urlencode 'limit=1' \
    "$LOKI_URL/loki/api/v1/query_range" |
    python3 -c 'import json, sys; payload=json.load(sys.stdin); raise SystemExit(0 if payload.get("data", {}).get("result") else 1)'
}

probe_tempo_traces() {
  curl -fsS "$TEMPO_URL/api/search?limit=20" |
    python3 -c 'import json, sys; payload=json.load(sys.stdin); raise SystemExit(0 if payload.get("traces") else 1)'
}

check_cardinality() {
  local prometheus_series
  local start_ns
  local loki_streams

  prometheus_series="$(
    curl -fsS "$PROMETHEUS_URL/api/v1/status/tsdb" |
      python3 -c 'import json, sys; print(json.load(sys.stdin)["data"]["headStats"]["numSeries"])'
  )"
  if ((prometheus_series > PROMETHEUS_SERIES_LIMIT)); then
    fail "Prometheus active series $prometheus_series exceeds limit $PROMETHEUS_SERIES_LIMIT"
  fi
  ok "Prometheus active series below threshold: $prometheus_series"

  start_ns="$(python3 - <<'PY'
import time
print(int((time.time() - 900) * 1_000_000_000))
PY
)"
  loki_streams="$(
    curl -fsG \
      --data-urlencode "match[]={deployment_target=\"$DEPLOYMENT_TARGET\"}" \
      --data-urlencode "start=$start_ns" \
      "$LOKI_URL/loki/api/v1/series" |
      python3 -c 'import json, sys; print(len(json.load(sys.stdin).get("data", [])))'
  )"
  if ((loki_streams > LOKI_STREAM_LIMIT)); then
    fail "Loki stream count $loki_streams exceeds limit $LOKI_STREAM_LIMIT"
  fi
  ok "Loki streams below threshold: $loki_streams"
}

check_docker_oom() {
  local docker_bin
  local ids=()

  if [[ "$CHECK_DOCKER_OOM" != "true" ]]; then
    return 0
  fi

  if ! docker_bin="$(find_docker)"; then
    fail "docker is missing; set CHECK_DOCKER_OOM=false to skip local container OOM checks"
  fi

  mapfile -t ids < <("$docker_bin" compose ps -q | sed '/^[[:space:]]*$/d')
  if ((${#ids[@]} == 0)); then
    fail "no Docker Compose containers found for OOM check"
  fi

  "$docker_bin" inspect --format '{{.Name}} {{.State.OOMKilled}}' "${ids[@]}" |
    tee /tmp/observability-smoke-oom.txt
  if grep -q ' true$' /tmp/observability-smoke-oom.txt; then
    fail "one or more Docker Compose containers were OOMKilled"
  fi
  ok "no Compose container reports OOMKilled"
}

require curl
require python3

printf 'Generating app telemetry through %s\n' "$APP_URL"
for _ in {1..8}; do
  probe_app || true
  sleep 0.25
done

wait_until "Grafana is reachable" probe_grafana
wait_until "Alertmanager is reachable" probe_alertmanager
wait_until "Prometheus has app request metrics" probe_prometheus_app_metrics
wait_until "Prometheus is connected to Alertmanager" probe_prometheus_alertmanager
wait_until "Prometheus has app instance versions" probe_prometheus_app_instances
wait_until "Loki has app container logs" probe_loki_logs
wait_until "Tempo has app traces" probe_tempo_traces
check_cardinality
check_docker_oom

printf '\nobservability smoke ok\n'
