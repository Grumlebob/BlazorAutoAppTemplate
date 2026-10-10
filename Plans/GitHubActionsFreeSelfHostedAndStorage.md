# GitHub Actions Free Self-Hosted And Storage Execution Plan

## Goal

Completely fix `Grumlebob/BlazorAutoAppTemplate` so it stops using avoidable GitHub Actions storage, stops using avoidable GitHub-hosted jobs, keeps deployment working, and does not reintroduce the same failure mode later.

The project lives here:

```text
%USERPROFILE%\Documents\Programming\Csharp\BlazorAutoApp
```

This plan intentionally uses `%USERPROFILE%\Documents\Programming\Csharp\ImprovedDb` as the reference implementation because ImprovedDb was cloned from this project and later hardened for:

- `node-main` self-hosted CI/CD.
- short migration artifact retention.
- exact-name artifact pruning.
- persistent-runner prerequisite bootstrap.
- persistent-runner Docker cleanup.
- workflow audit enforcement.
- safer CI to CD artifact ordering.

## Current State - 2026-06-19

Local repo:

- Local clone: `%USERPROFILE%\Documents\Programming\Csharp\BlazorAutoApp`.
- Remote: `origin https://github.com/Grumlebob/BlazorAutoAppTemplate.git`.
- Fast-forwarded to `origin/main` during planning.
- Current `origin/main`: `ec489759ea5eaa4a469a35ccecd068e04d12e2ab`.
- Worktree was clean before this plan file was added.

GitHub repo:

- Repo: `Grumlebob/BlazorAutoAppTemplate`.
- Visibility: public.
- Default branch: `main`.
- Existing self-hosted runner:
  - name: `node-main-books`
  - labels: `self-hosted`, `Linux`, `X64`, `localcluster`, `localcluster-books`
  - status: online
- Repo variable:
  - `LOCALCLUSTER_RUNNER_LABEL=localcluster-books`
- Environments:
  - `localcluster`
  - `cloud-hetzner`
- Repo secret:
  - `ANSIBLE_VAULT_PASSWORD`
- Cloud environment secrets exist for `cloud-hetzner`, including SSH, Hetzner, GHCR, PostgreSQL, Redis, and Cloudflare values.

Current release/deploy identity:

- `app_name: books`
- `app_image: ghcr.io/grumlebob/books`
- `migration_bundle_name: books-migrate`
- `migration_runtime: linux-x64`
- current migration artifact name: `books-migrate-linux-x64`

Current Actions storage:

| Artifact group | Count | MB | Notes |
| --- | ---: | ---: | --- |
| `ship-migrate-linux-x64` | 68 | 4332.2 | obsolete old app name |
| `books-migrate-linux-x64` | 46 | 2751.6 | current app, but unbounded old CI artifacts |
| SARIF artifacts | 8 | 0.4 | tiny, not the storage problem |
| Total artifacts | 122 | 7084.2 | too high |
| Caches | 36 | 822.7 | mostly npm and CodeQL caches |

Current workflow problems:

- `.github/workflows/ci.yml` uses `runs-on: ubuntu-24.04`.
- `.github/workflows/cd-cloud.yml` uses `runs-on: ubuntu-24.04`.
- `.github/workflows/auto-merge-dependabot.yml` uses `runs-on: ubuntu-24.04`.
- `.github/workflows/cd-localcluster.yml` is self-hosted but has a weak fallback label: `localcluster` instead of `localcluster-books`.
- CI uses GitHub cloud npm caching through `actions/setup-node`.
- CI uploads migration artifacts without `retention-days`.
- CI uploads migration artifacts before Docker image build and push.
- CI does not prune old artifacts.
- Current deployment audit does not enforce no-hosted-runner, short retention, pruning, or self-hosted cleanup.
- The repo is public, so moving all jobs to self-hosted needs explicit external-fork protection.

Important live failure:

- Recent Dependabot PR CI run `27819201938` failed on the GitHub-hosted runner at `npm audit`.
- The runner migration should not hide that. After the infrastructure fix, rerun CI and fix any real package audit issue separately if it still fails.

## GitHub Facts That Shape The Design

Official GitHub docs checked on 2026-06-19:

- Self-hosted runners are free to use with GitHub Actions, but you maintain the machine.
- Standard GitHub-hosted runners are free and unlimited for public repositories, but the user wants this repo moved to self-hosted anyway.
- GitHub recommends using self-hosted runners only with private repositories because public fork PRs can run dangerous code on self-hosted machines.
- Dependency caches from self-hosted workflow runs are still stored on GitHub-owned cloud storage.
- Workflow artifacts consume GitHub storage until they expire or are deleted.

Sources:

