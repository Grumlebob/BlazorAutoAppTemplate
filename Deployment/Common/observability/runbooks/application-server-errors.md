# Application Server Errors

Check the Grafana application dashboard first.

1. Open the HTTP request panel and identify the route or status code.
2. Open Loki logs for the same time range and filter by `service="web"`.
3. Use the `TraceId` field from the request log to open the matching Tempo trace.
4. Confirm whether the error is app code, database, Redis, or upstream connectivity.
5. Keep health/static requests out of the investigation unless the failing route is `/health/ready`.
