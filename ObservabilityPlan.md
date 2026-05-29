# Observability Plan

Status: accepted architecture plan created on 2026-05-29 and hardened after repo scan plus official-doc review on 2026-05-29.

This document is a plan only. It does not authorize code, deployment, firewall, Cloudflare, Hetzner, or data-destruction changes until execution is explicitly requested.

This plan is intended to be complete enough that implementation can proceed in small verified slices without re-deciding the architecture.

## Handoff Instructions

If another agent implements this plan, it must follow these instructions exactly:

1. Read this whole document before editing files.
2. Do not replace the chosen stack with another observability product family.
3. Do not add servers, nodes, hosted SaaS requirements, public dashboards, or Cloudflare API-token dependencies.
4. Do not remove Seq until Phase 3 entry criteria are met.
5. Do not implement Cloud or LocalCluster observability before the local Docker observability slice is proven.
6. Do not change the app's deployment domains, app ports, database ports, Redis ports, or Cloudflare tunnel routing as part of observability.
7. Do not commit secrets, generated state files, generated inventories, Grafana SQLite databases, Prometheus/Loki/Tempo data, or local `.env` files.
8. Before every phase, run `git status --short` and preserve unrelated user changes.
9. Every phase must end with concrete verification commands and their result.
10. If a check fails, fix the implementation or update this plan before continuing to the next phase.

Implementation must be boring and incremental. The goal is a reliable operator view for the existing app, not a new platform.

## Existing Topology

The plan assumes these deployments already exist and must keep their shape:

```text
local Docker:
  web
  postgres
  redis
  redisinsight
  seq, temporary until Phase 3

LocalCluster:
  node-main  - Caddy, cloudflared, GitHub runner, observability backend
  node-app1  - app container, Alloy agent
  node-app2  - app container, Alloy agent
  node-db    - PostgreSQL, Redis, Alloy agent, database exporters
  public DNS - books.jacobgrum.com

Cloud:
  cloud-main - Caddy, cloudflared, SSH bastion, observability backend
  cloud-app1 - app container, Alloy agent
  cloud-app2 - app container, Alloy agent
  cloud-db   - PostgreSQL, Redis, Alloy agent, database exporters
  public DNS - bookscloud.jacobgrum.com
```

The Cloud deployment remains exactly four Hetzner servers. The LocalCluster deployment remains exactly four nodes.

## Files To Inspect First

Before changing implementation, inspect the current versions of these files because the repo may have moved since this plan was written:

```text
README.md
HowToRunLocally.md
RunLocal.ps1
docker-compose.yml
docker/local-status.py
.env.example
Directory.Packages.props
BlazorAutoApp/BlazorAutoApp.csproj
BlazorAutoApp/Program.cs
BlazorAutoApp/appsettings.json
BlazorAutoApp/appsettings.Docker.json
BlazorAutoApp/Infrastructure/Hosting/ObservabilityExtensions.cs
BlazorAutoApp/Infrastructure/Hosting/HealthCheckEndpointExtensions.cs
BlazorAutoApp/Features/Books/Endpoints/BooksEndpoints.cs
Deployment/Common/README.md
Deployment/LocalCluster/HowToDeployLocalCluster.md
Deployment/LocalCluster/compose/app-server/docker-compose.yml
Deployment/LocalCluster/compose/node-db/docker-compose.yml
Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2
Deployment/LocalCluster/ansible/roles/firewall/tasks/main.yml
Deployment/Cloud/HowToDeployCloud.md
Deployment/Cloud/compose/app-server/docker-compose.yml
Deployment/Cloud/compose/data/docker-compose.yml
Deployment/Cloud/ansible/roles/caddy/templates/app.caddy.j2
Deployment/Cloud/ansible/roles/firewall/tasks/main.yml
Deployment/Cloud/infra/opentofu/terraform.tfvars.example
.github/workflows/ci.yml
.github/workflows/cd-localcluster.yml
.github/workflows/cd-cloud.yml
```

If the implementation finds conflicting facts, update this plan first instead of guessing.

## Accepted Decision

We will build a self-hosted Grafana observability stack for this distributed app:

- Grafana for dashboards.
- Prometheus for metrics and alert rules.
- Loki for logs.
- Tempo for traces.
- Grafana Alloy as the node agent and OpenTelemetry collector.
- Exporters for host, container, PostgreSQL, Redis, Caddy, cloudflared, and synthetic probes.
- OpenTelemetry instrumentation in the .NET app.

Seq is not part of the long-term plan. It is currently useful in local Docker, but once Loki/Grafana log search works locally, Seq should be removed from:

- `docker-compose.yml`
- `BlazorAutoApp/appsettings.Docker.json`
- `BlazorAutoApp/BlazorAutoApp.csproj`
- `Directory.Packages.props`
- `.env.example`
- `HowToRunLocally.md`
- `README.md`

The final system should not run both Seq and Loki for the same app logs.

## Component Responsibilities

Use these responsibilities when deciding where configuration belongs:

```text
OpenTelemetry:
  app instrumentation API and protocol.
  owns trace/metric/log correlation inside the .NET app.

Grafana Alloy:
  one collector/agent per node.
  receives OTLP from local app containers.
  tails local Docker/systemd logs.
  scrapes local/private metrics.
  applies memory limiting, batching, relabeling, and drop rules.
  forwards logs to Loki, traces to Tempo, and metrics to Prometheus.

Prometheus:
  stores metrics.
  evaluates metric alert rules.
  scrapes exporters directly or through Alloy, depending on the final target config.

Loki:
  stores centralized logs.
  replaces Seq after parity is proven.
  must use low-cardinality labels only.

Tempo:
  stores distributed traces.
  receives sampled traces through Alloy.
  uses short retention, especially in Cloud.

Grafana:
  displays dashboards.
  provisions datasources and dashboards from git.
  may manage alert contact points if Alertmanager is not used separately.

blackbox_exporter:
  probes public and origin health endpoints.
  distinguishes Cloudflare/public failures from private origin failures.

postgres_exporter:
  exposes PostgreSQL health/performance metrics from the data node.

redis_exporter:
  exposes Redis health/performance metrics from the data node.
```

Do not add another collector family beside Alloy. Do not add another log backend beside Loki after Seq is removed.

## Why This Is The Right Option

This repo is not a single-node toy deployment. It has:

- two app nodes per deployed environment.
- one ingress node per deployed environment.
- one data node per deployed environment.
- Caddy load balancing.
- Cloudflare Tunnel.
- PostgreSQL.
- Redis.
- LocalCluster and Hetzner Cloud deployments that intentionally run as separate environments.

The accepted stack fits because:

- OpenTelemetry is the right app instrumentation layer for modern .NET.
- Grafana Alloy reduces duplicated agents by collecting logs, metrics, and traces with one tool per node.
- Prometheus is the right backend for host, container, exporter, Caddy, cloudflared, and blackbox metrics.
- Loki is a better production log target than Seq for this chosen Grafana stack.
- Tempo gives trace storage without running a heavier tracing system.
- Grafana gives one operator view across logs, metrics, traces, dashboards, and alerts.
- Everything can be kept private and short-retention, which fits the current cost-sensitive showcase setup.

## Core Principles

- One observability stack per deployed target unless explicitly exporting to a shared long-retention backend.
- One node agent per node: Grafana Alloy.
- No duplicate log systems after migration: Loki replaces Seq.
- No public observability ports in v1.
- No Cloudflare API token requirement.
- No high-cardinality metric labels.
- No secrets, auth headers, cookies, passwords, connection strings, or request bodies in logs/traces.
- App telemetry is target-neutral; deployment wiring is target-specific.
- Dashboards, alert rules, and common validation belong in `Deployment/Common/observability`.
- LocalCluster and Cloud deployment details stay target-specific.
- Every observability change must keep existing app acceptance checks green.