- `https://docs.github.com/actions/hosting-your-own-runners`
- `https://docs.github.com/actions/hosting-your-own-runners/adding-self-hosted-runners`
- `https://docs.github.com/actions/using-jobs/choosing-the-runner-for-a-job`
- `https://docs.github.com/en/actions/concepts/workflows-and-actions/dependency-caching`
- `https://docs.github.com/actions/managing-workflow-runs/removing-workflow-artifacts`

## Design Decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| CI runner | `node-main-books` self-hosted runner | User explicitly allowed complete self-hosted fix, and the repo already has the correct runner. |
| Runner label fallback | `localcluster-books` | App-specific label prevents jobs from landing on another LocalCluster runner. |
| Public fork PRs | Skip before runner allocation | Public self-hosted runners are risky; job-level `if` guard avoids running fork code on node-main. |
| Dependabot PRs | Allow same-repo Dependabot PRs | Current Dependabot branches are same-repo branches and can use the self-hosted runner. |
| NPM cache | Remove GitHub cache usage | Self-hosted workflow caches still use GitHub cloud storage. |
| Migration artifact retention | `7` days | Matches ImprovedDb and keeps recent deployability without long storage retention. |
| Artifact keep count | newest `5` current-name artifacts | Matches ImprovedDb steady-state, about 5 * 60-70 MB. |
| Obsolete `ship` artifacts | delete all | Current release identity is `books`; `ship` artifacts cannot be used by current CD. |
| Current `books` artifacts | keep newest 5 initially | Preserves recent deploy targets until a new green CI run produces a fresh artifact. |
| Artifact pruning scope | exact artifact name only | Avoids broad deletion of SARIF or future useful artifacts. |
| Docker cleanup | targeted only | Node-main hosts real LocalCluster workloads; no broad `docker system prune --volumes`. |
| Cloud CD | migrate to self-hosted; deploy after CI if Cloud is intended live | Cloud environment/secrets exist. The runner migration can be verified statically, but the complete fix can run Cloud CD if live Cloud deployment is desired. |
| Audit | enforce the policy in code | The durable fix is not YAML alone; future regressions must fail CI. |

## ImprovedDb Files To Copy Or Adapt

Use these ImprovedDb files as direct reference points:

| ImprovedDb file | BlazorAutoApp action |
| --- | --- |
| `.github/workflows/ci.yml` | Copy structure, but adapt labels to `localcluster-books` and keep BlazorAutoApp-specific test/build steps. |
| `.github/workflows/auto-merge-dependabot.yml` | Copy self-hosted runner proof and `gh` availability check, adapt label fallback. |
| `.github/workflows/cd-localcluster.yml` | Copy runner proof and app-specific fallback pattern, adapt environment stays `localcluster`. |
| `.github/workflows/cd-cloud.yml` | Copy self-hosted runner target and wording improvements, adapt Cloud path names. |
| `Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh` | Copy almost directly. |
| `Deployment/Common/Scripts/prune-actions-artifacts.sh` | Copy directly. |
| `Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py` | Copy directly. |
| `Deployment/LocalCluster/Scripts/prune-docker-residue.sh` | Copy or create a smaller equivalent; prefer copying if compatible. |
| `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` | Port the runner, retention, pruning, upload-order, and cleanup checks. |
| `Deployment/LocalCluster/HowToDeployLocalCluster.md` | Port the self-hosted CI/CD and storage policy docs. |
| `Deployment/Cloud/HowToDeployCloud.md` | Port the self-hosted Cloud runner wording. |
| `Plans/GitHubActionsStorage.md` | Use as artifact cleanup/pruning precedent. |
| `Plans/NodeMainActionsRunnerMigration.md` | Use as runner migration precedent. |

Do not blindly copy references to `ImprovedDb`, `improveddb`, `localcluster-improveddb`, or `node-main-improveddb`. BlazorAutoApp must use:

- `books`
- `ghcr.io/grumlebob/books`
- `books-migrate-linux-x64`
- `localcluster-books`
- `node-main-books`

## Phase 0 - Preflight

- [ ] Run the local repo agent requirement:

```powershell
& '%USERPROFILE%\Documents\Programming\Stikky\turn-off.ps1'
```

- [ ] Confirm the worktree is clean and current:

```powershell
cd %USERPROFILE%\Documents\Programming\Csharp\BlazorAutoApp
git status --short --branch
git fetch origin
git pull --ff-only origin main
git status --short --branch
```

- [ ] Confirm `gh` auth:

```powershell
gh auth status
```

- [ ] Confirm runner and repo settings:

```powershell
gh repo view Grumlebob/BlazorAutoAppTemplate --json nameWithOwner,visibility,defaultBranchRef
gh variable list --repo Grumlebob/BlazorAutoAppTemplate
gh api repos/Grumlebob/BlazorAutoAppTemplate/actions/runners --paginate
gh api repos/Grumlebob/BlazorAutoAppTemplate/environments --paginate
```

