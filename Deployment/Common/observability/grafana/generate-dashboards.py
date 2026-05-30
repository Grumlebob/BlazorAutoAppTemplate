#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from dashboard_spec import DashboardSpec, PanelSpec, dashboards


ROOT = pathlib.Path(__file__).resolve().parent
DASHBOARD_DIR = ROOT / "dashboards"


def variable(name: str) -> dict[str, Any]:
    common_current = {"selected": False, "text": "All", "value": ".*"}
    definitions: dict[str, dict[str, Any]] = {
        "deployment_target": {
            "allValue": ".*",
            "current": common_current,
            "includeAll": True,
            "label": "Deployment target",
            "multi": True,
            "name": "deployment_target",
            "options": [],
            "query": "local,localcluster,cloud",
            "type": "custom",
        },
        "service_job": query_variable(
            "service_job",
            "Service job",
            "label_values(http_server_request_duration_seconds_count, job)",
        ),
        "app_instance": query_variable(
            "app_instance",
            "App instance",
            'label_values(http_server_request_duration_seconds_count{job=~"$service_job"}, instance)',
        ),
        "node": query_variable(
            "node",
            "Node",
            'label_values(up{deployment_target=~"$deployment_target"}, node)',
        ),
        "http_route": query_variable(
            "http_route",
            "HTTP route",
            'label_values(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}, http_route)',
        ),
        "status_code": query_variable(
            "status_code",
            "Status code",
            'label_values(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}, http_response_status_code)',
        ),
        "book_operation": query_variable(
            "book_operation",
            "Book operation",
            'label_values(books_operations_total{job=~"$service_job", instance=~"$app_instance"}, books_operation)',
        ),
        "book_outcome": query_variable(
            "book_outcome",
            "Book outcome",
            'label_values(books_operations_total{job=~"$service_job", instance=~"$app_instance"}, books_outcome)',
        ),
        "service_name": {
            "current": {"selected": False, "text": "BlazorAutoApp", "value": "BlazorAutoApp"},
            "label": "Trace service",
            "name": "service_name",
            "query": "BlazorAutoApp",
            "type": "textbox",
        },
    }
    return definitions[name]


def query_variable(name: str, label: str, query: str) -> dict[str, Any]:
    return {
        "allValue": ".*",
        "current": {"selected": False, "text": "All", "value": ".*"},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "definition": query,
        "includeAll": True,
        "label": label,
        "multi": True,
        "name": name,
        "options": [],
        "query": {
            "query": query,
            "refId": f"PrometheusVariableQueryEditor-{name}",
        },
        "refresh": 1,
        "type": "query",
    }


def render_panel(panel: PanelSpec, panel_id: int) -> dict[str, Any]:
    rendered: dict[str, Any] = {
        "description": panel.description,
        "gridPos": {"h": panel.h, "w": panel.w, "x": panel.x, "y": panel.y},
        "id": panel_id,
        "title": panel.title,
        "type": panel.kind,
    }

    if panel.datasource is not None:
        rendered["datasource"] = panel.datasource
    if panel.targets:
        rendered["targets"] = panel.targets
    if panel.unit:
        rendered["fieldConfig"] = {
            "defaults": {
                "unit": panel.unit,
            },
            "overrides": [],
        }

    if panel.kind == "stat":
        rendered.setdefault("fieldConfig", {"defaults": {}, "overrides": []})
        rendered["options"] = {
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {
                "calcs": ["lastNotNull"],
                "fields": "",
                "values": False,
            },
            "textMode": "auto",
        }
    elif panel.kind == "timeseries":
        rendered["options"] = {
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "single", "sort": "none"},
        }
    elif panel.kind == "table":
        rendered["options"] = {"showHeader": True}
    elif panel.kind == "logs":
        rendered["options"] = {
            "dedupStrategy": "none",
            "enableLogDetails": True,
            "prettifyLogMessage": False,
            "showCommonLabels": False,
            "showLabels": True,
            "showTime": True,
            "sortOrder": "Descending",
            "wrapLogMessage": True,
        }
    elif panel.kind == "text":
        rendered["options"] = {
            "code": {
                "language": "plaintext",
                "showLineNumbers": False,
                "showMiniMap": False,
            },
            "content": panel.content or "",
            "mode": "markdown",
        }

    return rendered


def render_dashboard(spec: DashboardSpec) -> dict[str, Any]:
    return {
        "annotations": {"list": []},
        "editable": False,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": None,
        "links": [
            {
                "asDropdown": False,
                "icon": "external link",
                "includeVars": True,
                "keepTime": True,
                "tags": [],
                "targetBlank": False,
                "title": title,
                "tooltip": "",
                "type": "link",
                "url": f"/d/{uid}",
            }
            for title, uid in spec.links
        ],
        "panels": [render_panel(panel, panel_id) for panel_id, panel in enumerate(spec.panels, start=1)],
        "refresh": spec.refresh,
        "schemaVersion": 41,
        "tags": ["books", "observability"],
        "templating": {"list": [variable(name) for name in spec.variables]},
        "time": {"from": spec.from_time, "to": "now"},
        "timezone": "browser",
        "title": spec.title,
        "uid": spec.uid,
        "version": 1,
    }


def expected_files() -> dict[pathlib.Path, str]:
    filenames = {
        "books-command-center": "00-books-command-center.json",
        "books-application-and-books": "01-application-and-books.json",
        "books-infrastructure-and-data": "02-infrastructure-and-data.json",
        "books-telemetry-and-alerts": "03-telemetry-and-alerts.json",
        "books-logs-and-traces": "04-logs-and-traces.json",
    }
    files: dict[pathlib.Path, str] = {}
    for spec in dashboards():
        path = DASHBOARD_DIR / filenames[spec.uid]
        payload = json.dumps(render_dashboard(spec), indent=2, sort_keys=False)
        files[path] = payload + "\n"
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Grafana dashboard JSON.")
    parser.add_argument("--check", action="store_true", help="verify generated dashboards are up to date")
    args = parser.parse_args()

    files = expected_files()
    if args.check:
        stale = []
        for path, expected in files.items():
            actual = path.read_text(encoding="utf-8") if path.exists() else ""
            if actual != expected:
                stale.append(path)
        if stale:
            print("dashboard JSON is stale:", file=sys.stderr)
            for path in stale:
                print(f"  {path.relative_to(ROOT.parent.parent.parent.parent)}", file=sys.stderr)
            return 1
        print("dashboard JSON is up to date")
        return 0

    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    for path, contents in files.items():
        path.write_text(contents, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT.parent.parent.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
