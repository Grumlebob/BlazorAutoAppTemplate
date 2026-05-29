# Proper Deployment Naming Thorough

## Goal

Rename the deployed LocalCluster app from the old ship identity to a books identity while keeping the same application, same cluster, same machines, and same port choices.

The current production database and Redis state are disposable. That changes the safest path: do not migrate Docker volumes or Redis state from `ship` to `books`. Create a fresh `books` runtime identity, verify it, then remove the old `ship` runtime identity.

## Starting Facts

- Current deployed public hostname: `shipinspection.jacobgrum.com`.
- Desired public hostname: `books.jacobgrum.com`.
- Current LocalCluster settings in `Deployment/LocalCluster/inventory/prod/group_vars/all.yml`:
  - `app_name: ship`
  - `app_image: ghcr.io/grumlebob/ship`
  - `app_port: 8080`
  - `postgres_port: 5432`
  - `redis_port: 6379`
  - `public_hostname: shipinspection.jacobgrum.com`
  - `deploy_root: /opt/ship`
  - `cloudflare_tunnel_name: ship-prod`
  - `migration_bundle_name: ship-migrate`
- You already changed Cloudflare:
  - Tunnel name is now `books-prod`.
  - Public hostname `books.jacobgrum.com` is added to that tunnel.
  - The hostname routes to `http://127.0.0.1:80`.
- The current database, Redis data, Data Protection keys, and app runtime state are disposable.
- Keep using the same LocalCluster nodes:
  - `node-main`
  - `node-app1`
  - `node-app2`
  - `node-db`

## Recommended Strategy

Use a full deployment identity rename:

```yaml
app_name: books
app_image: ghcr.io/grumlebob/books
app_port: 8080
postgres_port: 5432
redis_port: 6379
public_hostname: books.jacobgrum.com
deploy_root: /opt/books
cloudflare_tunnel_name: books-prod
cloudflared_version: 2026.5.2
migration_bundle_name: books-migrate
```

This produces clean names for:

- Docker Compose project: `books`
- App containers and volumes: `books_*`
- App root: `/opt/books`
- GHCR package: `ghcr.io/grumlebob/books`
- Migration bundle artifact file: `books-migrate`
- CI artifact: `books-migrate-linux-x64`
- Deploy SSH key: `~/.ssh/books_deploy`
- GitHub runner default name: `node-main-books`
- GitHub runner default label: `localcluster-books`
- Caddy site file: `/etc/caddy/sites/books.caddy`
- Firewall unit: `books-docker-user-firewall.service`
- App marker: `/etc/localcluster/apps/books.env`

Because the current data is disposable, this is preferable to preserving `app_name: ship` or trying to rename Docker volumes in place.

## Automation Boundary

This repository is currently open on a developer PC, not on the LocalCluster control machine. That matters because the deployment scripts that touch nodes require the control machine's SSH, Ansible, GitHub runner, Docker, and Cloudflare/GitHub context.

### What Can Be Automated From This Developer PC

I can safely do repo-local work here:

- Update `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` from `ship` to `books`.
- Update `Deployment/LocalCluster/inventory/prod/hosts.yml` to use `~/.ssh/books_deploy`.
- Update active docs or plans that still point at `shipinspection.jacobgrum.com`.
- Add a focused checklist/script for the control-machine commands.
- Run repo-local validation that does not SSH to nodes.
- Search for stale `ship` deployment references.

Current limitation on this PC:

- `Deployment/LocalCluster/machines.yml` is not present here, so I cannot regenerate `hosts.yml` from the normal source file unless you copy that file into this checkout. Since `hosts.yml` already contains the node IPs, I can still update only the key path in `hosts.yml` if you want the repo prepared from this PC.
- I cannot create `~/.ssh/books_deploy` on the real control machine from here.
- I cannot install the deploy key on the nodes from here unless this PC also has network/SSH/Ansible access and the old `ship` deploy key.
- I cannot stop old containers, remove old systemd units, or run acceptance checks from here.
- I cannot guarantee GitHub package permissions for `ghcr.io/grumlebob/books`; that has to be verified through GitHub/GHCR credentials.

First manual breakpoint from this PC:

1. Review the repo edits.
2. Commit and push or merge the naming change to `main`.
3. Move to the control machine for the cluster-facing steps.

### What Can Be Automated On The Control Machine

Once the updated repo is on the control machine, most command-line work is scriptable. From the control machine, the deployment scripts can automate:

