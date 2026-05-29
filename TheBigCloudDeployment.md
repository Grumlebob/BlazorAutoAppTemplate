# The Big Cloud Deployment

Status: planning only

Date: 2026-05-29

## Goal

Design a second, independent deployment target under `Deployment/Cloud` for a Hetzner Cloud VPS fleet.

The target site is:

```text
https://bookscloud.jacobgrum.com
```

This cloud deployment must be independent from the LocalCluster deployment:

- LocalCluster remains `books.jacobgrum.com`.
- Cloud becomes `bookscloud.jacobgrum.com`.
- Each deployment has its own PostgreSQL database, Redis instance, Data Protection keys, backups, runtime state, and deployment secrets.
- Both deployments can run the exact same app code and image.
- The separation is intentional, because the two sites demonstrate different deployment abilities.

## Current LocalCluster Review

The current deployment is not just "Docker Compose". It is a full four-node local production design:

- CI builds and tests the app.
- CI publishes a GHCR image.
- CI builds an EF Core migration bundle.
- CD runs from a self-hosted GitHub runner on `node-main`.
- Ansible deploys to four machines:
  - `node-main`: Caddy, Cloudflare Tunnel, control/routing.
  - `node-app1`: app container.
  - `node-app2`: app container.
  - `node-db`: PostgreSQL and Redis.
- Caddy routes by hostname to both app nodes and keeps sticky sessions.
- Cloudflare Tunnel exposes the local cluster without public router forwarding.
- PostgreSQL and Redis run through a node-db compose stack.
- App servers run a separate compose stack.
- EF migrations run once before app containers start.
- Pre-migration database backups are created with `pg_dump`.
- Health checks verify app, PostgreSQL, Redis, Caddy, cloudflared, public HTTPS, compose state, and data ports.
- Firewall rules protect Docker-published ports.
- App ownership markers prevent accidental side-by-side collisions.

That is a strong local-lab deployment. It is a better conceptual match for a multi-VPS cloud design than for a one-node VPS, but the implementation still has local-network assumptions that should not leak into `Deployment/Cloud`.

## What Should Be Reused

Reuse concepts and tested behavior:

- The existing `BlazorAutoApp/Dockerfile`.
- The GHCR image as the release artifact.
- The EF Core migration bundle idea.
- The deployment order:
  - render env
  - start PostgreSQL/Redis
  - backup database
  - run migrations once
  - pull/start app
  - reload ingress
  - run acceptance checks
- The health endpoint contract:
  - `/health/live`
  - `/health/ready`
  - `/health`
- The backup and restore script shape.
- The settings validation pattern.
- The summary/preflight/acceptance-check idea.
- The Caddy reverse proxy pattern.
- The Cloudflare Tunnel pattern if choosing tunnel-based cloud ingress.
- The rule that Redis is required outside local/test fallback.
- The rule that Docker deployments set `Database__RunMigrationsAtStartup=false`.

Reuse files carefully:

- It is fine to copy and simplify parts of LocalCluster scripts into `Deployment/Cloud`.
- It is not ideal for `Deployment/Cloud` scripts to import from `Deployment/LocalCluster`, because the goal is an independent deployment folder.
- Use `Deployment/Common` as the shared boundary, but grow it slowly.
- First extract only values and pure helper scripts that are genuinely deployment-target independent.
- After every extraction, verify that LocalCluster CI and CD still work.
- Cloud should only depend on a Common item after LocalCluster already uses that item successfully.

## What Should Not Be Reused Directly

Do not reuse the LocalCluster implementation directly:

- The four-machine idea fits the cloud target, but the host aliases, network, firewall, bootstrap, and runner assumptions must be cloud-specific.
- `node-main`, `node-app1`, `node-app2`, and `node-db` names do not belong in cloud.
- Local router/DHCP workflow does not apply.
- Linux Mint preparation is not the right default for Hetzner cloud. Use Ubuntu LTS or Debian.
- LocalCluster app ownership marker collision checks are too local-network-specific.
- LocalCluster Docker firewall rules assume LAN addresses and a local-machine threat model. Cloud needs role-specific Hetzner Firewall rules plus host firewall defense in depth.
- Self-hosted runner on the deployment target is not necessary for Hetzner and increases the attack surface.
- CI used to read image and migration names from `Deployment/LocalCluster/inventory/prod/group_vars/all.yml`. That coupling is the first thing to move into `Deployment/Common`.

## Important Shared Boundary To Refactor Carefully

Before the Common refactor, CI read:

```bash
Deployment/LocalCluster/Scripts/read-deploy-setting.sh app_name
Deployment/LocalCluster/Scripts/read-deploy-setting.sh app_image
Deployment/LocalCluster/Scripts/read-deploy-setting.sh migration_bundle_name
```

That means the build artifact names were controlled by the LocalCluster settings. This was acceptable for one deployment target, but it is the wrong boundary for two independent deployments.

