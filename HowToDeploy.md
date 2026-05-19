# How To Deploy

This guide starts with fresh physical machines and ends with the hostname from `public_hostname` serving the app. The default example is `https://ship.jacobgrum.com`. Follow it from top to bottom for the first deployment.

## Result

```text
Cloudflare
  -> Cloudflare Tunnel
  -> node-main: cloudflared + Caddy ingress/control
  -> node-app1 / node-app2: app containers
  -> node-db: PostgreSQL + Redis
```

Default public hostname:

```text
ship.jacobgrum.com
```

## First Deployment Checklist

Use this checklist while following the guide:

```text
[ ] Linux Mint installed on all four nodes
[ ] Hostnames set to node-main, node-app1, node-app2, node-db
[ ] Control machine has the repo checked out
[ ] Shared deployment settings reviewed in Deployment/inventory/prod/group_vars/all.yml
[ ] Control machine tools installed and deploy SSH key created
[ ] SSH enabled on all four nodes
[ ] Username, LAN IP, and MAC discovered for every node
[ ] DHCP reservations created in the router
[ ] Local setup files copied: Deployment/machines.yml and Deployment/.deploy.local.env
[ ] Deployment/machines.yml filled with real values
[ ] Deployment/inventory/prod/hosts.yml and bootstrap-hosts.yml generated
[ ] Deployment/inventory/prod/hosts.yml committed
[ ] bash ./Deployment/scripts/status.sh bootstrap passes
[ ] Fresh machines prepared with Ansible
[ ] Cloudflare Tunnel token created and ready for vault.yml
[ ] Deployment/inventory/prod/vault.yml created and filled
[ ] GitHub secret ANSIBLE_VAULT_PASSWORD set
[ ] bash ./Deployment/scripts/check-vault.sh passes
[ ] bash ./Deployment/scripts/status.sh deploy passes
[ ] Self-hosted GitHub Actions runner installed on node-main
[ ] CI has pushed the GitHub-selected ref image to GHCR
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

The current deployment workflow assumes x86_64/amd64 Linux machines. The self-hosted runner target is `linux, x64`, the EF migration bundle is built for `linux-x64`, and the setup automation fails fast on other CPU architectures.

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
- `Deployment/inventory/prod/hosts.yml`: generated Ansible inventory used by Ansible. This file is committed so the self-hosted GitHub runner can deploy from a fresh checkout.
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
- `Deployment/ansible/roles/caddy/templates/app.caddy.j2`: generated Caddy config template using app-node IPs from inventory.
- `Deployment/scripts/bootstrap-node.sh`: optional helper to run on each fresh Linux Mint node for hostname, SSH, sleep, and discovery output.
- `Deployment/scripts/install-ansible.sh`: installs the repo-approved Ansible toolchain.
- `Deployment/scripts/setup-control-machine.sh`: installs Ansible and creates the default deploy SSH key on the control machine.
- `Deployment/scripts/setup-cloudflare-tunnel.sh`: optional Cloudflare API helper that creates or reuses the tunnel, configures the public hostname, updates DNS, and prints the vault token line.
- `Deployment/scripts/setup-secrets.sh`: creates/edits the encrypted Ansible Vault and sets the GitHub repository vault-password secret with `gh`.
- `Deployment/scripts/install-github-runner.sh`: installs and registers the GitHub Actions self-hosted runner on `node-main` using `gh`.
- `Deployment/scripts/discover-machines.sh`: prints the username, hostname, likely LAN IP, and likely MAC address on a fresh node.
- `Deployment/scripts/generate-inventory.sh`: generates `Deployment/inventory/prod/hosts.yml` from `Deployment/machines.yml`.
- `Deployment/scripts/status.sh`: shows what is ready and what is still missing.
- `Deployment/scripts/ping-fresh-machines.sh`: tests Ansible access with the Linux Mint install user before hardening SSH.
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
- A Cloudflare Tunnel token for the tunnel named by `cloudflare_tunnel_name`.
- A password for `Deployment/inventory/prod/vault.yml`.
- GitHub CLI authentication that can set repository secrets and create a self-hosted runner registration token.

## Placeholder Values

Commands in this guide use values wrapped in angle brackets, such as `<linux-mint-install-user>`. Replace the whole placeholder, including `<` and `>`, with your real value.

Example blocks use fake values. They are there to show formatting, quoting, and likely value shape; do not reuse the example passwords, tokens, IPs, or MAC addresses.

Common placeholders:

- `<repo-root>`: the folder where this repository is checked out. Example: `/home/jacob/BlazorAutoApp`.
- `<app-name>`: the value of `app_name` in `Deployment/inventory/prod/group_vars/all.yml`. Example: `ship`.
- `<deploy-root>`: the value of `deploy_root` in `Deployment/inventory/prod/group_vars/all.yml`. Example: `/opt/ship`.
- `<public_hostname>`: the value of `public_hostname` in `Deployment/inventory/prod/group_vars/all.yml`. Example: `ship.jacobgrum.com`.
- `<node-name>`: one of `node-main`, `node-app1`, `node-app2`, or `node-db`.
- `<linux-mint-install-user>`: the username you created while installing Linux Mint on the node.
- `<node-main-lan-ip>`: the reserved LAN IP for `node-main` from `Deployment/inventory/prod/hosts.yml`.
- `<git-sha>`: the commit SHA used only for advanced manual deploy or rollback commands.

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

## 0. Install Linux Mint

Install Linux Mint directly on every physical machine.

Use the same edition everywhere if possible. Cinnamon is fine for decent laptops; XFCE is better for weaker machines.

During Linux Mint installation you create a normal user account. Write that username down. This guide calls it:

```text
<linux-mint-install-user>
```

Example: if you create a user named `jacob`, then `<linux-mint-install-user>` means `jacob`.

The next automated node-bootstrap step sets hostnames, installs SSH, and masks Linux sleep targets. Also disable sleep/suspend in Linux Mint power settings:

```text
Suspend when inactive: Never
When laptop lid is closed: Do nothing, if the machine will run closed
```

## 1. Set Up The Control Machine

Use `node-main` as the control machine unless you intentionally want to run deployment commands from another Linux shell. WSL is also fine for this role.

### Optional: Clone With GitHub CLI Browser Login

If the fresh Linux control machine does not have this repository yet, GitHub CLI gives a browser-login flow similar to Git Credential Manager on Windows.

Install Git and GitHub CLI:

```bash
sudo apt update
sudo apt install -y git gh
```

Log in:

```bash
gh auth login
```

Choose:

```text
GitHub.com
HTTPS
Yes, authenticate Git with your GitHub credentials
Login with a web browser
```

After the browser flow finishes, check the login:

```bash
gh auth status
```

Then clone:

```bash
git clone https://github.com/Grumlebob/BlazorAutoApp.git
cd BlazorAutoApp
```

If `gh` says credentials were saved in plaintext, that means the GitHub token is stored under your Linux user profile, commonly in `~/.config/gh/hosts.yml`. That is acceptable for a private, disk-encrypted machine used only by you. On a shared machine or long-lived server, prefer an SSH key or a repository deploy key with limited access.

### Optional: Install VS Code

Install Visual Studio Code on the control machine if you want a comfortable editor on Linux.

```bash
sudo apt update
sudo apt install -y wget gpg apt-transport-https
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
rm packages.microsoft.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | sudo tee /etc/apt/sources.list.d/vscode.list >/dev/null
sudo apt update
sudo apt install -y code
```

Open this repository from the repo root:

```bash
code .
```

Make VS Code the default editor for Git:

```bash
git config --global core.editor "code --wait"
git config --global -l | grep core.editor
```

Make VS Code the default editor for terminal programs started by your user:

```bash
printf '\nexport EDITOR="code --wait"\nexport VISUAL="code --wait"\n' >> ~/.bashrc
source ~/.bashrc
```

Make VS Code the default app for plain text files in the Linux Mint file manager:

```bash
xdg-mime default code.desktop text/plain
xdg-mime query default text/plain
```

You can also do this from the file manager: right-click a text file, choose `Properties`, open `Open With`, select `Visual Studio Code`, and set it as the default.

## 2. Confirm Shared Deployment Settings

Review:

```text
Deployment/inventory/prod/group_vars/all.yml
```

These are the high-level deployment settings. Change these before generating inventory, creating the deploy key, or preparing machines. `app_name` affects the default SSH key name, and `deploy_root` affects the directories Ansible creates on the nodes.

Shape:

```yaml
app_name: <app-name>
app_image: ghcr.io/<github-owner-or-org>/<image-name>
app_port: 8080
public_hostname: <public-hostname>
deploy_root: /opt/<app-name>
cloudflare_tunnel_name: <cloudflare-tunnel-name>
cloudflared_version: <pinned-cloudflared-version>
caddy_sticky_cookie_name: <cookie-name>
migration_bundle_name: <app-name>-migrate
```

Current default example:

```yaml
app_name: ship
app_image: ghcr.io/grumlebob/ship
app_port: 8080
public_hostname: ship.jacobgrum.com
deploy_root: /opt/ship
cloudflare_tunnel_name: ship-prod
cloudflared_version: 2026.5.0
caddy_sticky_cookie_name: ship_lb
migration_bundle_name: ship-migrate
```

Example for a different app:

```yaml
app_name: potatoes
app_image: ghcr.io/grumlebob/potatoes
app_port: 8080
public_hostname: potatoes.example.com
deploy_root: /opt/potatoes
cloudflare_tunnel_name: potatoes-prod
cloudflared_version: 2026.5.0
caddy_sticky_cookie_name: potatoes_lb
migration_bundle_name: potatoes-migrate
```

Do not set `cloudflared_version` to `latest`.

Role-specific variables live here:

```text
Deployment/inventory/prod/group_vars/app_servers.yml
Deployment/inventory/prod/group_vars/node_db.yml
Deployment/inventory/prod/group_vars/load_balancer.yml
```

Those files hold role-specific ports, container names, and service paths. You normally should not need to edit them for the first deployment.

### Set Up The Control Machine Tools

Run this after reviewing `all.yml` so generated defaults use the right `app_name`:

```bash
bash ./Deployment/scripts/setup-control-machine.sh
ansible --version
ansible-playbook --version
```

This installs the Ansible toolchain automatically, creates the default deploy SSH key if it does not already exist, and does not overwrite an existing key. The default key path is `~/.ssh/<app_name>_deploy`. The generated key has no passphrase so the later self-hosted runner can use it non-interactively; protect the control machine accordingly.

The installer uses `apt` and `pipx`, installs `sshpass` for the first password-based Ansible bootstrap, pins an Ansible version that matches the Python version on Linux Mint, and makes the Ansible commands available in `/usr/local/bin`.

## 3. Bootstrap First SSH On Each Node

On every node, set the hostname, install SSH, disable sleep targets, and print the discovery values.

If the repository is available on the node, run:

```bash
bash ./Deployment/scripts/bootstrap-node.sh <node-name>
```

Example on `node-main`:

```bash
bash ./Deployment/scripts/bootstrap-node.sh node-main
```

If the repository is not available on the node yet, paste this command block on that node instead:

```bash
NODE_NAME=<node-name>
sudo hostnamectl set-hostname "$NODE_NAME"
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
whoami
hostname
ip -brief address
ip route get 1.1.1.1
ip -brief link
```

Use the matching value from:

```text
node-main
node-app1
node-app2
node-db
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

