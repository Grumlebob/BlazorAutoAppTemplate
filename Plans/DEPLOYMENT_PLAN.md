# Local Cluster Deployment Plan

## Goal

Run the Blazor Auto app on a small local cluster:

```text
Cloudflare
  -> Cloudflare Tunnel
  -> node-main: cloudflared + Caddy
  -> node-app-01 / node-app-02: ASP.NET Core app containers
  -> node-db-redis: PostgreSQL + Redis
```

No public router port forwarding is required. Cloudflare Tunnel is the only public ingress path.

## Decisions

| Area | Decision |
|---|---|
| Node OS | Install Linux Mint directly on every physical node. |
| Public ingress | Cloudflare Tunnel runs on `node-main`. |
| Internal load balancer | Caddy runs on `node-main` and routes to the app nodes. |
| App protocol | App containers listen on plain HTTP `8080` on the LAN. |
| Public TLS | Cloudflare terminates public HTTPS. |
| Blazor Auto / Server | Caddy must support WebSockets and sticky sessions. |
| Database/cache | PostgreSQL and Redis run on `node-db-redis`. |
| Durable uploads | Deferred. Do not rely on local app-node disk for important multi-node file storage yet. |
| Images | GHCR images stay private. Nodes use read-only deploy credentials. |
| Migrations | Run EF Core migrations once during deployment, before app restart. |
| Data Protection | Persist keys in Redis when Redis is configured, so auth/antiforgery state works across app nodes. |
| Docker firewalling | Use UFW for host rules and `DOCKER-USER` iptables rules for Docker-published ports. |
| Downtime | Short planned downtime is acceptable. |

## Target Node Names

These hostnames are fixed:

```text
node-main
node-app-01
node-app-02
node-db-redis
```

Do not invent IP addresses in the plan. Discover the real LAN IPs after Linux is installed, reserve them in the router, then put the real values once into `Deployment/inventory/prod/hosts.yml`.

## Repository Layout

The repository contains this deployment folder:

```text
Deployment/
  inventory/
    prod/
      hosts.yml
      vault.example.yml
      vault.yml
      group_vars/
        all.yml
        db_redis.yml
        load_balancer.yml
        app_servers.yml
      host_vars/
        node-db-redis.yml
        node-main.yml
        node-app-01.yml
        node-app-02.yml

  ansible/
    playbooks/
      site.yml
      PrepareFreshLinuxMachine.yml
      db-redis.yml
      load-balancer.yml
      app-server.yml
      migrate.yml
    roles/
      mint_base/
      ssh_hardening/
      firewall/
      docker/
      postgres/
      redis/
      cloudflared/
      caddy/
      app/
    ansible.cfg

  compose/
    db-redis/
      docker-compose.yml
    load-balancer/
      docker-compose.yml
    app-server/
      docker-compose.yml

  caddy/
    Caddyfile
    sites/
      ship.caddy

  scripts/
    install-ansible.sh
    preflight.sh
    prepare-fresh-linux-machines.sh
    discover-node.sh
    deploy.sh
    backup-db.sh
    restore-db.sh
    health-check.sh
```

The practical operator guide is `HowToDeploy.md`. The local development guide is `HowToRunLocally.md`.

The deployment files are checked into the repo. The files you still need to fill with machine-specific values are `Deployment/inventory/prod/hosts.yml` and the encrypted `Deployment/inventory/prod/vault.yml`. Do not maintain node IP addresses in markdown files; `hosts.yml` is the single source of truth.

## Manual Steps That Remain

These steps cannot be fully automated from the repository because they require physical access, router access, or third-party one-time tokens:

- Install Linux Mint on each physical laptop.
- Enable SSH once on each fresh machine so Ansible can connect.
- Discover LAN IP/MAC addresses and create DHCP reservations in the router.
- Create the Cloudflare Tunnel/public hostname and copy the generated tunnel token into Ansible Vault.
- Create the GitHub self-hosted runner registration token in GitHub.
- Fill `Deployment/inventory/prod/hosts.yml` and encrypted `Deployment/inventory/prod/vault.yml`.

Everything after those handoff points should be run through scripts, Ansible, or GitHub Actions.

## Phase 1: Install Linux Mint On The Nodes

Install Linux Mint on every physical node.

