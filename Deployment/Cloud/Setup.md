# First Cloud deployment

Use this runbook for a new Cloud stack. Run command blocks from the repository root in a Linux shell, including WSL Ubuntu. Do not manually create Hetzner servers; OpenTofu owns them.

Read [the target overview](README.md) for topology and network boundaries. Cloud public ingress is through Cloudflare Tunnel on `cloud-main`. App and database nodes have no public IPs and use its NAT route for outbound traffic.

## Before starting

- Have access to the repository, GitHub Actions settings, a Hetzner project, and Cloudflare Zero Trust.
- Cloud CD requires an existing self-hosted Linux x64 Actions runner on a host named `node-main`. Cloud setup does not install this runner. Configure repository variable `LOCALCLUSTER_RUNNER_LABEL` to match its label, and include `cloud` in `DEPLOY_TARGETS`.
- Keep OpenTofu state, provider credentials, private keys, Cloudflare tokens, and generated files out of Git. Keep secrets for each deployment target separate.

## 1. Check tools, settings, and release inputs

From the repository root:

~~~bash
bash ./Deployment/Cloud/Scripts/setup-currentpc-tools.sh
bash ./Deployment/Cloud/Scripts/check-currentpc-tools.sh
bash ./Deployment/Cloud/Scripts/validate-cloud-settings.sh
bash ./Deployment/Common/Scripts/validate-common-release.sh
bash ./Deployment/Cloud/Scripts/summary.sh
~~~

Expected result: each check exits successfully, and the summary shows the selected Cloud settings. Fix reported errors before creating infrastructure.

Review the committed Cloud settings in `Deployment/Cloud/inventory/prod/group_vars/all.yml` and compare them with `all.example.yml`. Set this deployment's public hostname, app identity, paths, network, and observability choices there. These settings are public configuration, not secrets. Shared image and migration artifact settings come from `Deployment/Common/release.yml`; see the [release contract](../Common/ReleaseContract.md).

## 2. Prepare deploy access and Hetzner credentials

Choose one dedicated SSH key path. Export `CLOUD_SSH_PRIVATE_KEY_PATH` in every shell that runs Cloud scripts, and use the same path for setup and later operations:

~~~bash
export CLOUD_SSH_PRIVATE_KEY_PATH="$HOME/.ssh/cloud_deploy"
install -d -m 0700 "$(dirname "$CLOUD_SSH_PRIVATE_KEY_PATH")"
if [ ! -f "$CLOUD_SSH_PRIVATE_KEY_PATH" ]; then
  ssh-keygen -t ed25519 -f "$CLOUD_SSH_PRIVATE_KEY_PATH" -C "cloud-deploy" -N ""
fi
chmod 0600 "$CLOUD_SSH_PRIVATE_KEY_PATH"
chmod 0644 "$CLOUD_SSH_PRIVATE_KEY_PATH.pub"
~~~

Create a Hetzner API token with Read & Write permissions in the project that will own this stack. Keep it in a local secret store or repo-root `.env.cloud`, then run:

~~~bash
bash ./Deployment/Cloud/Scripts/check-hcloud-token.sh
~~~

Continue only when the check succeeds. It does not print the token. OpenTofu uses it to manage infrastructure; Cloud CD uses it only for the dedicated temporary SSH firewall.

## 3. Plan and create infrastructure

Run the helper from the repository root. It detects the controller's public IPv4 and sets `admin_ssh_cidrs` to that single `/32`:

~~~bash
bash ./Deployment/Cloud/Scripts/prepare-opentofu-tfvars.sh
~~~

Before planning, confirm the CIDR matches the controller. If more administrators need SSH, edit the local tfvars. Review `Deployment/Cloud/infra/opentofu/terraform.tfvars` against `terraform.tfvars.example`. Set `ssh_public_key_path` to the absolute public key path from Step 2 by appending `.pub` to `CLOUD_SSH_PRIVATE_KEY_PATH`. Review deployment identity, location, server type, image, network, and private IP values. Keep public networking only on `cloud-main`.

~~~bash
cd ./Deployment/Cloud/infra/opentofu
tofu init
tofu fmt -check versions.tf variables.tf locals.tf main.tf firewalls.tf outputs.tf
tofu validate
tofu plan -out cloud.tfplan
~~~

Review the plan before applying. It should create the four configured servers, private network, deploy key, and Cloud firewalls for this stack. Confirm only `cloud-main` has public networking; private nodes use its NAT route. Public HTTP/HTTPS, app, database, Redis, and observability ports must remain closed.

Apply only a reviewed plan:

~~~bash
tofu apply cloud.tfplan
tofu output
~~~

Continue only when apply succeeds and the required outputs are available. OpenTofu state contains sensitive values. Back it up outside the repository with owner-only permissions:

~~~bash
install -d -m 0700 "$HOME/.local/state/cloud"
cp terraform.tfstate "$HOME/.local/state/cloud/terraform.tfstate.$(date -u +%Y%m%dT%H%M%SZ)"
chmod 0600 "$HOME/.local/state/cloud/terraform.tfstate."*
~~~

