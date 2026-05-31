# Observability Guide

This is the durable operator guide and architecture reference for the current
Books observability stack. It replaces the historical implementation plan:
keep this file, not the phase-by-phase rollout notes.

## Purpose

The stack gives a private, self-hosted operator view for the existing app across
three targets:

```text
local Docker
LocalCluster at books.jacobgrum.com
Cloud at bookscloud.jacobgrum.com
```

It answers:

- Is the app healthy from the public edge and from origin?
- Are both app nodes in a deployed target serving traffic?
- Which Git SHA is deployed per app instance?
- Are requests, latency, errors, rate limits, book operations, PostgreSQL, Redis,
  host resources, logs, traces, and alerts behaving normally?
- Is the telemetry pipeline itself healthy?

It is not a public monitoring service, a SIEM, a long-term audit log, or a
requirement for app startup. The app must keep serving requests if observability
is down.

## Current Topology

Local Docker:

```text
web
postgres
redis
redisinsight
optional observability profile:
  grafana
  prometheus
  alertmanager
  loki
  tempo
  alloy
  postgres-exporter
  redis-exporter
```

LocalCluster:

```text
node-main  - Caddy, cloudflared, GitHub runner, observability backend
node-app1  - app container, Alloy agent, node-exporter
node-app2  - app container, Alloy agent, node-exporter
node-db    - PostgreSQL, Redis, Alloy agent, node-exporter, database exporters
```

Cloud:

```text
cloud-main - Caddy, cloudflared, SSH bastion, observability backend
cloud-app1 - app container, Alloy agent, node-exporter
cloud-app2 - app container, Alloy agent, node-exporter
cloud-db   - PostgreSQL, Redis, Alloy agent, node-exporter, database exporters
```

The deployed shape intentionally uses existing nodes only. There is no
`node-obs`, no `cloud-obs`, and no public observability endpoint.

## Architecture

Signal flow:

```text
Browser / external check
        |
Cloudflare
        |
cloudflared on ingress node
        |
Caddy on ingress node
        |
        +--> app node 1: Blazor app container
        +--> app node 2: Blazor app container
                   |
                   +--> data node: PostgreSQL container
                   +--> data node: Redis container

Every deployed node:
  Alloy + node-exporter
    - receives local app OTLP where applicable
    - scrapes local node metrics
    - tails local Docker logs
    - forwards metrics/logs/traces to the backend

Data node:
  postgres-exporter
  redis-exporter

Backend node:
  Grafana
  Prometheus
  Alertmanager
  Loki
  Tempo
```

Component responsibilities:

- OpenTelemetry: app metrics/traces/log correlation emitted by the .NET app.
- Grafana Alloy: per-node collector for OTLP, Docker logs, local metrics, memory
  limiting, batching, relabeling, and forwarding.
- Prometheus: metrics storage and alert rule evaluation.
- Alertmanager: alert routing, grouping, silencing, and local alert state.
- Loki: centralized logs. Seq is no longer part of this stack.
- Tempo: distributed trace storage.
- Grafana: dashboards and Explore UI.
- node-exporter: host metrics.
- postgres-exporter: PostgreSQL metrics.
- redis-exporter: Redis metrics.

App telemetry:

```text
Blazor app -> OTLP gRPC -> local Alloy -> Prometheus and Tempo
Blazor app stdout/stderr -> Docker logs -> Alloy -> Loki
```

PostgreSQL and Redis telemetry:

```text
database container logs -> Alloy -> Loki
database exporters      -> Prometheus scrape -> Prometheus
```

Caddy and cloudflared:

- service health and routing are verified by deployment acceptance scripts.
- logs can be collected through host logging paths where configured.
- native Caddy/cloudflared Prometheus metrics are post-v1 work because exposing
  host-service metrics to containerized Prometheus needs a private exposure
  design that does not publish admin or metrics ports.

## Source Of Truth