Recommended shared boundary:

```text
Deployment/Common/
  README.md
  release.yml
  Scripts/
    read-release-setting.sh
```

Example `Deployment/Common/release.yml`:

```yaml
app_image: ghcr.io/grumlebob/books
migration_bundle_name: books-migrate
migration_artifact_name: books-migrate-linux-x64
```

Then:

- CI reads `Deployment/Common/release.yml` for build artifact settings.
- LocalCluster CD keeps reading LocalCluster deployment settings for LocalCluster-only values such as `app_name`, `public_hostname`, and `runner_label`.
- LocalCluster CD reads shared artifact values from `Deployment/Common` after CI has proven the artifact names.
- Cloud CD later reads Cloud deployment settings plus the already-proven shared artifact values from `Deployment/Common`.
- Both deployments consume the same image and same migration bundle from the same commit.
- Neither deployment owns the global build artifact names.

This preserves the useful current behavior while removing accidental LocalCluster ownership of build output.

The refactor should begin with LocalCluster. The goal is not to prepare Cloud first; the goal is to make the existing LocalCluster CI/CD use the correct shared boundary without changing its behavior.

Staged LocalCluster-first refactor:

1. Record the current LocalCluster CI/CD behavior and artifact names.
2. Add `Deployment/Common/release.yml` with values that exactly match current LocalCluster values.
3. Add `Deployment/Common/Scripts/read-release-setting.sh`.
4. Add validation that proves Common values match the current LocalCluster-derived values.
5. Run LocalCluster validation with no workflow behavior change.
6. Update CI to read `app_image`, `migration_bundle_name`, and `migration_artifact_name` from Common.
7. Run CI and confirm it publishes the same GHCR image tag and migration artifact name as before.
8. Update LocalCluster CD to read `app_image`, `migration_bundle_name`, and `migration_artifact_name` from Common while leaving LocalCluster-only values in `Deployment/LocalCluster`.
9. Run LocalCluster CD and verify the live LocalCluster deployment still works.
10. Only then let the Cloud guide and future Cloud scripts consume those Common values.

This is slower than a direct move, but every step protects the already-working LocalCluster deployment.

Good first candidates for `Deployment/Common`:

- release artifact metadata.
- read-only setting readers.
- simple shell helpers that do not know about LocalCluster or Cloud paths.
- documentation for shared artifact naming.
- later, after release metadata is stable, possibly small generic helpers such as Ansible installation or deploy locking if they have no target-specific assumptions.

Poor first candidates for `Deployment/Common`:

- Ansible inventories.
- firewall roles.
- Caddy templates.
- Docker Compose files.
- LocalCluster bootstrap scripts.
- LocalCluster deployment audit scripts.
- scripts that assume `node-main`, `node-app1`, `node-app2`, or `node-db`.

Those can be revisited later, one by one, after both deployment targets exist and the repeated shape is obvious.

## LocalCluster Verification Gates

Every `Deployment/Common` extraction should pass a LocalCluster gate before continuing.

Local checks from the developer machine:

```bash
git diff --check
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
find Deployment/LocalCluster/Scripts Deployment/Common/Scripts -type f -name '*.sh' -print0 | xargs -0 shellcheck --severity=warning
yamllint .github Deployment/LocalCluster Deployment/Common
```

Repository checks:

- CI must pass on the branch.
- CI must still build the same Docker image path:
  - `ghcr.io/grumlebob/books:<commit-sha>`
- CI must still upload the same migration artifact name:
  - `books-migrate-linux-x64`
- The downloaded file inside that artifact must still be:
  - `books-migrate`

Deployment checks:

- Dispatch `CD - Deploy LocalCluster` from `main`.
- First safe check can use `run_migrations=false` if the app schema is already current.
- When changing migration artifact wiring, run one deployment with `run_migrations=true` against disposable data or after confirming the migration bundle is expected.
- Verify `https://books.jacobgrum.com/health/ready`.
- Run the LocalCluster acceptance check.

Do not start implementing `Deployment/Cloud` scripts against a newly extracted Common helper until the LocalCluster gate has passed.

## Naming Boundary

Use cloud-specific host aliases. Do not reuse LocalCluster names in the cloud inventory.

Use these cloud host aliases from the beginning:

```text
cloud-main  - Caddy, Cloudflare Tunnel, bastion/jump host, ingress checks
cloud-app1  - app container
cloud-app2  - app container
cloud-db    - PostgreSQL and Redis
```

There is no technical downside to this. Ansible inventory host aliases are just names used by the deployment code. They do not need to match Linux hostnames, Hetzner server names, DNS records, or Docker container names, although keeping them reasonably aligned helps humans.

Recommended inventory shape:

