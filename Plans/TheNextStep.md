# The Next Step Plan

Status: first expansion executed; later backlog recorded.

Last updated: 2026-05-30.

Important repo note: `/Plans/` is ignored by `.gitignore`. This plan is
intentionally stored here because requested, but it will not be committed unless
moved to `docs/` or the ignore rule changes.

## Goal

Use the new `BlazorAutoApp.Simulation` runner to expand the project plan from
real evidence across all three environments:

```text
local               https://localhost:7186
localcluster-public https://books.jacobgrum.com
cloud-public        https://bookscloud.jacobgrum.com
```

The first expansion should be slow and evidence-driven:

- run comparable simulations against local, LocalCluster, and Cloud.
- collect the generated `summary.json`, `summary.md`, and synthetic ledgers.
- compare latency, status codes, rate limits, auth, writes, browser sampler, and cleanup.
- correlate with CI/CD and observability where possible.
- turn findings into concrete repo changes, documentation updates, and a later roadmap.

This plan does not start with new architecture work. It starts by making the
simulation results trustworthy enough that later expansion is based on measured
behavior rather than guesses.

## Current Baseline Evidence

Latest verified acceptance from `Plans/ImprovedSimulation.md`:

| Environment | Latest key report | Coverage | Result |
| --- | --- | --- | --- |
| local | `20260530-212438-local-smoke` | auth, API writes, browser sampler, cleanup | passed, leftovers `0` |
| local | `20260530-212537-local-smoke` | cleanup-only | passed, leftovers `0` |
| LocalCluster | `20260530-211922-localcluster-public-smoke` | auth, API writes, browser sampler, cleanup | passed, leftovers `0` |
| LocalCluster | `20260530-212017-localcluster-public-smoke` | cleanup-only | passed, leftovers `0` |
| Cloud | `20260530-212050-cloud-public-smoke` | auth, API writes, browser sampler, cleanup | passed, leftovers `0` |
| Cloud | `20260530-212143-cloud-public-smoke` | cleanup-only | passed, leftovers `0` |

Observed baseline:

- no failed simulation thresholds.
- no unexpected `429` responses.
- no `5xx` responses in the accepted runs.
- deployed browser sampler works on both public environments.
- synthetic books are cleaned up on local, LocalCluster, and Cloud.
- Cloud authenticated browser p95 was lower than LocalCluster in the latest run, but the sample size is too small to treat as a performance conclusion.
- local p95 is around 2 seconds in the latest run, likely influenced by local dev server behavior; this should be measured again before treating it as a defect.

Latest GitHub state checked from CurrentPC:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" auth status
& "C:\Program Files\GitHub CLI\gh.exe" run list --limit 10 --json databaseId,displayTitle,workflowName,status,conclusion,headSha,createdAt,url
```

GH CLI is authenticated as `Grumlebob`, but `gh` is not on this PowerShell
PATH. Use the full executable path above unless PATH is fixed.

Latest remote `main` state observed:

```text
branch: main
head: bdf265525fff2443f7252ddba2b15568c23eed2d
latest CI: success
latest LocalCluster CD observed in run list: success for an earlier deployed SHA
latest Cloud CD observed in run list: success for an earlier deployed SHA
```

Before drawing deployment conclusions, always compare the deployed app version
reported by telemetry/health/observability against the commit being tested.

## Scope

In scope for this plan:

- run simulator evidence collection across all three targets.
- inspect generated reports.
- inspect latest CI/CD state with GH CLI.
- decide what should become documentation, tests, scripts, dashboards, or future backlog.
- keep simulation outside production deployment.
- keep all synthetic writes behind explicit gates.

Out of scope for this first expansion:

- adding high-volume load testing.
- adding paid third-party test infrastructure.
- adding more cloud nodes.
- deploying the simulator as a service.
- making a permanent background traffic generator.
- changing rate limits before evidence shows a real problem.

## Safety Rules

- Never run deployed write traffic without `-AllowDeployed -AllowWrite`.
- Never use `burst` against `localcluster-public` or `cloud-public`.
- Never put simulator passwords in command history.
- Use disposable simulator users for deployed registration tests.
- Cleanup must report `leftovers=0` after every write/browser pass.
- If cleanup leaves leftovers, stop and run cleanup-only before continuing.
- Reports under `artifacts/simulation/` are local evidence and must not be committed.
- Simulation must remain excluded from app Docker images and CD workflows.

## Phase 0 - Prepare The Evidence Pass

Status: completed.

Purpose: make the environment state explicit before collecting new simulation
data.

Checklist:

- [x] Confirm current branch and commit:

```powershell
git branch --show-current
git rev-parse HEAD
```

- [x] Check for unrelated dirty worktree changes and avoid reverting them:

```powershell
git status --short
```

- [x] Confirm GH CLI access using the full installed path:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" auth status
```

