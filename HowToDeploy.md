# How To Deploy

This guide is written for a first deployment from fresh physical machines to a working `https://ship.jacobgrum.com` site. You should be able to follow this file without reading another deployment document first.

`Plans/DEPLOYMENT_PLAN.md` still exists as the detailed design and rationale, but this file is the operator guide.

## Result

The final production topology is:

```text
Cloudflare
  -> Cloudflare Tunnel
  -> node-main: cloudflared + Caddy
  -> node-app-01 / node-app-02: app containers
  -> node-db-redis: PostgreSQL + Redis
```

The public hostname is:

```text
ship.jacobgrum.com
```

## Machine Names

Install Linux Mint on four physical machines and use exactly these hostnames:

```text
node-main
node-app-01
node-app-02
node-db-redis
```

Roles:

- `node-main`: Cloudflare Tunnel, Caddy, GitHub Actions self-hosted runner.
- `node-app-01`: app container.
- `node-app-02`: app container.
- `node-db-redis`: PostgreSQL and Redis.

## Files You Will Edit

You will edit these files:

- `Deployment/inventory/prod/hosts.yml`: put real LAN IP addresses here. This is the only IP source of truth.
- `Deployment/inventory/prod/group_vars/all.yml`: shared settings such as domain, ports, deploy root, image name, and pinned `cloudflared_version`.
- `Deployment/inventory/prod/vault.yml`: encrypted Ansible Vault file you create.

## Useful Files

These useful files mean the following:

- `Deployment/inventory/prod/vault.example.yml`: template showing the required secret names for `vault.yml`.
- `Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml`: prepares fresh Linux Mint nodes.
- `Deployment/ansible/playbooks/site.yml`: deploys DB/Redis, Caddy/cloudflared, migrations, and app servers.
- `Deployment/scripts/install-ansible.sh`: installs the repo-approved Ansible toolchain.
- `Deployment/scripts/preflight.sh`: checks prerequisites before bootstrap or deploy.
- `Deployment/scripts/prepare-fresh-linux-machines.sh`: runs the fresh-machine playbook correctly.
- `Deployment/scripts/deploy.sh`: runs the normal deployment playbook.
- `.github/workflows/ci.yml`: builds/tests, creates migration bundle, builds image, and pushes image to GHCR.
- `.github/workflows/deploy-lan.yml`: deploys from the self-hosted runner.

Reference-only docs:

- `README.md`: project overview.
- `HowToRunLocally.md`: local development.
- `Plans/DEPLOYMENT_PLAN.md`: detailed deployment design.

## What You Must Provide

These values cannot be invented by the repo:

- Real LAN IP address for each node.
- Router DHCP reservation for each node.
- SSH access to the fresh Linux Mint install user on each node.
- A GitHub token that can read the private GHCR image package.
- A Cloudflare Tunnel token for `ship-prod`.
- A password for `Deployment/inventory/prod/vault.yml`.
- A GitHub Actions self-hosted runner registration token.

## 1. Install Linux Mint

Install Linux Mint directly on every physical machine.

Use the same edition everywhere if possible. Cinnamon is fine for decent laptops; XFCE is better for weaker machines.

On each node, set the correct hostname:

```bash
sudo hostnamectl set-hostname <node-name>
```

Use the matching value from:

```text
node-main
node-app-01
node-app-02
node-db-redis
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

At this point, Ansible will still use the normal Linux Mint user you created during OS installation. The `deploy` user is created later by automation.

## 3. Discover LAN IPs And Reserve Them

On each node, run:

```bash
hostname
ip -brief address
ip route get 1.1.1.1
ip link show
```

Record:

- Hostname.
- LAN IP address.
- MAC address.

Open your router admin UI. Create DHCP reservations so each node keeps the same LAN IP.

Enter the reserved IPs once in:

```text
Deployment/inventory/prod/hosts.yml
```

Replace every `REPLACE_WITH_...` value:

```yaml
all:
  vars:
    ansible_user: deploy
    ansible_ssh_private_key_file: ~/.ssh/ship_deploy

  children:
    load_balancer:
      hosts:
        node-main:
          ansible_host: REPLACE_WITH_NODE_MAIN_LAN_IP

    app_servers:
      hosts:
        node-app-01:
          ansible_host: REPLACE_WITH_NODE_APP_01_LAN_IP
        node-app-02:
          ansible_host: REPLACE_WITH_NODE_APP_02_LAN_IP

    db_redis:
      hosts:
        node-db-redis:
          ansible_host: REPLACE_WITH_NODE_DB_REDIS_LAN_IP
