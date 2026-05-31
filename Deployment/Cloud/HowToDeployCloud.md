# How To Deploy Cloud

This is the only cloud deployment plan and runbook. Follow it from top to bottom.

The target site is:

```text
https://bookscloud.jacobgrum.com
```

## Current Status

The Cloud deployment has been brought live at `https://bookscloud.jacobgrum.com`.

This guide remains the source of truth for rebuilding, repairing, or repeating the Cloud deployment. Follow it from top to bottom for a fresh deployment; for an existing deployment, run the doctor script first and continue from the first `ACTION` or `BLOCKER`.

Cloud observability is part of this deployment. Grafana, Prometheus, Alertmanager, Loki, and Tempo run privately on `cloud-main`; Alloy and node-exporter run on every Cloud node; PostgreSQL and Redis exporters run on `cloud-db`.

Do not create Hetzner servers manually. OpenTofu owns them.

No `[ControlPC]` action is needed for Cloud deployment.

## Fixed Decisions

- Architecture: Option A, multi-VPS Docker Compose with Cloudflare Tunnel.
- Infrastructure: OpenTofu manages Hetzner Cloud resources.
- Runtime/deploy: Ansible manages OS configuration, services, Docker Compose, migrations, backups, and checks.
- App build: existing shared CI builds the app image and migration bundle.
- Cloud CD: separate `CD - Cloud` workflow, not a duplicate CI.
- Cloud site: `bookscloud.jacobgrum.com`.
- LocalCluster site remains: `books.jacobgrum.com`.
- App image remains shared: `ghcr.io/grumlebob/books`.
- Migration bundle remains shared: `books-migrate-linux-x64`.
- Cloud server OS: Ubuntu 24.04 LTS for v1.
- Cloud server type: `cx23` for all four servers in v1.
- Hetzner location: `fsn1` for v1.
- Hetzner network zone: `eu-central` for v1.
- Public networking: only `cloud-main` gets public IPv4 and IPv6. App and data nodes stay private-only and use `cloud-main` as a NAT gateway for outbound package, Docker, GHCR, and update traffic.
- Public ingress: Hetzner Cloud Firewalls allow no public HTTP/HTTPS and no public app/data ports. SSH is public only to `cloud-main` from explicit temporary/admin CIDRs.
- Private-network enforcement: host firewall rules are mandatory because Hetzner Cloud Firewalls do not secure private-network traffic.
- CD temporary SSH rule: use a dedicated OpenTofu-created firewall for temporary SSH access and expose its ID as `cloud_temp_ssh_firewall_id`.
- OpenTofu state for first deployment: local state on `[CurrentPC]`, ignored by git, backed up after apply.
- Cloud secrets for v1: GitHub environment secrets. Do not introduce a Cloud Ansible Vault unless the guide is updated to make that the only secret path.

## Architecture

```text
Cloudflare -> cloudflared on cloud-main -> Caddy on cloud-main
                                             |
                                             -> cloud-app1 app container
                                             -> cloud-app2 app container

cloud-app1/cloud-app2 -> cloud-db PostgreSQL container
cloud-app1/cloud-app2 -> cloud-db Redis container

cloud-main Prometheus/Grafana/Alertmanager/Loki/Tempo
cloud-main Prometheus scrapes all Cloud nodes over private IPs
each Cloud node Alloy sends app logs, metrics, and traces to cloud-main
```

Nodes:

```text
cloud-main  - Caddy, Cloudflare Tunnel, SSH bastion, ingress checks, observability backend and Alertmanager
cloud-app1  - app container, observability agent
cloud-app2  - app container, observability agent
cloud-db    - PostgreSQL and Redis containers, database exporters, observability agent
```

Network:

```text
cloud_private_network_cidr: 10.10.0.0/24
cloud_private_gateway_ip: 10.10.0.1
cloud_main_private_ip: 10.10.0.10
cloud_app1_private_ip: 10.10.0.11
cloud_app2_private_ip: 10.10.0.12
cloud_db_private_ip: 10.10.0.13
```

Security posture:

