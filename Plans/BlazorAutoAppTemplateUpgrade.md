# BlazorAutoAppTemplate Upgrade: Backport ImprovedDb Lessons

Status: executing (2026-10-09). D15 and P1–P12 are merged. P13a shared building blocks are merged and main validation/publishing are green at `b12dcd5502bce4340d21dad3a2a546a2c4ac4e8b`. P12 triage and fresh-fork closeout passed; all fourteen original/P12 upgrade branches were deleted after recording their full heads. P13b target selection is in progress. LocalSingleNode deployment and node-demo live acceptance remain pending. The execution goal is [BlazorAutoAppTemplateUpgradeGoal.md](BlazorAutoAppTemplateUpgradeGoal.md).

Execution context updated 2026-10-09: the current computer is the operator's Windows **main PC**, observed hostname `DESKTOP-FDU51L5`. The deployment target is a separate PC, **node-demo**, at **`192.168.0.212`**, with a fixed DHCP lease. The main-PC agent owns repository work, GitHub operations and the LAN acceptance check. Node bootstrap, runner installation and local Ansible deployment run on node-demo only. Naming node-demo in this plan does not authorise treating the current PC or a WSL distribution as node-demo. The operator confirms node-demo is installed and the repository is cloned; no further node setup has been done. Authentication, bootstrap, runner readiness and site availability remain pending. The phase records below remain the 2026-10-08 handoff except for the explicit preflight updates in 11.6.
Prepared: 2026-10-08.
Executes in: `Grumlebob/BlazorAutoAppTemplate` (the template). This plan lives in the template's `Plans/` folder (moved from ImprovedDb on 2026-10-08). ImprovedDb is the read-only evidence source.
Companion inventory: [Support/BlazorAutoAppTemplateUpgrade/FileTriage.md](Support/BlazorAutoAppTemplateUpgrade/FileTriage.md) (299 files, each with a decision and phase).

Pinned baselines (all evidence in this plan was read at these commits):

| Repository | Commit | Notes |
| --- | --- | --- |
| ImprovedDb | `2073e2ec19b5ae5383132f75b90357c3d70e7751` | Source of fixes. Read-only for this plan. |
| BlazorAutoAppTemplate | `ad710610c9a6c0df8380cf1eb257226cb7d41bc7` | Target. Last non-Dependabot commit 2026-09-28. |

**How to use this plan (read first).** It is long. Do not read it all at once:

1. Read section 3 (rules), section 9 (blockers) and section 10 (decisions) once.
2. Work from **11.2 Open items**, top to bottom. For each item, read only the phase it names (for example P13), and only that phase's steps.
3. P0–P6, P8a and P9 are **done**. Do not redo them; their sections are history and porting reference.
4. If a fact here is wrong, correct the plan (docs-only commit, 11.7) and continue. If something is ambiguous, prefer the safer option, record it in the PR body, and continue. Ask the operator only for MB5–MB9.

If either repository has moved on when you start, keep these SHAs as the evidence base. Use the newer template `main` as the branch base, and re-run the diff commands in section 3.5 per file before porting.

---

## 1. Goal

ImprovedDb was forked from BlazorAutoAppTemplate in May 2026 and has since fixed many problems in hosting, testing, CI, CD and LocalCluster operations. Bring the **generic** fixes back to the template so the next app forked from it deploys easily and avoids the failures ImprovedDb already paid for.

Success means:

1. A fresh fork of the template can be customised, built, tested, released and deployed with fewer manual steps and fewer secrets than today. In particular, no GHCR personal access token is needed.
2. The template no longer contains the defects listed in section 2.2.
3. Template CI is green on `main`, and every change was merged through a PR whose required check `build-test-push` passed.
4. Nothing ImprovedDb-specific (media, people, awards, data import, ML, statistics, coordinator, desktop CI pool) entered the template.
5. Nothing in the template assumes a particular cluster: node IPs, hostnames, DNS suffix, domain, ports and runner hosts stay fork-specific settings (section 3.4.3).

### 1.1 Non-goals

- Do not port ImprovedDb product features or its data pipeline.
- Do not port ImprovedDb's multi-agent coordinator, durable deploy supervisor, operation journal, desktop CI runner pool, release-state recovery workflows or `Scripts/DeployLocalCluster.ps1`. They solve ImprovedDb's scale (multi-hour data jobs, several concurrent agents, two CI hosts). A template should stay understandable. Section 8 lists what was deferred and why.
- Do not change ImprovedDb in this plan.
- Do not rename the template's projects or namespaces (`BlazorAutoApp.*`).
- Do not replace the Books sample feature. It is the template's teaching slice.

---

## 2. Background and evidence

### 2.1 How the two repositories relate

- The template still ships the Books sample, Cloud (Hetzner) deployment, LocalCluster deployment, observability and simulator.
- ImprovedDb replaced Books with the media product, added DataImport/ML/statistics, and hardened CI/CD and LocalCluster operations.
- After the fork, the template itself received some changes that ImprovedDb lacks: Dependabot package bumps (template package versions are mostly **newer**), Cloud SSH-key handling (2026-06-19), the Actions storage policy and the Lighthouse pin. **Never overwrite those with older ImprovedDb content.**
- Both apps can run side by side on the same four LocalCluster nodes, as ImprovedDb's guide documents. In that setup they share `node-main` (Caddy, cloudflared, the Docker daemon, GitHub runners) and the deploy lock directory `/tmp/localcluster-deploy.lockdir`. Each fork has its own `machines.yml` and generated `hosts.yml`; the template's committed inventory is sample data, not a statement about any real cluster.

### 2.2 Defects confirmed in the template (fix these first)