```

Do not copy these IPs into markdown files or scripts.

## 4. Prepare The Control Machine

Run these commands from a Linux shell with the repo checked out. WSL is fine for this control machine role.

From the repository root:

```bash
bash ./Deployment/scripts/install-ansible.sh
ssh-keygen -t ed25519 -f ~/.ssh/ship_deploy -C "ship deploy"
bash ./Deployment/scripts/preflight.sh bootstrap
```

The bootstrap preflight verifies:

- Ansible is installed.
- `Deployment/inventory/prod/hosts.yml` parses.
- No inventory placeholder IPs remain.
- `~/.ssh/ship_deploy` and `~/.ssh/ship_deploy.pub` exist.

## 5. Prepare Fresh Linux Machines

Use the Linux Mint username you created during OS installation:

```bash
bash ./Deployment/scripts/prepare-fresh-linux-machines.sh <linux-mint-install-user>
```

This runs `Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml`.

It creates the `deploy` user, installs your deploy SSH public key, configures SSH hardening, installs Docker, configures host firewalling, installs Docker published-port firewalling, creates `/opt/ship`, and verifies Docker Compose on each node.

After this step, deployment uses:

```text
User: deploy
SSH key: ~/.ssh/ship_deploy
Deploy root on nodes: /opt/ship
```

## 6. Create The Encrypted Vault

Create the encrypted secrets file:

```bash
ansible-vault create Deployment/inventory/prod/vault.yml
```

Use exactly this shape:

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
ansible-vault view Deployment/inventory/prod/vault.yml
ansible-vault edit Deployment/inventory/prod/vault.yml
```

Store the vault password in your password manager. You will also add it as a GitHub repository secret later.

Run deploy preflight:

```bash
bash ./Deployment/scripts/preflight.sh deploy
```

## 7. Create The Cloudflare Tunnel

Assume the tunnel does not exist yet.

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

## 9. Build And Push The First Image

Push your branch/commit through GitHub so `.github/workflows/ci.yml` runs.

CI does the important production build work:

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

## 10. First Manual Deploy

The first deploy can be run manually from the control machine.

Without migrations:

```bash
bash ./Deployment/scripts/deploy.sh <git-sha>
```

With a local migration bundle:

```bash
bash ./Deployment/scripts/deploy.sh <git-sha> --migrate <path-to-ship-migrate>
```

For the normal first real deployment, use migrations. The deployment stops app containers, backs up the database, runs the migration bundle once on `node-db-redis`, then starts the app servers.

If you do not already have the migration bundle locally, use the GitHub Actions deployment flow in the next step. It builds the bundle on the runner.

## 11. Install The GitHub Actions Runner

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

## 12. Deploy From GitHub Actions

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

## 13. Verify The Deployment

From the control machine:

```bash
curl -fsS https://ship.jacobgrum.com/health/ready
```

Check app nodes:

```bash
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "curl -fsS http://localhost:8080/health/ready"
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose ps"
```

Check DB/Redis:

```bash
ansible db_redis -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose ps"
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
ansible db_redis -i Deployment/inventory/prod/hosts.yml -a "/opt/ship/backup-db.sh"
```

Restore is intentionally manual and should be done carefully:

```bash
ansible db_redis -i Deployment/inventory/prod/hosts.yml -a "/opt/ship/restore-db.sh <backup-file>"
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
ansible db_redis -i Deployment/inventory/prod/hosts.yml -a "cd /opt/ship && docker compose logs --tail=100"
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "journalctl -u caddy --no-pager -n 100"
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "journalctl -u cloudflared --no-pager -n 100"
```

Important rule: change IPs in `Deployment/inventory/prod/hosts.yml`, change secrets in `Deployment/inventory/prod/vault.yml`, and change shared non-secret deployment settings in `Deployment/inventory/prod/group_vars/all.yml`.