- [ ] Confirm current artifact/cache totals and paste the numbers into this plan before cleanup:

```powershell
$repo = 'Grumlebob/BlazorAutoAppTemplate'
$artifacts = @()
$page = 1
while ($true) {
  $json = gh api "repos/$repo/actions/artifacts?per_page=100&page=$page" | ConvertFrom-Json
  if (-not $json.artifacts -or $json.artifacts.Count -eq 0) { break }
  $artifacts += $json.artifacts
  if ($json.artifacts.Count -lt 100) { break }
  $page++
}
$artifacts | Group-Object name | ForEach-Object {
  $sum = ($_.Group | Measure-Object -Property size_in_bytes -Sum).Sum
  [pscustomobject]@{ Name = $_.Name; Count = $_.Count; MB = [math]::Round($sum / 1MB, 1) }
} | Sort-Object MB -Descending | Format-Table -AutoSize

gh cache list --repo $repo --limit 100
```

- [ ] Stop if any workflow is currently running:

```powershell
gh run list --repo Grumlebob/BlazorAutoAppTemplate --limit 20
```

## Phase 1 - Immediate Remote Storage Cleanup

This phase can run before code changes because the current storage pressure is already known.

### Phase 1A - Delete Obsolete `ship` Migration Artifacts

Reason:

- Current `Deployment/Common/release.yml` uses `books-migrate`, not `ship-migrate`.
- Current CD expects `books-migrate-linux-x64`.
- `ship-migrate-linux-x64` artifacts are old content and cannot be used by the current deployment contract.

Dry-run:

```powershell
$repo = 'Grumlebob/BlazorAutoAppTemplate'
$name = 'ship-migrate-linux-x64'
$artifacts = @()
$page = 1
while ($true) {
  $json = gh api "repos/$repo/actions/artifacts?per_page=100&page=$page&name=$name" | ConvertFrom-Json
  if (-not $json.artifacts -or $json.artifacts.Count -eq 0) { break }
  $artifacts += $json.artifacts
  if ($json.artifacts.Count -lt 100) { break }
  $page++
}
$artifacts |
  Sort-Object created_at -Descending |
  Select-Object id,name,@{Name='MB';Expression={[math]::Round($_.size_in_bytes / 1MB, 1)}},created_at,expires_at |
  Format-Table -AutoSize
```

Delete after reviewing the dry-run output:

```powershell
foreach ($artifact in $artifacts) {
  gh api -X DELETE "repos/$repo/actions/artifacts/$($artifact.id)"
}
```

Expected recovery: about `4332 MB`.

### Phase 1B - Prune Current `books` Migration Artifacts

Keep newest 5 until a new green CI run exists.

```powershell
$repo = 'Grumlebob/BlazorAutoAppTemplate'
$name = 'books-migrate-linux-x64'
$keep = 5
$artifacts = @()
$page = 1
while ($true) {
  $json = gh api "repos/$repo/actions/artifacts?per_page=100&page=$page&name=$name" | ConvertFrom-Json
  if (-not $json.artifacts -or $json.artifacts.Count -eq 0) { break }
  $artifacts += $json.artifacts
  if ($json.artifacts.Count -lt 100) { break }
  $page++
}
$delete = $artifacts | Sort-Object created_at -Descending | Select-Object -Skip $keep
$delete |
  Select-Object id,name,@{Name='MB';Expression={[math]::Round($_.size_in_bytes / 1MB, 1)}},created_at,expires_at |
  Format-Table -AutoSize
```

Delete after reviewing:

```powershell
foreach ($artifact in $delete) {
  gh api -X DELETE "repos/$repo/actions/artifacts/$($artifact.id)"
}
```

Expected recovery: about `2460 MB`, leaving about `5 * 60 MB`.

### Phase 1C - Delete Caches

Reason:

- Caches are rebuildable.
- Current cache total is about `823 MB`.
- The code fix removes the npm cloud cache.
- CodeQL caches may come back if GitHub-managed CodeQL remains enabled, but they are smaller than migration artifacts.

List before delete:

```powershell
gh cache list --repo Grumlebob/BlazorAutoAppTemplate --limit 100
```

Delete:

```powershell
gh cache delete --all --succeed-on-no-caches --repo Grumlebob/BlazorAutoAppTemplate
```

### Phase 1D - Re-measure

```powershell
# Repeat the Phase 0 artifact/cache measurement.
```

Expected post-cleanup target before new CI:

- Artifacts: about `345 MB` if keeping 5 `books` artifacts plus tiny SARIF.
- Caches: about `0 MB`.
- Visible Actions storage: below `400 MB`.

## Phase 2 - CI Workflow Migration

Edit `.github/workflows/ci.yml`.

### Required CI Shape

- [ ] Add branch/job concurrency:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

