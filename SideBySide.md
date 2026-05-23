# Side-By-Side LocalCluster Notes

Goal: run two independent forks/apps on the same four Linux Mint nodes at the same time.

Non-goal: shared database design. Each app gets its own PostgreSQL container and Redis container, using separate published host ports.

The normal guide remains a single-site guide first. If this is the only app on the nodes, keep the default ports and do not create extra GitHub repository variables.

## Implemented Design

- PostgreSQL and Redis host ports are configurable through `postgres_port` and `redis_port`.
- Caddy routes by `public_hostname`, but binds only to `127.0.0.1` on `node-main`.
- Cloudflare Tunnel stays shared by default; each public hostname points to `http://127.0.0.1:80`.
- The Cloudflare helper preserves existing tunnel hostnames and refuses accidental tunnel token replacement during deploy.
- Docker published-port firewalling uses app-specific `DOCKER-USER` chains instead of flushing shared rules.
- GitHub runners are installed under `/opt/actions-runner-<app_name>`.
- Each runner gets the shared `localcluster` label and an app-specific label derived from `app_name`.
- CD can target an app-specific runner with repository variable `LOCALCLUSTER_RUNNER_LABEL`.
- CD can target an app-specific GitHub environment with repository variable `LOCALCLUSTER_ENVIRONMENT`.
- CD deploys use a lock on `node-main`.
- Manual deploys use the same `node-main` lock through SSH.
- Deploy preflight checks port collisions and rejects a `deploy_root` that belongs to another marked app.

## Unique Values Per App

For a second fork on the same nodes, do not reuse these values from the first app:

- `app_name`
- `app_image`
- `app_port`
- `postgres_port`
- `redis_port`
- `deploy_root`
- `public_hostname`
- `migration_bundle_name`
- GitHub runner name derived from `app_name`
- GitHub runner label derived from `app_name`

The second fork normally reuses the same machine IPs, `cloudflare_tunnel_name`, and Cloudflare tunnel token.

## Example Shape

```yaml
# app 1
app_name: notes
app_port: 8080
postgres_port: 5432
redis_port: 6379
deploy_root: /opt/notes
public_hostname: notes.example.com

# app 2
app_name: secondnotes
app_port: 8081
postgres_port: 5433
redis_port: 6380
deploy_root: /opt/secondnotes
public_hostname: secondnotes.example.com
```

For the second fork, set GitHub repository variable `LOCALCLUSTER_RUNNER_LABEL` to `localcluster-secondnotes` if you want CD to use only that app's runner. Set `LOCALCLUSTER_ENVIRONMENT` only if you want a separate GitHub deployment environment.

## Remaining Validation

Still validate on real nodes before considering side-by-side production-proven:

- Deploy app A with default ports.
- Deploy app B with distinct app, PostgreSQL, and Redis ports.
- Confirm app A Caddy and firewall rules survive app B deployment.
- Confirm app B Caddy and firewall rules survive app A redeployment.
- Confirm app A and app B CD jobs serialize through the shared node-main deploy lock.
- Confirm both public hostnames route through the same Cloudflare tunnel.