- No public HTTP/HTTPS ports for v1; Cloudflare Tunnel is the public ingress.
- Public IPv4/IPv6 exists only on `cloud-main`; private nodes use `cloud-main` NAT for outbound package and image access.
- Private nodes route outbound traffic to the Hetzner private-network gateway, which has an OpenTofu route to `cloud-main`.
- Hetzner Cloud Firewalls protect public inbound traffic.
- Host firewalls protect private-network traffic.
- SSH to `cloud-main` is public only from an explicit admin CIDR or temporary GitHub runner CIDR.
- SSH to private nodes is not public; Ansible reaches them through `cloud-main`.
- App port `8080` is allowed only from `cloud-main` over the private network by host firewall.
- PostgreSQL and Redis are allowed only from `cloud-app1` and `cloud-app2` over the private network by host firewall.
- PostgreSQL and Redis are never public.
- Grafana, Prometheus, Alertmanager, Loki, Tempo, Alloy, node-exporter, postgres-exporter, and redis-exporter are never public.
- Open the Cloud Grafana dashboard only through `Deployment/Cloud/Scripts/open-observability-tunnel.sh`.
- Cloud deployment secrets are separate from LocalCluster secrets.

## Location Labels

```text
[CurrentPC]       run on this developer machine from the repository root
[GitHub]          do this in GitHub
[Cloudflare]      do this in the Cloudflare dashboard
[Hetzner]         do this in the Hetzner Cloud dashboard
[each cloud node] run separately on cloud-main, cloud-app1, cloud-app2, and cloud-db
[cloud-main]      run on cloud-main only
[cloud-app1]      run on cloud-app1 only
[cloud-app2]      run on cloud-app2 only
[cloud-db]        run on cloud-db only
```

`[ControlPC]` is not used for Cloud. The local cluster has a control machine; the cloud target uses `[CurrentPC]` for OpenTofu bring-up and GitHub-hosted runners for app deployment.

`cloud-main` is a bastion and ingress node, not a control machine. Do not run commands on cloud servers unless a step is explicitly labeled `[cloud-main]`, `[cloud-db]`, `[cloud-app1]`, `[cloud-app2]`, or `[each cloud node]`.

If your editor runs markdown commands from the markdown file folder, run this first:

```bash
cd "$(git rev-parse --show-toplevel)"
```

## LocalCluster Guardrail

Cloud work must not break LocalCluster.

Rules:

- `Deployment/Cloud` must not import from `Deployment/LocalCluster`.
- Shared target-independent helpers belong in `Deployment/Common`.
- Only move a helper to `Deployment/Common` when LocalCluster can keep using it successfully.
- If `Deployment/Common` or LocalCluster deployment code changes, run the LocalCluster validation gate before continuing.

LocalCluster validation gate:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Common/Scripts/validate-common-release.sh
bash ./Deployment/LocalCluster/Scripts/audit-deployment.sh
bash ./Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
git diff --check
```

If a Common refactor needs real deployment verification, stop and run the requested `[ControlPC]` deployment step before continuing.

## 0. Confirm Repo And Shared Release Settings

[CurrentPC]

```bash
cd "$(git rev-parse --show-toplevel)"
pwd
git status --short
test -f Deployment/Cloud/HowToDeployCloud.md
test -f Deployment/Common/release.yml
bash ./Deployment/Common/Scripts/validate-common-release.sh
```

Show the current guide readiness:

```bash
bash ./Deployment/Cloud/Scripts/doctor.sh
```

Review:

```text
Deployment/Common/release.yml
```

Expected values:

```yaml
app_image: ghcr.io/grumlebob/books
migration_bundle_name: books-migrate
migration_runtime: linux-x64
```

Do not duplicate these values in Cloud settings. CI owns the shared build artifacts; Cloud consumes them.

## 1. Install CurrentPC Tools

[CurrentPC]

Use WSL Ubuntu or another Linux shell for the command blocks in this guide.

Required tools:

```text
ansible
ansible-playbook
bash
curl
git
gh
jq
openssl
python3
shellcheck
ssh
ssh-keygen
tofu
yamllint
```

Install and verify the CurrentPC toolchain:

```bash
bash ./Deployment/Cloud/Scripts/setup-currentpc-tools.sh
```

This script is idempotent on apt-based Linux shells such as Ubuntu, Debian, or WSL Ubuntu. It installs:

- base packages from apt.
- GitHub CLI from the official GitHub CLI apt repository.
- OpenTofu from the official OpenTofu installer.
- pinned Ansible from `Deployment/Common/Scripts/install-ansible.sh`.
- validation tools `shellcheck` and `yamllint`.

If you only want to verify without installing, run:

```bash
bash ./Deployment/Cloud/Scripts/check-currentpc-tools.sh
```

Do not rely on tools installed only in Windows PowerShell when following bash command blocks. They must be available in the Linux shell where this guide runs.

## Cost Note

The v1 Cloud deployment deliberately uses four small servers because the goal is to demonstrate a multi-node cloud architecture:

```text
cloud-main
cloud-app1
cloud-app2
cloud-db
```

For Hetzner Germany/Finland, `cx23` is the current cheapest x86_64 shared-resource server type in the checked pricing docs. It matches the current app artifact path:

- Docker image built on the normal GitHub x64 builder path.
- EF migration bundle built for `linux-x64`.
- Ubuntu 24.04 x86_64 server image.

Do not switch to ARM/CAX only to chase a lower sticker price. That would require deliberate multi-arch Docker images, `linux-arm64` migration bundles, and separate validation. It also is not currently cheaper than `cx23` in the referenced Germany/Finland price table.

## Quick Destroy And Recreate

Powering off Hetzner Cloud servers does not stop billing. To stop Cloud costs, destroy the OpenTofu-owned Cloud stack.

[CurrentPC]

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/quick-destroy-cloud.sh
```

