# How To Fork This Repo

Use this guide for fork identity and deployment target selection. The numbered LocalCluster steps then cover a new fork on the same four prepared nodes:

```text
node-main
node-app1
node-app2
node-db
```

The full first-time machine bootstrap guide stays in `Deployment/LocalCluster/HowToDeployLocalCluster.md`. This guide is the shorter fork path after those machines already exist.

Location labels:

```text
[CurrentPC]    your development PC
[ControlPC]    the LocalCluster control machine; normally node-main
[Cloudflare]   the Cloudflare dashboard
[GitHub]       the fork's GitHub repository
```

If a terminal starts from the wrong folder, run this first:

```bash
cd "$(git rev-parse --show-toplevel)"
```

## Choose deployment targets

Start with the [deployment chooser](../Deployment/README.md). Set the GitHub repository variable for the targets you intend to operate:

```bash
gh variable set DEPLOY_TARGETS --body localsinglenode
# A deliberate multi-target example:
gh variable set DEPLOY_TARGETS --body localcluster,localsinglenode
```

| Path | Follow |
| --- | --- |
| One native PC | Shared identity steps 1 and 3–6 below, then the [single-node guide](../Deployment/LocalSingleNode/HowToDeployLocalSingleNode.md) and its [AgentSetup.md](../Deployment/LocalSingleNode/AgentSetup.md); skip LocalCluster topology/SSH steps 2 and 7–8 |
| Prepared four-PC LocalCluster | The numbered steps below |
| Cloud | Shared fork identity and the [Cloud guide](../Deployment/Cloud/HowToDeployCloud.md) |

Keep all target folders. CI still validates them and uses audit/render/smoke entry points under LocalCluster. A disabled target's machine inventory, provisioning, secrets and runtime topology can be ignored. Common release settings are required for every target.

For LocalSingleNode, edit `Deployment/LocalSingleNode/inventory/group_vars/all.yml`: app slug, runtime/backup roots, unique app/database/Redis/LAN HTTP ports and a private Docker subnet that does not overlap the LAN or another app. Keep `observability_enabled: false`. Keep the internal `app_name` consistent in LocalCluster `all.yml` too because common CI still reads that file for its app identity, even in a single-node-only fork. Cloud identity is customized through its guide when enabled. Never put a real node address in tracked settings; facts are detected on the native node.

`Deployment/Common/release.yml` must use your lowercase GHCR owner and image name. Make customization through a branch and PR: local gate first, `build-test-push` on the exact PR head, then merge and require green main validation/publishing. No deployment occurs on merge alone.

If the fork has no registered CI runner, the local setup state machine defers fork edits and CI until the operator's single `--ci-runner` bootstrap command registers one. It sets `CI_RUNNER_LABEL=ci-<app_name>` and `CI_RUNNER_HOST=<node>`; the install user receives root-equivalent Docker group access for local gates and needs a fresh group session. Install other local gate tools in the user's environment as needed. Resume the customization PR once capacity exists; do not call deferred checks complete or substitute a dispatched CI run for main-push provenance. A missing initial main-push CI run is reported as a prerequisite.

The template repository already has CI capacity and keeps it on its existing runner; its single-node demo runner handles CD only. `LOCALSINGLENODE_HOST` has no fallback and must match the native hostname. Status sets it and the app-specific CD label after bootstrap.

## 1. Choose The Fork Identity

Pick these values before editing files. Write them down once and use them consistently.