- Creating `~/.ssh/books_deploy`.
- Installing the new `books` deploy key on all nodes using `~/.ssh/ship_deploy`.
- Verifying Ansible can reach the nodes with the new key.
- Installing or configuring the `node-main-books` GitHub runner.
- Stopping old `/opt/ship` Docker Compose stacks.
- Removing the old `ship` app marker if preflight sees a side-by-side collision.
- Running deploy preflight.
- Running acceptance checks after CD.
- Removing old `/opt/ship` runtime files, old Caddy site, old marker, and old firewall service after verification.

This repo now includes a reusable helper for the control-machine cutover:

```bash
bash ./Deployment/LocalCluster/Scripts/prepare-renamed-localcluster-app.sh --old-app-name ship
```

That command is a dry run: it validates the renamed settings and prints the current/old app names without touching the cluster.

For the current state, after the new deploy key and runner are already configured, the actual pre-CD cutover command is:

```bash
bash ./Deployment/LocalCluster/Scripts/prepare-renamed-localcluster-app.sh \
  --old-app-name ship \
  --stop-old-runtime \
  --remove-old-marker \
  --preflight \
  --confirm-cutover
```

For a future rename where the new deploy key and runner have not yet been prepared, the same helper can run the fuller control-machine sequence:

```bash
bash ./Deployment/LocalCluster/Scripts/prepare-renamed-localcluster-app.sh \
  --old-app-name ship \
  --setup-control-machine \
  --install-new-key \
  --existing-key ~/.ssh/ship_deploy \
  --configure-runner \
  --stop-old-runtime \
  --remove-old-marker \
  --preflight \
  --confirm-cutover
```

Manual or semi-manual control-machine/GitHub steps still remain:

- Pull the updated repository on the control machine.
- Ensure `gh auth status` is authenticated if runner setup or GitHub CLI commands are used.
- Set or update GitHub repository variable `LOCALCLUSTER_RUNNER_LABEL=localcluster-books` while both old and new runners exist.
- Confirm the new GHCR package `ghcr.io/grumlebob/books` is readable by the deploy token.
- Trigger the GitHub CD workflow, or run the equivalent `gh workflow run` command if preferred.
- Only after `books` is verified, decide whether to remove `shipinspection.jacobgrum.com` from Cloudflare.

## Main Risk

The three port values stay the same. That means the old `ship` containers must be stopped before the first `books` deploy can start:

- app servers still use host port `8080`.
- node-db still uses host port `5432`.
- node-db still uses host port `6379`.

The old `/opt/ship` stack can block those ports until it is stopped. The plan below stops it only after the new `books` config is prepared and before the first `books` deploy.

## Phase 1 - Update Repository Deployment Settings

Edit `Deployment/LocalCluster/inventory/prod/group_vars/all.yml`:

```yaml
app_name: books
app_image: ghcr.io/grumlebob/books
app_port: 8080
postgres_port: 5432
redis_port: 6379
public_hostname: books.jacobgrum.com
deploy_root: /opt/books
cloudflare_tunnel_name: books-prod
cloudflared_version: 2026.5.2
migration_bundle_name: books-migrate
```

Run:

```bash
bash ./Deployment/LocalCluster/Scripts/validate-deploy-settings.sh
bash ./Deployment/LocalCluster/Scripts/generate-inventory.sh
bash ./Deployment/LocalCluster/Scripts/summary.sh
```

Expected summary should show:

- `app_name` is `books`.
- `app_image` is `ghcr.io/grumlebob/books`.
- `public_hostname` is `books.jacobgrum.com`.
- `deploy_root` is `/opt/books`.
- ports remain `8080`, `5432`, and `6379`.
- `cloudflare_tunnel_name` is `books-prod`.
- generated SSH key path is `~/.ssh/books_deploy`.
- runner label is `localcluster-books`.

Generated `Deployment/LocalCluster/inventory/prod/hosts.yml` should switch from:

```yaml
ansible_ssh_private_key_file: ~/.ssh/ship_deploy
```

to:

```yaml
ansible_ssh_private_key_file: ~/.ssh/books_deploy
```

## Phase 2 - Create And Install The New Deploy Key

