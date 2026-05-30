#!/usr/bin/env bash
set -euo pipefail

PROMETHEUS_URL="${1:-http://localhost:9090}"
LOKI_URL="${2:-http://localhost:3100}"
DEPLOYMENT_TARGET="${3:-local}"
PROMETHEUS_SERIES_LIMIT="${PROMETHEUS_SERIES_LIMIT:-25000}"
LOKI_STREAM_LIMIT="${LOKI_STREAM_LIMIT:-100}"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "FAIL  missing command: $1" >&2
    exit 1
  }
}

require curl

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "FAIL  missing command: python3 or python" >&2
    exit 1
  fi
fi

prometheus_series="$(
  curl -fsS "$PROMETHEUS_URL/api/v1/status/tsdb" |
    "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["data"]["headStats"]["numSeries"])'
)"

if (( prometheus_series > PROMETHEUS_SERIES_LIMIT )); then
  echo "FAIL  Prometheus active series $prometheus_series exceeds limit $PROMETHEUS_SERIES_LIMIT" >&2
  exit 1
fi
echo "OK    Prometheus active series: $prometheus_series <= $PROMETHEUS_SERIES_LIMIT"

start_ns="$("$PYTHON_BIN" - <<'PY'
import time
print(int((time.time() - 900) * 1_000_000_000))
PY
)"

loki_streams="$(
  curl -fsG \
    --data-urlencode "match[]={deployment_target=\"$DEPLOYMENT_TARGET\"}" \
    --data-urlencode "start=$start_ns" \
    "$LOKI_URL/loki/api/v1/series" |
    "$PYTHON_BIN" -c 'import json,sys; print(len(json.load(sys.stdin)["data"]))'
)"

if (( loki_streams > LOKI_STREAM_LIMIT )); then
  echo "FAIL  Loki stream count $loki_streams exceeds limit $LOKI_STREAM_LIMIT" >&2
  exit 1
fi
echo "OK    Loki stream count: $loki_streams <= $LOKI_STREAM_LIMIT"

echo "telemetry cardinality check ok"