## 4. Discover LAN IPs, Reserve Them, And Create Inventory

If you used `bootstrap-node.sh` or the manual bootstrap command block above, use the values it printed. Otherwise, on each node run:

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

Now create the local deployment setup files from the repository root on the control machine:

```bash
test -f Deployment/machines.yml || cp Deployment/machines.example.yml Deployment/machines.yml
test -f Deployment/.deploy.local.env || cp Deployment/.deploy.local.env.example Deployment/.deploy.local.env
```

These commands do not overwrite existing local files. That matters if you are rerunning the guide later.

Enter the discovered values once in:

```text
Deployment/machines.yml
```

Shape:

```yaml
nodes:
  node-main:
    ip: REPLACE_WITH_NODE_MAIN_LAN_IP
    mac: REPLACE_WITH_NODE_MAIN_MAC
    install_user: REPLACE_WITH_LINUX_MINT_INSTALL_USER

  node-app1:
    ip: REPLACE_WITH_NODE_APP1_LAN_IP
    mac: REPLACE_WITH_NODE_APP1_MAC
    install_user: REPLACE_WITH_LINUX_MINT_INSTALL_USER

  node-app2:
    ip: REPLACE_WITH_NODE_APP2_LAN_IP
    mac: REPLACE_WITH_NODE_APP2_MAC
    install_user: REPLACE_WITH_LINUX_MINT_INSTALL_USER

  node-db:
    ip: REPLACE_WITH_NODE_DB_LAN_IP
    mac: REPLACE_WITH_NODE_DB_MAC
    install_user: REPLACE_WITH_LINUX_MINT_INSTALL_USER
```

