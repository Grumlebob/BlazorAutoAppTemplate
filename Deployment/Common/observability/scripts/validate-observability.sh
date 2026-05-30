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
  "$OBS_ROOT/grafana/dashboard_spec.py" \
  "$OBS_ROOT/grafana/generate-dashboards.py" \
  "$OBS_ROOT/grafana/dashboards/00-books-command-center.json" \
  "$OBS_ROOT/grafana/dashboards/01-application-and-books.json" \
  "$OBS_ROOT/grafana/dashboards/02-infrastructure-and-data.json" \
  "$OBS_ROOT/grafana/dashboards/03-telemetry-and-alerts.json" \
  "$OBS_ROOT/grafana/dashboards/04-logs-and-traces.json" \
  "$OBS_ROOT/grafana/dashboards/application-overview.json" \
  "$OBS_ROOT/alertmanager/alertmanager.yml" \
  "$OBS_ROOT/prometheus/rules/application.rules.yml" \
  "$OBS_ROOT/prometheus/rules/resource.rules.yml" \
  "$OBS_ROOT/scripts/smoke-observability.sh"; do
  [[ -f "$required" ]] || fail "missing $required"
done
ok "required observability assets exist"

"$PYTHON_BIN" "$OBS_ROOT/grafana/generate-dashboards.py" --check >/dev/null
ok "generated Grafana dashboards are up to date"

"$PYTHON_BIN" - "$OBS_ROOT/grafana/dashboards" <<'PY'
import json
import pathlib
import sys

dashboard_dir = pathlib.Path(sys.argv[1])
allowed_datasources = {"prometheus", "loki", "tempo"}
uids = {}
linked_uids = set()
runbook_links = set()
for path in sorted(dashboard_dir.glob("*.json")):
    with path.open(encoding="utf-8") as handle:
        dashboard = json.load(handle)
    uid = dashboard.get("uid")
    if not uid:
        raise SystemExit(f"{path}: dashboard uid is required")
    if uid in uids:
        raise SystemExit(f"{path}: duplicate dashboard uid {uid!r} also used by {uids[uid]}")
    uids[uid] = path
    if not dashboard.get("title"):
        raise SystemExit(f"{path}: dashboard title is required")
    if not dashboard.get("tags"):
        raise SystemExit(f"{path}: dashboard tags are required")
    if not dashboard.get("templating", {}).get("list"):
        raise SystemExit(f"{path}: dashboard variables are required")

    for link in dashboard.get("links", []):
        link_type = link.get("type")
        if link_type == "dashboard":
            linked_uid = link.get("uid")
            if not linked_uid:
                raise SystemExit(f"{path}: dashboard link missing uid")
            if "coming" in (link.get("title") or "").lower():
                raise SystemExit(f"{path}: dashboard link points to placeholder text")
            linked_uids.add(linked_uid)
        elif link_type == "link" and str(link.get("url", "")).startswith("/d/"):
            linked_uid = str(link["url"]).split("/", 2)[2].split("/", 1)[0]
            if "coming" in (link.get("title") or "").lower():
                raise SystemExit(f"{path}: dashboard link points to placeholder text")
            linked_uids.add(linked_uid)

    for panel in dashboard.get("panels", []):
        datasource = panel.get("datasource")
        if isinstance(datasource, dict):
            uid_value = datasource.get("uid")
            if uid_value not in allowed_datasources:
                raise SystemExit(f"{path}: panel {panel.get('title')!r} uses unexpected datasource uid {uid_value!r}")
        if not panel.get("title"):
            raise SystemExit(f"{path}: every panel needs a title")
        content = panel.get("options", {}).get("content", "")
        if "Deployment/Common/observability/runbooks/" in content:
            for token in content.replace(",", " ").split():
                if token.startswith("Deployment/Common/observability/runbooks/"):
                    runbook_links.add(token.strip("`.;:"))

missing_links = sorted(uid for uid in linked_uids if uid not in uids)
if missing_links:
    raise SystemExit(f"dashboard links point to missing uids: {', '.join(missing_links)}")

repo_root = dashboard_dir.parents[4]
for runbook in sorted(runbook_links):
    if not (repo_root / runbook).is_file():
        raise SystemExit(f"runbook link points to missing file: {runbook}")
PY
ok "Grafana dashboards are valid JSON with uid/title/tags/variables/links"

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