- [x] Capture latest CI/CD status:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run list --limit 20 --json databaseId,displayTitle,workflowName,status,conclusion,headSha,createdAt,url
```

- [x] Confirm local app is running before local simulation:

```powershell
Invoke-WebRequest -Uri "https://localhost:7186/health/ready" -SkipCertificateCheck -TimeoutSec 10
```

- [x] If local app is not running, start it:

```powershell
.\RunLocal.ps1 -NoBrowser -Observability
```

- [x] Confirm public deployed health endpoints:

```powershell
Invoke-WebRequest -Uri "https://books.jacobgrum.com/health/ready" -TimeoutSec 20
Invoke-WebRequest -Uri "https://bookscloud.jacobgrum.com/health/ready" -TimeoutSec 20
```

- [x] Confirm Playwright browser is installed:

```powershell
.\RunSimulation.ps1 -InstallBrowsers
```

Exit criteria:

- Current commit, local state, and latest GH runs are recorded.
- Local and both deployed targets are reachable.
- Browser sampler prerequisites are installed.

Done notes:

- Current branch: `main`.
- Current commit: `fde1733b9abe024e32dc59a7092cc095e6a63854`.
- GH CLI works through `C:\Program Files\GitHub CLI\gh.exe`.
- Latest CI for `fde1733b9abe024e32dc59a7092cc095e6a63854` was `in_progress` when the evidence pass started: run `26695648541`.
- Latest observed LocalCluster and Cloud CD runs were successful but for older deployed SHAs, so any public environment comparison must treat deployed-version alignment as a separate check.
- `https://localhost:7186/health/ready` returned `200 Healthy`.
- `https://books.jacobgrum.com/health/ready` returned `200 Healthy`.
- `https://bookscloud.jacobgrum.com/health/ready` returned `200 Healthy`.
- `.\RunSimulation.ps1 -InstallBrowsers` passed.

## Phase 1 - Run A Comparable Three-Environment Matrix

Status: completed.

Purpose: collect a comparable smoke matrix before deciding what to improve.

### Local

Run local read-only, auth, browser write, and cleanup:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke -Duration 60s
.\RunSimulation.ps1 -Target local -AuthCheck
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -Cleanup -BrowserSampler -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
```

Expected:

- `failedThresholds=false`.
- `unexpected 429: 0`.
- no `5xx`.
- browser sampler `1/1` succeeded.
- cleanup `ok, leftovers=0`.

### LocalCluster

Use a disposable account or a known simulator account. Password must be passed
through environment, not command history.

```powershell
$env:SIMULATION_AUTH_EMAIL = "localcluster-sim-<date>@example.com"
$env:SIMULATION_AUTH_PASSWORD = "<secret from secure local source>"

.\RunSimulation.ps1 -Target localcluster-public -Profile smoke -AllowDeployed -Duration 60s
.\RunSimulation.ps1 -Target localcluster-public -AuthCheck -RegisterSyntheticUser -AllowDeployed -AllowWrite
.\RunSimulation.ps1 -Target localcluster-public -AuthCheck -AllowDeployed
.\RunSimulation.ps1 -Target localcluster-public -Profile smoke -Writes -Cleanup -BrowserSampler -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target localcluster-public -CleanupOnly -AllowDeployed -AllowWrite

Remove-Item Env:SIMULATION_AUTH_EMAIL -ErrorAction SilentlyContinue
Remove-Item Env:SIMULATION_AUTH_PASSWORD -ErrorAction SilentlyContinue
```

Expected:

- registration succeeds for new account, or login succeeds for existing account.
- authenticated API check succeeds.
- API write smoke succeeds.
- browser sampler succeeds.
- cleanup `ok, leftovers=0`.

### Cloud

Use a separate disposable account from LocalCluster. The two environments have
separate databases by design.

```powershell
$env:SIMULATION_AUTH_EMAIL = "cloud-sim-<date>@example.com"
$env:SIMULATION_AUTH_PASSWORD = "<secret from secure local source>"

