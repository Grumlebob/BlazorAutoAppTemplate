# Observability Guide

This is the short operator guide for the current observability stack.

## Current Status

Local Docker:

- Grafana, Prometheus, Alertmanager, Loki, Tempo, and Alloy are optional.
- Start them with `.\RunLocal.ps1 -Observability`.

LocalCluster:

- Grafana, Prometheus, Alertmanager, Loki, and Tempo run on `node-main`.
- Alloy and node-exporter run on every LocalCluster node.
- PostgreSQL and Redis exporters run on `node-db`.
- Dashboards are private and reached through SSH tunneling.

Cloud:

- Cloud app deployment and health checks are live.
- Grafana, Prometheus, Alertmanager, Loki, and Tempo run on `cloud-main`.
- Alloy and node-exporter run on every Cloud node.
- PostgreSQL and Redis exporters run on `cloud-db`.
- Dashboards are private and reached through SSH tunneling.

Alerts:

- Prometheus alert rules are versioned in git and routed to Alertmanager.
- External alert destinations such as Slack, PagerDuty, or email are not configured because no destination secret has been provided yet.

## Components

- Grafana: dashboards and Explore UI.
- Prometheus: metrics and alert rule evaluation.
- Alertmanager: alert routing, grouping, silencing, and local alert state.
- Loki: centralized logs.
- Tempo: distributed traces.
- Grafana Alloy: local collector for OTLP telemetry and Docker logs.
- node-exporter: host metrics.
- postgres-exporter: PostgreSQL metrics.
- redis-exporter: Redis metrics.

## Local Docker

[CurrentPC]

```powershell
.\RunLocal.ps1 -Observability
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

Warm the dashboards with safe read-only traffic:

```powershell
.\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
```

Use the last 15 minutes in Grafana. Normal smoke and demo simulation runs should show `unexpected 429: 0`; if `429` appears, the simulator records it separately and backs off according to `Retry-After`. Authenticated simulation adds book create/update/delete activity for the Books panels and then cleans up V2 synthetic books.

The shared Bash smoke script checks the same core telemetry path and can be run from WSL or Linux shells:

```bash
bash ./Deployment/Common/observability/scripts/smoke-observability.sh
```

Open:

```text
http://localhost:3000
```

Useful local endpoints:

```text
Grafana:    http://localhost:3000
Prometheus: http://localhost:9090
Alertmanager: http://localhost:9093
Loki:       http://localhost:3100
Tempo:      http://localhost:3200
Alloy:      http://localhost:12345
```

All local observability ports bind to `127.0.0.1`.

## LocalCluster

Run the app and observability checks from the control machine:

[ControlPC]

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
bash ./Deployment/LocalCluster/Scripts/observability-doctor.sh
```

Open Grafana from CurrentPC:

[CurrentPC]

```bash
cd "$(git rev-parse --show-toplevel)"
CONTROLPC_SSH_TARGET=jacob@node-main bash ./Deployment/LocalCluster/Scripts/open-observability-tunnel.sh
```

Then open:

```text
http://127.0.0.1:3000
```

If `node-main` is not resolvable from CurrentPC, use:

```bash
CONTROLPC_SSH_TARGET=jacob@<node-main-lan-ip> bash ./Deployment/LocalCluster/Scripts/open-observability-tunnel.sh
```

## Cloud

Run the app and observability checks from CurrentPC while temporary SSH access is available, or from GitHub Actions during `CD - Cloud`:

[CurrentPC]

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/acceptance-check.sh
bash ./Deployment/Cloud/Scripts/observability-doctor.sh
```

Open Cloud Grafana from CurrentPC:

[CurrentPC]

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/open-observability-tunnel.sh
```

Then open:

```text
http://127.0.0.1:3000
```

## Dashboards

Open Grafana and use:

```text
Application Observability Overview
```

The dashboard includes:

- request rate by route and app instance.
- app logs from Loki.
- book operation metrics.
- recent traces from Tempo.
- app instance inventory with `service_version`, which is the deployed image SHA on LocalCluster and Cloud.

Use the dashboard variables to narrow by service job, instance, deployment target, or trace service.

## Fast Health Queries

In Prometheus:

```promql
up{job="node-exporter"}
up{job="alloy"}
up{job="postgres-exporter"}
up{job="redis-exporter"}
sum(rate(http_server_request_duration_seconds_count[5m])) by (job, instance, http_route)
prometheus_tsdb_head_series
```

To run a safe Alertmanager route test:

```bash
bash ./Deployment/Common/observability/scripts/test-alertmanager-route.sh http://127.0.0.1:9093 local
```

In Loki:

```logql
{service="web", deployment_target="localcluster"}
{service="web", deployment_target="localcluster", node="node-app1"}
{service="web", deployment_target="localcluster"} |= "Error"
```

In Tempo:

```traceql
{ resource.service.name = "books" }
```

## Guardrails

Do not expose Grafana, Prometheus, Loki, Tempo, Alloy, or exporter ports publicly.

Current retention:

- Local Docker: short local retention.
- LocalCluster Prometheus: 7 days or 6 GB.
- LocalCluster Loki: 7 days.
- LocalCluster Tempo: 24 hours.
- Cloud Prometheus: 7 days or 4 GB.
- Cloud Loki: 3 days.
- Cloud Tempo: 24 hours.
Alertmanager stores only short local alert state; dashboard/rule definitions are recreated from git.

The LocalCluster and Cloud CD preflights run capacity checks before deploying observability. Each CD observability doctor checks scrape targets, dashboard provisioning, cardinality budgets, and OOMKilled state after app acceptance.

Caddy and cloudflared are still verified by the deployment acceptance checks as active services and healthy routing paths. Their native Prometheus metrics are not enabled in v1 because exposing those endpoints from host services into containerized Prometheus needs a separate private-exposure design.

## Disable Or Recover

To stop local observability:

[CurrentPC]

```powershell
docker compose --profile observability down
```

To disable LocalCluster telemetry export, set `observability_enabled: false` in `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` and deploy through LocalCluster CD. The app compose still creates the external observability network so the app can start safely even when telemetry export is disabled.

To stop LocalCluster observability containers manually:

[ControlPC]

```bash
cd /opt/books-observability && docker compose down
cd /opt/books-observability/agent && docker compose down
```

To stop Cloud observability, use `quick-destroy-cloud.sh` if the goal is to stop Hetzner billing. Cloud observability data is disposable and is destroyed with the Cloud servers.

Run the app acceptance check after any recovery action.
