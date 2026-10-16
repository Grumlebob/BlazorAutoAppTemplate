# Observability operations

Use [Architecture](Architecture.md) for signal flow, configuration ownership, labels, and sampling. This guide covers access, diagnosis, validation, retention, capacity, and recovery.

## Access dashboards

Start the local stack from the repository root:

```powershell
.\Scripts\RunLocal.ps1 -Observability
```

Open Grafana at `http://127.0.0.1:3000`. Prometheus is at `http://127.0.0.1:9090`, Alertmanager at `http://127.0.0.1:9093`, Loki at `http://127.0.0.1:3100`, and Tempo at `http://127.0.0.1:3200`. The ports bind to loopback; local Grafana allows anonymous admin access, so never publish these ports. Port overrides are in [`.env.example`](../../.env.example).

For deployed dashboards, follow the tunnel and doctor commands in [LocalCluster operations](../../Deployment/LocalCluster/Operations.md#observe-the-stack) or [Cloud operations](../../Deployment/Cloud/Operations.md#observe-the-stack). Keep the tunnel open. Do not expose Grafana, Prometheus, Alertmanager, Loki, Tempo, Alloy, or exporter ports publicly.

## Diagnose signals

Use the default Grafana dashboard first. Select the target and instance, use a recent time range, and check that each expected app instance reports the deployed `service_version`. Local Docker has less host coverage than LocalCluster and Cloud.

Useful Prometheus queries:

```promql
up{job="node-exporter"}
target_info{service_version!=""}
sum(rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
```

Useful Loki query:

```logql
{service="web"} |= "Error"
```

For a failing route, check the secret-free `/health/ready` endpoint and target acceptance result first. Then correlate app logs and traces with the `TraceId` field. Use the focused runbook for [application server errors](../../Deployment/Common/observability/runbooks/application-server-errors.md), [missing telemetry](../../Deployment/Common/observability/runbooks/telemetry-missing.md), [a down target](../../Deployment/Common/observability/runbooks/observability-target-down.md), or [high cardinality](../../Deployment/Common/observability/runbooks/telemetry-cardinality.md).

The [Prometheus rules](../../Deployment/Common/observability/prometheus/rules) cover application errors, missing telemetry, target health, resource guardrails, and exporter queue failures. Alertmanager currently has no external notification destination. Caddy/cloudflared health is covered by acceptance checks; continuous public and origin probes are not configured. There is no traffic generator; use ordinary app requests or existing browser journeys to create activity.

## Validate

After starting the local stack, run its smoke check:

```powershell
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

After changing shared assets, validate the configuration. Run the resource-limit check when Compose limits change. With the local stack running, use the smoke and cardinality checks; after changing Alertmanager routing, run the safe route test:

.```powershell
bash ./Deployment/Common/observability/scripts/validate-observability.sh
bash ./Deployment/Common/observability/scripts/check-compose-resource-limits.sh
bash ./Deployment/Common/observability/scripts/smoke-observability.sh
bash ./Deployment/Common/observability/scripts/check-telemetry-cardinality.sh http://127.0.0.1:9090 http://127.0.0.1:3100 local
bash ./Deployment/Common/observability/scripts/test-alertmanager-route.sh http://127.0.0.1:9093 local
```

Deployment workflows run target capacity checks and, after acceptance, observability doctors. Use the target commands linked above for manual diagnosis. The [shared cardinality checker](../../Deployment/Common/observability/scripts/check-telemetry-cardinality.sh) defaults to 25,000 active Prometheus series and 100 Loki streams; LocalCluster uses those defaults. The [Cloud doctor](../../Deployment/Cloud/Scripts/observability-doctor.sh) currently allows 25,000 series and 300 streams.

## Retention and capacity

These are current template values; the linked configuration is authoritative if a target or fork changes them.

| Target | Prometheus | Loki | Tempo | Source |
| --- | --- | --- | --- | --- |
| Local Docker | 24 hours / 512 MB | 24 hours | 1 hour | [`docker-compose.yml`](../../docker-compose.yml), [`Loki config`](../../docker/observability/loki/loki.yml), [`Tempo config`](../../docker/observability/tempo/tempo.yml) |
| LocalCluster | 7 days / 6 GB | 7 days | 24 hours | [`LocalCluster group vars`](../../Deployment/LocalCluster/inventory/prod/group_vars/all.yml) |
| Cloud | 7 days / 4 GB | 3 days | 24 hours | [`Cloud group vars`](../../Deployment/Cloud/inventory/prod/group_vars/all.yml) |

Container memory and CPU limits are defined in Compose/Ansible source; do not raise them without measuring the host. The [LocalCluster](../../Deployment/LocalCluster/Scripts/observability-capacity-check.sh) and [Cloud](../../Deployment/Cloud/Scripts/observability-capacity-check.sh) preflights require 25% memory headroom plus target-specific free-memory and disk margins. OOM-killed containers or repeated restarts block rollout. Reduce trace sampling, log volume, scrape frequency, or retention before resizing a node; do not add an observability node.

Cloud metrics, logs, and traces are disposable and are destroyed with the Cloud servers. No remote telemetry archive is configured. Arrange an export path before destroying Cloud resources if history must be kept.

## Disable or recover

To suspend only local telemetry containers while leaving the app and data services running, stop the profile services from the repository root:

```powershell
.\Scripts\RunLocal.ps1 -StopObservability
```

This preserves volumes. The app may still attempt telemetry export, but export failure must not block requests. To resume the local telemetry profile, use `RunLocal.ps1 -Observability`.

For deployed targets, set `observability_enabled: false` through the target's normal settings and deployment route. Do not stop Compose services manually on a deployed shared host. The [Cloud destroy procedure](../../Deployment/Cloud/Operations.md#destroy-or-recreate-the-stack) deletes telemetry history and app data; use it only when that loss is intended.

For resource pressure, recover in this order: lower or disable app trace export; stop Tempo if traces are the source; reduce log collection or retention; increase scrape intervals; stop the target's observability backend through its documented route; then rerun normal app acceptance. Restore temporary sampling changes after recovery. Do not destroy PostgreSQL, Redis, tunnel, or runner state to recover observability.
