# Perfect Dashboards Plan

Status: planning document created on 2026-05-30.

Goal: when Grafana opens for the first time, the operator should immediately understand whether the app is healthy, which deployment they are looking at, which app instances are emitting telemetry, what version is deployed, whether the data layer is healthy, and where to click next if something looks wrong.

This is a dashboard plan only. It does not authorize deployment, firewall, Cloudflare, Hetzner, or data-destruction changes until execution is explicitly requested.

## Current Execution Status

Status: V1 local implementation complete on CurrentPC. Remote LocalCluster and Cloud rollout still requires committing/pushing these repo changes or explicitly running the deployment playbooks from this working tree.

Completed locally:

- [x] Local PostgreSQL and Redis exporter parity added under the observability profile.
- [x] Five V1 dashboards generated from repo-owned dashboard-as-code.
- [x] Grafana default home dashboard set to the Command Center for local, LocalCluster, and Cloud compose templates.
- [x] Validation scripts check generated dashboard freshness, required dashboard files, unique UIDs, datasource UIDs, dashboard links, and runbook references.
- [x] Local and shared smoke scripts verify app metrics, data exporter metrics, V1 dashboard provisioning, Loki logs, Tempo traces, cardinality, and OOM status.
- [x] Opt-in Playwright Grafana smoke test added and passed against local Grafana.
- [x] Full local E2E category passed with the observability test enabled.

Remote rollout gates:

- [ ] LocalCluster CD/doctor must pass after these changes are committed/pushed or explicitly applied.
- [ ] Cloud CD/doctor must pass after these changes are committed/pushed or explicitly applied.

## Current Baseline

The observability stack is already deployed for:

- Local Docker: optional Grafana, Prometheus, Alertmanager, Loki, Tempo, and Alloy profile.
- LocalCluster: backend on `node-main`, Alloy and node-exporter on every node, PostgreSQL and Redis exporters on `node-db`.
- Cloud: backend on `cloud-main`, Alloy and node-exporter on every node, PostgreSQL and Redis exporters on `cloud-db`.

V1 dashboard work should add local PostgreSQL and Redis exporter parity before the Data panels are considered complete. Local Docker does not need full `node-exporter` parity for V1; Infrastructure node panels should show an explicit local-limited state when the selected target is `local`.

The current common dashboard is:

```text
Deployment/Common/observability/grafana/dashboards/application-overview.json
```

It currently has:

- HTTP request rate.
- app logs.
- Books operation rate.
- recent traces.
- app instance inventory through `target_info`.

That is useful, but it is not yet a first-open command center. It lacks a strong top-level status row, node fleet overview, data-layer panels, alert state, guided drill-down, dashboard links, and an intentional home-dashboard experience.

## Design Principles

Use these rules throughout implementation:

- The first screen answers: "Is it healthy, what version is running, where is the problem?"
- Start high-level, then drill down. The first row is status, not raw graphs.
- Use RED for user-facing app health: rate, errors, duration.
- Use USE for nodes: utilization, saturation, errors.
- Use a small number of curated dashboards, not dashboard sprawl.
- Use variables and links instead of copy-pasted target-specific dashboards.
- Keep dashboards versioned in git and provisioned from `Deployment/Common/observability`.
- Do not edit dashboards manually in the Grafana browser except for temporary exploration.
- Keep refresh intervals reasonable. Default to 30s or 1m, not 5s or 10s.
- Keep queries bounded with `rate(...[5m])`, `topk`, and focused labels.
- Do not add high-cardinality labels such as request IDs, user IDs, book IDs, URLs, trace IDs, or exception messages.
- Do not expose Grafana, Prometheus, Loki, Tempo, Alertmanager, Alloy, or exporter ports publicly.
- Do not require a Cloudflare API token.
- Do not add observability nodes. LocalCluster and Cloud stay four nodes each.
- Do not reintroduce Seq.

Official guidance this plan follows:

- Grafana dashboard best practices: https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
- Grafana provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/
- Grafana variables: https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/
- Grafana annotations: https://grafana.com/docs/grafana/latest/dashboards/annotations/
- Grafana `default_home_dashboard_path`: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#default_home_dashboard_path

## First-Open Experience

The first Grafana page should be a curated home dashboard:

```text
Books Observability Command Center
```

Opening Grafana should show it automatically. Implement this by provisioning the dashboard JSON and setting:

```text
GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/00-books-command-center.json
```

Apply that environment variable in:

```text
docker-compose.yml
Deployment/LocalCluster/ansible/roles/observability_backend/templates/docker-compose.yml.j2
Deployment/Cloud/ansible/roles/observability_backend/templates/docker-compose.yml.j2
```