Example:

```yaml
nodes:
  node-main:
    ip: 192.168.1.20
    mac: aa:bb:cc:dd:ee:01
    install_user: jacob

  node-app1:
    ip: 192.168.1.21
    mac: aa:bb:cc:dd:ee:02
    install_user: jacob

  node-app2:
    ip: 192.168.1.22
    mac: aa:bb:cc:dd:ee:03
    install_user: jacob

  node-db:
    ip: 192.168.1.23
    mac: aa:bb:cc:dd:ee:04
    install_user: jacob
```

Edit `Deployment/.deploy.local.env` and set your Linux Mint install username.

Shape:

```env
LINUX_MINT_INSTALL_USER=<linux-mint-install-user>
```

Example:

```env
LINUX_MINT_INSTALL_USER=jacob
```

If every node uses the same Linux Mint install username, this saves you from typing it repeatedly. If you fill `install_user` in `Deployment/machines.yml`, the generated bootstrap inventory also saves the username for the fresh-machine phase.

The deploy SSH key path is intentionally not configurable in local env. It is derived from `app_name` as `~/.ssh/<app_name>_deploy`, and the generated Ansible inventory uses the same path.

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

Commit the generated production inventory after it contains real reserved IPs:

```bash
git add Deployment/inventory/prod/hosts.yml
git commit -m "Configure production deployment inventory"
```

