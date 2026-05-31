# How To Fork This Repo

Use this guide when you fork the template and want the fork deployed quickly without rebuilding the whole LocalCluster. It focuses on the common case: a new fork running on the same four prepared LocalCluster nodes:

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

Do not rename the LocalCluster nodes. `node-main`, `node-app1`, `node-app2`, and `node-db` are infrastructure roles, not product names.

## 2. Decide Replacement Or Side By Side

Use one of these paths.

| Path | Use it when | What changes |
| --- | --- | --- |
| Side-by-side fork | You want the original app and the fork live on the same four nodes. | Use unique `APP_SLUG`, ports, `DEPLOY_ROOT`, `APP_IMAGE`, `PUBLIC_HOSTNAME`, runner label, database name, and secrets. Reuse the node IPs and usually reuse the same Cloudflare tunnel. |
| Replacement fork | You want the fork to replace the existing app on these nodes. | You may reuse ports and `DEPLOY_ROOT` only after the old app is stopped or cleaned up. Follow the rename or cleanup sections in `Deployment/LocalCluster/HowToDeployLocalCluster.md`. |
| Fresh cluster | You want new machines. | Do not use this guide. Follow `Deployment/LocalCluster/HowToDeployLocalCluster.md` from step 0. |

For the fastest and safest fork demo, use side by side. The existing database and Redis instances can stay untouched, and the fork gets its own PostgreSQL and Redis ports.

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

`App:Name` is used for Data Protection isolation, cache-invalidation channel naming, and authenticator-app issuer names. In deployed LocalCluster app containers it is set from `app_name`, so the least surprising choice is `APP_IDENTITY_NAME=APP_SLUG`. Choose it deliberately and avoid changing it repeatedly after users exist.

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

## 9. Commit And Push The Fork Settings

[CurrentPC]

Run the fast local checks:

```bash
bash ./Deployment/Common/Scripts/validate-common-release.sh
bash ./Deployment/LocalCluster/Scripts/validate-deploy-settings.sh
bash ./Deployment/LocalCluster/Scripts/summary.sh
git diff --check
```

Commit and push:

```bash
git status --short
git add README.md docs/HowToRunLocally.md .env.example
git add BlazorAutoApp/appsettings.json BlazorAutoApp/appsettings.Docker.json
git add Deployment/Common/release.yml Deployment/LocalCluster/inventory/prod/group_vars/all.yml Deployment/LocalCluster/inventory/prod/hosts.yml
# Add any feature, test, simulator, dashboard, or extra docs files you intentionally changed.
git commit -m "Customize template fork identity"
git push
```

Do not commit:

```text
.env
Deployment/LocalCluster/machines.yml
Deployment/LocalCluster/inventory/prod/vault.yml
Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml
artifacts/
```

These are ignored by git and should stay local.

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
vault_ghcr_username: <github username or bot account>
vault_ghcr_token: <classic PAT with read:packages>
vault_cloudflare_tunnel_token: <existing shared tunnel token>
```

For a side-by-side fork, use a new PostgreSQL database name, database password, and Redis password. Reusing the same Cloudflare tunnel token is normal when the fork shares the existing `cloudflared` service.

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

## 15. Run CI

[GitHub]

Run or wait for:

```text
Actions -> CI
```

CI must pass on `main`. It validates deployment settings, builds and tests the solution, builds the EF migration bundle, builds the Docker image, and pushes:

```text
<APP_IMAGE>:<commit-sha>
```

If the GHCR push fails, check:

- `Deployment/Common/release.yml` uses the fork owner and lowercase image path.
- GitHub Actions has permission to write packages.
- The fork is not blocked by an organization policy.

## 16. Deploy The Fork

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

The CD workflow:

- selects the app-specific runner through `LOCALCLUSTER_RUNNER_LABEL`,
- reads `Deployment/Common/release.yml`,
- reads LocalCluster `all.yml`,
- downloads the migration bundle from the successful CI run,
- deploys PostgreSQL and Redis on `node-db`,
- deploys the app containers on `node-app1` and `node-app2`,
- renders Caddy on `node-main`,
- runs acceptance checks,
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

## 18. What Not To Rename For A Fast Fork

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

## 19. Fork Customization Checklist

Before first deploy:

- `README.md` describes the fork.
- `.env.example` uses the fork app name.
- `BlazorAutoApp/appsettings.json` and `BlazorAutoApp/appsettings.Docker.json` use the fork app name.
- `Deployment/Common/release.yml` points to the fork GHCR image and migration bundle.
- `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` has unique side-by-side ports and runtime paths.
- `Deployment/LocalCluster/inventory/prod/hosts.yml` was regenerated for the fork `app_name`.
- `Deployment/LocalCluster/inventory/prod/vault.yml` exists on ControlPC and has no placeholders.
- Cloudflare has a public hostname route to `http://127.0.0.1:80`.
- GitHub has `ANSIBLE_VAULT_PASSWORD`.
- GitHub variables target the app-specific runner label and environment.
- CI passed on `main`.
- CD passed on `main`.
- `acceptance-check.sh` passed.
- `observability-doctor.sh` passed if observability is enabled.

After first deploy:

- Update or remove any remaining Books-specific UI, docs, metrics, dashboards, and simulation code that no longer matches the fork.
- Configure real email delivery before requiring confirmed accounts or relying on password reset email in production.
- Configure real OAuth credentials if the fork uses Google login.
- Revisit rate limits for the real product.
- Remove `InvariantGlobalization` from `BlazorAutoApp.Client/BlazorAutoApp.Client.csproj` if the fork needs culture-specific formatting, parsing, sorting, or localization in the hydrated WebAssembly client.