Use the same edition everywhere if possible. Cinnamon is fine for laptops with enough RAM; XFCE is better for older machines.

Also disable suspend from the desktop power settings:

```text
Power Management:
  Suspend when inactive: Never
  When laptop lid is closed: Do nothing, if the machine will run closed
```

On every node, set the hostname:

```bash
sudo hostnamectl set-hostname node-main
```

Use the correct hostname for each machine:

```text
node-main
node-app-01
node-app-02
node-db-redis
```

Install SSH server on every node:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
```

This is the manual handoff point. Use the normal Linux Mint user created during OS installation for the first Ansible run. Do not manually create the `deploy` user; `PrepareFreshLinuxMachine.yml` creates it, installs its SSH key, and then hardens SSH.

## Phase 2: Discover Real LAN Addresses

Run this on each node:

```bash
hostname
ip -brief address
ip route get 1.1.1.1
```

Record the active LAN interface, IP address, and MAC address temporarily while discovering the machines.

To find the MAC address for the active interface:

```bash
ip link show
```

In the router, create DHCP reservations for each node using the real MAC addresses. After reservations are saved, reboot each node and confirm that each node receives the reserved IP.

Do not continue until you have the real values needed for `Deployment/inventory/prod/hosts.yml`:

```text
Node          Hostname       LAN IP          MAC address       Role
node-main     node-main      discovered      discovered        tunnel + caddy
node-app-01   node-app-01    discovered      discovered        app server
node-app-02   node-app-02    discovered      discovered        app server
node-db-redis node-db-redis  discovered      discovered        postgres + redis
```

## Phase 3: Fill Ansible Inventory

This inventory file exists and is the only source of truth for node IP addresses:

```text
Deployment/inventory/prod/hosts.yml
```

Replace the `REPLACE_WITH_...` values with real LAN IPs:

```yaml
all:
  vars:
    ansible_user: deploy
    ansible_ssh_private_key_file: ~/.ssh/ship_deploy

  children:
    load_balancer:
      hosts:
        node-main:
          ansible_host: <node-main-lan-ip>

    app_servers:
      hosts:
        node-app-01:
          ansible_host: <node-app-01-lan-ip>
        node-app-02:
          ansible_host: <node-app-02-lan-ip>

    db_redis:
      hosts:
        node-db-redis:
          ansible_host: <node-db-redis-lan-ip>
```

All later generated files use these values through Ansible `hostvars`. Do not copy node IPs into compose files, Caddy files, firewall files, or `.env` files manually.

## Phase 4: Configure SSH From The Control Machine

Use the machine that will run Ansible. This can be your dev machine or `node-main`.

Recommended: use `node-main` as the control machine once Linux Mint is installed, because it is always inside the LAN.

Install Ansible on the control machine using the repo installer:

```bash
cd <repo-root>
bash ./Deployment/scripts/install-ansible.sh
ansible --version
```

The installer uses `pipx` and pins a compatible `ansible-core` version based on the control machine Python version. Override with `ANSIBLE_CORE_VERSION=<version>` only when intentionally upgrading Ansible.

Create a deploy key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/ship_deploy -C "ship deploy"
```

Run the bootstrap preflight from the repo root:

```bash
cd <repo-root>
bash ./Deployment/scripts/preflight.sh bootstrap
```

This checks Ansible, the inventory, and the deploy SSH key before the first node-preparation playbook runs.

Test SSH to each node with the normal Linux Mint install user:

```bash
ssh <linux-mint-install-user>@<node-main-lan-ip> hostname
ssh <linux-mint-install-user>@<node-app-01-lan-ip> hostname
ssh <linux-mint-install-user>@<node-app-02-lan-ip> hostname
ssh <linux-mint-install-user>@<node-db-redis-lan-ip> hostname
```

Keep the current SSH session open while testing a new SSH session, so you do not lock yourself out later when SSH hardening is applied.

Verify Ansible can reach every fresh machine with the Linux Mint install user:

```bash
cd <repo-root>/Deployment/ansible
ansible all -i ../inventory/prod/hosts.yml -u <linux-mint-install-user> --ask-pass --ask-become-pass -m ping
```

Do not continue until all four nodes return `pong`.

## Phase 5: Run PrepareFreshLinuxMachine.yml

`Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml` is the first Infrastructure as Code entrypoint after a fresh Linux Mint install.