`Deployment/machines.yml` and `Deployment/inventory/prod/bootstrap-hosts.yml` stay local and ignored by git. The deployment workflow checks out the repository on `node-main`, so it needs the committed `hosts.yml`.

## 5. Verify Bootstrap Access

Run these commands from the repository root on the control machine:

```bash
ansible --version
bash ./Deployment/scripts/status.sh bootstrap
bash ./Deployment/scripts/preflight.sh bootstrap
```

The bootstrap preflight verifies:

- Ansible is installed.
- `Deployment/inventory/prod/hosts.yml` parses.
- No inventory placeholder IPs remain.
- The deploy SSH private and public keys exist. By default they are `~/.ssh/<app_name>_deploy` and `~/.ssh/<app_name>_deploy.pub`.

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

## 6. Prepare Fresh Linux Machines

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

It creates the `deploy` user, installs your deploy SSH public key on every node, installs the deploy private/public key files for the `deploy` user on `node-main`, trusts the deployment nodes in `/home/deploy/.ssh/known_hosts` on `node-main`, configures SSH hardening, installs Docker, configures host firewalling, installs Docker published-port firewalling, creates the configured `deploy_root`, and verifies Docker Compose on each node.

After this step, deployment uses:

```text
User: deploy
SSH key: ~/.ssh/<app_name>_deploy
Deploy root on nodes: value of `deploy_root` from `Deployment/inventory/prod/group_vars/all.yml`
```

The private key is copied only to `node-main` because that machine later runs the GitHub Actions runner and needs to SSH to the other deployment nodes.

The deploy root is not the git repository. It is the runtime directory on each Linux node where Ansible places generated deployment files for that node. With the default settings it is `/opt/ship`:

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