Shared, target-neutral observability assets live under:

```text
Deployment/Common/observability/
  alertmanager/
  grafana/
    dashboard_spec.py
    generate-dashboards.py
    dashboards/
    provisioning/
  prometheus/rules/
  runbooks/
  scripts/
```

Target-specific wiring lives under:

```text
docker/observability/
Deployment/LocalCluster/ansible/roles/observability_backend/
Deployment/LocalCluster/ansible/roles/observability_agent/
Deployment/LocalCluster/inventory/prod/group_vars/all.yml
Deployment/Cloud/ansible/roles/observability_backend/
Deployment/Cloud/ansible/roles/observability_agent/
Deployment/Cloud/inventory/prod/group_vars/all.yml
```

Ownership rules:

- Dashboards, datasource provisioning, alert rules, runbooks, and shared checks
  belong in `Deployment/Common/observability`.
- Compose files, firewall rules, inventories, retention values, scrape targets,
  and secrets are target-specific.
- Do not import LocalCluster deployment files into Cloud, or Cloud deployment
  files into LocalCluster.
- Do not commit target-specific hostnames, IPs, generated inventories, Grafana
  SQLite data, Prometheus/Loki/Tempo data, or secrets under Common.

Important app/runtime configuration:

```text
Observability__OpenTelemetry__Enabled
Observability__OpenTelemetry__Endpoint
Observability__OpenTelemetry__Protocol
Observability__OpenTelemetry__TraceSampleRatio
Observability__OpenTelemetry__DeploymentTarget
APP_VERSION
```

`APP_VERSION` is passed into deployed app containers so dashboards can display
the Git SHA through `service_version`.

## Access

Observability services are private. Do not expose Grafana, Prometheus,
Alertmanager, Loki, Tempo, Alloy, node-exporter, postgres-exporter, or
redis-exporter publicly.

Local Docker:

```powershell
.\RunLocal.ps1 -Observability
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

Open:

```text
http://localhost:3000
```

Local ports bind to `127.0.0.1`:

```text
Grafana:      http://localhost:3000
Prometheus:   http://localhost:9090
Alertmanager: http://localhost:9093
Loki:         http://localhost:3100
Tempo:        http://localhost:3200
Alloy:        http://localhost:12345
```

Deployed private ports:

```text
Grafana              3000
Prometheus           9090
Alertmanager         9093
Loki                 3100
Tempo HTTP           3200
OTLP gRPC            4317
OTLP HTTP            4318
Alloy HTTP/debug     12345
node-exporter        9100
postgres-exporter    9187
redis-exporter       9121
Caddy admin/metrics  2019  not enabled in v1
cloudflared metrics  2000  not enabled in v1
blackbox_exporter    9115  not enabled in v1
```

Firewall/exposure rules:

- public clients must not reach these ports.
- app nodes can send OTLP to Alloy.
- Alloy can forward to Prometheus remote write, Loki, and Tempo on the backend
  node.
- the backend node can scrape Alloy/node-exporter on all nodes and database
  exporters on the data node.
- Caddy/cloudflared public routing is checked by deployment acceptance, not by
  public observability ports.

LocalCluster from CurrentPC:

```bash
cd "$(git rev-parse --show-toplevel)"
CONTROLPC_SSH_TARGET=jacob@node-main bash ./Deployment/LocalCluster/Scripts/open-observability-tunnel.sh
```

Then open:

```text
http://127.0.0.1:3000
```

## Health Endpoints

Public health endpoints:

```text
/health/live
/health/ready
/health
```

`/health/ready` is the endpoint used by deployment acceptance, Caddy upstream
checks, and public CurrentPC checks. It must stay safe to expose publicly and
must not reveal secrets.

Version and node identity are exposed to observability through OpenTelemetry
resource attributes, especially `service_version`, `deployment_target`, and
`host_name`. The dashboards use those labels instead of requiring a public
version endpoint.

If `node-main` is not resolvable from CurrentPC:

```bash
CONTROLPC_SSH_TARGET=jacob@<node-main-lan-ip> bash ./Deployment/LocalCluster/Scripts/open-observability-tunnel.sh
```

Cloud from CurrentPC:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/open-observability-tunnel.sh
```

