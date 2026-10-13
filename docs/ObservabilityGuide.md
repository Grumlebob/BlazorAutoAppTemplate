# Observability

Optional, private telemetry is supported for local Docker, LocalCluster, and Cloud. LocalSingleNode keeps observability disabled. App startup and requests must continue when telemetry is disabled or unavailable.

## Choose a route

- Start a local stack, open dashboards, query data, validate, or recover: [Operations](Observability/Operations.md).
- Reach a deployed dashboard or run that target's observability doctor: use the [LocalCluster guide](../Deployment/LocalCluster/HowToDeployLocalCluster.md) or [Cloud guide](../Deployment/Cloud/HowToDeployCloud.md), then use [Operations](Observability/Operations.md) for shared queries and recovery.
- Change instrumentation, signal flow, labels, correlation, or sampling: [Architecture](Observability/Architecture.md).
- Investigate a specific failure: start with the diagnosis routes and linked runbooks in [Operations](Observability/Operations.md).

Do not expose observability services publicly. The app must keep serving requests if telemetry export fails.