- [ ] Keep top-level permissions read-only:

```yaml
permissions:
  contents: read
```

- [ ] Add same-repo PR guard before runner allocation:

```yaml
jobs:
  build-test-push:
    if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository
```

- [ ] Change `build-test-push` runner:

```yaml
runs-on: [self-hosted, linux, x64, "${{ vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}"]
```

- [ ] Scope GHCR push permission to the build job:

```yaml
permissions:
  contents: read
  packages: write
```

- [ ] Add early runner proof:

```yaml
- name: Verify node-main runner
  run: |
    echo "Runner name: ${RUNNER_NAME:-unknown}"
    echo "Host: $(hostname)"
    test "$(hostname)" = "node-main"
```

- [ ] Add prerequisite bootstrap after checkout:

```yaml
- name: Ensure self-hosted runner prerequisites
  run: bash Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh
```

- [ ] Add a disk guard. Use ImprovedDb's current check as the model.
- [ ] Add `Configure self-hosted tool paths` so .NET installs under `RUNNER_TEMP`.
- [ ] Replace `sudo apt-get install shellcheck` in the lint step with a plain `shellcheck` call.
- [ ] Add a Python virtualenv setup before Python package installs, using ImprovedDb's `Setup Python` pattern.
- [ ] Remove these `actions/setup-node` cache lines:

```yaml
cache: npm
cache-dependency-path: BlazorAutoApp.Client/package-lock.json
```

### CI Artifact Order

The final publish order must be:

1. Build and test.
2. Build EF migration bundle.
3. Build Docker image.
4. Docker verification if present.
5. Login to GHCR.
6. Push Docker image.
7. Upload migration artifact with `retention-days: 7`.
8. Run Docker residue cleanup.
9. Run separate pruning job.

Change migration artifact upload to happen after Docker image push:

```yaml
- name: Upload migration bundle
  if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
  uses: actions/upload-artifact@v7
  with:
    name: ${{ env.MIGRATION_ARTIFACT_NAME }}
    path: artifacts/migrations/${{ env.MIGRATION_BUNDLE_NAME }}
    retention-days: 7
```

### CI Docker Cleanup

Add either the ImprovedDb `prune-docker-residue.sh` script or a smaller safe equivalent.

Preferred: copy and adapt ImprovedDb's:

```text
%USERPROFILE%\Documents\Programming\Csharp\ImprovedDb\Deployment\LocalCluster\Scripts\prune-docker-residue.sh
```

Then add:

```yaml
- name: Clean self-hosted Docker build residue
  if: always()
  run: |
    if ! bash Deployment/LocalCluster/Scripts/prune-docker-residue.sh \
      --force \
      --remove-image "${APP_IMAGE:-}:${{ github.sha }}" \
      --min-free-mb 20480 \
      --container-until 24h \
      --dangling-image-until 168h \
      --localcluster-image-until 168h \
      --builder-until 48h \
      --network-until 24h; then
      echo "::warning::Docker residue cleanup failed; inspect runner disk before the next deployment."
    fi
```

Do not use:

```bash
docker system prune -af --volumes
```

### CI Prune Job

Add a second job:

```yaml
prune-migration-artifacts:
  needs: build-test-push
  if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
  runs-on: [self-hosted, linux, x64, "${{ vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}"]
  permissions:
    actions: write
    contents: read

  steps:
    - name: Checkout
      uses: actions/checkout@v6

    - name: Verify node-main runner
      run: |
        echo "Runner name: ${RUNNER_NAME:-unknown}"
        echo "Host: $(hostname)"
        test "$(hostname)" = "node-main"

    - name: Load release settings
      run: |
        echo "MIGRATION_ARTIFACT_NAME=$(bash Deployment/Common/Scripts/read-release-setting.sh migration_artifact_name)" >> "$GITHUB_ENV"

    - name: Prune old migration bundle artifacts
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        bash Deployment/Common/Scripts/prune-actions-artifacts.sh \
          --artifact-name "${MIGRATION_ARTIFACT_NAME}" \
          --keep 5
```

## Phase 3 - Add Shared Helper Scripts

Copy from ImprovedDb:

```powershell
Copy-Item `
  %USERPROFILE%\Documents\Programming\Csharp\ImprovedDb\Deployment\LocalCluster\Scripts\ensure-actions-runner-prereqs.sh `
  Deployment\LocalCluster\Scripts\ensure-actions-runner-prereqs.sh

Copy-Item `
  %USERPROFILE%\Documents\Programming\Csharp\ImprovedDb\Deployment\Common\Scripts\prune-actions-artifacts.sh `
  Deployment\Common\Scripts\prune-actions-artifacts.sh

Copy-Item `
  %USERPROFILE%\Documents\Programming\Csharp\ImprovedDb\Deployment\Common\Scripts\Component\lib\prune-actions-artifacts.py `
  Deployment\Common\Scripts\Component\lib\prune-actions-artifacts.py

Copy-Item `
  %USERPROFILE%\Documents\Programming\Csharp\ImprovedDb\Deployment\LocalCluster\Scripts\prune-docker-residue.sh `
  Deployment\LocalCluster\Scripts\prune-docker-residue.sh
```