If `HCLOUD_TOKEN` is not already set, the script loads repo-root `.env.cloud` when present. It first creates a destroy plan and then asks you to type:

```text
destroy bookscloud
```

For a non-interactive run after reviewing the plan:

```bash
bash ./Deployment/Cloud/Scripts/quick-destroy-cloud.sh --confirm "destroy bookscloud"
```

To recreate the Cloud stack later:

[CurrentPC]

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh
```

The recreate script asks you to type:

```text
recreate bookscloud
```

It then creates the Hetzner resources, renders inventory, refreshes GitHub environment secrets that depend on new server IPs, provisions the nodes, and dispatches `CD - Cloud` with migrations enabled.
Cloud observability data is disposable and is destroyed with the servers unless you export it first.

For a non-interactive run after reviewing the plan:

```bash
bash ./Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh --confirm "recreate bookscloud"
```

Useful safe variants:

```bash
bash ./Deployment/Cloud/Scripts/quick-destroy-cloud.sh --plan-only
bash ./Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh --plan-only
bash ./Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh --skip-cd
```

LocalCluster is unaffected by these scripts.

## 2. Confirm Cloud Settings Examples

[CurrentPC]

Review:

```text
Deployment/Cloud/inventory/prod/group_vars/all.yml
Deployment/Cloud/inventory/prod/group_vars/all.example.yml
Deployment/Cloud/inventory/prod/hosts.example.yml
Deployment/Cloud/infra/opentofu/terraform.tfvars.example
```

Verify those files exist:

```bash
test -f Deployment/Cloud/inventory/prod/group_vars/all.yml
test -f Deployment/Cloud/inventory/prod/group_vars/all.example.yml
test -f Deployment/Cloud/inventory/prod/hosts.example.yml
test -f Deployment/Cloud/infra/opentofu/terraform.tfvars.example
```

Expected Cloud deployment identity:

```yaml
app_name: bookscloud
public_hostname: bookscloud.jacobgrum.com
deploy_root: /opt/bookscloud
cloudflare_tunnel_name: bookscloud-prod
```

`Deployment/Cloud/inventory/prod/group_vars/all.yml` is committed because it contains non-secret Cloud settings.

Validate Cloud settings:

```bash
bash ./Deployment/Cloud/Scripts/validate-cloud-settings.sh
bash ./Deployment/Cloud/Scripts/summary.sh
```

At this point the Cloud inventory has not been rendered yet. The summary should show `inventory not rendered yet [WAIT for Step 8]`; that is expected before OpenTofu creates the servers.

## 3. Confirm Cloud Settings Are Not Secret

[CurrentPC]

Print the committed Cloud settings:

```bash
bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh app_name
bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh public_hostname
bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh deploy_root
bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh cloudflare_tunnel_name
```

Expected output values:

```text
bookscloud
bookscloud.jacobgrum.com
/opt/bookscloud
bookscloud-prod
```

These are not secrets and can stay committed.

## 4. Create The Cloud Deploy SSH Key

[CurrentPC]

Generate a dedicated deploy key pair:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
if [ ! -f ~/.ssh/bookscloud_deploy ]; then
  ssh-keygen -t ed25519 -f ~/.ssh/bookscloud_deploy -C "bookscloud-deploy" -N ""
fi
chmod 600 ~/.ssh/bookscloud_deploy
chmod 644 ~/.ssh/bookscloud_deploy.pub
```