Create the new app-specific deploy key locally:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-control-machine.sh
```

This should create:

```text
~/.ssh/books_deploy
~/.ssh/books_deploy.pub
```

Because the nodes currently trust the old `ship` deploy key, install the new `books` key using the existing key:

```bash
bash ./Deployment/LocalCluster/Scripts/prepare-existing-localcluster-app.sh --existing-key ~/.ssh/ship_deploy
```

Expected result:

- all nodes accept SSH using `~/.ssh/books_deploy`.
- node-main also receives `/home/deploy/.ssh/books_deploy`.
- Ansible can reach the cluster using the regenerated `hosts.yml`.

## Phase 3 - GitHub Runner Rename

The current runner is expected to be named and labeled from the old `ship` identity. The clean target is:

- runner name: `node-main-books`
- runner labels: `localcluster`, `localcluster-books`
- runner directory on node-main: `/opt/actions-runner-books`

Install or configure the new runner:

```bash
bash ./Deployment/LocalCluster/Scripts/install-github-runner.sh
bash ./Deployment/LocalCluster/Scripts/check-github-runner.sh
```

GitHub Actions settings:

- If repository variable `LOCALCLUSTER_RUNNER_LABEL` exists and points to `localcluster-ship`, change it to `localcluster-books`.
- If `LOCALCLUSTER_RUNNER_LABEL` does not exist, create it with value `localcluster-books` until the old runner has been removed. Without the app-specific variable, GitHub may choose any online runner with the shared `localcluster` label.
- Keep the deployment environment name as `localcluster` unless there is a separate reason to rename GitHub environments.
- Keep the same `ANSIBLE_VAULT_PASSWORD` secret.

Do not delete the old runner until the first `books` deploy succeeds. After verification, remove the old `node-main-ship` runner from GitHub and remove `/opt/actions-runner-ship` from node-main.

## Phase 4 - Vault And Cloudflare Checks

Keep `Deployment/LocalCluster/inventory/prod/vault.yml` unless you intentionally want new passwords. Since data is disposable, it is acceptable to reuse:

- `vault_postgres_user`
- `vault_postgres_password`
- `vault_postgres_db`
- `vault_redis_password`
- `vault_ghcr_username`
- `vault_ghcr_token`
- `vault_cloudflare_tunnel_token`

Important Cloudflare detail:

- Renaming the tunnel in Cloudflare does not usually change the tunnel token.
- If the token did not change, do not rotate `vault_cloudflare_tunnel_token`.
- If a new token was generated, update `vault.yml` intentionally and expect the playbook to reinstall the cloudflared service.

Run the read-only Cloudflare check if the required Cloudflare API environment variables are available:

```bash
bash ./Deployment/LocalCluster/Scripts/check-cloudflare-tunnel.sh
```

Expected result:

- tunnel named `books-prod` exists.
- `books.jacobgrum.com` exists on the tunnel.
- route target is `http://127.0.0.1:80`.
- DNS CNAME points at the selected tunnel.

## Phase 5 - Stop Old Ship Runtime Before First Books Deploy

Because we are reusing ports `8080`, `5432`, and `6379`, stop the old `ship` stacks before the first `books` deploy.

From the control machine:

```bash
ansible app_servers -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -m ansible.builtin.shell \
  -a "if [ -f /opt/ship/docker-compose.yml ]; then cd /opt/ship && docker compose down; fi"

ansible node_db -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -m ansible.builtin.shell \
  -a "if [ -f /opt/ship/docker-compose.yml ]; then cd /opt/ship && docker compose down; fi"
```

Do not remove `/opt/ship` yet. Keep it available for inspection until the `books` deployment passes acceptance.

## Phase 6 - Validate Preflight For Books

Run:

```bash
bash ./Deployment/LocalCluster/Scripts/preflight.sh deploy
```

If `validate-side-by-side.sh` reports collisions with the old `ship` marker, inspect the markers:

```bash
bash ./Deployment/LocalCluster/Scripts/list-deployed-apps.sh
```

Since this is a rename, not a real side-by-side deployment, it is acceptable to remove the old marker after the old runtime is stopped:

```bash
ansible all -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -m ansible.builtin.file \
  -a "path=/etc/localcluster/apps/ship.env state=absent" \
  --become
```

Then rerun:

```bash
bash ./Deployment/LocalCluster/Scripts/preflight.sh deploy
```

Expected result:

```text
preflight ok (deploy)
```

## Phase 7 - Build And Deploy From GitHub

Commit the deployment naming changes and push or merge them to `main`.

Wait for CI to pass. CI should publish:

- image: `ghcr.io/grumlebob/books:<commit-sha>`
- migration artifact: `books-migrate-linux-x64`
- migration file inside artifact: `books-migrate`

Before CD, confirm the GHCR token used by the cluster can read the new package name. The old token may have read access to `ghcr.io/grumlebob/ship` but not automatically to `ghcr.io/grumlebob/books`, depending on package permissions.

```bash
APP_VERSION="$(git rev-parse HEAD)"
docker manifest inspect "ghcr.io/grumlebob/books:${APP_VERSION}" >/dev/null
```

