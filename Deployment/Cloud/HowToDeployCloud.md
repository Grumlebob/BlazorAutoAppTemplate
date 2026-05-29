# How To Deploy Cloud

This is the only cloud deployment plan and runbook. Follow it from top to bottom.

The target site is:

```text
https://bookscloud.jacobgrum.com
```

## Current Status

The Cloud deployment is not live yet.

Current runnable range:

- Steps 0, 1, 1.1, 2, 4, and 5 can be followed now.
- Step 3 is an implementation checklist for Codex.
- Stop before Step 6 until the OpenTofu module has been implemented.
- Do not create Hetzner servers manually.
- No cloud server commands are needed yet because the cloud servers do not exist yet.

Implemented:

- Cloud runbook exists.
- Cloud folder skeleton exists.
- Cloud committed settings and examples exist.
- Cloud settings validation, setting reader, summary, and CurrentPC tool setup/checks exist.

Pending implementation:

- OpenTofu module.
- OpenTofu inventory outputs.
- inventory renderer.
- Cloud Compose files.
- Caddy config.
- Cloud Ansible playbooks and roles.
- Cloud CD workflow.
- acceptance, backup, and restore scripts.

Do not run commands for missing scripts or workflows. When this guide reaches a missing implementation item, Codex should implement it, we validate it, and then you continue from the next runbook step.

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
- Public networking: all four servers get public IPv4 and IPv6 in v1 so package installs, Docker pulls, GHCR pulls, and outbound updates are simple and reliable.
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
```

Nodes:

```text
cloud-main  - Caddy, Cloudflare Tunnel, SSH bastion, ingress checks
cloud-app1  - app container
cloud-app2  - app container
cloud-db    - PostgreSQL and Redis containers
```

Network:

```text
cloud_private_network_cidr: 10.10.0.0/24
cloud_main_private_ip: 10.10.0.10
cloud_app1_private_ip: 10.10.0.11
cloud_app2_private_ip: 10.10.0.12
cloud_db_private_ip: 10.10.0.13
```

Security posture:

- No public HTTP/HTTPS ports for v1; Cloudflare Tunnel is the public ingress.
- Public IPv4/IPv6 exists on all nodes for outbound package and image access.
- Hetzner Cloud Firewalls protect public inbound traffic.
- Host firewalls protect private-network traffic.
- SSH to `cloud-main` is public only from an explicit admin CIDR or temporary GitHub runner CIDR.
- SSH to private nodes is not public; Ansible reaches them through `cloud-main`.
- App port `8080` is allowed only from `cloud-main` over the private network by host firewall.
- PostgreSQL and Redis are allowed only from `cloud-app1` and `cloud-app2` over the private network by host firewall.
- PostgreSQL and Redis are never public.
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

## 1.1. Confirm Cost Target

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

Cost note:

- Four `cx23` servers are the cheapest v1 shape for this multi-VPS x86_64 design.
- A one-server deployment would be cheaper, but it would not demonstrate the chosen multi-node architecture.
- v1 deliberately gives all four nodes public IPv4 for reliable outbound internet, so budget for four IPv4 addresses.
- Backups, snapshots, volumes, object storage, and traffic over included limits can add cost.
- Check Hetzner's current pricing before applying if exact monthly cost matters.

## 2. Confirm Cloud Settings Examples

[CurrentPC]

Review:

```text
Deployment/Cloud/inventory/prod/group_vars/all.yml
Deployment/Cloud/inventory/prod/group_vars/all.example.yml
Deployment/Cloud/inventory/prod/hosts.example.yml
Deployment/Cloud/infra/opentofu/terraform.tfvars.example
```

Expected Cloud deployment identity:

```yaml
app_name: bookscloud
public_hostname: bookscloud.jacobgrum.com
deploy_root: /opt/bookscloud
cloudflare_tunnel_name: bookscloud-prod
```

Generated/private files:

```text
Deployment/Cloud/inventory/prod/hosts.yml
Deployment/Cloud/infra/opentofu/terraform.tfvars
Deployment/Cloud/infra/opentofu/terraform.tfstate
```

`Deployment/Cloud/inventory/prod/group_vars/all.yml` is committed because it contains non-secret Cloud settings. The generated/private files above must not be committed.

Validate Cloud settings:

```bash
bash ./Deployment/Cloud/Scripts/validate-cloud-settings.sh
bash ./Deployment/Cloud/Scripts/summary.sh
```

## 3. Implementation Queue

[CurrentPC]

Before the first real Cloud deployment, these files must be implemented:

```text
Deployment/Cloud/infra/opentofu/*.tf
Deployment/Cloud/infra/opentofu/cloud-init.yaml.tftpl
Deployment/Cloud/Scripts/render-inventory-from-tofu.sh
Deployment/Cloud/Scripts/preflight.sh
Deployment/Cloud/Scripts/provision.sh
Deployment/Cloud/Scripts/deploy.sh
Deployment/Cloud/Scripts/acceptance-check.sh
Deployment/Cloud/Scripts/backup-db.sh
Deployment/Cloud/Scripts/restore-db.sh
Deployment/Cloud/ansible/ansible.cfg
Deployment/Cloud/ansible/playbooks/provision.yml
Deployment/Cloud/ansible/playbooks/deploy.yml
Deployment/Cloud/ansible/roles/*
Deployment/Cloud/compose/app-server/docker-compose.yml
Deployment/Cloud/compose/data/docker-compose.yml
Deployment/Cloud/caddy/Caddyfile
.github/workflows/cd-cloud.yml
```

Implementation order:

1. OpenTofu module and inventory outputs.
2. Inventory renderer.
3. Compose files and Caddy template.
4. Ansible provision/deploy playbooks.
5. Cloud CD workflow.
6. Acceptance, backup, and restore scripts.

The OpenTofu module must expose at least these outputs because later guide steps and GitHub secrets depend on their exact names:

```text
cloud_main_public_ipv4
cloud_main_private_ip
cloud_app1_private_ip
cloud_app2_private_ip
cloud_db_private_ip
cloud_temp_ssh_firewall_id
```

Each implementation pass must end with:

```bash
git diff --check
bash ./Deployment/Common/Scripts/validate-common-release.sh
bash ./Deployment/Cloud/Scripts/validate-cloud-settings.sh
bash ./Deployment/Cloud/Scripts/check-currentpc-tools.sh
shellcheck Deployment/Cloud/Scripts/*.sh Deployment/Common/Scripts/*.sh
yamllint Deployment/Cloud Deployment/Common
```

If `Deployment/Common` or `Deployment/LocalCluster` changed in that pass, also run the LocalCluster validation gate.

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

OpenTofu will install this public key on the cloud servers. GitHub CD will later need the private key as `CLOUD_SSH_PRIVATE_KEY`.

Do not commit either key.

## 5. Create Hetzner API Token

[Hetzner]

Create a Hetzner Cloud project for the Cloud deployment, or use an existing project dedicated to this app.

Create an API token for OpenTofu and temporary SSH firewall updates.

Token use:

- `[CurrentPC]` OpenTofu creates infrastructure.
- `[GitHub]` `CD - Cloud` temporarily updates the dedicated temporary SSH firewall for `cloud-main`.

Store the token in your password manager. Do not commit it.

[CurrentPC]

Set it for the current shell:

```bash
export HCLOUD_TOKEN="REPLACE_WITH_HETZNER_TOKEN"
```

Check that it is present without printing it:

```bash
test -n "${HCLOUD_TOKEN:?HCLOUD_TOKEN is required}"
```

## 6. Prepare OpenTofu Variables

[CurrentPC]

After the OpenTofu module exists, create local tfvars:

```bash
cd "$(git rev-parse --show-toplevel)"
cp -n Deployment/Cloud/infra/opentofu/terraform.tfvars.example Deployment/Cloud/infra/opentofu/terraform.tfvars
```

Set your current public IPv4 CIDR for initial `[CurrentPC]` SSH access:

```bash
CURRENT_PUBLIC_IPV4="$(curl -fsS4 https://checkip.amazonaws.com | tr -d '[:space:]')"
python3 - "$CURRENT_PUBLIC_IPV4" <<'PY'
from pathlib import Path
import sys

path = Path("Deployment/Cloud/infra/opentofu/terraform.tfvars")
current_ip = sys.argv[1]
content = path.read_text(encoding="utf-8")
content = content.replace('admin_ssh_cidrs = ["REPLACE_WITH_YOUR_CURRENT_PUBLIC_IPV4/32"]', f'admin_ssh_cidrs = ["{current_ip}/32"]')
path.write_text(content, encoding="utf-8")
PY
```

If you change network, VPN, or public IP before provisioning, rerun this replacement or edit `admin_ssh_cidrs` before the next `tofu plan`.

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

After the OpenTofu module exists:

```bash
cd "$(git rev-parse --show-toplevel)/Deployment/Cloud/infra/opentofu"
test -n "${HCLOUD_TOKEN:?HCLOUD_TOKEN is required}"
tofu init
tofu fmt -check
tofu validate
tofu plan -out cloud.tfplan
```

Review the plan. It should create:

- `cloud-main`
- `cloud-app1`
- `cloud-app2`
- `cloud-db`
- one private network
- private network attachments
- public IPv4 and IPv6 enabled for all four servers
- baseline public firewalls
- dedicated temporary SSH firewall for `CD - Cloud`
- one SSH key resource

The plan should not create a public load balancer, public HTTP/HTTPS listener, public database port, or public Redis port.

Apply only after the plan matches:

```bash
tofu apply cloud.tfplan
tofu output
```

Back up the local state after apply:

```bash
mkdir -p ~/.local/state/bookscloud
cp terraform.tfstate ~/.local/state/bookscloud/terraform.tfstate.$(date -u +%Y%m%dT%H%M%SZ)
chmod 600 ~/.local/state/bookscloud/terraform.tfstate.*
```

Do not commit state or plan files.

## 8. Render Cloud Inventory

[CurrentPC]

After the inventory renderer exists:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/render-inventory-from-tofu.sh
```

Expected generated file:

```text
Deployment/Cloud/inventory/prod/hosts.yml
```

Verify host aliases:

```bash
grep -E "cloud-main|cloud-app1|cloud-app2|cloud-db" Deployment/Cloud/inventory/prod/hosts.yml
```

`cloud-main` should have the public IP as `ansible_host`. The other nodes should use private IPs and `ProxyJump` through `cloud-main`.

## 9. Create Cloudflare Tunnel

[Cloudflare]

Create a tunnel:

```text
Tunnel name: bookscloud-prod
```

Add public hostname:

```text
Hostname: bookscloud.jacobgrum.com
Service: http://127.0.0.1:80
```

Copy the generated tunnel token. It will become the GitHub environment secret `CLOUD_CLOUDFLARE_TUNNEL_TOKEN`.

Do not install the connector manually on the server. Ansible will install cloudflared on `cloud-main`.

## 10. Configure GitHub Environment

[GitHub]

Create environment:

```text
cloud-hetzner
```

Use environment protection if you want a manual approval gate before deployment.

[CurrentPC]

After OpenTofu has created infrastructure, set environment variables for values that can be derived from outputs:

```bash
cd "$(git rev-parse --show-toplevel)/Deployment/Cloud/infra/opentofu"
export CLOUD_BASTION_HOST="$(tofu output -raw cloud_main_public_ipv4)"
export CLOUD_TEMP_SSH_FIREWALL_ID="$(tofu output -raw cloud_temp_ssh_firewall_id)"
```

Generate database and Redis secrets:

```bash
export CLOUD_POSTGRES_USER="bookscloud_app"
export CLOUD_POSTGRES_DB="bookscloud"
export CLOUD_POSTGRES_PASSWORD="$(openssl rand -base64 36 | tr -d '\n')"
export CLOUD_REDIS_PASSWORD="$(openssl rand -base64 36 | tr -d '\n')"
```

Set GitHub environment secrets:

```bash
cd "$(git rev-parse --show-toplevel)"
gh secret set CLOUD_SSH_PRIVATE_KEY --env cloud-hetzner < ~/.ssh/bookscloud_deploy
gh secret set CLOUD_BASTION_HOST --env cloud-hetzner --body "$CLOUD_BASTION_HOST"
gh secret set CLOUD_SSH_USER --env cloud-hetzner --body "deploy"
gh secret set CLOUD_HETZNER_API_TOKEN --env cloud-hetzner --body "$HCLOUD_TOKEN"
gh secret set CLOUD_TEMP_SSH_FIREWALL_ID --env cloud-hetzner --body "$CLOUD_TEMP_SSH_FIREWALL_ID"
gh secret set CLOUD_POSTGRES_USER --env cloud-hetzner --body "$CLOUD_POSTGRES_USER"
gh secret set CLOUD_POSTGRES_PASSWORD --env cloud-hetzner --body "$CLOUD_POSTGRES_PASSWORD"
gh secret set CLOUD_POSTGRES_DB --env cloud-hetzner --body "$CLOUD_POSTGRES_DB"
gh secret set CLOUD_REDIS_PASSWORD --env cloud-hetzner --body "$CLOUD_REDIS_PASSWORD"
```

Set these secrets interactively so they are not printed in shell history:

```bash
gh secret set CLOUD_GHCR_USERNAME --env cloud-hetzner
gh secret set CLOUD_GHCR_TOKEN --env cloud-hetzner
gh secret set CLOUD_CLOUDFLARE_TUNNEL_TOKEN --env cloud-hetzner
```

Required secret list:

```text
CLOUD_SSH_PRIVATE_KEY
CLOUD_BASTION_HOST
CLOUD_SSH_USER
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

## 11. Provision Cloud Nodes

[CurrentPC] or [GitHub]

Provisioning installs and configures:

- Docker on app and data nodes.
- Caddy and cloudflared on `cloud-main`.
- SSH hardening.
- Host firewall rules that enforce private-network access.
- Deployment directories.

After Ansible playbooks and scripts exist, run:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/preflight.sh
bash ./Deployment/Cloud/Scripts/provision.sh
```

Expected result:

- Ansible reaches all four nodes.
- Private-node SSH goes through `cloud-main`.
- Docker is available where needed.
- Caddy and cloudflared prerequisites are ready on `cloud-main`.
- Host firewalls block app, PostgreSQL, and Redis traffic from unauthorized sources.

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
- confirm all `cloud-hetzner` secrets exist.

First deployment:

```text
Actions -> CD - Cloud -> Run workflow -> run_migrations=true
```

The workflow must:

- require `main`.
- require successful CI for the same commit.
- verify the GHCR image exists.
- download the migration bundle when migrations are enabled.
- temporarily allow SSH from the GitHub runner IP to `cloud-main`.
- deploy PostgreSQL and Redis on `cloud-db`.
- create a pre-migration PostgreSQL backup.
- run the migration bundle once on `cloud-db`.
- deploy app containers on `cloud-app1` and `cloud-app2`.
- deploy Caddy and cloudflared on `cloud-main`.
- run acceptance checks.
- remove the temporary SSH allow rule even if deployment fails.

## 13. Acceptance Checks

[GitHub] or [CurrentPC]

After the acceptance script exists:

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
- Caddy load-balances to both app nodes.
- cloudflared is connected on `cloud-main`.
- public `https://bookscloud.jacobgrum.com/health/ready` works.
- app home page returns success.
- public PostgreSQL and Redis are not reachable.
- public app port `8080` is not reachable on app nodes.
- app port, PostgreSQL, and Redis reject unauthorized private-network sources.
- backup directory exists on `cloud-db`.

## 14. Backup And Restore

[GitHub] or [cloud-db]

Minimum backup posture after first deployment:

- Hetzner server backups enabled at least for `cloud-db`.
- PostgreSQL `pg_dump` before every migration.
- scheduled PostgreSQL dumps.
- off-server copy of PostgreSQL dumps.
- Redis append-only persistence enabled.
- restore drill to a disposable database.

Do not treat Hetzner snapshots as the only database backup.

After backup scripts exist:

```bash
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/backup-db.sh
bash ./Deployment/Cloud/Scripts/restore-db.sh --help
```

## 15. Troubleshooting Loop

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
- Hetzner Cloud Firewall FAQ: `https://docs.hetzner.com/cloud/firewalls/faq/`
- Cloudflare Tunnel firewall requirements: `https://developers.cloudflare.com/tunnel/configuration/`
- Hetzner Cloud Server FAQ: `https://docs.hetzner.com/cloud/servers/faq`
- Hetzner Object Storage overview: `https://docs.hetzner.com/storage/object-storage/overview/`
- Cloudflare Tunnel docs: `https://developers.cloudflare.com/tunnel/`
- Cloudflare Tunnel configuration docs: `https://developers.cloudflare.com/tunnel/configuration/`
- OpenTofu Debian/Ubuntu install docs: `https://opentofu.org/docs/intro/install/deb/`
- GitHub CLI install docs: `https://github.com/cli/cli/blob/trunk/docs/install_linux.md`
- OpenTofu S3 backend docs: `https://opentofu.org/docs/language/settings/backends/s3/`
- OpenTofu sensitive state docs: `https://opentofu.org/docs/language/state/sensitive-data/`
- OpenTofu provider requirements and lock-file guidance: `https://opentofu.org/docs/language/providers/requirements/`
- OpenTofu v1.x compatibility promises: `https://opentofu.org/docs/language/v1-compatibility-promises/`
- Terraform hcloud provider docs: `https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs`