The home dashboard should use a 30 minute time range and 30s refresh. It should not require navigation, login, or manual variable changes to be useful.

The V1 Command Center shows the currently deployed version from `target_info.service_version`. Do not add deployment timeline annotations in V1. They need a private, idempotent deployment event writer first.

Post-V1 deployment annotation requirements:

- Write annotations only after a successful CD deploy and observability doctor.
- Write through the private Grafana API on the target backend node over localhost or SSH/Ansible, never through a public Grafana endpoint.
- Include deployment target, Git SHA, workflow run URL, whether migrations ran, and an idempotency tag such as `deployment:<target>:<sha>:<workflow_run_id>`.
- Before creating an annotation, query for the idempotency tag and skip duplicates.
- Annotation write failures must be non-blocking unless a future strict mode explicitly opts in.

## Dashboard Set

Create these dashboard files under:

```text
Deployment/Common/observability/grafana/dashboards/
```

Use numeric prefixes only to keep the files readable in git. V1 should have five polished dashboards, all linked and useful; no placeholder or "coming next" dashboards are allowed.

```text
00-books-command-center.json
01-application-and-books.json
02-infrastructure-and-data.json
03-telemetry-and-alerts.json
04-logs-and-traces.json
```

Keep all of them in the existing provisioned Grafana folder:

```text
Application Observability
```

Do not rely on file names for Grafana navigation order. Use dashboard titles, dashboard links, and a dashboard-list/link panel. Do not create separate LocalCluster and Cloud dashboard JSON unless a dashboard is truly target-specific. The normal path is common dashboards with variables.

## Metric Contract

The dashboard implementation must respect the real label contract before writing JSON:

- App HTTP metrics currently have labels such as `job`, `instance`, `http_route`, `http_request_method`, `http_response_status_code`, `network_protocol_version`, and `url_scheme`.
- App HTTP metrics do not currently carry `deployment_target` or `host_name`.
- Books metrics currently have labels such as `job`, `instance`, `books_operation`, `books_outcome`, and histogram `le`.
- Books metrics do not currently carry `deployment_target` or `host_name`.
- App identity and deployed version are available through `target_info`, including `deployment_target`, `host_name`, `service_version`, `job`, and `instance`.
- Loki streams carry `deployment_target`; distributed targets also carry `node`.
- Infrastructure/exporter metrics from LocalCluster and Cloud carry `deployment_target` and `node`.
- Local Docker currently has app, Prometheus, Alertmanager, Loki, Tempo, and Alloy metrics. It does not currently have local `node-exporter`, `postgres-exporter`, or `redis-exporter` targets.

Consequences:

- Do not filter app HTTP or Books metric selectors by `deployment_target` unless the app metric pipeline is intentionally changed to add that label.
- Use `job` and `instance` variables for app metric panels.
- Use `target_info` for app node identity, deployment target, and deployed SHA.
- If a panel needs app metrics and deployed version together, use a PromQL join against `target_info`; otherwise keep the queries separate.
- V1 local parity decision: add local `postgres-exporter` and `redis-exporter` under the observability profile before accepting the Data panels.
- V1 local Node Fleet decision: do not add local `node-exporter` until Docker Desktop/WSL host-metric behavior is verified. Local Node panels must display a local-limited state instead of pretending to show a four-node topology.

## Shared Variables

Keep the Command Center simple. It should expose only variables that are necessary for first-open use:

```text
deployment_target
service_job
app_instance
```

Detailed dashboards can add these variables where they are useful:

```text
node
http_route
status_code
book_operation
book_outcome
service_name
```

Suggested Prometheus variable sources:

```promql
label_values(up, deployment_target)
label_values(up{deployment_target=~"$deployment_target"}, node)
label_values(target_info{deployment_target=~"$deployment_target", service_version!=""}, job)
label_values(target_info{deployment_target=~"$deployment_target", job=~"$service_job"}, instance)
label_values(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}, http_route)
label_values(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}, http_response_status_code)
label_values(books_operations_total{job=~"$service_job", instance=~"$app_instance"}, books_operation)
label_values(books_operations_total{job=~"$service_job", instance=~"$app_instance"}, books_outcome)
```

Use a textbox variable for Tempo service queries:

```text
service_name = BlazorAutoApp
```

If the exact ASP.NET Core metric name differs between local and deployed targets, validate with:

```promql
{__name__=~"http_server_request_duration.*"}
```

Then use the deployed metric name consistently. Current smoke scripts already handle these candidates:

```text
http_server_request_duration_seconds_count
http_server_request_duration_milliseconds_count
http_server_request_duration_count
```