```yaml
all:
  vars:
    ansible_user: deploy
  children:
    cloud:
      children:
        cloud_ingress:
          hosts:
            cloud-main:
              ansible_host: 203.0.113.10
              cloud_private_ip: 10.10.0.10
        cloud_app_servers:
          vars:
            ansible_ssh_common_args: "-o ProxyJump=deploy@203.0.113.10"
          hosts:
            cloud-app1:
              ansible_host: 10.10.0.11
              cloud_private_ip: 10.10.0.11
            cloud-app2:
              ansible_host: 10.10.0.12
              cloud_private_ip: 10.10.0.12
        cloud_data:
          vars:
            ansible_ssh_common_args: "-o ProxyJump=deploy@203.0.113.10"
          hosts:
            cloud-db:
              ansible_host: 10.10.0.13
              cloud_private_ip: 10.10.0.13
```

`cloud-main` should be reachable from the deployment runner over SSH. The other nodes should be reached over the Hetzner private network, preferably through `cloud-main` as an SSH bastion with `ProxyJump`. That keeps app and data nodes off the public management path while still letting Ansible manage all four machines.

These names are better than reusing `node-main`, `node-app1`, `node-app2`, and `node-db`. Nothing meaningful is lost by changing the aliases; the important thing is that group names, playbooks, firewall rules, and documentation all agree.

Workflow naming should make the same distinction:

- Keep one shared app CI for build, test, image publish, and migration bundle publish.
- Add a separate cloud deployment workflow, for example `.github/workflows/cd-cloud.yml` with display name `CD - Cloud`.
- Keep the LocalCluster deployment workflow separate, for example display name `CD - LocalCluster`.
- Do not create a full duplicate `CI - Cloud` unless cloud-specific validation later needs its own checks.

Reasoning: the app artifact is the same for both deployments. Duplicating CI would mean building and testing the same commit twice, and it can create drift between the LocalCluster and cloud artifacts. The target-specific part is deployment, not app CI.

## Cloud Architecture Options

### Option A - Multi-VPS, Docker Compose, Cloudflare Tunnel

Shape:

```text
Cloudflare -> cloudflared on cloud-main -> Caddy on cloud-main
                                             |
                                             -> cloud-app1 app container
                                             -> cloud-app2 app container

cloud-app1/cloud-app2 -> cloud-db PostgreSQL container
cloud-app1/cloud-app2 -> cloud-db Redis container
```

Ingress:

- `bookscloud.jacobgrum.com` is a Cloudflare Tunnel public hostname.
- `cloudflared` connects outbound from `cloud-main`.
- Caddy on `cloud-main` load-balances to `cloud-app1` and `cloud-app2` over the Hetzner private network.
- PostgreSQL and Redis live on `cloud-db` and accept traffic only from the app nodes over the private network.
- Hetzner Firewall can block inbound HTTP/HTTPS entirely.
- SSH is restricted to trusted IPs or temporarily to the GitHub Actions runner IP during deployment.

Pros:

- Closest reuse of LocalCluster ingress model.
- No public web ports required on the cloud servers.
- No public origin certificate complexity.
- Smaller attack surface.
- Good demonstration of secure tunnel-based cloud ingress, private networking, segmented firewalls, load balancing, and multi-node deployment automation.
- Avoids a later rewrite from one-VPS compose to multi-host inventory.

Cons:

- Less demonstration of classic public VPS ingress.
- Cloudflare Tunnel becomes a hard dependency.
- If the tunnel is misconfigured, the public site is unreachable even if the app nodes are healthy.
- Higher monthly cost and more moving parts than one VPS.
- `cloud-main` and `cloud-db` are still single points of failure unless a later phase adds redundant ingress and database architecture.

### Option B - Multi-VPS, Docker Compose, Public Caddy

Shape:

```text
Cloudflare DNS/proxy -> Hetzner public IP on cloud-main -> Caddy on cloud-main
                                                             |
                                                             -> cloud-app1 app container
                                                             -> cloud-app2 app container

cloud-app1/cloud-app2 -> cloud-db PostgreSQL container
cloud-app1/cloud-app2 -> cloud-db Redis container
```

Ingress:

- Hetzner Firewall allows inbound `80` and `443` to `cloud-main`.
- SSH is restricted to trusted IPs.
- Caddy binds public `80`/`443` on `cloud-main`.
- App, PostgreSQL, and Redis stay private on the Hetzner network.

Pros:

- More traditional cloud VPS architecture.
- Demonstrates public DNS, firewall, reverse proxy, TLS, and host hardening.
- Does not require Cloudflare Tunnel.

Cons:

- Bigger public attack surface.
- More certificate/DNS details to get right.
- Need stricter host firewall and Docker bind discipline.
- Still leaves `cloud-main` as the only public ingress node unless a later phase adds a Hetzner Load Balancer or second ingress node.

### Option C - Managed Database Elsewhere

Shape:

```text
cloud-main -> cloud-app1/cloud-app2
cloud-app1/cloud-app2 -> external managed PostgreSQL
cloud-app1/cloud-app2 -> Redis on cloud-db
```