## 7. Create The Cloudflare Tunnel

The normal path is the Cloudflare dashboard. Open:

```text
https://one.dash.cloudflare.com/
```

Then create the tunnel in Cloudflare Zero Trust:

```text
Networks -> Tunnels -> Create tunnel
Tunnel type: Cloudflared
Tunnel name: <cloudflare-tunnel-name>
Connector environment: Debian
```

Example:

```text
Networks -> Tunnels -> Create tunnel
Tunnel type: Cloudflared
Tunnel name: ship-prod
Connector environment: Debian
```

Copy the generated tunnel token and keep it ready for the next step. You will paste it into `Deployment/inventory/prod/vault.yml` when `setup-secrets.sh` opens the encrypted vault.

Shape:

```yaml
vault_cloudflare_tunnel_token: <cloudflare-tunnel-token>
```

Example:

```yaml
vault_cloudflare_tunnel_token: "eyJhIjoiexample-only-cloudflare-tunnel-token"
```

Add the public hostname in Cloudflare.

Shape:

```text
Public hostname: <public-hostname>
Service type: HTTP
Service URL: 127.0.0.1:80
```

Example:

```text
Public hostname: ship.jacobgrum.com
Service type: HTTP
Service URL: 127.0.0.1:80
```

The service URL is local to `node-main` because cloudflared connects to Caddy on the same machine. Do not put an app-node LAN IP here.

Cloudflare's dashboard tunnel guide is here:

```text
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/
```

### Optional: Create The Tunnel With The Cloudflare API

Skip this subsection if you created the tunnel in the Cloudflare dashboard.

The optional API helper does the same Cloudflare-side setup: it creates or reuses the tunnel named by `cloudflare_tunnel_name`, configures the public hostname from `public_hostname` to route to `http://127.0.0.1:80`, creates or updates the proxied CNAME record, and prints the `vault_cloudflare_tunnel_token` line for the next step.

Required Cloudflare API token permissions:

```text
Cloudflare Tunnel Write
Zone DNS Edit
```

Set these values in your shell, or put them in `Deployment/.deploy.local.env`:

Shape:

```env
CLOUDFLARE_ACCOUNT_ID=<cloudflare-account-id>
CLOUDFLARE_ZONE_ID=<cloudflare-zone-id>
CLOUDFLARE_API_TOKEN=<cloudflare-api-token>
```

Example:

```env
CLOUDFLARE_ACCOUNT_ID=0123456789abcdef0123456789abcdef
CLOUDFLARE_ZONE_ID=abcdef0123456789abcdef0123456789
CLOUDFLARE_API_TOKEN=cfapi_example_only_000000000000000000000000
```

Run:

```bash
bash ./Deployment/scripts/setup-cloudflare-tunnel.sh
```

Copy only the printed `vault_cloudflare_tunnel_token` line into the encrypted vault in the next step. Do not commit Cloudflare API tokens.

Cloudflare's API references for this helper are:

```text
https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/cloudflared/
https://developers.cloudflare.com/tunnel/advanced/tunnel-tokens/
https://developers.cloudflare.com/api/go/resources/zero_trust/subresources/tunnels/subresources/cloudflared/subresources/configurations/methods/update/
```

The Ansible role installs the pinned `cloudflared_version` from `Deployment/inventory/prod/group_vars/all.yml` and runs the tunnel on `node-main`. If you later change the tunnel token in the vault, the role detects the change and reinstalls the cloudflared service.

After deployment, verify on `node-main`:

```bash
systemctl status cloudflared --no-pager
journalctl -u cloudflared --no-pager -n 100
```

## 8. Create Secrets And The GitHub Vault Secret

Create or edit the encrypted Ansible Vault, validate it, and set the GitHub repository secret used by the deployment workflow:

```bash
bash ./Deployment/scripts/setup-secrets.sh
```

The script asks for the Ansible Vault password once, opens `Deployment/inventory/prod/vault.yml` for editing, validates the encrypted contents, and runs `gh secret set ANSIBLE_VAULT_PASSWORD` when GitHub CLI is authenticated.