It connects with the normal Linux Mint install user, upgrades packages, reboots if the OS requires it, creates the `deploy` user, grants it passwordless sudo for Ansible automation, installs `~/.ssh/ship_deploy.pub` into `/home/deploy/.ssh/authorized_keys`, disables password SSH login, installs Docker, and applies the firewall baseline.

It prepares every node by applying these roles:

```text
mint_base
ssh_hardening
docker
firewall
```

Run it from the control machine:

```bash
cd <repo-root>
bash ./Deployment/scripts/prepare-fresh-linux-machines.sh <linux-mint-install-user>
```

If the deploy public key is not at `~/.ssh/ship_deploy.pub`, pass it explicitly:

```bash
bash ./Deployment/scripts/prepare-fresh-linux-machines.sh <linux-mint-install-user> <path-to-ship_deploy.pub>
```

The script runs the playbook and then verifies SSH and Docker:

```bash
cd <repo-root>/Deployment/ansible
ansible all -i ../inventory/prod/hosts.yml -m ping
ansible all -i ../inventory/prod/hosts.yml -a "docker version"
ansible all -i ../inventory/prod/hosts.yml -a "docker compose version"
```

## Phase 6: Create Shared Variables

This variable file exists:

```text
Deployment/inventory/prod/group_vars/all.yml
```

Use real values:

```yaml
app_name: ship
app_image: ghcr.io/grumlebob/ship
app_port: 8080
public_hostname: ship.jacobgrum.com
deploy_root: /opt/ship
cloudflare_tunnel_name: ship-prod
cloudflared_version: 2026.5.0
caddy_sticky_cookie_name: ship_lb
```

`deploy_root` is the directory on each Linux node where Ansible places the runtime files for this deployment. It is not the git repository. `cloudflared_version` must be an explicit release number, not `latest`, so node rebuilds are reproducible. `deploy_root` contains the files Docker Compose needs on that node, such as:

```text
/opt/ship/
  docker-compose.yml
  .env
  backups/
  migrations/
```

Each node gets only the runtime files for its role. For example, app nodes get the app compose file, while `node-db-redis` gets the database/Redis compose file. Keeping this under `/opt/ship` follows the normal Linux convention that optional, locally managed service software lives under `/opt`.

These role variable files exist:

```text
Deployment/inventory/prod/group_vars/app_servers.yml
Deployment/inventory/prod/group_vars/db_redis.yml
Deployment/inventory/prod/group_vars/load_balancer.yml
```

These files should hold role-specific ports, container names, and service paths.

Create the encrypted secrets file from the provided example:

```bash
ansible-vault create Deployment/inventory/prod/vault.yml
```

Minimum required secrets:

```yaml
vault_postgres_user: ship
vault_postgres_password: <strong-db-password>
vault_postgres_db: ship
vault_redis_password: <strong-redis-password>
vault_ghcr_username: <github-username>
vault_ghcr_token: <github-token-with-read-packages>
vault_cloudflare_tunnel_token: <cloudflare-tunnel-token>
```

Every playbook that needs secrets must include:

```yaml
vars_files:
  - ../../inventory/prod/vault.yml
```

Verify the vault can be read:

```bash
ansible-vault view Deployment/inventory/prod/vault.yml
```

Commit the encrypted vault file to the repository so the self-hosted deploy workflow can read it after checkout:

```bash
git add Deployment/inventory/prod/vault.yml
git commit -m "Add encrypted production Ansible vault"
```

Only commit the Ansible Vault encrypted file. Do not commit plaintext secrets.

Run the deploy preflight from the repo root:

```bash
cd <repo-root>
bash ./Deployment/scripts/preflight.sh deploy
```

This verifies the same repo-side prerequisites as the bootstrap check and also confirms that `Deployment/inventory/prod/vault.yml` exists.

## Phase 7: Configure Cloudflare Tunnel

Cloudflare Tunnel is the public ingress. Assume it has not been created yet.

Create the tunnel in the Cloudflare dashboard:

```text
1. Open Cloudflare Zero Trust.
2. Go to Networks -> Tunnels.
3. Create a tunnel.
4. Select Cloudflared.
5. Name it ship-prod.
6. Choose Debian as the connector environment.
7. Copy the generated tunnel token.
8. Store the token in vault_cloudflare_tunnel_token.
```