.\RunSimulation.ps1 -Target cloud-public -Profile smoke -AllowDeployed -Duration 60s
.\RunSimulation.ps1 -Target cloud-public -AuthCheck -RegisterSyntheticUser -AllowDeployed -AllowWrite
.\RunSimulation.ps1 -Target cloud-public -AuthCheck -AllowDeployed
.\RunSimulation.ps1 -Target cloud-public -Profile smoke -Writes -Cleanup -BrowserSampler -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target cloud-public -CleanupOnly -AllowDeployed -AllowWrite

Remove-Item Env:SIMULATION_AUTH_EMAIL -ErrorAction SilentlyContinue
Remove-Item Env:SIMULATION_AUTH_PASSWORD -ErrorAction SilentlyContinue
```

Expected:

- same as LocalCluster.
- no temporary Cloud SSH/firewall changes are needed for public simulation.
- if Cloud was destroyed, recreate and deploy it before this phase.

Exit criteria:

- Each target has fresh reports under `artifacts/simulation/`.
- Each target has at least one read-only report and one authenticated browser/write/cleanup report.
- Cleanup-only passes after writes on all targets.

Done notes:

- Local read-only passed: `20260530-214512-local-smoke`.
- Local auth passed: `20260530-214617-local-smoke`.
- Local browser write/cleanup passed: `20260530-214626-local-smoke`.
- Local cleanup-only passed: `20260530-214725-local-smoke`.
- LocalCluster read-only passed: `20260530-214748-localcluster-public-smoke`.
- LocalCluster first registration attempt with a long disposable email timed out before writes. No synthetic data was created. This is recorded as a diagnostics improvement, not as an environment failure, because the same target passed with a shorter disposable email immediately afterward.
- LocalCluster registration passed: `20260530-214956-localcluster-public-smoke`.
- LocalCluster login passed: `20260530-214959-localcluster-public-smoke`.
- LocalCluster browser write/cleanup passed: `20260530-215002-localcluster-public-smoke`.
- LocalCluster cleanup-only passed: `20260530-215056-localcluster-public-smoke`.
- Cloud read-only passed: `20260530-215113-cloud-public-smoke`.
- Cloud registration passed: `20260530-215215-cloud-public-smoke`.
- Cloud login passed: `20260530-215219-cloud-public-smoke`.
- Cloud browser write/cleanup passed: `20260530-215221-cloud-public-smoke`.
- Cloud cleanup-only passed: `20260530-215315-cloud-public-smoke`.

## Phase 2 - Parse And Compare Reports

Status: completed.

Purpose: turn simulation output into a measured comparison table.

Collect the latest report directories:

```powershell
Get-ChildItem .\artifacts\simulation -Directory |
  Where-Object Name -match '^\d{8}-\d{6}-(local|localcluster-public|cloud-public)-' |
  Sort-Object Name -Descending |
  Select-Object -First 30 Name