Pros:

- Better operational database reliability if using a serious managed database provider.
- Simpler database backup story.

Cons:

- Hetzner Cloud does not provide a first-party managed PostgreSQL product in the same way AWS/RDS or Azure Database does.
- Adds a second provider.
- Less useful if the goal is to demonstrate end-to-end VPS operations.

### Option D - Kubernetes Or k3s

Pros:

- Strong platform demonstration.
- Natural stepping stone for multi-node cloud deployment.

Cons:

- Overkill for one app.
- More moving parts than value right now.
- Backups, ingress, secrets, and volume management become harder, not easier.

## Recommended Cloud Target

Use Option A first:

```text
Four Hetzner x86_64 VPS machines
Hetzner private network
Docker Compose on each service node
cloud-main: Caddy + Cloudflare Tunnel
cloud-app1: app container
cloud-app2: app container
cloud-db: PostgreSQL + Redis containers
Cloudflare Tunnel for bookscloud.jacobgrum.com
GitHub-hosted CD runner SSHs to cloud-main and reaches private nodes through cloud-main as bastion
```

Reasoning:

- It reuses the strongest parts of LocalCluster without copying local-network assumptions.
- It gives the cloud guide the right shape immediately: inventory groups, private network firewalling, Caddy upstreams, app/data separation, and multi-node acceptance checks.
- It avoids a future migration from one-host Docker Compose to multi-host Ansible.
- It is secure by default: no inbound HTTP/HTTPS required.
- It avoids certificate friction while still demonstrating Hetzner, private networking, firewall segmentation, Docker, database operations, Redis, Caddy, Cloudflare, GitHub Actions, and deployment automation.
- It can be extended later to Option B if you want a public Caddy/firewall showcase.

Tradeoff:

- It costs more than one VPS.
- It is operationally more complex.
- It is not full high availability yet. `cloud-main` and `cloud-db` remain single points of failure. The first cloud goal is multi-node deployment architecture, not a fully redundant production platform.

Recommended naming:

```yaml
app_name: bookscloud
app_image: ghcr.io/grumlebob/books
public_hostname: bookscloud.jacobgrum.com
deploy_root: /opt/bookscloud
app_port: 8080
postgres_port: 5432
redis_port: 6379
cloud_private_network_cidr: 10.10.0.0/24
cloud_main_private_ip: 10.10.0.10
cloud_app1_private_ip: 10.10.0.11
cloud_app2_private_ip: 10.10.0.12
cloud_db_private_ip: 10.10.0.13
cloudflare_tunnel_name: bookscloud-prod
migration_bundle_name: books-migrate
```

Important: `app_image` should remain `ghcr.io/grumlebob/books`. The image is the app, not the deployment target. The deployment-specific identity belongs in `app_name`, `deploy_root`, environment variables, runner/environment names, and Cloudflare hostname.

## Hetzner Cloud VPS Baseline

Target x86_64/amd64 servers first.

Why:

- The current migration bundle is built for `linux-x64`.
- The Docker image is built on GitHub's default x64 builder path.
- ARM would be possible later, but it requires deliberate multi-arch Docker images and `linux-arm64` migration bundles.

Recommended OS:

```text
Ubuntu LTS or Debian stable
```

Avoid using Linux Mint as the cloud baseline. It was fine for the local physical cluster, but cloud servers should use a standard server distribution with predictable package support.

Hetzner resources to consider:

- Four Cloud Servers:
  - `cloud-main`
  - `cloud-app1`
  - `cloud-app2`
  - `cloud-db`
- One Hetzner private network attached to all four servers.
- Hetzner Cloud Firewall rules, either one carefully scoped firewall or role-specific firewalls.
- Server backups enabled at least for `cloud-db`, preferably for all four servers.
- Optional manual snapshots before risky operations.
- Optional Volume for `cloud-db` only if root disk size becomes insufficient.

Storage decision:

- For v1, keep Docker volumes on each server root disk.
- Enable Hetzner server backups, especially on `cloud-db`.
- Also create explicit PostgreSQL dumps and copy them off-server.
- Do not rely on Hetzner server backups alone.
- If using Hetzner Volumes later, remember that Hetzner documents that server backups/snapshots do not include attached Volumes.

## Security Baseline

Minimum cloud posture:

- SSH key auth only.
- No password SSH login.
- No root SSH login.
- Dedicated `deploy` user.
- Hetzner private network for all app/database traffic.
- Hetzner Cloud Firewall:
  - allow SSH to `cloud-main` only from trusted IPs or a temporary deployment runner IP.
  - allow SSH to `cloud-app1`, `cloud-app2`, and `cloud-db` only from `cloud-main` over the private network.
  - for tunnel mode, do not allow inbound HTTP/HTTPS to any node.
  - for public Caddy mode, allow inbound `80` and `443` only to `cloud-main`.
  - allow app port `8080` on `cloud-app1` and `cloud-app2` only from `cloud-main` private IP.
  - allow PostgreSQL and Redis on `cloud-db` only from `cloud-app1` and `cloud-app2` private IPs.
