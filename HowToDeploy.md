# How To Deploy

This guide starts with fresh physical machines and ends with `https://ship.jacobgrum.com` serving the app. Follow it from top to bottom for the first deployment.

## Result

```text
Cloudflare
  -> Cloudflare Tunnel
  -> node-main: cloudflared + Caddy ingress/control
  -> node-app1 / node-app2: app containers
  -> node-db: PostgreSQL + Redis
```

Public hostname:

```text
ship.jacobgrum.com
```

## First Deployment Checklist

Use this checklist while following the guide:

```text
[ ] Local setup files copied: Deployment/machines.yml and Deployment/.deploy.local.env
[ ] Linux Mint installed on all four nodes
[ ] Hostnames set to node-main, node-app1, node-app2, node-db
[ ] SSH enabled on all four nodes
[ ] Username, LAN IP, and MAC discovered for every node
[ ] DHCP reservations created in the router
[ ] Deployment/machines.yml filled with real values
[ ] Deployment/inventory/prod/hosts.yml and bootstrap-hosts.yml generated
[ ] Ansible installed on the control machine
[ ] bash ./Deployment/scripts/status.sh bootstrap passes
[ ] Fresh machines prepared with Ansible
[ ] Deployment/inventory/prod/vault.yml created and filled
[ ] bash ./Deployment/scripts/check-vault.sh passes
[ ] Cloudflare Tunnel token added to vault.yml
[ ] bash ./Deployment/scripts/status.sh deploy passes
[ ] CI has pushed ghcr.io/grumlebob/ship:<git-sha>
[ ] First deployment run
[ ] Public health check passes
```

## Machine Names

Install Linux Mint on four physical machines and use exactly these hostnames:

```text
node-main
node-app1
node-app2
node-db
```

Roles:

- `node-main`: Cloudflare Tunnel, Caddy, GitHub Actions self-hosted runner, and deployment/control responsibilities.
- `node-app1`: app container.
- `node-app2`: app container.
- `node-db`: PostgreSQL and Redis.

`node-db` is the physical machine hostname. `node_db` is the Ansible inventory group and role-variable name for the PostgreSQL/Redis services on that host; Ansible group names use underscores so they remain valid inventory identifiers.

`node-main` is intentionally not an app server in the recommended first deployment. Keeping it focused on ingress and deployment control makes failures easier to reason about: app CPU/memory spikes do not compete with Caddy/cloudflared, and a bad app deployment is less likely to interfere with the node that controls access and deployment.

## Deployment Decisions

- Linux Mint is installed directly on every physical node.
- Cloudflare Tunnel is the only public ingress path.
- Do not configure router port forwarding to the app, PostgreSQL, Redis, Seq, or Redis Insight.
- Cloudflare terminates public HTTPS.
- Caddy listens on `node-main` and load balances to both app nodes over LAN HTTP port `8080`.
- `node-main` is the ingress/control node, not an app backend by default.
- PostgreSQL and Redis run on `node-db`.
- EF Core migrations run once during deployment, before app containers restart.
- App containers do not run startup migrations in production.
- Data Protection keys are shared through Redis so auth and antiforgery state work across app nodes.
- Docker-published ports are restricted with UFW and `DOCKER-USER` firewall rules.
- Durable multi-node upload storage is deferred. Do not rely on local app-node disk for important shared uploads yet.

Optional later change: `node-main` can become a third app backend (`app3`) if `node-app1` and `node-app2` are overloaded and `node-main` has spare capacity. Do not start with that layout; add it only after monitoring shows you need the extra app capacity.

## Files You Will Edit

You will edit these files:

- `Deployment/machines.yml`: put real LAN IPs, MAC addresses, and Linux Mint install usernames here once. This file is ignored by git.
- `Deployment/inventory/prod/group_vars/all.yml`: shared non-secret settings such as domain, ports, deploy root, image name, and pinned `cloudflared_version`.
- `Deployment/inventory/prod/vault.yml`: encrypted Ansible Vault file you create for secrets.
- `Deployment/.deploy.local.env`: optional local defaults for your control machine. This file is ignored by git.