Add the public hostname in Cloudflare:

```text
Public hostname: ship.jacobgrum.com
Service type: HTTP
Service URL: 127.0.0.1:80
```

Record the real Cloudflare settings in your password manager or operations notes, using this exact shape:

```text
Tunnel name: ship-prod
Public hostname: ship.jacobgrum.com
Service: http://127.0.0.1:80
Connector node: node-main
Token location: Ansible Vault key vault_cloudflare_tunnel_token
```

The Ansible `cloudflared` role installs the pinned `cloudflared_version`, registers the service with `vault_cloudflare_tunnel_token`, verifies the installed version, and starts it on `node-main`.

Verification from `node-main`:

```bash
systemctl status cloudflared
journalctl -u cloudflared --no-pager -n 100
```

Verification from outside the LAN:

```bash
curl https://ship.jacobgrum.com/health/ready
```

This will only work after Caddy and the app are also deployed.

## Phase 8: Configure Caddy

These Caddy files exist:

```text
Deployment/caddy/Caddyfile
Deployment/caddy/sites/ship.caddy
```

Caddy receives traffic from `cloudflared` and load balances to the app nodes.

The Ansible `caddy` role installs Caddy, renders `/etc/caddy/sites/ship.caddy`, and starts the service on `node-main`.

`Deployment/caddy/sites/ship.caddy` is a static reference file and does not contain node IPs. The deployed `/etc/caddy/sites/ship.caddy` is generated from Ansible inventory by `Deployment/ansible/roles/caddy/templates/ship.caddy.j2`, so it uses the real app-node LAN IPs from `hosts.yml`:

```caddyfile
127.0.0.1:80 {
  reverse_proxy {{ node-app-01 from inventory }}:8080 {{ node-app-02 from inventory }}:8080 {
    lb_policy cookie ship_lb
    health_uri /health/ready
    header_up X-Forwarded-Proto https
    header_up X-Forwarded-Host {host}
  }
}
```

Validate on `node-main`:

```bash
caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
systemctl status caddy
```

## Phase 9: Configure Docker Runtime

The `docker` role in `PrepareFreshLinuxMachine.yml` must install Docker Engine and Docker Compose plugin on every node.

Role implementation should follow this Linux Mint command sequence:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "Using Ubuntu base codename: $UBUNTU_CODENAME"
test -n "$UBUNTU_CODENAME"
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $UBUNTU_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

The role must also add `deploy` to the `docker` group:

```bash
sudo usermod -aG docker deploy
```

Log out and back in as `deploy` after the role adds it to the `docker` group.

For the same shell session, this can be tested with:

```bash
newgrp docker
```

Verify on every node:

```bash
docker version
docker compose version
docker run --rm hello-world
```

Log in to GHCR on nodes that pull private images:

```bash
echo "<ghcr-read-token>" | docker login ghcr.io -u "<github-username>" --password-stdin
```

In automation, the GHCR username and read token must come from Ansible Vault.

## Phase 10: Configure DB And Redis

This compose file exists:

```text
Deployment/compose/db-redis/docker-compose.yml
```

This compose file runs PostgreSQL and Redis on `node-db-redis`.

Template:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 10
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}"]
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a ${REDIS_PASSWORD} ping | grep PONG"]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
```

Ansible must render `/opt/ship/.env` on `node-db-redis`:

```env
POSTGRES_USER=<vault_postgres_user>
POSTGRES_PASSWORD=<vault_postgres_password>
POSTGRES_DB=<vault_postgres_db>
REDIS_PASSWORD=<vault_redis_password>
```

Requirements:

- PostgreSQL data is stored in a named Docker volume or `/opt/ship/postgres`.
- Redis is private to the LAN.
- Database credentials come from Ansible Vault.
- PostgreSQL and Redis ports are not exposed to the internet.

The `firewall` role applies these UFW rules on `node-db-redis` using IPs from `hosts.yml`:

```bash
sudo ufw allow from {{ app server IPs from inventory }} to any port 5432 proto tcp
sudo ufw allow from {{ app server IPs from inventory }} to any port 6379 proto tcp
sudo ufw status
```

Verification from `node-db-redis`:

```bash
cd /opt/ship
docker compose ps
docker compose logs postgres
docker compose logs redis
```

## Phase 11: Configure App Servers

This compose file exists:

```text
Deployment/compose/app-server/docker-compose.yml
```

The app compose file runs only the ASP.NET Core app container.

Template:

```yaml
services:
  web:
    image: ${APP_IMAGE}:${APP_VERSION}
    restart: unless-stopped
    environment:
      ASPNETCORE_ENVIRONMENT: Docker
      ASPNETCORE_URLS: http://+:8080
      Database__RunMigrationsAtStartup: "false"
      ConnectionStrings__DefaultConnection: Host=${POSTGRES_HOST};Port=5432;Database=${POSTGRES_DB};Username=${POSTGRES_USER};Password=${POSTGRES_PASSWORD}
      Redis__Configuration: ${REDIS_HOST}:6379,password=${REDIS_PASSWORD},abortConnect=false
    ports:
      - "8080:8080"
    volumes:
      - app_storage:/app/Storage

