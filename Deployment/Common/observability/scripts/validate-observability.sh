#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OBS_ROOT="$ROOT/Deployment/Common/observability"
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

fail() {
  echo "FAIL  $*" >&2
  exit 1
}

ok() {
  echo "OK    $*"
}

for required in \
  "$OBS_ROOT/grafana/provisioning/datasources/datasources.yml" \
  "$OBS_ROOT/grafana/provisioning/dashboards/dashboards.yml" \
  "$OBS_ROOT/grafana/dashboards/application-overview.json" \
  "$OBS_ROOT/alertmanager/alertmanager.yml" \
  "$OBS_ROOT/prometheus/rules/application.rules.yml" \
  "$OBS_ROOT/prometheus/rules/resource.rules.yml"; do
  [[ -f "$required" ]] || fail "missing $required"
done
ok "required observability assets exist"

"$PYTHON_BIN" - "$OBS_ROOT/grafana/dashboards" <<'PY'
import json
import pathlib
import sys

dashboard_dir = pathlib.Path(sys.argv[1])
for path in sorted(dashboard_dir.glob("*.json")):
    with path.open(encoding="utf-8") as handle:
        dashboard = json.load(handle)
    if not dashboard.get("uid"):
        raise SystemExit(f"{path}: dashboard uid is required")
    if not dashboard.get("title"):
        raise SystemExit(f"{path}: dashboard title is required")
PY
ok "Grafana dashboards are valid JSON with uid/title"

while IFS= read -r -d '' script; do
  bash -n "$script"
done < <(find "$OBS_ROOT/scripts" -type f -name '*.sh' -print0)
ok "observability shell scripts parse"

if grep -RInE --exclude=validate-observability.sh 'bookscloud|books\.jacobgrum\.com|bookscloud\.jacobgrum\.com|cloud-main|cloud-app|cloud-db|node-main|node-app|node-db|10\.10\.|192\.168\.' "$OBS_ROOT"; then
  fail "Deployment/Common/observability contains target-specific values"
fi
ok "Common observability assets contain no target-specific hostnames or IPs"

if grep -RInE 'password|secret|token' "$OBS_ROOT/grafana" "$OBS_ROOT/prometheus" "$OBS_ROOT/runbooks"; then
  fail "Common observability assets contain suspicious secret words"
fi
ok "Common observability assets contain no obvious secrets"

echo "observability validation ok"
