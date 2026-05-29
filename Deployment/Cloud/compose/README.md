# Cloud Compose

Cloud Docker Compose files live here.

Projects:

- `app-server`: app container for `cloud-app1` and `cloud-app2`.
- `data`: PostgreSQL and Redis containers for `cloud-db`.

Do not publish app, PostgreSQL, or Redis ports on public interfaces. Bind service ports to private Hetzner network addresses.
