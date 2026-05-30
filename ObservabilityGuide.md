# Observability Guide

This is the short operator guide for the current observability stack.

## Current Status

Local Docker:

- Grafana, Prometheus, Loki, Tempo, and Alloy are optional.
- Start them with `.\RunLocal.ps1 -Observability`.

LocalCluster:

- Grafana, Prometheus, Loki, and Tempo run on `node-main`.
- Alloy and node-exporter run on every LocalCluster node.
- PostgreSQL and Redis exporters run on `node-db`.
- Dashboards are private and reached through SSH tunneling.

Cloud:

- Cloud app deployment and health checks are live.
- Cloud observability is not implemented yet. It is tracked in `ObservabilityPlan.md` Phase 6.

Alerts:

- Prometheus alert rules are versioned in git.
- Alert notification delivery is not wired yet. It is tracked in `ObservabilityPlan.md` Phase 7.

## Components

- Grafana: dashboards and Explore UI.
- Prometheus: metrics and alert rule evaluation.
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

Open:

```text
http://localhost:3000
```

Useful local endpoints:

```text
Grafana:    http://localhost:3000
Prometheus: http://localhost:9090
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
- Cloud observability: not implemented yet.

The LocalCluster CD preflight runs a capacity check before deploying observability. The CD observability doctor checks scrape targets, dashboard provisioning, cardinality budgets, and OOMKilled state after app acceptance.

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

Run the app acceptance check after any recovery action.