Run GitHub workflow:

```text
Actions -> CD - Deploy LocalCluster -> Run workflow
run_migrations: true
branch: main
```

Use `run_migrations: true` because `/opt/books` and the `books` Compose project are fresh.

## Phase 8 - Acceptance Verification

Run:

```bash
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
```

Also run direct public checks:

```bash
curl -I https://books.jacobgrum.com/
curl -I https://books.jacobgrum.com/health/ready
curl -I https://books.jacobgrum.com/books
```

Expected results:

- `https://books.jacobgrum.com/health/ready` succeeds.
- app nodes serve on port `8080`.
- node-db serves Postgres on `5432`.
- node-db serves Redis on `6379`.
- Caddy has a `books.caddy` site.
- Cloudflare Tunnel is active.
- the app is reachable through the new books hostname.

## Phase 9 - Clean Up Old Ship Runtime

Only do this after `books` passes acceptance.

Remove old Caddy site:

```bash
ansible load_balancer -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -m ansible.builtin.file \
  -a "path=/etc/caddy/sites/ship.caddy state=absent" \
  --become

ansible load_balancer -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -a "systemctl reload caddy" \
  --become
```

Remove old app marker:

```bash
ansible all -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -m ansible.builtin.file \
  -a "path=/etc/localcluster/apps/ship.env state=absent" \
  --become
```

Remove old firewall service and script:

```bash
ansible all -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -m ansible.builtin.shell \
  -a "systemctl disable --now ship-docker-user-firewall.service || true; rm -f /etc/systemd/system/ship-docker-user-firewall.service /usr/local/sbin/ship-docker-user-firewall; systemctl daemon-reload" \
  --become
```

Remove old runtime directory and old Docker Compose resources:

```bash
ansible app_servers:node_db -i Deployment/LocalCluster/inventory/prod/hosts.yml \
  -m ansible.builtin.shell \
  -a "if [ -d /opt/ship ]; then cd /opt/ship && docker compose down -v --remove-orphans || true; fi; rm -rf /opt/ship" \
  --become
```

Remove old GitHub runner after confirming `node-main-books` is online:

- GitHub UI: Repository -> Settings -> Actions -> Runners.
- Remove `node-main-ship`.
- On node-main, remove `/opt/actions-runner-ship` if it remains.

Keep or remove old Cloudflare hostname deliberately:

- Keep `shipinspection.jacobgrum.com` temporarily if you want a transition period.
- Remove it from the Cloudflare tunnel when you no longer want it serving this app.
- If it remains while Caddy no longer has `ship.caddy`, it should no longer route to the app.

## Phase 10 - Clean Up Repository References

Active deployment config should no longer contain `ship` or `shipinspection` except in historical docs or this migration plan.

Search:

```bash
rg -n -i "ship|shipinspection|ship-prod|ship_deploy|localcluster-ship|node-main-ship|/opt/ship" .
```

Recommended cleanup:

- Update `BigScoresPlan.md` production URLs if it is still an active plan.
- Leave historical `docs/plans/archive/**` references alone unless they confuse current instructions.
- Keep `/books/author/ship` compatibility route only if it refers to a seeded author book slug, not deployment naming.
- Consider renaming the seeded showcase book currently using seed key `ship` and title `Ship Inspections` in a separate product-data cleanup if that visible content is also unwanted.

## Done Criteria

- `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` uses `books` naming.
- `Deployment/LocalCluster/inventory/prod/hosts.yml` uses `~/.ssh/books_deploy`.
- GitHub runner `node-main-books` is online.
- CI publishes `ghcr.io/grumlebob/books:<sha>`.
- CD deploys with `run_migrations: true`.
- `acceptance-check.sh` passes.
- `https://books.jacobgrum.com/health/ready` passes.
- Old `ship` containers are stopped and removed.
- Old `/opt/ship` runtime is removed after verification.
- Old `ship` app marker, Caddy site, firewall service, and GitHub runner are removed or explicitly kept with a written reason.
- Remaining `ship` references are either historical documentation or intentional book-content slugs.

## Rollback

Before deleting `/opt/ship`, rollback is simple:

1. Stop the new `/opt/books` stacks.
2. Restore the old `ship` settings in `all.yml`.
3. Regenerate inventory so it uses `~/.ssh/ship_deploy`.
4. Start the old `/opt/ship` stacks or rerun CD from the last known working `ship` commit.
5. Point Cloudflare hostname back as needed.

After deleting `/opt/ship` and its Docker volumes, rollback means redeploying the old app identity fresh. That is acceptable because the old database and Redis state are disposable.