Then open:

```text
http://127.0.0.1:3000
```

## Dashboards

Grafana dashboards are generated from:

```text
Deployment/Common/observability/grafana/dashboard_spec.py
```

Generated dashboard JSON is committed under:

```text
Deployment/Common/observability/grafana/dashboards/
```

Main dashboards:

- `Books Observability Command Center`
- `Books Application And Books`
- `Books Infrastructure And Data`
- `Books Telemetry And Alerts`
- `Books Logs And Traces`

The command center is the default home dashboard. It shows:

- overall scrape/target health.
- deployed version count and version by app instance.
- app telemetry presence.
- request rate.
- error rate.
- p95 latency.
- firing alerts.
- active series budget.
- app logs and recent traces.

Use dashboard variables to narrow by:

```text
deployment_target
service_job
app_instance
node
http_route
status_code
book_operation
book_outcome
service_name
```

Operational notes:

- Empty "Recent App Errors" panels are healthy.
- The "App Version By Instance" table is the best quick check that both app
  nodes are emitting telemetry for the deployed SHA.
- Local Docker intentionally has less host-node coverage than LocalCluster and
  Cloud.
- Dashboard time ranges should stay short by default: local around 30 minutes,
  deployed dashboards around 1 hour unless investigating a specific incident.

## Useful Queries

Prometheus:

```promql
up{job="node-exporter"}
up{job="alloy"}
up{job="postgres-exporter"}
up{job="redis-exporter"}
target_info{service_version!=""}
sum(rate(http_server_request_duration_seconds_count[5m])) by (job, instance, http_route)
histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket[5m])) by (le, http_route))
sum(rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
prometheus_tsdb_head_series
```

Loki:

```logql
{service="web", deployment_target="localcluster"}
{service="web", deployment_target="localcluster", node="node-app1"}
{service="web", deployment_target="localcluster"} |= "Error"
```

Tempo:

```traceql
{ resource.service.name = "books" }
{ resource.service.name = "books" && status = error }
```

Safe Alertmanager route test:

```bash
bash ./Deployment/Common/observability/scripts/test-alertmanager-route.sh http://127.0.0.1:9093 local
```

## Validation

Local validation:

```powershell
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

Shared validation:

```bash
bash ./Deployment/Common/observability/scripts/validate-observability.sh
bash ./Deployment/Common/observability/scripts/smoke-observability.sh
bash ./Deployment/Common/observability/scripts/check-telemetry-cardinality.sh http://127.0.0.1:9090
bash ./Deployment/Common/observability/scripts/check-compose-resource-limits.sh
```

LocalCluster validation on ControlPC:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
bash ./Deployment/LocalCluster/Scripts/observability-doctor.sh
bash ./Deployment/LocalCluster/Scripts/observability-capacity-check.sh
```