The dashboard implementation should choose the active name and update smoke tests so a metric rename cannot silently break the dashboards.

## Dashboard 00: Books Observability Command Center

Purpose: impressive first page and fastest answer to "is the system okay?"

Top row, stat panels:

- Overall health: green only when app metrics exist, app telemetry instances have current `service_version`, expected infrastructure targets are up for the selected target, and no alerts are firing. Local Docker uses the local-limited expected node target set until local node-exporter parity is deliberately added.
- Deployed version: latest Git SHA from `target_info.service_version`, one value per app node.
- App telemetry instances: count of app instances currently represented by `target_info`. This proves telemetry/version presence, not public readiness.
- Request rate: total app requests per second.
- Error rate: 5xx percentage.
- p95 latency: HTTP p95 over 5 minutes.
- Active alerts: firing alert count.
- Telemetry budget: Prometheus active series versus budget.

Core queries:

```promql
count(count by (host_name, service_version) (target_info{deployment_target=~"$deployment_target", job=~"$service_job", instance=~"$app_instance", service_version!=""}))
sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m]))
sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance", http_response_status_code=~"5.."}[5m]))
/
clamp_min(sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m])), 0.001)
histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket{job=~"$service_job", instance=~"$app_instance"}[5m])) by (le))
count(ALERTS{alertstate="firing"})
prometheus_tsdb_head_series
```

Second row, health matrix:

- app telemetry instances: `node-app1/node-app2` or `cloud-app1/cloud-app2` from `target_info`.
- ingress/backend node.
- data node.
- PostgreSQL.
- Redis.
- Alloy per node.
- node-exporter per node.

Use a state timeline or table panel with:

```promql
up{deployment_target=~"$deployment_target", job=~"alloy|node-exporter|postgres-exporter|redis-exporter"}
```

For local Docker, this matrix should show only the local expected observability targets plus a local-limited node note until local node-exporter parity is deliberately added.

Third row, traffic and latency:

- request rate by route.
- p95 latency by route.
- error rate by app metric `instance`, with a companion `target_info` table showing the human node name.

Fourth row, investigation launcher:

- recent app errors from Loki.
- recent traces from Tempo.
- dashboard links to Application And Books, Infrastructure And Data, Telemetry And Alerts, and Logs And Traces.

Design details:

- Use thresholds: green normal, amber warning, red critical.
- Use units: `reqps`, `percentunit`, `ms`, `bytes`, `short`.
- Keep the first visible viewport dense but not cramped.
- Add a short text panel at the bottom explaining the dashboard purpose and safe next clicks.

Definition of done:

- This dashboard is the Grafana home dashboard.
- It renders with useful data in local Docker, LocalCluster, and Cloud.
- It identifies both app telemetry instances and their deployed SHA.
- It has links to all V1 dashboards.
- It does not depend on public probes, Cloudflare APIs, or target-specific IPs.

## Dashboard 01: Application And Books

Purpose: user-facing app health plus books-specific behavior in one screen.

Rows:

- Overview: request rate, error rate, p50/p95/p99 latency, current app version.
- Route breakdown: rate, latency, errors by `http_route`.
- Instance comparison: same route split by app metric `instance`, with a companion `target_info` table for the human node name.
- Status codes: 2xx/3xx/4xx/5xx distribution.
- Runtime health: process/runtime metrics if emitted by OpenTelemetry runtime instrumentation.
- Book operation volume by operation and outcome.
- Book operation p95 duration by operation.
- Book errors by operation.
- Recent domain logs.
- Trace list for `books.*` spans.

Core queries:

```promql
sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m])) by (http_route)
sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance", http_response_status_code=~"5.."}[5m])) by (instance)
histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket{job=~"$service_job", instance=~"$app_instance"}[5m])) by (le, http_route))
sum(rate(http_server_request_duration_seconds_count{job=~"$service_job", instance=~"$app_instance"}[5m])) by (http_response_status_code)
target_info{deployment_target=~"$deployment_target", job=~"$service_job", instance=~"$app_instance", service_version!="", host_name=~"$node"}
```

If runtime metrics are present, add:

```promql
dotnet_process_memory_working_set_bytes
dotnet_gc_collections_total
dotnet_thread_pool_thread_count_total
dotnet_exceptions_total
```

If names differ, discover with:

```promql
{__name__=~".*dotnet.*|.*process.*|.*runtime.*"}
```

Books domain queries:

```promql
sum(rate(books_operations_total{job=~"$service_job", instance=~"$app_instance"}[5m])) by (books_operation, books_outcome)
histogram_quantile(0.95, sum(rate(books_operation_duration_milliseconds_bucket{job=~"$service_job", instance=~"$app_instance"}[5m])) by (le, books_operation))
sum(rate(books_operations_total{job=~"$service_job", instance=~"$app_instance", books_outcome="error"}[5m])) by (books_operation)
```

