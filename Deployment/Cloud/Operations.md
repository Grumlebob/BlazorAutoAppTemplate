# Cloud operations

Run command blocks from the repository root in a Linux shell. Export the same `CLOUD_SSH_PRIVATE_KEY_PATH` used during setup in each shell. Start by checking the current state:

~~~bash
bash ./Deployment/Cloud/Scripts/doctor.sh
~~~

Follow the first reported action or blocker. On failure, stop at that step, record the command and error, fix the cause, and rerun the smallest relevant check. Do not patch cloud servers manually; use the repository scripts and a reviewed OpenTofu plan for infrastructure changes.

## Release the app

The [`CD - Cloud` workflow](../../.github/workflows/cd-cloud.yml) is the supported release path. It runs on the existing self-hosted Linux x64 runner on `node-main`, requires CI success for the same commit, provisions hosts idempotently, manages temporary SSH access, and runs acceptance checks.

In GitHub Actions, open `CD - Cloud`, choose **Run workflow** on `main`, and set `run_migrations=true` when the release includes a migration bundle that must run. Require successful publishing CI for that exact commit; Cloud has no `target_sha` input. If documentation commits skipped CI, [publish current main first](../Common/ReleaseContract.md#select-a-published-source). Wait for CD to finish green. The workflow creates a pre-migration PostgreSQL backup and runs the bundle once.

## Diagnose connectivity and readiness

Run local tool, inventory, and SSH preflight checks:

~~~bash
bash ./Deployment/Cloud/Scripts/preflight.sh
~~~

If `cloud-main` is reachable but private-node SSH fails, inspect the private route from the bastion:

~~~bash
bash ./Deployment/Cloud/Scripts/diagnose-cloud-private-network.sh
~~~

If TCP/22 from the bastion to a private node fails, stop. Repair the guest interface or route before rerunning provisioning. If the checks succeed, rerender and validate inventory before retrying.

### Replace servers after private-network attachment failure

Use this recovery only for the private-network attachment failure covered by the [replacement helper](Scripts/plan-replace-cloud-servers.sh). It replaces all four Cloud servers, not one server. Replacement deletes host-local app, PostgreSQL/Redis, and observability data. Before planning, create a verified database dump, fetch it from the node, and confirm a copy exists outside the Cloud stack. Export telemetry if history matters. See [observability recovery](../../docs/Observability/Operations.md); no remote telemetry archive is configured.

Back up OpenTofu state before planning, then create and inspect the replacement plan:

~~~bash
cd ./Deployment/Cloud/infra/opentofu
install -d -m 0700 "$HOME/.local/state/cloud"
cp terraform.tfstate "$HOME/.local/state/cloud/terraform.tfstate.pre-replace.$(date -u +%Y%m%dT%H%M%SZ)"
chmod 0600 "$HOME/.local/state/cloud/terraform.tfstate.pre-replace."*
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/plan-replace-cloud-servers.sh
~~~

The plan should replace all four servers and retain the network, firewalls, and SSH key. Stop if it includes other changes or the backup is not stored outside the stack. If OpenTofu says the saved plan is stale, regenerate and review a new plan. Apply only the reviewed plan:

~~~bash
cd ./Deployment/Cloud/infra/opentofu
tofu apply cloud.tfplan
tofu output
install -d -m 0700 "$HOME/.local/state/cloud"
cp terraform.tfstate "$HOME/.local/state/cloud/terraform.tfstate.post-replace.$(date -u +%Y%m%dT%H%M%SZ)"
chmod 0600 "$HOME/.local/state/cloud/terraform.tfstate.post-replace."*
cd "$(git rev-parse --show-toplevel)"
bash ./Deployment/Cloud/Scripts/render-inventory-from-tofu.sh
bash ./Deployment/Cloud/Scripts/validate-rendered-inventory.sh
~~~

Verify the new host identities through their consoles using [SSH host trust](../Common/SshTrust.md), then reset only the cached Cloud inventory keys and refresh GitHub's bastion address. Keep the existing data credentials; do not enable `ROTATE_CLOUD_DATA_SECRETS`:

~~~bash
bash ./Deployment/Cloud/Scripts/reset-cloud-known-hosts.sh
bash ./Deployment/Cloud/Scripts/configure-github-environment.sh
bash ./Deployment/Cloud/Scripts/check-github-environment.sh
bash ./Deployment/Cloud/Scripts/provision.sh
~~~

Provisioning prepares hosts, Caddy and optional telemetry; it does not start the app, PostgreSQL, Redis or Cloudflare connector. For an intentionally empty replacement stack, continue with [first deployment](Setup.md#8-run-the-first-deployment). To recover existing data, stop here until an operator-reviewed database recovery plan covers the empty database, selected backup, migrations and release. The import limitations below apply. A green redeployment alone does not restore lost data.

After deployment and any data recovery, validate recovered records and run `bash ./Deployment/Cloud/Scripts/acceptance-check.sh`.

Cloudflare managed challenges are tolerated only for public-edge checks after origin checks pass. To require a strict public response, run:

~~~bash
CLOUD_ACCEPT_CLOUDFLARE_CHALLENGE=false bash ./Deployment/Cloud/Scripts/acceptance-check.sh
~~~

## Observe the stack

The deployment workflow runs the Cloud observability doctor when observability is enabled. Run it directly when diagnosing telemetry or capacity:

~~~bash
bash ./Deployment/Cloud/Scripts/observability-doctor.sh
bash ./Deployment/Cloud/Scripts/observability-resource-report.sh
~~~

Open the private Grafana endpoint through an SSH tunnel; do not expose observability ports:

~~~bash
bash ./Deployment/Cloud/Scripts/open-observability-tunnel.sh
~~~

For shared dashboard, retention, query, and recovery guidance, see [Observability operations](../../docs/Observability/Operations.md).

## Back up and restore PostgreSQL

Create a PostgreSQL dump:

~~~bash
bash ./Deployment/Cloud/Scripts/backup-db.sh
~~~

The script reports a path under the configured `deploy_root/backups/` on `cloud-db` and checks the gzip stream and SQL dump marker. It does not test a restore or copy the dump off the node. Fetch it to a protected controller directory, then copy it to approved off-host storage before destructive changes:

~~~bash
install -d -m 0700 "$HOME/cloud-backups"
ANSIBLE_CONFIG=./Deployment/Cloud/ansible/ansible.cfg ANSIBLE_ROLES_PATH=./Deployment/Cloud/ansible/roles \
  ansible node_db -i ./Deployment/Cloud/inventory/prod/hosts.yml \
  -m ansible.builtin.fetch \
  -a "src=<deploy-root>/backups/<backup-file>.sql.gz dest=$HOME/cloud-backups/ flat=yes"
chmod 0600 "$HOME/cloud-backups/<backup-file>.sql.gz"
gzip -t "$HOME/cloud-backups/<backup-file>.sql.gz"
~~~

Replace `<deploy-root>` and `<backup-file>` with the configured path and name printed by the backup script. The deployment workflow also creates a pre-migration backup. Neither backup is an off-host disaster-recovery copy until you transfer it.

The database dump does not contain the Data Protection certificate private key. Keep the `CLOUD_DATA_PROTECTION_CERTIFICATE_BASE64` and `CLOUD_DATA_PROTECTION_CERTIFICATE_PASSWORD` environment secrets with protected off-host backups. Preserve both values across routine deployment and database restore. The same pair must be installed on every app server before restored users, cookies, or encrypted account-mail outbox rows can be read.

Restore requires an operator-reviewed recovery plan with app writes stopped and an empty target schema. The [current SQL importer](Scripts/Component/cloud-db/restore-db.sh) does not clear existing objects, stop app writes, or use [ON_ERROR_STOP](https://www.postgresql.org/docs/18/app-psql.html); its exit code alone cannot prove recovery succeeded. Never run it against a populated database expecting a safe replacement or isolated test restore.

The wrapper requires a dump under the configured deploy root's `backups/` directory and exact app/database confirmation. Once the recovery prerequisites are satisfied, copy an off-host dump back to `cloud-db` and import it:

~~~bash
gzip -t "$HOME/cloud-backups/<backup-file>.sql.gz"
ANSIBLE_CONFIG=./Deployment/Cloud/ansible/ansible.cfg ANSIBLE_ROLES_PATH=./Deployment/Cloud/ansible/roles \
  ansible node_db -i ./Deployment/Cloud/inventory/prod/hosts.yml \
  -m ansible.builtin.file \
  -a "path=<deploy-root>/backups state=directory owner=deploy group=deploy mode=0750"
ANSIBLE_CONFIG=./Deployment/Cloud/ansible/ansible.cfg ANSIBLE_ROLES_PATH=./Deployment/Cloud/ansible/roles \
  ansible node_db -i ./Deployment/Cloud/inventory/prod/hosts.yml \
  -m ansible.builtin.copy \
  -a "src=$HOME/cloud-backups/<backup-file>.sql.gz dest=<deploy-root>/backups/<backup-file>.sql.gz owner=deploy group=deploy mode=0600"
bash ./Deployment/Cloud/Scripts/restore-db.sh "<deploy-root>/backups/<backup-file>.sql.gz" --confirm "<app-name>/<database-name>"
~~~

Replace the placeholders with current configured values. A gzip check proves archive integrity only. Inspect SQL output for errors, validate recovered records and migration history, and apply any required migrations before resuming app writes. Run app acceptance afterwards; HTTP readiness alone does not prove data recovery.

## Destroy or recreate the stack

Running Hetzner servers continue to incur charges. Use full-stack destroy only to retire the stack, not for routine repair. Destroying it deletes Cloud app data and observability metrics, logs, and traces. First copy needed data off the stack and back up OpenTofu state.

Review the destroy plan without applying it:

~~~bash
bash ./Deployment/Cloud/Scripts/quick-destroy-cloud.sh --plan-only
~~~

If the plan matches the intended stack, run a fresh interactive destroy. Type the exact configured confirmation phrase when prompted:

~~~bash
bash ./Deployment/Cloud/Scripts/quick-destroy-cloud.sh
~~~

The script backs up local state, destroys only OpenTofu-owned resources, and removes generated inventory after success.

To recreate, first review its plan:

~~~bash
bash ./Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh --plan-only
~~~

Then run a fresh interactive recreate and type the configured confirmation phrase when prompted:

~~~bash
bash ./Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh
~~~

It creates billable resources, refreshes generated inventory and GitHub secrets, provisions the nodes, and dispatches Cloud CD. The recreated database and observability stores start empty; migrations are enabled by default for the CD dispatch.

[Cloud target boundaries](README.md)