After copying:

- [ ] Search copied files for `improveddb`, `ImprovedDb`, and `localcluster-improveddb`.
- [ ] Confirm scripts are generic or adapt to `books`.
- [ ] Run shell syntax checks.

## Phase 4 - Auto-Merge Workflow Migration

Edit `.github/workflows/auto-merge-dependabot.yml`.

- [ ] Change runner:

```yaml
runs-on: [self-hosted, linux, x64, "${{ vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}"]
```

- [ ] Add runner proof:

```yaml
- name: Verify node-main runner
  run: |
    echo "Runner name: ${RUNNER_NAME:-unknown}"
    echo "Host: $(hostname)"
    test "$(hostname)" = "node-main"
```

- [ ] Add `gh` check:

```yaml
- name: Verify GitHub CLI
  run: command -v gh
```

- [ ] Keep existing skip checks for:
  - semver major,
  - Dockerfiles,
  - compose files,
  - `Deployment/`,
  - `.github/workflows/`.

## Phase 5 - LocalCluster CD Migration

Edit `.github/workflows/cd-localcluster.yml`.

- [ ] Change runner fallback:

```yaml
runs-on: [self-hosted, linux, x64, "${{ vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}"]
```

- [ ] Add runner proof before checkout:

```yaml
- name: Verify node-main runner
  run: |
    echo "Runner name: ${RUNNER_NAME:-unknown}"
    echo "Host: $(hostname)"
    test "$(hostname)" = "node-main"
```

- [ ] Keep environment fallback as `localcluster`.
- [ ] Keep successful-CI gate.
- [ ] Keep artifact download by `run-id`.
- [ ] Keep migrations optional.
- [ ] Do not rebuild migration bundles in CD.

## Phase 6 - Cloud CD Migration

Edit `.github/workflows/cd-cloud.yml`.

- [ ] Change runner:

```yaml
runs-on: [self-hosted, linux, x64, "${{ vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books' }}"]
```

- [ ] Add runner proof before checkout.
- [ ] Keep `Determine runner SSH CIDR`, but update docs/comments from GitHub-hosted wording to Actions runner wording.
- [ ] Keep temporary firewall `clear` step under `if: always()`.
- [ ] Keep Cloud secrets in the `cloud-hetzner` environment.
- [ ] Prefer switching GHCR auth to `${{ github.actor }}` and `${{ secrets.GITHUB_TOKEN }}` only if tests prove it can read the package from this repo. Otherwise keep existing Cloud GHCR secrets.

Cloud CD can be dispatched after LocalCluster proof if the Cloud app is intended to remain live.

## Phase 7 - Deployment Audit Hardening

Edit `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py`.

Port these ImprovedDb audit checks:

- [ ] Every workflow `runs-on:` line must include `self-hosted`.
- [ ] Every workflow `runs-on:` line must not include:
  - `ubuntu-`
  - `ubuntu-latest`
  - `windows-`
  - `macos-`
- [ ] Every workflow with `runs-on` must include `localcluster-books`.
- [ ] Every workflow with `runs-on` must include `Verify node-main runner`.
- [ ] CI must include:
  - external fork PR guard,
  - `Ensure self-hosted runner prerequisites`,
  - `RUNNER_TEMP` tool paths,
  - `retention-days: 7`,
  - `prune-migration-artifacts`,
  - `needs: build-test-push`,
  - `actions: write` only for prune job,
  - `--keep 5`,
  - `Clean self-hosted Docker build residue`,
  - `bash Deployment/Common/Scripts/prune-actions-artifacts.sh`.
- [ ] CI artifact upload must happen after Docker image push.
- [ ] CD must still consume CI artifact by `run-id`.
- [ ] CD must not run `dotnet ef migrations bundle`.
- [ ] Audit must require the new helper scripts exist:
  - `Deployment/Common/Scripts/prune-actions-artifacts.sh`
  - `Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py`
  - `Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh`
  - `Deployment/LocalCluster/Scripts/prune-docker-residue.sh`

Run this after edits:

```powershell
python -m py_compile Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
```

## Phase 8 - Documentation Updates

Update these files precisely, without bloating them:

- `Deployment/LocalCluster/HowToDeployLocalCluster.md`
- `Deployment/Cloud/HowToDeployCloud.md`
- `Deployment/LocalCluster/Scripts/README.md` if it mentions runner policy or cleanup.
- `README.md` if it summarizes CI/CD ownership.
- `agent.md` only if it helps future agents avoid rediscovery.