- Host firewall as defense in depth.
- Do not publish PostgreSQL or Redis to the public interface.
- Bind Docker-published app/data ports to private interfaces where possible.
- Keep GHCR token read-only for deployment.
- Keep Hetzner API token out of the repo.
- Keep Cloudflare tunnel token out of the repo.
- Use GitHub environment protection for `cloud-hetzner`.
- Do not run untrusted pull request code with production secrets.

## Proposed Folder Shape

Add:

```text
Deployment/Common/
  README.md
  release.yml
  Scripts/
    read-release-setting.sh
    validate-common-release.sh

Deployment/Cloud/
  HowToDeployCloud.md
  README.md
  infra/
    opentofu/
      main.tf
      variables.tf
      outputs.tf
      terraform.tfvars.example
  inventory/
    prod/
      hosts.example.yml
      group_vars/
        all.example.yml
  compose/
    app-server/
      docker-compose.yml
    data/
      docker-compose.yml
  caddy/
    Caddyfile
  ansible/
    ansible.cfg
    playbooks/
      provision.yml
      deploy.yml
    roles/
      docker/
      app/
      postgres/
      redis/
      caddy/
      cloudflared/
      firewall/
      backup/
      bastion/
  scripts/
    read-cloud-setting.sh
    validate-cloud-settings.sh
    render-inventory-from-tofu.sh
    setup-control-machine.sh
    provision.sh
    deploy.sh
    preflight.sh
    acceptance-check.sh
    backup-db.sh
    restore-db.sh
    summary.sh
```

Add GitHub workflow:

```text
.github/workflows/cd-cloud.yml
```

Suggested workflow display names:

```yaml
name: CD - Cloud
```

Keep the existing shared build/test workflow as the app CI. Rename it only if that improves clarity, for example `CI - App`. Do not make cloud deployment own the app build artifact.

Do not make `Deployment/Cloud` depend on `Deployment/LocalCluster` paths. Reuse by copying patterns first, not by importing LocalCluster implementation details.

## Proposed Cloud Compose Shape

Use separate compose projects by role.

On `cloud-app1` and `cloud-app2`, run only the app container:

```yaml
services:
  web:
    image: ${APP_IMAGE}:${APP_VERSION}
    restart: unless-stopped
    environment:
      ASPNETCORE_ENVIRONMENT: Docker
      ASPNETCORE_HTTP_PORTS: 8080
      App__Name: ${APP_NAME}
      ForwardedHeaders__KnownProxies__0: ${CLOUD_MAIN_PRIVATE_IP}
      Database__RunMigrationsAtStartup: "false"
      ConnectionStrings__DefaultConnection: Host=${CLOUD_DB_PRIVATE_IP};Port=5432;Database=${POSTGRES_DB};Username=${POSTGRES_USER};Password=${POSTGRES_PASSWORD}
      Redis__Configuration: ${CLOUD_DB_PRIVATE_IP}:6379,password=${REDIS_PASSWORD},abortConnect=false
    ports:
      - "${APP_BIND_IP}:8080:8080"
    volumes:
      - app_storage:/app/Storage
```

On `cloud-db`, run PostgreSQL and Redis:

```yaml
services:
  postgres:
    image: postgres:18.4-alpine3.23
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql
    ports:
      - "${CLOUD_DB_PRIVATE_IP}:5432:5432"

  redis:
    image: redis:8.8.0-alpine3.23
    restart: unless-stopped
    command:
      - redis-server
      - --requirepass
      - ${REDIS_PASSWORD}
      - --appendonly
      - "yes"
      - --appendfsync
      - everysec
    volumes:
      - redis_data:/data
    ports:
      - "${CLOUD_DB_PRIVATE_IP}:6379:6379"
```

Notes:

- App nodes need to publish `8080` so `cloud-main` can reach them over the private network. `APP_BIND_IP` should be the app node's private IP, and validation should fail if it is empty.
- PostgreSQL and Redis need to publish their ports on `cloud-db` so app nodes can reach them, but they must bind to `CLOUD_DB_PRIVATE_IP`, not `0.0.0.0`.
- Do not publish app, PostgreSQL, or Redis to public interfaces.
- PostgreSQL and Redis should listen only where the app nodes can reach them.
- Run the EF migration bundle on `cloud-db` before app containers are started.
- Keep `cloud-main` as host-level Caddy/cloudflared first. Do not put cloud ingress into the app compose files.
- Per-app-node `app_storage` is acceptable for current runtime storage because Redis backs shared Data Protection state. If the app later adds user-uploaded files or generated media, move that data to PostgreSQL, object storage, or a deliberately shared storage design before relying on two app nodes.

## Caddy And Forwarded Headers