Print the public key:

```bash
cat ~/.ssh/bookscloud_deploy.pub
```

Keep this key pair on `[CurrentPC]`. Do not paste it into GitHub yet.

Do not commit either key.

## 5. Create Hetzner API Token

[Hetzner]

Open the Hetzner Console:

```text
https://console.hetzner.cloud/projects
```

Create a dedicated project for this deployment, or open the project you want to use for `bookscloud`.

Suggested project name:

```text
bookscloud
```

Inside that project:

1. Select `Security` in the left menu.
2. Select `API tokens` in the top menu.
3. Select `Generate API token`.
4. Description:

```text
bookscloud-opentofu-cd
```

5. Permission:

```text
Read & Write
```

Use `Read & Write`, not `Read`. OpenTofu needs to create and update servers, networks, SSH keys, and firewalls. `CD - Cloud` also needs to update the temporary SSH firewall rule.

6. Create the token.
7. Copy the token immediately.

Hetzner shows the token only once. Store it in your password manager before closing the dialog. Do not commit it.

Token use:

- `[CurrentPC]` OpenTofu creates infrastructure.
- `[GitHub]` `CD - Cloud` temporarily updates the dedicated temporary SSH firewall for `cloud-main`.

If the console gives you a direct project URL later, it will look similar to:

```text
https://console.hetzner.cloud/projects/<project-id>/security/tokens
```

[CurrentPC]

Set it for the current shell, or put `HCLOUD_TOKEN="..."` in repo-root `.env.cloud`. Cloud helper scripts load `.env.cloud` when `HCLOUD_TOKEN` is not already set.

```bash
export HCLOUD_TOKEN="REPLACE_WITH_HETZNER_TOKEN"
```

Check that it is available without printing it:

```bash
bash ./Deployment/Cloud/Scripts/check-hcloud-token.sh
```

Expected success output:

```text
Hetzner API token check ok
  HCLOUD_TOKEN is set in this shell
  Hetzner API is reachable
  location fsn1 is available
```

## 6. Prepare OpenTofu Variables

[CurrentPC]

Create local tfvars:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/prepare-opentofu-tfvars.sh
```

This creates `terraform.tfvars` if needed and updates `admin_ssh_cidrs` to your current public IPv4 `/32`. If you change network, VPN, or public IP before provisioning, rerun the same script before the next `tofu plan`.

Review:

```text
Deployment/Cloud/infra/opentofu/terraform.tfvars
```

Expected v1 values:

```hcl
project_name = "bookscloud"
location = "fsn1"
network_zone = "eu-central"
server_type = "cx23"
image = "ubuntu-24.04"
ssh_public_key_path = "~/.ssh/bookscloud_deploy.pub"
public_ipv4_enabled = true
public_ipv6_enabled = true
admin_ssh_cidrs = ["<your-current-public-ipv4>/32"]
private_network_cidr = "10.10.0.0/24"
cloud_main_private_ip = "10.10.0.10"
cloud_app1_private_ip = "10.10.0.11"
cloud_app2_private_ip = "10.10.0.12"
cloud_db_private_ip = "10.10.0.13"
```

`terraform.tfvars` is ignored by git.

## 7. Create Hetzner Infrastructure With OpenTofu

[CurrentPC]

Do not manually create the four servers in Hetzner. OpenTofu owns them.

Only continue after Step 6 has created:

```text
Deployment/Cloud/infra/opentofu/terraform.tfvars
```

```bash
cd "$(git rev-parse --show-toplevel)/Deployment/Cloud/infra/opentofu"
bash ../../Scripts/check-hcloud-token.sh
tofu init
tofu fmt -check versions.tf variables.tf locals.tf main.tf firewalls.tf outputs.tf
tofu validate
tofu plan -out cloud.tfplan
```

Review the plan. It should create:

- `cloud-main`
- `cloud-app1`
- `cloud-app2`
- `cloud-db`
- one private network
- private network attachments at server creation time
- cloud-init netplan DHCP configuration for the first Hetzner private-network interface
- public IPv4 and IPv6 enabled only for `cloud-main`
- a private-network default route through `cloud-main`
- baseline public firewalls
- dedicated temporary SSH firewall for `CD - Cloud`
- one SSH key resource

The plan should not create a public load balancer, public HTTP/HTTPS listener, public database port, or public Redis port.

If you previously created servers with an older copy of this guide and Step 11 failed with private hosts unreachable at `10.10.0.x`, rerun this plan/apply now. The updated OpenTofu module attaches the private network during server creation and writes the private-network netplan DHCP config during cloud-init. Because the current Cloud database is disposable, server replacement is acceptable.

For that exact recovery path, create a replacement plan instead of the normal plan:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/plan-replace-cloud-servers.sh
```

