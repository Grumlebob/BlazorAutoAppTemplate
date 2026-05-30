# Cloud Scripts

Cloud helper scripts live here.

Implemented local scripts:

- `setup-currentpc-tools.sh` installs the CurrentPC toolchain on apt-based Linux shells.
- `check-currentpc-tools.sh` verifies local tool prerequisites.
- `check-hcloud-token.sh` verifies `HCLOUD_TOKEN` without printing it.
- `read-cloud-setting.sh` reads one committed Cloud setting.
- `validate-cloud-settings.sh` validates committed Cloud settings.
- `summary.sh` prints shared release and Cloud deployment settings.
- `doctor.sh` reports local Cloud deployment state, GitHub CI/CD state, and public health.
- `status-guide.sh` is a backwards-compatible wrapper around `doctor.sh`.
- `prepare-opentofu-tfvars.sh` creates and updates local OpenTofu variables.
- `plan-replace-cloud-servers.sh` creates an explicit OpenTofu server replacement plan for private-network attachment recovery.
- `render-inventory-from-tofu.sh` renders `inventory/prod/hosts.yml` from OpenTofu outputs.
- `render-inventory-from-env.sh` renders CI inventory from GitHub environment secrets.
- `validate-rendered-inventory.sh` validates rendered host IPs, groups, and SSH routing.
- `check-ssh-reachability.sh` waits until Ansible can SSH to every Cloud node.
- `diagnose-cloud-private-network.sh` checks whether `cloud-main` has private-network routing to app/data SSH.
- `reset-cloud-known-hosts.sh` removes stale SSH host keys for current Cloud inventory addresses after server replacement.
- `configure-github-environment.sh` creates the GitHub environment and sets Cloud secrets.
- `check-github-environment.sh` verifies required Cloud GitHub secrets exist.
- `set-temporary-ssh-firewall.sh` updates the dedicated Hetzner temporary SSH firewall.
- `quick-destroy-cloud.sh` destroys the OpenTofu-owned Hetzner Cloud stack to stop billing.
- `quick-recreate-cloud-after-destruction.sh` recreates the Hetzner Cloud stack, refreshes generated configuration, provisions, and dispatches Cloud CD.
- `preflight.sh` validates local deploy prerequisites.
- `provision.sh` runs Cloud host provisioning.
- `deploy.sh` deploys the app and optionally runs migrations.
- `acceptance-check.sh` verifies the deployed Cloud app.
- `observability-capacity-check.sh` verifies Cloud memory/disk headroom before observability deployment.
- `observability-doctor.sh` verifies Cloud observability containers, scrape targets, app telemetry labels, dashboards, cardinality, and OOM state.
- `observability-resource-report.sh` prints Cloud observability memory, disk, and container resource snapshots.
- `open-observability-tunnel.sh` opens a private SSH tunnel to Cloud Grafana on `cloud-main`.
- `backup-db.sh` triggers a PostgreSQL backup on `cloud-db`.
- `restore-db.sh` wraps a guarded PostgreSQL restore on `cloud-db`.

Scripts may use target-independent helpers from `Deployment/Common`. They must not import from `Deployment/LocalCluster`.
