# Cloud Compose

Cloud Docker Compose files live here.

Projects:

- `app-server`: app container for `cloud-app1` and `cloud-app2`.
- `data`: PostgreSQL, Redis, postgres-exporter, and redis-exporter containers for `cloud-db`.

Do not publish app, PostgreSQL, Redis, exporter, or observability ports on public interfaces. Bind service ports to private Hetzner network addresses or loopback only.
