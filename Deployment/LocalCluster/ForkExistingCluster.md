# Fork Onto An Existing LocalCluster

Use this route after [shared fork identity](../../docs/HowToForkThisRepo.md) when the four nodes already exist and are prepared. For fresh nodes, use [LocalCluster setup](Setup.md). Single-node and Cloud forks use their own target guides.

**Second-fork flow on already-prepared nodes:** choose side by side or replacement, set unique app values, generate inventory, install this fork's deploy key, configure its vault and runner, then deploy after main CI publishes a release.

## Choose side by side or replacement

If another LocalCluster app already runs on these nodes, choose side by side or stop and clean up the existing app before reusing its identity or paths. For replacement, follow [Replace an app identity](Operations.md#replace-an-app-identity) and decide how to retain or migrate data first.

For a second fork on the same nodes, do not reuse these values from the first app:

- `app_name`, `app_image`, and `migration_bundle_name`
- App, database, and Redis ports; `deploy_root`; `public_hostname`
- Runner name and label
- Database and Redis credentials

The second fork normally reuses the same machine IPs, `cloudflare_tunnel_name`, and Cloudflare tunnel token. Apps sharing the tunnel must use the same Cloudflare account. See [LocalCluster settings](Settings.md#shared-host-choices) for uniqueness and defaults.

## Configure and commit the fork

In Deployment/Common/release.yml, set a unique image and migration bundle. In Deployment/LocalCluster/inventory/prod/group_vars/all.yml, choose unique app identity, ports, hostname, and runtime root. Keep Cloudflared version consistent with apps on the same nodes.

Create ignored Deployment/LocalCluster/machines.yml from machines.example.yml if needed. Use the existing cluster's IPs, MACs, and install users. Do not copy example addresses or another environment's values. Do not rerun `bootstrap-node.sh` or `prepare-fresh-linux-machines.sh` for already-prepared nodes.

Generate the fork's inventory and validate the target:

```bash
bash ./Deployment/LocalCluster/Scripts/generate-inventory.sh
bash ./Deployment/LocalCluster/Scripts/validate-deploy-settings.sh
bash ./Deployment/LocalCluster/Scripts/summary.sh
bash ./Deployment/LocalCluster/Scripts/validate-side-by-side.sh
```

Commit the intended release settings, app settings, and generated hosts.yml before GitHub CD runs. Keep machines.yml and bootstrap-hosts.yml ignored. Run the required local gate before pushing code changes.

## Prepare the control machine and deploy key

On the control machine, clone the fork or switch an existing checkout to its settings branch. Confirm GitHub CLI identifies the fork. Review [control-machine setup](Setup.md#1-set-up-the-control-machine), then run:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-control-machine.sh
```

Before accepting any node key, follow [SSH host trust](../Common/SshTrust.md). Set EXISTING_APP_SLUG to an app whose deploy key already works, then install this fork's key:

```bash
EXISTING_APP_SLUG="<existing-app-slug>"
bash ./Deployment/LocalCluster/Scripts/prepare-existing-localcluster-app.sh \
  --existing-key "$HOME/.ssh/${EXISTING_APP_SLUG}_deploy"
```

This adds the new deploy key without reinstalling packages, Docker, or node configuration. Continue only after this fork's deploy key is installed on the nodes. Verify access and app ownership:

```bash
ansible all -i Deployment/LocalCluster/inventory/prod/hosts.yml -m ping
bash ./Deployment/LocalCluster/Scripts/list-deployed-apps.sh
bash ./Deployment/LocalCluster/Scripts/validate-side-by-side.sh
```

If validation reports a collision, fix settings, regenerate and commit hosts.yml, push the branch, and update the control-machine checkout before continuing.

## Configure runner and first release

Before the first PR, ensure a self-hosted runner for this fork is online. If no runner is inherited, use the ordered [runner setup phase](Setup.md#10-install-the-github-actions-runner). Set CI_RUNNER_LABEL, LOCALCLUSTER_RUNNER_LABEL, and CI_RUNNER_HOST before opening the PR. Set GitHub Actions workflow permission to Read and write permissions so main CI can publish the image.

Require build-test-push to pass on the exact PR head, then merge. Main CI publishes the release. Follow [the shared release contract](../Common/ReleaseContract.md) before deployment.

## Reuse the tunnel and create the vault

Add this fork's `public_hostname` to the existing Cloudflare tunnel. In the Cloudflare dashboard, open the existing tunnel and add a public hostname with these values:

```text
Subdomain: <public-hostname subdomain>
Domain:    <public-hostname domain>
Type:      HTTP
URL:       127.0.0.1:80
```

Caddy routes by hostname. Do not expose app, database, Redis, Grafana, or exporter ports through the tunnel.

Create the fork's encrypted vault:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-secrets.sh
```

Use unique database and Redis credentials. Reuse the tunnel token only when intentionally sharing the existing tunnel. Commit encrypted vault.yml after setup succeeds; store its password as GitHub secret ANSIBLE_VAULT_PASSWORD. Never commit plaintext secrets.

## Configure the environment and deploy

Create the deployment environment and allow selected branch main. Confirm the GitHub secret exists. Runner variables must already be set before the PR.

Run deploy preflight from the control machine:

```bash
bash ./Deployment/LocalCluster/Scripts/doctor.sh deploy
bash ./Deployment/LocalCluster/Scripts/preflight.sh deploy
```

After main CI publishes the fork's release, run CD - Deploy LocalCluster from main. Use run_migrations=true for the new database and leave target_sha empty to use current main. Verify:

```bash
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
bash ./Deployment/LocalCluster/Scripts/list-deployed-apps.sh
```

For routine releases, backup, restore, and lock recovery, use [LocalCluster operations](Operations.md). For runner and Docker cleanup, follow [Runner And Docker Storage Maintenance](Operations.md#runner-and-docker-storage-maintenance).