Review the replacement plan. It should replace the four cloud servers and keep the network, firewalls, and SSH key managed by OpenTofu.

Apply only after the plan matches:

```bash
cd "$(git rev-parse --show-toplevel)/Deployment/Cloud/infra/opentofu"
tofu apply cloud.tfplan
tofu output
```

Confirm these outputs exist:

```bash
tofu output -raw cloud_main_public_ipv4
tofu output -raw cloud_main_private_ip
tofu output -raw cloud_app1_private_ip
tofu output -raw cloud_app2_private_ip
tofu output -raw cloud_db_private_ip
tofu output -raw cloud_temp_ssh_firewall_id
```

Back up the local state after apply:

```bash
mkdir -p ~/.local/state/bookscloud
cp terraform.tfstate ~/.local/state/bookscloud/terraform.tfstate.$(date -u +%Y%m%dT%H%M%SZ)
chmod 600 ~/.local/state/bookscloud/terraform.tfstate.*
```

State, plan, local tfvars, provider cache, and generated inventory files are ignored by `.gitignore`. The provider lock file is intentionally committed:

```text
Deployment/Cloud/infra/opentofu/.terraform.lock.hcl
```

Before committing, this command should report ignore rules for generated/private files:

```bash
cd "$(git rev-parse --show-toplevel)"
git check-ignore -v \
  Deployment/Cloud/infra/opentofu/terraform.tfvars \
  Deployment/Cloud/infra/opentofu/terraform.tfstate \
  Deployment/Cloud/infra/opentofu/cloud.tfplan \
  Deployment/Cloud/infra/opentofu/.terraform/providers/example \
  Deployment/Cloud/inventory/prod/hosts.yml
```

Then review `git status --short`. It should not show `terraform.tfvars`, `.terraform/`, `terraform.tfstate`, `cloud.tfplan`, or `Deployment/Cloud/inventory/prod/hosts.yml`.

## 8. Render Cloud Inventory

[CurrentPC]

Only continue after Step 7 has applied OpenTofu successfully.

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/render-inventory-from-tofu.sh
```

This creates:

```text
Deployment/Cloud/inventory/prod/hosts.yml
```

Validate host IPs, groups, and SSH routing:

```bash
bash ./Deployment/Cloud/Scripts/validate-rendered-inventory.sh
```

The generated inventory must route private nodes through `cloud-main` with an explicit `ProxyCommand` that passes the deploy key to the bastion leg. Do not hand-edit it back to `ProxyJump`; the preflight rejects stale `ProxyJump` inventory because the jump host may not receive the same identity options as the final SSH target.

If Step 7 replaced existing Cloud servers, remove stale SSH host keys for the old server identities before provisioning:

```bash
bash ./Deployment/Cloud/Scripts/reset-cloud-known-hosts.sh
```

Expected shape:

```text
Cloud inventory validation ok