## Useful Files

These useful files mean the following:

- `Deployment/machines.example.yml`: template for `Deployment/machines.yml`.
- `Deployment/.deploy.local.env.example`: template for local operator defaults.
- `Deployment/inventory/prod/hosts.yml`: generated Ansible inventory used by Ansible.
- `Deployment/inventory/prod/bootstrap-hosts.yml`: generated local bootstrap inventory using the Linux Mint install users from `machines.yml`; this file is ignored by git.
- `Deployment/inventory/prod/vault.example.yml`: template showing the required secret names for `vault.yml`.
- `Deployment/inventory/prod/group_vars/app_servers.yml`: app-server role settings.
- `Deployment/inventory/prod/group_vars/node_db.yml`: PostgreSQL/Redis role settings.
- `Deployment/inventory/prod/group_vars/load_balancer.yml`: Caddy/cloudflared role settings.
- `Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml`: prepares fresh Linux Mint nodes.
- `Deployment/ansible/playbooks/site.yml`: deploys DB/Redis, Caddy/cloudflared, migrations, and app servers.
- `Deployment/compose/node-db/docker-compose.yml`: runtime compose file copied to `node-db`.
- `Deployment/compose/app-server/docker-compose.yml`: runtime compose file copied to app nodes.
- `Deployment/compose/load-balancer/docker-compose.yml`: runtime compose file for load-balancer support services.
- `Deployment/ansible/roles/caddy/templates/ship.caddy.j2`: generated Caddy config template using app-node IPs from inventory.
- `Deployment/scripts/install-ansible.sh`: installs the repo-approved Ansible toolchain.
- `Deployment/scripts/discover-machines.sh`: prints the username, hostname, likely LAN IP, and likely MAC address on a fresh node.
- `Deployment/scripts/generate-inventory.sh`: generates `Deployment/inventory/prod/hosts.yml` from `Deployment/machines.yml`.
- `Deployment/scripts/status.sh`: shows what is ready and what is still missing.
- `Deployment/scripts/ping-fresh-machines.sh`: tests Ansible access with the Linux Mint install user before hardening SSH.
- `Deployment/scripts/create-vault.sh`: creates encrypted `Deployment/inventory/prod/vault.yml` from the example shape.
- `Deployment/scripts/check-vault.sh`: decrypts `vault.yml` and verifies required secret keys are present and no template placeholders remain.
- `Deployment/scripts/preflight.sh`: checks prerequisites before bootstrap or deploy.
- `Deployment/scripts/prepare-fresh-linux-machines.sh`: runs the fresh-machine playbook correctly.
- `Deployment/scripts/deploy.sh`: runs the normal deployment playbook.
- `Deployment/scripts/backup-db.sh`: database backup helper copied to `node-db`.
- `Deployment/scripts/restore-db.sh`: database restore helper copied to `node-db`.
- `.github/workflows/ci.yml`: builds/tests, creates migration bundle, builds image, and pushes image to GHCR.
- `.github/workflows/deploy-lan.yml`: deploys from the self-hosted runner.

Reference-only docs:

- `README.md`: project overview.
- `HowToRunLocally.md`: local development.

## What You Must Provide

These values cannot be invented by the repo:

- Real LAN IP address for each node.
- Router DHCP reservation for each node.
- SSH access to the fresh Linux Mint install user on each node.
- A GitHub token that can read the private GHCR image package.
- A Cloudflare Tunnel token for `ship-prod`.
- A password for `Deployment/inventory/prod/vault.yml`.
- A GitHub Actions self-hosted runner registration token.

## Placeholder Values

Commands in this guide use values wrapped in angle brackets, such as `<linux-mint-install-user>`. Replace the whole placeholder, including `<` and `>`, with your real value.

Common placeholders:

- `<repo-root>`: the folder where this repository is checked out. Example: `/home/jacob/BlazorAutoApp`.
- `<node-name>`: one of `node-main`, `node-app1`, `node-app2`, or `node-db`.
- `<linux-mint-install-user>`: the username you created while installing Linux Mint on the node.
- `<node-main-lan-ip>`: the reserved LAN IP for `node-main` from `Deployment/inventory/prod/hosts.yml`.
- `<git-sha>`: the commit SHA that passed CI and was pushed as a GHCR image tag.

To find the Linux Mint install username on a node, open a terminal on that node and run:

```bash
whoami
```

Example: if `whoami` prints `jacob`, then use `jacob` in commands:

```bash
ssh jacob@192.168.1.20 hostname
bash ./Deployment/scripts/prepare-fresh-linux-machines.sh jacob
```

To find the current repository root on a Linux shell:

```bash
pwd
```

## 0. Create Local Setup Files

From the repository root on the control machine:

```bash
cp Deployment/machines.example.yml Deployment/machines.yml
cp Deployment/.deploy.local.env.example Deployment/.deploy.local.env
```

Edit `Deployment/.deploy.local.env` and set your Linux Mint install username:

```env
LINUX_MINT_INSTALL_USER=jacob
SHIP_DEPLOY_KEY="$HOME/.ssh/ship_deploy"
SHIP_DEPLOY_KEY_PUB="$HOME/.ssh/ship_deploy.pub"
```

If every node uses the same Linux Mint install username, this saves you from typing it repeatedly. If you fill `install_user` in `Deployment/machines.yml`, the generated bootstrap inventory also saves the username for the fresh-machine phase.

Check your current setup at any time:

```bash
bash ./Deployment/scripts/status.sh bootstrap
```

## 1. Install Linux Mint

Install Linux Mint directly on every physical machine.

Use the same edition everywhere if possible. Cinnamon is fine for decent laptops; XFCE is better for weaker machines.

During Linux Mint installation you create a normal user account. Write that username down. This guide calls it:

```text
<linux-mint-install-user>
```

Example: if you create a user named `jacob`, then `<linux-mint-install-user>` means `jacob`.

On each node, set the correct hostname:

```bash
sudo hostnamectl set-hostname <node-name>
```

Use the matching value from:

```text
node-main
node-app1
node-app2
node-db
```

Disable sleep/suspend in Linux Mint power settings:

```text
Suspend when inactive: Never
When laptop lid is closed: Do nothing, if the machine will run closed
```

## 2. Enable First SSH Access

On every node, install and start SSH:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
```

Confirm SSH is running:

```bash
systemctl status ssh
```

At this point, Ansible still uses the normal Linux Mint user you created during OS installation. The `deploy` user is created later by automation.

If you are unsure what the Linux Mint install username is, open a terminal on that node and run:

```bash
whoami
```

Example output:

```text
jacob
```

If the output is `jacob`, then every command that says `<linux-mint-install-user>` should use `jacob`.

## 3. Discover LAN IPs And Reserve Them

On each node, run:

```bash
bash ./Deployment/scripts/discover-machines.sh
```

If the repository is not on the node yet, run the underlying commands manually:

```bash
whoami
hostname
ip -brief address
ip route get 1.1.1.1
ip link show
```

Record:

- Username.
- Hostname.
- LAN IP address.
- MAC address.

Open your router admin UI. Create DHCP reservations so each node keeps the same LAN IP.

Reboot each node after adding the DHCP reservations, then rerun:

```bash
ip -brief address
```

Do not continue until each node has the reserved IP.

Enter the discovered values once in:

```text
Deployment/machines.yml
```

Example:

```yaml
nodes:
  node-main:
    ip: REPLACE_WITH_NODE_MAIN_LAN_IP
    mac: REPLACE_WITH_NODE_MAIN_MAC
    install_user: REPLACE_WITH_LINUX_MINT_INSTALL_USER
```

Replace those placeholder values with your real discovered values, for example:

```yaml
nodes:
  node-main:
    ip: 192.168.1.20
    mac: aa:bb:cc:dd:ee:01
    install_user: jacob
