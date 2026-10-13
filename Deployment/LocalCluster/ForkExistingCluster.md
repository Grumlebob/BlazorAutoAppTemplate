# Fork Onto An Existing LocalCluster

Use this route after [shared fork identity](../../docs/HowToForkThisRepo.md) when the four LocalCluster nodes already exist and are prepared. It covers a new app on those nodes. For a fresh cluster, use [HowToDeployLocalCluster.md](HowToDeployLocalCluster.md). A single-node or Cloud fork follows its own target guide.

Run repository commands from the fork checkout root.

**Second-fork flow on already-prepared nodes:** choose side by side or replacement, commit unique app settings and generated inventory, prepare the fork's control key, add the fork to the existing tunnel, configure its vault and runner, then deploy after main CI publishes a release.

## Choose side by side or replacement

If another LocalCluster app already runs on these nodes, choose side by side or stop and clean up the existing app before reusing its identity and paths. For a replacement, review [Rename An Existing App Identity](HowToDeployLocalCluster.md#optional-rename-an-existing-app-identity) and decide how to retain or migrate its data first. Side by side is the normal fork path: each app owns its settings, runtime root, database, Redis credentials, Caddy site, runner, and published ports. Docker, Caddy, `cloudflared`, the runner host, and the deployment lock on `node-main` are shared.

For a second fork on the same nodes, do not reuse these values from the first app:

- `app_name`, `app_image`, and `migration_bundle_name`
- `app_port`, `postgres_port`, `redis_port`, and `deploy_root`
- `public_hostname`
- GitHub runner name and label derived from `app_name`
- PostgreSQL database name and the app's database and Redis passwords

The second fork normally reuses the same machine IPs and `Deployment/LocalCluster/machines.yml` values, `cloudflare_tunnel_name`, and Cloudflare tunnel token. All apps using the existing `cloudflared` service must use a tunnel in the same Cloudflare account. A separate account or tunnel on the same `node-main` needs a custom multi-service design.

## Configure and push the fork branch

In `Deployment/Common/release.yml`, set the lowercase `app_image` and a unique `migration_bundle_name`; keep `migration_runtime: linux-x64` for this target. In `Deployment/LocalCluster/inventory/prod/group_vars/all.yml`, set `app_name`, `app_port`, `postgres_port`, `redis_port`, `public_hostname`, `deploy_root`, and the existing `cloudflare_tunnel_name`. Give the app unique published ports and a unique runtime root. Keep `cloudflared_version` consistent with other apps on the same nodes. If observability is enabled, its published ports and runtime paths must also be unique; otherwise set `observability_enabled: false`. See [LocalCluster settings](HowToDeployLocalCluster.md#2-confirm-shared-release-and-localcluster-settings) for their full meanings.

Create or update the ignored `Deployment/LocalCluster/machines.yml` using addresses, MACs, and install users for this same cluster. If it does not exist, copy `Deployment/LocalCluster/machines.example.yml` first. You may recover IPs from the existing LocalCluster inventory on these nodes. Do not copy demo addresses or another environment's values. Do not rerun `bootstrap-node.sh` or `prepare-fresh-linux-machines.sh` for already-prepared nodes. Before using a manual SSH path, follow [SSH host trust](../Common/SshTrust.md) and verify each host key independently.

Generate the fork's production inventory:

```bash
bash ./Deployment/LocalCluster/Scripts/generate-inventory.sh
```

Run the local gate before pushing changes. Create a branch, stage only intended files, and push the settings branch without opening a PR yet:

```bash
git switch -c fork/customize-template
git status --short
git add README.md docs/HowToRunLocally.md .env.example
git add BlazorAutoApp/appsettings.json BlazorAutoApp/appsettings.Docker.json
git add Deployment/Common/release.yml Deployment/LocalCluster/inventory/prod/group_vars/all.yml
git add Deployment/LocalCluster/inventory/prod/hosts.yml
git commit -m "Customize fork identity"
git push --set-upstream origin fork/customize-template
```

Add any frontend, feature, test, or documentation files you intentionally changed. Keep `.env`, `machines.yml`, `bootstrap-hosts.yml`, build artifacts, plaintext secrets, and vault passwords out of Git. The generated `hosts.yml` and settings must be committed before GitHub CD runs.

## Prepare the control machine and CI runner before the PR

On the control machine, clone the fork and check out the settings branch:

```bash
GITHUB_OWNER="your-owner"
GITHUB_REPO="your-repo"
gh repo clone "$GITHUB_OWNER/$GITHUB_REPO"
cd "$GITHUB_REPO"
git fetch origin fork/customize-template
git switch --track -c fork/customize-template origin/fork/customize-template
gh repo view --json nameWithOwner,url
```

For an existing checkout, fetch and switch to the same branch. Review the [control-machine setup](HowToDeployLocalCluster.md#1-set-up-the-control-machine), then create this fork's deploy key:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-control-machine.sh
```

Follow [SSH host trust](../Common/SshTrust.md) before connecting to any node whose key is not already verified. Set `EXISTING_APP_SLUG` to an app whose deploy key already works on these nodes, then install the new key:

```bash
EXISTING_APP_SLUG="existing-app"
bash ./Deployment/LocalCluster/Scripts/prepare-existing-localcluster-app.sh \
  --existing-key "$HOME/.ssh/${EXISTING_APP_SLUG}_deploy"
```

This does not upgrade packages, reboot nodes, reinstall Docker, or rotate secrets. It adds this fork's deploy key to the `deploy` user. Continue only after this fork's deploy key is installed on the nodes, then verify access and collision checks:

```bash
ansible all -i Deployment/LocalCluster/inventory/prod/hosts.yml -m ping
bash ./Deployment/LocalCluster/Scripts/list-deployed-apps.sh
bash ./Deployment/LocalCluster/Scripts/validate-side-by-side.sh
```

If validation reports a collision, fix `all.yml`, regenerate and commit `hosts.yml`, push the branch, and pull it onto the control machine before continuing.

CI uses `CI_RUNNER_LABEL`, then `LOCALCLUSTER_RUNNER_LABEL`, then the template default. Install this fork's LocalCluster runner before opening a PR so its checks have an online runner:

```bash
bash ./Deployment/LocalCluster/Scripts/install-github-runner.sh
bash ./Deployment/LocalCluster/Scripts/check-github-runner.sh
RUNNER_LABEL="$(bash ./Deployment/LocalCluster/Scripts/read-deploy-setting.sh runner_label)"
gh variable set LOCALCLUSTER_RUNNER_LABEL --body "$RUNNER_LABEL"
gh variable set CI_RUNNER_LABEL --body "$RUNNER_LABEL"
gh variable set CI_RUNNER_HOST --body node-main
```

Set `Workflow permissions: Read and write permissions` in the repository's Actions settings so the main CI run can publish the image. The workflow checks that `CI_RUNNER_HOST` matches the runner host. Do not proceed while PR checks would remain queued for lack of runner capacity.

## Run CI and merge the settings

Open a PR from `fork/customize-template` to `main` only after the runner is online. Require `build-test-push` to pass on the exact PR head, then merge. The main push runs CI and publishes the first release. Read the [shared release contract](../Common/ReleaseContract.md) for the qualifying run, attempt, artifact, image, profile, and migration checks.

After merge, update the control-machine checkout:

```bash
git switch main
git pull --ff-only
```

## Reuse the tunnel and create the fork vault

Add this fork's `public_hostname` to the existing Cloudflare tunnel. In the Cloudflare dashboard, open the existing tunnel and add a public hostname with these values:

```text
Subdomain: <PUBLIC_HOSTNAME subdomain>
Domain:    <PUBLIC_HOSTNAME domain>
Type:      HTTP
URL:       127.0.0.1:80
```

Caddy on `node-main` routes by hostname; do not expose app, database, Redis, Grafana, or exporter ports through the tunnel.

Create the fork's encrypted vault with:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-secrets.sh
```

For the inherited template vault, remove only that inherited encrypted file before the first setup. Do not remove a vault already created for this fork. Use a new PostgreSQL database name, database password, and Redis password. Reuse the tunnel token only when intentionally sharing the existing tunnel. Commit the encrypted `Deployment/LocalCluster/inventory/prod/vault.yml` after setup succeeds, and store its password in the fork's `ANSIBLE_VAULT_PASSWORD` GitHub secret. The vault password is secret and must not be committed. If `setup-secrets.sh` cannot set the GitHub secret, add `ANSIBLE_VAULT_PASSWORD` under the repository's Actions secrets.

Before dispatching CD, run the live deployment preflight from the control machine:

```bash
bash ./Deployment/LocalCluster/Scripts/doctor.sh deploy
bash ./Deployment/LocalCluster/Scripts/preflight.sh deploy
```

## Configure the deployment environment and deploy

In **Repository → Settings → Environments**, create the deployment environment and allow selected branch `main`. Set `LOCALCLUSTER_ENVIRONMENT=localcluster-<APP_SLUG>` only when using a separate environment from the default. `LOCALCLUSTER_RUNNER_LABEL` was set before the PR so CI could start. Confirm `ANSIBLE_VAULT_PASSWORD` exists under Actions secrets.

After main CI publishes the fork's release, start `CD - Deploy LocalCluster` from `main`:

```text
Branch: main
run_migrations: true
target_sha: leave empty to use the current main commit
```

Use `run_migrations: true` for the new database. CD deploys only a selected commit on `main` with a qualifying successful publishing attempt. Before migration, the workflow validates its release manifest, image digest and labels, profiles, and migration bundle.

Verify the deployment:

```bash
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
bash ./Deployment/LocalCluster/Scripts/list-deployed-apps.sh
```

When observability is enabled, also run:

```bash
bash ./Deployment/LocalCluster/Scripts/observability-doctor.sh
```

Open `https://<PUBLIC_HOSTNAME>`. For routine releases, backup, restore, and lock handling, use [Routine Deployments](HowToDeployLocalCluster.md#routine-deployments). For runner and Docker cleanup, follow [Runner And Docker Storage Maintenance](HowToDeployLocalCluster.md#runner-and-docker-storage-maintenance).