```

For each environment, record:

- report directory.
- target.
- profile.
- start/end timestamp.
- request count.
- p50/p95/p99 latency.
- status code map.
- unexpected `429`.
- `5xx`.
- `failedThresholds`.
- auth mode and `authenticatedApiCheckSucceeded`.
- writes created/updated/deleted.
- browser sampler journeys started/succeeded/failed.
- cleanup deleted count and leftovers.
- error list.

Manual inspection command:

```powershell
Get-Content .\artifacts\simulation\<report>\summary.md
Get-Content .\artifacts\simulation\<report>\summary.json -Raw | ConvertFrom-Json
```

Recommended comparison dimensions:

| Dimension | Local | LocalCluster | Cloud | Question |
| --- | --- | --- | --- | --- |
| p95 read-only | pending | pending | pending | Is public latency reasonable compared with local? |
| p95 authenticated write | pending | pending | pending | Are database/write paths slower on one environment? |
| browser sampler duration | pending | pending | pending | Does UI interactivity differ materially? |
| unexpected 429 | pending | pending | pending | Are simulator budgets safe? |
| 5xx | pending | pending | pending | Is any environment unstable? |
| cleanup leftovers | pending | pending | pending | Is synthetic data hygiene reliable? |
| auth bootstrap duration | pending | pending | pending | Is login/register slow or flaky? |

Exit criteria:

- A measured comparison table exists in this plan or in a follow-up report.
- Any difference is classified as expected, suspicious, or actionable.
- No conclusion is based on a single request if the sample size is too small.

Measured comparison:

| Report | Target | Requests | Status | P95Ms | Unexpected429 | Failed | Auth | AuthApi | Writes | Cleanup | Browser |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20260530-214512-local-smoke` | local | 60 | `200=56, 404_expected=4` | 5.5 | 0 | false | disabled |  | false | not needed |  |
| `20260530-214617-local-smoke` | local | 1 | `200=1` | 2036.0 | 0 | false | browser-login | true | false | not needed |  |
| `20260530-214626-local-smoke` | local | 13 | `200=10, 201=1, 204=2` | 2051.0 | 0 | false | browser-login | true | true | ok, leftovers=0 | 1/1 |
| `20260530-214725-local-smoke` | local | 3 | `200=3` | 2039.8 | 0 | false | browser-login | true | true | ok, leftovers=0 |  |
| `20260530-214748-localcluster-public-smoke` | localcluster-public | 60 | `200=58, 404_expected=2` | 289.3 | 0 | false | disabled |  | false | not needed |  |
| `20260530-214956-localcluster-public-smoke` | localcluster-public | 1 | `200=1` | 71.7 | 0 | false | browser-register | true | false | not needed |  |
| `20260530-214959-localcluster-public-smoke` | localcluster-public | 1 | `200=1` | 78.8 | 0 | false | browser-login | true | false | not needed |  |
| `20260530-215002-localcluster-public-smoke` | localcluster-public | 13 | `200=10, 201=1, 204=2` | 308.5 | 0 | false | browser-login | true | true | ok, leftovers=0 | 1/1 |
| `20260530-215056-localcluster-public-smoke` | localcluster-public | 3 | `200=3` | 76.4 | 0 | false | browser-login | true | true | ok, leftovers=0 |  |
| `20260530-215113-cloud-public-smoke` | cloud-public | 60 | `200=58, 404_expected=2` | 87.3 | 0 | false | disabled |  | false | not needed |  |
| `20260530-215215-cloud-public-smoke` | cloud-public | 1 | `200=1` | 77.7 | 0 | false | browser-register | true | false | not needed |  |
| `20260530-215219-cloud-public-smoke` | cloud-public | 1 | `200=1` | 83.2 | 0 | false | browser-login | true | false | not needed |  |
| `20260530-215221-cloud-public-smoke` | cloud-public | 13 | `200=10, 201=1, 204=2` | 75.9 | 0 | false | browser-login | true | true | ok, leftovers=0 | 1/1 |
| `20260530-215315-cloud-public-smoke` | cloud-public | 3 | `200=3` | 81.7 | 0 | false | browser-login | true | true | ok, leftovers=0 |  |

Classification:

- Expected: local auth/write/cleanup p95 is around 2 seconds because those runs include browser login and the local Docker/dev path. Local read-only p95 is low at 5.5 ms, so this is not evidence of local API slowness.
- Expected: LocalCluster read-only p95 is higher than Cloud in this single pass; sample size is too small to make a performance claim.
- Actionable: the first LocalCluster registration timeout did not leave a useful auth failure artifact. Improve simulator auth diagnostics for unexpected Playwright exceptions.
- Actionable: manual parsing was repetitive and culture-sensitive; add a report analyzer that uses invariant number formatting.
- Good baseline: all accepted reports have `failedThresholds=false`, unexpected `429=0`, no `5xx`, and cleanup `leftovers=0`.

## Phase 3 - Correlate With GitHub CI/CD

Status: completed.

Purpose: know exactly which code was tested and whether deployed systems match
the repo state.