```

Then generate the Ansible inventory:

```bash
bash ./Deployment/scripts/generate-inventory.sh
```

This writes:

```text
Deployment/inventory/prod/hosts.yml
Deployment/inventory/prod/bootstrap-hosts.yml
```

`hosts.yml` is the normal deployment inventory. `bootstrap-hosts.yml` is only for preparing fresh machines before the `deploy` user exists.

All generated runtime files use `hosts.yml` through Ansible inventory. Do not copy node IPs into markdown files, compose files, Caddy files, firewall files, or `.env` files.

## 4. Prepare The Control Machine

Run these commands from a Linux shell with the repo checked out. WSL is fine for this control machine role.

From the repository root:

```bash
bash ./Deployment/scripts/install-ansible.sh
ansible --version
ssh-keygen -t ed25519 -f ~/.ssh/ship_deploy -C "ship deploy"
bash ./Deployment/scripts/status.sh bootstrap
bash ./Deployment/scripts/preflight.sh bootstrap
```

The bootstrap preflight verifies:

- Ansible is installed.
- `Deployment/inventory/prod/hosts.yml` parses.
- No inventory placeholder IPs remain.
- `~/.ssh/ship_deploy` and `~/.ssh/ship_deploy.pub` exist.

Test SSH to each node with the normal Linux Mint install user.

Replace `<linux-mint-install-user>` with the username from `whoami`. Replace each `<node-...-lan-ip>` with the reserved IP you put in `Deployment/inventory/prod/hosts.yml`.

```bash
ssh <linux-mint-install-user>@<node-main-lan-ip> hostname
ssh <linux-mint-install-user>@<node-app1-lan-ip> hostname
ssh <linux-mint-install-user>@<node-app2-lan-ip> hostname
ssh <linux-mint-install-user>@<node-db-lan-ip> hostname
```

Example if your Linux Mint username is `jacob` and `node-main` is `192.168.1.20`:

```bash
ssh jacob@192.168.1.20 hostname
```

Verify Ansible can reach every fresh machine with the Linux Mint install user.

If you generated `bootstrap-hosts.yml`, this command can read the per-node install usernames from there:

```bash
bash ./Deployment/scripts/ping-fresh-machines.sh
```

You can still pass the username explicitly. Example if your Linux Mint username is `jacob`:

```bash
bash ./Deployment/scripts/ping-fresh-machines.sh jacob
```

Do not continue until all four nodes return `pong`.

## 5. Prepare Fresh Linux Machines

Use the Linux Mint username you created during OS installation. This is the same value described above as `<linux-mint-install-user>`.

To find it on a node:

```bash
whoami
```

If `whoami` prints `jacob`, run:

```bash
bash ./Deployment/scripts/prepare-fresh-linux-machines.sh jacob
```

If `LINUX_MINT_INSTALL_USER=jacob` is set in `Deployment/.deploy.local.env`, or if `bootstrap-hosts.yml` was generated from `machines.yml`, you can run:

```bash
bash ./Deployment/scripts/prepare-fresh-linux-machines.sh
```

Command shape:

```bash
bash ./Deployment/scripts/prepare-fresh-linux-machines.sh [linux-mint-install-user]
```

This runs `Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml`.

It creates the `deploy` user, installs your deploy SSH public key, configures SSH hardening, installs Docker, configures host firewalling, installs Docker published-port firewalling, creates `/opt/ship`, and verifies Docker Compose on each node.

After this step, deployment uses:

```text
User: deploy
SSH key: ~/.ssh/ship_deploy
Deploy root on nodes: /opt/ship
```

`/opt/ship` is not the git repository. It is the runtime directory on each Linux node where Ansible places generated deployment files for that node:

```text
/opt/ship/
  docker-compose.yml
  .env
  backups/
  migrations/
