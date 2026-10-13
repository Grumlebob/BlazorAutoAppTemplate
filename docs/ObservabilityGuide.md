# Observability

Optional, private telemetry is supported for local Docker, LocalCluster, and Cloud. LocalSingleNode keeps observability disabled. App startup and requests must continue when telemetry is disabled or unavailable.

## Choose a route

- Start a local stack, open dashboards, query data, validate, or recover: [Operations](Observability/Operations.md).
- Reach a deployed dashboard or run its doctor: use [LocalCluster observability operations](../Deployment/LocalCluster/Operations.md#observe-the-stack) or [Cloud observability operations](../Deployment/Cloud/Operations.md#observe-the-stack), then use [Operations](Observability/Operations.md) for shared queries and recovery.
- Change instrumentation, signal flow, labels, correlation, or sampling: [Architecture](Observability/Architecture.md).
- Investigate a specific failure: start with the diagnosis routes and linked runbooks in [Operations](Observability/Operations.md).

Do not expose observability services publicly. The app must keep serving requests if telemetry export fails.
