from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROMETHEUS = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
TEMPO = {"type": "tempo", "uid": "tempo"}


@dataclass(frozen=True)
class PanelSpec:
    title: str
    kind: str
    datasource: dict[str, str] | None
    targets: list[dict[str, Any]]
    x: int
    y: int
    w: int
    h: int
    description: str = ""
    unit: str | None = None
    content: str | None = None


@dataclass(frozen=True)
class DashboardSpec:
    uid: str
    title: str
    refresh: str
    from_time: str
    variables: list[str]
    panels: list[PanelSpec]
    links: list[tuple[str, str]]


def prom_target(expr: str, ref_id: str = "A", legend: str | None = None, instant: bool = False) -> dict[str, Any]:
    target: dict[str, Any] = {
        "expr": expr,
        "refId": ref_id,
    }
    if legend:
        target["legendFormat"] = legend
    if instant:
        target["instant"] = True
    return target


def loki_target(expr: str, ref_id: str = "A") -> dict[str, Any]:
    return {
        "expr": expr,
        "refId": ref_id,
    }


def tempo_target(query: str, ref_id: str = "A") -> dict[str, Any]:
    return {
        "query": query,
        "queryType": "traceql",
        "refId": ref_id,
    }


def stat(
    title: str,
    expr: str,
    x: int,
    y: int,
    *,
    w: int = 3,
    h: int = 4,
    unit: str | None = None,
    description: str = "",
) -> PanelSpec:
    return PanelSpec(title, "stat", PROMETHEUS, [prom_target(expr, instant=True)], x, y, w, h, description, unit)


def timeseries(
    title: str,
    expr: str,
    x: int,
    y: int,
    *,
    w: int = 12,
    h: int = 8,
    unit: str | None = None,
    legend: str | None = None,
    description: str = "",
) -> PanelSpec:
    return PanelSpec(title, "timeseries", PROMETHEUS, [prom_target(expr, legend=legend)], x, y, w, h, description, unit)


def loki_timeseries(
    title: str,
    expr: str,
    x: int,
    y: int,
    *,
    w: int = 12,
    h: int = 8,
    unit: str | None = None,
    description: str = "",
) -> PanelSpec:
    return PanelSpec(title, "timeseries", LOKI, [loki_target(expr)], x, y, w, h, description, unit)


def table(
    title: str,
    expr: str,
    x: int,
    y: int,
    *,
    w: int = 12,
    h: int = 8,
    description: str = "",
) -> PanelSpec:
    return PanelSpec(title, "table", PROMETHEUS, [prom_target(expr, instant=True)], x, y, w, h, description)


def logs(title: str, expr: str, x: int, y: int, *, w: int = 12, h: int = 8, description: str = "") -> PanelSpec:
    return PanelSpec(title, "logs", LOKI, [loki_target(expr)], x, y, w, h, description)


def traces(title: str, query: str, x: int, y: int, *, w: int = 12, h: int = 8, description: str = "") -> PanelSpec:
    return PanelSpec(title, "traces", TEMPO, [tempo_target(query)], x, y, w, h, description)


def text(title: str, content: str, x: int, y: int, *, w: int = 24, h: int = 4) -> PanelSpec:
    return PanelSpec(title, "text", None, [], x, y, w, h, content=content)


def dashboard_links() -> list[tuple[str, str]]:
    return [
        ("Application And Books", "books-application-and-books"),
        ("Infrastructure And Data", "books-infrastructure-and-data"),
        ("Telemetry And Alerts", "books-telemetry-and-alerts"),
        ("Logs And Traces", "books-logs-and-traces"),
    ]


BASE_VARIABLES = ["deployment_target", "service_job", "app_instance"]
DETAIL_VARIABLES = BASE_VARIABLES + ["node", "http_route", "status_code", "book_operation", "book_outcome", "service_name"]