Keep the state backup, plan, and local tfvars private. The repository ignores generated OpenTofu files and rendered inventory.
Return to the repository root before the next phase:

~~~bash
cd "$(git rev-parse --show-toplevel)"
~~~

## 4. Render and validate inventory

From the repository root:

~~~bash
bash ./Deployment/Cloud/Scripts/render-inventory-from-tofu.sh
bash ./Deployment/Cloud/Scripts/validate-rendered-inventory.sh
~~~

The generated inventory must route private-node SSH through `cloud-main` and use the deploy key on both SSH legs. Do not hand-edit generated inventory. Verify host identities through their Hetzner consoles using [SSH host trust](../Common/SshTrust.md) before accepting keys. After a deliberate server replacement, use `reset-cloud-known-hosts.sh` only after verifying the replacement identities; never clear keys to bypass an unexplained mismatch.

## 5. Create the Cloudflare Tunnel

In Cloudflare Zero Trust, create a Cloudflared tunnel. Add the public hostname from the committed Cloud settings and route HTTP to `127.0.0.1:80` on `cloud-main`. Copy the connector token for the GitHub environment step.

Do not run Cloudflare's displayed install command on a server. Ansible installs the connector on `cloud-main`. Do not expose app or observability ports publicly.

## 6. Configure GitHub deployment secrets

Keep the SSH path and Hetzner token available in the current shell. Supply the tunnel token to the helper when prompted, or through `CLOUD_CLOUDFLARE_TUNNEL_TOKEN`:

~~~bash
bash ./Deployment/Cloud/Scripts/configure-github-environment.sh
bash ./Deployment/Cloud/Scripts/check-github-environment.sh
~~~

Continue only when the environment check succeeds. The helper configures the `cloud-hetzner` environment with the SSH key, bastion address, Hetzner token, temporary firewall ID, database credentials, Redis password, Cloudflare token, and one app-owned encrypted Data Protection certificate/passphrase pair. It generates missing values once and preserves existing certificate values. Keep the pair with protected database backups; do not rotate it during routine deployment or recovery. The optional `ROTATE_CLOUD_DATA_SECRETS=1` changes database GitHub secrets only; it does not rotate the password in an initialized PostgreSQL database. Do not use it on an existing stack.

Accounts remain disabled unless enabled in Cloud `group_vars/all.yml`. An Admin seed needs `accounts_enabled`, `accounts_admin_seed_enabled`, and `accounts_admin_seed_email`, but no SMTP settings. Public registration also needs the public HTTPS origin, SMTP host, and sender. To configure an initial Admin password or authenticated SMTP, provide `CLOUD_ACCOUNTS_ADMIN_SEED_PASSWORD`, or both `CLOUD_ACCOUNTS_EMAIL_USERNAME` and `CLOUD_ACCOUNTS_EMAIL_PASSWORD`, in the operator environment or repo-root `.env.cloud` before running this helper. These optional GitHub secrets are set only when supplied and are never rotated by the helper; existing values are kept. Keep the file private and use quoted values when they contain spaces, `$`, `#`, `=`, or quotes.

For a one-time legacy Data Protection import, set `data_protection_legacy_key_store` in Cloud `group_vars/all.yml` to `Redis` with the exact old repository key, or to `FileSystem`. For FileSystem, copy the source XML key files to `/etc/<app_name>/data-protection/legacy` on both app servers, owned by `root:deploy` mode `0440` inside a `root:deploy` mode `0750` directory. The app mounts that directory read-only at `/run/legacy-data-protection`. Dispatch the first account/key-store transition with `run_migrations=true`; the workflow stops both app replicas before schema changes. Wait for both app servers to become healthy, then set the store to `None`, clear the Redis key, and deploy again. Keep the source until the PostgreSQL key ring and existing authentication cookies have been verified.

Custom PostgreSQL and Redis passwords must be 16–128 characters from letters, digits, `.`, `_`, `@`, `%`, `+`, `/`, `=`, or `-`. The deployment passes them through Compose interpolation; account and SMTP values use the separate raw app environment file.

Use GitHub environment protection if a human approval gate is wanted before CD.

## 7. Provision nodes

From the repository root:

~~~bash
bash ./Deployment/Cloud/Scripts/provision.sh
~~~

Preflight checks SSH reachability before Ansible changes hosts. Continue only when provisioning exits successfully. If private nodes cannot be reached through the bastion, stop and run `bash ./Deployment/Cloud/Scripts/diagnose-cloud-private-network.sh`. Fix the private interface or route before retrying provisioning.

## 8. Run the first deployment

Push the Cloud configuration through the normal review process. On `main`, confirm CI passed for the exact commit and the GitHub environment check succeeds. In Actions, dispatch `CD - Cloud` with migrations enabled when the database needs its initial schema.

The workflow provisions idempotently, deploys the database and app, applies migrations once when requested, configures ingress, and runs acceptance checks. It also runs the observability doctor when observability is enabled.

A successful first deployment ends with the workflow green and `doctor.sh` reporting no blockers. For repeat releases, diagnosis, backup/restore, and teardown, use [Operations](Operations.md).