## Hard Constraints And Non-Goals

Hard constraints:

- Existing-node-only architecture.
- LocalCluster stays four nodes.
- Cloud stays four Hetzner servers.
- No public Grafana, Prometheus, Loki, Tempo, Alloy, exporters, or Caddy admin endpoints.
- No Cloudflare API token requirement.
- No observability dependency may block app startup or request handling.
- No high-cardinality labels.
- No long retention in Cloud.
- No secrets in git.
- No duplicate centralized log systems after Seq removal.
- No target-specific IPs, hostnames, secrets, or inventory values in `Deployment/Common/observability`.

Non-goals for v1:

- Kubernetes.
- Docker Swarm.
- managed Grafana Cloud as a requirement.
- public dashboard sharing.
- full SIEM/security analytics.
- long-term audit log retention.
- autoscaling.
- synthetic browser journeys beyond HTTP health probes.
- a dedicated observability server.
- cross-environment shared Prometheus/Loki/Tempo storage.

Allowed later only after v1 works:

- exporting Cloud telemetry to LocalCluster or Grafana Cloud for long-term history.
- increasing an existing node's resources if measured pressure justifies it.
- adding more dashboards based on real operational questions.

## Memory And Capacity Position

No plan can honestly guarantee "no memory problems." Operating systems, Docker, .NET, Prometheus, Loki, Tempo, Alloy, traffic spikes, cardinality mistakes, and log floods can all create memory pressure.

What this plan can and must guarantee:

- every observability component has an explicit memory budget before it is deployed.
- every backend has explicit retention and, where supported, size limits.
- every telemetry pipeline has backpressure or drop behavior that protects the app.
- every deployment has a preflight capacity check before enabling observability.
- every rollout has a rollback path that can disable traces, reduce log collection, or stop the observability stack without taking the app down.
- alerts exist for memory, disk, container restarts, dropped telemetry, missing targets, and high cardinality symptoms.
- observability must fail open for the app: if Alloy, Prometheus, Loki, or Tempo are unavailable, app requests must still work.

The first implementation must prove this with measurements, not guesses.

Non-negotiable memory standards:

- Add container memory and CPU limits to local, LocalCluster, and Cloud observability compose files from day one.
- Add container memory and CPU limits to the app, PostgreSQL, Redis, and observability containers after validating that the current Docker Compose version enforces them correctly.
- Configure Alloy `otelcol.processor.memory_limiter` in every OTLP pipeline before batching/export.
- Configure Alloy `otelcol.processor.batch` after memory limiting and sampling/drop processors.
- Keep Prometheus series count low and alert on sudden series growth.
- Keep Loki labels static and low-cardinality.
- Keep Tempo retention short and sampling configurable.
- Suppress or downgrade health-check request logs before shipping logs to Loki.
- Never use request IDs, trace IDs, book IDs, user IDs, email addresses, IP addresses, user agents, URLs, exception messages, or book titles as metric labels or Loki labels.
- Keep 25 percent host memory free after steady-state observability startup.
- Keep enough disk free for WALs, Docker logs, and compaction work; do not set retention to consume the whole disk.

Capacity must be checked in scripts, not by visual inspection.

Required capacity checks:

```text
local:
  Docker memory limit support is available.
  at least 4 GB free RAM before starting full local observability.
  at least 10 GB free disk before starting full local observability.

LocalCluster node-main:
  enough free RAM for Caddy, cloudflared, runner, Grafana, Prometheus, Loki, Tempo, Alloy, and blackbox_exporter.
  at least 25 percent memory remains free after startup.
  at least 20 GB free disk before enabling 30d metrics / 14d logs / 7d traces.

Cloud cloud-main:
  Hetzner server type is queried through the API or `hcloud server-type describe`.
  projected observability limits fit with at least 25 percent memory headroom.
  at least 10 GB free disk before enabling Cloud retention.
```

If these checks fail, the plan is not to continue and hope. The plan is:

1. reduce retention.
2. reduce scrape frequency.
3. reduce trace sample rate.
4. disable Tempo first if traces are the pressure source.
5. reduce the observability component memory budgets and feature set until the stack fits.
6. resize the existing `node-main` or `cloud-main` host only after the measured pressure is understood.

Do not add any extra observability node or fifth Cloud server. The constraint is existing nodes only.

## Current Baseline

Already present:

- Serilog request logging in `BlazorAutoApp/Infrastructure/Hosting/ObservabilityExtensions.cs`.
- Health endpoints in `BlazorAutoApp/Infrastructure/Hosting/HealthCheckEndpointExtensions.cs`:
   - `/health/live`
   - `/health/ready`
   - `/health`

- PostgreSQL readiness through `PostgresHealthCheck`.
- Redis readiness through `RedisHealthCheck`.
- Caddy upstream health checks in:
   - `Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2`
   - `Deployment/Cloud/ansible/roles/caddy/templates/app.caddy.j2`

- Local Docker Seq service in `docker-compose.yml`.
- LocalCluster acceptance in `Deployment/LocalCluster/Scripts/acceptance-check.sh`.
- Cloud acceptance in `Deployment/Cloud/Scripts/acceptance-check.sh`.
- Cloud doctor in `Deployment/Cloud/Scripts/doctor.sh`.
- LocalCluster doctor in `Deployment/LocalCluster/Scripts/doctor.sh`.

Main gaps:

- no production central logs.
- no metrics retention.
- no distributed traces.
- no node-by-node dashboard.
- no private Grafana.
- no alerting.
- no deployed SHA view per app node.
- no Caddy access log dashboard.
- no cloudflared tunnel metrics dashboard.
- no long enough history to answer "what changed after deploy?"
- no explicit container memory/CPU limits in the local, LocalCluster, or Cloud compose files.
- no app-server container healthcheck in the LocalCluster or Cloud app compose files.
- Caddy currently probes `/health/ready` every 5 seconds; current request logging would log those health requests unless changed.
- `BlazorAutoApp/Features/Books/Endpoints/BooksEndpoints.cs` currently logs the created book title; that must be removed before central log shipping.
- Cloud currently uses one server type for all four nodes in `Deployment/Cloud/infra/opentofu/terraform.tfvars.example`; this plan must keep that four-node shape.
- Cloud observability history will be disposable if stored only on `cloud-main`.

Current repo facts from the scan:

- Local Docker runs `postgres`, `web`, `seq`, `redis`, and `redisinsight`.
- Local Docker publishes local ports only on `127.0.0.1`, which is good for local safety.
- LocalCluster app/data compose files have `restart: unless-stopped`, but app-server compose has no healthcheck.
- Cloud app/data compose files have `restart: unless-stopped`, but app-server compose has no healthcheck.
- Deployed app logs currently go to console/stdout unless local Docker config adds Seq.
- Current app health endpoints already separate liveness and readiness.


## Target Architecture

```text
Browser / external probe
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

Every node:
  Grafana Alloy
    - receives app OTLP where local
    - scrapes local node/container/service metrics
    - tails local Docker/systemd logs
    - forwards to observability backend

Observability backend node:
  Grafana
  Prometheus
  Loki
  Tempo
  Alertmanager or Grafana-managed alerts
  blackbox_exporter
```

## Node Responsibilities

### Local Development

Local Docker should end in this shape:

```text
web
postgres
redis
grafana
prometheus
loki
tempo
alloy
redisinsight, optional
```

Remove after replacement:

```text
seq
```

Local Alloy responsibilities:

- receive OTLP from `web`.
- scrape app, PostgreSQL, Redis, Docker, and optional Caddy/local probes.
- collect Docker logs.
- write metrics to Prometheus.
- write logs to Loki.
- write traces to Tempo.