host         ansible_host    private_ip      public_ipv4     route
cloud-main   <public-ip>     10.10.0.10      <public-ip>     direct public SSH
cloud-app1   10.10.0.11      10.10.0.11      -               via cloud-main (<cloud-main-public-ip>)
cloud-app2   10.10.0.12      10.10.0.12      -               via cloud-main (<cloud-main-public-ip>)
cloud-db     10.10.0.13      10.10.0.13      -               via cloud-main (<cloud-main-public-ip>)
```

## 9. Create Cloudflare Tunnel

[Cloudflare]

Open the Cloudflare dashboard:

```text
https://dash.cloudflare.com/
```

Go to:

```text
Zero Trust -> Networks -> Connectors -> Cloudflare Tunnels
```

If Cloudflare sends you to the Zero Trust dashboard directly, the URL will look similar to:

```text
https://one.dash.cloudflare.com/
```

Create a tunnel:

1. Select `Create a tunnel`.
2. Choose `Cloudflared`.
3. Tunnel name:

```text
bookscloud-prod
```

4. Save the tunnel.
5. In the connector/install step, choose a Linux/Docker option only so Cloudflare shows the connector command.
6. Copy only the long token value from the command. It will become the GitHub environment secret `CLOUD_CLOUDFLARE_TUNNEL_TOKEN`.

The command shown by Cloudflare usually looks like this:

```text
cloudflared service install <long-token-value>
```

Do not run that command on any cloud server. Ansible will install cloudflared on `cloud-main`.

Add the public hostname:

1. Open the tunnel `bookscloud-prod`.
2. Go to `Public Hostnames`.
3. Select `Add a public hostname`.
4. Enter:

```text
Subdomain: bookscloud
Domain: jacobgrum.com
Path: leave empty
Type: HTTP
URL: 127.0.0.1:80
```

The resulting public hostname should be:

```text
bookscloud.jacobgrum.com
```

Save the public hostname.

[CurrentPC]

Verify public health from your current machine:

```bash
cd "$(git rev-parse --show-toplevel)"
curl -fsS https://bookscloud.jacobgrum.com/health/ready
bash ./Deployment/Cloud/Scripts/doctor.sh
```

No Cloudflare API token is required by this guide. If GitHub Actions later receives a Cloudflare managed challenge while your browser and `doctor.sh` can reach the site, the Cloud deployment acceptance script treats that as Cloudflare edge policy after all origin checks have passed.

## 10. Configure GitHub Environment

[CurrentPC]

Only continue after Step 7 has applied OpenTofu and Step 9 has produced the Cloudflare tunnel token.

Prepare the values the script may prompt for:

```text
CLOUD_GHCR_USERNAME
```

Use the GitHub username for the account that owns the package-read token. For this repo, that is usually:

```text
Grumlebob
```

```text
CLOUD_GHCR_TOKEN
```

Use a GitHub personal access token for pulling the app image from GitHub Container Registry. This is not the Hetzner token, not the Cloudflare tunnel token, and not your GitHub password.

Create it in GitHub:

1. Open:

```text
https://github.com/settings/tokens
```

2. Select `Generate new token`.
3. Select `Generate new token (classic)`.
4. Note:

```text
bookscloud-ghcr-read
```

5. Expiration: choose a sensible rotation window.
6. Scopes: select only:

```text
read:packages
```

7. Generate the token.
8. Copy it immediately. It will usually start with `ghp_`.

If GitHub shows an organization SSO authorization button for the token, authorize it for the organization that owns `ghcr.io/grumlebob/books`.

```text
CLOUD_CLOUDFLARE_TUNNEL_TOKEN
```

Use the long token value copied from the Cloudflare `cloudflared service install <long-token-value>` command in Step 9. If repo-root `.env.cloud` contains a value that looks like a real Cloudflare tunnel token, `configure-github-environment.sh` uses it. If it is missing or looks like a note/placeholder, the script keeps an existing GitHub secret or prompts as before.

Configure the GitHub environment and secrets:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/configure-github-environment.sh
```

The script creates the `cloud-hetzner` environment, reads OpenTofu outputs, sets infrastructure secrets, creates missing PostgreSQL/Redis secrets, and prompts for any missing GHCR or Cloudflare secrets. `CLOUD_GHCR_USERNAME` and `CLOUD_GHCR_TOKEN` must be able to pull `ghcr.io/grumlebob/books`.

Existing PostgreSQL and Redis secrets are kept by default. To intentionally rotate disposable Cloud data secrets, run:

```bash
ROTATE_CLOUD_DATA_SECRETS=1 bash ./Deployment/Cloud/Scripts/configure-github-environment.sh
```

[GitHub]

Use environment protection if you want a manual approval gate before deployment.

Required secret list:

```text
CLOUD_SSH_PRIVATE_KEY
CLOUD_BASTION_HOST
CLOUD_HETZNER_API_TOKEN
CLOUD_TEMP_SSH_FIREWALL_ID
CLOUD_GHCR_USERNAME
CLOUD_GHCR_TOKEN
CLOUD_POSTGRES_USER
CLOUD_POSTGRES_PASSWORD
CLOUD_POSTGRES_DB
CLOUD_REDIS_PASSWORD
CLOUD_CLOUDFLARE_TUNNEL_TOKEN
```

[CurrentPC]

Verify the environment contains every required secret name:

```bash
bash ./Deployment/Cloud/Scripts/check-github-environment.sh
```

## 11. Provision Cloud Nodes

[CurrentPC]

Provisioning installs and configures:

- Docker on app and data nodes.
- Caddy on `cloud-main`.
- SSH hardening.
- Host firewall rules that enforce private-network access.
- Deployment directories.

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/provision.sh
```

`provision.sh` runs preflight before Ansible changes the nodes. The preflight includes an SSH reachability check for all four Cloud nodes. It should print:

```text
Cloud SSH reachability check ok
```

If preflight repeatedly reports private nodes unreachable at `10.10.0.x` with `Connection closed by UNKNOWN port 65535`, stop the retry loop and check the bastion-to-private network path:

```bash
bash ./Deployment/Cloud/Scripts/diagnose-cloud-private-network.sh
```

The diagnosis connects only to `cloud-main`, then prints its private addresses, routes, and TCP/22 checks to `cloud-app1`, `cloud-app2`, and `cloud-db`.

- If those TCP/22 checks are `OK`, rerender and validate inventory, then rerun preflight. The likely issue is stale SSH proxy inventory.
- If those TCP/22 checks are `FAIL`, the Hetzner private interface or route is not up inside the guest. Stop and fix that layer before running provisioning again.

This should result in:

- Ansible reaches all four nodes.
- Private-node SSH goes through `cloud-main`.
- Docker is available where needed.
- Caddy is ready on `cloud-main`.
- Host firewalls block app, PostgreSQL, and Redis traffic from unauthorized sources.
- Firewall rules are applied on private service nodes first, then on `cloud-main`, so the bastion is not changed while it is carrying private-node provisioning traffic.

The `CD - Cloud` workflow also runs provisioning idempotently before deployment.

## 12. Deploy The App

[GitHub]

The workflow must be:

```text
.github/workflows/cd-cloud.yml
```

Display name:

```yaml
name: CD - Cloud
```

Before dispatch:

- commit and push the Cloud deployment code to `main`.
- confirm `CI` passed for the same commit.
- confirm `bash ./Deployment/Cloud/Scripts/check-github-environment.sh` passes.

First deployment:

```text
Actions -> CD - Cloud -> Run workflow -> run_migrations=true
```

The workflow does:

- require `main`.
- require successful CI for the same commit.
- verify the GHCR image exists.
- download the migration bundle when migrations are enabled.
- temporarily allow SSH from the GitHub runner IP to `cloud-main`.
- render Cloud inventory from GitHub environment secrets.
- provision Cloud nodes idempotently.
- run the Cloud observability capacity preflight.
- deploy the Cloud observability backend and agents when `observability_enabled: true`.
- deploy PostgreSQL and Redis on `cloud-db`.
- create a pre-migration PostgreSQL backup.
- run the migration bundle once on `cloud-db`.
- deploy app containers on `cloud-app1` and `cloud-app2`.
- deploy Caddy and cloudflared on `cloud-main`.
- run acceptance checks.
- run the Cloud observability doctor when `observability_enabled: true`.
- remove the temporary SSH allow rule even if deployment fails.

## 13. Acceptance Checks

[GitHub] or [CurrentPC]

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/acceptance-check.sh
```

Acceptance must verify:

- SSH to `cloud-main` works.
- SSH through `cloud-main` to `cloud-app1`, `cloud-app2`, and `cloud-db` works.
- Docker Compose project is running on each service node.
- PostgreSQL container is healthy on `cloud-db`.
- Redis container is healthy on `cloud-db`.
- app `/health/ready` works on both app nodes over the private network.
- Caddy can route locally on `cloud-main`.
- both app nodes pass direct private-network readiness checks, and Caddy routes through the app pool.
- cloudflared service is active on `cloud-main`.
- public `https://bookscloud.jacobgrum.com/health/ready` works, or Cloudflare explicitly returns a managed challenge to the GitHub runner after origin checks have already passed.
- app home page returns success, or Cloudflare explicitly returns a managed challenge to the GitHub runner after origin checks have already passed.
- public PostgreSQL and Redis are not reachable.
- public app port `8080` is not reachable on app nodes.
- public Grafana, Alertmanager, Prometheus, Loki, and Tempo ports are not reachable on `cloud-main`.
- app port, PostgreSQL, and Redis reject unauthorized private-network sources.
- backup directory exists on `cloud-db`.

The acceptance script is challenge-tolerant by default only for Cloudflare managed challenges from the public edge. It remains strict for SSH, Docker, PostgreSQL, Redis, Caddy local routing, app-node health, and firewall checks. To force strict public edge checks, run:

```bash
CLOUD_ACCEPT_CLOUDFLARE_CHALLENGE=false bash ./Deployment/Cloud/Scripts/acceptance-check.sh
```