Loki examples:

```logql
{service="web", deployment_target=~"$deployment_target"} |= "Created book"
{service="web", deployment_target=~"$deployment_target"} |= "Error"
```

Tempo examples:

```traceql
{ span.name =~ "books.*" }
```

Important constraint:

- Continue not logging book titles or other user content into centralized logs.

Future app metrics, only if needed:

- cache hit/miss counters with labels `cache_area` and `outcome`.
- seed duration and seed result counters.
- database query duration is already available through Npgsql/OpenTelemetry; do not add query text labels.

Definition of done:

- A reviewer can see that this is a books app, not a generic infrastructure demo.
- A 5xx issue can be tied to route and app node within one screen.
- The user can distinguish no traffic from broken telemetry.
- Domain metrics stay low-cardinality.
- No book title, user ID, request ID, or trace ID is used as a metric label.
- The dashboard links from bad panels to Logs and Traces with matching variables where possible.

## Dashboard 02: Infrastructure And Data

Purpose: show the distributed four-node architecture, PostgreSQL, and Redis clearly.

Node rows:

- Node map: one table for each target node with role, target, scrape health, and up/down state.
- CPU: normalized CPU usage by node.
- Memory: available memory percentage and absolute available memory.
- Disk: root filesystem usage and free space.
- Network: receive/transmit rate by node.
- Saturation: load average or CPU pressure where available.

Core queries:

```promql
up{deployment_target=~"$deployment_target", job="node-exporter"}
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{deployment_target=~"$deployment_target", mode="idle"}[5m])))
100 * (1 - node_memory_MemAvailable_bytes{deployment_target=~"$deployment_target"} / node_memory_MemTotal_bytes{deployment_target=~"$deployment_target"})
node_memory_MemAvailable_bytes{deployment_target=~"$deployment_target"}
100 * (1 - node_filesystem_avail_bytes{deployment_target=~"$deployment_target", fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{deployment_target=~"$deployment_target", fstype!~"tmpfs|overlay"})
sum(rate(node_network_receive_bytes_total{deployment_target=~"$deployment_target", device!~"lo|docker.*|br-.*|veth.*"}[5m])) by (node)
sum(rate(node_network_transmit_bytes_total{deployment_target=~"$deployment_target", device!~"lo|docker.*|br-.*|veth.*"}[5m])) by (node)
node_load1{deployment_target=~"$deployment_target"}
```

Container metrics note:

- Do not pretend we have full container CPU/memory dashboards unless that metric source exists.
- Current guardrails use Docker inspect and doctors for OOMKilled state.
- If live container metrics become necessary, make a separate mini-plan first. Prefer an Alloy-native or Docker-native approach if practical. Add cAdvisor only if the benefit justifies one extra exporter per node.

Definition of done:

- A viewer can instantly see the four-node topology.
- CPU and memory are normalized by node, not raw values that hide differences.
- Disk panels exclude noisy pseudo filesystems.
- Local Docker clearly states that full node fleet metrics are only available on LocalCluster and Cloud.

PostgreSQL rows:

- PostgreSQL up.
- database size.
- active backends/connections.
- transactions per second.
- rollback rate.
- cache hit ratio.
- locks and deadlocks.

Redis rows:

- Redis up.
- memory used.
- connected clients.
- operations per second.
- keyspace hit ratio.
- rejected connections or errors where exported.

Core PostgreSQL queries:

```promql
pg_up{deployment_target=~"$deployment_target"}
pg_database_size_bytes{deployment_target=~"$deployment_target"}
pg_stat_database_numbackends{deployment_target=~"$deployment_target"}
sum(rate(pg_stat_database_xact_commit{deployment_target=~"$deployment_target"}[5m])) by (datname)
sum(rate(pg_stat_database_xact_rollback{deployment_target=~"$deployment_target"}[5m])) by (datname)
sum(pg_stat_database_blks_hit{deployment_target=~"$deployment_target"}) / clamp_min(sum(pg_stat_database_blks_hit{deployment_target=~"$deployment_target"} + pg_stat_database_blks_read{deployment_target=~"$deployment_target"}), 1)
rate(pg_stat_database_deadlocks{deployment_target=~"$deployment_target"}[5m])
```

Core Redis queries:

```promql
redis_up{deployment_target=~"$deployment_target"}
redis_memory_used_bytes{deployment_target=~"$deployment_target"}
redis_connected_clients{deployment_target=~"$deployment_target"}
rate(redis_commands_processed_total{deployment_target=~"$deployment_target"}[5m])
rate(redis_keyspace_hits_total{deployment_target=~"$deployment_target"}[5m]) / clamp_min(rate(redis_keyspace_hits_total{deployment_target=~"$deployment_target"}[5m]) + rate(redis_keyspace_misses_total{deployment_target=~"$deployment_target"}[5m]), 1)
rate(redis_rejected_connections_total{deployment_target=~"$deployment_target"}[5m])
```

Definition of done:

- The data node has its own dashboard.
- PostgreSQL and Redis can be evaluated without SSH.
- Panels avoid exposing passwords, connection strings, or query text.
- Local Docker Data panels are considered complete only after local PostgreSQL and Redis exporters are added under the observability profile.

## Dashboard 03: Telemetry And Alerts

Purpose: prove the observability stack itself is healthy and make alerting understandable before external notifications are configured.

Telemetry rows:

- Prometheus target health by job.
- Prometheus active series, scrape samples, scrape duration.
- Alertmanager connection and firing alerts.
- Loki stream count and ingestion rate.
- Tempo trace ingestion and query readiness where metrics are available.
- Alloy exporter failures and queue pressure.
- Retention/disk budget reminders.
- firing alerts.
- pending alerts.
- alerts by severity.
- runbook links.
- target down details.
- telemetry missing/cardinality warnings.

Core queries:

```promql
up{deployment_target=~"$deployment_target"}
prometheus_tsdb_head_series
rate(prometheus_tsdb_head_samples_appended_total[5m])
scrape_duration_seconds{deployment_target=~"$deployment_target"}
count(ALERTS{alertstate="firing"}) by (alertname, severity)
sum(rate(otelcol_exporter_send_failed_spans_total[5m]))
sum(rate(otelcol_exporter_send_failed_metric_points_total[5m]))
ALERTS{alertstate="firing"}
ALERTS{alertstate="pending"}
count by (alertname, severity, runbook) (ALERTS{alertstate=~"firing|pending"})
up{deployment_target=~"$deployment_target"} == 0
```

Loki stream count can be shown with a Loki metric query if Grafana supports it in the target panel, otherwise keep it in the doctor and show log ingestion volume:

```logql
sum by (service, node) (rate({deployment_target=~"$deployment_target"}[5m]))
```

Definition of done:

- A broken dashboard is distinguishable from a broken app.
- The same budgets used by doctors are visible in Grafana.
- The dashboard links to telemetry and alert runbooks.
- Alert panels do not filter by `deployment_target` unless the alert rule is known to preserve that label.
- It states clearly that external Slack/PagerDuty/email/webhook notification delivery is post-v1 until a real destination secret is provided.

Runbook links should point to these repo files in panel text, and to the equivalent GitHub URLs when a clickable Grafana link is needed:

```text
Deployment/Common/observability/runbooks/application-server-errors.md
Deployment/Common/observability/runbooks/observability-target-down.md
Deployment/Common/observability/runbooks/telemetry-cardinality.md
Deployment/Common/observability/runbooks/telemetry-missing.md
```

## Dashboard 04: Logs And Traces

Purpose: make investigation feel connected, not like three separate tools.

Rows:

- app error logs.
- warning/error log rate by node.
- logs for selected node/service.
- recent traces.
- slow traces or traces with errors if Tempo query support and attributes allow it.
- instructions for clicking from log `TraceId` to Tempo.

Loki examples:

```logql
{service="web", deployment_target=~"$deployment_target"} |= "Error"
sum by (node) (rate({service="web", deployment_target=~"$deployment_target"} |= "Error" [5m]))
{service="web", deployment_target=~"$deployment_target", node=~"$node"}
```

Tempo examples:

```traceql
{ resource.service.name =~ "$service_name" }
{ resource.service.name =~ "$service_name" && status = error }
{ span.books.operation =~ "$book_operation" }
```

Datasource link requirement:

- Preserve the existing Loki derived field from `TraceId` to Tempo.
- Add panel descriptions explaining that log rows with `TraceId` can open the related trace.

Definition of done:

- A request error can be followed from dashboard stat, to logs, to trace.
- No sensitive request bodies, cookies, auth headers, book titles, passwords, or connection strings appear in log panels.

## Visual Design Standard

Use a consistent visual system:

- Command Center: top row stat panels, then health matrix, then supporting charts.
- Detailed dashboards: rows with a clear story, not random panels.
- Use panel descriptions. They should explain what "bad" means and where to go next.
- Use dashboard links in the top right.
- Use the same variable order everywhere.
- Use `transparent=false` and normal Grafana panel framing for readability.
- Avoid novelty visualizations unless they answer a real operational question.
- Prefer tables for inventory and version state.
- Prefer time series for trends.
- Prefer stat/gauge panels for "right now" state.
- Use thresholds consistently:
  - green: healthy.
  - amber: degraded or budget warning.
  - red: broken or urgent.