Local Grafana:

- bind only to `127.0.0.1`.
- provision datasources and dashboards from git.
- use short demo credentials from `.env`, not committed secrets.

### LocalCluster

Current node roles:

```text
node-main  - Caddy, cloudflared, GitHub runner, observability backend
node-app1  - app container, Alloy agent
node-app2  - app container, Alloy agent
node-db    - PostgreSQL, Redis, Alloy agent, database exporters
```

Recommended LocalCluster placement:

- Run Grafana, Prometheus, Loki, Tempo, Alertmanager, and blackbox_exporter on `node-main`.
- Run Alloy on every node.
- Run PostgreSQL and Redis exporters on `node-db`.
- Run Caddy metrics and cloudflared metrics on `node-main`.
- Run container metrics on every node that runs Docker containers.

Why `node-main`:

- It is already the ingress/operator node.
- It already hosts the self-hosted runner.
- It is the natural SSH tunnel target for dashboards.
- It can probe both public and origin paths.

Risk:

- `node-main` can become crowded.

Mitigation:

- Keep retention modest.
- Monitor `node-main` CPU, RAM, and disk first.
- If `node-main` is pressured, tune retention, sampling, scrape intervals, and resource limits first.
- If tuning is not enough, resize the existing `node-main`; do not add a new node.

### Cloud

Current node roles:

```text
cloud-main  - Caddy, cloudflared, SSH bastion, observability backend
cloud-app1  - app container, Alloy agent
cloud-app2  - app container, Alloy agent
cloud-db    - PostgreSQL, Redis, Alloy agent, database exporters
```

Recommended Cloud placement:

- Run Grafana, Prometheus, Loki, Tempo, Alertmanager, and blackbox_exporter on `cloud-main`.
- Run Alloy on every cloud node.
- Run PostgreSQL and Redis exporters on `cloud-db`.
- Run Caddy metrics and cloudflared metrics on `cloud-main`.
- Run container metrics on app/data nodes.

Why `cloud-main`:

- It is already the bastion.
- It is reachable through controlled SSH.
- It has public egress and private access to all nodes.
- It keeps the Cloud architecture at exactly four Hetzner servers.

Risk:

- Cloud is cost-sensitive and disposable.
- Destroying Cloud destroys Cloud-local observability history.

Mitigation:

- Keep short retention.
- Make `quick-destroy-cloud.sh` explicitly warn that Cloud-local observability history will be destroyed.
- If `cloud-main` is pressured, tune retention, sampling, scrape intervals, and resource limits first.
- If tuning is not enough, resize the existing `cloud-main`; do not add a fifth server.
- If history matters later, export Cloud telemetry to LocalCluster or Grafana Cloud before destroy.

## Signal Flow

### App Metrics And Traces

```text
Blazor app -> OTLP -> local Alloy -> Prometheus/Tempo
```

The app should emit:

- ASP.NET Core request metrics and traces.
- runtime metrics.
- process metrics.
- database spans when supported.
- Redis/cache spans or custom events where useful.
- custom Books/cache metrics with low-cardinality labels only.

### App Logs

```text
Blazor app -> stdout/stderr -> Docker log files -> Alloy -> Loki
```

Do not send the same app logs to Seq after Loki is accepted.

Serilog remains useful for structured logging, but the sink should become console/stdout for deployed environments. Alloy ships those logs to Loki.

### Caddy

```text
Caddy access logs -> journald/file -> Alloy -> Loki
Caddy metrics     -> Alloy scrape   -> Prometheus
```

Caddy metrics should be enabled on a private or loopback endpoint. Caddy access logs should be structured enough to show:

- method.
- host.
- path.
- status.
- duration.
- upstream address.
- upstream errors.
- request id if available.

### cloudflared

```text
cloudflared logs    -> journald -> Alloy -> Loki
cloudflared metrics -> Alloy    -> Prometheus
```

The metrics endpoint must bind to loopback/private network only.

### PostgreSQL

```text
postgres container logs -> Alloy -> Loki
postgres_exporter       -> Alloy/Prometheus scrape -> Prometheus
```

Exporter credentials:

- read-only.
- stored in LocalCluster Vault or GitHub Cloud environment secrets.
- never committed.

### Redis

```text
redis container logs -> Alloy -> Loki
redis_exporter       -> Alloy/Prometheus scrape -> Prometheus
```

Redis exporter must use the Redis password from the deployment secret path.

### Host And Container Metrics

```text
node_exporter / Alloy host metrics -> Prometheus
Docker/cAdvisor metrics            -> Prometheus
```

If Alloy can collect enough host/container metrics directly for v1, prefer that over running separate agents. Add node_exporter or cAdvisor only where Alloy alone is insufficient.

## Ports And Exposure

Default private ports to reserve:

```text
Grafana              3000
Prometheus           9090
Alertmanager         9093
Loki                 3100
Tempo                3200
OTLP gRPC            4317
OTLP HTTP            4318
Alloy HTTP/debug     12345
blackbox_exporter    9115
postgres_exporter    9187
redis_exporter       9121
Caddy admin/metrics  2019
cloudflared metrics  2000
```

Rules:

- Grafana binds private/loopback only.
- Prometheus, Loki, Tempo, Alloy, exporters, and Caddy admin must not be public.
- In Cloud, Hetzner Cloud firewalls must not expose observability ports.
- In both targets, host firewall rules allow scrape/OTLP only from the observability backend or local node agent.
- Normal dashboard access uses SSH tunnel.

Expected operator access:

```text
LocalCluster Grafana: http://127.0.0.1:3000 through node-main tunnel
Cloud Grafana:        http://127.0.0.1:3000 through cloud-main tunnel
```

## Telemetry Volume And Cardinality Budgets

The memory risk in this system is not the number of VPS nodes. Four nodes is small. The risk is unbounded telemetry:

- too many Prometheus time series.
- too many Loki streams.
- too much health-check logging.
- too much trace sampling.
- too many dashboard queries over long ranges.
- too much retained data for the disk size.

### Metric Cardinality Budget

Metric labels must be bounded and reviewed.

Allowed metric labels:

```text
deployment_target
environment
node
service_name
service_version
route
method
status_class
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

Route labels must use ASP.NET route templates, not raw URLs. For example:

```text
good: /api/books/{id}
bad:  /api/books/123
```

Series limits for v1:

```text
Local development:     warn at 10,000 active series
LocalCluster:          warn at 25,000 active series, critical at 50,000
Cloud:                 warn at 15,000 active series, critical at 30,000
```

These numbers are intentionally conservative. The app is small, and the point is to catch mistakes early.

### Loki Stream Budget

Loki labels should identify the source, not the event.

Allowed Loki labels:

```text
deployment_target
environment
node
service_name
container
level
logger_category, only if bounded enough after testing
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

Trace IDs and request IDs should remain searchable as structured log fields, not Loki labels.

Stream limits for v1:

```text
Local development:     warn at 100 active streams
LocalCluster:          warn at 300 active streams
Cloud:                 warn at 200 active streams
```

### Log Volume Budget

Before Loki is enabled:

- suppress or downgrade `/health/live`, `/health/ready`, `/health`, `/metrics`, `/_framework`, `/assets`, and `/favicon.ico` request logs.
- remove book title logging from `Created book {BookId} - {Title}`.
- keep `Microsoft` and `System` overrides at `Warning`.
- keep app default log level at `Information` unless debugging locally.
- do not enable EF SQL command logging in deployed environments.
- do not log request bodies.
- do not log auth headers, cookies, tokens, or connection strings.

Daily log volume targets:

```text
Local development:     no strict limit, but keep default under 250 MB/day.
LocalCluster:          target under 1 GB/day.
Cloud:                 target under 500 MB/day.
```