Cloud validation from CurrentPC while Cloud SSH access is available, or from
GitHub Actions during `CD - Cloud`:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/acceptance-check.sh
bash ./Deployment/Cloud/Scripts/observability-doctor.sh
bash ./Deployment/Cloud/Scripts/observability-capacity-check.sh
bash ./Deployment/Cloud/Scripts/observability-resource-report.sh
```

The deployed observability doctors verify:

- backend containers on the ingress node.
- Alloy and node-exporter on every node.
- PostgreSQL and Redis exporters on the data node.
- backend health endpoints.
- Prometheus target health.
- app telemetry labels and Git-SHA-shaped service versions.
- Grafana dashboard provisioning.
- Prometheus connection to Alertmanager.
- no observability containers were OOMKilled.
- Prometheus active series is within budget.
- Loki stream count is within budget.

CI validates shared observability assets through `validate-observability.sh` and
also runs the normal deployment, YAML, shell, .NET, frontend, migration, and
Docker checks.

## Retention

Current retention is intentionally short.

Local Docker:

```text
Prometheus: 24h or 512MB
Loki:       24h
Tempo:      1h
Grafana:    persistent local Docker volume
```

LocalCluster:

```text
Prometheus: 7d or 6GB
Loki:       7d
Tempo:      24h
Path:       /opt/books-observability
```

Cloud:

```text
Prometheus: 7d or 4GB
Loki:       3d
Tempo:      24h
Path:       /opt/bookscloud-observability
```

Cloud observability data is disposable. `quick-destroy-cloud.sh` destroys Cloud
app data and Cloud-local metrics/logs/traces; GitHub environment secrets and
LocalCluster observability are not destroyed.

If history matters later, export Cloud telemetry to LocalCluster or a hosted
backend before destroying Cloud.

## Capacity And Guardrails

No documentation can guarantee "no memory problems." The guarantee here is that
the stack is bounded, checked, and fails open for the app:

- observability containers have memory and CPU limits.
- deployed preflights run capacity checks.
- Alloy uses a memory limiter before batching/exporting OTLP telemetry.
- retention and size limits are explicit.
- observability failure must not fail app requests.
- doctors fail on OOMKilled containers and telemetry/cardinality budget issues.

Current container starting limits:

```text
Backend node:
  Prometheus:   384m, CPU 0.50
  Alertmanager: 128m, CPU 0.15
  Loki:         256m, CPU 0.50
  Tempo:        384m, CPU 0.35
  Grafana:      256m, CPU 0.35
  Alloy:        192m deployed / 256m local, CPU 0.35

Agent/data services:
  node-exporter:      64m,  CPU 0.10
  postgres-exporter: 128m, CPU 0.15
  redis-exporter:     96m, CPU 0.10