Required doc facts:

- This repo now uses `node-main-books` for CI, auto-merge, LocalCluster CD, and Cloud CD.
- The workflow fallback label is `localcluster-books`.
- The repo is public, so external fork PRs must not run on the self-hosted runner.
- Self-hosted runners are free, but artifacts and caches still consume GitHub storage.
- NPM GitHub cache is intentionally disabled.
- Migration artifacts use `retention-days: 7`.
- CI prunes current migration artifacts to newest 5.
- Obsolete `ship-migrate-linux-x64` artifacts were deleted because current release uses `books-migrate-linux-x64`.
- Persistent runner cleanup is required because node-main is not an ephemeral GitHub-hosted VM.

Suggested one-line `agent.md` addition:

```text
- For GitHub Actions/deployment fixes, compare this repo against the hardened ImprovedDb deployment files first, then adapt names to books/localcluster-books instead of copying blindly.
```

## Phase 9 - Local Validation

Run from `%USERPROFILE%\Documents\Programming\Csharp\BlazorAutoApp`.

```powershell
bash -n Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh
bash -n Deployment/Common/Scripts/prune-actions-artifacts.sh
bash -n Deployment/LocalCluster/Scripts/prune-docker-residue.sh
python -m py_compile `
  Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py `
  Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:1.7.12 `
  .github/workflows/ci.yml `
  .github/workflows/auto-merge-dependabot.yml `
  .github/workflows/cd-localcluster.yml `
  .github/workflows/cd-cloud.yml
rg -n "runs-on: ubuntu-24.04|runs-on: ubuntu-latest|runs-on: windows-|runs-on: macos-" .github/workflows
rg -n "cache: npm|cache-dependency-path" .github/workflows
```

Expected:

- `rg` hosted-runner search returns no matches.
- `rg` npm cache search returns no matches.
- Audit passes.
- Actionlint passes.

Run focused app checks only if needed before pushing. Do not run `dotnet build` and `dotnet test` in parallel.

## Phase 10 - Commit And Push

Use path-limited staging.

Expected files:

- `.github/workflows/ci.yml`
- `.github/workflows/auto-merge-dependabot.yml`
- `.github/workflows/cd-localcluster.yml`
- `.github/workflows/cd-cloud.yml`
- `Deployment/Common/Scripts/prune-actions-artifacts.sh`
- `Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py`
- `Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh`
- `Deployment/LocalCluster/Scripts/prune-docker-residue.sh`
- `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py`
- `Deployment/LocalCluster/HowToDeployLocalCluster.md`
- `Deployment/Cloud/HowToDeployCloud.md`
- optional docs listed in Phase 8
- `Plans/GitHubActionsFreeSelfHostedAndStorage.md`

Commands:

```powershell
git status --short
git diff --stat
git add <only intended files>
git diff --cached --stat
git diff --cached --name-only
git diff --cached
git commit -m "Run template CI on self-hosted runner"
git push origin main
```

## Phase 11 - Watch CI

Find and watch the run:

```powershell
$sha = git rev-parse HEAD
$ciRun = $null
for ($i = 0; $i -lt 30; $i++) {
  $runs = gh run list --repo Grumlebob/BlazorAutoAppTemplate --workflow CI --branch main --limit 10 --json databaseId,headSha,status,conclusion,url | ConvertFrom-Json
  $ciRun = $runs | Where-Object { $_.headSha -eq $sha } | Select-Object -First 1
  if ($ciRun) { break }
  Start-Sleep -Seconds 10
}
if (-not $ciRun) { throw "No CI run found for $sha" }
gh run watch --repo Grumlebob/BlazorAutoAppTemplate $ciRun.databaseId --exit-status
```

If queued for more than 5 minutes:

```powershell
gh api repos/Grumlebob/BlazorAutoAppTemplate/actions/runners --paginate
ssh -i ~/.ssh/currentpc_node_main jacob@192.168.0.128 "systemctl list-units 'actions.runner.Grumlebob-BlazorAutoAppTemplate*' --no-pager"
```

If failed:

```powershell
gh run view --repo Grumlebob/BlazorAutoAppTemplate $ciRun.databaseId --log-failed
```

Fix, commit, push, and watch again until green.

After green:

```powershell
gh run view --repo Grumlebob/BlazorAutoAppTemplate $ciRun.databaseId --json jobs | ConvertFrom-Json | ConvertTo-Json -Depth 20
gh api "repos/Grumlebob/BlazorAutoAppTemplate/actions/runs/$($ciRun.databaseId)/artifacts" | ConvertFrom-Json
```

Expected:

- CI `build-test-push` ran on `node-main-books`.
- CI uploaded one `books-migrate-linux-x64` artifact.
- Artifact expiry is about 7 days after upload.
- `prune-migration-artifacts` ran on `node-main-books`.
- Current artifact count is newest 5 `books-migrate-linux-x64` plus tiny SARIF artifacts.