If Cloud exceeds 500 MB/day, reduce request log volume before increasing retention or disk.

### Trace Volume Budget

Trace sampling must be configurable per target.

Defaults:

```text
Local development:     1.00
LocalCluster:          0.25 initially, allow 1.00 during short debugging windows
Cloud:                 0.10 initially, allow 1.00 during short demos only
```

Emergency values:

```text
Observability__TraceSampleRatio=0.0
Observability__TracesEnabled=false
```

The app must continue serving requests if OTLP export fails.

### Scrape Budget

Initial scrape intervals:

```text
app metrics:           30s
Caddy metrics:         30s
cloudflared metrics:   30s
host metrics:          30s
container metrics:     30s
PostgreSQL exporter:   30s
Redis exporter:        30s
blackbox public probe: 60s
blackbox origin probe: 30s
Prometheus self:       30s
Alloy self:            30s
```

Do not lower scrape intervals until dashboards prove a real need.

### Dashboard Query Budget

Dashboards must default to short ranges:

```text
local:        last 30 minutes
LocalCluster: last 6 hours
Cloud:        last 1 hour
```

Heavy dashboard panels should use recording rules when queries become slow or memory-heavy.

## Resource Limits And Sizing

All limits below are starting budgets, not performance promises. They must be encoded as variables so LocalCluster and Cloud can be tuned without editing many files.

### Backend Node Starting Budgets

These are the initial limits for `node-main` and `cloud-main` when they host the observability backend:

```text
Grafana:             memory 256m, CPU 0.25
Prometheus:          memory 768m LocalCluster / 512m Cloud, CPU 0.75
Loki:                memory 512m, CPU 0.50
Tempo:               memory 384m, CPU 0.50
Alloy backend agent: memory 256m, CPU 0.25
blackbox_exporter:   memory 64m,  CPU 0.10
Alertmanager:        memory 128m, CPU 0.10
```

If these limits are too tight during controlled startup, increase them deliberately and update the plan with measured evidence. Do not remove limits.

### App And Data Node Starting Budgets

These are starting limits for service containers after Compose resource-limit support is verified:

```text
Blazor app:       memory 512m, CPU 0.75 per app node
PostgreSQL:       memory 1024m, CPU 1.00 on data node
Redis:            memory 384m, CPU 0.50 on data node
Alloy node agent: memory 192m, CPU 0.25 on app/data nodes
postgres_exporter: memory 64m, CPU 0.10
redis_exporter:    memory 64m, CPU 0.10
```

PostgreSQL and Redis may need tuning if load grows, but the current production data is disposable and expected to be small.

### Required Resource-Limit Implementation

Use Docker Compose resource controls supported by the target Docker Compose version.

Preferred shape:

```yaml
mem_limit: "${SERVICE_MEMORY_LIMIT:-512m}"
mem_reservation: "${SERVICE_MEMORY_RESERVATION:-256m}"
cpus: "${SERVICE_CPU_LIMIT:-0.50}"
```

If Compose behavior differs by version, add a script that starts a tiny test container, verifies the reported memory limit through `docker inspect`, and fails preflight if limits are not enforced.

### Host Headroom Rules

Observability must not consume all memory on `node-main` or `cloud-main`.

Rules:

- steady-state used memory after startup must leave at least 25 percent free.
- no single observability container should exceed 80 percent of its memory limit during idle plus smoke traffic.
- any OOMKilled container blocks the rollout.
- repeated restarts block the rollout.
- Prometheus WAL replay after restart must complete without exhausting memory.
- Loki and Tempo compaction must not drive disk over the critical threshold.

### Disk Budget

Initial disk budgets:

```text
Local development observability volumes: 5 GB soft cap
LocalCluster observability volumes:      20 GB soft cap
Cloud observability volumes:             10 GB soft cap
```

Prometheus must use time retention and should add size retention after baseline measurement.

Loki and Tempo must use explicit retention. Cloud starts shortest.

Docker log rotation should be configured so local container logs cannot fill the host:

```text
max-size: 10m
max-file: 5
```

Apply log rotation consistently to app, PostgreSQL, Redis, Caddy if file-based, cloudflared if file-based, and observability containers.

### Failure And Rollback Controls

The app must survive observability failure.

Emergency rollback order:

1. Set `Observability__TracesEnabled=false` or `Observability__TraceSampleRatio=0.0`.
2. Disable OTLP export from app containers.
3. Stop Tempo.
4. Shorten Loki retention and reduce log collection.
5. Increase scrape intervals.
6. Stop the observability backend compose stack.
7. Re-run normal app acceptance.

Rollback must not require destroying the app database, Redis, Cloud servers, Cloudflare Tunnel, or GitHub runner.

## Retention Policy

Retention must be explicit because this is a small, multi-node deployment.

### Local Development

Purpose:

- debugging current local work.

Retention:

```text
Prometheus metrics: 24h to 72h
Loki logs:          24h to 72h
Tempo traces:       24h
Grafana data:       persistent local Docker volume
```

Storage:

- Docker volumes.
- Safe to reset.

### LocalCluster

Purpose:

- stable home lab production-like environment.
- compare behavior before and after deploys.
- demonstrate operating a real distributed app.

Retention:

```text
Prometheus metrics: 30d
Loki logs:          14d
Tempo traces:       7d
Alert history:      30d if using Grafana-managed alerts
```

Storage:

- persistent Docker volumes on `node-main`.
- keep under a documented path, for example `/opt/books-observability`.

Disk guardrails:

- warn at 70 percent disk usage.
- critical at 85 percent disk usage.
- reduce Loki/Tempo retention before adding disk.

### Cloud

Purpose:

- short-lived showcase environment.
- prove the app runs on real multi-VPS infrastructure.
- catch Cloud-specific network and performance issues.

Retention:

```text
Prometheus metrics: 7d
Loki logs:          3d
Tempo traces:       24h to 72h
Alert history:      7d if using Grafana-managed alerts
```

Storage:

- persistent Docker volumes on `cloud-main`.
- destroyed by `quick-destroy-cloud.sh` unless backed up/exported first.

Disk guardrails:

- warn at 65 percent disk usage.
- critical at 80 percent disk usage.
- prefer reducing retention over increasing VPS size.

### Retention Mechanics

Prometheus:

- set retention with `storage.tsdb.retention.time` or equivalent current config.
- set a size cap if needed after measuring disk growth.

Loki:

- enable retention through the compactor.
- define `limits_config.retention_period`.
- use local filesystem storage for v1 unless object storage is deliberately added later.

Tempo:

- set block retention explicitly.
- keep short in Cloud.

Grafana:

- dashboard definitions live in git.
- Grafana database can be disposable because provisioning should recreate dashboards/datasources.
- only user preferences and ad hoc dashboards are lost on reset.

## Data Ownership And Disposable Cloud

LocalCluster observability data is semi-durable.

Cloud observability data is disposable unless we later add export.

`quick-destroy-cloud.sh` must report:

- Cloud app data will be destroyed.
- Cloud observability metrics/logs/traces will be destroyed.
- GitHub environment secrets are left in place.
- LocalCluster observability is unaffected.

`quick-recreate-cloud-after-destruction.sh` must:

- recreate observability backend on `cloud-main`.
- redeploy Alloy on all nodes.
- refresh Grafana dashboards from git.
- start with empty Cloud metrics/logs/traces history.

## Preflight And Automation Standards

The guide should not ask the operator to manually inspect memory, ports, or generated files when a script can check them.

Add common observability automation:

```text
Deployment/Common/observability/scripts/check-compose-resource-limits.sh
Deployment/Common/observability/scripts/check-telemetry-cardinality.sh
Deployment/Common/observability/scripts/check-observability-config.sh
Deployment/Common/observability/scripts/smoke-observability.sh
Deployment/Common/observability/scripts/resource-report.sh
Deployment/Common/observability/scripts/validate-dashboard-json.sh
Deployment/Common/observability/scripts/validate-prometheus-rules.sh
```

Add target-specific automation:

```text
Deployment/LocalCluster/Scripts/observability-capacity-check.sh
Deployment/LocalCluster/Scripts/observability-doctor.sh
Deployment/LocalCluster/Scripts/open-observability-tunnel.sh

Deployment/Cloud/Scripts/observability-capacity-check.sh
Deployment/Cloud/Scripts/observability-doctor.sh
Deployment/Cloud/Scripts/open-observability-tunnel.sh
Deployment/Cloud/Scripts/observability-resource-report.sh
```

Required script behavior:

- print clear `OK`, `WARN`, and `FAIL` lines.
- fail fast on missing tools.
- never expose secrets in output.
- support `--plan-only` where a script can change infrastructure.
- print exact next commands when manual steps remain.
- be idempotent.
- be safe to run repeatedly.

Capacity check output should include:

```text
target
node
total memory
available memory
disk free
docker version
docker compose version
resource-limit support
running observability containers
current container memory usage
current container restart count
current Prometheus active series
current Loki stream count
current log ingestion rate
current trace ingestion rate
```

Doctor output should include current state, not a static checklist.

The doctor should query:

- Grafana health API.
- Prometheus health, targets, active series, and rules.
- Loki readiness and recent app log query.
- Tempo readiness and recent trace query.
- Alloy health on every node.
- Caddy metrics target.
- cloudflared metrics target.
- PostgreSQL exporter target.
- Redis exporter target.
- public `/health/ready`.
- origin `/health/ready`.
- latest deployed SHA per app node.

## Guide And Manual-Step Conventions

Any future guide edits must label manual commands by machine:

```text
[CurrentPC]   developer workstation / WSL / local repo clone.
[ControlPC]   LocalCluster control machine behind the user.
[Cloud]       commands executed by Ansible/GitHub Actions on Hetzner nodes, not manual SSH unless explicitly stated.
[LocalDocker] local Docker compose stack on the developer workstation.
```

Do not write guide steps that say "check the generated file" without first generating it in an earlier step.

Do not ask the operator to paste long repeated parameters when a script can read repo settings or prompt safely.

Do not include future decisions in the middle of a current operational step. A guide step should explain only what to do now, what success looks like, and what to do if it fails.

## Repository Layout

Shared, target-neutral assets:

```text
Deployment/Common/observability/
  grafana/
    dashboards/
    provisioning/
  prometheus/
    rules/
  loki/
    rules/
  alloy/
    modules/
  scripts/
```

LocalCluster target assets:

```text
Deployment/LocalCluster/observability/
  compose/
  ansible/
  scripts/
```

Cloud target assets:

```text
Deployment/Cloud/observability/
  compose/
  ansible/
  scripts/
```

Local development assets:

```text
docker/observability/
```

Rules:

- Dashboards and alert rules should be shared when possible.
- Compose files, firewall rules, secrets, and inventory-specific scrape targets are target-specific.
- Do not import from `Deployment/LocalCluster` into `Deployment/Cloud`.
- Use `Deployment/Common` only when the asset is target-neutral.

## Configuration Ownership

Keep one source of truth for each kind of value:

```text
Deployment/Common/observability:
  dashboard JSON
  dashboard provisioning templates without target hostnames
  Prometheus alert rule templates
  shared runbooks
  shared validation scripts
  shared Alloy snippets only when they contain no target-specific addresses

Local Docker:
  local compose service wiring
  local ports bound to 127.0.0.1
  local demo credentials in .env/.env.example shape
  local retention/resource defaults

LocalCluster inventory/vault:
  LocalCluster node addresses
  LocalCluster Grafana admin secret
  LocalCluster exporter credentials
  LocalCluster scrape targets
  LocalCluster firewall allowances
  LocalCluster retention/resource overrides

Cloud GitHub environment and Cloud inventory:
  Cloud node addresses
  Cloud Grafana admin secret
  Cloud exporter credentials
  Cloud scrape targets
  Cloud firewall allowances
  Cloud retention/resource overrides

App configuration:
  OpenTelemetry enable/disable flags
  trace sampling ratio
  service name/version/resource attributes
  OTLP endpoint
  log suppression settings
```

Configuration values must flow from these sources into generated compose/env/config files. Do not copy the same literal in multiple unrelated places when a script or template can render it.

Required target variables:

```text
OBSERVABILITY_ENABLED
OBSERVABILITY_METRICS_ENABLED
OBSERVABILITY_TRACES_ENABLED
OBSERVABILITY_TRACE_SAMPLE_RATIO
OBSERVABILITY_LOGS_ENABLED
OBSERVABILITY_SUPPRESS_HEALTH_REQUEST_LOGS
OBSERVABILITY_OTLP_ENDPOINT
GRAFANA_ADMIN_USER
GRAFANA_ADMIN_PASSWORD
PROMETHEUS_RETENTION_TIME
PROMETHEUS_RETENTION_SIZE
LOKI_RETENTION_PERIOD
TEMPO_RETENTION_PERIOD
OBSERVABILITY_DOCKER_LOG_MAX_SIZE
OBSERVABILITY_DOCKER_LOG_MAX_FILE
```

Use app configuration keys with double-underscore form when passed to containers:

```text
Observability__Enabled
Observability__MetricsEnabled
Observability__TracesEnabled
Observability__TraceSampleRatio
Observability__LogsCorrelationEnabled
Observability__SuppressHealthRequestLogs
OTEL_EXPORTER_OTLP_ENDPOINT
OTEL_EXPORTER_OTLP_PROTOCOL
```

## App Instrumentation Plan

### Packages

Add OpenTelemetry packages to the app:

- OpenTelemetry hosting.
- OTLP exporter.
- ASP.NET Core instrumentation.
- HTTP client instrumentation.
- runtime/process instrumentation.
- database instrumentation after confirming the current recommended Npgsql/EF path.

Keep Serilog packages needed for structured console logging.

Remove `Serilog.Sinks.Seq` only after Loki is proven locally and deployed.

### Configuration

Add environment-driven configuration:

```text
Observability__Enabled=true
Observability__ServiceName=books
Observability__DeploymentTarget=localcluster|cloud|local
Observability__NodeName=node-app1|node-app2|cloud-app1|cloud-app2|local
Observability__MetricsEnabled=true
Observability__TracesEnabled=true
Observability__LogsCorrelationEnabled=true
Observability__TraceSampleRatio=0.10|0.25|1.00
Observability__SuppressHealthRequestLogs=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://<alloy-host>:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

Resource attributes:

```text
service.name
service.version
deployment.environment
host.name
app.name
app.deployment_target
app.node
app.version
```

`APP_VERSION` should be passed into app containers so dashboards can show deployed SHA per node.

### Traces

Trace:

- HTTP requests.
- API endpoints.
- database calls when supported.
- outbound HTTP calls.
- cache invalidation publish/apply where useful.
- startup migration/seed work if it causes slow starts.

Sampling:

- Local: 100 percent.
- LocalCluster: 25 percent by default; allow 100 percent temporarily during short debugging windows.
- Cloud: 10 percent by default; allow 100 percent temporarily during short demos only.
- Emergency: 0 percent or traces disabled.

Never put secrets, auth tokens, cookies, user emails, book titles, or raw request bodies in spans.

Exporter behavior:

- bounded queue.
- bounded batch size.
- short export timeout.
- retry policy with backoff.
- failed export must not fail app requests.
- app startup must not require Alloy to be reachable.

### Metrics

Use built-in .NET metrics first.

Add custom metrics only where they answer a real product question:

```text
books.api.requests
books.created
books.updated
books.deleted
books.not_found
books.cache_invalidation.failures
books.cache_invalidation.published
author_books.seed.duration
author_books.seed.failures
```

Allowed labels:

```text
deployment_target
environment
node
service_name
service_version
route
method
status_class
operation
cache_scope
```

Forbidden metric labels:

```text
user_id
email
book_id
book_title
url
request_id
trace_id
exception_message
ip_address
user_agent
```

### Logs

Keep structured Serilog logs.

Production sinks:

- console/stdout.

Production shipping:

- Alloy tails Docker logs and sends to Loki.

Add log fields:

```text
TraceId
SpanId
RequestId
Application
Environment
DeploymentTarget
ServiceVersion
NodeName
```

Review current logs before shipping to Loki:

- `BlazorAutoApp/Features/Books/Endpoints/BooksEndpoints.cs` currently logs book title when a book is created. Replace with book id/action before central log collection.
- account logs should not include sensitive values.
- request logs should not include auth headers or cookies.
- `/health/*`, `/metrics`, `/_framework`, `/assets`, and `/favicon.ico` should be suppressed or downgraded before Loki is enabled.
- logs that contain user IDs can remain structured fields only if the retention/security decision accepts that; they must not become Loki labels.

## Endpoint Plan

Keep public endpoints:

```text
/health/live
/health/ready
/health
```

Add internal endpoints:

```text
/internal/health/details
/internal/version
```

`/internal/health/details` should return JSON:

- overall status.
- individual check status.
- duration per check.
- app version.
- node name.
- deployment target.

It must not expose secrets, connection strings, stack traces, Redis passwords, or raw exception details.

`/internal/version` should return:

- app name.
- git SHA.
- runtime version.
- build timestamp if available.
- deployment target.
- node name.

Routing:

- Do not expose internal endpoints publicly in v1.
- Allow internal probes from Caddy/Alloy/Ansible only.

Add app container healthchecks to:

- `Deployment/LocalCluster/compose/app-server/docker-compose.yml`
- `Deployment/Cloud/compose/app-server/docker-compose.yml`

## Logs And Metrics Sources

### App Containers

Collect:

- stdout/stderr logs.
- HTTP server metrics.
- runtime metrics.
- traces.
- container CPU/memory/restarts.

### Caddy

Collect:

- structured access logs.
- Caddy admin metrics.
- reverse proxy upstream health.
- request durations.
- status code counts.
- upstream selection.

Update:

- LocalCluster Caddy template.
- Cloud Caddy template.
- root Caddyfiles if metrics need global enablement.

### cloudflared

Collect:

- systemd logs.
- Prometheus metrics endpoint.
- tunnel request count.
- tunnel error count.
- tunnel connection state.
- reconnects.

### PostgreSQL

Collect:

- postgres container logs.
- exporter metrics.
- connection count.
- max connection utilization.
- database size.
- transactions.
- locks/deadlocks.
- checkpoint/write pressure where available.

### Redis

Collect:

- redis container logs.
- exporter metrics.
- memory usage.
- connected clients.
- command rate.
- keyspace hit/miss.
- pub/sub channels/subscribers.
- evictions.

### Hosts

Collect from every node:

- CPU.
- load.
- memory.
- disk free.
- disk IO.
- network IO.
- systemd unit status where useful.
- Docker/container state.

### Synthetic Probes

Use blackbox probes:

Public:

- `https://books.jacobgrum.com/health/ready`
- `https://books.jacobgrum.com/`
- `https://bookscloud.jacobgrum.com/health/ready`
- `https://bookscloud.jacobgrum.com/`

Origin:

- LocalCluster Caddy loopback health on `node-main`.
- Cloud Caddy loopback health on `cloud-main`.
- direct app-node readiness over private network.

Cloudflare challenge note:

- Public probe challenge from Cloudflare is different from origin failure.
- Dashboards must show public edge result and origin result separately.

## Dashboards

Dashboards live as code in `Deployment/Common/observability/grafana/dashboards`.

### Dashboard 1: Executive Overview

Panels:

- public health by target.
- origin health by target.
- current deployed SHA per app node.
- request rate.
- p50/p95/p99 latency.
- 5xx rate.
- 429 rate.
- Caddy upstream health.
- cloudflared tunnel status.
- PostgreSQL up.
- Redis up.
- node disk pressure.

### Dashboard 2: Endpoint Performance

Panels:

- request rate by route.
- latency by route.
- status code distribution.
- slowest routes.
- errors by route.
- rate-limit rejections.

Routes:

- `/`
- `/books`
- `/api/author-books`
- `/api/author-books/{id}`
- `/api/books`
- `/api/books/{id}`
- `/Account/*`

### Dashboard 3: App Node Comparison

Panels:

- requests by app node.
- errors by app node.
- latency by app node.
- CPU/memory by app node.
- GC heap by app node.
- thread pool pressure by app node.
- container restarts by app node.
- deployed SHA by app node.

This dashboard is required because there are two app nodes.

### Dashboard 4: Ingress

Panels:

- Caddy request rate.
- Caddy latency.
- Caddy upstream selected.
- Caddy upstream health.
- Caddy errors.
- cloudflared tunnel health.
- Cloudflare edge/public probe result.
- origin probe result.

### Dashboard 5: Data Layer

Panels:

- PostgreSQL up.
- PostgreSQL connections.
- PostgreSQL locks/deadlocks.
- PostgreSQL database size.
- Redis up.
- Redis memory.
- Redis hit/miss ratio.
- Redis pub/sub channel/subscriber state.

### Dashboard 6: Host And Container

Panels:

- CPU by node.
- RAM by node.
- disk free by node.
- network IO by node.
- container CPU/memory.
- container restarts.
- Docker daemon health.

### Dashboard 7: Deployments

Panels:

- latest CI result.
- latest LocalCluster CD result.
- latest Cloud CD result.
- deployed SHA per target.
- deployment age.
- failed deployment count.

First implementation can feed this from existing GitHub CLI doctor scripts. Later, create a small textfile exporter or GitHub workflow status exporter if useful.

## Alerting

Use Prometheus alert rules first, routed to Alertmanager or Grafana.

Initial alerts:

```text
PublicHealthDown
OriginHealthDown
AllAppNodesDown
OneAppNodeDown
CaddyUpstreamUnhealthy
CloudflaredDown
PostgresDown
RedisDown
AppHigh5xxRate
AppHighLatencyP95
DiskSpaceWarning
DiskSpaceCritical
ContainerRestarted
NodeMetricsMissing
TelemetryPipelineDown
LatestCiFailed
LatestLocalClusterCdFailed
LatestCloudCdFailed
```

Noise rules:

- Do not alert on one failed scrape.
- Do not alert on isolated 404s.
- Do not alert on isolated 429s.
- Do not page on GitHub-runner Cloudflare challenges if origin checks pass.
- Use warning before critical for disk pressure.

Runbooks:

```text
Deployment/Common/observability/runbooks/
```

Required runbooks:

- public site down.
- origin down.
- one app node unhealthy.
- both app nodes unhealthy.
- PostgreSQL down.
- Redis down.
- Caddy upstream unhealthy.
- cloudflared down.
- telemetry pipeline down.
- disk filling.
- deployment failed.

## Security

Access:

- No public Grafana in v1.
- Use SSH tunnels.
- Later public access must use Cloudflare Access or equivalent authentication.

Secrets:

- LocalCluster Grafana/admin/exporter secrets go in Ansible Vault.
- Cloud Grafana/admin/exporter secrets go in GitHub environment secrets unless the Cloud secret model is changed.
- No observability secrets in plaintext repo files.

Network:

- Prometheus scrapes only private/loopback endpoints.
- Alloy accepts OTLP only from app nodes/private networks.
- Exporters bind private/loopback only.
- Hetzner Cloud firewalls expose none of the observability ports publicly.
- LocalCluster UFW allows only required internal scrape/OTLP paths.

Data:

- Logs are treated as sensitive.
- Retention is short by default.
- Loki labels must stay low-cardinality.
- Trace attributes must be reviewed for PII.

## CI And Validation

Add CI checks for:

- Grafana dashboard JSON validity.
- Grafana datasource provisioning YAML.
- Prometheus rule syntax using `promtool`.
- Loki config syntax where practical.
- Tempo config syntax where practical.
- Alloy config formatting/validation where practical.
- shellcheck for new scripts.
- yamllint for observability YAML.

CI must continue to validate:

- existing LocalCluster deployment.
- existing Cloud deployment settings.
- .NET build/tests.
- Docker build.

## Implementation Protocol

Every implementation phase must use this protocol:

1. Read the files listed in `Files To Inspect First` that are relevant to the phase.
2. Run `git status --short`.
3. State the intended file set before editing.
4. Make the smallest coherent change.
5. Run formatting or validation for the touched file types.
6. Run the phase verification commands.
7. Update this plan if reality differs from the plan.
8. Do not proceed to the next phase until verification passes.

Suggested verification command families:

```text
dotnet build BlazorAutoApp.sln
dotnet test BlazorAutoApp.sln
docker compose config
docker compose up -d
docker compose ps
bash Deployment/Common/observability/scripts/validate-observability.sh
bash Deployment/LocalCluster/Scripts/doctor.sh
bash Deployment/Cloud/Scripts/doctor.sh
```

Only run target deployment scripts after the local slice works and the target guide has been updated.

Commit guidance:

- Keep commits phase-sized.
- Do not mix observability planning, app instrumentation, LocalCluster deployment, and Cloud deployment in one large commit.
- Do not include generated telemetry data, OpenTofu state, generated inventories, secrets, or local `.env` files.
- Mention verification results in commit messages or PR notes.

## Implementation Phases

### Phase 0: Keep Current Deployments Stable

Status: not started.

Work:

- Commit or consciously ignore unrelated worktree changes.
- Confirm LocalCluster and Cloud are currently healthy.
- Add a no-change capacity report script that can read current node memory/disk/container state.
- Add a no-change local Compose resource-limit support check.
- Do not remove Seq yet.
- Do not add production observability yet.

Verification:

- LocalCluster doctor/acceptance still works.
- Cloud doctor/acceptance still works.
- capacity scripts report current state without changing services.
- resource-limit check proves Docker Compose can enforce memory limits before limits are added broadly.

### Phase 1: App OpenTelemetry, Disabled By Default

Status: not started.

Work:

- Add OpenTelemetry packages.
- Extend `AddAppObservability`.
- Add app resource attributes.
- Add trace/log correlation.
- Add low-cardinality custom metrics.
- Add bounded exporter queue/batch settings.
- Make OTLP exporter failure non-fatal.
- Suppress or downgrade health/static request logs.
- Remove book title from created-book log message.
- Add tests for disabled observability.

Verification:

- `dotnet build`.
- `dotnet test`.
- local app works with observability disabled.
- app starts when Alloy endpoint is missing.
- `/health/*` requests do not generate normal information-level request logs.
- no created-book log contains book title.
- no deployment behavior changes.

### Phase 2: Local Grafana Stack Beside Seq

Status: not started.

Work:

- Add local optional observability profile.
- Add local Grafana, Prometheus, Loki, Tempo, Alloy.
- Add resource limits to local observability containers.
- Add retention and disk-size guardrails.
- Add Docker log rotation.
- Add Alloy memory limiter and batch processors.
- Add local observability capacity check.
- Keep Seq temporarily.
- Prove logs, metrics, and traces reach Grafana.

Verification:

- local Grafana shows app request metrics.
- local Grafana shows app logs in Loki.
- local Grafana shows traces in Tempo.
- local resource report shows container limits and no OOMKills.
- active Prometheus series and Loki streams are below v1 warning thresholds.
- Seq still works during comparison.

### Phase 3: Remove Seq

Status: not started.

Entry criteria:

- Loki/Grafana log search works locally.
- trace ids connect logs and traces.
- local developer workflow is documented.

Work:

- Remove `seq` service from `docker-compose.yml`.
- Remove Seq env vars from `.env.example`.
- Remove Seq sink from `appsettings.Docker.json`.
- Remove `Serilog.Sinks.Seq` package if no longer used.
- Update `README.md`.
- Update `HowToRunLocally.md`.
- Update `RunLocal.ps1` output if it prints Seq URL.
- Update `docker/local-status.py` if it checks Seq.

Verification:

- local Docker starts without Seq.
- logs appear in Loki/Grafana.
- Docker logs are rotated.
- `RunLocal.ps1` prints Grafana instead of Seq.
- `docker/local-status.py` reports Grafana/Loki/Prometheus readiness instead of Seq.
- tests pass.
- docs no longer advertise Seq.

### Phase 4: Shared Observability Assets

Status: not started.

Work:

- Create `Deployment/Common/observability`.
- Add dashboards.
- Add Prometheus alert rules.
- Add runbooks.
- Add validation scripts.
- Add shared capacity/cardinality validation scripts.
- Add shared Grafana datasource provisioning.
- Add shared dashboard UID conventions so LocalCluster and Cloud use the same dashboards with target variables.

Verification:

- CI validates dashboards and rules.
- CI validates shell scripts.
- CI validates no target-specific hostnames/IPs are committed under Common.
- no target-specific values leak into Common.

### Phase 5: LocalCluster Observability

Status: not started.

Work:

- Add LocalCluster observability compose and Ansible roles.
- Deploy backend on `node-main`.
- Deploy Alloy on all LocalCluster nodes.
- Add exporters on `node-db`.
- Enable Caddy/cloudflared metrics.
- Add resource limits to LocalCluster app/data/observability compose files where safe.
- Add Docker log rotation.
- Add LocalCluster observability capacity check.
- Add firewall rules.
- Add dashboard tunnel script.
- Add observability doctor script.
- Update `Deployment/LocalCluster/HowToDeployLocalCluster.md`.

Manual step expected:

```text
[ControlPC]
Run the LocalCluster deployment/observability step after scripts are committed.
```

Verification:

- capacity check passes before deployment.
- LocalCluster app acceptance passes.
- LocalCluster observability doctor passes.
- Grafana shows node-main, node-app1, node-app2, node-db.
- `node-main` has at least 25 percent free memory after startup and smoke traffic.
- no observability container is OOMKilled.
- Prometheus active series and Loki streams are below thresholds.

### Phase 6: Cloud Observability

Status: not started.

Work:

- Add Cloud observability compose and Ansible roles.
- Deploy backend on `cloud-main`.
- Deploy Alloy on all Cloud nodes.
- Add exporters on `cloud-db`.
- Enable Caddy/cloudflared metrics.
- Add resource limits to Cloud app/data/observability compose files where safe.
- Add Docker log rotation.
- Add Cloud observability capacity check that queries the chosen Hetzner server type and current node resources.
- Add firewall rules.
- Add dashboard tunnel script.
- Add observability doctor script.
- Update `Deployment/Cloud/HowToDeployCloud.md`.
- Update quick destroy/recreate scripts for observability data notes.

Manual step expected:

```text
[CurrentPC]
Run Cloud provision/deploy after scripts are committed.
```

Verification:

- capacity check passes before deployment.
- Cloud app acceptance passes.
- Cloud observability doctor passes.
- Grafana shows cloud-main, cloud-app1, cloud-app2, cloud-db.
- `cloud-main` has at least 25 percent free memory after startup and smoke traffic.
- no observability container is OOMKilled.
- Prometheus active series and Loki streams are below Cloud thresholds.
- `quick-destroy-cloud.sh --plan-only` clearly warns about Cloud observability data loss.

### Phase 7: Alerts

Status: not started.

Work:

- Add alert rules.
- Add runbook links.
- Configure contact point.
- Test safe alerts.
- Add memory-pressure alerts for host and containers.
- Add disk-pressure alerts for host and observability volumes.
- Add Prometheus active-series growth alert.
- Add Loki ingestion/stream growth alert.
- Add Tempo ingestion/drop alert.
- Add Alloy dropped telemetry alert.

Verification:

- alert fires for a controlled test condition.
- notification arrives.
- alert resolves cleanly.
- runbook link works.

## Operator Scripts

Planned scripts:

```text
Deployment/LocalCluster/Scripts/open-observability-tunnel.sh
Deployment/LocalCluster/Scripts/observability-capacity-check.sh
Deployment/LocalCluster/Scripts/observability-doctor.sh
Deployment/Cloud/Scripts/open-observability-tunnel.sh
Deployment/Cloud/Scripts/observability-capacity-check.sh
Deployment/Cloud/Scripts/observability-doctor.sh
Deployment/Cloud/Scripts/observability-resource-report.sh
Deployment/Common/observability/scripts/validate-observability.sh
Deployment/Common/observability/scripts/check-compose-resource-limits.sh
Deployment/Common/observability/scripts/check-telemetry-cardinality.sh
Deployment/Common/observability/scripts/smoke-observability.sh
```

Doctor output should report:

- Grafana reachable.
- Prometheus reachable.
- Loki reachable.
- Tempo reachable.
- Alloy healthy on every node.
- app metrics received in last 5 minutes.
- app logs received in last 5 minutes.
- app traces received in last 5 minutes.
- Caddy metrics present.
- cloudflared metrics present.
- PostgreSQL exporter present.
- Redis exporter present.
- public probes passing.
- origin probes passing.
- deployed SHA per app node.

## Acceptance Criteria

The observability implementation is complete when:

- Seq is removed.
- local Grafana stack replaces local Seq.
- app logs, metrics, and traces are visible in Grafana.
- LocalCluster Grafana shows every LocalCluster node.
- Cloud Grafana shows every Cloud node.
- dashboards identify both app nodes separately.
- Caddy upstream health is visible.
- cloudflared tunnel health is visible.
- PostgreSQL and Redis metrics are visible.
- host and container metrics are visible.
- public health and origin health are separate.
- deployed SHA is visible per app node.
- alert rules exist for the first critical failure modes.
- dashboards and rules are versioned in git.
- LocalCluster and Cloud guides explain how to open dashboards.
- no observability port is public.
- observability containers have explicit memory and CPU limits.
- app/data containers have explicit memory and CPU limits where Compose enforcement is verified.
- Docker log rotation is configured.
- health/static request logs do not create normal Loki noise.
- active Prometheus series and Loki streams are below documented thresholds.
- trace sampling can be reduced without redeploying code.
- the app still serves traffic when Alloy/Loki/Tempo/Prometheus are down.
- no observability rollout leaves less than 25 percent free host memory at steady state.
- no observability container is OOMKilled during startup plus smoke traffic.
- capacity, doctor, and tunnel scripts exist for LocalCluster and Cloud.
- existing app acceptance checks still pass.

## First Implementation Slice

Do this first:

1. Add no-change capacity/resource-limit check scripts.
2. Add OpenTelemetry to the app, disabled by default.
3. Suppress health/static request log noise and remove created-book title logging.
4. Add local Grafana/Prometheus/Loki/Tempo/Alloy profile with memory limits, retention, and log rotation.
5. Keep Seq temporarily only during comparison.
6. Prove one request appears as:
   - metric in Prometheus/Grafana.
   - log in Loki/Grafana.
   - trace in Tempo/Grafana.

7. Prove resource reports stay under warning thresholds during smoke traffic.
8. Remove Seq once parity is proven.

Do not start with Cloud or LocalCluster observability. Starting local keeps the feedback loop short and avoids debugging firewalls, Ansible, Hetzner, Cloudflare, and telemetry at the same time.

## Handoff Summary For Next Agent

If this plan is handed to another AI, give it this instruction:

```text
Implement ObservabilityPlan.md one phase at a time.
Do not redesign the stack.
Use Grafana, Prometheus, Loki, Tempo, Grafana Alloy, OpenTelemetry, blackbox_exporter, postgres_exporter, and redis_exporter.
Do not add nodes or servers.
Do not expose observability ports publicly.
Do not require a Cloudflare API token.
Do not remove Seq until local Loki/Grafana log parity is proven.
Start with Phase 0 and Phase 1 only.
Before editing, inspect the files listed in "Files To Inspect First".
After editing, run the verification commands listed in the phase.
If a check fails, stop and fix it before continuing.
```

The most likely mistakes by a weaker agent:

- starting with Cloud before local Docker works.
- adding an extra observability node.
- exposing Grafana publicly.
- leaving Seq and Loki both running permanently.
- using request IDs, user IDs, URLs, book IDs, or trace IDs as labels.
- forgetting resource limits and retention limits.
- logging `/health/ready` every 5 seconds into Loki.
- making OpenTelemetry export required for app startup.
- putting target-specific values in `Deployment/Common`.
- updating dashboards manually in Grafana instead of provisioning from git.

## Official References Used

- OpenTelemetry .NET docs: https://opentelemetry.io/docs/languages/dotnet/
- Microsoft .NET OpenTelemetry observability: https://learn.microsoft.com/en-us/dotnet/core/diagnostics/observability-with-otel
- Microsoft ASP.NET Core health checks: https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks
- Grafana Alloy introduction: https://grafana.com/docs/alloy/latest/introduction/
- Grafana Alloy application observability setup: https://grafana.com/docs/opentelemetry/collector/grafana-alloy/
- Grafana Alloy memory limiter docs: https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.processor.memory_limiter/
- Grafana Alloy batch processor docs: https://grafana.com/docs/grafana-cloud/send-data/alloy/reference/components/otelcol/otelcol.processor.batch/
- Grafana provisioning docs: https://grafana.com/docs/grafana/latest/administration/provisioning/
- Prometheus configuration docs: https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- Prometheus alerting docs: https://prometheus.io/docs/alerting/latest/overview/
- Prometheus metric and label naming docs: https://prometheus.io/docs/practices/naming/
- Prometheus instrumentation practices: https://prometheus.io/docs/practices/instrumentation/
- Prometheus storage docs: https://prometheus.io/docs/prometheus/latest/storage/
- Loki label docs: https://grafana.com/docs/loki/latest/get-started/labels/
- Loki label best practices: https://grafana.com/docs/loki/latest/get-started/labels/bp-labels/
- Loki retention docs: https://grafana.com/docs/loki/latest/operations/storage/retention/
- Tempo configuration docs: https://grafana.com/docs/tempo/latest/configuration/
- Docker Compose service resource docs: https://docs.docker.com/reference/compose-file/services/
- Caddy metrics docs: https://caddyserver.com/docs/metrics
- Caddy metrics directive docs: https://caddyserver.com/docs/caddyfile/directives/metrics
- Cloudflare Tunnel metrics docs: https://developers.cloudflare.com/tunnel/monitoring/
- Prometheus blackbox_exporter: https://github.com/prometheus/blackbox_exporter
- Prometheus node_exporter: https://github.com/prometheus/node_exporter
- PostgreSQL exporter: https://github.com/prometheus-community/postgres_exporter
- Redis exporter: https://github.com/oliver006/redis_exporter
