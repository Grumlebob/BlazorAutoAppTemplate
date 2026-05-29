# Telemetry Missing

Use this when metrics, logs, or traces stop appearing.

1. Check whether the app is still healthy.
2. Check Alloy health and logs.
3. Check Prometheus, Loki, and Tempo health.
4. Verify the app still has OpenTelemetry enabled for that target.
5. Confirm no firewall or Docker network change blocks OTLP, Loki push, Tempo OTLP, or Prometheus remote write.
