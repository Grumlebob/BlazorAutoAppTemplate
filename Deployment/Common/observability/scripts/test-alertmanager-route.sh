#!/usr/bin/env bash
set -euo pipefail

ALERTMANAGER_URL="${1:-http://127.0.0.1:9093}"
DEPLOYMENT_TARGET="${2:-local}"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "FAIL  missing command: $1" >&2
    exit 1
  }
}

require curl
require python3

starts_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ends_at="$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"

payload="$(
  STARTS_AT="$starts_at" ENDS_AT="$ends_at" DEPLOYMENT_TARGET="$DEPLOYMENT_TARGET" python3 - <<'PY'
import json
import os

print(json.dumps([
    {
        "labels": {
            "alertname": "ObservabilityRouteTest",
            "deployment_target": os.environ["DEPLOYMENT_TARGET"],
            "severity": "info",
        },
        "annotations": {
            "summary": "Synthetic Alertmanager route test",
        },
        "startsAt": os.environ["STARTS_AT"],
        "endsAt": os.environ["ENDS_AT"],
        "generatorURL": "https://example.invalid/observability-route-test",
    }
]))
PY
)"

curl -fsS \
  -H "Content-Type: application/json" \
  -d "$payload" \
  "$ALERTMANAGER_URL/api/v2/alerts" >/dev/null

alerts_json="$(curl -fsS "$ALERTMANAGER_URL/api/v2/alerts")"

ALERTS_JSON="$alerts_json" python3 - "$DEPLOYMENT_TARGET" <<'PY'
import json
import os
import sys

deployment_target = sys.argv[1]
alerts = json.loads(os.environ["ALERTS_JSON"])

for alert in alerts:
    labels = alert.get("labels") or {}
    if (
        labels.get("alertname") == "ObservabilityRouteTest"
        and labels.get("deployment_target") == deployment_target
    ):
        print("OK    Alertmanager accepted ObservabilityRouteTest")
        raise SystemExit(0)

raise SystemExit("FAIL  Alertmanager did not return ObservabilityRouteTest")
PY