## 14. Verify Cloud Observability

[GitHub] or [CurrentPC]

The `CD - Cloud` workflow runs this automatically after acceptance when `observability_enabled: true`:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/observability-doctor.sh
```

The doctor verifies:

- Grafana, Prometheus, Alertmanager, Loki, and Tempo are running on `cloud-main`.
- Alloy and node-exporter are running on every Cloud node.
- PostgreSQL and Redis exporters are running on `cloud-db`.
- Prometheus sees all Cloud scrape targets.
- app telemetry identifies `cloud-app1` and `cloud-app2` separately through `host_name` labels with `deployment_target="cloud"` and Git-SHA `service_version` values.
- the shared Grafana dashboard is provisioned.
- no observability container has been OOMKilled.
- active Prometheus series and Loki streams stay below the Cloud budgets.

Open Cloud Grafana from CurrentPC:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/open-observability-tunnel.sh
```

Then open:

```text
http://127.0.0.1:3000
```

To print a Cloud observability resource snapshot:

```bash
bash ./Deployment/Cloud/Scripts/observability-resource-report.sh
```

Do not expose Grafana, Prometheus, Loki, Tempo, Alloy, or exporter ports publicly.

## 15. Backup And Restore

[CurrentPC]

Minimum backup posture before treating Cloud data as valuable:

- Hetzner server backups or scheduled snapshots enabled at least for `cloud-db`.
- PostgreSQL `pg_dump` before every migration.
- scheduled PostgreSQL dumps.
- off-server copy of PostgreSQL dumps.
- Redis append-only persistence enabled.
- restore drill to a disposable database.

Do not treat Hetzner snapshots as the only database backup.

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/backup-db.sh
bash ./Deployment/Cloud/Scripts/restore-db.sh --help
```

## 16. Troubleshooting Loop

When a step fails:

1. Stop at the failing step.
2. Capture the exact command and error.
3. Fix the implementation or guide.
4. Rerun the smallest relevant check.
5. Continue from the failed step, not from the beginning.

Do not manually patch cloud servers outside the guide unless the guide is updated with the exact command and reason.

## Sources

- Hetzner Cloud docs overview: `https://docs.hetzner.com/cloud/`
- Hetzner Cloud servers overview: `https://docs.hetzner.com/cloud/servers/overview`
- Hetzner Cloud price adjustment table: `https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/`
- Hetzner Cloud network options and public IP note: `https://docs.hetzner.com/cloud/servers/overview/`
- Hetzner Cloud Firewall docs: `https://docs.hetzner.com/cloud/firewalls/getting-started/creating-a-firewall/`
- Hetzner Cloud Firewall overview: `https://docs.hetzner.com/cloud/firewalls/overview`
- Hetzner Cloud Firewall FAQ: `https://docs.hetzner.com/cloud/firewalls/faq/`
- Hetzner Cloud API reference: `https://docs.hetzner.cloud/reference/cloud`
- Hetzner Cloud API token guide: `https://docs.hetzner.com/cloud/api/getting-started/generating-api-token`
- Cloudflare Tunnel firewall requirements: `https://developers.cloudflare.com/tunnel/configuration/`
- Hetzner Cloud Server FAQ: `https://docs.hetzner.com/cloud/servers/faq`
- Hetzner Object Storage overview: `https://docs.hetzner.com/storage/object-storage/overview/`
- Cloudflare Tunnel docs: `https://developers.cloudflare.com/tunnel/`
- Cloudflare Tunnel configuration docs: `https://developers.cloudflare.com/tunnel/configuration/`
- Cloudflare dashboard tunnel creation guide: `https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/`
- OpenTofu Debian/Ubuntu install docs: `https://opentofu.org/docs/intro/install/deb/`
- GitHub CLI install docs: `https://github.com/cli/cli/blob/trunk/docs/install_linux.md`
- GitHub Container Registry authentication docs: `https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry`
- GitHub personal access token docs: `https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens`
- OpenTofu S3 backend docs: `https://opentofu.org/docs/language/settings/backends/s3/`
- OpenTofu sensitive state docs: `https://opentofu.org/docs/language/state/sensitive-data/`
- OpenTofu provider requirements and lock-file guidance: `https://opentofu.org/docs/language/providers/requirements/`
- OpenTofu v1.x compatibility promises: `https://opentofu.org/docs/language/v1-compatibility-promises/`
- Terraform hcloud provider docs: `https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs`