| # | Defect | Evidence | Fixed in |
| --- | --- | --- | --- |
| D1 | The deploy lock is reclaimed by age. After 4 hours (`LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS=14400`) any waiter deletes `token`, `owner` and `created_epoch` from a lock it does not own. Side-by-side apps share this lock directory (ImprovedDb uses the same default path). A long operation by another app (ImprovedDb's weekly refresh, for example) can lose its lock, and the other app's metadata gets corrupted. | Template `Deployment/LocalCluster/Scripts/Component/with-deploy-lock.sh` (`cleanup_stale_lock`) and `Component/with-node-main-deploy-lock.sh`. ImprovedDb removed age reclamation: "a dead shell can leave live children". | P1 |
| D2 | The lock wrapper runs the command in the foreground. On cancellation (SIGINT/SIGTERM) the EXIT trap can release the lock while `ansible-playbook` children are still mutating nodes. | Same files. ImprovedDb's `with-deploy-lock.sh` waits for the owned child. | P1 |
| D3 | CI runs `prune-docker-residue.sh --force` after **every** run. It does unscoped `docker container prune`, `docker image prune`, `docker builder prune -af` and `docker network prune` on the shared node-main daemon, which can remove other apps' stopped containers, images and build cache. | Template `ci.yml` step "Clean self-hosted Docker build residue" and `prune-docker-residue.sh` lines 513–517. ImprovedDb scopes CI cleanup to its own labels and moved routine cleanup into one scheduled maintenance job. | P1 (stop), P8 (replace) |
| D4 | The Prometheus template uses the **host-published** port for in-network targets on node-main (`alloy:{{ observability_alloy_http_port }}`, `node-exporter:{{ observability_node_exporter_port }}`). With default ports this works by coincidence. Any fork with side-by-side ports (`12346`, `9101`) gets dead scrape targets. | `Deployment/LocalCluster/ansible/roles/observability_backend/templates/prometheus.yml.j2`. ImprovedDb uses the container ports `12345`/`9100`. | P1 |
| D5 | CI `concurrency: group: ci-${{ github.ref }}` with `cancel-in-progress: false` on `main`. GitHub keeps at most one pending run per group, so when several commits land quickly, intermediate `main` commits lose their CI run and can never be deployed. | Template `ci.yml`. ImprovedDb gives each main run its own group. | P5 |
| D6 | Dependabot auto-merge does not verify that CI tested the PR's **current** head SHA, approves with `GITHUB_TOKEN`, and cannot recover a PR that is behind `main`. | Template `auto-merge-dependabot.yml`. ImprovedDb version checks run identity, head SHA, merge state and refreshes branches. | P6 |
| D7 | CD deploys by mutable tag lookup and does not verify that the image and the migration bundle come from the same CI run. | Template `cd-localcluster.yml`. ImprovedDb writes `release-manifest.json` (image digest + bundle SHA-256 + ordered migrations) in CI and validates it in CD. | P5, P7 |
| D8 | Deploys need a long-lived classic PAT (`vault_ghcr_token`) on the nodes, and `docker login` persists GHCR credentials in the deploy user's Docker config. | Template `roles/app/tasks/main.yml`, `vault.example.yml`, `HowToForkThisRepo.md` §12. ImprovedDb uses the job's `GITHUB_TOKEN` and a temporary `DOCKER_CONFIG`. | P7 |
| D9 | Integration test containers leak. They are stopped with `StopAsync()` instead of disposed, and PostgreSQL 18 declares `/var/lib/postgresql` as a volume, so every run creates anonymous volumes on the runner. ImprovedDb measured 2,191 volumes (≈109 GB) on node-main. | Template `WebAppFactory.cs`, `SharedIntegrationEnvironment.cs`, `TestContainerImages.cs`, CI `TESTCONTAINERS_RYUK_DISABLED: "true"`. | P3 |
| D10 | The global rate limiter counts static assets. One WASM boot downloads dozens of `_framework/*` files and can exhaust the per-IP global budget (600/min); E2E and simulation runs then see 429s. | Template `AppRateLimiting.cs`. ImprovedDb exempts static asset paths. | P2 |
| D11 | Cache invalidation ignores caller cancellation (fresh `CancellationTokenSource`), the Redis subscriber can hang shutdown (`SubscribeAsync` without `WaitAsync(stoppingToken)`), and malformed messages are not rejected. | Template `Infrastructure/Hosting/CacheInvalidation/*`. | P2 |
| D12 | CI jobs run `apt-get` through `ensure-actions-runner-prereqs.sh` and `install-ansible.sh`. ImprovedDb CI failed repeatedly on an apt lock held by `mint-refresh-ca`. Provisioning must be explicit; CI must only check. | ImprovedDb `Plans/LocalClusterCICDReliabilityAndPerformance.md` §2 (maintenance runs 35499972120 and 34747362962, PR CI 35658976655). | P8 (scripts), P5 (CI uses `--check`) |
| D13 | `acceptance-check.sh` and cloudflared downloads have no timeouts or retries; one slow endpoint hangs CD. | Template `acceptance-check.sh`, `roles/cloudflared/tasks/main.yml`. | P1 |
| D15 | **Known admin password in every deployment.** Deployments run with `ASPNETCORE_ENVIRONMENT=Docker`. In that environment `LocalLoginAccountSeedExtensions` defaults to enabled, and `appsettings.Docker.json` seeds `admin@admin.com` / `Admin123` (role Admin) and `user@user.com` / `User123`. On **every start** it resets those passwords to the configured values, so changing them on a live site does not stick. No deployment overrides it; only `ci-docker-smoke.sh` sets `LocalAccounts__Enabled=false`. ImprovedDb has the same code and settings. | Template and ImprovedDb `BlazorAutoApp/Features/Login/Account/Seed/LocalLoginAccountSeedExtensions.cs`, `appsettings.Docker.json`; LocalCluster/Cloud app compose files (found 2026-10-08). Not yet checked on a live site. ImprovedDb fixed in PR #238 (merge queued 2026-10-08); the template copies that fix. | 11.2 item 0 |
| D14 | Apps are stopped before Caddy/cloudflared are re-rendered, and both app nodes restart together. There is no rolling restart for no-migration deploys, and the image is not pulled before the stop window. | Template `site.yml`. ImprovedDb stages the exact image first, rolls app nodes `serial: 1`, and renders Caddy after app readiness. | P7 |

### 2.3 Generic lessons that are not bugs but should become template defaults

- Separate PR validation from main publication. PRs build and test but never push images. Main publishes an image, a migration bundle and a release manifest (ImprovedDb `ci.yml`).
- Run a disposable Docker smoke test of the built image (Postgres + Redis + app + a few Playwright checks) before publishing (ImprovedDb `ci-docker-smoke.sh`).
- Label every CI-created Docker resource with repository + run + attempt so cleanup can be proven safe (ImprovedDb `TestContainerLabels`, `ci-docker-smoke.sh`).
- Use one scheduled, lock-protected maintenance workflow for runner/Docker/artifact cleanup with capacity thresholds and exit codes `0/1/2/75`, instead of cleanup inside every CI job (ImprovedDb `run-localcluster-maintenance.sh`).
- Never `docker volume prune`. Never delete a lock by age. Never auto-delete a runner directory whose identity cannot be read.
- On self-hosted Linux Mint runners use `python3 -m venv` with a constraints file, not `actions/setup-python`.
- Wait for Blazor interactivity in E2E through a hidden probe element instead of sleeps. Disable interactive controls during prerender.
- Do not write tests that only construct DTOs to satisfy architecture rules (ImprovedDb `PassiveRequestDtoConstructionTests_AreNotAllowed`).
- Keep a short, enforceable `AGENTS.md` and a canonical `docs/Requirements.md` so AI agents working in a fork follow the same rules.

### 2.4 P0 findings (read-only, 2026-10-08)

Gathered through the GitHub API before execution started. Re-check them in P0; they are evidence, not a substitute.

- The template runner `node-main-books` works: the last `main` CI run ([36483118223](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/36483118223), commit `ad710610`) succeeded on 2026-09-28 in about 8 minutes.
- 12 Dependabot PRs are open, the oldest from 2026-06-19 (`actions/checkout` 6→7, `setup-node` 6→7, `setup-dotnet` 5→6, `docker/login-action` 4→4.5.2, Tailwind 4.3.3, ASP.NET Core 10.0.11 packages, Lighthouse 13.5.0). Workflow-file bumps are excluded from auto-merge by design; the others failed CI.
- Why they failed, with evidence:
  - August runs (for example [31689720638](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/31689720638)) failed in "Check self-hosted runner disk": node-main had 9.4 GB free (96% used). `docker system df` showed **1,971 local volumes, 98.84 GB, 97% reclaimable**. That is D9 (leaked test-container volumes, from both repositories' CI on the same daemon). The template's unscoped cleanup then ran against the shared daemon (D3) and could not help, because volumes are protected.
  - The 2026-09-22 run [35714209166](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/35714209166) passed all 135 tests, then failed in `docker build`: `lookup registry-1.docker.io on 127.0.0.53:53 ... i/o timeout` (node-main DNS). This was an infrastructure flake, not a template defect.
- The cleanup logs also show the template's `prune-docker-residue.sh` inspects ImprovedDb's deploy roots (`/opt/improveddb/data-runner`, `/opt/improveddb/LocalData`) and treats `ghcr.io/grumlebob/improveddb` as a candidate repository. That confirms the cross-app reach described in D3.
- Consequence for P0.5: before P1, ask Dependabot to recreate the stale PRs (`@dependabot recreate` comment) or close them. Do this after P1 and P3 merge, so their CI runs with the scoped cleanup and leak fixes. Merge the action-version PRs (`checkout`, `setup-node`, `setup-dotnet`, `login-action`) manually once green; P5 also adopts those versions.

---

## 3. Ground rules for the executing agent

Read this whole section before Phase 0. These rules apply to every phase.

### 3.0 Running on the operator's Windows main PC

The executing agent runs on the operator's Windows main PC (`DESKTOP-FDU51L5` as observed on 2026-10-09). The current checkout is `C:\Users\jgrum\Documents\Programming\Csharp\BlazorAutoApp`, whose `origin` is `Grumlebob/BlazorAutoAppTemplate`. node-demo is the separate deployment target at `192.168.0.212` (fixed DHCP lease).

- **Check machine roles before setup.** Windows and its WSL distributions are controller environments. Never run `bootstrap-node.sh`, `PrepareSingleNode.yml`, runner installation, hostname changes or node firewall changes there. P13.D steps 1–3 belong to an agent and operator physically on node-demo. GitHub workflow dispatch from the main PC schedules deployment on node-demo's runner; the controller does not deploy locally.
- **Use WSL (Ubuntu 24.04) for implementation and the local verification gate.** Documentation planning can use the current Windows checkout. The deployment scripts, tests and linters are bash/Python/Ansible. On 2026-10-09, `Ubuntu-24.04` was backed up and converted from WSL 1 to WSL 2. Its development checkout is `/home/grumbo/src/BlazorAutoAppTemplate`; Docker Desktop integration and the gate tools are prepared (11.6). Recheck Docker access before each implementation session. Do not repurpose or stop `ImprovedDb-CI` for this plan. Keep the template **inside the WSL filesystem**, not under `/mnt/c`; that path is slow and breaks file modes. Run `dotnet`, `pwsh`, `docker` and `gh` from the same WSL shell. The installed SDK is `10.0.303`. Use one checkout per phase; transfer reviewed Windows plan edits explicitly before continuing in WSL.
- **`gh` must be logged in** (`gh auth status`) with push and admin rights on `Grumlebob/BlazorAutoAppTemplate`, and read access to `Grumlebob/ImprovedDb`. ImprovedDb remains read-only; plan corrections live in the template. Run `gh auth setup-git` once so `git push` uses the same login.
- **Line endings:** run `git config --global core.autocrlf input` in WSL before cloning. CRLF in a `.sh` file breaks it.
- **Plan edits** (11.1 evidence, 11.7 corrections, the status line) live in this repository. Include them in the next phase PR you open; a merge SHA is known only after merge, so record it in the following PR. For a correction with no code PR in flight, open a docs-only PR. Never push to `main` directly.
- **Waiting on CI:** use `gh pr checks <n> --watch` or `gh run watch <id>`. Do not poll faster than once a minute, and do not cancel runs you did not start.
- **Long runs:** the full test suite takes about 5–10 minutes and needs Docker. Never run two `dotnet build`/`dotnet test` commands at the same time in one clone.

### 3.1 Paths used in this plan

```bash
export IDB=/path/to/ImprovedDb            # checkout of Grumlebob/ImprovedDb at 2073e2ec19b5...
export TPL=/path/to/BlazorAutoAppTemplate # writable clone of Grumlebob/BlazorAutoAppTemplate
export IDB_SHA=2073e2ec19b5ae5383132f75b90357c3d70e7751
export TPL_BASE_SHA=ad710610c9a6c0df8380cf1eb257226cb7d41bc7
```

All file paths in this plan are relative to the repository root they belong to. "IDB file" means `$IDB/<path>` at `$IDB_SHA` (read it with `git -C "$IDB" show "$IDB_SHA:<path>"` if ImprovedDb has moved on). "Template file" means `$TPL/<path>`.

### 3.2 Branches, PRs and commits

- Work only in the template repository. Create one branch per phase from the current `origin/main`: `upgrade/p01-shared-cluster-safety`, `upgrade/p02-app-runtime`, and so on. Phases that the plan marks "same PR as" share a branch.
- Open one PR per phase. Title format: `Template upgrade P<n>: <phase name>`. The PR body must list: the defects/lessons fixed (by ID), the files changed, the triage rows handled, the local verification output, and anything skipped with the reason.
- Merge with squash only after the required check `build-test-push` is green on the PR's exact head. Do not merge two phases in one PR unless the plan says so.
- Stage explicit paths. Never `git add .` or `git add -A`.
- Do not push to the template's `main` directly. Every template change, documentation included, goes through a PR.
- Each phase is complete when its PR is merged **and** `main` CI for the merge commit is green. If `main` CI is red, fixing it is the next task before any new phase.

### 3.3 Never do

- Never copy ImprovedDb domain content. If a file mentions media, movies, series, episodes, people, awards, IMDb, TMDB, OMDb, MDBList, TheTVDB, Kaggle, statistics, ML/ONNX, DataImport, LocalData, provider refresh, data runner, CurrentPC sync, coordinator or supervisor, strip that part or skip the file.
- Never downgrade a package, action or tool version. When the template and ImprovedDb differ, keep the higher version.
- Never overwrite template Cloud SSH handling (`Deployment/Cloud/**`, `cd-cloud.yml` key steps) with ImprovedDb content. The template is newer there.
- Never add `docker volume prune`, `docker system prune --volumes`, unscoped `docker container prune`, or deletion of anything under `/opt/<app>` data paths.
- Never reclaim a deployment lock automatically, by age or otherwise.
- Never use `actions/setup-python` or GitHub-hosted runner labels (`ubuntu-*`, `windows-*`, `macos-*`). The template audit enforces self-hosted runners.
- Never put secrets, tokens, real passwords, private keys or vault contents in commits, PR bodies or logs.
- Never run `dotnet build` and `dotnet test` concurrently in one checkout.
- Never dispatch `CD - Deploy LocalCluster` or `CD - Cloud` for the template. The operator decided (Q1, section 10) that this plan's verification does not include a live LocalCluster or Cloud deploy. The only deploy this plan authorises is `CD - Deploy LocalSingleNode` to node-demo in P13.12 (Q4).
- Never hard-code a cluster value: node IPs, `.home` or any other DNS suffix, the `jacobgrum.com` domain, `node-main` runner hostnames beyond the existing `node-main` role name, or ImprovedDb ports. Section 3.4.3 has the rules.

### 3.4 Renaming and genericising rules

#### 3.4.1 Names

| ImprovedDb text | Template replacement |
| --- | --- |
| `ImprovedDb`, `improveddb` in script/temp-file names | Derive from `app_name` (`read-deploy-setting.sh app_name`) or use `localcluster` for shared, app-neutral names. |
| `localcluster-improveddb` runner label fallback | Keep the template's existing fallback `localcluster-books` (forks override with `LOCALCLUSTER_RUNNER_LABEL`). |
| `improveddb-migration-staging-…` artifact name | `${MIGRATION_BUNDLE_NAME}-staging-${run_id}-${run_attempt}` |
| `com.improveddb.ci.*` Docker labels | Generic label scheme in 3.4.2. |
| `/opt/improveddb/...` | `/opt/${APP_NAME}/...` |
| `books-ansible` (Ansible install root) | Unchanged. Both repos use `~/.local/share/books-ansible`; a rename would orphan the existing install. |

#### 3.4.2 Generic CI resource labels

Every Docker container, network and image that CI or tests create must carry these labels:

| Label | Value |
| --- | --- |
| `localcluster.ci.repository` | `${GITHUB_REPOSITORY}` (for example `Grumlebob/BlazorAutoAppTemplate`); `local` when unset |
| `localcluster.ci.owner` | `ci-build`, `ci-smoke` or `tests` |
| `localcluster.ci.purpose` | Short purpose, for example `shared-integration-postgres` |
| `localcluster.ci.run_id` | `${GITHUB_RUN_ID}` or `local` |
| `localcluster.ci.run_attempt` | `${GITHUB_RUN_ATTEMPT}` or `local` |
| `localcluster.ci.session` | `${run_id}-${run_attempt}` or `local-<guid>` |
| `localcluster.ci.created_at` | UTC ISO-8601 timestamp |

Cleanup code may delete only resources whose `localcluster.ci.repository` equals the current `GITHUB_REPOSITORY`. That is what makes cleanup safe on a node-main shared by several apps.

#### 3.4.3 Fork-specific values stay fork-specific

The template is a template. A fork may point at completely different machines.

- Do **not** edit `Deployment/LocalCluster/inventory/prod/hosts.yml` IPs in this plan. They are sample values regenerated per fork from the ignored `Deployment/LocalCluster/machines.yml` (`generate-inventory.sh`). Section 9 explains why the current values are stale.
- Any new check that needs a cluster value reads it from `group_vars/all.yml` or the inventory, has a safe default, and **skips** when the setting is empty (for example the optional DNS validation in P1).
- Reusable deployment docs must describe how a fork sets each value, not record ImprovedDb's or the template owner's values. This plan, its execution goal and the node-demo operator guide may record the operator's actual target as execution context. Do not copy `192.168.0.212` or `DESKTOP-FDU51L5` into reusable scripts, workflows, inventories, defaults or fixtures.

### 3.5 How to port one file

For each triage row you handle:

1. Diff both directions:
   ```bash
   git diff --no-index -- "$TPL/<path>" "$IDB/<path>"
   ```
2. Classify each hunk: generic fix, product content, or template-newer content. Product and template-newer hunks are dropped.
3. Apply only the generic hunks by editing the template file. For a `PORT` row, you may copy the whole file and then edit, but read the result line by line afterwards.
4. Run `grep -n -i -E 'improveddb|media|people|award|imdb|tmdb|omdb|mdblist|thetvdb|kaggle|dataimport|LocalData|coordinat|supervisor|statistic|jacobgrum|\.home' <path>` on every changed file. Each hit must be justified or removed.
5. Record the row as handled in the PR body (path, decision, one-line summary).

### 3.6 Local verification gate

Run this before every push. Each command must pass. If one cannot run locally (no Docker daemon, for example), say so in the PR body and rely on CI, but run everything else.

```bash
cd "$TPL"
git diff --check
dotnet restore BlazorAutoApp.sln
dotnet format BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore
dotnet build BlazorAutoApp.sln --configuration Release --no-restore
dotnet test BlazorAutoApp.sln --configuration Release --no-build          # needs Docker
bash Deployment/Common/Scripts/validate-common-release.sh
bash Deployment/Cloud/Scripts/validate-cloud-settings.sh
bash Deployment/Common/observability/scripts/validate-observability.sh
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
python3 -m venv /tmp/tpl-venv && /tmp/tpl-venv/bin/pip install -c Deployment/Common/ci-python-constraints.txt jinja2 yamllint
PATH="/tmp/tpl-venv/bin:$PATH" bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
PATH="/tmp/tpl-venv/bin:$PATH" yamllint .github Deployment docker-compose.yml .yamllint.yml
find Deployment -type f -name '*.sh' -print0 | xargs -0 shellcheck --severity=warning
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12
```

If Docker Hub rate-limits the actionlint pull, download the `actionlint` 1.7.12 Linux release binary from `github.com/rhysd/actionlint/releases` and run it from the repository root. Install `shellcheck` with `apt` or as a release binary. Do not skip either check.

When a phase touches `BlazorAutoApp.Client/Styles` or Razor markup classes, also run `cd BlazorAutoApp.Client && npm ci && npm run css:build` and commit `BlazorAutoApp/wwwroot/tailwind.css` if it changed. CI fails on a stale `tailwind.css`.

### 3.7 The deployment audit is a contract test

`Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` checks workflow and script text with "needle" strings. For example, it currently **requires** `LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS` and `created_epoch` in the lock script. When a phase intentionally changes such behaviour:

1. Update the audit in the same commit.
2. If ImprovedDb's audit has a rule for the new behaviour, port that rule. Find it with `grep -n "<needle>" "$IDB/Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py"`.
3. Replace "must contain old behaviour" needles with "must contain new behaviour" and "must not contain old behaviour" checks. Never just delete a needle.

---

## 4. Phase overview

| Phase | Name | Main defects/lessons | Risk | Depends on |
| --- | --- | --- | --- | --- |
| P0 | Preflight and baseline | - | none | - |
| P1 | Shared-cluster safety fixes | D1 D2 D3 D4 D13 | high value, low risk | P0 |
| P2 | App runtime fixes | D10 D11 + small fixes | low | P0 |
| P3 | Test infrastructure hardening | D9 + E2E helpers | medium (test flakiness) | P2 |
| P4 | Dependencies and tooling | transitive pinning, axe-core | low | P0 |
| P5 | CI workflow rework | D5 D7 (CI side) D12 (CI side) | high (CI is the merge gate) | P1 P3 P4 |
| P6 | Dependabot auto-merge hardening | D6 | medium | P5 |
| P7 | [#110](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/110) | `0e9257717434d0457eb74a84c19c82b2d7e9b921` | Local gate: 163 passed, 11 opt-in skipped; 24 release tests, identity fixtures and syntax/render checks passed. Exact-head PR CI [37945842490](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37945842490) and main CI [37947192982](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37947192982) succeeded, including publishing. | Merged, verified |
| P8 | [#111](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/111) | `3960b4855751a99d5e70866601522df7cdf6b390` | Local gate: 163 passed, 11 opt-in skipped; six shell suites and 51 Python tests passed. Exact-head PR CI [37949131184](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37949131184) and main CI [37950400186](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37950400186) succeeded, including publishing. No live maintenance. | Merged, verified |
| P9 | Local developer ergonomics | local Docker residue | low | P0 |
| P10 | [#112](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/112) | `7b6699fcfddbcd378a0c2158843a49f5363ee5de` | Local gate: 167 passed, 11 opt-in skipped; all four agent guardrails passed; links and ignore rules checked. Exact-head PR CI [37952225896](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37952225896) and main CI [37953161424](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37953161424) succeeded, including publishing. | Merged, verified |
| P11 | [#113](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/113) | `f5949378b5fe3db8db2d11ef305c4bc5ae8325e6` | Local gate: 167 passed, 11 opt-in skipped; seven shell suites and 68 Python tests passed. Exact-head PR CI [37969690167](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37969690167) and main CI [37970580512](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37970580512) succeeded, including publishing. | Merged, verified |
| P12 | [#114](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/114) | `f4a9aba85e1016fc55c52dc333cd182c56dc4ca1` | Local gate: 169 passed, 11 opt-in skipped; seven shell suites and 68 Python tests passed. Exact-head PR CI [37972029836](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37972029836) and main CI [37972952941](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37972952941) succeeded, including publishing. Final merged fresh-fork rehearsal passed. Original merged branches deleted. P12.4 skipped (Q1). | Merged, verified |
| P13 | LocalSingleNode deployment target (node-demo) | new target; target selection | high (new deploy path, moves shared scripts) | P7 P8 (merged) |

Order constraints: P1 first (it removes hazards to other apps on shared nodes). P2, P4, P9 and P10 can run in any order after P0. P8.1 and P8.2 (check-only provisioning, small PR `upgrade/p08a-check-only-provisioning`) must merge before P5, because the new CI calls `--check`. P5 must come after P3, because P5 makes CI run the new lifecycle test. P6, P7 and the rest of P8 come after P5. P11 is last before P12.

Recommended sequence: P0 → P1 → P2 → P4 → P3 → P8a → P5 → P6 → P7 → P8 → P9 → P10 → P11 → P12 → P13.

P13 starts only after P7, P8, P10 and P11 are merged. Its PRs go in this order: P13a (Common building blocks), P13b (target selection), P13c (single-node target), P13d (docs). The node-demo live test P13.12 comes after them.

---

## 5. Phases

### P0. Preflight and baseline

Goal: confirm access, tooling and the template's current health before changing anything.

- [ ] P0.1 Confirm you can push branches and open PRs on `Grumlebob/BlazorAutoAppTemplate` (`gh repo view Grumlebob/BlazorAutoAppTemplate --json viewerPermission` must show `WRITE`, `MAINTAIN` or `ADMIN`). If not, stop and report manual blocker MB1 (section 9).
- [ ] P0.2 Clone both repositories (or update existing clones) and set the variables from 3.1. Check out ImprovedDb at `$IDB_SHA` in a separate worktree if its `main` has moved:
  ```bash
  git -C "$IDB" worktree add /tmp/idb-baseline "$IDB_SHA" && export IDB=/tmp/idb-baseline
  ```
- [ ] P0.3 Record the template state:
  ```bash
  git -C "$TPL" log -1 --format='%H %cs %s' origin/main
  git -C "$TPL" log --oneline "$TPL_BASE_SHA"..origin/main   # anything new since this plan?
  gh pr list --repo Grumlebob/BlazorAutoAppTemplate --state open
  gh run list --repo Grumlebob/BlazorAutoAppTemplate --workflow ci.yml --limit 10
  gh api repos/Grumlebob/BlazorAutoAppTemplate/branches/main/protection --jq '.required_status_checks.contexts' || true
  gh api repos/Grumlebob/BlazorAutoAppTemplate/actions/runners --jq '.runners[] | [.name,.status,(.labels|map(.name)|join(","))] | @tsv'
  gh api repos/Grumlebob/BlazorAutoAppTemplate/actions/variables --jq '.variables[] | [.name,.value] | @tsv'
  gh api repos/Grumlebob/BlazorAutoAppTemplate/actions/secrets --jq '.secrets[].name'
  ```
  Write the output into the P1 PR body under "Baseline". Expected: a runner named like `node-main-books` with labels `self-hosted, linux, x64, localcluster, localcluster-books`, online. If no online runner carries the label CI uses, stop: manual blocker MB2.
- [ ] P0.4 If commits landed on the template after `$TPL_BASE_SHA`, read each one. If any touches a file in the triage inventory, note it in the P1 PR body and re-diff that file when its phase comes.
- [ ] P0.5 Open Dependabot PRs: let them merge or close as they normally would before P5. Do not rebase them onto upgrade branches.
- [ ] P0.6 Tooling. Install the .NET SDK required by `global.json` if missing:
  ```bash
  curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
  bash /tmp/dotnet-install.sh --jsonfile "$TPL/global.json" --install-dir "$HOME/.dotnet"
  export PATH="$HOME/.dotnet:$PATH"
  ```
  Also need: `docker` with a running daemon (for tests), `node`/`npm`, `python3`, `shellcheck`, `pwsh` (for `Scripts/*.ps1` checks). Record which are unavailable.
- [ ] P0.7 Baseline gate: run section 3.6 on an untouched `origin/main` checkout. Record pass/fail per command. A command that already fails on baseline is a pre-existing failure: fix it in P1 only if trivial, otherwise record it and make sure later phases do not make it worse.
- [ ] P0.8 Skim `$IDB/AGENTS.md`, `$IDB/docs/Requirements.md` and this plan's triage file so you know the vocabulary.

Done when: access confirmed, baseline recorded, blockers (if any) reported.

### P1. Shared-cluster safety fixes

Goal: stop the template from harming other apps on shared nodes, and fix the cheap reliability bugs. Branch `upgrade/p01-shared-cluster-safety`.

#### P1.A Deploy lock without age reclamation (D1, D2)

- [ ] P1.A1 Replace the body of `Deployment/LocalCluster/Scripts/Component/with-deploy-lock.sh` with the logic below. Keep the shebang and `set -euo pipefail`. It mirrors ImprovedDb's script without the Python helper (`deploy_lock.py` is coordinator-specific and 1,585 lines). Keep the variable names; other scripts and the audit rely on `LOCALCLUSTER_DEPLOY_LOCK_DIR` and `LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS`.
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  if [[ $# -eq 0 ]]; then
    echo "usage: $0 <command> [args...]" >&2
    exit 1
  fi

  fail() {
    echo "LocalCluster deploy lock failed: $*" >&2
    exit 1
  }

  # Shared by every app deployed to this node-main. Other repositories use the
  # same directory and may store extra metadata files in it.
  LOCK_DIR="${LOCALCLUSTER_DEPLOY_LOCK_DIR:-/tmp/localcluster-deploy.lockdir}"
  LOCK_TIMEOUT_SECONDS="${LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS:-1800}"
  LOCK_TOKEN="$(date +%s)-$$-${RANDOM:-0}"
  LOCK_OWNER="$(hostname):pid=$$:repo=${GITHUB_REPOSITORY:-manual}:run=${GITHUB_RUN_ID:-none}-${GITHUB_RUN_ATTEMPT:-0}:started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  LOCK_ACQUIRED=0
  ACTIVE_COMMAND_PID=""
  PENDING_SIGNAL_STATUS=0

  [[ "$LOCK_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS must be a number"
  [[ "$LOCK_DIR" = /* ]] || fail "LOCALCLUSTER_DEPLOY_LOCK_DIR must be an absolute path"
  [[ -d "$(dirname "$LOCK_DIR")" ]] || fail "lock parent directory does not exist: $(dirname "$LOCK_DIR")"

  # Never reclaim a lock automatically. A dead shell can leave live children,
  # and another app may legitimately hold the lock for hours. Recovery is the
  # manual, verified procedure in release-deploy-lock.sh.
  release_lock() {
    [[ "$LOCK_ACQUIRED" == "1" ]] || return 0
    if [[ "$(cat "$LOCK_DIR/token" 2>/dev/null || true)" != "$LOCK_TOKEN" ]]; then
      echo "LocalCluster lock token changed while held; leaving $LOCK_DIR for inspection" >&2
      return 75
    fi
    local unexpected
    unexpected="$(find "$LOCK_DIR" -mindepth 1 -maxdepth 1 ! -name token ! -name owner ! -name created_epoch -print -quit)"
    if [[ -n "$unexpected" ]]; then
      echo "LocalCluster lock contains unexpected file $unexpected; leaving it for inspection" >&2
      return 75
    fi
    rm -f "$LOCK_DIR/token" "$LOCK_DIR/owner" "$LOCK_DIR/created_epoch"
    rmdir "$LOCK_DIR" || { echo "could not remove $LOCK_DIR; inspect it" >&2; return 75; }
    LOCK_ACQUIRED=0
  }

  finish() {
    local status=$?
    trap - EXIT
    local release_status=0
    release_lock || release_status=$?
    if [[ "$status" == "0" && "$release_status" != "0" ]]; then
      status=75
    fi
    exit "$status"
  }
  trap finish EXIT

  wait_for_owned_command_then_exit() {
    local signal_status="$1"
    trap '' TERM INT
    if [[ -n "$ACTIVE_COMMAND_PID" ]]; then
      echo "termination received; waiting for owned command PID $ACTIVE_COMMAND_PID before releasing the lock" >&2
      set +e
      while kill -0 "$ACTIVE_COMMAND_PID" 2>/dev/null; do
        wait "$ACTIVE_COMMAND_PID"
      done
      set -e
    fi
    exit "$signal_status"
  }

  handle_signal() {
    local signal_status="$1"
    if [[ -z "$ACTIVE_COMMAND_PID" ]]; then
      [[ "$LOCK_ACQUIRED" == "1" ]] || exit "$signal_status"
      PENDING_SIGNAL_STATUS="$signal_status"
      return
    fi
    wait_for_owned_command_then_exit "$signal_status"
  }
  trap 'handle_signal 143' TERM
  trap 'handle_signal 130' INT

  deadline=$((SECONDS + LOCK_TIMEOUT_SECONDS))
  echo "waiting for LocalCluster deployment lock: $LOCK_DIR"
  # 0755 so other apps' runners can read the owner line when they time out.
  while ! (umask 022; mkdir "$LOCK_DIR") 2>/dev/null; do
    if (( SECONDS >= deadline )); then
      echo "timed out waiting for LocalCluster deployment lock: $LOCK_DIR" >&2
      for file in owner owner.json; do
        [[ -r "$LOCK_DIR/$file" ]] && echo "lock $file: $(head -c 2000 "$LOCK_DIR/$file")" >&2
      done
      echo "Do not delete the lock by hand. Follow 'Deployment lock' in Deployment/LocalCluster/HowToDeployLocalCluster.md." >&2
      exit 1
    fi
    sleep 2
  done

  LOCK_ACQUIRED=1
  export LOCALCLUSTER_DEPLOY_LOCK_DIR="$LOCK_DIR" LOCALCLUSTER_DEPLOY_LOCK_TOKEN="$LOCK_TOKEN"
  printf '%s\n' "$LOCK_TOKEN" > "$LOCK_DIR/token"
  printf '%s\n' "$LOCK_OWNER" > "$LOCK_DIR/owner"
  date +%s > "$LOCK_DIR/created_epoch"
  echo "LocalCluster deployment lock acquired: $LOCK_DIR"

  [[ "$PENDING_SIGNAL_STATUS" == "0" ]] || exit "$PENDING_SIGNAL_STATUS"
  "$@" &
  ACTIVE_COMMAND_PID=$!
  command_status=0
  wait "$ACTIVE_COMMAND_PID" || command_status=$?
  ACTIVE_COMMAND_PID=""
  [[ "$PENDING_SIGNAL_STATUS" == "0" ]] || exit "$PENDING_SIGNAL_STATUS"
  exit "$command_status"
  ```
- [ ] P1.A2 In `Deployment/LocalCluster/Scripts/Component/with-node-main-deploy-lock.sh` (the manual control-machine path used by `deploy.sh`): delete `LOCK_STALE_SECONDS`, `lock_stale_q`, `cleanup_stale_lock()` and its call in the wait loop. In the remote `release_lock` heredoc, apply the same rules as P1.A1: release only when the token matches, and leave the directory with a message (exit 75) when files other than `token/owner/created_epoch` exist. Change the remote `mkdir` to `(umask 022; mkdir "$LOCK_DIR")`. Change `StrictHostKeyChecking=accept-new` to `StrictHostKeyChecking=yes`. ImprovedDb's lesson: first-seen keys for a reused IP must be verified, not accepted. Document known_hosts seeding in P11.
- [ ] P1.A3 Add `Deployment/LocalCluster/Scripts/release-deploy-lock.sh` for manual recovery. Behaviour:
  - Usage: `release-deploy-lock.sh --inspect` and `release-deploy-lock.sh --release --token <exact token>`. Run it on node-main.
  - `--inspect` prints every file in the lock dir (truncated to 2,000 bytes each), the parsed host and PID from `owner`, and whether that PID is alive (`kill -0`) when the host matches `hostname`. Exit 0.
  - `--release` refuses (exit 1) when: the token argument differs from `token`; the owner host is not this host, unless the operator passes `--owner-host-checked` after checking that host (manual deploys run on a control machine); the owner PID is alive; any `ansible-playbook` process is running for the current user (`pgrep -u "$USER" -f ansible-playbook`); or files other than `token/owner/created_epoch` exist (another app's lock format: tell the operator to use that app's recovery tool). Otherwise it removes the three files and the directory.
  - Never offers a `--force` flag.
- [ ] P1.A4 Add `Deployment/LocalCluster/Scripts/Tests/test-with-deploy-lock.sh`. Start from `$IDB/Deployment/LocalCluster/Scripts/Tests/test-with-deploy-lock.sh` and drop its Python helper and supervisor expectations. Cover:
  1. Lock acquired, command runs, lock removed, exit code propagated (0 and non-zero).
  2. An existing lock with `created_epoch` 10 hours old is **not** removed. The wrapper times out with `LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS=2` and exits 1.
  3. A lock containing an extra `owner.json` (another app's format) is not touched.
  4. A command that ignores SIGTERM for 2 seconds: send TERM to the wrapper; the lock still exists while the child runs and is released after the child exits.
  Use a temp `LOCALCLUSTER_DEPLOY_LOCK_DIR` under `mktemp -d`. The test must never touch `/tmp/localcluster-deploy.lockdir`.
- [ ] P1.A5 Update `audit_deployment.py` (section 3.7). Remove the needles that require stale cleanup. Add needles that require `release_lock`, `wait_for_owned_command_then_exit` and `trap 'handle_signal 143' TERM`. Add checks that **fail** if `LOCK_STALE_SECONDS` or `cleanup_stale_lock` appears in either lock script.
- [ ] P1.A6 Add a CI step "Test LocalCluster deployment lock" running the new test. It goes in the existing job now; P5 moves it.

#### P1.B Stop unscoped Docker cleanup in CI (D3)

- [ ] P1.B1 In `.github/workflows/ci.yml`, delete the step "Clean self-hosted Docker build residue" (the `if: always()` step that calls `prune-docker-residue.sh --force --remove-image ...`).
- [ ] P1.B2 In the step "Check self-hosted runner disk", replace the inline `prune-docker-residue.sh --force ...` call. If free space is below the threshold, fail with a message telling the operator to run the maintenance workflow, or until P8 lands, `prune-docker-residue.sh --dry-run` followed by a reviewed manual run. P8 brings the scoped capacity-recovery script.
- [ ] P1.B3 In `prune-docker-residue.sh`, make the four unscoped prune commands (`docker container prune`, `docker image prune`, `docker builder prune -af`, `docker network prune`, lines ≈513–517) run only when a new flag `--include-unlabelled-host-residue` is passed, and print a warning that this affects every app on the host. Keep the existing behaviour that is already multi-app aware: `--remove-image` targets, and old-tag cleanup limited to discovered LocalCluster image repositories with every deployed image ref protected. Update the script's `--help` text and `Deployment/LocalCluster/Scripts/README.md`.
- [ ] P1.B4 Update the audit: CI must not call `prune-docker-residue.sh`. Port the matching ImprovedDb rule if one exists.

#### P1.C Small infrastructure bug fixes

- [ ] P1.C1 (D4) `roles/observability_backend/templates/prometheus.yml.j2`: copy the ImprovedDb hunk. For the load-balancer host, targets are `alloy:12345` and `node-exporter:9100` (container ports). Other hosts keep `<ansible_host>:<published port>`. Check every other in-network target in the file (postgres/redis exporters, loki, tempo) for the same mistake and fix it the same way. `Deployment/Cloud/ansible/roles/observability_backend/templates/prometheus.yml.j2` has the identical bug; fix it too. Add an assertion to `validate-rendered-templates.sh` that renders the template with non-default ports (`observability_alloy_http_port: 12346`, `observability_node_exporter_port: 9101`) and checks for `alloy:12345` and `node-exporter:9100`. Port the matching assertion from ImprovedDb's `validate-rendered-templates.sh` if present.
- [ ] P1.C2 (D13) `acceptance-check.sh`: copy ImprovedDb's curl flags. Every `curl` gets `--connect-timeout` and `--max-time` (public: 5/20, local Caddy: 3/10, app node: 5/20). Do not port the data-runner, statistics, media, provider or award blocks.
- [ ] P1.C3 (D13) `roles/cloudflared/tasks/main.yml`: add `force: true`, `timeout: 60`, `register`, `retries: 5`, `delay: 10`, `until: ... is succeeded` to the download task, as ImprovedDb did. Apply the same pattern to any other `get_url` in the LocalCluster roles. Leave Cloud roles alone unless an identical task exists there.
- [ ] P1.C4 `Deployment/LocalCluster/ansible/ansible.cfg`: add `timeout = 30` under `[defaults]`.
- [ ] P1.C5 Optional inventory DNS validation, kept generic:
  - Port `$IDB/Deployment/LocalCluster/Scripts/validate-inventory-dns.sh`, but read the suffix from a new optional `group_vars/all.yml` setting `inventory_dns_suffix` (default `""`). When empty, print `inventory DNS validation skipped (inventory_dns_suffix is empty)` and exit 0. Never default to `.home`.
  - Call it from `preflight.sh` right after `ansible-inventory ... --list`, as ImprovedDb does.
  - Add `inventory_dns_suffix` to the deploy-settings validator (`deploy_settings.py`) as an optional string matching `^$|^\.?[a-z0-9.-]+$`.
  - Add one line to the fork guide (P11): set it when the router publishes stable names, so preflight catches stale IPs.
- [ ] P1.C6 Run the gate (3.6). Open the PR. Merge when green.

Done when: lock tests pass in CI, CI no longer prunes the shared Docker daemon, Prometheus renders container ports, and the PR is merged with `main` green.

### P2. App runtime fixes

Goal: port generic hosting fixes. Branch `upgrade/p02-app-runtime`.

- [ ] P2.1 (D10) `BlazorAutoApp/Infrastructure/Hosting/AppRateLimiting.cs`: port `StaticAssetExtensions`, `IsStaticAssetRequest(PathString)` and the `RateLimitPartition.GetNoLimiter("static-assets")` branch at the top of the global limiter. Do **not** port `MediaImagesPolicyName` or the `MediaImages` options. Make `IsStaticAssetRequest` `internal` so tests can call it (the template already has `InternalsVisibleTo("BlazorAutoApp.Test")`).
- [ ] P2.2 Port the tests from `$IDB/BlazorAutoApp.Test/Infrastructure/Hosting/RateLimitingTests.cs`: `StaticAssetPaths_AreExcludedFromGlobalRateLimit` (theory), `ApplicationPaths_AreNotExcludedFromGlobalRateLimit` (theory; use `/`, `/api/books`, `/Account/Login`, `/books`) and `StaticAssets_DoNotReturnTooManyRequests_WhenGlobalLimitIsExceeded`. Keep the template's existing Books API and account limit tests. Skip `MediaImageRequests_*`.
- [ ] P2.3 (D11) Cache invalidation, porting from `$IDB/BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/`:
  - Add `CacheInvalidationResult.cs` (copy).
  - `ICacheInvalidator.InvalidateAsync` returns `Task<CacheInvalidationResult>`.
  - `HybridCacheInvalidator`: linked cancellation tokens with `CancelAfter`, rethrow `OperationCanceledException` when the caller cancelled, collect warnings, and return a result in all paths (copy the ImprovedDb method body).
  - `RedisCacheInvalidationSubscriber`: `.SubscribeAsync(channel).WaitAsync(stoppingToken)` and the `IsUsableMessage` guard.
  - Do not port the `PublicDataCache` lines in `HybridCacheInvalidationApplier`.
  - Update callers in `BlazorAutoApp/Features/Books/**` to compile. They may ignore the result, but if a write endpoint already logs failures, log `result.Warnings` at Warning.
  - Port `$IDB/BlazorAutoApp.Test/Infrastructure/Hosting/CacheInvalidation/HybridCacheInvalidatorTests.cs`, adapted to template types. It must cover: publish failure returns `Published=false` with a warning; caller cancellation throws; local apply failure still publishes.
- [ ] P2.4 `AppCachingExtensions.cs`: replace `services.AddHybridCache();` with an options lambda setting `MaximumKeyLength = 1024`, `MaximumPayloadBytes = 1024 * 1024` and `ReportTagMetrics = false`. Leave `DefaultEntryOptions` unset; Books sets per-entry options. Do not port `PublicDataCache*` registrations.
- [ ] P2.5 `Infrastructure/Persistence/PersistenceExtensions.cs`: port the `AddDbContextFactory<AppDbContext>((serviceProvider, options) => { ConfigureDbContext(options); options.AddInterceptors(serviceProvider.GetServices<DbCommandInterceptor>()); })` change. Add a one-line comment that features register `DbCommandInterceptor` services to observe SQL.
- [ ] P2.6 Move `CurrentUserAccessor` to the Login slice:
  - Move `BlazorAutoApp/Features/Books/Services/CurrentUserAccessor.cs` to `BlazorAutoApp/Features/Login/Account/CurrentUserAccessor.cs` and change the namespace to `BlazorAutoApp.Features.Login.Account`. Compare with `$IDB/BlazorAutoApp/Features/Login/Account/CurrentUserAccessor.cs` and keep the better-tested version.
  - Register `services.AddHttpContextAccessor()` and `services.AddScoped<ICurrentUserAccessor, CurrentUserAccessor>()` in `LoginFeatureExtensions.AddLoginFeature` and remove the Books registration.
  - Update usings in Books. Run the architecture tests; if a slice rule forbids Books depending on Login, follow the rule the tests state (Login is the shared identity slice).
- [ ] P2.7 Unauthenticated API behaviour (verify first, then fix only if needed):
  - Add an integration test `Api_AnonymousRequest_WithRealIdentityCookieChallenge_Returns401NotRedirect`. P3 adds a `UseIdentityCookieChallenge = true` factory option; if P3 is not merged yet, add that option to `WebAppFactoryOptions`/`WebAppFactory` now, exactly as in `$IDB/BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs`. Call `GET /api/books` without the test user header. Assert `401`, no `Location` header, and a body that is not HTML.
  - If it passes (.NET 10 suppresses cookie redirects for API endpoints), keep the test as a regression guard and change nothing else.
  - If it fails with 302, port ImprovedDb's `OnRedirectToLogin`/`OnRedirectToAccessDenied` events from `LoginFeatureExtensions.cs`, generalised to `request.Path.StartsWithSegments("/api")`, and add the matching 403 test.
- [ ] P2.8 Private responses: user-specific API responses must not be cacheable by proxies. In `BooksEndpoints` (and any endpoint that returns data for the current user), add `Cache-Control: private, no-store` and `Pragma: no-cache`. Prefer an endpoint filter `PrivateNoStoreEndpointFilter` in `BlazorAutoApp/Infrastructure/Hosting/` applied to the `/api/books` group over ImprovedDb's path-matching middleware. Add a test asserting the header on `GET /api/books` for an authenticated user.
- [ ] P2.9 App shell:
  - `BlazorAutoApp.Client/Features/AppShell/Layout/MainLayout.razor`: add the hidden probe as the first element:
    ```razor
    <span hidden
          data-testid="app-interactivity-probe"
          data-current-renderer="@RendererInfo.Name"
          data-interactive="@RendererInfo.IsInteractive.ToString().ToLowerInvariant()"></span>
    ```
    Keep the template's existing render-mode diagnostics on the Books page. The probe is the stable E2E hook.
  - `BlazorAutoApp/Components/Pages/Error.razor`: remove the "Development Mode" paragraphs (they advertise how to expose exception details). Add `data-testid="app-error-page"`, keep the request ID, add a link to `/`. Use template styling (light theme). Do not copy ImprovedDb's dark classes.
  - `BlazorAutoApp.Client/Features/AppShell/Routes/NotFound.razor`: add `data-testid="app-not-found-page"` and a link back to `/`. Keep template styling.
  - `BlazorAutoApp/Components/App.razor`: change the favicon to `href="@Assets["favicon.png"]"` (fingerprinted), as ImprovedDb did. Do not add `color-scheme: dark` or the Grumlebob SVG logo.
  - If these changes alter Tailwind classes, rebuild `tailwind.css` (3.6).
- [ ] P2.10 `docker-compose.yml` (local stack): add `APP_NODE_NAME: ${APP_NODE_NAME:-local-web}`, `App__Url: ${APP_URL:-https://localhost:${APP_HTTPS_HOST_PORT:-7186}}`, and the three local rate-limit overrides (`RateLimiting__Global__PermitLimit` default 10000, `__Api__` 1000, `__Authentication__` 1000), as ImprovedDb did. Local E2E and simulation runs from one IP otherwise hit 429. Keep the template's Grafana home dashboard path.
- [ ] P2.11 Run the gate. Open the PR. Merge when green.

### P3. Test infrastructure hardening

Goal: no leaked containers or volumes, faster and steadier tests, reusable E2E helpers. Branch `upgrade/p03-test-infrastructure`.

- [ ] P3.1 (D9) `BlazorAutoApp.Test/TestSupport/Integration/TestContainerImages.cs`: port ImprovedDb's file. Add the tmpfs constants, `ConfigurePostgreSqlData`/`ConfigureRedisData`, and `TestContainerLabels.For(purpose)` using the label scheme in 3.4.2 (`localcluster.ci.*`, repository from `GITHUB_REPOSITORY`, owner `tests`). Keep the template's image tags. Never downgrade them; check `postgres:`/`redis:` tags against CI's `docker pull` lines and keep them in sync.
- [ ] P3.2 Apply to every container builder in `WebAppFactory.cs`, `SharedIntegrationEnvironment.cs` and any other `new PostgreSqlBuilder`/`new ContainerBuilder` in the test project (`grep -rn "Builder(TestContainerImages" BlazorAutoApp.Test`): `.WithCreateParameterModifier(...)`, `.WithLabel(TestContainerLabels.For("<purpose>"))`, `.WithCleanUp(true)`. Replace `StopAsync()` with `DisposeAsync()` and aggregate dispose failures as ImprovedDb does.
- [ ] P3.3 `WebAppFactory.cs` and `WebAppFactoryOptions.cs`: port the generic options and disposal:
  - `ConfigurationOverrides` (`Dictionary<string,string?>`) and `ConfigureTestServices` (`Action<IServiceCollection>?`). Re-express the template's Books cache TTL options (`LocalListTtlSeconds`, `LocalItemTtlSeconds`, `DisableLocalCache`) through `ConfigurationOverrides` **only if** all call sites are updated in this PR. Otherwise keep them.
  - Rate-limit overrides (`Global`, `Api`, `Authentication` permit limits) with defaults 10,000/1,000/1,000 in integration tests. Tests that assert limits set low values explicitly. Find them with `grep -rn "RateLimiting" BlazorAutoApp.Test`.
  - `UseIdentityCookieChallenge` (already added in P2.7 if needed).
  - `InitializeDatabaseRespawner` (default `true`) and the clear error when it is false.
  - Idempotent `DisposeAsync` with `Interlocked.Exchange` and aggregated failures.
  - OpenTelemetry protocol/interval/timeout options.
  - Keep `WebApplicationFactory<Program>`. ImprovedDb's `<AppDbContext>` change exists only because DataImport added another `Program`.
  - In `ResetDatabaseAsync`, keep the Books cache tag resets.
- [ ] P3.4 `TestAuthenticationHandler.cs`: port the `X-Test-Roles` header (comma/semicolon separated, added as role claims). Add one test that an Admin-only endpoint (if the template has none, a test-only endpoint mapped through `ConfigureTestServices`) returns 403 without the header and 200 with `X-Test-Roles: Admin`.
- [ ] P3.5 `TestCollections.cs`: port the named collections and `[assembly: CollectionBehavior(MaxParallelThreads = 2)]`. Keep only the collections the template uses: `Integration`, `StartupIntegration`, `StartupSeed` (with `PostgresTestDatabaseFixture`), `CrossNodeRedis`, `EnvironmentMutation`, `E2E`. Put every existing test class into the right collection:
  - Tests that set process environment variables → `EnvironmentMutation`.
  - Tests that build their own factory with startup migrations → `StartupIntegration`.
  - Book seed tests → `StartupSeed`.
  - Cross-node cache tests → `CrossNodeRedis`.
  - Playwright tests → `E2E`.
  - Everything using the shared `WebAppFactory` → `Integration`.

  A test class without a collection runs in parallel with others. If it shares mutable process state, the suite becomes flaky. Run the full suite three times locally; all three must pass.
- [ ] P3.6 Port `PostgresTestDatabaseFixture.cs`, `HttpProblemDetailsAssert.cs` (replace the Books-local `ProblemDetailsAssert` if equivalent; otherwise keep both and note it) and `TestContainerLifecycleTests.cs`. The lifecycle tests must be skipped unless `RUN_TESTCONTAINER_LIFECYCLE=1`, exactly as in ImprovedDb.
- [ ] P3.7 E2E support (`BlazorAutoApp.Test/E2E/Support/`):
  - Port `E2EArtifactPaths.cs` (+ tests), `E2ETestCredentials.cs`, `E2ELocalAdminCredentials.cs` (+ tests), `E2ETestGuardTests.cs`, `ResponsiveViewport.cs`.
  - `E2ETestGuard.cs`: keep `IsEnabled` and `IsObservabilityEnabled`. Skip the LocalData/provider/responsive flags.
  - `BlazorE2ETestBase.cs`: port `WaitForInteractivityAsync()` (waits for `[data-testid=app-interactivity-probe][data-interactive=true]`), `SetViewportAsync`, `AssertNoPageHorizontalOverflowAsync`, `AssertNoVisibleBrokenImagesAsync`, `AssertImageLoadedAsync`, `AssertNoInsecureImageSourcesAsync`, `AssertNoCriticalOrSeriousAxeViolationsAsync` (injects `node_modules/axe-core/axe.min.js` from `BlazorAutoApp.Client`; P4 adds the package), `CaptureVisualAuditScreenshotAsync`, `TrackCreatedUser`, `RegisterUniqueUserAsync`, `LoginAsLocalAdminAsync`, failure-only tracing and the artifact path helpers. Remove anything referencing media canaries or synthetic environments.
  - Keep the template's `E2ETestDataCleanup.cs` (it cleans Books data).
- [ ] P3.8 Use the helpers in existing E2E tests: `RenderModeE2ETests` and `IdentityE2ETests` call `WaitForInteractivityAsync()` instead of fixed delays or renderer text polling (keep the renderer-text assertions that are the point of the test).
- [ ] P3.9 New E2E test `BlazorAutoApp.Test/E2E/AppShell/PreHydrationControlsE2ETests.cs`, modelled on ImprovedDb's: load `/` with WASM boot blocked (`page.RouteAsync("**/_framework/**", route => route.AbortAsync())`), assert the Books page's interactive buttons (for example "Add Book" for a logged-in user, or the bookcase controls) are disabled or absent in prerendered HTML, then load normally, call `WaitForInteractivityAsync()` and assert they are enabled. If the Books components do not currently disable controls before hydration, fix the components (`disabled="@(!RendererInfo.IsInteractive)"`) in this phase. That is the lesson the test protects.
- [ ] P3.10 Architecture tests:
  - Replace `EachCoreRequest_HasMatchingFeatureTestClass` with ImprovedDb's `CoreFeaturesWithUseCases_HaveFeatureTestCoverage` and add `PassiveRequestDtoConstructionTests_AreNotAllowed` (copy from `$IDB/BlazorAutoApp.Test/Architecture/Slices/FeatureSlicesArchitectureTests.cs`).
  - Delete any template test that only constructs request DTOs and asserts their properties. The new rule flags them.
  - Review `HttpClientUsageTests`, `DiWiringTests`, `EndpointSurfaceTests`, `EntityConfigurationLocationTests` and `ArchitectureTests` diffs. Port only generic helper or false-positive fixes; feature lists stay Books.
- [ ] P3.11 `RenderModeHtmlTests`: port `StaticAndAccountPages_DoNotLoadInteractiveBlazorRuntime` (use `/Account/Login`, `/not-found`) and `PublicPages_DoNotReferenceRemovedScopedCssBundle` with template routes. Skip the About-page tests.
- [ ] P3.12 Run the full gate and the lifecycle tests locally (`RUN_TESTCONTAINER_LIFECYCLE=1 dotnet test ... --filter FullyQualifiedName~TestContainerLifecycleTests`). Before and after one full test run, record `docker volume ls -q | wc -l`; the count must not grow. Put both numbers in the PR body. Merge when green.

### P4. Dependencies and tooling

Goal: safer dependency resolution without downgrades. Branch `upgrade/p04-dependencies`.

- [ ] P4.1 `Directory.Packages.props`: add `<CentralPackageTransitivePinningEnabled>true</CentralPackageTransitivePinningEnabled>`. Restore and build. If restore reports NU1109/NU1608 or a downgrade, raise the pinned version; never lower one.
- [ ] P4.2 Compare every `PackageVersion` with ImprovedDb. Keep the higher version for every package both use. Add a package only if a file ported in P2/P3 needs it. `bunit` and `AngleSharp` are needed only if you port a bUnit test; none of P2/P3 requires it.
- [ ] P4.3 Security pins: run `dotnet list BlazorAutoApp.sln package --vulnerable --include-transitive`. ImprovedDb pins `System.Security.Cryptography.Xml` 10.0.12 to override a vulnerable transitive version. Add that pin (or a newer version) only if the template's audit reports the vulnerability, and note the advisory ID in the PR.
- [ ] P4.4 `BlazorAutoApp.Client/package.json`: add `axe-core` to `devDependencies` (the version ImprovedDb uses, `^4.13.0`, or newer). Keep the newest `@tailwindcss/cli`, `tailwindcss` and `lighthouse` (the template pins Lighthouse "audit-clean"; keep that intent). Port the `overrides` block for `@parcel/watcher` **only** if `npm ci`/`npm audit` in the template fails without it; record which. Run `npm install` to regenerate `package-lock.json`, then `npm ci`, `npm audit` and `npm run css:build`, and commit `package-lock.json` and any `tailwind.css` change.
- [ ] P4.5 `.config/dotnet-tools.json`: keep the highest `dotnet-ef` version that matches the EF Core package major/minor.
- [ ] P4.6 Gate, PR, merge.

### P5. CI workflow rework

Goal: a CI that validates PRs without publishing, publishes verifiable releases from `main`, and never loses a main run. Branch `upgrade/p05-ci`. This is the riskiest phase because CI is the merge gate. Read the whole phase first.

Rules for this phase:

- The required status check name **must stay `build-test-push`** for PRs, or branch protection blocks every PR. ImprovedDb uses this name expression on the validating job:
  ```yaml
  name: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && 'validate' || 'build-test-push' }}
  ```
  and the publishing job is named `build-test-push` on main. Copy this pattern exactly. After merging, confirm in the P5 PR checks list that a check named `build-test-push` appeared and passed.
- Do not port: `select-ci-runner` and desktop/canary runner routing, `runner_pool` input, `CI_RUNNER_INVENTORY_APP_*`, the publisher harness artifact, ML/statistics/AwardPredictionLab steps, coordination tests, actionlint-from-a-PR-branch build, `Plans/Support` fixtures.
- Both jobs run on `[self-hosted, linux, x64, "${{ vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}"]` and keep the external-fork guard `github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository` on every job.

Steps:

- [ ] P5.1 (D5) Concurrency:
  ```yaml
  # Only superseded PR validation shares a cancellable group. Each main run keeps
  # its own group so release provenance cannot be displaced by another push.
  concurrency:
    group: ci-${{ github.event_name == 'pull_request' && format('pr-{0}', github.event.pull_request.number) || format('run-{0}', github.run_id) }}
    cancel-in-progress: ${{ github.event_name == 'pull_request' }}
  ```
- [ ] P5.2 Split into two jobs.
  - `validate` (PR name `build-test-push`, main name `validate`), `permissions: contents: read`, `timeout-minutes: 75`.
  - `publish-main` (name `build-test-push` on main), `needs: validate`, `if: ${{ !cancelled() && github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && needs.validate.result == 'success' }}`, `permissions: contents: read, packages: write`, `timeout-minutes: 60`.
  - Both check out with `ref: ${{ github.sha }}` and `clean: true`.
  - Use the newest major versions of `actions/checkout`, `actions/setup-dotnet`, `actions/setup-node`, `actions/upload-artifact`, `actions/download-artifact` and `docker/login-action` found in either repository.
- [ ] P5.3 `validate` job steps, in this order:
  1. Checkout.
  2. "Isolate registry credentials for this job": `DOCKER_CONFIG` in a `mktemp -d` dir under `$RUNNER_TEMP`, mode 0700 (copy from ImprovedDb).
  3. "Verify self-hosted runner profile": Linux, workspace not under `/mnt/*`, `docker info` OSType linux, `test "$(hostname)" = "node-main"` (keep the template's existing host check).
  4. `bash Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh --check` (added by P8.1, merged before P5).
  5. "Activate validated Ansible generation": `install-ansible.sh --check` and add `~/.local/share/books-ansible/current/bin` to `GITHUB_PATH` (added by P8.2).
  6. "Validate LocalCluster Ansible playbook syntax": copy ImprovedDb's step (temp inventory, empty vault, `ansible-playbook --syntax-check`).
  7. Disk check: `bash Scripts/CI/check-runner-capacity.sh` (port from ImprovedDb; it must only report and fail, never prune).
  8. Tool paths `DOTNET_INSTALL_DIR`/`DOTNET_ROOT` under `$RUNNER_TEMP` (existing).
  9. `actions/setup-dotnet` with `global-json-file: global.json`.
  10. `dotnet restore`, `dotnet format --verify-no-changes`.
  11. Shell lint (existing). Script tests: `test-with-deploy-lock.sh` (P1) plus any script tests added by later phases.
  12. actionlint with a pinned release image (`docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:<newest pinned tag>`). Do not build actionlint from source; the template does not use `concurrency.queue`.
  13. Existing validations: common release, Cloud settings, observability, deployment audit.
  14. "Setup Python": venv under `$RUNNER_TEMP`, a constraints file `Deployment/Common/ci-python-constraints.txt` (create it with pinned `jinja2`, `MarkupSafe`, `yamllint`, `PyYAML`, `pathspec` and `pip` versions; resolve current versions with `pip install jinja2 yamllint && pip freeze`), `PIP_CONSTRAINT` exported, `pip==<pinned>` installed. Copy ImprovedDb's step shape.
  15. Template render validation and yamllint (existing, now using the constraints).
  16. Setup Node 24.
  17. .NET vulnerability and deprecation audits (existing).
  18. Build: `dotnet build --configuration Release --no-restore`, then assert `BlazorAutoApp.Test/bin/Release/net10.0/BlazorAutoApp.Test.dll` and `playwright.ps1` exist.
  19. Simulation wrapper help (existing).
  20. Docker preflight pulls (existing image tags).
  21. Test: `dotnet test --configuration Release --no-build --logger "trx;LogFileName=ci.trx" --results-directory "$RUNNER_TEMP/test-results/${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}/suite"`. **Remove `TESTCONTAINERS_RYUK_DISABLED: "true"`** (P3 made disposal explicit; Ryuk is the backstop). If Ryuk cannot start on the runner, keep it disabled but say why in a YAML comment and rely on the lifecycle test.
  22. "Prove Testcontainers lifecycle cleanup": `RUN_TESTCONTAINER_LIFECYCLE=1` filter `TestContainerLifecycleTests`.
  23. Upload `*.trx` (`if: ${{ !cancelled() }}`, retention 3 days, `if-no-files-found: ignore`).
  24. `npm ci`, `npm audit`, `npm run css:build`, verify generated CSS is current (existing).
  25. `dotnet tool restore`; "Load release settings" (existing, plus `CI_IMAGE_TAG=${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`).
  26. PR/non-main only: `docker build --pull --label localcluster.ci.repository=${GITHUB_REPOSITORY} --label localcluster.ci.owner=ci-build --label localcluster.ci.run_id=... --label localcluster.ci.run_attempt=... -t "${APP_IMAGE}:${CI_IMAGE_TAG}"`, then the Docker smoke (P5.5), then remove the PR image (`docker image rm "${APP_IMAGE}:${CI_IMAGE_TAG}"`, `if: always()`, ignore "no such image"). Removing an image this job built is owned cleanup; it is not a prune.
  27. Main only: build the EF migration bundle (existing command), then `python3 Scripts/CI/migration_staging_artifact.py create --directory artifacts/migrations --bundle-filename "$MIGRATION_BUNDLE_NAME" --runtime "$MIGRATION_RUNTIME" --repository-root "$GITHUB_WORKSPACE"` (port the script; replace ImprovedDb names per 3.4.1), then upload artifact `${MIGRATION_BUNDLE_NAME}-staging-${run_id}-${run_attempt}` with the bundle and `migration-provenance.json`, retention 1 day.
  28. Final "Report runner capacity" (`df -h /opt; df -Pi /opt`), `if: always()`, no pruning.
- [ ] P5.4 `publish-main` job steps:
  1. "Validate required CI results" (copy the ImprovedDb step, removing runner-selection checks; require `needs.validate.result == 'success'` and event/ref `push|workflow_dispatch` on `refs/heads/main`).
  2. Checkout, DOCKER_CONFIG isolation, runner profile, prereqs `--check`, capacity check, tool paths, setup-dotnet with `global.json`.
  3. Load release settings (same as validate).
  4. Download the staging artifact by exact name, then `migration_staging_artifact.py validate ...`.
  5. Setup Python (constraints). Needed by the smoke and manifest steps.
  6. `docker build --pull` with labels (owner `ci-build`), tag `${APP_IMAGE}:${CI_IMAGE_TAG}`.
  7. Docker smoke (P5.5). It needs the test binaries: build the test project in this job (`dotnet build BlazorAutoApp.Test/BlazorAutoApp.Test.csproj -c Release`) before the smoke step. Do not port ImprovedDb's publisher-harness artifact.
  8. Login to GHCR with `GITHUB_TOKEN`, `docker tag ... "${APP_IMAGE}:${GITHUB_SHA}"`, `docker push "${APP_IMAGE}:${GITHUB_SHA}"`.
  9. "Resolve pushed image digest and write release manifest": copy ImprovedDb's inline Python verbatim. It is generic: it reads RepoDigests, verifies the bundle SHA-256 against provenance, and writes `artifacts/migrations/release-manifest.json` with `schema_version`, `repository`, `commit_sha`, `ci_run_id`, `attempt`, `image_ref`, `image_digest`, `ordered_migration_ids`, `bundle{file,sha256,runtime}` and `tools.dotnet_sdk`.
  10. Upload artifact named `${MIGRATION_ARTIFACT_NAME}` containing the bundle **and** `release-manifest.json`, retention 7 days.
  11. Remove the local `${APP_IMAGE}:${CI_IMAGE_TAG}` tag only (keep `:${GITHUB_SHA}` for fast redeploys; maintenance ages it out).
  12. Report capacity.
- [ ] P5.5 Docker smoke: port `$IDB/Deployment/LocalCluster/Scripts/ci-docker-smoke.sh` as `Deployment/LocalCluster/Scripts/ci-docker-smoke.sh`:
  - Labels per 3.4.2 (owner `ci-smoke`). Ownership checks compare `localcluster.ci.repository`, `owner`, `run_id` and `run_attempt`.
  - Container names `${APP_NAME}-ci-{postgres,redis,web}-${session}`, network `${APP_NAME}-ci-${session}`. Read `APP_NAME` via `read-deploy-setting.sh app_name`.
  - tmpfs for Postgres/Redis data (no volumes).
  - Image tags for postgres/redis must equal the ones in `TestContainerImages.cs` and CI preflight.
  - App env: `ASPNETCORE_ENVIRONMENT=Docker`, `Database__RunMigrationsAtStartup=true`, `Redis__AllowMissing=false`, `LocalAccounts__Enabled=false`, `Observability__OpenTelemetry__Enabled=false`, raised `RateLimiting__Api__PermitLimit`/`Global` for the smoke.
  - Replace the award-prediction checks with: wait up to 180 s for `GET /health/ready` = 200, then `GET /` contains `<!DOCTYPE html>` and the `_framework/blazor.web` script, then `GET /api/books` returns 401 without auth (P2.7).
  - Browser smoke: `pwsh BlazorAutoApp.Test/bin/Release/net10.0/playwright.ps1 install chromium`, then `RUN_E2E=1 E2E_BASE_URL=... E2E_HEADLESS=1 dotnet test ... --no-build --filter "FullyQualifiedName~RenderModeE2ETests|FullyQualifiedName~PreHydrationControlsE2ETests"`. Keep the list in `BlazorAutoApp.Test/E2E/Support/BrowserSmokeCatalog.cs` (port and adapt) so the filter is not duplicated.
  - Do not use `playwright install --with-deps` (it runs apt; D12). If Chromium system deps are missing, add them to `ensure-actions-runner-prereqs.sh --provision` instead.
  - Port `Deployment/LocalCluster/Scripts/Tests/test-ci-docker-smoke.sh` (resource lifecycle test with Docker stubbed) and run it in `validate`.
- [ ] P5.6 Remove the `prune-migration-artifacts` job from `ci.yml`. P8 moves artifact retention to maintenance. If P8 will not merge soon after P5, keep the job until then but scope its `--keep` to at least 3.
- [ ] P5.7 Audit updates (3.7). Port ImprovedDb's CI rules where they apply: validate/publish split, release manifest present, migration upload after image push, no `actions/setup-python`, no GitHub npm cache, no `TESTCONTAINERS_RYUK_DISABLED` (unless you kept it with a comment; then require the comment). Port `$IDB/Deployment/Common/Scripts/Tests/test_release_contract.py` and `test_ci_provenance.py` if they test files you ported, and run them in `validate`.
- [ ] P5.8 Before pushing, run actionlint and the audit locally. After pushing, watch the PR run. Because PR runs skip `publish-main`, also verify the main path right after merge: watch the first `main` run, and confirm it uploaded `${MIGRATION_ARTIFACT_NAME}` with `release-manifest.json` (`gh run view <id> --json artifacts` or the UI) and pushed `${APP_IMAGE}:${sha}`. If main fails, fixing it is the immediate next task.

### P6. Dependabot auto-merge hardening

Goal: auto-merge only exactly-tested, low-risk Dependabot PRs. Branch `upgrade/p06-dependabot`.

- [ ] P6.1 Rewrite `.github/workflows/auto-merge-dependabot.yml` from `$IDB/.github/workflows/auto-merge-dependabot.yml` with these edits:
  - Runner label fallback `localcluster-books`.
  - Remove the `elif [[ "$SOURCE_RUN_HEAD_BRANCH" == 'main' ]]` branch that checks `display_title` for `pool=`. The template CI has no pool routing.
  - Keep: workflow-run identity verification (conclusion, event, head branch/SHA, attempt, workflow path `.github/workflows/ci.yml`, URL), open-PR checks, `head_sha == SOURCE_SHA`, base `main`, author `dependabot[bot]`/`app/dependabot`, deployment-surface exclusion (`Dockerfile`, compose files, `Deployment/`), the action-version-only rule for workflow files, disabling existing auto-merge when manual review is required, `mergeStateStatus` polling, BEHIND refresh via `update-branch` with `expected_head_sha` and the Workflows-permission error message, and the dispatch path (`workflow_dispatch` inputs + attaching the `build-test-push` check to the PR head after verifying head tree equals merge tree).
  - Keep the template's `semver-major` label exclusion, which ImprovedDb dropped: major bumps need a human.
  - Merge with `gh pr merge "$pr" --merge --auto`. Do not pass `--delete-branch`; ImprovedDb found deleting Dependabot branches breaks Dependabot's own tracking. If the template's merge convention is squash, use `--squash --auto`.
  - `GH_TOKEN: ${{ secrets.GH_TOKEN || secrets.GITHUB_TOKEN }}`. Document the optional `GH_TOKEN` secret (fine-grained PAT: Contents write, Pull requests write, Workflows write) in P11. Without it, branch refresh of workflow-file PRs is skipped with a clear summary message; nothing else breaks.
- [ ] P6.2 Add the `notify-dependabot-automerge` job to `ci.yml` (copy from ImprovedDb). It dispatches the auto-merge workflow after a successful `workflow_dispatch` CI run on a `dependabot/*` branch by `github-actions[bot]`. Runner label fallback `localcluster-books`.
- [ ] P6.3 Ensure `auto-merge-dependabot.yml` and `ci.yml` are listed in the audit's workflow contract (ImprovedDb commit "include Dependabot callback in workflow contract"). actionlint must pass.
- [ ] P6.4 Verification: no live Dependabot PR is needed to merge P6. After merge, the next Dependabot PR must show either a merge or an "Auto-merge deferred: <reason>" step summary. Record the first observed outcome in the P12 closeout.

### P7. CD hardening

Goal: deploy exactly what CI built and verified, with no PAT and less downtime. Branch `upgrade/p07-cd`.

- [x] P7.1 Port release helpers (3.5): `Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py` (ImprovedDb version with `--expected-run-id/--expected-run-attempt/--json`; keep `find-successful-ci-run.sh` as the wrapper and make it print the run id as before), `Deployment/Common/Scripts/validate_release_manifest.py`, `Deployment/Common/Scripts/Component/lib/release_artifact.py` (replace the `improveddb-migration-staging-` prefix check with one derived from the configured bundle name) and `Deployment/LocalCluster/Scripts/validate-ci-release-artifact.py`. Port their tests (`test_ci_provenance.py`, `test_release_artifact.py`, `test_ci_release_artifact.py`) and run them in CI `validate`.
- [x] P7.2 `cd-localcluster.yml` inputs: keep `run_migrations` (choice, default `"true"`; template users deploy schema changes more often than they care about 30 s of downtime) and add optional `target_sha` (string, default empty = `GITHUB_SHA`). Do not add ImprovedDb's `workflow_sha`, `operation_id`, `request_id`, `artifact_id`, `artifact_digest`, `manifest_sha256`, `image_digest` or `refresh_rating_ranks` inputs. The workflow resolves those itself.
- [x] P7.3 `cd-localcluster.yml` job settings: `timeout-minutes: 60`, `concurrency: group: cd-localcluster, cancel-in-progress: false` (do not add `queue: max`; released actionlint rejects it), `run-name: "CD LocalCluster @ ${{ inputs.target_sha || github.sha }}"`.
- [x] P7.4 Steps, in order:
  1. Require main (existing).
  2. Resolve and validate the target: `TARGET_SHA="${INPUT_TARGET_SHA:-$GITHUB_SHA}"`, regex `^[0-9a-f]{40}$`, export via `GITHUB_ENV`.
  3. DOCKER_CONFIG isolation (copy).
  4. Verify node-main runner (existing).
  5. Checkout with `fetch-depth: 0`, then `git merge-base --is-ancestor "$TARGET_SHA" "$GITHUB_SHA"`. Only commits already on main can deploy.
  6. Common release settings validation; load deployment settings (existing; `APP_VERSION=$TARGET_SHA`).
  7. "Require successful CI for this commit": `python3 Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py --target-sha "$TARGET_SHA" --json`. Parse the run id and attempt into `CI_RUN_ID`/`CI_RUN_ATTEMPT`. The run must be a `push` to `main` and the `publish-main` job must have succeeded; extend the script if it does not check this.
  8. Download artifact `${MIGRATION_ARTIFACT_NAME}` from `run-id: ${CI_RUN_ID}` **always**, not only when migrating; the manifest is needed in both cases.
  9. Login to GHCR with `github.actor` / `secrets.GITHUB_TOKEN`; `docker pull` by tag; write RepoDigests JSON (copy ImprovedDb "Capture registry release descriptor", adapted to tag input).
  10. `validate_release_manifest.py` with `--expected-sha "$TARGET_SHA" --expected-ci-run-id "$CI_RUN_ID" --expected-ci-run-attempt "$CI_RUN_ATTEMPT" --expected-image "$APP_IMAGE" --expected-bundle-name "$MIGRATION_BUNDLE_NAME"`. Export the printed digest as `RELEASE_IMAGE_DIGEST`.
  11. `install-ansible.sh --check` and add its `bin` to `GITHUB_PATH` (P8.2).
  12. Vault password file (existing). Write a temporary extra-vars JSON file (umask 077, under `$RUNNER_TEMP`) with `vault_ghcr_username: ${{ github.actor }}` and `vault_ghcr_token: ${{ secrets.GITHUB_TOKEN }}`. Pass it with `-e @"$GHCR_EXTRA_VARS_FILE"`; extra vars override vault values. Delete it in the final `if: always()` step together with the vault password file.
  13. Capacity check `check-node-main-capacity.sh` (P8.3; until P8 merges, inline `df` with a 20 GiB threshold).
  14. Deployment preflight (existing).
  15. Deploy (existing two steps for with/without migrations, wrapped in `with-deploy-lock.sh`). Add `-e "release_image_digest=${RELEASE_IMAGE_DIGEST}"` and `-e @"$GHCR_EXTRA_VARS_FILE"`.
  16. Acceptance check; optionally `verify-release-identity.sh` (P7.8); observability doctor (existing).
  17. Cleanup of temporary files (existing, extended).
- [x] P7.5 Ansible changes (`site.yml`, roles):
  - Add the play "Stage the exact app image before any app interruption" (copy from ImprovedDb) before "Stop app containers before migration". It pulls `app_image@release_image_digest` (fallback `:app_version` when the digest is empty, for manual deploys) with a temporary `DOCKER_CONFIG`, retries 5 × 15 s, and asserts RepoDigests contains the digest.
  - `roles/app/tasks/main.yml`: replace "Log in to GHCR" + "Pull and start app container" with ImprovedDb's single task "Pull application image with command-owned registry credentials" (temporary `DOCKER_CONFIG`, `docker login`, `docker compose up -d --pull always --remove-orphans`, `no_log: true`).
  - `app.env.j2` + `compose/app-server/docker-compose.yml`: add `APP_IMAGE_REF` = `app_image@release_image_digest` when set, else `app_image:app_version`. The compose `image:` becomes `${APP_IMAGE_REF:?APP_IMAGE_REF is required}`. Keep `APP_VERSION` for telemetry. Update `validate-rendered-templates.sh` and the audit for the new variable.
  - "Deploy app servers": add `serial: 1` and `any_errors_fatal: true`. The role already waits for `/health` before moving on, so one node keeps serving during no-migration deploys.
  - Move the "Deploy Caddy and Cloudflare Tunnel" play after "Deploy app servers", as ImprovedDb did ("after app readiness"). Keep a Caddy/cloudflared play before migrations **only** if a fresh cluster needs Caddy before the app exists; otherwise one play after the apps is enough. Test with `--syntax-check` and the render validation.
  - Do not port coordinator, data-runner, rank-refresh, people-image or statistics plays.
- [x] P7.6 Remove the PAT requirement:
  - `vault.example.yml`: delete `vault_ghcr_username`/`vault_ghcr_token` lines, or mark them optional for manual deploys only (manual `deploy.sh` runs need some registry credential; recommend `gh auth token`-derived values passed with `-e`).
  - `validate-vault.py`/`check-vault.sh`: make these keys optional.
  - `cd-cloud.yml`: replace `CLOUD_GHCR_USERNAME`/`CLOUD_GHCR_TOKEN` secrets with `github.actor`/`secrets.GITHUB_TOKEN` (ImprovedDb hunk). Keep every other template Cloud change.
  - `Deployment/Cloud/Scripts/configure-github-environment.sh`: remove the interactive GHCR secret prompts (ImprovedDb hunk).
  - The workflow needs `permissions: packages: read`; it already has it.
- [x] P7.7 Manual `deploy.sh`: keep it (the template supports manual deploys from a control machine). Make it pass `-e release_image_digest=` when the operator supplies `--digest sha256:...` (optional flag), and print a warning that manual deploys skip CI provenance checks. Do not disable it as ImprovedDb did.
- [x] P7.8 Optional, recommended: port `verify-release-identity.sh` so acceptance checks that every app node runs the expected image digest (`docker inspect` of the running `web` container). Strip ImprovedDb names; port its test.
- [x] P7.9 Gate (render validation with and without `release_image_digest`, `ansible-playbook --syntax-check`, audit), PR, merge. A live deploy is **not** part of P7 (decision Q1, section 10).

### P8. Runner and cluster maintenance

Goal: replace per-CI cleanup with one safe scheduled job; make CI check-only. Branch `upgrade/p08-maintenance`. P8.1 and P8.2 may be merged before P5 if P5 needs them; keep them as a separate small PR `upgrade/p08a-check-only-provisioning`.

- [x] P8.1 (D12) `Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh`: port ImprovedDb's `--check`/`--provision` split, bounded `apt_run` (3 attempts, `timeout 300`), curl timeouts and fail-closed sudo check. No-argument mode stays "provision" for backward compatibility. Port `test-install-ansible-check.sh`-style tests if useful.
- [x] P8.2 (D12) `Deployment/Common/Scripts/install-ansible.sh` (and `Deployment/LocalCluster/Scripts/install-ansible.sh` wrapper): port the generation layout (`$INSTALL_ROOT/ansible-core-$VERSION` + `.ready` marker + `current` symlink), `--check` validation, `flock` serialisation and bounded apt. Keep the template's pinned Ansible version unless ImprovedDb's is newer. Port `$IDB/Deployment/LocalCluster/Scripts/Tests/test-install-ansible-check.sh` and run it in CI. Update `setup-control-machine.sh` and Cloud callers to call `--provision` explicitly.
- [x] P8.3 Capacity: port `localcluster-capacity-thresholds.sh` (20 GiB / 5% inodes on node-main, 2 GiB app nodes, 4 GiB db; keep values, document them as defaults) and `check-node-main-capacity.sh` (exit 0 ok, 1 cannot measure, 2 below reserve). Port `Scripts/CI/check-runner-capacity.sh` if P5 did not.
- [x] P8.4 `prune-docker-residue.sh`: port ImprovedDb's low-disk handling and the result codes `0` (done/no-op), `1` (failure), `2` (insufficient capacity after cleanup), `75` (deferred, protected candidates skipped). Replace `com.improveddb.ci.repository=ImprovedDb` with `localcluster.ci.repository=${GITHUB_REPOSITORY}`. Keep P1.B3's rule: unscoped prunes only with `--include-unlabelled-host-residue`. Never prune volumes; the script must print "Docker volumes are protected". Port `test-prune-docker-residue-low-disk.sh`.
- [x] P8.5 Port `prune-actions-runner-residue.sh` (runner `_diag`, old runner versions, `_work/_temp` older than thresholds; protects active runner versions and all workspaces) and its test `test-prune-actions-runner-residue.sh`.
- [x] P8.6 Port `prune-cluster-docker-residue.sh` (runs scoped image cleanup on app/db nodes through Ansible). Confirm it touches only images of this app's `app_image` repository plus dangling images older than the threshold. If it prunes anything unscoped, scope it.
- [x] P8.7 Port `prune-ci-residue.py`. Set `REPOSITORY` from `GITHUB_REPOSITORY`, `PREFIX = "localcluster.ci."`, `OWNERS = {"ci-smoke", "ci-build", "tests"}`, and network-name regex `^<app_name>-ci-[a-z0-9][a-z0-9_.-]*$`. Replace `from deploy_lock import require_lock` with a check that `LOCALCLUSTER_DEPLOY_LOCK_TOKEN` is set (the script must run under `with-deploy-lock.sh`). Port `test_prune_ci_residue.py`.
- [x] P8.8 Port `run-localcluster-maintenance.sh`: stages `runner`, `ci-residue`, `docker`, `remote-docker`, volume inventory (report only), disk/inode report, final capacity check. Remove the `source-downloads` stage and the `deploy_lock.py` call. It re-executes itself under `with-deploy-lock.sh` with a 300 s lock timeout. Port `test-localcluster-maintenance.sh`.
- [x] P8.9 Workflow `.github/workflows/localcluster-docker-maintenance.yml`: port ImprovedDb's file. Schedule `17 3 * * 1-6` and `17 3 * * 0` (keep the minute offset to avoid the top of the hour). Per Q3 (section 10), ship the `schedule:` block commented out with a note telling forks to enable it, and keep `workflow_dispatch`. Use runner label fallback `localcluster-books`. Delete the "Capture pending coordinator artifact references" step. The artifact-retention job instead passes `--protect-run-id <id>` for the run ids used by the last two successful `CD - Deploy LocalCluster` runs (P8.10).
- [x] P8.10 Artifact retention: diff `prune-actions-artifacts.py` in both repos (the template has its own 2026-06-19 hardening; keep it). Add `--protect-run-id` (repeatable): artifacts from those CI runs are never deleted. In the workflow, compute protected runs with `gh run list --workflow cd-localcluster.yml --status success --limit 2 --json databaseId,headSha`, then map each `headSha` to its CI run through `find-successful-ci-run.py --target-sha`. If any lookup fails, skip deletion entirely (fail closed). Keep `--keep 2` as the floor. Port `test_prune_actions_artifacts.py`, adapted.
- [x] P8.11 Deferred optional workflow (see triage closeout). Optional: port `.github/workflows/localcluster-readonly-diagnostics.yml` as a manual (`workflow_dispatch`) read-only report: disk/inodes, lock status (`release-deploy-lock.sh --inspect`), `docker ps` for this app, runner versions. Strip ImprovedDb sections.
- [x] P8.12 `install-github-runner.sh`: port the fail-closed identity handling. Never auto-delete a runner directory with unreadable identity; fail with instructions. Port the `printf %q` quoting fixes. Skip `ci_runner_contract.py`, `CI_RUNNER_LABEL` and desktop label logic. Port `check-github-runner.sh` changes only if they do not depend on `ci_runner_contract.py`.
- [x] P8.13 Agent guardrail test (generic part, may also land in P10): `DockerCleanupScripts_DoNotPruneVolumes`. Add the "Docker volumes are protected" text to `prune-docker-residue.sh` if missing.
- [x] P8.14 Gate, PR, merge. Do not run the maintenance workflow against node-main as part of this plan (Q1/Q3). Its script tests in CI are the verification; the operator runs it manually when they choose.

### P9. Local developer ergonomics

Branch `upgrade/p09-local-dev`.

- [ ] P9.1 Port `Scripts/PruneLocalDockerResidue.ps1`. Replace `improveddb-web` with the template's Compose project/image name (check `docker compose config --images`). Keep its rules: dangling images immediately, stopped containers > 24 h, unused networks > 24 h, builder cache > 48 h, `-Aggressive`, `-DryRun`, never volumes.
- [ ] P9.2 `Scripts/RunLocal.ps1`: after a successful build/start, call `PruneLocalDockerResidue.ps1` unless `-SkipDockerCleanup` is passed. Do **not** port the agent-task registration, port reservation or per-worktree Compose project naming; they depend on ImprovedDb's coordination scripts. `-StopStack` is optional: port it only in the simple form (`docker compose down --remove-orphans`, plus `--volumes` when combined with `-ResetDatabase`).
- [ ] P9.3 `Scripts/AnalyzeSimulationReports.ps1`: review the +6/-1 diff; port only if generic.
- [ ] P9.4 Verify on a Windows or pwsh-capable machine: `pwsh -NoProfile -Command "& ./Scripts/PruneLocalDockerResidue.ps1 -DryRun"` prints commands and deletes nothing. If no Docker is available, run it with a stub `docker` function and say so in the PR.

### P10. Agent rules and repository hygiene

Branch `upgrade/p10-agent-rules`.

- [x] P10.1 Create `AGENTS.md` at the template root. Keep it under 60 lines and portable. Include:
  - Plans: tracked under `Plans/`; scratch under `Plans.local/` (ignored). A plan-driven change is complete when merged to `main` with CI green; record the merge commit in the plan or PR.
  - Code changes go through a PR with the required `build-test-push` check; docs-only changes may follow the repository owner's documentation rule.
  - Run the local gate (copy the command list from `docs/Test.md`) before pushing; do not use CI as the first test run.
  - Hard stops: no `docker volume prune` or unscoped prunes, no deleting deployment locks, no secrets in git, no force-push to `main`, no deploy dispatch without operator authorisation, no `git add -A`.
  - Keep build and test sequential in one checkout.
  - Machine-specific paths, hosts, keys and IPs never go in tracked files.
  - Do not copy coordination-script rules from ImprovedDb (`StartAgentTask.ps1` and the rest do not exist in the template).
- [x] P10.2 Add `CLAUDE.md` containing one line, `See AGENTS.md.`, so Claude Code sessions load the same rules. Keep `.codex/config.toml` as is.
- [x] P10.3 `.gitignore`: remove `/Plans/` from ignored paths and the comment "Use docs/plans for retained plans"; add `/Plans.local/` and `.claude/settings.local.json`. Create `Plans/README.md` explaining the convention. Leave existing `docs/plans` content where it is; mention it in `Plans/README.md` as historical.
- [x] P10.4 Create `docs/Requirements.md` for the template, adapted from ImprovedDb's with product lines removed:
  - Product routes must work in SSR/prerender and after WASM hydration through `InteractiveAuto`. Do not force `InteractiveServer` to hide Auto bugs.
  - Bounded prerender payloads; `PersistentComponentState` only for bounded public data.
  - Components use Core contracts or feature state, never raw `HttpClient`.
  - Tailwind first; rebuild and commit `tailwind.css`.
  - Public pages: useful SSR content, no N+1 queries, bounded payloads, stable layouts, cache behaviour that works across app nodes.
  - Interactive controls rendered during prerender are disabled until interactive (P3.9).
  - User-specific API responses are `private, no-store` (P2.8).
  - Redis is required outside development/test. Observability fails open.
  - Test the risk: solution gate for normal changes, E2E for browser/render-mode workflows, Lighthouse when first load changes.
  - Never log or commit secrets, auth headers, cookies or raw request bodies.
- [x] P10.5 `BlazorAutoApp.Test/Architecture/AgentGuardrailTests.cs`: port these tests only. `LocalClusterWorkflows_DoNotUseActionsSetupPython`, `DotnetBuildAndTest_AreNotInSameWorkflowStep`, `DockerCleanupScripts_DoNotPruneVolumes` (if not added in P8), `LocalClusterCd_RequiresSuccessfulCiForSelectedCommit` (adapted to the P7 needles: `find-successful-ci-run.py`, `validate_release_manifest.py`, `git merge-base --is-ancestor`). Skip DataImport/CurrentPC tests. If P7 is not merged yet, add the CD test in P7 instead.
- [x] P10.6 Port `.github/actionlint.yaml` only if actionlint warns about the custom runner labels (`localcluster-books`); list the labels there.
- [x] P10.7 Gate, PR, merge.

### P11. Documentation

Branch `upgrade/p11-docs`. Edit template docs. Do not paste ImprovedDb text that mentions its product or values.

- [x] P11.1 `docs/HowToForkThisRepo.md`:
  - §1 table: add `inventory_dns_suffix` (optional) and a note that all node values come from the fork's own `machines.yml`.
  - New note in §2: apps sharing nodes share host-level services (Caddy, cloudflared, Docker, the deploy lock). Keep `cloudflared_version` and other host-level versions aligned across every app on the same nodes, because the last deploy wins.
  - §8: scan each node's host key into a temporary file, compare its fingerprint on the node console, and append that same key to `known_hosts` only after it matches. Manual deploy paths use strict host-key checking.
  - §12: the vault no longer needs `vault_ghcr_username`/`vault_ghcr_token`; CD uses the workflow token. Remove the PAT instructions.
  - §14: optional `GH_TOKEN` secret for Dependabot branch refresh (P6). Keep "Workflow permissions must allow packages: write".
  - §15: CI now has `validate` and `publish-main`. Main publishes the image, migration bundle and `release-manifest.json`. PRs never push images.
  - §16: `target_sha` input (optional); CD deploys only commits on `main` with successful CI and a valid manifest.
  - §17: mention `verify-release-identity.sh` if ported.
  - New section: daily maintenance workflow, what it deletes and never deletes, and the exit codes.
  - §19 checklist: update accordingly.
- [x] P11.2 `Deployment/LocalCluster/HowToDeployLocalCluster.md`: port these ImprovedDb sections, generalised: runner policy (self-hosted only; external fork PRs skipped before runner allocation; no untrusted code on self-hosted runners), release manifest paragraph, "Runner And Docker Storage Maintenance", low-disk recovery commands, "Deployment lock" (new: how to read `owner`, `release-deploy-lock.sh --inspect/--release`, never delete by age), the known_hosts note, and `--check` vs `--provision`. Remove the GHCR PAT instructions.
- [x] P11.3 `Deployment/LocalCluster/Scripts/README.md`: document every new script (`release-deploy-lock.sh`, `ci-docker-smoke.sh`, capacity scripts, prune scripts, maintenance, validate-inventory-dns, verify-release-identity) and exit codes.
- [x] P11.4 `Deployment/Common/README.md`: release manifest, provenance and validation helpers.
- [x] P11.5 `docs/Test.md`: test collections and what goes where (P3.5), tmpfs/labels/lifecycle test, raised integration rate limits and how to lower them per test, E2E helpers (`WaitForInteractivityAsync`, axe, overflow), the CI Docker smoke, and the local gate list (the same list as AGENTS.md references).
- [x] P11.6 `docs/HowToRunLocally.md`: port ImprovedDb's "Local Docker Storage Maintenance" section with template names.
- [x] P11.7 `docs/HowToAddANewFeature.md`: link `docs/Requirements.md`; add the lessons: disable controls before hydration; `PersistentComponentState` only for bounded data; put a schema version in cache keys so a deploy that changes a cached response shape does not read old entries (`books:v2:...`); user-specific responses `private, no-store`; no passive DTO tests; feature-owned operational entities may live in the server feature `Persistence` folder.
- [x] P11.8 `README.md`: add `docs/Requirements.md`, `AGENTS.md` and `Plans/` to "Start Here" and "Repository Layout"; update the CI description (validate/publish, manifest, smoke) and the LocalCluster description (maintenance workflow).
- [x] P11.9 `docs/MigrateProjectPlanningPrompt.md`: add `AGENTS.md` and `docs/Requirements.md` to "First actions" reading list; replace "docs/MigrateProjectPlan.md" with "Plans/MigrateProjectPlan.md" if P10.3 made Plans tracked; mention the release manifest in CI/CD context.
- [x] P11.10 Link check: every relative Markdown link in changed `.md` files must resolve to an existing file (write a 10-line Python script that finds `](target)` links, skips `http`/`#` targets, and checks the path relative to the file). Gate, PR, merge. Docs-only PRs still run CI; that is fine.

### P12. Integration and closeout

- [x] P12.1 Confirm every phase PR is merged and `main` CI is green on the final merge commit. Record: final template `main` SHA, CI run URL, list of PRs.
- [x] P12.2 Walk the triage inventory: every PORT/ADAPT/REVIEW row must be handled or have a written reason. Add a short "Execution notes" section at the end of `Plans/Support/BlazorAutoAppTemplateUpgrade/FileTriage.md` (in this repository). Include rows you handled differently from the table.
- [x] P12.3 Fresh-fork rehearsal (no deploy). In a temporary clone of the upgraded template, follow `docs/HowToForkThisRepo.md` §1–§9 with fake values (`APP_SLUG=rehearsal`, IPs from `192.0.2.0/24`, hostname `rehearsal.example.com`). Run `validate-common-release.sh`, `validate-deploy-settings.sh`, `generate-inventory.sh` (with a fake `machines.yml`), `summary.sh`, `validate-rendered-templates.sh` and the audit. Every step must pass or fail with a clear message. Fix doc or script gaps found. Do not push the rehearsal clone.
- [ ] P12.4 Skipped by decision Q1 (section 10). Kept for a later follow-up: live deploy, dispatch `CD - Deploy LocalCluster` with `run_migrations=true` on the template's own cluster configuration, after confirming with the operator that the template's committed inventory points to machines they want changed (section 9). Watch it to completion, run `acceptance-check.sh`, record the run URL and deployed digest. If it fails, stop and report; do not retry blindly.
- [x] P12.5 Record the P0–P12 closeout with the final template SHA and date. The overall plan status remains "executing" until the required P13 live test and P13.13 closeout are complete. Delete merged upgrade branches in the template after recording each branch's last SHA in the closeout.

### P13. LocalSingleNode deployment target (tested on node-demo)

Goal: a fork can deploy the whole app (web, PostgreSQL, Redis and a reverse proxy) to **one chosen local PC**. That PC runs its own CD runner and deploys to itself. The first real target is `node-demo`, a freshly installed Linux Mint PC on the operator's LAN. A newly cloned project enables `localsinglenode`, `localcluster`, `cloud`, or several of them, with one repository variable.

Ship it as four PRs, in this order. Each one must pass the local gate (3.6) and `build-test-push`, and is squash-merged before the next starts:

| PR | Branch | Steps |
| --- | --- | --- |
| P13a | `upgrade/p13a-common-building-blocks` | P13.1, P13.2 |
| P13b | `upgrade/p13b-target-selection` | P13.3 |
| P13c | `upgrade/p13c-local-single-node` | P13.4 to P13.9 |
| P13d | `upgrade/p13d-single-node-docs` | P13.10, P13.11 |

Then do the live test (P13.12) and the closeout (P13.13).

Done when all four PRs are merged with green `main` CI, the node-demo live test (P13.12) passes every check, and 11.1 records the evidence.

#### P13.A Design decisions (2026-10-08; the operator delegated these, see Q4 and Q5)

| ID | Decision | Reason |
| --- | --- | --- |
| S1 | New top-level folder `Deployment/LocalSingleNode/`, a peer of `Deployment/LocalCluster/` and `Deployment/Cloud/`. It is not a LocalCluster profile. | The topology differs: one Compose project, no `app_servers`/`node_db`/`load_balancer` groups, no traffic between nodes, and no SSH. The LocalCluster `caddy` and `firewall` roles loop over those groups (verified 2026-10-08), so they cannot serve one node unchanged. |
| S2 | Only pieces the single node actually reuses move to `Deployment/Common/`. The exact list is in P13.2. No compatibility shims at old paths. | Keeps the move small enough to prove that LocalCluster is unchanged. New targets never reach into another target's folder. |
| S3 | Targets are enabled with the repository variable `DEPLOY_TARGETS`, a comma-separated list such as `localcluster,localsinglenode`. Every CD and maintenance workflow checks it in its first step and stops with a clear message when its target is missing. The template repository uses `localcluster,localsinglenode`, set by the agent (Q5). | One visible switch per fork. A disabled target cannot be dispatched by mistake. |
| S4 | Deleting unused target folders is **not** part of P13 (section 8). Forks keep all folders, and the docs say which folders an unused target can ignore. | CI, the deployment audit and the Docker smoke live under `Deployment/LocalCluster/`. Deleting that folder would break CI. Making every folder removable is a separate refactor. |
| S5 | One Compose project per app, named `<app_name>`, at `/opt/<app_name>`. It has three services: `web`, `postgres`, `redis`. Its network has a fixed subnet `docker_subnet` (default `172.30.10.0/24`, unique per app on the node). `web` publishes `127.0.0.1:<app_port>`. `postgres` and `redis` publish only `127.0.0.1:<port>`, used by the migration bundle and backups. Nothing binds `0.0.0.0` except host Caddy. | The LAN can reach only the reverse proxy. A fixed subnet lets the app trust forwarded headers from exactly that network (S6). |
| S6 | Host Caddy is shared by all apps on the PC. Each app owns only `/etc/caddy/sites/<app_name>.caddy` and one LAN port, `lan_http_port`: 80 for the first app, then 8081, 8082 and so on. The site addresses are `http://<node name>.local:<lan_http_port>` (avahi mDNS, installed by default on Mint) and `http://<node IP>:<lan_http_port>`, plus any extra `lan_hostnames`. TLS is off, and the `http://` prefix stops Caddy from trying ACME certificates on a LAN. UFW opens `lan_http_port` to the LAN only. The app trusts forwarded headers through `ForwardedHeaders__KnownNetworks__0=<docker_subnet>`. A Cloudflare tunnel is deferred (section 8). | The template app has no HTTPS redirection, no HSTS and no secure-only cookie policy (checked on template `main`, 2026-10-08), so sign-in works over LAN HTTP; P13.12 proves it. Ports separate apps without extra DNS. mDNS cannot publish `app.node-demo.local` names without extra avahi aliases. |
| S7 | CD runs **on the node itself**. A self-hosted runner on node-demo runs as user `deploy`, with label `localsinglenode-<app_name>` (override with `vars.LOCALSINGLENODE_RUNNER_LABEL`). Ansible uses `ansible_connection: local`. As on LocalCluster nodes, `deploy` is in the `docker` group and has passwordless sudo. | No SSH keys or known_hosts. LocalCluster already relies on passwordless sudo (`install-github-runner.sh` runs `sudo ./svc.sh`, and roles use `become`). The `docker` group is root-equivalent anyway, so sudo adds no new trust. The docs say this plainly. |
| S8 | Template CI does not move. Every CI job's runner label becomes `vars.CI_RUNNER_LABEL \|\| vars.LOCALCLUSTER_RUNNER_LABEL \|\| 'localcluster-books'`, so a one-PC fork can run CI on its single node without a "localcluster" name. | Books CI is unchanged. Forks get a neutral setting. |
| S9 | Deploy by digest from the verified release manifest, with the same CI gate as P7: `target_sha` must be an ancestor of `main`, `find-successful-ci-run.py` must find successful CI, and `validate_release_manifest.py` must pass. A deploy has a short downtime: pull, stop `web`, migrate if asked, start `web`, health check. `postgres` and `redis` restart only when their image or settings change. | Same release safety as LocalCluster. A single instance cannot roll. |
| S10 | Same lock: `/tmp/localcluster-deploy.lockdir`, taken through `with-deploy-lock.sh` (moved to Common). Do not rename the directory or the `LOCALCLUSTER_DEPLOY_LOCK_*` variables. | All apps on one PC must share one lock, including apps deployed by older versions of the scripts. |
| S11 | Secrets stay on the node. `bootstrap-node.sh` generates `/etc/<app_name>/secrets.yml` (independent 48-character cryptographically random alphanumeric PostgreSQL and Redis passwords from Ansible’s password lookup), owner `deploy`, mode `0600`, and never overwrites an existing file. CD passes it to Ansible with `-e @/etc/<app_name>/secrets.yml`. There is no GitHub secret, no vault password and no committed vault. | One machine: the secrets never leave it, and there are fewer manual steps. Backups copy the file (S12). |
| S12 | A nightly systemd timer, `<app_name>-backup.timer`, runs `pg_dump -Fc` through `docker compose -p <app_name> exec -T postgres` into `/opt/<app_name>-backups`. It also copies `secrets.yml`, keeps 7 days, and writes `last-success` with a timestamp. `verify-backup.sh` restores the newest dump into a throwaway container and counts tables. The docs say a single disk is not a backup, and tell the operator to copy the folder elsewhere. | A single node has no second machine to protect the data. |
| S13 | Observability is off (`observability_enabled: false`). It is not part of P13. | Keeps the first version small. |
| S14 | Machine facts are **detected, not typed**, on the actual deployment node; the node name comes from an explicit request to set up that machine ("you are node-demo"). Bootstrap reads the hostname, the IPv4 address and CIDR of the default-route interface (`ip -4 -o route show default`, `ip -4 -o address show dev <if> scope global`) and the install user (`id -un`). It shows them; the operator confirms the intended native host/address by running the printed `--yes` command. It validates them and writes `/etc/localsinglenode/machine.yml`. Each CD run detects the address again; if it changed, CD logs a warning, uses the live value and updates the file. Only the operator’s explicit current-node setup request and `--node` permit bootstrap to change the hostname. No node-specific value enters reusable configuration. `machine.example.yml` documents optional overrides only. For this live test, compare the detected address with the operator's fixed lease `192.168.0.212` before bootstrap. If it differs, resolve the discrepancy before continuing; detect the LAN CIDR instead of inferring `/24` from the IP. | Hand-edited IPs and CIDRs are the most likely operator error. The fixed lease is already configured for node-demo. Detection still keeps forks portable and confirms the intended node. |
| S16 | One acceptance script, `Scripts/Test-DeployedSite.ps1`, compatible with Windows PowerShell 5.1 and PowerShell 7. It is used by CI's Docker smoke, by CD on the node, by maintenance and by the operator's main PC (`-Node <name>` or `-BaseUrl <url>`). It uses HTTP only: no browser, no .NET SDK, no repository clone. | The checks the operator runs are the same code CI runs on every PR, so they cannot rot. Browser behaviour of the same image digest is already proven by CI's Playwright smoke. |
| S17 | Bootstrap imports the GitHub user's public SSH keys (`https://github.com/<login>.keys`, login from `gh api user`) into the install user's `authorized_keys`. `ssh_hardening` (no password SSH) is applied **only if** at least one key was imported; otherwise password SSH stays on, and bootstrap says so. | No lockout and no `ssh-copy-id` step. |
| S18 | The reboot check is done by the agent: maintenance input `reboot_check` starts a root-owned helper that waits for the whole GitHub run to complete successfully, then waits 30 seconds before rebooting. Failed or cancelled runs never reboot; a later `acceptance_only` run proves recovery. | Nobody has to stand at the PC. |
| S19 | Setup is **agent-driven on the deployment node**. `setup-status.sh --json` is a state machine that names the next step and who does it (agent or human). Its first check rejects Windows and WSL as node bootstrap environments. The agent runbook `AgentSetup.md` loops on it, reached from the template `AGENTS.md` and a Claude Code skill. The operator only clones, authenticates and says "set it up, you are node-demo" on node-demo itself. The main-PC agent handles repository work and remote verification through GitHub and HTTP. | The operator's real workflow. Explicit machine roles prevent setup from modifying the controller. A state machine keeps a weaker agent on rails: one next step, exact commands, no guessing. |
| S20 | **Exactly one mandatory human step after authentication: one `sudo` command** that `setup-status.sh` prints with every argument filled in. The agent never handles passwords, never runs `sudo` itself and never adds sudoers rules for the user. | An agent's shell cannot answer a sudo prompt, and must not hold root credentials. One copy-paste command is easy for a person. |
| S21 | A one-PC fork with no registered CI runner registers the node's runner for CI too (`--ci-runner`: extra label `ci-<app_name>`; variables `CI_RUNNER_LABEL` and `CI_RUNNER_HOST`). The template repository keeps CI on node-main, so node-demo is CD-only. | Without it a new fork can never get the successful CI run that CD requires. |
| S15 | The template demo on node-demo uses the template's own image `ghcr.io/grumlebob/books`, with `app_name: books` and `deploy_root: /opt/books`, `backup_root: /opt/books-backups` (mode 0750, owner `deploy`, group = the install user's group, so the operator can copy backups without sudo), ports `8080`/`5432`/`6379` (loopback only) and `docker_subnet: 172.30.10.0/24`. | Proves the target with the real app. node-demo is otherwise empty. |

#### P13.B Folder layout after P13

```text
Deployment/
  Common/
    ansible/roles/{docker,ssh_hardening,cloudflared,mint_base,app_marker,caddy_install}/   # moved or new (P13.2)
    caddy/Caddyfile                                          # moved; "import /etc/caddy/sites/*.caddy"
    Scripts/{with-deploy-lock.sh,release-deploy-lock.sh,ensure-actions-runner-prereqs.sh,prune-actions-runner-residue.sh}  # moved
    Scripts/Component/with-deploy-lock.sh                    # moved
    Scripts/Tests/{test-with-deploy-lock.sh,...}             # moved with their scripts
  LocalCluster/   # same behaviour; its roles_path also lists ../../Common/ansible/roles
  Cloud/          # unchanged
  LocalSingleNode/
    HowToDeployLocalSingleNode.md
    machine.example.yml
    ansible/ansible.cfg                       # roles_path = roles:../../Common/ansible/roles
    ansible/playbooks/PrepareSingleNode.yml   # bootstrap, once, operator types the sudo password
    ansible/playbooks/site.yml                # every deploy, run by CD as deploy
    ansible/roles/single_node_firewall/
    ansible/roles/single_node_stack/          # .env, compose, image pull, migrations, start, health
    ansible/roles/single_node_caddy_site/
    ansible/roles/single_node_backup/
    compose/docker-compose.yml
    inventory/group_vars/all.yml              # app settings, no machine facts
    Scripts/{bootstrap-node.sh,validate-machine.sh,generate-inventory.sh,install-github-runner.sh,
             setup-status.sh,setup-next-step.sh,detect-machine.sh,acceptance-check.sh,doctor.sh,verify-backup.sh,run-maintenance.sh}
    Scripts/Tests/
.github/workflows/
  cd-localsinglenode.yml
  localsinglenode-maintenance.yml             # workflow_dispatch only (like Q3)
```

#### P13.C Steps

- [x] P13.0 **Preconditions.** 11.2 items 1, 2 and 4 are done: P7, P8, P10 and P11 are merged, P12 closeout is recorded and `main` CI is green. Item 3 is an observation of the next Dependabot PR, not a prerequisite requiring a new PR to appear. Create each P13 branch from the newest `origin/main`.

- [x] P13.1 **Reuse inventory (P13a PR body).** This was checked on 2026-10-08 against `upgrade/p11-docs`. Re-run the greps on current `main` and note any difference:
  ```bash
  for r in docker ssh_hardening cloudflared mint_base caddy firewall app_marker; do
    echo "== $r"; git grep -n -E "app_servers|node_db|load_balancer|node-main|groups\[" -- "Deployment/LocalCluster/ansible/roles/$r"
  done
  ```
  Expected: `docker`, `ssh_hardening` and `cloudflared` have no hits, so move them. `mint_base` has 3 tasks gated on `groups["load_balancer"]` (deploy key and known_hosts on the control node), so move it after the change in P13.2 step 3. `app_marker` only has `runner_name | default('node-main-' ~ app_name)`, so move it; single node passes `runner_name`. The marker template also requires Cloudflare fields; make those fields optional with empty defaults so a LAN-only target can use the marker. Cluster values and rendered content stay unchanged. `caddy` and `firewall` loop over cluster groups, so they stay in LocalCluster; P13.2 step 4 splits Caddy's install part out.

- [x] P13.2 **PR P13a: move shared pieces to Common, LocalCluster behaviour unchanged.**
  1. Record "before" evidence on the unchanged branch:
     ```bash
     cd Deployment/LocalCluster/ansible
     for p in site.yml PrepareFreshLinuxMachine.yml PrepareExistingLocalClusterApp.yml; do
       ansible-playbook -i ../inventory/prod/hosts.yml "playbooks/$p" --list-tasks > "/tmp/before-$p.txt"
     done
     ```
     If a vault file or variable is missing, use the empty-vault trick from CI's "Validate LocalCluster Ansible playbook syntax" step.
  2. `git mv` the roles `docker`, `ssh_hardening`, `cloudflared`, `mint_base` and `app_marker` to `Deployment/Common/ansible/roles/`. Move `Deployment/LocalCluster/caddy/Caddyfile` to `Deployment/Common/caddy/Caddyfile`. Move `Scripts/with-deploy-lock.sh`, `Scripts/release-deploy-lock.sh`, `Scripts/Component/with-deploy-lock.sh`, `Scripts/Tests/test-with-deploy-lock.sh`, `Scripts/ensure-actions-runner-prereqs.sh` and `Scripts/prune-actions-runner-residue.sh` (with their tests under `Scripts/Tests/`) to the same relative places under `Deployment/Common/`. If a moved script `source`s or calls another LocalCluster script, move that one too, or pass the value as an argument. Record which in the PR body. Keep `Component/with-node-main-deploy-lock.sh` in LocalCluster, and repoint its `source`/call to the new Common path.
  3. In the moved `mint_base`, replace each `groups["load_balancer"]` with `groups.get('load_balancer', [])`. LocalCluster renders the same, and a single node skips those tasks. Guard the reboot task with `mint_base_reboot_after_upgrade | default(true) | bool`: LocalCluster retains its reboot behavior, while PrepareSingleNode sets false because Ansible rejects rebooting its local controller. Also guard the task "Install deploy SSH public key" with `when: mint_base_install_deploy_key | default(true) | bool`. It reads `~/.ssh/<app_name>_deploy.pub` on the controller, which a single node does not have. `PrepareSingleNode.yml` sets the variable to `false`. This was checked on 2026-10-08: `ssh_hardening`, `docker` and `cloudflared` have no controller-side lookups, and `ssh_hardening` only sets `PasswordAuthentication no`.
  4. Create `Deployment/Common/ansible/roles/caddy_install/` with the install tasks from LocalCluster `caddy/tasks/main.yml`: prerequisites, apt key, repository, package, `/etc/caddy/sites`, and the root Caddyfile copied from `{{ playbook_dir }}/../../../Common/caddy/Caddyfile`. Copy the "Reload caddy" handler too. Remove those tasks from LocalCluster `caddy`, and add `caddy/meta/main.yml` with `dependencies: [caddy_install]`.
  5. Set `roles_path = roles:../../Common/ansible/roles` in `Deployment/LocalCluster/ansible/ansible.cfg`. If `Deployment/Cloud` uses any moved role (`git grep -n "role: docker\|- docker$" Deployment/Cloud`), do the same in Cloud's `ansible.cfg`. Otherwise leave Cloud alone.
  6. Fix every reference to the moved files: `git grep -n -E "LocalCluster/(Scripts/(with-deploy-lock|release-deploy-lock|ensure-actions-runner-prereqs|prune-actions-runner-residue|Component/with-deploy-lock|Tests/test-with-deploy-lock)|caddy/Caddyfile|ansible/roles/(docker|ssh_hardening|cloudflared|mint_base|app_marker))"` must return nothing in `.github`, `Deployment`, `Scripts`, `docs`, `BlazorAutoApp.Test`, `README.md` and `AGENTS.md`. That includes the CI "Test LocalCluster deployment lock" step, the maintenance script's `SCRIPT_DIR` calls, `cd-localcluster.yml`, the audit and `AgentGuardrailTests`.
  7. Update `audit_deployment.py` path rules per 3.7: replace each old path with the new one, and keep every rule.
  8. "After" evidence: repeat step 1 into `/tmp/after-*.txt`. Preserve the raw diffs. Extracting the Caddy dependency changes only six task role prefixes from `caddy` to `caddy_install`; normalize exactly `caddy_install :` to `caddy :` for the task/order comparison. That normalized diff must be empty for all three playbooks. Do not claim the raw site.yml diff is empty. Also run `ansible-playbook --syntax-check` on them, `validate-rendered-templates.sh`, the audit, `bash Deployment/Common/Scripts/Tests/test-with-deploy-lock.sh` and the full 3.6 gate. Put the empty diffs in the PR body.

- [x] P13.3 **PR P13b: `DEPLOY_TARGETS` and the CI runner label.**
  1. **Before** opening the PR, set the variables on the template repository (Q5 authorises the agent):
     ```bash
     gh variable set DEPLOY_TARGETS --repo Grumlebob/BlazorAutoAppTemplate --body "localcluster,localsinglenode"
     gh variable set LOCALSINGLENODE_HOST --repo Grumlebob/BlazorAutoAppTemplate --body "node-demo"
     ```
  2. Add this as the first step of the first job in `cd-localcluster.yml`, `cd-cloud.yml` (target `cloud`) and `localcluster-docker-maintenance.yml` (both jobs). Change only `TARGET`:
     ```yaml
     - name: Require this deployment target to be enabled
       env:
         DEPLOY_TARGETS: ${{ vars.DEPLOY_TARGETS }}
         TARGET: localcluster
       run: |
         targets=",${DEPLOY_TARGETS// /},"
         if [[ "$targets" != *",${TARGET},"* ]]; then
           echo "::error::Deployment target '${TARGET}' is not enabled. Add it to the DEPLOY_TARGETS repository variable (Settings > Secrets and variables > Actions > Variables), for example 'localcluster,localsinglenode'."
           exit 1
         fi
     ```
  3. In `ci.yml`, change every `runs-on` label expression to S8's `vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books'`. Do the same in `auto-merge-dependabot.yml`, which runs CI-side checks. If the audit pins the old expression, update that rule (3.7).
  4. The runner-profile steps in `ci.yml` (3 jobs) and `auto-merge-dependabot.yml` hard-code `test "$(hostname)" = "node-main"`. Change them to compare with `${{ vars.CI_RUNNER_HOST || 'node-main' }}` (via `env`), so a one-PC fork can run CI on its node (S21). Leave the LocalCluster CD and maintenance host checks as they are.
  5. Add a guardrail test, `DeploymentWorkflows_RequireEnabledTarget`, to `AgentGuardrailTests.cs`: every `.github/workflows/cd-*.yml` and `*-maintenance.yml` contains `Require this deployment target to be enabled` and `vars.DEPLOY_TARGETS`. Add the matching audit rule.
  6. Gate, PR, merge. Then check that `gh variable list --repo Grumlebob/BlazorAutoAppTemplate` shows both variables.

- [ ] P13.4 **PR P13c, part 1: settings and machine facts.**
  - `Deployment/LocalSingleNode/machine.example.yml` documents the detected facts (S14). An operator copies it to `machine.yml` only to override detection, for example on a PC with two network cards. Bootstrap prefers `machine.yml` over detection when it exists:
    ```yaml
    # Optional. Bootstrap detects these values; copy to Deployment/LocalSingleNode/machine.yml only to override them.
    node:
      name: REPLACE_WITH_NODE_HOSTNAME        # must equal `hostname`, e.g. node-demo
      ip: REPLACE_WITH_NODE_LAN_IP            # fixed DHCP lease
      lan_cidr: REPLACE_WITH_LAN_CIDR         # e.g. 192.0.2.0/24; SSH and HTTP are allowed only from here
      install_user: REPLACE_WITH_LINUX_MINT_INSTALL_USER
    ```
  - `inventory/group_vars/all.yml`: `app_name: books`, `app_port: 8080`, `postgres_port: 5432`, `redis_port: 6379`, `deploy_root: /opt/books`, `docker_subnet: 172.30.10.0/24`, `lan_http_port: 80`, `lan_hostnames: []` (extra names; `<node name>.local` and the node IP are always included), `backup_root: /opt/books-backups`, `backup_keep_days: 7`, `observability_enabled: false`. A fork that renames the app changes `app_name` in each enabled target's `group_vars`; the fork guide (P13.10) lists both files. Add a read helper, `Scripts/read-setting.sh <key>`, that prints one key from this file (copy LocalCluster's `read-deploy-setting.sh` shape). CD and scripts use it; they never parse YAML with `grep`.
  - `Scripts/validate-machine.sh <file>`: fails on any `REPLACE_WITH_` value, an invalid IPv4 address or CIDR, an IP outside `lan_cidr`, or `name` different from `hostname` when run on the node (skip that last check with `--not-on-node`).
  - `Scripts/detect-machine.sh [--output <file>]`: prints or writes the S14 facts as `machine.yml` YAML. It is used by bootstrap and by every CD run. It has a fixture test with stubbed `ip`, `hostname` and `id` commands.
  - `Scripts/generate-inventory.sh --machine <file> --output <file>`: writes
    ```yaml
    all:
      hosts:
        <name>:
          ansible_connection: local
          ansible_python_interpreter: /usr/bin/python3
          node_ip: <ip>
          lan_cidr: <lan_cidr>
    ```
  - `.gitignore`: add `Deployment/LocalSingleNode/machine.yml`.
  - Port-collision check: `Scripts/check-port-collisions.sh` (single-node version) fails when `app_port`, `postgres_port`, `redis_port`, `lan_http_port` or `docker_subnet` is already used by another app's `/opt/*/docker-compose.yml` or `/etc/caddy/sites/*.caddy`, or by a listening socket (`ss -ltn`) that is not this app's own.

- [ ] P13.5 **PR P13c, part 2: Compose file (S5).** `Deployment/LocalSingleNode/compose/docker-compose.yml`:
  - `name: ${APP_NAME}`. A `default` network with `ipam.config: [{subnet: ${DOCKER_SUBNET}}]`.
  - `postgres`: the same image tag as LocalCluster `node-db` compose and `TestContainerImages.cs`; `ports: ["127.0.0.1:${POSTGRES_PORT}:5432"]`; volume `postgres_data:/var/lib/postgresql`; the same health check.
  - `redis`: the same image and command as LocalCluster (`--requirepass`, `--appendonly yes`); `ports: ["127.0.0.1:${REDIS_PORT}:6379"]`; volume `redis_data:/data`; health check.
  - `web`: `image: ${APP_IMAGE_REF:?APP_IMAGE_REF is required}`; `restart: unless-stopped`; `ports: ["127.0.0.1:${APP_PORT}:${APP_PORT}"]`; `depends_on` `postgres`/`redis` with `condition: service_healthy`; volume `app_storage:/app/Storage`.
  - `web` environment: copy LocalCluster's app-server env, with `ConnectionStrings__DefaultConnection: Host=postgres;Port=5432;...`, `Redis__Configuration: redis:6379,password=${REDIS_PASSWORD},abortConnect=false`, `Database__RunMigrationsAtStartup: "false"`, `ForwardedHeaders__KnownNetworks__0: ${DOCKER_SUBNET}`, `Observability__OpenTelemetry__Enabled: "false"`, `Observability__OpenTelemetry__DeploymentTarget: localsinglenode`, `LocalAccounts__Enabled: "false"` (D15). Drop the external observability network.
  - Every service: the `json-file` logging anchor (10m × 3) and the label `localsinglenode.app=${APP_NAME}`.
  - `.env` keys (rendered by Ansible, mode 0600): `APP_NAME APP_IMAGE_REF APP_VERSION APP_PORT POSTGRES_PORT REDIS_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD REDIS_PASSWORD DOCKER_SUBNET`.
  - Validate with `docker compose --env-file <fake.env> -f ... config -q` in a script test.

- [ ] P13.6 **PR P13c, part 3: agent-driven node setup (S19–S21).** The operator clones the repository on the new PC, runs `gh auth login`, starts a coding agent and says something like "I just cloned this, set it up, you are node-demo". The agent must finish the setup and stop only for things a person must do. Build it as a state machine with one root command.
  - **`Scripts/setup-status.sh --node <name> [--json]`** (no sudo, read-only, safe to run any time). It evaluates these checks in order and reports the **first** that is not done. With `--json` it prints one object: `{"step": "<id>", "actor": "agent" | "human" | "none", "summary": "...", "command": "...", "human_message": "...", "done": ["<id>", ...]}`. Exit codes: 0 when everything is done, 10 when the next action is the agent's, 20 when it is the human's, 1 when the check itself failed.

    | Step id | Done when | If not done: actor and action |
    | --- | --- | --- |
    | `platform` | Native Linux deployment node, not Windows or WSL | human: move setup to the intended deployment PC. No bootstrap command is emitted on an unsupported platform |
    | `repo` | Inside a clone whose `origin` is a GitHub repository, on `main`, clean, and equal to `origin/main` | agent: `git switch main && git pull --ff-only`. If the tree is dirty: human ("commit or remove your local changes") |
    | `tools` | GitHub CLI is available | agent: install the reviewed official Linux x64 CLI under the user’s local directory with published SHA256 verification, without sudo |
    | `gh` | `gh auth status` passes, and `gh api repos/<o>/<r> --jq .permissions.admin` is `true` | human: `gh auth login --hostname github.com --git-protocol https --web`, using an account with admin on the repository |
    | `fork` | `release.yml` `app_image` owner equals the repository owner | agent: follow `docs/HowToForkThisRepo.md` and ask the user for the app name only if the fork has none yet |
    | `machine` | Detected facts (S14) validate, and `--node` matches `hostname` or bootstrap will set it | agent: run `detect-machine.sh` and show the facts. A failure (no IPv4 default route, for example) is human: "connect the PC to the LAN" |
    | `ci` | A successful `ci.yml` push run exists for `origin/main` HEAD, with a successful publish job | agent: watch an existing push run, or rerun it with `gh run rerun <id>`; dispatch cannot satisfy P7. If no push run exists, report the initial-push prerequisite. With no CI capacity, defer fork customization and CI until root/variables/runner create it; `root` gets `--ci-runner` |
    | `root` | `/etc/localsinglenode/bootstrap.json` exists, its `version` equals the script's version, and `doctor.sh` passes | **human**: the one sudo command below |
    | `variables` | `DEPLOY_TARGETS` contains `localsinglenode`; `LOCALSINGLENODE_HOST` equals the node name; with `--ci-runner`, also `CI_RUNNER_LABEL` and `CI_RUNNER_HOST` | agent: `gh variable set ...` (Q5) |
    | `runner` | The runners API shows `<node>-<app_name>` online with label `localsinglenode-<app_name>` | agent: wait, polling every 30 s for up to 5 min. After that, human: "run `sudo systemctl status 'actions.runner.*'` and paste the output" |
    | `deploy` | A successful `cd-localsinglenode.yml` run exists for `origin/main` HEAD | agent: `gh workflow run cd-localsinglenode.yml --ref main -f run_migrations=true`, then watch it. Never re-dispatch because a watcher stopped |
    | `verify` | `Test-DeployedSite.ps1 -BaseUrl http://<ip>:<lan_http_port>` passes on the node | agent: run it. Report a failure; never loop |
    | `done` | All above | none. Print the site URL and the main-PC check (P13.D step 4); recommend a DHCP reservation for forks that do not already have one |

  - **`Scripts/bootstrap-node.sh`: the one root command.** The human runs it on the deployment node exactly as `setup-status.sh` prints it, for example `sudo bash ~/<repo>/Deployment/LocalSingleNode/Scripts/bootstrap-node.sh --node node-demo --user <install user> --github-login <login> --yes [--ci-runner]`. Before any mutation, it rejects Windows/WSL, requires root and a real `SUDO_USER`, and never asks anything with `--yes`. It numbers its steps. On failure it prints `FAILED at step N: <name>` and the same command to re-run. Every step is idempotent. In order:
    1. `apt-get install -y git gh curl openssh-server avahi-daemon libnss-mdns python3-venv python3-pip sshpass iproute2 ca-certificates` (bounded retries, like P8.1). If `hostname` differs from `--node`, run `hostnamectl set-hostname <node>` and update `/etc/hosts`.
    2. Detect and validate the machine facts (S14); write `/etc/localsinglenode/machine.yml`.
    3. As `SUDO_USER`: `bash Deployment/Common/Scripts/install-ansible.sh --provision --user-only`. Root installs prerequisites first; user-only provisioning never calls sudo/apt or writes global links.
    4. `ansible-playbook playbooks/PrepareSingleNode.yml` (local connection, as root).
    5. Import `https://github.com/<login>.keys` into `SUDO_USER`'s `authorized_keys`. Apply `ssh_hardening` only if at least one key was imported (S17).
    6. As `deploy`: `install-ansible.sh --provision`, then `ensure-actions-runner-prereqs.sh --provision` (installs `pwsh` for S16).
    7. Runner (`install-github-runner.sh`, run as root): get the registration token as the human's own `gh` login with `sudo -u "$SUDO_USER" -H gh api -X POST repos/<o>/<r>/actions/runners/registration-token --jq .token`. Never print the token. Labels are `localsinglenode-<app_name>`, plus `ci-<app_name>` with `--ci-runner`.
    8. Write `/etc/localsinglenode/bootstrap.json` (`version`, timestamp, node, flags), then run `doctor.sh`.
  - **`Deployment/LocalSingleNode/AgentSetup.md`**, the agent runbook. It is short and imperative:
    1. Confirm the user explicitly asked to set up the current machine as a deployment node. A main-PC planning session that mentions node-demo is not that request. Refuse local node setup on Windows or WSL. Read the node name from the user's words ("you are node-demo"). If none is given, use `hostname`. Show the native Linux hostname and detected address before the root step; compare any operator-provided target address, and stop on a mismatch. Only the operator's explicit node-setup request permits renaming that Linux machine.
    2. Loop: run `setup-status.sh --node <name> --json`. If `actor` is `agent`, run `command`, then re-run status. If `actor` is `human`, show `human_message` and `command` verbatim in one short message and stop. When the user says it is done, resume the loop. If `actor` is `none`, report the URL and stop.
    3. Never ask for, type or store a password or token. Never add sudoers rules for the user. Never run `sudo` yourself; the root command is the human's.
    4. Never edit files under `/etc` by hand, never prune Docker volumes, never dispatch other CD workflows.
    5. If the same agent step fails twice, stop and report its output.
    6. At the end, summarise what was done and print the command for the main-PC agent's independent LAN check (P13.D step 4).
  - **Agent entry points.** In the template `AGENTS.md`, add a section "Setting up this machine as a deployment node": only an explicit request to set up the current PC (for example "you are node-demo" in a session on that node) triggers `Deployment/LocalSingleNode/AgentSetup.md`. A controller session discussing another node does not trigger it. Add `.claude/skills/setup-local-single-node/SKILL.md` with the same trigger boundary and a body that points to `AgentSetup.md`. Codex reads `AGENTS.md`. Both paths lead to the same runbook, so nothing is duplicated.
  - **Tests** (`Scripts/Tests/test-setup-status.sh`): use stub `git`, `gh`, `hostname`, `ip`, `id`, `uname`, `systemctl`, `curl` and `pwsh` on `PATH`, plus fixture `/etc` paths through `LOCALSINGLENODE_ETC`. Assert the JSON `step`/`actor` for each row of the table, and the exit codes 0, 10, 20 and 1. Assert that Windows and WSL fail the platform check without emitting a bootstrap command. Add a test that `bootstrap-node.sh` refuses to run on Windows/WSL, without root or without `SUDO_USER`, and builds the right command line. Use fake hostnames and addresses in fixtures.
  - `PrepareSingleNode.yml` applies these roles in order: `mint_base` (creates `deploy` with passwordless sudo exactly as on LocalCluster nodes; `mint_base_install_deploy_key: false`, `mint_base_reboot_after_upgrade: false`), `docker` (adds `deploy` to `docker`), `single_node_firewall` and `caddy_install`. It ensures `avahi-daemon` is running, creates `/etc/<app_name>/secrets.yml` only if missing (S11), and creates `{{ deploy_root }}` and `{{ backup_root }}` (S12 permissions).
  - `single_node_firewall`: UFW default deny incoming, allow outgoing; allow `22/tcp`, `{{ lan_http_port }}/tcp` and mDNS `5353/udp` from `lan_cidr`; enable. Published container ports are loopback-only, so Docker's iptables rules do not bypass UFW here. The audit enforces that (P13.9).
  - `install-github-runner.sh` (single node, local, no SSH): downloads the same pinned runner version as the LocalCluster script into `/home/deploy/actions-runner-<app_name>`, configures `--unattended --name <node>-<app_name> --labels <labels> --work _work`, and runs `./svc.sh install deploy && ./svc.sh start`. If the directory already holds a runner for another repository, or its `.runner` cannot be read, it stops; it never deletes (P8.12 rule). An existing runner for the same repository is kept, and its labels are checked.
  - `doctor.sh [--json]`: checks the runner service is active, `deploy` is in `docker`, UFW is active, Caddy is active, `/etc/<app_name>/secrets.yml` is mode 0600, at least 20 GiB is free on `/opt`, and that `getent hosts <node>.local` resolves. Exit 0 when all pass, else 1, with one line (or one JSON entry) per check.

- [ ] P13.7 **PR P13c, part 4: deploy playbook `site.yml` (run by CD as `deploy`).** Inputs (extra vars): `app_version` (target SHA), `release_image_digest`, `run_migrations`, `migration_bundle_local_path`, the GHCR extra-vars file (copy LocalCluster's temporary-`DOCKER_CONFIG` pattern) and `-e @/etc/<app_name>/secrets.yml`. Plays, in order:
  1. Assert the inputs, and that `inventory_hostname` equals `ansible_hostname`.
  2. Run `check-port-collisions.sh`.
  3. Render `{{ deploy_root }}/.env` (0600) and copy `docker-compose.yml`.
  4. Pull `app_image@release_image_digest` with a temporary `DOCKER_CONFIG` (5 retries, 15 s apart), and assert that the RepoDigests contain the digest (copy LocalCluster's "Stage the exact app image" play).
  5. Run `docker compose up -d postgres redis`, then wait until both are healthy (timeout 120 s).
  6. If `run_migrations`: run `docker compose stop web`, then copy the bundle to `{{ deploy_root }}/migrations/` and run it with `--connection "Host=127.0.0.1;Port={{ postgres_port }};..."` (copy LocalCluster `site.yml`'s migration task shape; `no_log: true`).
  7. Run `docker compose up -d --remove-orphans web`, then wait until `http://127.0.0.1:{{ app_port }}/health/ready` returns 200 (timeout 180 s).
  8. Apply `single_node_caddy_site` (template below; `become: true`; validate with `caddy validate --config /etc/caddy/Caddyfile` before reload).
  9. Wait until `http://{{ node_ip }}:{{ lan_http_port }}/health/ready` returns 200 through Caddy. Then print `Site URL: http://<node name>.local:<port>/` (drop `:80` for port 80).
  10. Apply `app_marker` with `runner_name: <node name>-<app_name>`.
  On failure of steps 7 or 9, print `docker compose logs --tail 200 web` and fail. Never remove volumes.
  Caddy site template `single_node_caddy_site/templates/app.caddy.j2`:
  ```
  {% for h in ([inventory_hostname ~ '.local'] + lan_hostnames) %}http://{{ h }}:{{ lan_http_port }}, {% endfor %}http://{{ node_ip }}:{{ lan_http_port }} {
    reverse_proxy 127.0.0.1:{{ app_port }} {
      health_uri /health/ready
    }
  }
  ```

- [ ] P13.8 **PR P13c, part 5: CD workflow `cd-localsinglenode.yml`.** Copy `cd-localcluster.yml` and change these things:
  - `name: CD - Deploy LocalSingleNode`, `run-name: "CD LocalSingleNode @ ${{ inputs.target_sha || github.sha }}"`, `concurrency: {group: cd-localsinglenode, cancel-in-progress: false}`, `timeout-minutes: 45`, `workflow_dispatch` only, with inputs `run_migrations` (default `"true"`) and `target_sha`.
  - `runs-on: [self-hosted, linux, x64, "${{ vars.LOCALSINGLENODE_RUNNER_LABEL || 'localsinglenode-books' }}"]`.
  - Step 1 is the target gate with `TARGET: localsinglenode`. Step 2 checks the host: `test -n "$LOCALSINGLENODE_HOST" && test "$(hostname)" = "$LOCALSINGLENODE_HOST"` (from `vars.LOCALSINGLENODE_HOST`; no default).
  - Keep these unchanged: require main, `target_sha` resolution and ancestor check, `find-successful-ci-run.py --target-sha ... --json`, artifact download from `CI_RUN_ID` (always), `validate_release_manifest.py`, GHCR extra-vars file with `secrets.GITHUB_TOKEN`, `install-ansible.sh --check`, and cleanup in `if: always()`.
  - Remove the vault password, SSH, `known_hosts`, node-main capacity and observability steps.
  - Add "Generate inventory": `bash Deployment/LocalSingleNode/Scripts/generate-inventory.sh --machine /etc/localsinglenode/machine.yml --output "$RUNNER_TEMP/hosts.yml"`.
  - Deploy step: `bash Deployment/Common/Scripts/with-deploy-lock.sh ansible-playbook -i "$RUNNER_TEMP/hosts.yml" Deployment/LocalSingleNode/ansible/playbooks/site.yml -e @/etc/<app_name>/secrets.yml -e @"$GHCR_EXTRA_VARS_FILE" -e "app_version=$TARGET_SHA" -e "release_image_digest=$RELEASE_IMAGE_DIGEST" -e "run_migrations=..." [-e migration_bundle_local_path=...]`. Read `<app_name>` with `Scripts/read-setting.sh app_name` into `APP_NAME` in an early step.
  - Detect the address again (S14) before generating the inventory.
  - After deploying, run `pwsh -NoProfile -File Scripts/Test-DeployedSite.ps1 -BaseUrl http://<node_ip>:<lan_http_port>` (S16), and an identity check: the running `web` container's image digest equals `RELEASE_IMAGE_DIGEST`.

- [ ] P13.9 **PR P13c, part 6: maintenance, audit and tests.**
  1. `localsinglenode-maintenance.yml`: `workflow_dispatch` only, same runner label, target gate first, with inputs `backup_now` (boolean, default `true`), `reboot_check` (boolean, default `false`, S18) and `acceptance_only` (boolean, default `false`). `acceptance_only` runs only `Test-DeployedSite.ps1` and prints `uptime -s`. It runs `Scripts/run-maintenance.sh [--backup-now]`. With `--backup-now`, start and wait for the lock-taking backup service **before** acquiring the maintenance lock; verify the dump and perform cleanup under that lock. This prevents a nested-lock deadlock. Stages: remove this app's images (`--filter reference=<app_image>`) that no container uses and that are older than 168 h, keeping the image of the running `web`; delete only old images with this repository’s source label and image references, preserving every container image and the released digest; report unowned dangling images without deletion; run `prune-actions-runner-residue.sh` for this node's runner root; report dangling volumes (report only); report disk and inodes for `/opt`; fail if `{{ backup_root }}/last-success` is older than 36 h. Exit codes `0/1/2/75` as in P8.
  2. Audit rules (`audit_deployment.py`, new section `localsinglenode`):
     - The compose file has no `ports:` entry without a `127.0.0.1:` prefix.
     - `cd-localsinglenode.yml` contains the target gate, `find-successful-ci-run.py --target-sha`, `validate_release_manifest.py`, `release_image_digest`, `with-deploy-lock.sh` and `git merge-base --is-ancestor`.
     - There is no `docker volume prune`/`system prune`.
     - The `web` service sets `LocalAccounts__Enabled: "false"` (D15).
     - There is no IPv4 literal in tracked LocalSingleNode files other than `127.0.0.1`, `172.30.` and documentation examples from `192.0.2.0/24`.
     - `machine.yml` is in `.gitignore`.
  3. Script tests in `Deployment/LocalSingleNode/Scripts/Tests/`, run in CI `validate`:
     - `test-validate-machine.sh`: placeholders, a bad IP, an IP outside the CIDR, and a valid file.
     - `test-generate-inventory.sh`: exact output.
     - `test-compose-config.sh`: `docker compose config -q` with fake env, and no `0.0.0.0` ports.
     - `test-check-port-collisions.sh`: fixture `/opt` tree via an `OPT_ROOT` override.
     - `test-target-gate.sh`: the gate snippet with `localcluster`, `localsinglenode,cloud`, `localsinglenodex`, empty and spaces.
  4. `Scripts/Test-DeployedSite.ps1` (S16). Parameters: `-Node <name>` (base URL `http://<name>.local`; on a resolve failure, print the re-run command with `-Address`), `-Address <ip>`, `-BaseUrl <url>`, `-Port`. Use `Invoke-WebRequest -UseBasicParsing` and a `WebRequestSession`; nothing that needs PowerShell 7. Checks, each printed as `PASS`/`FAIL <name>: <reason>`:
     1. Name resolution and TCP connect.
     2. `/health/ready` returns 200.
     3. `/` returns HTML containing `_framework/blazor.web`.
     4. `/api/books` returns 401 without following redirects.
     5. Register a random `check-<guid>@example.invalid` with a generated password: GET `/Account/Register`, then POST the form with `__RequestVerificationToken`, `_handler=register`, `Input.Email`, `Input.Password` and `Input.ConfirmPassword`.
     6. Sign in through `/Account/Login` in a **fresh session** (read the field names from `Login.razor`); registration’s auto-login cookie cannot prove password login.
     7. An authenticated GET of `/Account/Manage` returns 200, not a redirect to login.
     8. Signing in as `admin@admin.com` / `Admin123` fails (D15).
     9. Delete the test user through `/Account/Manage/DeletePersonalData` in `finally`, using the retained registration session, then verify deleted credentials fail in another fresh session.
     It exits 0 only if all checks pass, and prints `RESULT: PASS` or `RESULT: FAIL`. CI's `ci-docker-smoke.sh` runs it against the smoke container (`pwsh` is on the runner), so a change to the forms breaks CI rather than the operator's check.
  5. CI `validate`: add `Deployment/LocalSingleNode` to shellcheck and yamllint, add `ansible-playbook --syntax-check` for both single-node playbooks (temporary inventory with one local host), and render the Caddy, `.env` and compose templates in `validate-rendered-templates.sh` with fake values.
  6. Gate, PR, merge.

- [ ] P13.10 **PR P13d: docs.**
  - `Deployment/README.md` (new) has the chooser table:

    | Target | Machines | Needs | Downtime per deploy | Backups | Pick it when |
    | --- | --- | --- | --- | --- | --- |
    | `localsinglenode` | 1 PC | Linux Mint, LAN | short | nightly local dump | demos, hobby apps, first deploy |
    | `localcluster` | 4 PCs | Mint ×4, Cloudflare | none without migrations | per guide | HA at home |
    | `cloud` | Hetzner | cloud account and cost | per guide | per guide | public production |

    It also explains `DEPLOY_TARGETS`, and says which folders an unused target can ignore (S4).
  - `Deployment/LocalSingleNode/HowToDeployLocalSingleNode.md`: the exact P13.12 sequence, with "operator" and "agent" columns. It covers recovery (re-run bootstrap; restore with `verify-backup.sh --restore-into <app_name>` after confirmation), backups and copying them off the machine, the `docker` group and sudo statement (S7), and removing the app (stop the stack; data volumes stay until the operator runs `docker volume rm` by hand).
  - `docs/HowToForkThisRepo.md`: a new step, "Choose deployment targets", that sets `DEPLOY_TARGETS` and links the chooser. `README.md`: link `Deployment/README.md`. `AGENTS.md` (template): the shared-host rule also covers single nodes; never pass `--volumes` to compose down on a node.
  - Run the link check from P11.10.

- [ ] P13.11 **Fresh-fork rehearsal for single node (no deploy).** In a temporary clone, with fake values (`node-rehearsal`, IP `192.0.2.10`, CIDR `192.0.2.0/24`): run `validate-machine.sh --not-on-node`, `generate-inventory.sh`, render validation, `docker compose config -q`, `ansible-playbook --syntax-check` on both playbooks, and the audit. Everything must pass, or fail with a clear message. Do not push the clone.

- [ ] P13.12 **Live test on node-demo (`192.168.0.212`, fixed DHCP lease).** Q4 authorises deploys to node-demo only; this never touches LocalCluster nodes. P13.D steps 1–3 belong to the operator and a local agent on node-demo. The main-PC agent does the remaining checks, including independent LAN acceptance. Record each result in 11.1.

  | # | Who | Action | Pass condition |
  | --- | --- | --- | --- |
  | 1 | Operator | P13.D step 1: confirm Mint is installed; install only if needed | Mint desktop is up on the separate node-demo PC |
  | 2 | Operator, and an agent on node-demo | P13.D steps 2–3: clone, authenticate, "set it up, you are node-demo"; compare detected address with `192.168.0.212`; run the one sudo command the local agent prints | The local agent reaches `step: done` and prints the URL, initial CD run URL, deployed SHA and digest. This exercises S19–S21 exactly as a real fork would. Record the agent's transcript summary in 11.1 |
  | 3 | Main-PC agent | Confirm what the local agent did: check the runner via `gh api repos/Grumlebob/BlazorAutoAppTemplate/actions/runners` (online, name `node-demo-books`, label `localsinglenode-books`). Inspect the initial CD run and manifest. If that run already deployed the intended SHA with migrations, use its evidence; dispatch `gh workflow run cd-localsinglenode.yml --repo Grumlebob/BlazorAutoAppTemplate --ref main -f target_sha=<verified-main-sha> -f run_migrations=true` only if the required deployment has not occurred. Record the run ID before watching; never re-dispatch because a watcher stopped | Run succeeds on node-demo; `Test-DeployedSite.ps1` passes on the node; the running digest equals the manifest |
  | 4 | Main-PC agent | P13.D step 4: run the checkout's `Scripts/Test-DeployedSite.ps1 -Address 192.168.0.212` from Windows on the main PC after syncing to the verified merged commit. Check `node-demo.local` separately if it resolves | Required IP check prints `RESULT: PASS`. Record mDNS success or its unavailable status separately; mDNS is not a prerequisite for reaching the fixed IP |
  | 5 | Main-PC agent | Dispatch the same SHA again with `run_migrations=false` | Succeeds; `Test-DeployedSite.ps1` passes again |
  | 6 | Main-PC agent | Reboot check: `gh workflow run localsinglenode-maintenance.yml --repo Grumlebob/BlazorAutoAppTemplate -f reboot_check=true`. The job schedules a reboot 30 s after it finishes. Poll the runners API every 60 s, for up to 15 min, until the runner is online again. Then dispatch `-f acceptance_only=true` | The second run passes, and it reports an uptime under 30 min (proof of the reboot) |
  | 7 | Main-PC agent | Rollback: dispatch CD with `target_sha` = an older `main` SHA that has successful CI and the same migrations, then dispatch the newest again | Both succeed |
  | 8 | Main-PC agent | `gh workflow run localsinglenode-maintenance.yml --repo Grumlebob/BlazorAutoAppTemplate -f backup_now=true` | Exit 0; the log shows a new dump and a restore with more than 0 tables |

  If a step fails, stop and record the failure and logs in 11.1. Fix it in a PR (gate and CI as usual), then resume from that step. Do not retry blindly. If the main-PC check (row 4) fails, the main-PC agent already has its output; diagnose reachability and the named failing check before asking for anything that requires physical access to node-demo.

- [ ] P13.13 **Closeout.** Record in 11.1: the four PR merge commits, the node-demo run URLs, the deployed digest and the results of rows 1–8. Close P13 in 11.2, and update the status line.

#### P13.D Operator guide for node-demo

**Site URL after deployment:** `http://192.168.0.212/` (fixed DHCP lease), also `http://node-demo.local/` when mDNS resolves. It is plain HTTP (browsers show "Not secure"), works only on the home LAN, and is not reachable from the internet. A second app on node-demo would get `http://192.168.0.212:8081/` or `http://node-demo.local:8081/` (S6). The main PC is the controller; all installation and bootstrap commands below run on the separate node-demo PC.

Start after the agent's message "node-demo: ready for you", which comes when P13a–P13d are merged. Before that, the setup scripts do not exist on `main`.

**Step 1: installation is done for this live test.** The operator confirmed on 2026-10-09 that node-demo is installed and the repository is cloned. Keep that installation; check the Mint version during setup instead of reinstalling. For a future fresh machine that still needs installation (about 20 minutes), write Linux Mint 22.x Cinnamon to a USB stick (Rufus or balenaEtcher), boot the intended deployment PC from it, and choose "Erase disk and install Linux Mint" (everything on that PC is erased). Any computer name and username work; the local agent renames the intended node to the name you give it.

**Step 2: use the existing clone, authenticate, and ask the agent (5 minutes).** On node-demo, enter the repository folder already cloned and run `gh auth status`. If authentication is missing, run `gh auth login` as shown below. Do not clone over the existing directory. The complete commands below are for a fresh machine; skip installation and clone commands already completed:
```bash
sudo apt-get update && sudo apt-get install -y git gh
gh auth login          # GitHub.com > HTTPS > Yes > Login with a web browser; use the account that owns the repository
git clone https://github.com/Grumlebob/BlazorAutoAppTemplate.git ~/BlazorAutoAppTemplate && cd ~/BlazorAutoAppTemplate
```
Start your coding agent in that folder (Claude Code or Codex, installed as usual) and say:

> I just cloned this on the deployment PC. Set it up. You are node-demo. Its fixed DHCP lease is 192.168.0.212. Detect and confirm the address before setup.

**Step 3: run the one command the agent gives you (about 15 minutes, mostly waiting).** The agent checks everything it can by itself. It then stops once and shows a single line starting with `sudo bash ...`. Paste it into a terminal, type your password, wait for `FINISHED`, and tell the agent "done". The agent then finishes on its own: it registers settings, waits for the runner, deploys and checks the site. It ends with the site URL. If it stops again, it shows exactly what to do, in one short message.

**Step 4 (main-PC agent, about 1 minute): verify access across the LAN.** After P13 scripts are merged, run from the template checkout on the Windows main PC:
```powershell
& .\Scripts\Test-DeployedSite.ps1 -Address 192.168.0.212
```
The main-PC agent runs this required check itself and records the output in 11.1. No .NET SDK or browser is needed. Over your LAN it checks that the site answers; that health, the home page and the Blazor script work; that the API answers 401; that a test user can register and sign in; and that `admin@admin.com` / `Admin123` is **rejected** (D15). It deletes its test user, and prints `RESULT: PASS` or `RESULT: FAIL` with the failing check. The agent also checks `node-demo.local` and records whether mDNS works; the fixed-IP check is the required acceptance result.

For an operator without a checkout, the same script can be run in Windows PowerShell:
```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/Grumlebob/BlazorAutoAppTemplate/main/Scripts/Test-DeployedSite.ps1))) -Address 192.168.0.212
```

**DHCP reservation: already done.** The operator confirmed the fixed lease `192.168.0.212` on 2026-10-09. Keep that reservation. Every deploy still detects the live address; a discrepancy with this lease needs investigation rather than silently changing the planned acceptance URL.

**Afterwards (day 2).**
- **New versions** are deployed on request, not on every merge: ask an agent, or use the template's Actions > "CD - Deploy LocalSingleNode" > Run workflow on `main`.
- **Backups** are written nightly to `/opt/books-backups`. Copy them elsewhere now and then, for example `scp -r <user>@192.168.0.212:/opt/books-backups D:\Backups\node-demo` (SSH works if your GitHub account has an SSH key; S17).
- **Power:** keep node-demo plugged in. Setup disables sleep, so a laptop lid may be closed. Updates and reboots are fine; the site and the runner come back on their own.
- **Reinstalling:** remove the old runner under Settings > Actions > Runners (it shows "Offline"), then repeat steps 1 to 3.
- **Removing the app:** see "Remove the app" in `HowToDeployLocalSingleNode.md`. Data volumes are deleted only by hand.

---

## 6. Verification matrix

| Change | Local proof | CI proof | Live proof (only if authorised) |
| --- | --- | --- | --- |
| Lock wrapper (P1.A) | `test-with-deploy-lock.sh` | Same test in `validate` | Next CD shows "lock acquired"/released |
| No unscoped CI prune (P1.B) | audit | audit in CI | none needed |
| Prometheus ports (P1.C1) | render validation with non-default ports | same | Grafana targets up |
| Rate limiting (P2.1) | unit + integration tests | test suite | - |
| Cache invalidation (P2.3) | tests | suite | - |
| Test containers (P3) | volume count unchanged; lifecycle test | lifecycle step | runner volume count stops growing |
| CI split (P5) | actionlint, audit | PR check `build-test-push` green; main uploads manifest | - |
| Dependabot (P6) | actionlint | next Dependabot PR summary | - |
| CD (P7) | syntax check, render, manifest tests | audit | CD run + acceptance + digest match |
| Maintenance (P8) | script tests | tests in CI | first scheduled run result |
| Common building blocks (P13.2) | `--list-tasks` output identical before and after for three LocalCluster playbooks; syntax check; render; audit | same | none (LocalCluster unchanged) |
| Target selection (P13.3) | guardrail test; actionlint | same | dispatching a disabled target fails at step 1 |
| LocalSingleNode (P13.4–P13.9) | fixture tests, render, compose config, syntax check, audit, rehearsal (P13.11) | same | node-demo: CD run, acceptance, reboot, redeploy, rollback, backup restore (P13.12) |

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Required check name changes and PRs can never merge | medium | high | P5 rule on `build-test-push`; confirm in the P5 PR before merging. Branch protection may need an owner edit (MB3). |
| Template CI runner unavailable or shared with ImprovedDb and slow | medium | medium | P0.3 runner check; PRs are small; no CI runs on CurrentPC. |
| Ported code drags in ImprovedDb names | high | low | 3.5 step 4 grep on every changed file. |
| Downgrading packages or overwriting newer template Cloud code | medium | medium | 3.3 rules; P4.2 comparison. |
| Parallel test collections cause flakiness | medium | medium | P3.5 classification; run the suite 3×. |
| Removing CI cleanup lets node-main fill up before P8 | low | medium | Capacity check fails loudly; P8 follows P5. Manual maintenance is documented. |
| Rolling deploy (`serial: 1`) with migrations | low | medium | Migrations still stop both apps first (unchanged play); serial only affects the start. |
| Lock format differences between apps on one node-main | low | high | P1.A treats unknown files as "not mine"; never deletes them. |
| GITHUB_TOKEN expires before nodes pull | low | medium | Pull happens inside the deploy job; the token lives for the job's duration. Staging pulls early. |
| Moving scripts to Common breaks the Books LocalCluster deploy | medium | high | P13.2 is a separate PR whose only proof is "LocalCluster renders and checks identically". Lock directory name unchanged (S10). |
| `DEPLOY_TARGETS` not set after P13b, so CD refuses | low | low | The agent sets it before opening P13b (P13.3 step 1). The gate fails closed with a clear message. |
| Single-node data loss (one disk) | medium | high | Nightly dump + restore test (S12); docs require an off-machine copy. |
| CI and CD on one PC starve each other in a one-PC fork | medium | medium | S8 keeps template CI elsewhere; docs explain the capacity reserve and the maintenance workflow. |
| `ssh_hardening` locks the operator out of password SSH on node-demo | low | low | Applied only when GitHub SSH keys were imported (S17); the console always works. |
| LAN HTTP breaks sign-in | low | medium | Checked: no HTTPS redirect, HSTS or secure-only cookie policy in the app. `Test-DeployedSite.ps1` proves it in CI and in P13.12 rows 3 and 4. |
| `deploy` user (docker group, passwordless sudo) is root-equivalent | certain | medium | Same as LocalCluster nodes. Dedicated node, LAN-only key SSH, UFW. Stated plainly in the docs (S7). |

---

## 8. Deferred (valuable, not in this plan)

| Item | Why deferred | Where it lives in ImprovedDb |
| --- | --- | --- |
| Generation-based public-data cache (`PublicDataCache*`) | Generic core, but keys/options are media-specific and Books does not need it. Port when a fork has mostly-static public data. | `BlazorAutoApp/Infrastructure/Hosting/PublicDataCache*.cs`, `Plans/MostlyStaticHybridCache.md` |
| Durable deploy supervisor + coordinator journal | Solves runner disconnects during multi-hour jobs; heavy (thousands of lines). | `Deployment/LocalCluster/Scripts/{cluster-coordination.py,supervise-localcluster-deploy.py,deploy_lock.py}` |
| Desktop CI runner pool | ImprovedDb-specific capacity solution. | `Scripts/CI/**`, `Plans/ParallelCiWithDesktopRunner.md` |
| Exact-SHA PowerShell deploy wrapper | Depends on the coordinator; `gh workflow run` + P7 checks cover the template. | `Scripts/DeployLocalCluster.ps1` |
| Multi-agent task coordination scripts | ImprovedDb process tooling. | `Scripts/Coordination/**`, `docs/Operations/MultiAgentCoordination.md` |
| Self-contained synthetic browser environment | Media-coupled; P5 Docker smoke covers the template's need. | `BlazorAutoApp.Test/E2E/Support/Synthetic*` |
| Application quality manifest/guard | ImprovedDb process. | `BlazorAutoApp.Test/TestSupport/Quality/**` |
| Generic "app secrets from GitHub secrets" pass-through in CD | New design, not a port; forks needing API keys can follow ImprovedDb's extra-vars pattern. | `cd-localcluster.yml` "Write GHCR deploy credentials" step |
| Removable target folders (`select-deployment-targets.sh`) | CI, the audit and the smoke live under `Deployment/LocalCluster/`; making every target deletable needs those moved first (S4). | - |
| Cloudflare tunnel and observability for LocalSingleNode | node-demo is LAN-only (Q6); observability adds a second stack (S13). | LocalCluster `cloudflared` and observability roles |
| Ubuntu + dotnet-install Dockerfile | Needed by ImprovedDb for Python/Skia. Template keeps MCR images so Dependabot can track them. | `BlazorAutoApp/Dockerfile` |

---

## 9. Manual blockers (only the operator can do these)

Resolved or not needed (rechecked 2026-10-08):

- **MB1 Template write access:** resolved. The agent pushed and merged P1–P9.
- **MB2 Working CI runner:** resolved. `node-main-books` (runner id 22) ran every job. Jobs only queued behind each other on the single runner.
- **MB3 Branch protection:** corrected on 2026-10-09. GitHub reports `main` as unprotected, the classic protection endpoint returns 404, and the effective branch-rules endpoint returns `[]`. Earlier green PR checks did not prove protection existed. This does not prevent execution: the agent must enforce the exact-head `build-test-push` and green-main gates before every merge. Q5 forbids changing protection; owner-enforced protection is a separate decision, not permission for the agent to bypass CI.
- **MB4 LocalCluster facts:** not needed (Q1).
- **Repository variables and Dependabot clean-up:** done by the agent (Q5).
- **Cloudflare:** not needed (Q6).

Still needing evidence, only for the P13.12 live test (up to about 40 minutes if installation is needed, mostly waiting; the full guide is P13.D). The current session is on the main PC, so the local agent and operator perform these on node-demo:

- **MB5 Install node-demo:** done, operator-confirmed 2026-10-09. The OS is installed and the repository is cloned; no further setup has been done. Verify the Mint version during local setup, without reinstalling.
- **MB6 Authenticate and ask on node-demo** (P13.D step 2): use the existing clone; check `gh auth status`, run `gh auth login` in the browser if needed, then start a local agent with "set it up, you are node-demo; fixed lease 192.168.0.212". Cloning is already done; authentication and agent setup are not yet confirmed.
- **MB7 The one sudo command on node-demo** (P13.D step 3), printed by its local agent with every argument filled in. P13.D step 4 is a required check run by the main-PC agent, not a manual blocker.
- **Node-demo network address:** resolved by the operator on 2026-10-09: `192.168.0.212`, fixed DHCP lease. No router reservation step remains. Detect and confirm the node's actual address and LAN CIDR during setup; SSH access and runner readiness are not implied by knowing the IP.

- **MB9 (optional) Live accounts (D15).** After a deploy that contains the fix, the old `admin@admin.com` and `user@user.com` accounts are locked automatically if they still used the default password. Deleting them afterwards is optional tidy-up. Releasing ImprovedDb (PR #238) is your call.

Nothing else is needed: no PAT, no GitHub secrets, no Cloudflare account and no branch-protection change.

## 10. Decisions (operator answers and delegated decisions, 2026-10-08; execution context updated 2026-10-09)

| ID | Question | Decision |
| --- | --- | --- |
| Q1 | Redeploy the template's own LocalCluster deployment as part of verification? | **No, not for now.** Verification stops at CI + the fresh-fork rehearsal (P12.3). P12.4 is skipped. Do not dispatch CD or mutate node-main for this plan. |
| Q2 | Should the template's `books` deployment keep existing on the nodes? | **Yes.** The template is also a deployment showcase, so Books and its LocalCluster/Cloud deployment files stay first-class. Docs describe the committed inventory as the template's own demo deployment that each fork regenerates from its own `machines.yml`. Do not delete or "sample-ify" the deployment configuration. |
| Q3 | Run the maintenance workflow on a schedule for the template? | **Ship it manual-only.** Keep the `schedule:` block commented out with a note telling forks to enable it; keep `workflow_dispatch`. |
| Q4 | Add a LocalSingleNode target and test it on node-demo? | **Yes** (operator request, 2026-10-08). Separate `Deployment/LocalSingleNode/` folder; forks choose targets with `DEPLOY_TARGETS`. Design decisions S1–S21 are in P13.A. Live CD to node-demo is authorised for P13.12; this does not change Q1 for LocalCluster. |
| Q5 | May the agent change repository settings and close PRs? | **Yes, within limits** (operator delegated routine decisions on 2026-10-08: "take intelligent recommendations"). The agent may set the repository variables `DEPLOY_TARGETS`, `LOCALSINGLENODE_HOST`, `LOCALSINGLENODE_RUNNER_LABEL` and `CI_RUNNER_LABEL`, and close superseded Dependabot PRs with a comment naming the replacing commit. It may not change branch protection or secrets, or manually alter existing runner registrations. P13.6's operator-run bootstrap on node-demo may register that node's runner, as required by Q4; it must preserve existing runners and keep template CI on node-main. |
| Q6 | Expose node-demo publicly? | **No.** LAN-only over HTTP through Caddy (S6). A tunnel is deferred (section 8). |
| Q7 | Dependabot #45 (checkout v7) and #87 (login-action 4.5.2) still touch `cd-cloud.yml`, which keeps `@v6`/`@v4` after P7. | Add both bumps to the P7 PR, then close #45 and #87 as superseded. |
| Q8 | A helper that deletes unused target folders? | **Deferred** (S4, section 8). |
| Q9 | Which machine runs this agent, and what is node-demo's address? | **Main PC is the controller** (operator clarification, 2026-10-09); observed Windows hostname `DESKTOP-FDU51L5`. **node-demo is a separate target at `192.168.0.212`, with a fixed DHCP lease.** The controller runs repository work, GitHub operations and P13.12 row 4. Native node setup runs only on node-demo; never bootstrap Windows or WSL as that node. Record the real address only in this execution plan/goal, not reusable deployment configuration. |

## 11. Completion record and handoff

Historical phase records were verified on 2026-10-08, about 13:10 UTC. D15 and the environment records were updated on 2026-10-09. Items marked "not confirmed" must be checked before anyone relies on them. Template PRs are in `Grumlebob/BlazorAutoAppTemplate`.

### 11.1 Phase status

| Phase | Template PR | Merge commit on template `main` | Verification | Status |
| --- | --- | --- | --- | --- |
| D15 | [#109](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/109) | `0115995228fabcfcdbe76e05e5a68d10d08ecf2f` | Local gate: 163 passed, 11 opt-in skipped; both audit mutation checks passed. Exact-head PR CI [37940054202](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37940054202) and main CI [37943481306](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37943481306) succeeded, including publishing. | Merged, verified |
| P0 | - | - | Runner worked (last `main` CI success 2026-09-28). 12 stale Dependabot PRs. Findings in 2.4. | Done |
| P1 | #101 | `5f1a86024c224daf6b5143a715d68d95a2b0ff59` | PR CI green (`bbf109c`, run 37768420570). `main` run 37771507324 success. | Merged |
| P2 | #102 | `d99b65e857cb4786f1d899f9210b38778241c21c` | PR CI green (`fdba3a1`, run 37771774997). Covered by the green `main` run 37776013256 of P3. | Merged |
| P3 | #105 | `675bf5e8167a4cf418d24b2d49fe6bc5d9cd41f4` | PR CI green (`26bb59a`). `main` run 37776013256 success. | Merged |
| P4 | #104 | `d72d22a725c6570465f3b5fccbdb260d8f9542b2` | PR CI green (`2934b6e`, run 37772146821). Its `main` run 37775251797 was cancelled (see 11.7). | Merged |
| P8a | #103 | `c683e789af52af3a466bff85aadc0ad5b7419b69` | PR CI green (`552a61a`, run 37771861192). Its `main` run 37773351490 was cancelled (see 11.7). | Merged |
| P5 | #106 | `3c13fef3f26c80b782be5d4f56a69c1c7a86efe2` | PR CI green (`0d750a9`, run 37776653144). `main` run 37778029231: `validate` success; publish job `build-test-push` (job 113324747811) success 13:15–13:18 UTC (smoke, push, manifest, upload); artifact `books-migrate-linux-x64` (id 11552703711) present. | Merged, verified |
| P6 | #108 | `4f476922362af635565859d54f000704a849d2d6` | PR CI green (`b18a154`, run 37778084296). `main` run 37782129527 success. First real Dependabot PR not yet observed (P6.4). | Merged |
| P7 | [#110](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/110) | `0e9257717434d0457eb74a84c19c82b2d7e9b921` | Local gate: 163 passed, 11 opt-in skipped; 24 release tests, identity fixtures and syntax/render checks passed. Exact-head PR CI [37945842490](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37945842490) and main CI [37947192982](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37947192982) succeeded, including publishing. | Merged, verified |
| P8 | [#111](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/111) | `3960b4855751a99d5e70866601522df7cdf6b390` | Local gate: 163 passed, 11 opt-in skipped; six shell suites and 51 Python tests passed. Exact-head PR CI [37949131184](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37949131184) and main CI [37950400186](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37950400186) succeeded, including publishing. No live maintenance. | Merged, verified |
| P9 | #107 | `37565a7a5cb3cd432b0295792b5f87f1381ed1f9` | PR CI green (`2f4afe3`, run 37776821466). `main` run 37780109019 success. | Merged |
| P10 | [#112](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/112) | `7b6699fcfddbcd378a0c2158843a49f5363ee5de` | Local gate: 167 passed, 11 opt-in skipped; all four agent guardrails passed; links and ignore rules checked. Exact-head PR CI [37952225896](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37952225896) and main CI [37953161424](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37953161424) succeeded, including publishing. | Merged, verified |
| P11 | [#113](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/113) | `f5949378b5fe3db8db2d11ef305c4bc5ae8325e6` | Local gate: 167 passed, 11 opt-in skipped; seven shell suites and 68 Python tests passed. Exact-head PR CI [37969690167](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37969690167) and main CI [37970580512](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37970580512) succeeded, including publishing. | Merged, verified |
| P12 | [#114](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/114) | `f4a9aba85e1016fc55c52dc333cd182c56dc4ca1` | Local gate: 169 passed, 11 opt-in skipped; seven shell suites and 68 Python tests passed. Exact-head PR CI [37972029836](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37972029836) and main CI [37972952941](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37972952941) succeeded, including publishing. Final merged fresh-fork rehearsal passed. Original merged branches deleted. P12.4 skipped (Q1). | Merged, verified |
| P13a | [#116](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/116) | `b12dcd5502bce4340d21dad3a2a546a2c4ac4e8b` | Integrated local gate: 173 passed, 11 opt-in skipped; eight shell suites and 68 Python tests passed; ten lock-handshake stress rounds passed. Original runner fixture failure, integrated cache-test race and CI lock-fixture startup race were fixed; failure logs remain retained. All three normalized task/order diffs empty; cluster marker render unchanged; syntax/render/link checks passed. Exact-head PR CI [37980438650](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37980438650) and main CI [37981571872](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37981571872) succeeded, including publishing. | Merged, verified |
| P13b | [#117](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/117) | `1ea1cd34346f71a554cadc5e0978b983f9ce05f1` | Local gate: 174 passed, 11 opt-in skipped; eight shell suites and 81 Python tests passed. Exact-head PR CI [37983621675](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37983621675) and main CI [37985192155](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37985192155) succeeded, including publishing. Both authorized variables read back after merge. | Merged, verified |
| P13c | branch `upgrade/p13c-local-single-node` | - | Final local gate: 175 passed, 11 opt-in skips; 15 shell suites and 122 Python tests; real Docker HTTP and two browser smoke tests passed. No node bootstrap or live dispatch. | Local gate passed; PR/main CI pending |
| P13 | - | - | P13a and P13b merged; P13c in progress. Node-demo live rows remain pending (Q4). | Executing |

### 11.2 Open items, in order

Current checkpoint (2026-10-09): items 0, 1, 2 and 4 are complete. P12 main validation/publishing and final fresh-fork rehearsal passed. P13a and P13b are merged and verified; P13c is in progress (item 5). Item 3 remains observational and does not block P13.

Rechecked 2026-10-08, after 13:40 UTC. Template `main` is at `7136072` (Dependabot #100, lighthouse 13.5.0, merged), and every `main` CI run since P3 is green.

0. **Security fix D15 first (PR `upgrade/d15-no-seeded-accounts`, before the stack).** Copy ImprovedDb PR #238 (`Grumlebob/ImprovedDb`, "Stop seeding known admin logins in deployments and lock existing ones"); its diff is the reference implementation. Read it with `gh pr diff 238 --repo Grumlebob/ImprovedDb`. The template's seeder file is the same as ImprovedDb's was before that PR.
   1. Copy `BlazorAutoApp/Features/Login/Account/Seed/LocalLoginAccountSeedExtensions.cs` and `BlazorAutoApp.Test/Features/Login/Account/LocalLoginAccountSeedTests.cs` from ImprovedDb `main` (after #238 merges). Change test-collection names only if the template's differ (`TestCollectionNames.Integration`). The seeder is then: on by default only in Development; Docker seeds only when `LocalAccounts:Enabled` is set; deployments lock accounts that still use the published passwords.
   2. In `appsettings.Docker.json`, set `"LocalAccounts": { "Enabled": false }` and remove both seeded passwords.
   3. In the repository-root `docker-compose.yml` (local developer stack; check it uses `ASPNETCORE_ENVIRONMENT: Docker`), add `LocalAccounts__Enabled: "true"`, so local Docker runs keep the demo logins. Check `Scripts/RunLocal.ps1` and `docs/HowToRunLocally.md`, which may name those logins, and keep them accurate.
   4. In `Deployment/LocalCluster/compose/app-server/docker-compose.yml` and `Deployment/Cloud/compose/app-server/docker-compose.yml`, add `LocalAccounts__Enabled: "false"` to `web`.
   5. Add the audit rule from #238 for the template's two deployment app compose files (LocalCluster and Cloud must contain `LocalAccounts__Enabled: "false"`; ImprovedDb's data-runner compose does not belong in the template) to the template's `audit_deployment.py`. Mutation-check it: delete the line from one compose file, see the audit fail, then restore the line.
   6. Gate, PR, merge. Rebase the stack (item 1) onto the result.
   7. **Live data:** the fix locks old default-password accounts by itself at the first start after a deploy, so no database work is required. Optionally, the operator deletes both accounts afterwards (MB9). For ImprovedDb, that happens with its next release after PR #238; this plan does not release ImprovedDb.
1. **Merge the stack P7 → P8 → P10 → P11.** The branches form a linear stack on `4f47692`: P7 `cb60566` ← P8 `9cdcac9` ← P10 `313e5ee` ← P11 `ac45b73`. Each one merges cleanly into `7136072` (`git merge-tree`). For P7:
   ```bash
   git fetch origin && git switch upgrade/p07-cd && git rebase origin/main
   # Q7: in .github/workflows/cd-cloud.yml set actions/checkout@v7 and docker/login-action@v4.5.2; commit that file.
   # Run the 3.6 gate. Then:
   git push --force-with-lease origin upgrade/p07-cd
   gh pr create --repo Grumlebob/BlazorAutoAppTemplate --base main --head upgrade/p07-cd --fill-first
   gh pr checks <pr> --repo Grumlebob/BlazorAutoAppTemplate --watch       # build-test-push green on the exact head
   gh pr merge <pr> --repo Grumlebob/BlazorAutoAppTemplate --squash --match-head-commit "$(git rev-parse HEAD)"
   ```
   Then wait for `main` CI (`validate` and the publish job) to go green. For each next branch, replace its old parent with the new `main`. Use the **old** parent SHAs given here, not the branch names:
   ```bash
   git fetch origin
   git rebase --onto origin/main cb60566 upgrade/p08-maintenance    # P10: 9cdcac9 upgrade/p10-agent-rules; P11: 313e5ee upgrade/p11-docs
   ```
   Then gate, `--force-with-lease` push, PR, merge and green `main`, the same as for P7. Add a "Verification" section with the gate results to each PR body (3.2). Force-pushing these `upgrade/*` branches is fine, because the agent created them and nothing else builds on them. Never force-push `main`. If a rebase conflicts, resolve it by keeping both sides' intent, re-run the gate, and say so in the PR.
2. **Close the superseded Dependabot PRs** (Q5), after P7 merges. Close #45, #61, #68, #75, #76, #87, #94, #96, #97, #98 and #99, each with `gh pr close <n> --repo Grumlebob/BlazorAutoAppTemplate --comment "Superseded: main already has <package> <version> (<commit>)."`. Do not delete their branches; Dependabot manages them. Verified on `main` `7136072`: every `Microsoft.AspNetCore.*` package is at 10.0.12, `tailwindcss` and `@tailwindcss/cli` are at `^4.3.3`, and `actions/setup-node@v7` and `actions/setup-dotnet@v6` are used everywhere. `actions/checkout@v6` and `docker/login-action@v4` remain only in `cd-cloud.yml`, which item 1 fixes. Recheck each PR right before closing it.
3. **First Dependabot PR after P6.** Dependabot opens it on its own schedule. When it appears, record whether it merged or showed "Auto-merge deferred: <reason>". Nothing to do until then.
4. **P12 closeout:** P12.1, P12.2, P12.3 (re-run on the merged `main`) and P12.5.
5. **P13**, all of it (P13.0 to P13.13). The operator's part is section 9 MB5–MB7 (P13.D), needed only at P13.12.
6. **Not authorised:** a live LocalCluster or Cloud deploy (Q1).

Resolved since the first handoff:

- **The P5 publish job is verified** (11.1). The manifest file itself was not opened; the first CD run (P13.12) validates it.
- **The runner is healthy.** The "stuck" jobs were queued behind each other on the single runner.
- **Commit `2073e2e`** is already on ImprovedDb `main` as `53961da`.

### 11.3 Runbook for whoever continues

- This session is on the main PC; node-demo is `192.168.0.212` (fixed lease). Follow 3.0 for implementation: verify the WSL/Docker prerequisites, clone or update the template repository inside the WSL filesystem, then `git fetch --all`. Preserve reviewed plan edits if moving from the Windows checkout. The historical stack is `upgrade/p07-cd` (`cb60566`), `upgrade/p08-maintenance` (`9cdcac9`), `upgrade/p10-agent-rules` (`313e5ee`), `upgrade/p11-docs` (`ac45b73`); recheck every tip before rebasing.
- Run the local gate in `docs/Test.md#local-gate` before pushing. Use the SDK band from `global.json`.
- Runner status: use the GitHub runners API and Actions logs from the main PC. Q1 forbids mutating node-main in this plan; do not restart its runner or change its services. node-demo's runner is installed by the operator-run bootstrap on node-demo only.
- Hard stops, same as `AGENTS.md`: no `docker volume prune`; no LocalCluster or Cloud CD dispatch; no force push to `main`; do not remove another app's runner, lock or images. Q4 already authorises LocalSingleNode CD to node-demo for P13.12. Never touch the LocalCluster deploy lock by hand.

### 11.4 Decisions made during execution

| Decision | Reason | Phase |
| --- | --- | --- |
| One `validate` job for PRs and `main`; `publish-main` only on `main`, carrying the `build-test-push` name there | One required check name; publish only after validation | P5 |
| `main` runs get their own concurrency group | A pending `main` run was replaced by a newer one (11.7) | P5 |
| `publish-main` builds the test project itself; ImprovedDb's publisher-harness artifact not ported | The harness belongs to ImprovedDb's publisher; the smoke only needs the test binaries (deviates from P5.4.7) | P5 |
| Browser-smoke filter lives in `ci-docker-smoke.sh`, not `BrowserSmokeCatalog.cs` | ImprovedDb's catalog seeds media data and is not a filter list (deviates from P5.5) | P5 |
| Smoke PostgreSQL published on a random loopback port | `PreHydrationControlsE2ETests` cleans up users through `E2E_CLEANUP_CONNECTION_STRING` | P5 |
| Ryuk stays enabled | Explicit disposal is proven by the lifecycle test; Ryuk is the backstop | P3, P5 |
| No GHCR token stored anywhere in CD | Nodes pull with the run's `GITHUB_TOKEN` through a temporary Docker config, by digest, from the verified manifest | P7 |
| Vault GHCR keys optional and set as a pair | Only needed for manual deploys of a private image | P7 |
| CD deploys only commits that are ancestors of `main`; default is the dispatched commit | "Only `main` deploys" rule | P7 |
| App nodes deploy one at a time and stop on the first failure; Caddy and cloudflared run after apps are ready | Keeps one node serving during a deploy without migrations | P7 |
| Maintenance is manual by default; `schedule:` is commented out | Decision Q3 | P8 |
| Artifact retention keeps the newest 2 and protects the last 2 successful deploys; fails closed if a lookup fails | Redeploy and rollback must still find their manifests | P8 |
| Host-wide Docker prunes need `--include-unlabelled-host-residue`; volumes are never pruned | The node-main Docker daemon is shared | P8 |
| The runner installer fails closed on an unreadable runner directory instead of deleting it | Deleting could remove a working runner | P8 |
| `prune-cluster-docker-residue.sh` requires host keys already in `known_hosts`; no DNS suffix assumed | The template must not hard-code cluster values | P8 |
| `AnalyzeSimulationReports.ps1` not ported | ImprovedDb's diff depends on a field renamed in its own simulation | P9 |
| `RunLocal.ps1` removes dangling images after a build; broader cleanup stays manual | Other projects' containers may share the Docker Desktop | P9 |
| `xunit` v4 deferred | Major version change | P4 |
| `Plans/` is tracked in the template; `Plans.local/` is ignored | `AGENTS.md` convention | P10 |
| Live deploy (P12.4) skipped | Decision Q1 | P12 |

### 11.5 ImprovedDb side

- This plan, its goal and the triage file live in this repository under `Plans/`. ImprovedDb keeps only a pointer (`Plans/BlazorAutoAppTemplateUpgrade.md` there links here).
- The planning session's branch `claude/fervent-lamport-6tcdxp` was restarted from `main` for ImprovedDb PR #238 (D15). Its old tip was `893643501f00c427d33caa8f6fbc24f3b7e19bdc`, and everything on it was already on `main` (`2073e2e` = `53961da`; the plan files landed by fast-forward). Delete the branch after #238 merges.
- ImprovedDb PR #238 is the reference fix for D15. It needs an ImprovedDb release to take effect; that is the operator's decision, outside this plan.

### 11.6 Environment knowledge

- **Current computer (2026-10-09):** operator's Windows main PC, hostname `DESKTOP-FDU51L5`; checkout `C:\Users\jgrum\Documents\Programming\Csharp\BlazorAutoApp`, origin `Grumlebob/BlazorAutoAppTemplate`. This is the controller, not node-demo.
- **Node-demo state (operator-confirmed, 2026-10-09):** OS installed and repository cloned, no further setup. Fixed DHCP lease `192.168.0.212`. Intended site after P13 deployment: `http://192.168.0.212/`; `http://node-demo.local/` is an additional mDNS address. Authentication, native Mint version, bootstrap, runner registration and a working site still need verification. Read-only TCP probes from the main PC on 2026-10-09 received connection refusals on ports 22 and 80; SSH and HTTP are not currently available. This is a setup-stage observation, not a failed P13 deployment.
- **WSL preparation (completed, 2026-10-09):** `Ubuntu-24.04` was exported to `C:\Users\jgrum\.codex\backups\template-sync-20261009-151806\Ubuntu-24.04-before-wsl2.tar`, then converted to WSL 2. Development user `grumbo` has `/home/grumbo/src/BlazorAutoAppTemplate`. `docker-desktop` and `ImprovedDb-CI` stayed running; the shared Docker engine was not restarted. Windows and WSL checkouts are on `main` at the observed `origin/main` SHA below, with the reviewed plan/config edits preserved as uncommitted changes in both. Do not alter `ImprovedDb-CI` for this plan.
- **Template head and CI (read-only checks, 2026-10-09):** current checkout and GitHub `main` are `fba2df2a8779e7f97eb00850d3212a0c20f166d9` ("old plans", committed 10:29:23 UTC). [Main CI run 37917917697](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37917917697) succeeded, including `validate` and `build-test-push`. Remote P7/P8/P10/P11 tips still match `cb60566`/`9cdcac9`/`313e5ee`/`ac45b73`. Recheck PR state and exact head checks before acting; these observations do not complete any pending phase.
- **Main-PC preflight (2026-10-09):** GitHub login `Grumlebob` has template admin and push access, verified from both Windows and native WSL `gh`. The WSL wrapper obtains an ephemeral token from the Windows GitHub CLI credential manager without storing another token in WSL. Runner `node-main-books` was online and idle; node-demo has no registered runner in this repository yet. Ubuntu has SDK `10.0.303`, PowerShell `7.6.6`, Node `24.21.0`, npm `11.19.0`, actionlint `1.7.12`, yamllint `1.38.0`, ShellCheck `0.9.0`, and provisioned ansible-core `2.21.0`. Python gate tools use the repository's constraints. Login shells load `~/.local/share/template-dev/environment.sh`. The Ansible installer `--check`, SDK selection from the repository, native Docker client/server `29.8.2`, and a disposable container reading and writing a native WSL bind mount passed. These are environment checks, not evidence that the pending application phases passed their gates. Preserve the uncommitted plan/config edits before changing checkout or rebasing.
- **Docker/WSL shutdown repair (2026-10-09):** Docker's shared host/guest socket mounts and CLI ISO mount were missing, causing the repeated Ubuntu integration error. They were restored without stopping the engine. Ubuntu shutdown also removed shared mounts and the VM-wide `WSLInterop` registration. Two Ubuntu-only services, `wsl-interop-protection.service` and `wsl-shared-mount-guard.service`, apply the protection described in [Microsoft's WSL init source](https://github.com/microsoft/WSL/blob/master/src/linux/init/init.cpp): a shadow binfmt status file and `mount --make-rslave /mnt/wsl` during shutdown. The first service calls `/usr/local/sbin/wsl-protect-interop`; both are enabled under `/etc/systemd/system`. Docker exports and Windows interop survived a subsequent Ubuntu termination. Full Docker Desktop/Windows restart was not exercised because other containers are active. Recheck integration after such a restart; remove these local workarounds once the installed WSL supplies equivalent protection. Intentionally terminating an integrated distro stops its proxy; use Docker's "Restart the WSL integration" action afterward.
- **D15 source (rechecked, 2026-10-09):** ImprovedDb PR #238 merged on 2026-10-08 at 15:11:48 UTC, commit `6d79bcbb4ec0b6fbe4c9ee0952e116fa6612483a`. Its reference fix is available; no wait for that merge remains.
- **SDK:** `global.json` pins `10.0.300` with `rollForward: latestFeature`. Use a 10.0.3xx SDK. The sandbox only had 10.0.1xx and built from a copy without `global.json`. That workaround must not be committed.
- **Solution file:** `dotnet format` takes `BlazorAutoApp.sln`, not `.slnx`.
- **Playwright:** the template pins `Microsoft.Playwright` 1.63.0, which expects Chromium revision 1243. Install with `pwsh BlazorAutoApp.Test/bin/Release/net10.0/playwright.ps1 install chromium`. Do not use `--with-deps`, and do not alias browser directories by hand.
- **E2E:** `RUN_E2E=1 E2E_BASE_URL=https://localhost:7186 E2E_HEADLESS=1`, then the filter in `docs/Test.md`. The local app needs Postgres, Redis and a development certificate.
- **Test status:** the template suite with Docker on the P3 branch: 155 passed, 11 skipped (opt-in E2E, observability and lifecycle tests). The first full E2E run was 12 of 13 passing. `BooksE2ETests` was fixed and passes 3 of 3. The full E2E set has not been rerun since the fix.
- **Books E2E gotcha:** the author shelf (`bookcase-track-auto`) auto-scrolls and pauses only on hover, focus or active. Tests must hover a book before clicking it. The animation is disabled on touch devices, narrow widths and reduced motion. This failure also exists on `main` without the fix.
- **Docker Hub:** anonymous pulls of `rhysd/actionlint:1.7.12` hit the rate limit from the sandbox. Use the actionlint 1.7.12 release binary, or log in to Docker Hub. CI pulls the image on the runner.
- **Linters:** yamllint 1.38.0, pip 26.2.1 and Jinja2 3.1.6 are pinned in `Deployment/Common/ci-python-constraints.txt`. Run shellcheck with `--severity=warning` over the same file list as CI.
- **Shared-host test trap:** `test-with-deploy-lock.sh` failed while another `ansible-playbook` ran for the same user. Fixed in P5 (commit `88a6f0b` on the P5 branch): the test skips that case and resets the lock. Tests about host-wide process state must tolerate other apps' jobs.
- **Shared host:** node-main runs the template runner (`node-main-books`), the ImprovedDb runner (`node-main-improveddb`) and the Docker daemon for both. The deploy lock is `/tmp/localcluster-deploy.lockdir`. Do not prune volumes. Do not restart a runner without checking its jobs.
- **Single runner:** PR jobs and `main` jobs share one runner, so queued `main` jobs can wait behind PR jobs. The publish job waited behind other jobs.
- **Required check:** `build-test-push` remains the plan's mandatory merge gate, but GitHub does not currently enforce it through protection or effective branch rules on `main` (MB3). The agent must verify the exact head check itself and use `--match-head-commit`; do not merge because an unprotected branch permits it.
- **LocalCluster Caddy** binds `127.0.0.1` and is reached only through the Cloudflare tunnel on node-main. Its site template loops over `app_servers`.
- **`deploy` user:** on LocalCluster nodes it has passwordless sudo (`install-github-runner.sh` runs `sudo ./svc.sh`, and roles use `become`).
- **App and plain HTTP:** the app has no HTTPS redirection, no HSTS and no secure-only cookie policy. It supports `ForwardedHeaders:KnownNetworks`.

### 11.7 Corrections to earlier statements

- 2026-10-10 P13c review: CI workflow dispatch cannot satisfy P7 push provenance. Setup reruns/watches an existing main push run; no CI capacity defers fork customization and CI until root/variables/runner finish. A fresh OS may lack gh, so the unprivileged tools step installs the checksum-verified official CLI before authentication. Original-user Ansible uses a new user-only mode; no original-user sudoers change. Optional fork CI explicitly grants Docker group access for its local gates, with a fresh group session and root-equivalence disclosure.
- P13c detects the default-route interface without a public probe IP, preserves install_user during deploy refresh, and gives deploy the operator backup group so 0640 dumps/secret copies work in both nightly and CD contexts. Runtime secrets remain 0600. SSH hardening follows successful public-key import; missing keys retain password authentication. libnss-mdns and LAN mDNS rules are explicit prerequisites.
- P13c inspects existing app directories/shared Caddy before ownership changes, reuses repository configuration or unmodified package defaults, and fails on foreign configuration. Nightly backup takes the shared lock; manual maintenance waits for backup before taking it. Image cleanup uses repository proof and protects all container images/current digest; global dangling prune was incorrect for shared hosts. Reboot waits for the entire workflow’s successful completion, then 30 seconds.
- LocalCluster’s installer previously selected latest runner per new install, despite the plan calling it pinned. Both new installations now use reviewed runner 2.338.0 and its published SHA256; the user-local CLI pin is 2.102.0. Existing registrations/services are not restarted by this controller. Both single-node playbooks explicitly load target settings and Common release variables for temporary inventories. HTTP login/negative/deleted-user checks use independent sessions; cleanup runs in finally.

- 2026-10-09 P13a review: Ansible rejects its reboot action for a local connection, so the moved Mint base role gains a default-true guard and single-node preparation will defer reboot. Caddy extraction changes task role prefixes; raw and precisely normalized task/order diffs are retained separately. Common runner cleanup now takes explicit app/root selection instead of reading LocalCluster settings. Cloudflare marker fields are optional with unchanged cluster rendering. The Common README incorrectly still said main push or dispatch; it now matches P7's push-only publisher provenance. No LocalCluster, Cloud or node bootstrap was run.

- 2026-10-09 P12 review: the old stack lacked the generic favicon tests and shared ProblemDetails helper; the integration PR completes both. The triage inventory records specific substitutions and deferrals for every remaining unchanged or absent PORT/ADAPT/REVIEW row. A changed filename alone was not treated as proof of implementation.

- 2026-10-09 P11 review: SSH onboarding now verifies the fingerprint before trusting the same scanned key. Deployment docs explicitly require a successful main push and publish-main on the exact CI attempt. D15 local-account guidance survived the clean rebase unchanged. The audit enforces the new documentation contract.
- 2026-10-09 P8 review: observability now reads the shared disk thresholds; CI network deletion requires both ownership provenance and an app-specific network name; runner reuse rejects missing repository identity. Offline fixtures and the audit enforce these changes. The P8 rebase onto verified P7 main was clean. No maintenance was dispatched.
- 2026-10-09 Dependabot cleanup: #45, #61, #68, #75, #76, #87, #94, #96, #97, #98 and #99 were rechecked against main `0e925771` and closed with replacement-version comments. Their branches were retained.
- 2026-10-09 P7 helper adaptation: the template downloads the named release artifact from the verified CI run with actions/download-artifact@v8, then validates repository, SHA, run, attempt, registry digest and bundle checksum with `validate_release_manifest.py`. It retains its P5 migration staging validator. The reference ZIP extraction helpers (`release_artifact.py`, `validate-ci-release-artifact.py` and their two test modules) consume coordinator-frozen artifact IDs/digests and are not copied as unused code. These rows are handled by the template release validators and tests; P12 records the mapping in the triage inventory.
- 2026-10-09 execution: P12 closeout does not mark the full plan complete before P13. The next Dependabot PR is observational (11.2 item 3) and does not block P13; the goal completion definition requires items 0, 1, 2, 4 and 5. P13 starts after P12 closeout and green main CI.
- 2026-10-09 P7 review: the existing branch selected a successful overall CI run but did not explicitly require the publish-main job. The helper now verifies the successful `build-test-push` publishing job on the selected main push, exact run attempt and SHA, then rechecks run identity to reject a rerun race. Main workflow_dispatch runs are excluded as required by P7.4.7. The deployment audit and fixtures enforce this contract.
- 2026-10-09 D15: the reference audit covers three ImprovedDb compose files, including its product-only data runner. The template has two deployment app compose files. Both are enforced here; P13 adds the LocalSingleNode equivalent when that target exists. No data-runner content is ported.
- 2026-10-09 setup: the earlier WSL 1/missing-tool observations are superseded by the prepared WSL 2 checkout and environment checks in 11.6. Windows `main` and the new native WSL checkout now match `origin/main`; the reviewed plan/config changes remain uncommitted. Ubuntu shutdown protection was added after reproducing the Docker shared-mount and interop failures.
- 2026-10-09 preflight: MB3 previously inferred branch protection from successful PR merges. GitHub now reports no classic protection and no effective rules for `main`. Keep the plan's CI gates mandatory, without changing repository protection under Q5. The operator also confirmed installation and clone are done on node-demo; only subsequent setup remains. Main CI, template admin access, the existing CI runner and the D15 source merge were rechecked in 11.6.
- 2026-10-09: the operator confirmed this session runs on the main PC and node-demo has the fixed lease `192.168.0.212`. Main-PC acceptance is now an agent task and a required P13.12 result. The older optional operator check and router-reservation reminder no longer apply to this live test. Machine setup must reject Windows/WSL and run only on the intended deployment node.
- 2026-10-09: 3.0 incorrectly requested ImprovedDb push rights for plan corrections, although this plan lives in the template and ImprovedDb is read-only. Read access is sufficient. 11.3 also suggested restarting node-main's runner, which contradicted Q1; use read-only GitHub diagnostics instead. Q5 now names the existing P13.6 bootstrap exception for node-demo runner registration.
- The P8a row used to say its `main` run was "cancelled by the old shared concurrency group (D5)". That mechanism was not verified. What was observed: P8a's `main` run (37773351490) was marked cancelled at 12:12:36 UTC, when P4's merge queued a `main` run. P4's run was then cancelled at 12:19:10 UTC when P3's merge queued one. This matches GitHub's rule that a newer run replaces a pending run in the same concurrency group. P5 gives `main` runs their own groups, which avoids that case. The cause has not been confirmed separately.
- PR #106's body says the P5 change "fixes D5" and cites the cancelled P8a run. Treat the causal link as unconfirmed for the same reason.
- PR #105's body says all 13 non-observability E2E tests pass. The first full run was 12 of 13. The failing test was fixed and its class passed 3 of 3. The full set was not rerun after the fix.
- Earlier drafts said `origin/main` lacked the ledger removal in `2073e2e` and had 20 commits the branch did not. Both were wrong when checked on 2026-10-08. `53961da` (PR #218) is the same change, and `origin/main` had 40 such commits. See 11.2 item 4 and 11.5.

### 11.8 Verification log

- Template PRs: each PR's `build-test-push` check was green on its exact head before the squash merge (11.1).
- Template P10 branch, local: `dotnet format --verify-no-changes` clean; Release build succeeded; architecture tests 32 of 32; deployment audit passed; actionlint 1.7.12 clean; yamllint clean; shellcheck clean; render validation passed with and without a digest.
- P5 Docker smoke on the rebased tree: HTTP smoke passed; both browser tests passed after the smoke database fix; no CI containers or networks left behind.
- P8 fixture tests: maintenance, low-disk prune, runner residue, CI residue sweeper, artifact retention, identity verification, deploy lock (15 repeated runs, and once with a live `ansible-playbook` process present).
- Fresh-fork rehearsal with fake values: common release validation, deploy settings validation, inventory generation, summary, rendered templates and audit all passed. The DNS check was skipped as expected.
- ImprovedDb plan: 14 changed Markdown files, no broken relative links.

### 11.9 Template branches to delete after merge

Record these short SHAs before deleting. Get full SHAs with `git ls-remote origin 'upgrade/*'`.

- `upgrade/p01-shared-cluster-safety` `bbf109c09`
- `upgrade/p02-app-runtime` `fdba3a1b7`
- `upgrade/p03-test-infrastructure` `26bb59a56`
- `upgrade/p04-dependencies` `2934b6ed4`
- `upgrade/p05-ci` `0d750a910`
- `upgrade/p06-dependabot` `b18a154eb`
- `upgrade/p08a-check-only-provisioning` `552a61aa5`
- `upgrade/p09-local-dev` `2f4afe3aa`

All original upgrade branches are now merged. The full head ledger below preserves them before deletion; delete only after checking that each remote head still matches its merged PR.


### 11.10 P0–P12 integration checkpoint (2026-10-09)

P1–P11 and D15 are merged. Verified main checkpoint: `f5949378b5fe3db8db2d11ef305c4bc5ae8325e6`, [CI 37970580512](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37970580512), validation and publishing successful. P12 adds the remaining generic favicon tests and shared ProblemDetails helper, records all triage decisions and reruns the fresh-fork rehearsal. Its exact-head and final main CI evidence will be recorded in the integration PR description after merge. P12.4 remains skipped under Q1. The overall status stays executing until P13 live testing and closeout.

Merged branch heads recorded before deletion:

| PR | Branch | Last head | Merge |
| --- | --- | --- | --- |
| #101 | `upgrade/p01-shared-cluster-safety` | `bbf109c091d86374d56fea8bed1c92f6b2ca0ef4` | `5f1a86024c224daf6b5143a715d68d95a2b0ff59` |
| #102 | `upgrade/p02-app-runtime` | `fdba3a1b744a76968a89a75c1e327d1f2d992df8` | `d99b65e857cb4786f1d899f9210b38778241c21c` |
| #103 | `upgrade/p08a-check-only-provisioning` | `552a61aa5f279fe1ff3c9684e492c4bebcd9c98f` | `c683e789af52af3a466bff85aadc0ad5b7419b69` |
| #104 | `upgrade/p04-dependencies` | `2934b6ed4c087743ad810d898de57a03fbc73b26` | `d72d22a725c6570465f3b5fccbdb260d8f9542b2` |
| #105 | `upgrade/p03-test-infrastructure` | `26bb59a56077ef183f369dc4e4b509959a0e1c41` | `675bf5e8167a4cf418d24b2d49fe6bc5d9cd41f4` |
| #106 | `upgrade/p05-ci` | `0d750a91001315f2371966344d57252155febfc1` | `3c13fef3f26c80b782be5d4f56a69c1c7a86efe2` |
| #107 | `upgrade/p09-local-dev` | `2f4afe3aab245be0cc32884dd0d7557be8206862` | `37565a7a5cb3cd432b0295792b5f87f1381ed1f9` |
| #108 | `upgrade/p06-dependabot` | `b18a154eb8d595a3bb2d28d2930d93b504d338c2` | `4f476922362af635565859d54f000704a849d2d6` |
| #109 | `upgrade/d15-no-seeded-accounts` | `c338bb7b6702846f4517d392f00e0b5be3478e65` | `0115995228fabcfcdbe76e05e5a68d10d08ecf2f` |
| #110 | `upgrade/p07-cd` | `e255f900ce2930b7b81577c516a2b0145edea7a2` | `0e9257717434d0457eb74a84c19c82b2d7e9b921` |
| #111 | `upgrade/p08-maintenance` | `eb35e1b6b75cbdf90eb3a3f4f0bb91a78e6ca97a` | `3960b4855751a99d5e70866601522df7cdf6b390` |
| #112 | `upgrade/p10-agent-rules` | `e9c0a741ff6c717701f651fbee555fbaeb1c8b57` | `7b6699fcfddbcd378a0c2158843a49f5363ee5de` |
| #113 | `upgrade/p11-docs` | `5c58a33595db8d73a6ef0a6df8b956cc4f61c6ed` | `f5949378b5fe3db8db2d11ef305c4bc5ae8325e6` |

P12 local verification: 169 passed, 11 existing opt-in skips; build 0 warnings/errors. Gate `upgrade-p12-integration-gate-20261009T181339Z.log`; fixtures `upgrade-p12-integration-fixtures-20261009T181339Z.log` (seven shell suites, 68 Python tests); fresh-fork `p12-fresh-fork-20261009T180512Z.log` (six checks, ignored-file checks, encrypted-vault assertion and local commit, no push or deploy). The first local commit attempt reported missing Git author identity; the guide now explains checkout-local author settings. Review also corrected the false claim that LocalCluster vault.yml is ignored: only its encrypted contents are tracked, and a fork creates its own vault/password. Live SSH trust and external dashboard/authentication steps were not exercised in the offline rehearsal.

P12 final checkpoint: `f4a9aba85e1016fc55c52dc333cd182c56dc4ca1`, main CI [37972952941](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37972952941), validation and publishing successful. Final merged fresh-fork log `p12-fresh-fork-20261009T182441Z.log` passed. The thirteen original heads in 11.10 were verified against merged PRs and unchanged remote refs, then deleted with explicit leases. P12 integration branch head `6c2695154512df7b23746f081e7f749ed8feab8b` (#114) was recorded in its verified PR description and deleted with the same checks. All fourteen merged upgrade branches are deleted.

### 11.11 P13a shared-building-block review

The P13a PR will record the reuse inventory, exact moves, raw Caddy role-prefix difference, empty normalized task/order comparisons, syntax checks and gates. LocalCluster topology, shared lock directory/variables, app marker location and default guards remain compatible. Common helper selection is explicit, and check-only prerequisites have offline fixtures. Single-node preparation will disable controller reboot and deploy-key lookup; its live deployment remains a later P13 step.

P13a local evidence: `upgrade-p13a-common-building-blocks-gate-20261009T184527Z.log`, `upgrade-p13a-common-building-blocks-fixtures-20261009T184454Z.log`, `p13a-reuse-inventory.log`, `p13a-raw-site.yml.diff` (only six Caddy role prefixes), and three empty `p13a-normalized-*.diff` files. Fresh/existing preparation raw diffs are also empty. Cluster marker before/after outputs are identical; a marker without Cloudflare fields renders correctly. All five changed Markdown documents passed local file/heading checks. No old moved path references remain in the required operational/contributor scopes; historical plan paths are retained.

### P13a concurrent security integration

Separate PR #115 removed default Admin seeding and merged as `f4ec5d11c5c782ad7e58dcadb0cc2ee664133114`. The original Windows security checkout is preserved; this upgrade uses an isolated Windows validation worktree and the native WSL checkout. PR #116 was rebased onto the security merge without conflicts. Its obsolete CI run 37975790647 (head `4699d55e097379b0c8b424e5642766ef8f58afb6`) was cancelled to release the single runner for security main CI; it is not evidence of a test failure or success. The complete local gate, fixtures and after-move task/render comparison are rerun on the integrated code before the revised PR head is pushed. Security main CI must be green before publication/merge of the revised upgrade. Existing security behavior is retained.

P13a integrated gate `upgrade-p13a-common-building-blocks-gate-20261009T190530Z.log` failed at the missed-pubsub cache test: 172 passed, one failed, 11 opt-in skipped. The failure was the immediate stale-list assertion (line 124), not eventual expiry. The test used a real one-second L1 TTL and only one cache load, which can race asynchronous HybridCache tag reads. The revision primes tag reads with a second pre-write load and controls only Node B’s actual MemoryCache clock. It retains the stale-data assertion and strengthens expiry coverage: stale at 999 ms, fresh at exactly 1 s, without sleeps/retries or production changes. [HybridCache 10.10.0 uses the registered memory cache](https://github.com/dotnet/extensions/blob/v10.10.0/src/Libraries/Microsoft.Extensions.Caching.Hybrid/Internal/DefaultHybridCache.cs), and [tag checks treat pending reads as invalid](https://github.com/dotnet/extensions/blob/v10.10.0/src/Libraries/Microsoft.Extensions.Caching.Hybrid/Internal/DefaultHybridCache.TagInvalidation.cs). The failed log remains retained; the complete gate is rerun after the fix.

Integrated P13a revision local gate: `upgrade-p13a-common-building-blocks-gate-20261009T191257Z.log` (173 passed, 11 opt-in skipped; build 0 warnings/errors), `upgrade-p13a-common-building-blocks-fixtures-20261009T190530Z.log` (eight shell suites, 68 Python tests). Repeated after-move syntax/task evidence still has three empty normalized diffs and the same six Caddy role-prefix changes. Security main CI 37977675409 succeeded, including validation and publishing.

P13a exact-head CI [37979430446](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/37979430446), head `adabef6205b92eef4055b820e4e974370ba4ec12`, failed its deployment-lock fixture. Log `p13a-ci-lock-failure-37979430446.log` is retained. The fixture waited for the lock token, but the wrapper writes that token before launching its owned command. SIGTERM can therefore correctly cancel before any child exists, contrary to the fixture’s assumption. The fixture now waits for an explicit child-ready file and the existing signal-handler diagnostic, then checks the lock is still held while the child is blocked. It explicitly releases the child and retains the child-finished, wrapper exit 143 and lock-removed assertions. Production lock behavior and protection rules are unchanged. The complete local gate and fixtures are rerun before the next exact-head CI attempt.

P13a lock-fixture correction verification: `upgrade-p13a-common-building-blocks-gate-20261009T192347Z.log` passed (173 tests, 11 opt-in skips; build 0 warnings/errors; all format/validation/audit/render/lint gates). `upgrade-p13a-common-building-blocks-fixtures-20261009T192347Z.log` passed (eight shell suites, 68 Python tests). `p13a-lock-handshake-stress-20261009T192423Z.log` passed all ten full lock-fixture rounds. No live deployment lock was touched.

P13b local preparation starts from the P13a squash on origin/main while its main CI runs. No P13b PR or push occurs before P13a main validation and publishing are green. Initial twelve offline fixtures execute all four existing target gates and all four CI host profiles; they passed with audit and actionlint. Full local gate and all script fixtures are rerun before publication.

P13a verified checkpoint: PR #116 head `eeb8d234ba1ad45fb52c56d2c5ea66882e6e6b3b`, squash `b12dcd5502bce4340d21dad3a2a546a2c4ac4e8b`, PR CI 37980438650 and main CI 37981571872 succeeded. Existing local evidence and the initial fixture failure remain recorded above.

### 11.12 P13b target-selection review

Every existing CD and maintenance job checks its enabled target before checkout or deployment work. Matching strips ASCII spaces and uses exact comma-delimited target names; empty, unrelated, case-mismatched and prefix/suffix values fail closed. All CI and Dependabot jobs use the neutral CI runner label and configured host with the current LocalCluster/node-main defaults. LocalCluster CD and maintenance still verify node-main. Offline fixtures execute the actual workflow gates and all four actual CI host-profile scripts with temporary command stubs. No workflow is dispatched to test a disabled target, because Q1 forbids LocalCluster and Cloud deployment.

P13b publication evidence: `upgrade-p13b-target-selection-gate-20261009T194639Z.log` (174 passed, 11 opt-in skips; build 0 warnings/errors; full format/validation/audit/render/lint gate), `upgrade-p13b-target-selection-fixtures-20261009T194639Z.log` (eight shell suites, 81 Python tests). Thirteen new fixtures include the explicit single-node comma-list/localsinglenodex/empty/space cases and all four actual CI profiles. Repository variables were set and read back: DEPLOY_TARGETS=localcluster,localsinglenode and LOCALSINGLENODE_HOST=node-demo. Template CI variables were not changed; current defaults keep CI on node-main. No CD or maintenance workflow was dispatched.

### 11.13 P13c implementation checkpoint

P13b checkpoint: exact head `03ada8f0d780411b3820b517773c625173357b2c`, PR #117, squash `1ea1cd34346f71a554cadc5e0978b983f9ce05f1`, PR CI 37983621675 and main CI 37985192155 succeeded. Both authorized variables were read back. Template CI still uses node-main.

P13c initially branched from that squash. A separate session merged security follow-up #118 (`eef5809beec83e508afa1c271d5316796a3fc12d`) and docs #119 (`365f58881cd31f595a1ea374f2a77d9f18c029a4`); main CI 37991053326 succeeded. P13c’s own local commit was rebased cleanly onto that newest main before its full gate; the separate Windows checkout remained untouched.

Early development checks found an unused shell loop variable, target-neutral CI lint/runner rules that still assumed every workflow used node-main, two disallowed IPv4 test/OS literals, a doctor fixture count that omitted the native-platform check, and a trailing blank line. These were corrected before publication. Replacement audit rules preserve the existing LocalCluster protections while checking single-node host/label/loopback/provenance/ownership contracts. Offline backup/restore/doctor fixtures use temporary files and stubbed commands; no privileged bootstrap, runner install or live maintenance was executed here.

Local scripts already passed both playbook syntax checks, Compose/environment/Caddy rendering, target gates, smoke failure cleanup and 32 single-node Python tests. The full gate, all fixture suites, real Docker HTTP smoke and Markdown checks are required before publication. Node-demo remains OS plus existing clone only. The operator will update that clone themselves; final handoff must provide one prompt for its local AI to follow AgentSetup.md, and no controller bootstrap is authorized.

P13c first complete gate passed: `upgrade-p13c-local-single-node-gate-20261009T230441Z.log` (175 tests, 11 opt-in skips, zero build warnings/errors); `upgrade-p13c-local-single-node-fixtures-20261009T230453Z.log` passed 15 shell suites and 113 Python tests. Review then added per-app bootstrap markers to preserve other apps and image cleanup proof for historical CI labels as well as OCI source metadata. Multi-tag/foreign-reference images are preserved without forced removal. New CI builds carry OCI source labels. The final full gate is rerun after these changes, and real Docker HTTP/browser smoke runs before publication.

P13c final publication checks passed: `upgrade-p13c-local-single-node-gate-20261009T232409Z.log` (175 tests, 11 opt-in skips, zero warnings/errors), `upgrade-p13c-local-single-node-fixtures-20261009T232409Z.log` (15 shell suites and 120 unique Python tests: LocalCluster 23, Common 41, LocalSingleNode 39, CI 17), `p13c-extra-20261009T232409Z.log` (both playbook syntax checks, four changed Markdown documents and control-character scan), and the Windows PowerShell 5.1 parser. Recovery fixtures cover missing runner services, owned interrupted startup, active registrations, foreign secret directories and Docker/LAN subnet overlap.

Real Docker proof passed in `p13c-real-docker-smoke-20261009T232334Z.log`: all ten HTTP checks, including fresh-session password login and finally-account deletion, plus both Playwright browser smoke tests. Unique run labels, tmpfs databases and exact private proof-image labels scope cleanup; no volumes or shared runners were changed. Earlier failure logs remain retained: `p13c-real-docker-smoke-20261009T230725Z.log` caught overlong Docker DNS labels, fixed with short network aliases; `231239Z`/`231432Z` caught PowerShell's read-only HOME assignment, renamed homeResponse; `231518Z`, `231933Z`, `232014Z`, `232038Z` and `232105Z` caught a generated backspace in the input regex, replaced with literal backslash-b and guarded against control characters. `232211Z` passed HTTP but exposed missing libnspr4 in this main-PC WSL test environment; Playwright's official dependency installer repaired that environment only. The final complete local gate and fixture suites ran after all code fixes. No privileged node setup or deployment has occurred.

P13c final review preserved offline existing CI registrations: temporary offline status never requests --ci-runner or changes the existing CI host. Only absence of the selected CI label registration can request new fork capacity; an explicit existing bootstrap CI flag is retained. Public-CLI fixtures cover both the root command and subsequent CI step. Manual replacement restore also refuses names longer than PostgreSQL’s 63-character identifier limit before any database command. After these changes, `upgrade-p13c-local-single-node-gate-20261009T233020Z.log` passed all 175 tests/11 opt-in skips and the full gate; `upgrade-p13c-local-single-node-fixtures-20261009T233020Z.log` passed 15 shell suites and 122 unique Python tests (41 single-node). `p13c-extra-20261009T233214Z.log` repeated syntax/control-character/link checks. The earlier real HTTP/browser proof is unchanged. Initial PR run 38004425567 tested the preceding head and is superseded for merge purposes; the updated exact head requires its own successful PR run.

P13c interruption review: GitHub automatically cancelled superseded PR run 38004425567 during Docker/browser smoke. Its following exact-tag image removal correctly refused to force-delete an image still referenced by a smoke container; retained log `p13c-superseded-ci-38004425567.log` records that cancellation snapshot. No controller command reclaimed node-main resources. Both CI smoke jobs now have an always-run, exact-repository/run/attempt cleanup step before image handling. Cleanup-only rejects missing run identity, never starts a stack and verifies owned residue is gone; foreign objects and other runs are preserved. The audit enforces both jobs and cleanup ordering. Offline interrupted-leftover/idempotence/foreign-run fixtures and real private Docker proof `p13c-real-interruption-cleanup-20261009T233755Z.log` passed. HTTP plus both browser tests passed again in `p13c-real-docker-smoke-20261009T233827Z.log`; `upgrade-p13c-local-single-node-gate-20261009T233912Z.log` repeated the full 175-test/11-skip gate, `upgrade-p13c-local-single-node-fixtures-20261009T233912Z.log` repeated 15 shell suites and 122 Python tests, and `p13c-extra-20261009T233912Z.log` repeated syntax/link/control-character checks. This new head requires its own PR CI; no live maintenance or deployment was dispatched.