## Phase 12 - Deploy LocalCluster

Run LocalCluster CD after green CI.

If the change only touches workflow/docs/scripts, `run_migrations=false` is acceptable. If CI produced a new migration artifact and you want to prove artifact download, use `run_migrations=true`.

Recommended for this fix: `run_migrations=true`, because it proves the CI artifact contract.

```powershell
$dispatchStarted = (Get-Date).ToUniversalTime()
gh workflow run "CD - Deploy LocalCluster" --repo Grumlebob/BlazorAutoAppTemplate --ref main -f run_migrations=true
$sha = git rev-parse HEAD
$cdRun = $null
for ($i = 0; $i -lt 30; $i++) {
  $runs = gh run list --repo Grumlebob/BlazorAutoAppTemplate --workflow "CD - Deploy LocalCluster" --branch main --limit 20 --json databaseId,headSha,status,conclusion,url,createdAt | ConvertFrom-Json
  $cdRun = $runs |
    Where-Object { $_.headSha -eq $sha -and ([datetime]$_.createdAt).ToUniversalTime() -ge $dispatchStarted.AddMinutes(-1) } |
    Sort-Object createdAt -Descending |
    Select-Object -First 1
  if ($cdRun) { break }
  Start-Sleep -Seconds 10
}
if (-not $cdRun) { throw "No LocalCluster CD run found for $sha" }
gh run watch --repo Grumlebob/BlazorAutoAppTemplate $cdRun.databaseId --exit-status
```

Expected:

- CD ran on `node-main-books`.
- CD selected successful CI for the same SHA.
- CD downloaded `books-migrate-linux-x64`.
- Acceptance check passed.

## Phase 13 - Deploy Cloud

Cloud environment and secrets exist. Run only after LocalCluster is green.

Because this touches live Cloud infrastructure, first confirm Cloud is still supposed to be live. If yes:

```powershell
$dispatchStarted = (Get-Date).ToUniversalTime()
gh workflow run "CD - Cloud" --repo Grumlebob/BlazorAutoAppTemplate --ref main -f run_migrations=true
$sha = git rev-parse HEAD
$cloudRun = $null
for ($i = 0; $i -lt 30; $i++) {
  $runs = gh run list --repo Grumlebob/BlazorAutoAppTemplate --workflow "CD - Cloud" --branch main --limit 20 --json databaseId,headSha,status,conclusion,url,createdAt | ConvertFrom-Json
  $cloudRun = $runs |
    Where-Object { $_.headSha -eq $sha -and ([datetime]$_.createdAt).ToUniversalTime() -ge $dispatchStarted.AddMinutes(-1) } |
    Sort-Object createdAt -Descending |
    Select-Object -First 1
  if ($cloudRun) { break }
  Start-Sleep -Seconds 10
}
if (-not $cloudRun) { throw "No Cloud CD run found for $sha" }
gh run watch --repo Grumlebob/BlazorAutoAppTemplate $cloudRun.databaseId --exit-status
```

Expected:

- Cloud CD ran on `node-main-books`.
- It opened the temporary SSH firewall for node-main's public IPv4.
- It cleared the temporary SSH firewall in the `always()` cleanup step.
- It deployed the same SHA as green CI.
- Acceptance check passed.

If Cloud CD fails because of a real app/cloud issue unrelated to runner migration, record it in this plan and do not hide it by reverting runner changes.

## Phase 14 - Final Storage Verification

Re-measure:

```powershell
$repo = 'Grumlebob/BlazorAutoAppTemplate'
$artifacts = @()
$page = 1
while ($true) {
  $json = gh api "repos/$repo/actions/artifacts?per_page=100&page=$page" | ConvertFrom-Json
  if (-not $json.artifacts -or $json.artifacts.Count -eq 0) { break }
  $artifacts += $json.artifacts
  if ($json.artifacts.Count -lt 100) { break }
  $page++
}
$artifactTotal = ($artifacts | Measure-Object -Property size_in_bytes -Sum).Sum

$caches = @()
$page = 1
while ($true) {
  $json = gh api "repos/$repo/actions/caches?per_page=100&page=$page" | ConvertFrom-Json
  if (-not $json.actions_caches -or $json.actions_caches.Count -eq 0) { break }
  $caches += $json.actions_caches
  if ($json.actions_caches.Count -lt 100) { break }
  $page++
}
$cacheTotal = ($caches | Measure-Object -Property size_in_bytes -Sum).Sum

[pscustomobject]@{
  ArtifactCount = $artifacts.Count
  ArtifactMB = [math]::Round($artifactTotal / 1MB, 1)
  CacheCount = $caches.Count
  CacheMB = [math]::Round($cacheTotal / 1MB, 1)
  TotalMB = [math]::Round(($artifactTotal + $cacheTotal) / 1MB, 1)
}
```