Use GH CLI:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run list --workflow CI --limit 10 --json databaseId,headSha,status,conclusion,createdAt,url
& "C:\Program Files\GitHub CLI\gh.exe" run list --workflow "CD - Deploy LocalCluster" --limit 10 --json databaseId,headSha,status,conclusion,createdAt,url
& "C:\Program Files\GitHub CLI\gh.exe" run list --workflow "CD - Cloud" --limit 10 --json databaseId,headSha,status,conclusion,createdAt,url
```

For the tested commit, record:

- latest CI run id, SHA, conclusion, URL.
- latest LocalCluster CD run id, SHA, conclusion, URL.
- latest Cloud CD run id, SHA, conclusion, URL.
- whether LocalCluster and Cloud are on the same SHA.
- whether simulation results were collected before or after deployment.

If a deployment run is missing or old:

- do not treat public simulation differences as app-regression evidence until
  the deployed SHA is known.
- use `gh run view <run-id> --log-failed` if a workflow failed.
- trigger CD only after CI succeeds and the user asks to deploy, unless the
  current task explicitly includes deployment.

Exit criteria:

- Every simulation result is tied to a commit/deployment status.
- Stale deploys are identified before performance or reliability conclusions.

Done notes:

- Current local commit during the evidence pass: `fde1733b9abe024e32dc59a7092cc095e6a63854`.
- CI for `fde1733b9abe024e32dc59a7092cc095e6a63854` succeeded: run `26695648541`, display title `simulation`.
- Latest LocalCluster CD was successful for older SHA `408f35ef50f6042fa32d3f9313275df434ab9b66`: run `26685195235`.
- Latest Cloud CD was successful for older SHA `408f35ef50f6042fa32d3f9313275df434ab9b66`: run `26685195237`.
- Therefore, public simulation results prove current reachable environment health, but they do not prove that `fde1733b9abe024e32dc59a7092cc095e6a63854` is deployed.

## Phase 4 - Decide First Expansion Items

Status: completed.

Purpose: convert report findings into concrete next work.

Use this decision table:

| Finding | Action |
| --- | --- |
| all three targets pass and metrics are boring | document baseline and add a recurring runbook |
| local is slow but deployed is fast | inspect local dev server, HTTPS, DB container, and observability overhead |
| one deployed target is slower | compare node topology, app logs, DB logs, Grafana dashboards, and deployment SHA |
| unexpected `429` appears | lower simulator budgets first; only change app rate limits after confirming real user need |
| any `5xx` appears | inspect logs/traces before continuing with more simulation |
| auth bootstrap flakiness | add diagnostics screenshots, HTML capture, and better error categories |
| browser sampler flakiness | inspect UI hydration/interactivity markers and add targeted E2E coverage |
| cleanup leftovers | stop expansion, fix cleanup safety before any more write simulation |
| dashboards do not show traffic clearly | improve dashboard labels, target/environment variables, and exemplar links |

Candidate first expansion changes:

- add `RunSimulationMatrix.ps1` to run the safe three-target matrix with strict exit-code handling.
- add `AnalyzeSimulationReports.ps1` to summarize latest reports into a compact Markdown table.
- add a `docs/SimulationEvidence.md` generated-style report, if we want a durable checked-in template but not raw artifacts.
- add a docs section showing exactly how to run local, LocalCluster, and Cloud simulations safely.
- add a GH workflow helper script that reports latest CI/CD state for the tested SHA.
- add simulator report fields for app version and environment when the app exposes them reliably.

Do not implement all candidates automatically. Pick the smallest set justified
by the evidence.

Exit criteria:

- First expansion backlog is ranked by value and risk.
- Each item has a concrete file target and verification command.

Decision:

1. Implement `RunSimulationMatrix.ps1`.
   - Value: removes repetitive operator commands and prevents missed `$LASTEXITCODE` checks.
   - Risk: deployed writes must stay gated.
   - Verification: `pwsh -NoProfile -File .\RunSimulationMatrix.ps1 -Help` and a short local matrix run.
2. Implement `AnalyzeSimulationReports.ps1`.
   - Value: produces a consistent Markdown comparison table without ad hoc parsing or locale-specific decimal formatting.
   - Risk: low; local artifact parsing only.
   - Verification: `pwsh -NoProfile -File .\AnalyzeSimulationReports.ps1 -Latest 5`.
3. Update docs.
   - Value: makes the new workflow discoverable.
   - Risk: low.
   - Verification: manual doc review and repo quality gates.
4. Fix auth exception diagnostics.
   - Value: the LocalCluster timeout should have produced a screenshot or better diagnostic.
   - Risk: moderate because it touches auth bootstrap behavior.
   - Result: added best-effort catch-time screenshots around unexpected Playwright exceptions in `BrowserAuthBootstrap`.

## Phase 5 - Implement The Smallest Useful Automation

Status: completed.

Purpose: remove repetitive operator work only after the manual matrix proves
what should be automated.

Preferred first automation:

```text
RunSimulationMatrix.ps1
```

Expected behavior:

- supports `-Local`, `-LocalCluster`, `-Cloud`, and `-All`.
- defaults to safe read-only where no auth credentials are present.
- requires explicit switches for deployed writes.
- checks `$LASTEXITCODE` after every `RunSimulation.ps1` invocation.
- generates disposable emails when `-RegisterSyntheticUsers` is selected.
- never prints passwords.
- always runs cleanup-only after write/browser runs.
- prints a final table of report paths.

Optional second automation:

```text
Scripts/AnalyzeSimulationReports.ps1
```

Expected behavior:

- reads `summary.json` files.
- produces a Markdown comparison table.
- highlights failed thresholds, unexpected 429s, 5xx, leftovers, browser failures, and high p95 outliers.
- does not require network access.

Quality requirements:

- unit or architecture tests for parsing if implementation is non-trivial.
- no dependency from production app projects to simulation tooling.
- no secrets in output.
- no generated artifacts committed.

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.Simulation"
dotnet test .\BlazorAutoApp.sln --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore
git diff --check
```