| Value | Example | Rule |
| --- | --- | --- |
| `APP_SLUG` | `recipes` | Lowercase deployment name. Must start with a letter and use only letters, numbers, or hyphens. |
| `APP_IDENTITY_NAME` | `recipes` | Internal app identity. Use the same value as `APP_SLUG` unless you deliberately add separate display branding. |
| `GITHUB_OWNER` | `your-github-user` | Owner or organization of the fork. |
| `GITHUB_REPO` | `RecipesApp` | GitHub repository name. |
| `APP_IMAGE` | `ghcr.io/your-github-user/recipes` | Must be lowercase and must match the package CI pushes. |
| `PUBLIC_HOSTNAME` | `recipes.example.com` | Hostname inside your Cloudflare zone. |
| `DEPLOY_ROOT` | `/opt/recipes` | Runtime directory on the nodes. Use `/opt/<APP_SLUG>`. |
| `MIGRATION_BUNDLE_NAME` | `recipes-migrate` | Use `<APP_SLUG>-migrate` unless there is a conflict. |
| `APP_PORT` | `8081` | Host port on app nodes. Use `8080` only when no other app uses it. |
| `POSTGRES_PORT` | `5433` | Host port on `node-db`. Use `5432` only when no other app uses it. |
| `REDIS_PORT` | `6380` | Host port on `node-db`. Use `6379` only when no other app uses it. |
| `CLOUDFLARE_TUNNEL_NAME` | `books-prod` | Reuse the existing tunnel name when sharing the current `cloudflared` service on `node-main`. |
| `RUNNER_LABEL` | `localcluster-recipes` | Derived from `APP_SLUG` unless overridden in `all.yml`. |
| `GITHUB_ENVIRONMENT` | `localcluster-recipes` | Optional but recommended for a side-by-side fork. |
| `INVENTORY_DNS_SUFFIX` | empty, or `lan` | Optional `inventory_dns_suffix` in `all.yml`. When set, preflight checks that `<node>.<suffix>` resolves to each inventory IP. Leave it empty if your network has no local DNS names. |

Every node value (LAN IPs, MAC addresses, install users) comes from your fork's own ignored `Deployment/LocalCluster/machines.yml`. Do not copy IPs, DNS names or domains from another deployment; the values committed in this template are the template's own demo deployment.

Do not rename the LocalCluster nodes. `node-main`, `node-app1`, `node-app2`, and `node-db` are infrastructure roles, not product names.

## 2. Decide Replacement Or Side By Side

Use one of these paths.

| Path | Use it when | What changes |
| --- | --- | --- |
| Side-by-side fork | You want the original app and the fork live on the same four nodes. | Use unique `APP_SLUG`, ports, `DEPLOY_ROOT`, `APP_IMAGE`, `PUBLIC_HOSTNAME`, runner label, database name, and secrets. Reuse the node IPs and usually reuse the same Cloudflare tunnel. |
| Replacement fork | You want the fork to replace the existing app on these nodes. | You may reuse ports and `DEPLOY_ROOT` only after the old app is stopped or cleaned up. Follow the rename or cleanup sections in `Deployment/LocalCluster/HowToDeployLocalCluster.md`. |
| Fresh cluster | You want new machines. | Do not use this guide. Follow `Deployment/LocalCluster/HowToDeployLocalCluster.md` from step 0. |

For the fastest and safest fork demo, use side by side. The existing database and Redis instances can stay untouched, and the fork gets its own PostgreSQL and Redis ports.

Apps that share nodes also share host-level services: Docker, Caddy, `cloudflared`, the GitHub runner host and the deployment lock on `node-main`. Keep `cloudflared_version` and other host-level versions in `all.yml` the same in every app on the same nodes, because the last deploy wins. Deploys from different apps never overlap: each takes the shared lock `/tmp/localcluster-deploy.lockdir` on `node-main` and waits for the other to finish.

## 3. Change The Repository Identity

[CurrentPC]

Fork the repository in GitHub, clone your fork, then edit only the fork.

```bash
gh repo clone <GITHUB_OWNER>/<GITHUB_REPO>
cd <GITHUB_REPO>
```

Update the high-level documentation:

```text
README.md
docs/HowToRunLocally.md
```

At minimum, update the first README paragraph so it describes the fork. Do not change project and namespace names just to deploy quickly. The `BlazorAutoApp` project names are internal template names and can remain until you intentionally do a deeper rebrand.