Save the Ansible Vault password somewhere durable and private, like 1Password, Bitwarden, KeePass, or iCloud Keychain. You need the same password when running `ansible-vault view` or `ansible-vault edit`, and the GitHub repository secret must contain the same password.

Vault shape:

```yaml
vault_postgres_user: <postgres-user>
vault_postgres_password: <strong-db-password>
vault_postgres_db: <postgres-database>
vault_redis_password: <strong-redis-password>
vault_ghcr_username: <github-username>
vault_ghcr_token: <github-token-with-read-packages>
vault_cloudflare_tunnel_token: <cloudflare-tunnel-token>
```

Vault example:

```yaml
vault_postgres_user: ship
vault_postgres_password: "correct-horse-db-2026-not-real"
vault_postgres_db: ship
vault_redis_password: "correct-horse-redis-2026-not-real"
vault_ghcr_username: grumlebob
vault_ghcr_token: "ghp_ExampleOnlyReadPackagesToken0000000000"
vault_cloudflare_tunnel_token: "eyJhIjoiexample-only-cloudflare-tunnel-token"
```

Quoted and unquoted YAML string values both work. Quotes are useful for passwords or tokens because they avoid surprises with special characters such as `:`, `#`, `{`, or spaces.

GitHub secret shape:

```text
ANSIBLE_VAULT_PASSWORD=<password used for Deployment/inventory/prod/vault.yml>
```

GitHub secret example:

```text
ANSIBLE_VAULT_PASSWORD=correct-horse-vault-2026-not-real
```

In the GitHub UI, the secret name is `ANSIBLE_VAULT_PASSWORD` and the secret value is the password text only. Do not add surrounding quotes unless quotes are literally part of your vault password.

Useful vault commands:

```bash
bash ./Deployment/scripts/check-vault.sh
ansible-vault view Deployment/inventory/prod/vault.yml
ansible-vault edit Deployment/inventory/prod/vault.yml
```

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

## 9. Understand Runtime Services

PostgreSQL and Redis run from:

```text
Deployment/compose/node-db/docker-compose.yml
```

Ansible renders `<deploy-root>/.env` on `node-db` with:

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

Ansible renders `<deploy-root>/.env` on each app node with:

```env
APP_IMAGE=ghcr.io/grumlebob/ship
APP_VERSION=<selected commit SHA>
POSTGRES_HOST=<node-db IP from inventory>
POSTGRES_USER=<vault_postgres_user>
POSTGRES_PASSWORD=<vault_postgres_password>
POSTGRES_DB=<vault_postgres_db>
REDIS_HOST=<node-db IP from inventory>
REDIS_PASSWORD=<vault_redis_password>
```

Caddy is installed on `node-main`. The deployed Caddy site is generated from:

```text
Deployment/ansible/roles/caddy/templates/app.caddy.j2
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

The normal `CI` workflow should not require you to have completed this deployment guide. It uses committed defaults from `Deployment/inventory/prod/group_vars/all.yml`, builds/tests the app, builds the migration bundle, and builds/pushes the Docker image.

Do not expect `Deploy App To LAN` to pass until you have completed the runner, inventory, vault, and GitHub secret setup below. That workflow reaches into your LAN and deliberately depends on the real deployment environment.

CI does the production build work:

```text
1. Deployment audit.
2. dotnet restore.
3. dotnet build.
4. dotnet test.
5. Build EF migration bundle.
6. Build Docker image.
7. Push `<app_image>:${{ github.sha }}` on non-PR runs.
```

Wait for CI to succeed before deploying. The deployment workflow uses the selected GitHub ref's commit SHA automatically; you do not copy it by hand.

Production deploys use the Git SHA tag. CI intentionally does not push or deploy a mutable `latest` tag.

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
7. Verify `https://<public_hostname>/health/ready`.
```

The `site.yml` playbook handles that order when `run_migrations=true`.

Manual migration bundle run from `node-db`, if you need to inspect the exact command:

```bash
cd <deploy-root>
set -a
. ./.env
set +a
chmod +x ./migrations/<migration_bundle_name>
./migrations/<migration_bundle_name> --connection "Host=localhost;Port=5432;Database=$POSTGRES_DB;Username=$POSTGRES_USER;Password=$POSTGRES_PASSWORD"
```

## 12. Install The GitHub Actions Runner

Install the self-hosted runner on `node-main` as the `deploy` user after the fresh-machine preparation has succeeded. Run this from the repository root on the control machine:

```bash
bash ./Deployment/scripts/install-github-runner.sh
```

The script uses GitHub CLI to create a short-lived runner registration token, SSHes to `node-main` as `deploy`, downloads the current GitHub Actions runner, configures it under `/opt/actions-runner`, installs the systemd service, and starts it.

The workflow targets:

```yaml
runs-on: [self-hosted, linux, x64, homelab]
```

GitHub automatically supplies `self-hosted`, `linux`, and `x64`; you add `homelab`.

## 13. First Deploy From GitHub Actions

Use this workflow:

```text
.github/workflows/deploy-lan.yml
```

In GitHub:

```text
Actions -> Deploy App To LAN -> Run workflow
```

Inputs shape:

```text
run_migrations: true
```

Inputs example:

```text
run_migrations: true
```

GitHub shows a branch/tag selector in the Run workflow dialog. Leave it on `main` for the normal path. The workflow uses that selected ref's commit SHA automatically, checks that `<app_image>:<selected-commit-sha>` exists, builds the migration bundle from the same checkout, and deploys that image.

The workflow installs Ansible, reads the vault password from GitHub Secrets, runs `Deployment/ansible/playbooks/site.yml`, and verifies:

```text
https://<public_hostname>/health/ready
```

## 14. Verify The Deployment

From the control machine:

```bash
curl -fsS https://<public_hostname>/health/ready
```

From `node-main`:

```bash
curl -fsS http://localhost/health/ready
```

Check app nodes:

```bash
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "curl -fsS http://localhost:8080/health/ready"
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "cd <deploy-root> && docker compose ps"
```

Check DB/Redis:

```bash
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "cd <deploy-root> && docker compose ps"
```

Check Caddy and cloudflared:

```bash
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "systemctl status caddy --no-pager"
ansible load_balancer -i Deployment/inventory/prod/hosts.yml -a "systemctl status cloudflared --no-pager"
```

## Advanced: Manual Deploy Commands

Use this section only when you intentionally need to bypass GitHub Actions.

Wrapper script without migrations:

```bash
bash ./Deployment/scripts/deploy.sh <git-sha>
```

Wrapper script with a local migration bundle:

```bash
bash ./Deployment/scripts/deploy.sh <git-sha> --migrate <path-to-migration-bundle>
```

Raw Ansible with migrations:

```bash
cd <repo-root>/Deployment/ansible
bash ../scripts/preflight.sh deploy
ansible-playbook -i ../inventory/prod/hosts.yml playbooks/site.yml \
  --ask-vault-pass \
  -e app_version=<git-sha> \
  -e run_migrations=true \
  -e migration_bundle_local_path=<local-path-to-migration-bundle>
```

## Routine Deployments

For normal future deployments:

```text
1. Push code.
2. Wait for CI to pass.
3. Run "Deploy App To LAN" in GitHub Actions.
4. Leave the workflow ref selector on main unless you intentionally deploy another branch or tag.
5. Use run_migrations=true when the commit includes EF migrations.
6. Confirm /health/ready.
```

## Backup And Restore

Backups are created before deployment migrations.

Manual backup:

```bash
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "<deploy-root>/backup-db.sh"
```

Restore is intentionally manual and should be done carefully:

```bash
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "<deploy-root>/restore-db.sh <deploy-root>/backups/<backup-file>.sql.gz"
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
ansible app_servers -i Deployment/inventory/prod/hosts.yml -a "cd <deploy-root> && docker compose logs --tail=100"
ansible node_db -i Deployment/inventory/prod/hosts.yml -a "cd <deploy-root> && docker compose logs --tail=100"
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
- Protect `~/.ssh/<app_name>_deploy`; it can administer the deployment.
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