Exit criteria:

- Automation reduces repeated manual commands without making deployed writes easier to run accidentally.
- Existing simulator behavior remains unchanged.

Done notes:

- Added `RunSimulationMatrix.ps1`.
- Added `AnalyzeSimulationReports.ps1`.
- `RunSimulationMatrix.ps1` defaults to local read-only when no target is supplied.
- Deployed write matrix requires `-AllowDeployedWrites`.
- Generated deployed users require `-RegisterSyntheticUsers`.
- Generated passwords stay in process environment and are restored/removed after each target.
- The matrix runner checks the exit code after every `RunSimulation.ps1` invocation.
- The matrix runner always runs cleanup-only after write/browser runs.
- The analyzer reads local `summary.json` files only and emits Markdown.
- The analyzer flags failed thresholds, unexpected `429`, `5xx`, cleanup leftovers, and browser failures.
- Verification passed:

```powershell
pwsh -NoProfile -File .\RunSimulationMatrix.ps1 -Help
pwsh -NoProfile -File .\AnalyzeSimulationReports.ps1 -Latest 5
pwsh -NoProfile -File .\AnalyzeSimulationReports.ps1 -Report .\artifacts\simulation\20260530-215221-cloud-public-smoke
pwsh -NoProfile -File .\RunSimulationMatrix.ps1 -Local -Duration 5s
```

## Phase 6 - Update Documentation

Status: completed.

Purpose: make the workflow clear for a future operator.

Update targets:

```text
docs/SimulationGuide.md
docs/ObservabilityGuide.md
README.md
HowToRunLocally.md
```

Required doc additions:

- three-environment simulation matrix.
- deployed credential safety.
- cleanup recovery.
- report comparison workflow.
- GH CLI command examples using the full Windows path if `gh` is not on PATH.
- how to decide whether a finding belongs to app code, deployment, observability, or simulator tooling.
- clear statement that simulation is not deployed with the app.

Exit criteria:

- A developer can reproduce the three-target simulation evidence pass from docs alone.
- The docs do not imply that deployed write simulation is safe without explicit gates.

Done notes:

- Updated `docs/SimulationGuide.md` with matrix and report-analysis sections.
- Updated `README.md` to mention `RunSimulationMatrix.ps1` and `AnalyzeSimulationReports.ps1`.
- Updated `HowToRunLocally.md` with local matrix/report commands.
- Docs preserve the rule that simulation is not deployed with the app.
- Docs preserve explicit deployed write gates.

## Phase 7 - Optional CI/GH Integration Review

Status: completed.

Purpose: decide whether any simulation checks belong in GitHub Actions.

Current position:

- CI should keep building/testing the simulator and verifying `RunSimulation.ps1 -Help`.
- CI should not hit public deployed sites by default.
- CD acceptance should remain fast and deterministic.
- Full deployed simulation matrix should stay manual or workflow-dispatch unless we add dedicated secrets and strict safety gates.

Possible later workflow:

```text
Simulation - Manual Matrix
```

Properties:

- `workflow_dispatch` only.
- environment-protected secrets for simulator accounts.
- explicit inputs for target selection.
- no burst profile.
- no default deployed writes.
- uploads reports as workflow artifacts.
- prints summary table to GitHub step summary.

Before implementing:

- confirm whether generated simulation users should be permanent per environment or disposable per run.
- confirm retention policy for report artifacts.
- confirm whether Cloud may be destroyed when the workflow is dispatched.
- confirm whether LocalCluster self-hosted runner should ever run this workload.

Exit criteria:

- Decision recorded: no CI integration yet, or a constrained manual workflow design.

Decision:

- Do not add public-site simulation to default CI.
- Keep CI responsible for building/testing the simulator and checking wrapper help.
- Keep full deployed matrix execution manual for now, using `RunSimulationMatrix.ps1`.
- A future workflow-dispatch simulation matrix can be reconsidered after we decide simulator account retention, artifact retention, and whether public write simulation belongs in GitHub-hosted Actions.

## Phase 8 - Later Expansion Backlog

Status: recorded.

Only consider these after the first evidence pass is complete.

### Simulator Enhancements

- scenario tags for read API, auth API, write API, browser UI, cleanup.
- per-scenario SLA thresholds by target.
- compare current report against previous baseline.
- emit one compact machine-readable result for dashboards.
- add optional HTML capture on browser sampler failure.
- add target/environment/app-version metadata to report output.

### Observability Enhancements

- dashboard row for simulator runs by target.
- Loki query snippets for simulator user-agent.
- Tempo trace examples for auth/write/browser flows.
- dashboard annotations from simulation run timestamps.
- environment variable or label alignment across local, LocalCluster, and Cloud.

### Deployment Enhancements

- expose deployed app version in health or info endpoint if not already stable.
- add deploy summary with CI run id, image tag, migration artifact, and public URL.
- make post-deploy acceptance link directly to latest simulation/observability evidence.

### Reliability Enhancements

- repeat smoke matrix three times before declaring a flaky problem fixed.
- add soak-lite schedule for local only.
- add Cloud cost guard before any long-running Cloud simulation.
- add stop/recreate reminders before Cloud test sessions.

### Documentation Enhancements

- `docs/SimulationEvidence.md` template.
- "What good looks like" screenshots from Grafana after demo profile.
- troubleshooting table for auth, browser sampler, rate limits, cleanup, and Cloud reachability.

## Quality Gates

Status: completed.

Verification commands run after implementation:

```powershell
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.Simulation"
dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E = "1"
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"
Remove-Item Env:RUN_E2E
pwsh -NoProfile -File .\RunSimulationMatrix.ps1 -Help
pwsh -NoProfile -File .\AnalyzeSimulationReports.ps1 -Latest 5
git diff --check
.\RunSimulation.ps1 -Target local -AuthCheck
```

Results:

- Build passed with `0` warnings and `0` errors.
- Simulator-focused tests passed: `24` passed.
- Full solution tests passed: `128` passed, `7` skipped.
- E2E tests passed: `6` passed, `1` skipped.
- Formatting verification passed.
- `RunSimulationMatrix.ps1 -Help` passed.
- `AnalyzeSimulationReports.ps1 -Latest 5` passed.
- `git diff --check` passed.
- Local auth check after the auth diagnostic change passed: `20260530-220003-local-smoke`.

## Done Definition

This plan is complete when:

- fresh simulation reports exist for local, LocalCluster, and Cloud.
- every environment has read-only, auth, browser/write, and cleanup evidence.
- report comparison is recorded with concrete numbers.
- latest CI/CD state is recorded with GH run ids and SHAs.
- findings are classified and ranked.
- at least one small automation or documentation improvement is implemented if the evidence justifies it.
- quality gates pass after any repo changes.
- no synthetic books are left behind in any environment.
- the next expansion backlog is explicit enough for a weaker AI or another developer to continue safely.

Completion notes:

- All done-definition items are satisfied for the first expansion pass.
- Later backlog remains intentionally open for future work.