For visible product branding, update UI copy in the feature components you keep or migrate. Do not use `App:Name` as general marketing text; in this template it is an internal app identity.

## 4. Change Local App Settings

[CurrentPC]

Update these files:

```text
.env.example
BlazorAutoApp/appsettings.json
BlazorAutoApp/appsettings.Docker.json
```

Recommended changes:

```env
App__Name=<APP_IDENTITY_NAME>
App__Url=https://localhost:7186
```

```json
"App": {
  "Name": "<APP_IDENTITY_NAME>"
}
```

`App:Name` is used for Data Protection isolation, cache-invalidation channel naming, and authenticator-app issuer names. In deployed app containers it is set from `app_name`, so the least surprising choice is `APP_IDENTITY_NAME=APP_SLUG`. Choose it deliberately and avoid changing it repeatedly after users exist.

Local development uses `.env`, which is ignored by git. After changing `.env.example`, create or update your local `.env` when you want to run locally:

```powershell
Copy-Item .env.example .env -Force
.\Scripts\RunLocal.ps1
```

Only change local host ports in `.env` when your development PC already has a port conflict. Do not edit `docker-compose.yml` for machine-specific local port changes.

## 5. Decide What To Do With The Books Feature

The current product slice is Books. For a fast deployment, you can leave it in place and deploy the fork first. Then migrate real features one slice at a time using:

```text
docs/HowToAddANewFeature.md
```

When replacing Books, update all layers together:

```text
BlazorAutoApp.Core/Features/<Feature>
BlazorAutoApp/Features/<Feature>
BlazorAutoApp.Client/Features/<Feature>
BlazorAutoApp.Test/Features/<Feature>
BlazorAutoApp.Simulation
docs/SimulationGuide.md
docs/ObservabilityGuide.md
Deployment/Common/observability/grafana
```

Keep shared request and response contracts in `BlazorAutoApp.Core`. Keep server behavior in `BlazorAutoApp`. Keep routable client components under `BlazorAutoApp.Client/Features/<Feature>/Routes`. Keep tests in the matching `BlazorAutoApp.Test/Features/<Feature>` tree.

If the fork still uses the Books slice, the Books simulation and Books dashboards are valid. If the fork changes the main domain, update the simulator, metrics, dashboards, and guide text before relying on observability demos.

Cloud deployment files remain in the repository. They are not required for a fast LocalCluster fork, but CI still lint-checks and validates their shape. Do not run `CD - Cloud` until you intentionally customize `Deployment/Cloud/HowToDeployCloud.md`, `Deployment/Cloud/inventory/prod/group_vars/all.yml`, OpenTofu settings, Cloud secrets, and Cloud DNS for the fork.

## 6. Change Shared Release Settings

[CurrentPC]

Edit:

```text
Deployment/Common/release.yml
```

Example:

```yaml
app_image: ghcr.io/<GITHUB_OWNER>/<APP_SLUG>
migration_bundle_name: <APP_SLUG>-migrate
migration_runtime: linux-x64
```

Rules:

- `app_image` must be lowercase.
- `migration_runtime` stays `linux-x64` for the current LocalCluster.
- `migration_artifact_name` is derived automatically as `<migration_bundle_name>-<migration_runtime>`.
- Do not duplicate these values in LocalCluster `all.yml`.

Validate:

```bash
bash ./Deployment/Common/Scripts/validate-common-release.sh
```

## 7. Change LocalCluster Settings

[CurrentPC]

Edit:

```text
Deployment/LocalCluster/inventory/prod/group_vars/all.yml
```

Side-by-side example:

```yaml
app_name: <APP_SLUG>
app_port: 8081
postgres_port: 5433
redis_port: 6380
public_hostname: <PUBLIC_HOSTNAME>
deploy_root: /opt/<APP_SLUG>
cloudflare_tunnel_name: <EXISTING_TUNNEL_NAME>
cloudflared_version: 2026.5.2

observability_enabled: true
observability_root: /opt/<APP_SLUG>-observability
observability_docker_network: <APP_SLUG>_observability
observability_trace_sample_ratio: 0.1

observability_grafana_port: 3001
observability_alertmanager_port: 9094
observability_prometheus_port: 9091
observability_loki_port: 3101
observability_tempo_http_port: 3201
observability_tempo_otlp_grpc_port: 4319
observability_tempo_otlp_http_port: 4320
observability_alloy_http_port: 12346
observability_node_exporter_port: 9101
observability_postgres_exporter_port: 9188
observability_redis_exporter_port: 9122

observability_prometheus_retention_time: 7d
observability_prometheus_retention_size: 6GB
observability_loki_retention_period: 7d
observability_tempo_retention_period: 24h
```

If this fork is the only app on the four nodes, you can keep the default app, database, Redis, and observability ports. If another app already runs there, every published port in `all.yml` must be unique.

If you do not want observability for the side-by-side fork yet, set `observability_enabled: false` instead of inventing partial observability settings. When observability is enabled, its published ports also need to be unique because the backend runs on `node-main` and agents/exporters run on the existing nodes.

Validate:

```bash
bash ./Deployment/LocalCluster/Scripts/validate-deploy-settings.sh
bash ./Deployment/LocalCluster/Scripts/summary.sh
```

## 8. Reuse The Existing Four Nodes

[CurrentPC]

The generated inventory must use the fork's `app_name`, because that controls the deploy SSH key path:

```yaml
ansible_ssh_private_key_file: ~/.ssh/<APP_SLUG>_deploy
```

If you have the current LocalCluster machine values, create:

```text
Deployment/LocalCluster/machines.yml
```

Use `Deployment/LocalCluster/machines.example.yml` as the template. `machines.yml` is ignored by git.

The best source is the already-deployed repository on the ControlPC. Copy its ignored `Deployment/LocalCluster/machines.yml` into the fork checkout if it exists. If that file is gone, use the existing tracked `Deployment/LocalCluster/inventory/prod/hosts.yml` to recover the four LAN IPs, then fill the MAC addresses and install usernames from your router notes or the original first-deployment notes.

If the machine values exist only on the ControlPC, it is fine to do this inventory-generation step on the ControlPC instead. The important rule is that the generated `hosts.yml` must be committed to the fork before GitHub CD runs.

Then generate the tracked production inventory:

```bash
bash ./Deployment/LocalCluster/Scripts/generate-inventory.sh
```

Commit this generated file:

```text
Deployment/LocalCluster/inventory/prod/hosts.yml
```

Do not rerun `bootstrap-node.sh` or `prepare-fresh-linux-machines.sh` for a side-by-side fork on already-prepared nodes. Those scripts are for first-time machine bootstrap.

Seed and verify SSH host keys before the first deploy. Manual deploy, maintenance and lock tools use strict host-key checking and refuse unknown keys. On the ControlPC, for each node IP in `hosts.yml`:

```bash
host_key_candidate="$(mktemp)"
ssh-keyscan -T 10 -t ed25519 -H <node-ip> > "$host_key_candidate"
ssh-keygen -lf "$host_key_candidate"
```

Compare that fingerprint with `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` on the node's own console. Append the same scanned key only after the fingerprints match. If they differ, stop. Skip nodes already in `known_hosts` with the verified key.

```bash
mkdir -p ~/.ssh
cat "$host_key_candidate" >> ~/.ssh/known_hosts
rm -f "$host_key_candidate"
```

## 9. Review And Merge The Fork Settings

[CurrentPC]

Before the first commit, check that Git has an author identity:

```bash
git var GIT_AUTHOR_IDENT
```

If Git reports "Author identity unknown", set the identity for this checkout. Use your GitHub email or your GitHub no-reply address:

```bash
git config user.name "Your Name"
git config user.email "your-email@example.com"
```