volumes:
  app_storage:
```

Ansible must render `/opt/ship/.env` on each app node:

```env
APP_IMAGE=ghcr.io/grumlebob/ship
APP_VERSION=<git-sha>
POSTGRES_HOST={{ node-db-redis IP from inventory }}
POSTGRES_USER=<vault_postgres_user>
POSTGRES_PASSWORD=<vault_postgres_password>
POSTGRES_DB=<vault_postgres_db>
REDIS_HOST={{ node-db-redis IP from inventory }}
REDIS_PASSWORD=<vault_redis_password>
```

Requirements:

- Container listens on HTTP `8080`.
- Environment points to PostgreSQL and Redis on `node-db-redis`.
- No development HTTPS certificate mount.
- No app-server-local durable file storage assumption.

The `firewall` role applies this UFW rule on each app node using the `node-main` IP from `hosts.yml`:

```bash
sudo ufw allow from {{ node-main IP from inventory }} to any port 8080 proto tcp
sudo ufw status
```

Verification from each app node:

```bash
cd /opt/ship
docker compose ps
curl http://localhost:8080/health/ready
```

Verification through Ansible inventory:

```bash
ansible app_servers -i ../inventory/prod/hosts.yml -a "curl -fsS http://localhost:8080/health/ready"
```

## Phase 12: Make Required App Changes

The current app must be adjusted before the two-node deployment is considered production-ready.

Required changes:

- Expose `/health/live` and `/health/ready`; keep `/health` as a readiness alias.
- Do not run EF Core migrations automatically from every app server.
- Respect forwarded headers from Cloudflare Tunnel/Caddy before HTTPS redirection.
- Persist Data Protection keys in Redis for multi-node deployment.

### Health endpoint

The ASP.NET Core app must expose:

```text
/health/live
/health/ready
/health
```

The deployment should use `/health/ready` for Caddy and smoke checks because it verifies dependencies such as PostgreSQL and Redis. `/health/live` should only prove the process is alive.

Implementation shape:

```csharp
builder.Services.AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy(), tags: ["live"])
    .AddCheck<PostgresHealthCheck>("postgres", tags: ["ready"]);

var app = builder.Build();

app.MapHealthChecks("/health/live");
app.MapHealthChecks("/health/ready");
```

### Disable automatic multi-node migrations

The app currently runs `db.Database.Migrate()` at startup. That is unsafe with two app servers.

Replace unconditional startup migration with a config guard:

```csharp
var runMigrationsAtStartup = builder.Configuration.GetValue("Database:RunMigrationsAtStartup", app.Environment.IsDevelopment());
if (runMigrationsAtStartup)
{
    using var scope = app.Services.CreateScope();
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.Migrate();
}
```

In production app containers:

```text
Database__RunMigrationsAtStartup=false
```

Run migrations only from the migration playbook.

### Forwarded headers

Because public HTTPS terminates at Cloudflare and traffic reaches the app through `cloudflared` and Caddy, configure forwarded headers before `UseHttpsRedirection()`:

```csharp
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders =
        ForwardedHeaders.XForwardedFor |
        ForwardedHeaders.XForwardedProto |
        ForwardedHeaders.XForwardedHost;
    options.KnownNetworks.Clear();
    options.KnownProxies.Clear();
});

var app = builder.Build();