Suggested first row layout:

```text
Overall Health | Version | App Telemetry | RPS | Error % | p95 | Firing Alerts | Series Budget
```

## Implementation Strategy

### Phase 0: Dashboard Inventory And Metric Discovery

Status: planned.

Work:

- [ ] Query Prometheus for exact active metric names in local Docker.
- [ ] Query Prometheus for exact active metric names in LocalCluster.
- [ ] Query Prometheus for exact active metric names in Cloud.
- [ ] Save a short metric inventory in this plan or a generated `DashboardMetrics.md` if the list is long.
- [ ] Confirm whether runtime metrics exist and what names they use.
- [ ] Confirm PostgreSQL and Redis exporter metric names before finalizing queries.
- [ ] Confirm that app HTTP and Books metrics still lack `deployment_target` and `host_name`; if they gain those labels later, update the metric contract and dashboard queries deliberately.
- [ ] Add local Docker `postgres-exporter` and `redis-exporter` parity under the observability profile before accepting Data panels.
- [ ] Confirm local Docker node-exporter remains intentionally out of V1 and that local Infrastructure node panels show a local-limited state.

Verification:

```bash
curl -fsS 'http://127.0.0.1:9090/api/v1/label/__name__/values'
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=up'
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=target_info'
```

Do not proceed if a planned panel has no metric source.

### Phase 1: Dashboard-As-Code Helper

Status: planned.

Work:

- [ ] Add a small Python generator or validator under:

```text
Deployment/Common/observability/grafana/
```

- [ ] Prefer a lightweight repo-local Python script over hand-editing giant JSON.
- [ ] Generate stable dashboard JSON with deterministic panel IDs, UIDs, titles, links, variables, and grid positions.
- [ ] Keep generated JSON committed, because Grafana provisioning consumes JSON directly.

Suggested files:

```text
Deployment/Common/observability/grafana/generate-dashboards.py
Deployment/Common/observability/grafana/dashboard_spec.py
Deployment/Common/observability/grafana/dashboards/00-books-command-center.json
Deployment/Common/observability/grafana/dashboards/01-application-and-books.json
Deployment/Common/observability/grafana/dashboards/02-infrastructure-and-data.json
Deployment/Common/observability/grafana/dashboards/03-telemetry-and-alerts.json
Deployment/Common/observability/grafana/dashboards/04-logs-and-traces.json
```

Why not start with Grafonnet:

- Grafonnet is valid, but it adds another toolchain before we need it.
- A small Python generator fits the current repo and CI better.
- If dashboards grow beyond what Python can keep clean, revisit Grafonnet later.

Verification:

```bash
python Deployment/Common/observability/grafana/generate-dashboards.py --check
python -m json.tool Deployment/Common/observability/grafana/dashboards/00-books-command-center.json >/dev/null
bash Deployment/Common/observability/scripts/validate-observability.sh
```

### Phase 2: Build Command Center First

Status: planned.

Work:

- [ ] Create `00-books-command-center.json`.
- [ ] Set it as the default home dashboard for local, LocalCluster, and Cloud Grafana.
- [ ] Add links to every V1 dashboard. Every link must point to an implemented dashboard.
- [ ] Add deployment target, service job, and app instance variables.
- [ ] Add the top stat row and health matrix.
- [ ] Add app logs and recent traces panels.

Verification:

```powershell
.\RunLocal.ps1 -NoBrowser -Observability
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

Then open:

```text
http://localhost:3000
```

Expected result:

- The first page is the Command Center.
- It immediately shows app telemetry health, version, traffic, latency, alerts, and telemetry budget.

### Phase 2A: Deployment Timeline Annotations

Status: post-v1.

Work:

- [ ] Do not implement timeline annotations in V1.
- [ ] When this becomes V1+ work, add a private Grafana annotation writer script with idempotency and duplicate prevention.
- [ ] Call it only after successful LocalCluster or Cloud CD observability doctor.
- [ ] Include Git SHA, workflow run URL, deployment target, and migration mode.
- [ ] Keep writes private through localhost or Ansible/SSH on the backend node.

Verification:

- V1 Command Center has no annotation panel that implies deployment events exist.
- Current deployed SHA remains visible from `target_info`.
- Future annotation write failures cannot fail the app deployment unless explicitly configured as strict.

### Phase 3: Build Detailed Dashboards

Status: planned.

Work:

- [ ] Create Application And Books dashboard.
- [ ] Create Infrastructure And Data dashboard.
- [ ] Create Telemetry And Alerts dashboard.
- [ ] Create Logs And Traces dashboard.

Verification:

- Every dashboard appears in Grafana search.
- Command Center, Application And Books, Telemetry And Alerts, and Logs And Traces have useful data in local Docker.
- Infrastructure And Data has useful PostgreSQL and Redis data in local Docker after local exporter parity is added.
- Infrastructure And Data has full node, PostgreSQL, and Redis data in LocalCluster and Cloud.
- Dashboard links work.
- Variables work.
- No panel has a broken datasource.

### Phase 4: Strengthen Validation

Status: planned.

Work:

- [ ] Extend `validate-observability.sh` to require all dashboard files.
- [ ] Validate dashboard JSON parses.
- [ ] Validate dashboard UIDs are unique.
- [ ] Validate datasource UIDs are only `prometheus`, `loki`, and `tempo`.
- [ ] Validate no target-specific hostnames, public domains, private IPs, or secrets are committed under Common.
- [ ] Validate every dashboard has tags, variables, and a non-empty title.
- [ ] Validate all runbook links point to existing files.
- [ ] Validate dashboard links do not point to placeholders or missing dashboards.
- [ ] Extend smoke tests to assert the Command Center and every detailed dashboard are provisioned.
- [ ] Add a runtime check that opening Grafana root `/` renders or redirects to the Command Center, not only that the dashboard exists in search.

Potential API checks:

```bash
curl -fsS 'http://localhost:3000/api/search?query=Books%20Observability%20Command%20Center'
curl -fsS 'http://localhost:3000/api/search?query=Application%20And%20Books'
curl -fsS 'http://localhost:3000/api/search?query=Infrastructure%20And%20Data'
curl -fsS 'http://localhost:3000/api/search?query=Telemetry%20And%20Alerts'
curl -fsS 'http://localhost:3000/api/search?query=Logs%20And%20Traces'
```

### Phase 5: Screenshot And First-Impression Testing

Status: planned.

Work:

- [ ] Run the local observability smoke script immediately before screenshots so app metrics, logs, and traces exist.
- [ ] Add a small opt-in Playwright check for local Grafana using `RUN_E2E=1` and `RUN_OBSERVABILITY_E2E=1`.
- [ ] Keep the Playwright check focused on first-open UX: home dashboard, stable headings, implemented dashboard links, no obvious Grafana error text, and one screenshot artifact.
- [ ] Do not assert exact metric values, panel IDs, pixel-perfect charts, colors, or Grafana internals in Playwright.
- [ ] Verify the Command Center is not blank.
- [ ] Verify key text appears: `Books Observability Command Center`, `Overall Health`, `Deployed Version`, `App Telemetry`, `Error Rate`, `p95`.
- [ ] Verify no panel displays obvious `No data` on a fresh smoke run except panels that are documented as "no current errors".
- [ ] Capture screenshots into ignored local output, not git.

Suggested ignored output:

```text
artifacts/observability-screenshots/
```

Do not store screenshots in the repo unless the user explicitly asks for visual regression fixtures.

### Phase 6: LocalCluster Deployment

Status: planned.

Work:

- [ ] Deploy through LocalCluster CD.
- [ ] Run LocalCluster acceptance.
- [ ] Run LocalCluster observability doctor.
- [ ] Open the tunnel and verify the first page.

Commands:

```bash
CONTROLPC_SSH_TARGET=jacob@node-main bash ./Deployment/LocalCluster/Scripts/open-observability-tunnel.sh
```

Definition of done:

- Command Center opens through the tunnel.
- LocalCluster app nodes show distinct names and the deployed Git SHA.
- Infrastructure And Data shows all four LocalCluster nodes, PostgreSQL, and Redis.
- Telemetry And Alerts shows Prometheus, Alertmanager, Loki, Tempo, Alloy, node-exporter, postgres-exporter, redis-exporter, and alert health.

### Phase 7: Cloud Deployment

Status: planned.

Work:

- [ ] Deploy through Cloud CD.
- [ ] Run Cloud acceptance.
- [ ] Run Cloud observability doctor.
- [ ] Open the Cloud tunnel and verify the first page.

Commands:

```bash
bash ./Deployment/Cloud/Scripts/open-observability-tunnel.sh
```

Definition of done:

- Command Center opens through the tunnel.
- Cloud app nodes show distinct names and the deployed Git SHA.
- Infrastructure And Data shows all four Cloud nodes, PostgreSQL, and Redis.
- No observability ports are public.

## Testing Matrix

Before any deployment:

```bash
git diff --check
bash Deployment/Common/observability/scripts/validate-observability.sh
bash Deployment/Common/Scripts/validate-common-release.sh
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
bash Deployment/Cloud/Scripts/validate-cloud-settings.sh
docker compose --profile observability config --quiet
```

Local runtime:

```powershell
.\RunLocal.ps1 -NoBrowser -Observability
pwsh -File .\docker\observability\smoke-local-observability.ps1
$env:RUN_E2E='1'; $env:RUN_OBSERVABILITY_E2E='1'; $env:GRAFANA_URL='http://localhost:3000'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "FullyQualifiedName~GrafanaObservabilityE2ETests"
```

Shared smoke from WSL or Linux:

```bash
bash ./Deployment/Common/observability/scripts/smoke-observability.sh
```

.NET regression:

```powershell
dotnet test .\BlazorAutoApp.sln --no-restore
$env:RUN_E2E='1'; dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"
```

CI/CD:

- CI must pass.
- LocalCluster CD must pass before declaring LocalCluster dashboards done.
- Cloud CD must pass before declaring Cloud dashboards done.

## Performance And Memory Guardrails

Dashboard changes should not materially increase memory usage, but bad queries can still hurt Prometheus, Loki, or Grafana.

Rules:

- Default time range: 30 minutes for Command Center, 1 hour for detailed dashboards.
- Default refresh: 30s for Command Center, 1m for detailed dashboards.
- Avoid unbounded LogQL queries.
- Avoid high-cardinality `by (...)` groupings.
- Use `topk(10, ...)` when showing worst offenders.
- Prefer `rate(...[5m])` over instant raw counters.
- Keep Tempo trace panels narrow and time-bounded.
- Keep Command Center below roughly 20 panels.

Validation:

- Run cardinality checks after local smoke.
- Confirm Prometheus active series remains below the V1 budget of 25000.
- Confirm Loki stream count remains below existing budgets.
- Confirm no observability container reports OOMKilled.

## What Not To Build Yet

These are intentionally post-v1 dashboard improvements because they require extra instrumentation or security design:

- Native Caddy metrics panels. Caddy metrics need a private host-service scrape design first.
- Native cloudflared metrics panels. cloudflared metrics need controlled private exposure first.
- Continuous public blackbox probe panels. Public/origin health is currently verified by deployment acceptance scripts.
- Deployment timeline annotations. Add only after the private Grafana annotation writer is designed and tested.
- Full live container CPU/memory dashboard. Add only after choosing a container metrics source.
- External alert delivery dashboards for Slack/PagerDuty/email. Add only after a real destination secret exists.
- Business KPIs that require storing or labeling sensitive user/book data.

## Acceptance Criteria

The dashboard project is complete when:

- Opening Grafana shows `Books Observability Command Center` automatically.
- The Command Center answers health, version, traffic, latency, alerts, and telemetry budget in the first viewport.
- The dashboard set includes Command Center, Application And Books, Infrastructure And Data, Telemetry And Alerts, and Logs And Traces.
- Dashboard links create a clear drill-down path.
- Local Docker, LocalCluster, and Cloud all render the dashboards from the same Common assets.
- Local Docker includes PostgreSQL and Redis exporter parity for Data panels.
- LocalCluster and Cloud dashboards identify both app telemetry instances separately.
- Deployed Git SHA is visible per app node.
- PostgreSQL and Redis health/performance are visible.
- Alert state and runbook links are visible.
- Logs can link to traces through the existing Tempo derived field.
- No public observability ports are introduced.
- No new observability node is introduced.
- No target-specific IPs, hostnames, public domains, or secrets are committed under Common.
- Smoke tests and doctors verify the Command Center is provisioned.
- CI, LocalCluster CD, and Cloud CD pass after the changes.

## Final Reviewer Checklist

When this is implemented, review as if it were a customer demo:

- Does the first screen make the distributed architecture obvious?
- Can a non-author immediately tell whether LocalCluster or Cloud is being viewed?
- Can you see both app telemetry instances and their deployed SHA without opening Explore?
- Can you tell whether PostgreSQL or Redis is unhealthy?
- Can you tell whether telemetry is broken versus the app being broken?
- Can you click from a bad stat to the relevant detail dashboard?
- Can you click from a log with `TraceId` to a trace?
- Are there any blank panels during normal healthy operation?
- Are there any scary panels that look broken only because no errors are currently happening?
- Are all units and thresholds professional?
- Are dashboard titles specific to the books app?
- Is there any stale "ship" naming outside real book data?
- Are all changes safely versioned and deployable through the existing CI/CD paths?