Run the complete [local gate](Test.md#local-gate), including Docker-backed tests, before pushing. These setting checks supplement that gate:

```bash
bash ./Deployment/Common/Scripts/validate-common-release.sh
bash ./Deployment/LocalCluster/Scripts/validate-deploy-settings.sh
bash ./Deployment/LocalCluster/Scripts/summary.sh
git diff --check
```

Commit explicit paths on your customization branch and push that branch:

```bash
git switch -c fork/customize-template
git status --short
git add README.md docs/HowToRunLocally.md .env.example
git add BlazorAutoApp/appsettings.json BlazorAutoApp/appsettings.Docker.json
git add Deployment/Common/release.yml Deployment/LocalCluster/inventory/prod/group_vars/all.yml Deployment/LocalCluster/inventory/prod/hosts.yml
# Add any feature, test, simulator, dashboard, or extra docs files you intentionally changed.
git commit -m "Customize template fork identity"
git push --set-upstream origin fork/customize-template
gh pr create --base main --head fork/customize-template
```

Merge only after `build-test-push` succeeds on that exact head. Require successful main validation and publishing before deployment; record the squash commit and CI run. If your single-node changes also edit its settings, stage that explicit path too.

Do not commit:

```text
.env
Deployment/LocalCluster/machines.yml
Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml
artifacts/
```

These are ignored by git and should stay local. LocalCluster `vault.yml` is different: it is tracked because CD needs the encrypted file. Never commit plaintext vault contents or the vault password. Create the fork's own encrypted vault in section 12 and commit it only after setup-secrets.sh succeeds.

## 10. Prepare The Fork On The Control Machine

[ControlPC]

Clone or update the fork on the control machine:

```bash
export LOCALCLUSTER_REPO=<GITHUB_OWNER>/<GITHUB_REPO>
export LOCALCLUSTER_DIR="${LOCALCLUSTER_REPO##*/}"

if [ ! -d "$LOCALCLUSTER_DIR/.git" ]; then
  gh repo clone "$LOCALCLUSTER_REPO" "$LOCALCLUSTER_DIR"
fi

cd "$LOCALCLUSTER_DIR"
git pull --ff-only
gh repo view --json nameWithOwner,url --jq '"repo=\(.nameWithOwner) url=\(.url)"'
```

Install required tools, validate settings, and create this fork's deploy SSH key:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-control-machine.sh
```

Expected key:

```text
~/.ssh/<APP_SLUG>_deploy
```

For a side-by-side fork, install this fork's deploy key onto the already-prepared nodes by using an existing app key that already works:

```bash
bash ./Deployment/LocalCluster/Scripts/prepare-existing-localcluster-app.sh --existing-key ~/.ssh/<EXISTING_APP_SLUG>_deploy
```

Expected final line:

```text
existing LocalCluster nodes are ready for app: <APP_SLUG>
```

Then check the deployment state:

```bash
ansible all -i Deployment/LocalCluster/inventory/prod/hosts.yml -m ping
bash ./Deployment/LocalCluster/Scripts/validate-side-by-side.sh
```

Do not run `doctor.sh deploy` yet; it expects the encrypted vault created in step 12. If `validate-side-by-side.sh` reports a collision, fix `all.yml`, regenerate `hosts.yml` if needed, commit, push, and pull on the ControlPC before continuing.

## 11. Add The Cloudflare Public Hostname

[Cloudflare]

For the default shared LocalCluster tunnel design, add the fork hostname to the existing tunnel:

```text
Zero Trust -> Networks -> Tunnels -> <CLOUDFLARE_TUNNEL_NAME> -> Public Hostnames -> Add a public hostname
```

Use:

```text
Subdomain: <PUBLIC_HOSTNAME subdomain>
Domain:    <PUBLIC_HOSTNAME domain>
Type:      HTTP
URL:       127.0.0.1:80
```

Example for `recipes.example.com`:

```text
Subdomain: recipes
Domain:    example.com
Type:      HTTP
URL:       127.0.0.1:80
```

Do not point Cloudflare directly at app, PostgreSQL, Redis, Grafana, Prometheus, Loki, Tempo, or exporter ports. The tunnel should enter through Caddy on `node-main` at `http://127.0.0.1:80`; Caddy then routes by `PUBLIC_HOSTNAME`.

## 12. Create The Fork Vault

[ControlPC]

For a new fork, the inherited encrypted vault uses the upstream repository's password. Remove only that inherited file before setup; the script creates a new vault from vault.example.yml with your chosen password. Do not remove a vault already created for your own fork.

Create or edit the encrypted vault:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-secrets.sh
```

The vault contains:

```yaml
vault_postgres_user: <APP_SLUG>_app
vault_postgres_password: <strong unique password>
vault_postgres_db: <APP_SLUG>
vault_redis_password: <strong unique password>
vault_cloudflare_tunnel_token: <existing shared tunnel token>
```

No GitHub token is stored in the vault. CD lets the nodes pull the image with the workflow's own `GITHUB_TOKEN`. Manual deploys with `deploy.sh` take registry credentials from `GHCR_USERNAME`/`GHCR_TOKEN` or an authenticated `gh` CLI; add the optional `vault_ghcr_username` and `vault_ghcr_token` keys only if neither is available and the image is private.

For a side-by-side fork, use a new PostgreSQL database name, database password, and Redis password. Reusing the same Cloudflare tunnel token is normal when the fork shares the existing `cloudflared` service.

After setup-secrets.sh succeeds, commit the encrypted vault so CD can read it:

```bash
git add Deployment/LocalCluster/inventory/prod/vault.yml
git commit -m "Configure encrypted fork deployment vault"
git push
```

`setup-secrets.sh` also tries to set the GitHub repository secret:

```text
ANSIBLE_VAULT_PASSWORD
```

If GitHub CLI cannot set it automatically, set it manually in:

```text
[GitHub] Repository -> Settings -> Secrets and variables -> Actions -> Secrets
```

Now run the deploy preflight from the ControlPC:

```bash
bash ./Deployment/LocalCluster/Scripts/doctor.sh deploy
bash ./Deployment/LocalCluster/Scripts/preflight.sh deploy
```

These checks may ask for the Ansible Vault password. Use the same password you used when creating `Deployment/LocalCluster/inventory/prod/vault.yml`. This is the point that contacts the nodes and catches live side-by-side port collisions, including observability ports.

## 13. Install The Fork Runner

[ControlPC]

GitHub CLI must be authenticated to the fork repository with permission to create self-hosted runners:

```bash
gh auth status
gh repo view --json nameWithOwner,url --jq '"repo=\(.nameWithOwner) url=\(.url)"'
```

Install a GitHub Actions runner for this fork on `node-main`:

```bash
bash ./Deployment/LocalCluster/Scripts/install-github-runner.sh
```

The runner directory is:

```text
/opt/actions-runner-<APP_SLUG>
```

Expected labels:

```text
localcluster
localcluster-<APP_SLUG>
```

Check it:

```bash
bash ./Deployment/LocalCluster/Scripts/check-github-runner.sh
```

## 14. Configure GitHub Actions

[GitHub]

Enable Actions for the fork if GitHub asks.

Create the deployment environment:

```text
Repository -> Settings -> Environments -> New environment
```

For a side-by-side fork, recommended name:

```text
localcluster-<APP_SLUG>
```

Configure the environment rules:

```text
Deployment branches and tags: Selected branches and tags
Allowed branch: main
```

Set repository variables:

```text
Repository -> Settings -> Secrets and variables -> Actions -> Variables
```

Recommended side-by-side variables:

```text
LOCALCLUSTER_RUNNER_LABEL=localcluster-<APP_SLUG>
LOCALCLUSTER_ENVIRONMENT=localcluster-<APP_SLUG>
```

These are GitHub repository variables, not Ansible variables. GitHub resolves `runs-on` and `environment` before it checks out the repository.

Confirm the repository secret exists:

```text
ANSIBLE_VAULT_PASSWORD
```

Make sure the fork can publish packages. In GitHub, check:

```text
Repository -> Settings -> Actions -> General -> Workflow permissions
```

The repository or organization must allow the CI workflow's requested `packages: write` permission. If an organization policy blocks package writes, CI will fail at the GHCR push step.

Optional secret for Dependabot auto-merge:

```text
GH_TOKEN = fine-grained personal access token for this repository with
           Contents: write, Pull requests: write, Workflows: write
```

Without it, auto-merge still works for most Dependabot pull requests. It only cannot refresh an out-of-date Dependabot branch that changes workflow files; the run summary then says so and nothing else breaks.

## 15. Run CI

[GitHub]

Run or wait for:

```text
Actions -> CI
```

CI has two jobs:

- `validate` checks every pull request and every `main` push: deployment settings and audit, script tests, build, tests (with Docker), Tailwind output, and for pull requests a Docker image plus an HTTP and browser smoke test. Pull requests never push images. On pull requests this job is the required `build-test-push` check.
- `publish-main` runs only for `main` after `validate` succeeds, and carries the `build-test-push` name there. It builds and smoke-tests the image, pushes `<APP_IMAGE>:<commit-sha>`, and uploads the migration bundle together with `release-manifest.json`. The manifest binds the commit, the CI run and attempt, the image digest and the migration IDs, and CD checks every one of them.

CI must pass on `main` before you deploy.

If the GHCR push fails, check:

- `Deployment/Common/release.yml` uses the fork owner and lowercase image path.
- GitHub Actions has permission to write packages.
- The fork is not blocked by an organization policy.

## 16. Deploy The Fork

CD requires a successful main `push` CI run with a successful `publish-main` job on the same run attempt. A manual `workflow_dispatch` CI run does not satisfy this provenance gate.

[GitHub]

Run:

```text
Actions -> CD - Deploy LocalCluster -> Run workflow
```

Use:

```text
Branch: main
run_migrations: true
```

Use `run_migrations: true` for the first deploy. The database is new for a side-by-side fork, so migrations must run.

Optional input `target_sha`: deploy an earlier commit, for example to roll back. It must be a full commit SHA that is already on `main`; empty deploys the current `main` commit.

The CD workflow:

- selects the app-specific runner through `LOCALCLUSTER_RUNNER_LABEL`,
- refuses commits that are not on `main`,
- finds the newest successful `main` CI run for the commit,
- downloads that run's release artifact and validates `release-manifest.json` against the registry digest and the migration bundle,
- reads `Deployment/Common/release.yml` and LocalCluster `all.yml`,
- stages the exact image digest on both app nodes before stopping anything,
- deploys PostgreSQL and Redis on `node-db` and runs migrations when requested,
- deploys the app containers on `node-app1` and `node-app2` one at a time,
- renders Caddy and `cloudflared` on `node-main`,
- runs acceptance checks and verifies that every app node runs the released digest,
- runs the observability doctor when observability is enabled.

## 17. Verify The Fork

[ControlPC]

After CD succeeds:

```bash
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
if [ "$(bash ./Deployment/LocalCluster/Scripts/read-deploy-setting.sh observability_enabled)" = "true" ]; then
  bash ./Deployment/LocalCluster/Scripts/observability-doctor.sh
fi
bash ./Deployment/LocalCluster/Scripts/list-deployed-apps.sh
```

To confirm by hand which image every app node runs, pass the image and the digest from the CD run summary:

```bash
bash ./Deployment/LocalCluster/Scripts/verify-release-identity.sh <APP_IMAGE> sha256:<digest>
```

[CurrentPC]

Open the public app:

```text
https://<PUBLIC_HOSTNAME>
```

Open Grafana through an SSH tunnel:

```bash
CONTROLPC_SSH_TARGET=<your-control-user>@node-main bash ./Deployment/LocalCluster/Scripts/open-observability-tunnel.sh
```

Then open:

```text
http://127.0.0.1:3000
```

The script maps your local port `3000` to the fork's configured remote `observability_grafana_port`. If local port `3000` is already in use, pass another local port:

```bash
CONTROLPC_SSH_TARGET=<your-control-user>@node-main bash ./Deployment/LocalCluster/Scripts/open-observability-tunnel.sh 3001
```

Then open `http://127.0.0.1:3001`. If `node-main` does not resolve from CurrentPC, use the node-main LAN IP in `CONTROLPC_SSH_TARGET`.

## 18. Runner And Cluster Maintenance

`.github/workflows/localcluster-docker-maintenance.yml` cleans up `node-main` and the cluster under the shared deployment lock. It ships manual-only; to run it daily, uncomment its `schedule:` block in your fork.

It deletes only:

- old Actions runner versions, stale `_work/_update` and `_work/_temp` entries, and old runner diagnostic logs,
- this repository's CI containers and networks whose run finished more than 24 hours ago,
- dangling images labelled by this repository's CI, and old tags of this app's image that no container uses,
- the same app-image residue on the app and database nodes,
- release artifacts beyond the newest two, except those of the last two successful deploys.

It never deletes Docker volumes, database data, backups, `/opt/<app>` data, another app's images or containers, or anything while a deploy holds the lock. Exit codes: `0` done, `1` failure, `2` still below the disk reserve, `75` deferred because protected candidates were skipped.

## 19. What Not To Rename For A Fast Fork

Do not rename these just to deploy quickly:

```text
BlazorAutoApp.sln
BlazorAutoApp/
BlazorAutoApp.Client/
BlazorAutoApp.Core/
BlazorAutoApp.Test/
BlazorAutoApp.Simulation/
.github/workflows/ci.yml
.github/workflows/cd-localcluster.yml
node-main/node-app1/node-app2/node-db
```

Renaming projects and namespaces is a larger refactor. It touches solution files, project references, namespaces, tests, Dockerfile paths, GitHub workflows, docs, and scripts. Do it after the fork is live unless the new repository must have a complete internal rebrand before first deploy.

## 20. Fork Customization Checklist

Before first deploy:

- `README.md` describes the fork.
- `.env.example` uses the fork app name.
- `BlazorAutoApp/appsettings.json` and `BlazorAutoApp/appsettings.Docker.json` use the fork app name.
- `Deployment/Common/release.yml` points to the fork GHCR image and migration bundle.
- `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` has unique side-by-side ports and runtime paths.
- `Deployment/LocalCluster/inventory/prod/hosts.yml` was regenerated for the fork `app_name`.
- `Deployment/LocalCluster/inventory/prod/vault.yml` exists on ControlPC and has no placeholders.
- Cloudflare has a public hostname route to `http://127.0.0.1:80`.
- GitHub has `ANSIBLE_VAULT_PASSWORD`. No GHCR token is needed.
- `~/.ssh/known_hosts` on the ControlPC has verified host keys for every node.
- GitHub variables target the app-specific runner label and environment.
- CI passed on `main`, and the run has a release artifact with `release-manifest.json`.
- CD passed on `main`, including the release identity check.
- `acceptance-check.sh` passed.
- `observability-doctor.sh` passed if observability is enabled.

After first deploy:

- Update or remove any remaining Books-specific UI, docs, metrics, dashboards, and simulation code that no longer matches the fork.
- Configure real email delivery before requiring confirmed accounts or relying on password reset email in production.
- Configure real OAuth credentials if the fork uses Google login.
- Revisit rate limits for the real product.
- Remove `InvariantGlobalization` from `BlazorAutoApp.Client/BlazorAutoApp.Client.csproj` if the fork needs culture-specific formatting, parsing, sorting, or localization in the hydrated WebAssembly client.