app.UseForwardedHeaders();
app.UseHttpsRedirection();
```

Add these usings:

```csharp
using Microsoft.AspNetCore.HttpOverrides;
```

### Data Protection

The app now persists Data Protection keys to Redis when `Redis:Configuration` is set. This is the production path because both app nodes share the same key ring.

If Redis is not configured, the app falls back to filesystem keys under `/app/Storage/DataProtection-Keys`. That fallback is fine for local development, but not for multi-node production.

## Phase 13: Build And Push Image

This single CI workflow exists:

```text
.github/workflows/ci.yml
```

Use .NET `9.0.x`, because `BlazorAutoApp/BlazorAutoApp.csproj` targets `net9.0`.

`ci.yml` now handles restore, build, tests, migration bundle build, Docker image build, artifact upload, and GHCR push. Pull requests run validation without pushing artifacts or images.

Important Docker build command:

```bash
docker build \
  -f BlazorAutoApp/Dockerfile \
  -t ghcr.io/grumlebob/ship:${{ github.sha }} \
  -t ghcr.io/grumlebob/ship:latest \
  .
```

Production deploys should use the Git SHA tag, not `latest`.

Create the migration bundle in CI:

```bash
dotnet tool restore
dotnet ef migrations bundle \
  --project BlazorAutoApp/BlazorAutoApp.csproj \
  --startup-project BlazorAutoApp/BlazorAutoApp.csproj \
  --configuration Release \
  --self-contained \
  --runtime linux-x64 \
  --output artifacts/migrations/ship-migrate
```

The repo includes `.config/dotnet-tools.json` with `dotnet-ef`. To restore it locally:

```bash
dotnet tool restore
```

## Phase 14: Migration Strategy

Do not run EF Core migrations automatically from both app servers.

Backup command on `node-db-redis`:

```bash
cd /opt/ship
./backup-db.sh
```

Restore command on `node-db-redis`:

```bash
cd /opt/ship
./restore-db.sh /opt/ship/backups/<backup-file>.sql.gz
```

Deployment order:

```text
1. Build and push app image.
2. Create database backup.
3. Stop both app containers or put Caddy into maintenance mode.
4. Run EF Core migration bundle once.
5. Start app containers on both app nodes.
6. Verify app-node /health/ready.
7. Verify Caddy /health/ready through the Cloudflare hostname.
```

Manual migration bundle run from `node-db-redis`:

```bash
cd /opt/ship
set -a
. ./.env
set +a
chmod +x ./migrations/ship-migrate
./migrations/ship-migrate --connection "Host=localhost;Port=5432;Database=$POSTGRES_DB;Username=$POSTGRES_USER;Password=$POSTGRES_PASSWORD"
```

Rollback rule:

```text
Before migration: deploy previous app image.
After migration: use a forward-fix migration or restore the tested database backup.
```

## Phase 15: Deploy Manually First

Run the full deployment playbook:

```bash
cd <repo-root>/Deployment/ansible
bash ../scripts/preflight.sh deploy
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  -e app_version=<git-sha>
```

Run the full deployment playbook with a migration bundle:

```bash
cd <repo-root>/Deployment/ansible
bash ../scripts/preflight.sh deploy
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  -e app_version=<git-sha> \
  -e run_migrations=true \
  -e migration_bundle_local_path=<local-path-to-ship-migrate>
```

When `run_migrations=true`, `site.yml` stops app containers, copies the migration bundle to `node-db-redis`, creates a database backup, runs the migration once, then starts the app servers.

Run only app servers:

```bash
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  --limit app_servers \
  -e app_version=<git-sha>
```

Run only Caddy/cloudflared:

```bash
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  --limit load_balancer
```

## Phase 16: Verify The Real Deployment

From `node-main`:

```bash
curl http://localhost/health/ready
```

From the Ansible control machine:

```bash
cd <repo-root>/Deployment/ansible
ansible app_servers -i ../inventory/prod/hosts.yml -a "curl -fsS http://localhost:8080/health/ready"
```

From outside the LAN:

```bash
curl https://ship.jacobgrum.com/health/ready
```

Check services:

```bash
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "systemctl status cloudflared"
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "systemctl status caddy"
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose ps"
ansible db_redis -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose ps"
```

## Phase 17: Add GitHub Actions Deployment

Install a self-hosted GitHub Actions runner on `node-main`.

Run the runner as the `deploy` user after `PrepareFreshLinuxMachine.yml` has succeeded on `node-main`.

Install runner prerequisites:

```bash
sudo apt update
sudo apt install -y curl git tar
```

Create the runner in GitHub:

```text
GitHub repository -> Settings -> Actions -> Runners -> New self-hosted runner -> Linux -> x64
```

Use the generated registration token from GitHub in this command sequence on `node-main`:

```bash
sudo mkdir -p /opt/actions-runner
sudo chown deploy:deploy /opt/actions-runner
cd /opt/actions-runner