The app currently trusts explicitly configured forwarded headers only. That is good.

For Cloud:

- Caddy runs on `cloud-main`.
- App containers should trust `cloud-main` private IP as the known proxy.
- Caddy should route to `cloud-app1` and `cloud-app2` private IPs.
- Keep sticky sessions for Blazor Server.
- Do not switch to trust-all forwarded headers.

Tunnel mode Caddy:

```caddyfile
http://bookscloud.jacobgrum.com {
  bind 127.0.0.1
  reverse_proxy 10.10.0.11:8080 10.10.0.12:8080 {
    lb_policy cookie bookscloud_lb
    health_uri /health/ready
    health_interval 5s
    health_timeout 2s
    header_up X-Forwarded-Proto https
    header_up X-Forwarded-Host {host}
  }
}
```

Public Caddy mode should be treated as a separate variant:

```caddyfile
bookscloud.jacobgrum.com {
  reverse_proxy 10.10.0.11:8080 10.10.0.12:8080 {
    lb_policy cookie bookscloud_lb
    health_uri /health/ready
    health_interval 5s
    health_timeout 2s
    header_up X-Forwarded-Host {host}
  }
}
```

## GitHub Actions Design

Use GitHub-hosted runners for cloud CD.

Why:

- `cloud-main` is reachable over SSH.
- `cloud-app1`, `cloud-app2`, and `cloud-db` can be reached through `cloud-main` as an SSH bastion over the private network.
- There is no need to install a self-hosted runner on the cloud servers.
- A deployment target should not also execute arbitrary GitHub job code unless there is a specific reason.

Deployment connectivity:

- The workflow discovers its current public runner IP.
- The workflow uses the Hetzner API to add a temporary SSH allow rule for that runner IP to `cloud-main`.
- Ansible connects to `cloud-main` directly.
- Ansible connects to `cloud-app1`, `cloud-app2`, and `cloud-db` through `cloud-main` using `ProxyJump`.
- The SSH private key stays on the GitHub runner; `cloud-main` only forwards the SSH connection.
- The workflow removes the temporary SSH allow rule in an `always` cleanup step.

This avoids permanently opening SSH to broad GitHub-hosted runner IP ranges.

Proposed workflow:

```text
.github/workflows/cd-cloud.yml
```

Trigger:

```yaml
workflow_dispatch:
  inputs:
    run_migrations:
      required: true
      default: "true"
      type: choice
      options: ["true", "false"]
```

Environment:

```yaml
environment:
  name: cloud-hetzner
```

Secrets:

- `CLOUD_SSH_PRIVATE_KEY`
- `CLOUD_BASTION_HOST`
- `CLOUD_SSH_USER`
- `CLOUD_HETZNER_API_TOKEN`
- `CLOUD_HETZNER_FIREWALL_ID`
- `CLOUD_GHCR_USERNAME`
- `CLOUD_GHCR_TOKEN`
- `CLOUD_POSTGRES_USER`
- `CLOUD_POSTGRES_PASSWORD`
- `CLOUD_POSTGRES_DB`
- `CLOUD_REDIS_PASSWORD`
- `CLOUD_CLOUDFLARE_TUNNEL_TOKEN`

Workflow responsibilities:

- require `main`
- require successful CI for the same commit
- temporarily allow SSH from the runner IP to `cloud-main`
- verify image exists
- download migration bundle from CI if migrations are enabled
- install Ansible
- SSH to `cloud-main`
- reach private nodes through `cloud-main` as bastion
- render runtime env files per node role
- deploy PostgreSQL and Redis on `cloud-db`
- backup DB before migrations on `cloud-db`
- run migration bundle once on `cloud-db`
- deploy app containers on `cloud-app1` and `cloud-app2`
- deploy Caddy and cloudflared on `cloud-main`
- run acceptance check against `https://bookscloud.jacobgrum.com/health/ready`
- remove the temporary SSH allow rule even if deployment fails

## Provisioning Design

Two reasonable paths:

### V1 Manual Servers, Ansible Software

Create the four Hetzner servers, private network, SSH key, and firewall rules manually, then let `Deployment/Cloud` configure software.

Pros:

- Faster to implement.
- Less state management.
- Acceptable if you want to prove the Ansible/runtime path before writing infrastructure code.

Cons:

- Cloud resources are not fully reproducible from code.
- More room for drift across four servers.
- More manual clicking than the single-VPS path.

### V2 OpenTofu/Terraform, Ansible Software

Use OpenTofu/Terraform for:

- Hetzner servers.
- Hetzner private network and server attachments.
- Hetzner firewall rules.
- SSH key resource.
- cloud-init/user-data for the initial `deploy` user and SSH key.
- optional Volume for `cloud-db`.
- labels.

Use Ansible for:

- Docker installation.
- users and SSH hardening.
- Caddy/cloudflared.
- compose deployment.
- backups.

Pros:

- Better cloud best-practice story.
- More reproducible.
- Shows infrastructure-as-code ability.

Cons:

- Requires backend/state decisions.
- Hetzner API token handling becomes part of the deployment story.

Recommendation:

- For multi-VPS cloud, use OpenTofu/Terraform from the first real implementation if possible.
- If time is tight, create the servers manually once, but still write the Ansible inventory and firewall model as if OpenTofu will own the infrastructure later.
- Keep Ansible responsible for software and deployment, not cloud resource creation.

## Backup Strategy

Do not treat snapshots as the only backup.

Use layered backups:

- Hetzner server backups enabled for VM-level recovery, at least on `cloud-db`.
- Manual snapshot before high-risk infrastructure changes.
- PostgreSQL `pg_dump` on `cloud-db` before every migration.
- Scheduled PostgreSQL dumps.
- Copy PostgreSQL dumps off `cloud-db`:
  - Hetzner Storage Box,
  - S3-compatible object storage,
  - or another external backup target.
- Periodically test restore to a disposable database.

Redis:

- Persist Redis append-only data.
- Redis loss is less serious than PostgreSQL loss, but it affects Data Protection keys and can invalidate auth cookies.
- Keep the Redis volume persistent.

If using Hetzner Volumes:

- Add explicit file-level backup for volume contents.
- Do not assume server backup covers attached volumes.

## Acceptance Checks

Cloud acceptance should verify:

- SSH to `cloud-main` works.
- SSH through `cloud-main` to `cloud-app1`, `cloud-app2`, and `cloud-db` works.
- Docker Compose project is running on each service node.
- PostgreSQL container is healthy on `cloud-db`.
- Redis container is healthy on `cloud-db`.
- app `/health/ready` works on `cloud-app1` and `cloud-app2` over the private network.
- Caddy can route locally on `cloud-main`.
- Caddy load-balances to both app nodes.
- cloudflared is connected on `cloud-main` if using tunnel mode.
- public `https://bookscloud.jacobgrum.com/health/ready` works.
- app home page returns success.
- no public Postgres or Redis ports are reachable.
- app port `8080` is not reachable publicly on app nodes.
- backup directory exists on `cloud-db` and latest backup verifies after migrations.

## Deployment Phases

### Phase 1 - LocalCluster-First Common Refactor

- Add `Deployment/Common/release.yml` with the same artifact values LocalCluster currently implies.
- Add `Deployment/Common/Scripts/read-release-setting.sh`.
- Add `Deployment/Common/Scripts/validate-common-release.sh`.
- Update CI to read shared artifact values from `Deployment/Common`.
- Update `CD - Deploy LocalCluster` to read shared artifact values from `Deployment/Common`.
- Keep LocalCluster-only values in `Deployment/LocalCluster`.
- Run LocalCluster validation after each small change.
- Dispatch LocalCluster CD from `main` and verify the live site still works before implementing Cloud scripts against Common.

### Phase 2 - Common Refactor Follow-Up Candidates

Only after Phase 1 is green:

- Consider moving a generic setting parser into `Deployment/Common`.
- Consider moving generic Ansible installation helper logic into `Deployment/Common`.
- Consider moving deploy-lock helper logic into `Deployment/Common` if it can stay target-neutral.
- Do not move LocalCluster-specific audit, inventory, firewall, bootstrap, Caddy, or compose code yet.

Each follow-up candidate gets its own small PR/commit and LocalCluster CI/CD verification.

### Phase 3 - Cloud Plan Skeleton

- Add `Deployment/Cloud/README.md`.
- Add `Deployment/Cloud/HowToDeployCloud.md`.
- Add cloud settings examples.
- Add validation and summary scripts.
- Use only Common helpers that LocalCluster already uses successfully.
- No cloud remote changes yet.

### Phase 4 - Hetzner Infrastructure

- Prefer OpenTofu/Terraform for four x86_64 VPS machines.
- Create `cloud-main`, `cloud-app1`, `cloud-app2`, and `cloud-db`.
- Create the Hetzner private network.
- Attach all four servers to the private network.
- Add Hetzner Firewall rules by role.
- Add SSH key resource.
- Use cloud-init/user-data to create the initial `deploy` user and install the deploy public key on all four nodes.
- Output public and private IPs for inventory rendering.

### Phase 5 - Node Provisioning

- Verify the `deploy` user from cloud-init/user-data on all four nodes, or bootstrap it manually if OpenTofu was not used.
- Restrict SSH.
- Configure `cloud-main` as the SSH bastion path for private nodes.
- Install Docker with Ansible on `cloud-app1`, `cloud-app2`, and `cloud-db`.
- Install Caddy and cloudflared prerequisites on `cloud-main`.
- Verify Ansible ping to all nodes.

### Phase 6 - Compose And Runtime