```

Host rules:

- leave at least 25 percent memory headroom after startup.
- any OOMKilled observability container blocks rollout.
- repeated restarts block rollout.
- reduce trace sampling, log volume, scrape frequency, or retention before
  resizing nodes.
- resize an existing `node-main` or `cloud-main` only after measured pressure
  justifies it; do not add an observability node.

## Cardinality And Data Hygiene

Allowed metric labels:

```text
deployment_target
environment
node
service_name
service_version
route or http_route
method
status_class or http_response_status_code
operation
cache_scope
upstream
database
```

Forbidden metric labels:

```text
user_id
user_name
email
book_id
book_title
url
full_path
query_string
request_id
trace_id
span_id
exception_message
ip_address
user_agent
session_id
connection_string
```

Loki labels should identify the source, not the event. Allowed examples:

```text
deployment_target
environment
node
service_name
container
level
```

Forbidden Loki labels:

```text
request_id
trace_id
span_id
user_id
email
book_id
book_title
path
url
ip_address
user_agent
exception_message
```

Trace IDs and request IDs may be searchable structured fields, but they must not
be Loki labels.

Budget checks:

```text
Prometheus active series warning budget: 25,000
Loki stream warning budget:             300 LocalCluster / 200 Cloud
```

Logs must not contain request bodies, auth headers, cookies, tokens, connection
strings, or raw secrets. Health/static request logs are suppressed or downgraded
to avoid filling Loki with noise.

## Trace Sampling

Trace sampling is target-specific:

```text
Local Docker:   1.0 when observability is enabled
LocalCluster:   0.1 currently
Cloud:          0.1 currently
```

During a short debugging or demo window, temporarily increasing sampling can be
reasonable. Reset it afterward.

Emergency options:

```text
Observability__OpenTelemetry__TraceSampleRatio=0.0
Observability__OpenTelemetry__Enabled=false
```

OTLP export failure must not fail app startup or app requests.

## Alerts And Runbooks

Current Prometheus alert groups:

```text
application-observability
resource-guardrails
```

Current alerts:

```text
ApplicationHighServerErrorRate
ApplicationTelemetryMissing
ObservabilityTargetDown
PrometheusSeriesBudgetWarning
AlloyExporterQueueFailures
```

Runbooks live in:

```text
Deployment/Common/observability/runbooks/
```

Current runbooks:

```text
application-server-errors.md
observability-target-down.md
telemetry-cardinality.md
telemetry-missing.md
```

Alert routing:

- Prometheus evaluates rules.
- Alertmanager receives alerts.
- External destinations such as Slack, PagerDuty, or email are not configured
  yet because no destination secret has been provided.

Noise policy:

- do not alert on one failed scrape.
- do not alert on isolated 404s.
- do not alert on isolated 429s.
- do not page on GitHub-runner Cloudflare challenges if origin checks pass.

## Synthetic Traffic

Use the simulator to warm dashboards and verify telemetry:

```powershell
.\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
```

For a strict public matrix:

```powershell
.\RunSimulationMatrix.ps1 -LocalCluster -Cloud -IncludeWrites -RegisterSyntheticUsers -AllowDeployedWrites -Duration 60s
.\AnalyzeSimulationReports.ps1 -Latest 10
```

Normal smoke/demo simulation should show:

```text
unexpected 429: 0
cleanup: ok, leftovers=0
```

The simulator is not deployed with the app. It runs from the operator machine
and writes local reports under `artifacts/simulation/`.

## Security

Access:

- no public Grafana in v1.
- use SSH tunnels.
- later public access must use Cloudflare Access or equivalent authentication.

Secrets:

- LocalCluster secrets belong in Ansible Vault.
- Cloud secrets belong in GitHub environment secrets unless the Cloud secret
  model changes.
- no observability secrets in plaintext repo files.

Network:

- Prometheus scrapes private/loopback endpoints only.
- Alloy accepts OTLP only from app containers/private node paths.
- exporters bind loopback and private node addresses only.
- Hetzner Cloud firewalls expose none of the observability ports publicly.
- LocalCluster UFW and Docker user firewall rules allow only required internal
  scrape/OTLP paths.

Data:

- logs and traces are treated as sensitive.
- retention is short by default.
- labels stay low-cardinality.
- trace attributes must not include secrets or user content.

## Disable Or Recover

Local:

```powershell
docker compose --profile observability down
```

LocalCluster:

Set this in `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` and
deploy through LocalCluster CD:

```yaml
observability_enabled: false
```

Manual stop on ControlPC:

```bash
cd /opt/books-observability && docker compose down
cd /opt/books-observability/agent && docker compose down
```

Cloud:

- Use `quick-destroy-cloud.sh` if the goal is to stop Hetzner billing.
- Cloud observability history is destroyed with the Cloud servers.
- `quick-recreate-cloud-after-destruction.sh` recreates Cloud observability with
  empty metrics/logs/traces.

Emergency rollback order for observability pressure:

1. Lower `Observability__OpenTelemetry__TraceSampleRatio` or disable app OTLP.
2. Stop Tempo if traces are the pressure source.
3. Reduce log collection or shorten Loki retention.
4. Increase scrape intervals.
5. Stop the observability backend compose stack.
6. Re-run the normal app acceptance check.

Recovery should not require destroying PostgreSQL, Redis, Cloudflare Tunnel, or
the GitHub runner.

## Known Post-v1 Work

Keep these as deliberate future work, not accidental gaps:

- private Caddy metrics scrape design.
- private cloudflared metrics scrape design.
- blackbox_exporter for continuous public and origin probes.
- external Alertmanager destinations after a real destination secret exists.
- optional Cloud telemetry export before destroy if Cloud history becomes useful.
- richer deployment-status panels if GitHub workflow status becomes a first-class
  dashboard data source.