```

Each node gets only the runtime files for its role. App nodes get the app compose file. `node-db` gets the PostgreSQL/Redis compose file. `node-main` gets Caddy/cloudflared configuration.

Verify the prepared nodes:

```bash
cd <repo-root>/Deployment/ansible
ansible all -i ../inventory/prod/hosts.yml -m ping
ansible all -i ../inventory/prod/hosts.yml -a "docker version"
ansible all -i ../inventory/prod/hosts.yml -a "docker compose version"
```

## 6. Create The Encrypted Vault

Create the encrypted secrets file:

```bash
bash ./Deployment/scripts/create-vault.sh
```

The script opens the encrypted file for editing and validates it after you save. Use exactly this shape:

```yaml
vault_postgres_user: ship
vault_postgres_password: <strong-db-password>
vault_postgres_db: ship
vault_redis_password: <strong-redis-password>
vault_ghcr_username: <github-username>
vault_ghcr_token: <github-token-with-read-packages>
vault_cloudflare_tunnel_token: <cloudflare-tunnel-token>
```

Useful vault commands:

```bash
bash ./Deployment/scripts/check-vault.sh
ansible-vault view Deployment/inventory/prod/vault.yml
ansible-vault edit Deployment/inventory/prod/vault.yml
```

Store the vault password in your password manager. You will also add it as a GitHub repository secret later.

Commit only the encrypted vault file if this repository is the source used by the self-hosted deployment runner:

```bash
bash ./Deployment/scripts/check-vault.sh
git add Deployment/inventory/prod/vault.yml
git commit -m "Add encrypted production Ansible vault"
```

Never commit plaintext secrets.

Run deploy preflight:

```bash
bash ./Deployment/scripts/status.sh deploy
bash ./Deployment/scripts/preflight.sh deploy
```

## 7. Create The Cloudflare Tunnel

In Cloudflare Zero Trust:

```text
Networks -> Tunnels -> Create tunnel
Tunnel type: Cloudflared
Tunnel name: ship-prod
Connector environment: Debian
```

Copy the generated tunnel token into:

```yaml
vault_cloudflare_tunnel_token: <cloudflare-tunnel-token>
```

in `Deployment/inventory/prod/vault.yml`.

Add the public hostname in Cloudflare:

```text
Public hostname: ship.jacobgrum.com
Service type: HTTP
Service URL: 127.0.0.1:80
```

The Ansible role installs the pinned `cloudflared_version` from `Deployment/inventory/prod/group_vars/all.yml` and runs the tunnel on `node-main`.

After deployment, verify on `node-main`:

```bash
systemctl status cloudflared --no-pager
journalctl -u cloudflared --no-pager -n 100
```

## 8. Confirm Shared Deployment Settings

Review:

```text
Deployment/inventory/prod/group_vars/all.yml
```

Current important values:

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

Do not set `cloudflared_version` to `latest`.

Role-specific variables live here:

```text
Deployment/inventory/prod/group_vars/app_servers.yml
Deployment/inventory/prod/group_vars/node_db.yml
Deployment/inventory/prod/group_vars/load_balancer.yml
```

Those files hold role-specific ports, container names, and service paths. You normally should not need to edit them for the first deployment.

## 9. Understand Runtime Services

PostgreSQL and Redis run from:

```text
Deployment/compose/node-db/docker-compose.yml
```

Ansible renders `/opt/ship/.env` on `node-db` with:

```env
POSTGRES_USER=<vault_postgres_user>
POSTGRES_PASSWORD=<vault_postgres_password>
POSTGRES_DB=<vault_postgres_db>
REDIS_PASSWORD=<vault_redis_password>
```

App servers run from:

```text
Deployment/compose/app-server/docker-compose.yml
```

Ansible renders `/opt/ship/.env` on each app node with:

```env
APP_IMAGE=ghcr.io/grumlebob/ship
APP_VERSION=<git-sha>
POSTGRES_HOST=<node-db IP from inventory>
POSTGRES_USER=<vault_postgres_user>
POSTGRES_PASSWORD=<vault_postgres_password>
POSTGRES_DB=<vault_postgres_db>
REDIS_HOST=<node-db IP from inventory>
REDIS_PASSWORD=<vault_redis_password>
```

Caddy is installed on `node-main`. The deployed Caddy site is generated from:

```text
Deployment/ansible/roles/caddy/templates/ship.caddy.j2
```

It uses the real app-node LAN IPs from `Deployment/inventory/prod/hosts.yml`, keeps sticky sessions for Blazor Server, and checks `/health/ready`.

Validate Caddy after deployment:

```bash
caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
systemctl status caddy --no-pager
```

## 10. Build And Push The First Image

Push your branch/commit through GitHub so `.github/workflows/ci.yml` runs.

CI does the production build work:

```text
1. Deployment audit.
2. dotnet restore.
3. dotnet build.
4. dotnet test.
5. Build EF migration bundle.
6. Build Docker image.
7. Push ghcr.io/grumlebob/ship:<git-sha> on non-PR runs.
```

Wait for CI to succeed. The commit SHA is the deployment image tag.

Production deploys should use the Git SHA tag, not `latest`.

## 11. Migration Strategy

Do not run EF Core migrations automatically from both app servers.

The production deployment order is:

```text
1. Build and push the app image.
2. Create a database backup.
3. Stop both app containers.
4. Run the EF Core migration bundle once.
5. Start app containers on both app nodes.
6. Verify app-node /health/ready.
7. Verify https://ship.jacobgrum.com/health/ready.
```

The `site.yml` playbook handles that order when `run_migrations=true`.

Manual migration bundle run from `node-db`, if you need to inspect the exact command:

```bash
cd /opt/ship
set -a
. ./.env
set +a
chmod +x ./migrations/ship-migrate
./migrations/ship-migrate --connection "Host=localhost;Port=5432;Database=$POSTGRES_DB;Username=$POSTGRES_USER;Password=$POSTGRES_PASSWORD"
```

## 12. First Manual Deploy

The first deploy can be run manually from the control machine.

Without migrations:

```bash
bash ./Deployment/scripts/deploy.sh <git-sha>
```

With a local migration bundle:

```bash
bash ./Deployment/scripts/deploy.sh <git-sha> --migrate <path-to-ship-migrate>
```

For the normal first real deployment, use migrations. The deployment stops app containers, backs up the database, runs the migration bundle once on `node-db`, then starts the app servers.

If you do not already have the migration bundle locally, use the GitHub Actions deployment flow in the next step. It builds the bundle on the runner.

## Advanced: Direct Ansible Commands

Use this section only when you intentionally need to bypass the wrapper scripts.

Run the full playbook directly:

```bash
cd <repo-root>/Deployment/ansible
bash ../scripts/preflight.sh deploy
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  -e app_version=<git-sha>
```

With migrations:

```bash
cd <repo-root>/Deployment/ansible
bash ../scripts/preflight.sh deploy
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  -e app_version=<git-sha> \
  -e run_migrations=true \
  -e migration_bundle_local_path=<local-path-to-ship-migrate>