Target:

- Storage below `500 MB` for this repo after cleanup and one green CI run.
- No `ship-migrate-linux-x64` artifacts.
- No npm cloud caches.
- No more than 5 `books-migrate-linux-x64` artifacts.

## Phase 15 - Package Storage Check

The current token may need extra scopes for package visibility. If GitHub billing still reports storage pressure after artifact/cache cleanup, check GHCR packages:

```powershell
gh auth refresh -h github.com -s read:packages -s delete:packages
gh api "/users/Grumlebob/packages?package_type=container"
```

Look specifically for old `ship` packages or excessive untagged `books` package versions.

Do not delete GHCR package versions until:

- the current deployed image tag is identified,
- recent rollback tags are identified,
- old `ship` packages are confirmed obsolete,
- the deletion target is printed before delete.

## Failure Playbook

### External Fork PR Wants CI

- It should be skipped by the job-level guard.
- Do not remove the guard while the repo is public.
- If public contributor CI is needed, use GitHub-hosted runners for that narrow untrusted workflow or make a deliberate separate design.

### CI Fails On `npm audit`

- This already happened on run `27819201938`.
- Treat it as a real dependency issue, not a runner migration issue.
- Fix package versions or audit policy in a separate commit if needed.

### CI Queues Forever

- Check `node-main-books` runner status with `gh api`.
- Check the systemd service on node-main.
- Restart only the BlazorAutoAppTemplate runner service, not ImprovedDb's runner.

### CI Fails Because Tools Are Missing

- Fix `ensure-actions-runner-prereqs.sh`.
- It should install/verify `python3-venv`, `shellcheck`, `pwsh`, and Docker access.
- Do not rely on persistent manual installs without committing the prerequisite script.

### Docker Cleanup Fails

- Inspect runner disk:

```powershell
ssh -i ~/.ssh/currentpc_node_main jacob@192.168.0.128 "df -h / /opt && docker system df"
```

- Remove only named CI images/containers/networks.
- Do not prune volumes.

### CD Cannot Find CI

- Confirm CI passed for the exact SHA selected by CD.
- Confirm workflow name is still `CI`.
- Do not bypass the successful-CI gate.

### CD Cannot Download Artifact

- Confirm CI uploaded `books-migrate-linux-x64`.
- Confirm pruning kept newest 5 current-name artifacts.
- Rerun CI for current `main` if needed.

### Cloud CD Leaves Firewall Open

- The `Remove temporary SSH from cloud-main` step must remain `if: always()`.
- If a run is cancelled or fails before cleanup, manually run:

```powershell
gh workflow run "CD - Cloud" --repo Grumlebob/BlazorAutoAppTemplate --ref main -f run_migrations=false
```

or run the firewall clear script from a trusted machine with the Cloud env available.

## Acceptance Criteria

- [ ] `ship-migrate-linux-x64` artifacts are deleted.
- [ ] `books-migrate-linux-x64` artifacts are pruned to newest 5.
- [ ] Caches are deleted and npm GitHub cache usage is removed.
- [ ] `.github/workflows` contains no `ubuntu-24.04`, `ubuntu-latest`, `windows-*`, or `macos-*` runner labels.
- [ ] CI, auto-merge, LocalCluster CD, and Cloud CD target `localcluster-books`.
- [ ] Public fork PRs are skipped before self-hosted runner allocation.
- [ ] CI uploads migration artifacts only after Docker image push.
- [ ] CI upload has `retention-days: 7`.
- [ ] CI has a dedicated prune job with `actions: write` and `--keep 5`.
- [ ] Deployment audit fails if hosted runners, npm cloud cache, missing retention, missing prune, or wrong runner labels return.
- [ ] CI passes on `node-main-books`.
- [ ] LocalCluster CD passes on `node-main-books`.
- [ ] Cloud CD is either passed on `node-main-books` or explicitly recorded as not run because live Cloud deployment was intentionally skipped.
- [ ] Final visible Actions artifact/cache storage for this repo is below `500 MB`.
- [ ] `%USERPROFILE%\Documents\Programming\Stikky\turn-on.ps1` is run before final response in Codex turns.

## Execution Status

Fill this in during execution:

```text
## Execution Status - YYYY-MM-DD

- [ ] Pre-cleanup storage:
- [ ] Deleted obsolete ship artifacts:
- [ ] Pruned books artifacts:
- [ ] Deleted caches:
- [ ] Post-cleanup storage:
- [ ] Commit:
- [ ] CI run:
- [ ] LocalCluster CD run:
- [ ] Cloud CD run or reason skipped:
- [ ] Final storage:
- [ ] Runner proof:
```