curl -o actions-runner-linux-x64.tar.gz -L <github-runner-download-url-from-github>
tar xzf actions-runner-linux-x64.tar.gz

./config.sh \
  --url <github-repository-url-from-github> \
  --token <github-runner-registration-token> \
  --name node-main \
  --labels homelab \
  --unattended

sudo ./svc.sh install deploy
sudo ./svc.sh start
sudo ./svc.sh status
```

The runner labels must include `self-hosted`, `linux`, `x64`, and `homelab`, because `.github/workflows/deploy-lan.yml` targets:

```yaml
runs-on: [self-hosted, linux, x64, homelab]
```

Add this GitHub repository secret:

```text
ANSIBLE_VAULT_PASSWORD=<password used for Deployment/inventory/prod/vault.yml>
```

Before running `deploy-lan.yml`, let `ci.yml` finish for the commit you want to deploy. Use that commit SHA as `image_tag`.

This workflow exists:

```text
.github/workflows/deploy-lan.yml
```

The deploy workflow should:

```text
1. Checkout repository.
2. Install pinned Ansible through `Deployment/scripts/install-ansible.sh`.
3. Load Ansible Vault password from GitHub Secrets.
4. Run migration playbook.
5. Run deployment playbook with app_version=<git-sha>.
6. Verify public /health/ready.
```

Workflow input:

```yaml
workflow_dispatch:
  inputs:
    image_tag:
      description: Immutable Docker image tag to deploy, normally a Git SHA
      required: true
```

## Local Development

This setup still supports local development.

For normal local Docker launch from the repository root:

```bash
docker compose up --build
```

The root `docker-compose.yml` is intentionally local-development oriented:

- It builds from `BlazorAutoApp/Dockerfile`.
- It runs PostgreSQL and Redis locally.
- It sets `Database__RunMigrationsAtStartup=true`, so local Docker applies migrations automatically.
- It keeps the development HTTPS certificate mount.
- It persists local `/app/Storage` to `./data/storage`.

The deployment compose files under `Deployment/compose/` are separate and production-oriented:

- They use a prebuilt GHCR image.
- They disable startup migrations.
- They use Caddy/Cloudflare Tunnel for public ingress.
- They get DB/Redis addresses from Ansible inventory.

## Security Checklist

- Cloudflare Tunnel is the only public ingress path.
- No direct router port forwarding to app, database, Redis, Seq, or RedisInsight.
- Docker-published ports are restricted with `DOCKER-USER` rules generated by the firewall role.
- SSH uses keys only.
- Password SSH login is disabled.
- The `deploy` user has passwordless sudo for automation, so protect `~/.ssh/ship_deploy` and the self-hosted runner.
- GHCR images remain private.
- GHCR deploy token is read-only.
- Secrets live in Ansible Vault or GitHub Secrets, never plaintext repo files.
- The self-hosted runner does not run untrusted pull request code.
- Admin tools are LAN-only or protected behind authentication.

## Deferred Work

- Durable file upload storage across both app nodes.
- MinIO or another S3-compatible object store.
- Monitoring and alerting.
- Blue/green or canary deployments.
- Tailscale/WireGuard for private remote administration.

## References

- Debian releases: https://www.debian.org/releases/
- Linux Mint upgrades/support: https://linuxmint-user-guide.readthedocs.io/en/latest/upgrade.html
- Ansible inventory: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html
- Docker Compose interpolation: https://docs.docker.com/reference/compose-file/interpolation/
- Caddy reverse proxy: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- Cloudflare Tunnel routing: https://developers.cloudflare.com/tunnel/routing/
- GitHub self-hosted runners: https://docs.github.com/actions/hosting-your-own-runners