- Add Cloud app Docker Compose file for `cloud-app1` and `cloud-app2`.
- Add Cloud data Docker Compose file for `cloud-db`.
- Add Caddy config on `cloud-main` with both app node private IPs.
- Add cloudflared tunnel service on `cloud-main` for `bookscloud-prod`.
- Render `.env` files per node role.
- Start PostgreSQL and Redis on `cloud-db`.
- Run local/private-network health checks.

### Phase 7 - Cloud CD Workflow

- Add `.github/workflows/cd-cloud.yml`.
- Use GitHub-hosted runner.
- Use GitHub environment `cloud-hetzner`.
- Use the same CI image and migration bundle.
- Add temporary SSH firewall opening for the runner IP to `cloud-main`.
- Deploy to private nodes through `cloud-main` as bastion.
- Deploy with `run_migrations=true` for first deploy.

### Phase 8 - Backups And Restore

- Add cloud backup script.
- Add cloud restore script.
- Add scheduled backup plan.
- Add restore drill documentation.

### Phase 9 - Hardening

- Confirm no public DB/Redis ports.
- Confirm no unneeded Docker published ports.
- Confirm SSH restrictions.
- Confirm app nodes only accept `8080` from `cloud-main`.
- Confirm Cloudflare route.
- Confirm secrets are only in GitHub environment or encrypted vault.
- Add monitoring notes.

### Phase 10 - Optional Public Caddy Variant

Only after tunnel mode is stable:

- open `80`/`443` to `cloud-main` in Hetzner Firewall.
- configure public Caddy.
- decide Cloudflare proxy mode.
- update forwarded header trust.
- verify direct origin is not exposing data ports.

## Non-Goals For The First Pass

- No Kubernetes.
- No fully redundant high availability platform.
- No replicated PostgreSQL.
- No second ingress node.
- No LocalCluster changes except CI artifact decoupling if required.
- No data synchronization between LocalCluster and Cloud.
- No shared database.
- No replacing the current LocalCluster deployment.
- No public PostgreSQL or Redis.
- No cloud server builds; images still come from CI/GHCR.

## Open Decisions Before Implementation

- Confirm Option A multi-VPS tunnel mode is the first implementation.
- Confirm exact Hetzner OS image.
- Confirm whether Hetzner resources are created manually first or via OpenTofu immediately.
- Confirm server sizes for `cloud-main`, `cloud-app1`, `cloud-app2`, and `cloud-db`.
- Confirm whether cloud CD may use Hetzner API to temporarily allow the GitHub runner IP to SSH into `cloud-main`.
- Confirm backup destination for off-server PostgreSQL dumps.
- Confirm whether `bookscloud` should use the same GHCR image package `ghcr.io/grumlebob/books`.
- Confirm the exact first `Deployment/Common` extraction: release metadata and read script.
- Confirm LocalCluster CD verification expectation after the Common refactor.
- Confirm whether cloud secrets live only in GitHub environment secrets or also in an encrypted Ansible Vault.

## Suggested Decision

Proceed like this:

1. Start with a narrow `Deployment/Common` refactor for release artifact metadata.
2. Convert LocalCluster CI and LocalCluster CD to use that Common metadata.
3. Verify LocalCluster locally, in CI, and through `CD - Deploy LocalCluster`.
4. Add `Deployment/Cloud` as an independent folder that only uses Common pieces already proven by LocalCluster.
5. Build multi-VPS tunnel-mode deployment with `cloud-main`, `cloud-app1`, `cloud-app2`, and `cloud-db`.
6. Use a Hetzner private network for all app/database traffic.
7. Use GitHub-hosted runner for cloud CD, with `cloud-main` as the bastion.
8. Keep `bookscloud.jacobgrum.com` and `books.jacobgrum.com` completely independent at runtime.
9. Prefer OpenTofu/Terraform for Hetzner servers, network, firewall, and SSH key resources.

This keeps the already-working LocalCluster deployment as the guardrail for the refactor. The cloud plan still targets the richer multi-VPS architecture, but Common only grows when LocalCluster proves each shared piece is stable.

## Sources Reviewed

- Hetzner Cloud docs overview: `https://docs.hetzner.com/cloud/`
- Hetzner Cloud Volumes overview: `https://docs.hetzner.com/cloud/volumes/overview/`
- Hetzner Cloud Backups/Snapshots overview: `https://docs.hetzner.com/cloud/servers/backups-snapshots/overview`
- Hetzner Cloud Firewall docs: `https://docs.hetzner.com/cloud/firewalls/getting-started/creating-a-firewall/`
- Hetzner Cloud Firewall FAQ: `https://docs.hetzner.com/cloud/firewalls/faq/`
- Hetzner Cloud Server FAQ: `https://docs.hetzner.com/cloud/servers/faq`
- Cloudflare Tunnel docs: `https://developers.cloudflare.com/tunnel/`
- Cloudflare Tunnel configuration docs: `https://developers.cloudflare.com/tunnel/configuration/`