```

Run only app servers:

```bash
cd <repo-root>/Deployment/ansible
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  --limit app_servers \
  -e app_version=<git-sha>
```

Run only Caddy/cloudflared:

```bash
cd <repo-root>/Deployment/ansible
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  --limit load_balancer
```

## 13. Install The GitHub Actions Runner

Install the self-hosted runner on `node-main` as the `deploy` user after the fresh-machine preparation has succeeded.

SSH to `node-main`:

```bash
ssh -i ~/.ssh/ship_deploy deploy@<node-main-lan-ip>
```

Install runner prerequisites:

```bash
sudo apt update
sudo apt install -y curl git tar
```

In GitHub:

```text
Repository -> Settings -> Actions -> Runners -> New self-hosted runner -> Linux -> x64
```

Run the GitHub-provided download/config commands on `node-main`, but install it under `/opt/actions-runner`:

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

The workflow targets:

```yaml
runs-on: [self-hosted, linux, x64, homelab]
```

GitHub automatically supplies `self-hosted`, `linux`, and `x64`; you add `homelab`.

Add this GitHub repository secret:

```text
ANSIBLE_VAULT_PASSWORD=<password used for Deployment/inventory/prod/vault.yml>
```

## 14. Deploy From GitHub Actions

Use this workflow:

```text
.github/workflows/deploy-lan.yml
```

In GitHub:

```text
Actions -> Deploy Ship To LAN -> Run workflow
```

Inputs:

```text
image_tag: <git-sha>
run_migrations: true
```

Use the same commit SHA that already passed CI and pushed `ghcr.io/grumlebob/ship:<git-sha>`.

The workflow checks out that commit, builds the migration bundle, installs Ansible, reads the vault password from GitHub Secrets, runs `Deployment/ansible/playbooks/site.yml`, and verifies:

```text
https://ship.jacobgrum.com/health/ready
```

## 15. Verify The Deployment

From the control machine:

```bash
curl -fsS https://ship.jacobgrum.com/health/ready
```

From `node-main`:

```bash
curl -fsS http://localhost/health/ready
```

Check app nodes:

```bash
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "curl -fsS http://localhost:8080/health/ready"
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose ps"
```

Check DB/Redis:

```bash
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose ps"
```

Check Caddy and cloudflared:

```bash
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "systemctl status caddy --no-pager"
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "systemctl status cloudflared --no-pager"
```

## Routine Deployments

For normal future deployments:

```text
1. Push code.
2. Wait for CI to pass.
3. Copy the commit SHA.
4. Run "Deploy Ship To LAN" in GitHub Actions.
5. Use image_tag=<commit-sha>.
6. Use run_migrations=true when the commit includes EF migrations.
7. Confirm /health/ready.
```

## Backup And Restore

Backups are created before deployment migrations.

Manual backup:

```bash
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "/opt/ship/backup-db.sh"
```

Restore is intentionally manual and should be done carefully:

```bash
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "/opt/ship/restore-db.sh /opt/ship/backups/<backup-file>.sql.gz"
```

## Rollback

Before a migration, deploy the previous app image:

```bash
bash ./Deployment/scripts/deploy.sh <previous-git-sha>
```

After a migration, prefer a forward-fix migration. Restore the database backup only when you have decided data loss risk is acceptable and know which backup file to restore.

## Troubleshooting

Run preflight first:

```bash
bash ./Deployment/scripts/preflight.sh deploy
```

Common checks:

```bash
ansible all -i Deployment/inventory/prod/hosts.yml -m ping
ansible all -i Deployment/inventory/prod/hosts.yml -a "docker compose version"
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose logs --tail=100"
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose logs --tail=100"
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "journalctl -u caddy --no-pager -n 100"
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "journalctl -u cloudflared --no-pager -n 100"
```

Important rule: change machine IPs in `Deployment/machines.yml`, regenerate `Deployment/inventory/prod/hosts.yml`, change secrets in `Deployment/inventory/prod/vault.yml`, and change shared non-secret deployment settings in `Deployment/inventory/prod/group_vars/all.yml`.

## Security Checklist

- Cloudflare Tunnel is the only public ingress path.
- Do not configure router port forwarding to app, database, Redis, Seq, or Redis Insight.
- Docker-published ports are restricted with generated `DOCKER-USER` rules.
- SSH uses keys after the fresh-machine playbook succeeds.
- Password SSH login is disabled after SSH hardening.
- Protect `~/.ssh/ship_deploy`; it can administer the deployment.
- GHCR images remain private.
- GHCR deploy token is read-only.
- Secrets live in Ansible Vault or GitHub Secrets, never plaintext repo files.
- Do not run untrusted pull request code on the self-hosted runner.

## Deferred Work

- Durable file upload storage across both app nodes.
- MinIO or another S3-compatible object store.
- Monitoring and alerting.
- Blue/green or canary deployments.
- Tailscale or WireGuard for private remote administration.