def dashboards() -> list[DashboardSpec]:
    return [
        DashboardSpec(
            uid="books-command-center",
            title="Books Observability Command Center",
            refresh="30s",
            from_time="now-30m",
            variables=BASE_VARIABLES,
            links=dashboard_links(),
            panels=[
                stat("Overall Health", 'min(up{deployment_target=~"$deployment_target"})', 0, 0, unit="none", description="Green means expected Prometheus scrape targets are up for the selected target."),
                stat("Deployed Version", 'count(count by (service_version) (target_info{deployment_target=~"$deployment_target", job=~"$service_job", instance=~"$app_instance", service_version!=""}))', 3, 0, unit="short", description="Count of distinct app versions. Use the version table for exact SHA per app instance."),
                stat("App Telemetry", 'count(count by (host_name, service_version) (target_info{deployment_target=~"$deployment_target", job=~"$service_job", instance=~"$app_instance", service_version!=""}))', 6, 0, unit="short", description="App instances currently represented by target_info. This is telemetry identity, not a public readiness probe."),
                stat("RPS", 'sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m]))', 9, 0, unit="reqps"),
                stat("Error Rate", '(sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance", http_response_status_code=~"5.."}[5m])) or vector(0)) / clamp_min(sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m])), 0.001)', 12, 0, unit="percentunit"),
                stat("p95", 'histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket{job=~"$service_job", instance=~"$app_instance"}[5m])) by (le))', 15, 0, unit="s"),
                stat("Firing Alerts", 'count(ALERTS{alertstate="firing"}) or vector(0)', 18, 0, unit="short"),
                stat("Series Budget", "prometheus_tsdb_head_series / 25000", 21, 0, unit="percentunit", description="Prometheus active series divided by the V1 budget of 25000."),
                table("App Version By Instance", 'target_info{deployment_target=~"$deployment_target", job=~"$service_job", instance=~"$app_instance", service_version!=""}', 0, 4, w=12, h=7),
                table("Health Matrix", 'up{deployment_target=~"$deployment_target", job=~"prometheus|alloy|node-exporter|postgres-exporter|redis-exporter"}', 12, 4, w=12, h=7, description="Local Docker intentionally has limited node metrics; deployed targets include every node."),
                timeseries("Request Rate By Route", 'sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m])) by (http_route)', 0, 11, legend="{{http_route}}", unit="reqps"),
                timeseries("p95 Latency By Route", 'histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket{job=~"$service_job", instance=~"$app_instance"}[5m])) by (le, http_route))', 12, 11, legend="{{http_route}}", unit="s"),
                logs("Recent App Errors (Empty Is OK)", '{service="web", deployment_target=~"$deployment_target"} |= "Error"', 0, 19, description="Empty is healthy when there are no recent app errors."),
                traces("Recent Traces", '{ resource.service.name =~ "$service_name" }', 12, 19),
                text("Safe Next Clicks", "Use the top-right dashboard links to drill into app behavior, infrastructure/data, telemetry/alerts, and logs/traces. Observability services remain private.", 0, 27, h=4),
            ],
        ),
        DashboardSpec(
            uid="books-application-and-books",
            title="Books Application And Books",
            refresh="1m",
            from_time="now-1h",
            variables=DETAIL_VARIABLES,
            links=[("Command Center", "books-command-center")] + dashboard_links()[1:],
            panels=[
                stat("RPS", 'sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m]))', 0, 0, unit="reqps"),
                stat("5xx Responses", 'sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance", http_response_status_code=~"5.."}[5m])) or vector(0)', 3, 0, unit="reqps"),
                stat("Book Ops", 'sum(rate(books_operations_total{job=~"$service_job", instance=~"$app_instance"}[5m]))', 6, 0, unit="ops"),
                stat("Working Set", "sum(dotnet_process_memory_working_set_bytes)", 9, 0, unit="bytes"),
                table("App Instances", 'target_info{deployment_target=~"$deployment_target", job=~"$service_job", instance=~"$app_instance", service_version!=""}', 12, 0, w=12, h=7),
                timeseries("Request Rate By Route", 'sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance", http_route=~"$http_route"}[5m])) by (http_route)', 0, 7, legend="{{http_route}}", unit="reqps"),
                timeseries("Errors By Instance", 'sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance", http_response_status_code=~"5.."}[5m])) by (instance) or vector(0)', 12, 7, legend="{{instance}}", unit="reqps"),
                timeseries("Latency p95 By Route", 'histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket{job=~"$service_job", instance=~"$app_instance", http_route=~"$http_route"}[5m])) by (le, http_route))', 0, 15, legend="{{http_route}}", unit="s"),
                timeseries("Book Operations", 'sum(rate(books_operations_total{job=~"$service_job", instance=~"$app_instance", books_operation=~"$book_operation", books_outcome=~"$book_outcome"}[5m])) by (books_operation, books_outcome)', 12, 15, legend="{{books_operation}} {{books_outcome}}", unit="ops"),
                timeseries("Book Operation p95", 'histogram_quantile(0.95, sum(rate(books_operation_duration_milliseconds_bucket{job=~"$service_job", instance=~"$app_instance", books_operation=~"$book_operation"}[5m])) by (le, books_operation))', 0, 23, legend="{{books_operation}}", unit="ms"),
                logs("Recent Domain Logs", '{service="web", deployment_target=~"$deployment_target"} |~ "book|Book|Created"', 12, 23, description="Book titles and user content must not be logged."),
            ],
        ),
        DashboardSpec(
            uid="books-infrastructure-and-data",
            title="Books Infrastructure And Data",
            refresh="1m",
            from_time="now-1h",
            variables=DETAIL_VARIABLES,
            links=[("Command Center", "books-command-center"), ("Application And Books", "books-application-and-books"), ("Telemetry And Alerts", "books-telemetry-and-alerts"), ("Logs And Traces", "books-logs-and-traces")],
            panels=[
                text("Local Node Metrics Note", "Local Docker intentionally has limited node-exporter coverage in V1. Local PostgreSQL and Redis exporter panels should still show data. LocalCluster and Cloud show the full four-node fleet.", 0, 0, h=3),
                table("Node Target Health", 'up{deployment_target=~"$deployment_target", job=~"node-exporter|postgres-exporter|redis-exporter"}', 0, 3, w=12, h=7),
                timeseries("CPU Usage By Node", '100 * (1 - avg by (node) (rate(node_cpu_seconds_total{deployment_target=~"$deployment_target", mode="idle"}[5m])))', 12, 3, legend="{{node}}", unit="percent"),
                timeseries("Memory Available", 'node_memory_MemAvailable_bytes{deployment_target=~"$deployment_target"}', 0, 10, legend="{{node}}", unit="bytes"),
                timeseries("Disk Used Percent", '100 * (1 - node_filesystem_avail_bytes{deployment_target=~"$deployment_target", fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{deployment_target=~"$deployment_target", fstype!~"tmpfs|overlay"})', 12, 10, legend="{{node}} {{mountpoint}}", unit="percent"),
                stat("PostgreSQL Up", 'min(pg_up{deployment_target=~"$deployment_target"})', 0, 18, unit="none"),
                stat("Redis Up", 'min(redis_up{deployment_target=~"$deployment_target"})', 3, 18, unit="none"),
                stat("Redis Memory", 'sum(redis_memory_used_bytes{deployment_target=~"$deployment_target"})', 6, 18, unit="bytes"),
                stat("PostgreSQL DB Size", 'sum(pg_database_size_bytes{deployment_target=~"$deployment_target"})', 9, 18, unit="bytes"),
                timeseries("PostgreSQL Transactions", 'sum(rate(pg_stat_database_xact_commit{deployment_target=~"$deployment_target"}[5m])) by (datname)', 0, 22, legend="{{datname}}", unit="ops"),
                timeseries("Redis Operations", 'rate(redis_commands_processed_total{deployment_target=~"$deployment_target"}[5m])', 12, 22, unit="ops"),
                timeseries("PostgreSQL Cache Hit Ratio", 'sum(pg_stat_database_blks_hit{deployment_target=~"$deployment_target"}) / clamp_min(sum(pg_stat_database_blks_hit{deployment_target=~"$deployment_target"} + pg_stat_database_blks_read{deployment_target=~"$deployment_target"}), 1)', 0, 30, unit="percentunit"),
                timeseries("Redis Hit Ratio", 'rate(redis_keyspace_hits_total{deployment_target=~"$deployment_target"}[5m]) / clamp_min(rate(redis_keyspace_hits_total{deployment_target=~"$deployment_target"}[5m]) + rate(redis_keyspace_misses_total{deployment_target=~"$deployment_target"}[5m]), 1)', 12, 30, unit="percentunit"),
            ],
        ),
        DashboardSpec(
            uid="books-telemetry-and-alerts",
            title="Books Telemetry And Alerts",
            refresh="1m",
            from_time="now-1h",
            variables=DETAIL_VARIABLES,
            links=[("Command Center", "books-command-center"), ("Application And Books", "books-application-and-books"), ("Infrastructure And Data", "books-infrastructure-and-data"), ("Logs And Traces", "books-logs-and-traces")],
            panels=[
                stat("Firing Alerts", 'count(ALERTS{alertstate="firing"}) or vector(0)', 0, 0, unit="short"),
                stat("Pending Alerts", 'count(ALERTS{alertstate="pending"}) or vector(0)', 3, 0, unit="short"),
                stat("Series Budget", "prometheus_tsdb_head_series / 25000", 6, 0, unit="percentunit"),
                stat("Alloy Export Failures", "(sum(rate(otelcol_exporter_send_failed_spans_total[5m])) or vector(0)) + (sum(rate(otelcol_exporter_send_failed_metric_points_total[5m])) or vector(0))", 9, 0, unit="ops"),
                table("Prometheus Targets", 'up{deployment_target=~"$deployment_target"}', 12, 0, w=12, h=8),
                timeseries("Active Series", "prometheus_tsdb_head_series", 0, 8, unit="short"),
                timeseries("Scrape Duration", 'scrape_duration_seconds{deployment_target=~"$deployment_target"}', 12, 8, legend="{{job}} {{instance}}", unit="s"),
                table("Firing Alerts Detail", 'ALERTS{alertstate="firing"}', 0, 16, w=12, h=8),
                table("Pending Alerts Detail", 'ALERTS{alertstate="pending"}', 12, 16, w=12, h=8),
                timeseries("Alloy Export Failures", "sum(rate(otelcol_exporter_send_failed_spans_total[5m])) or sum(rate(otelcol_exporter_send_failed_metric_points_total[5m]))", 0, 24, unit="ops"),
                text("Runbooks", "Runbooks live in Deployment/Common/observability/runbooks. Use application-server-errors.md, observability-target-down.md, telemetry-cardinality.md, and telemetry-missing.md.", 12, 24, w=12, h=5),
            ],
        ),
        DashboardSpec(
            uid="books-logs-and-traces",
            title="Books Logs And Traces",
            refresh="1m",
            from_time="now-1h",
            variables=DETAIL_VARIABLES,
            links=[("Command Center", "books-command-center"), ("Application And Books", "books-application-and-books"), ("Infrastructure And Data", "books-infrastructure-and-data"), ("Telemetry And Alerts", "books-telemetry-and-alerts")],
            panels=[
                logs("App Logs", '{service="web", deployment_target=~"$deployment_target"}', 0, 0, w=12, h=9),
                logs("App Errors (Empty Is OK)", '{service="web", deployment_target=~"$deployment_target"} |= "Error"', 12, 0, w=12, h=9, description="Empty means there are no recent error logs."),
                loki_timeseries("Error Log Rate", 'sum by (node) (rate({service="web", deployment_target=~"$deployment_target"} |= "Error" [5m]))', 0, 9, unit="ops"),
                traces("Recent Traces", '{ resource.service.name =~ "$service_name" }', 12, 9, w=12, h=9),
                traces("Error Traces", '{ resource.service.name =~ "$service_name" && status = error }', 0, 18, w=12, h=9),
                traces("Book Operation Traces", '{ span.books.operation =~ "$book_operation" }', 12, 18, w=12, h=9),
                text("Trace Linking", "Loki is configured with a derived field from the structured TraceId property to Tempo. Open a log row that contains TraceId to jump to the related trace.", 0, 27, h=4),
            ],
        ),
    ]
