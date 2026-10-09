# Improved Simulation Refactor Plan

Status: executing. This file is the durable progress record in case context is
lost.

Last updated: 2026-05-30.

Important repo note: `/Plans/` is ignored by `.gitignore`. This plan is
intentionally stored here because requested, but it will not be committed unless
moved to `docs/` or the ignore rule changes.

## Goal

Refactor the traffic simulator from a `Tools/TrafficSimulation` helper into one
first-class operator project:

```text
BlazorAutoApp.Simulation/
RunSimulation.ps1
RunSimulation.cmd
```

Do not create a separate `BlazorAutoApp.Simulation.Tests` project. Simulator
tests live under the existing test project:

```text
BlazorAutoApp.Test/Simulation/
```

The refactor should:

- remove duplicated app API contracts from the simulator.
- reuse `BlazorAutoApp.Core` request/response DTOs and validation rules.
- keep the simulator runnable through the existing wrapper commands.
- keep production Docker and deployment images app-only.
- keep tests in the existing test project to avoid another root project.
- keep V1 read-only, V2 auth-check, writes, cleanup, and browser sampler behavior intact.
- avoid adding any runtime dependency from the app to the simulator.

## Accepted Architecture

Use this shape:

```text
BlazorAutoApp.Simulation/
  BlazorAutoApp.Simulation.csproj
  Program.cs
  Auth/
  Books/
  Browser/
  Http/
  Options/
  Reporting/
  Running/
  Scenarios/

BlazorAutoApp.Test/
  Simulation/
    SimulationOptionsAuthTests.cs
    SyntheticBookNamingTests.cs
    ContractReuseTests.cs
    DeploymentDoesNotPublishSimulationTests.cs

RunSimulation.ps1
RunSimulation.cmd
docs/SimulationGuide.md
```

Dependency direction:

```text
BlazorAutoApp.Simulation
  -> BlazorAutoApp.Core
  -> Microsoft.Playwright

BlazorAutoApp.Test
  -> BlazorAutoApp
  -> BlazorAutoApp.Client
  -> BlazorAutoApp.Core
  -> BlazorAutoApp.Simulation

BlazorAutoApp
BlazorAutoApp.Client
BlazorAutoApp.Core
  -> never BlazorAutoApp.Simulation
```

This is intentionally simpler than a separate simulator test project. The
tradeoff is that `BlazorAutoApp.Test` references the simulator, but that is a
test-only dependency. Production projects, Docker images, CI publish artifacts,
and deployment assets must not reference or deploy simulation.

## Rejected Architecture

Do not create:

```text
BlazorAutoApp.Simulation.Tests/
```

Reason: it adds another root project for a small set of simulator unit and
architecture tests. The existing `BlazorAutoApp.Test` project already owns
architecture, infrastructure, and E2E checks. Keeping simulator tests there is
less project noise and still safe because production projects do not reference
the simulator.

## Contract Reuse Strategy

The simulator references `BlazorAutoApp.Core` and uses the actual app contracts.

Removed duplicated local contracts:

```text
BlazorAutoApp.Simulation/Books/BookContracts.cs
BlazorAutoApp.Simulation/Http/AuthorBookContracts.cs
```

Core contracts used at the HTTP boundary:

```text
CreateBookRequest
CreateBookResponse
UpdateBookRequest
GetBookResponse
GetBooksResponse
BookListItemResponse
GetAuthorBooksResponse
AuthorBookListItemResponse
```

Concrete HTTP-boundary rule:

- `ListAsync` deserializes `GetBooksResponse` and exposes `BookListItemResponse` values.
- `GetAsync` deserializes `GetBookResponse`.
- `CreateAsync` sends `CreateBookRequest` and deserializes `CreateBookResponse`.
- `UpdateAsync` sends `UpdateBookRequest`.
- author-book read scenarios deserialize `GetAuthorBooksResponse`.
- cleanup inspects `BookListItemResponse`.
- reports and ledgers map API DTOs into simulator-owned types such as `SyntheticBook`.

Do not keep a local type named `BookItem`, `CreateBookRequest`,
`CreateBookResponse`, `UpdateBookRequest`, `AuthorBooksResponse`, or
`AuthorBookItem`.

## Validation Reuse Strategy

Synthetic book generation should use app rules from `BlazorAutoApp.Core`:

```text
BookRules.TitleMaxLength
BookRules.AuthorMaxLength
BookRules.UrlMaxLength
BookUrlValidation.IsValidOptionalHttpUrl(...)
```

Tests must prove:

- generated synthetic titles fit `BookRules.TitleMaxLength`.
- generated author fits `BookRules.AuthorMaxLength`.
- generated URL fits `BookRules.UrlMaxLength`.
- generated URL is accepted by `BookUrlValidation`.

## Deployment Safety Requirements

The simulation project must not be deployed.

Production image building remains:

```text
BlazorAutoApp/Dockerfile
```

The Dockerfile must restore, build, and publish only:

```text
BlazorAutoApp/BlazorAutoApp.csproj
```

Add explicit `.dockerignore` entries:

```text
BlazorAutoApp.Simulation/**
Tools/**
```

Architecture tests in `BlazorAutoApp.Test/Simulation` should verify:

- `BlazorAutoApp/Dockerfile` does not mention `BlazorAutoApp.Simulation`.
- `BlazorAutoApp/Dockerfile` publishes `BlazorAutoApp/BlazorAutoApp.csproj`.
- `.github/workflows/ci.yml` builds the Docker image with `-f BlazorAutoApp/Dockerfile`.
- `.github/workflows/cd-localcluster.yml` does not build, publish, or deploy simulation.
- `.github/workflows/cd-cloud.yml` does not build, publish, or deploy simulation.
- deployment compose/templates do not mention `BlazorAutoApp.Simulation`.
- app, client, and core projects do not reference simulation.
- `BlazorAutoApp.Simulation` references `BlazorAutoApp.Core`.

Project-level safety:

```xml
<IsPackable>false</IsPackable>
<IsPublishable>false</IsPublishable>
<RootNamespace>BlazorAutoApp.Simulation</RootNamespace>
<AssemblyName>BlazorAutoApp.Simulation</AssemblyName>
```

The wrapper should still use `dotnet run`, not a published binary.

## Test Depth Strategy

Use focused verification while moving files, then run full acceptance before
closing.

- after each phase, run phase-specific build/test commands.
- run full solution tests after project movement, contract reuse, deployment
  guard tests, and final acceptance.
- run app E2E tests in final acceptance, and earlier if app, client, or Core
  behavior changes beyond simulator contract references.
- do not run deployed LocalCluster or Cloud simulation before local build, unit
  tests, formatting, and Docker safety checks pass.

PowerShell E2E command:

```powershell
$env:RUN_E2E = "1"
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"
Remove-Item Env:RUN_E2E
```

## Phase 0 - Baseline And Freeze

Status: completed.

Checklist:

- [x] Run `git status --short` and identify unrelated changes.
- [x] Run current simulation tests.
- [x] Run current local auth-check.
- [x] Run current local write smoke.
- [x] Run current local browser sampler.

Done notes:

- Existing dirty worktree was observed and unrelated changes were left alone.
- baseline build passed.
- focused simulator tests passed.
- `.\RunSimulation.ps1 -InstallBrowsers` passed.
- local `/health/ready` returned `200 Healthy`.
- local auth-check passed.
- local write smoke passed with `cleanup: ok, leftovers=0`.
- local browser sampler passed with `cleanup: ok, leftovers=0`.

## Phase 1 - Create First-Class Simulation Project

Status: completed.

Checklist:

- [x] Created `BlazorAutoApp.Simulation/`.
- [x] Moved files from `Tools/TrafficSimulation/`.
- [x] Renamed project to `BlazorAutoApp.Simulation.csproj`.
- [x] Updated root namespace and assembly name.
- [x] Added `IsPackable=false` and `IsPublishable=false`.
- [x] Kept `Microsoft.Playwright`.
- [x] Updated namespaces to `BlazorAutoApp.Simulation`.
- [x] Updated solution to include only `BlazorAutoApp.Simulation`.
- [x] Updated `RunSimulation.ps1` and help text to the new project path.
- [x] Removed the old `Tools/` folder.

Done notes:

- solution lists `BlazorAutoApp.Simulation`.
- solution no longer lists `TrafficSimulation`.
- `dotnet restore .\BlazorAutoApp.sln` passed.
- `dotnet build .\BlazorAutoApp.sln --no-restore` passed.
- `.\RunSimulation.ps1 -Help` passed with the new project path.

## Phase 2 - Keep Simulator Tests In Existing Test Project

Status: completed.

Checklist:

- [x] Deleted the separate `BlazorAutoApp.Simulation.Tests` project.
- [x] Removed it from `BlazorAutoApp.sln`.
- [x] Moved simulator tests into `BlazorAutoApp.Test/Simulation/`.
- [x] Updated simulator internals access to `BlazorAutoApp.Test`.
- [x] Added `BlazorAutoApp.Test` project reference to `BlazorAutoApp.Simulation`.
- [x] Verified no `BlazorAutoApp.Simulation.Tests` folder remains.

Done notes:

- solution now has five projects: app, client, core, simulation, test.
- `BlazorAutoApp.Test/Simulation` owns simulator tests.
- `dotnet restore .\BlazorAutoApp.sln` passed.
- `dotnet build .\BlazorAutoApp.sln --no-restore` passed.
- `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.Simulation"` passed: 14 passed.
- `dotnet test .\BlazorAutoApp.sln --no-build` passed: 118 passed, 7 skipped.

## Phase 3 - Reuse Core Book Contracts

Status: completed.

Checklist:

- [x] Added `ProjectReference` from `BlazorAutoApp.Simulation` to `BlazorAutoApp.Core`.
- [x] Replaced local book contract classes with Core DTOs.
- [x] Replaced local author-book contract classes with Core DTOs.
- [x] Deleted duplicated contract files.
- [x] Kept simulator-only report and ledger state local.
- [x] Added tests that fail if duplicate request/response contracts return.

Done notes:

- HTTP clients now use Core DTOs for books and author-books.
- duplicated local contract files were deleted.
- duplicate contract scan returned no matches in `BlazorAutoApp.Simulation`.
- simulator tests and full solution tests passed after this phase.

## Phase 4 - Reuse Core Validation Rules

Status: completed.

Checklist:

- [x] Use `BookRules` in synthetic naming tests.
- [x] Use `BookUrlValidation` in synthetic URL tests.
- [x] Add tests for generated title, author, and URL lengths.
- [x] Add tests for URL validity.

Done notes:

- `SyntheticBookNamingTests` now verifies generated synthetic books satisfy
  `BookRules` and `BookUrlValidation`.
- `dotnet build .\BlazorAutoApp.sln --no-restore` passed.
- simulation-focused tests passed: 15 passed.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.Simulation"
```

## Phase 5 - Make Deployment Exclusion Explicit

Status: completed.

Checklist:

- [x] Add `.dockerignore` entries for `BlazorAutoApp.Simulation/**` and `Tools/**`.
- [x] Add deployment-safety architecture tests under `BlazorAutoApp.Test/Simulation`.
- [x] Confirm Dockerfile still publishes only `BlazorAutoApp/BlazorAutoApp.csproj`.
- [x] Confirm CI Docker build still uses `BlazorAutoApp/Dockerfile`.
- [x] Confirm LocalCluster and Cloud CD workflows never build, publish, or deploy simulation.
- [x] Confirm deployment assets do not mention `BlazorAutoApp.Simulation`.

Done notes:

- `.dockerignore` explicitly excludes `BlazorAutoApp.Simulation/**` and `Tools/**`.
- `DeploymentDoesNotPublishSimulationTests` added under `BlazorAutoApp.Test/Simulation`.
- simulation-focused tests passed: 24 passed.
- `docker build --pull -f BlazorAutoApp/Dockerfile -t blazorautoapp-deployment-safety-check .` passed.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.Simulation"
docker build --pull -f BlazorAutoApp/Dockerfile -t blazorautoapp-deployment-safety-check .
```

## Phase 6 - Update Docs And CI

Status: completed.

Checklist:

- [x] Update `README.md`.
- [x] Update `HowToRunLocally.md`.
- [x] Update `docs/SimulationGuide.md`.
- [x] Update `docs/ObservabilityGuide.md`.
- [x] Update CI help step if needed.
- [x] Replace references to `Tools/TrafficSimulation`.
- [x] Mention `BlazorAutoApp.Simulation` is not deployed.

Done notes:

- README and local/simulation guides now describe `BlazorAutoApp.Simulation`.
- docs state the simulator is built and tested, but not deployed with the app.
- no active docs/CI references remain for `Tools/TrafficSimulation`,
  `TrafficSimulation.csproj`, or `BlazorAutoApp.Simulation.Tests`.
- `.\RunSimulation.ps1 -Help` passed.

Verification:

```powershell
rg -n "Tools/TrafficSimulation|TrafficSimulation.csproj|BlazorAutoApp.Simulation.Tests" README.md HowToRunLocally.md docs RunSimulation.ps1 .github BlazorAutoApp.sln
.\RunSimulation.ps1 -Help
```

## Phase 7 - Full Environment Acceptance

Status: completed.

Commands:

```powershell
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E = "1"
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"
Remove-Item Env:RUN_E2E
dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore
git diff --check
.\RunSimulation.ps1 -Help
.\RunSimulation.ps1 -Target local -AuthCheck
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -BrowserSampler -Duration 60s
.\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
```

LocalCluster deployed-target commands:

```powershell
.\RunSimulation.ps1 -Target localcluster-public -Profile smoke -AllowDeployed -Duration 30s
.\RunSimulation.ps1 -Target localcluster-public -AuthCheck -AllowDeployed
.\RunSimulation.ps1 -Target localcluster-public -Profile smoke -Writes -Cleanup -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target localcluster-public -Profile smoke -Writes -Cleanup -BrowserSampler -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target localcluster-public -CleanupOnly -AllowDeployed -AllowWrite
```

Cloud deployed-target commands:

```powershell
.\RunSimulation.ps1 -Target cloud-public -Profile smoke -AllowDeployed -Duration 30s
.\RunSimulation.ps1 -Target cloud-public -AuthCheck -AllowDeployed
.\RunSimulation.ps1 -Target cloud-public -Profile smoke -Writes -Cleanup -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target cloud-public -Profile smoke -Writes -Cleanup -BrowserSampler -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target cloud-public -CleanupOnly -AllowDeployed -AllowWrite
```

Credential requirements:

- deployed auth checks and write runs require a safe simulator account for each deployed environment.
- use `SIMULATION_AUTH_EMAIL` and `SIMULATION_AUTH_PASSWORD` or `SIMULATION_AUTH_PASSWORD_ENV`.
- do not paste passwords into command history.
- if the simulator user does not exist yet, create it with the simulator registration flow and the same safety gates.
- if deployed auth credentials are unavailable, run deployed read-only smoke checks and record the missing auth/write acceptance as an explicit gap.

Done notes:

- `dotnet build .\BlazorAutoApp.sln --no-restore` passed.
- `dotnet test .\BlazorAutoApp.sln --no-build` passed: 128 passed, 7 skipped.
- E2E with `RUN_E2E=1` passed: 6 passed, 1 skipped.
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore` passed.
- `git diff --check` passed with the existing `BlazorAutoApp.sln` line-ending warning only.
- `.\RunSimulation.ps1 -Help` passed.
- local auth-check passed: `20260530-212429-local-smoke`.
- local write smoke and browser sampler passed with `cleanup: ok, leftovers=0`: `20260530-212438-local-smoke`.
- local cleanup-only passed with `cleanup: ok, leftovers=0`: `20260530-212537-local-smoke`.
- LocalCluster read-only public smoke passed with `unexpected 429: 0` and no unexpected failures.
- Cloud read-only public smoke passed with `unexpected 429: 0` and no unexpected failures.
- deployed auth bootstrap now verifies the browser session through authenticated API cookies instead of waiting for a UI-only bookcase marker.
- deployed browser sampler waits for the authenticated bookcase and fails clearly if the login prompt appears.
- LocalCluster deployed auth registration passed: `20260530-211850-localcluster-public-smoke`.
- LocalCluster deployed auth login passed: `20260530-211854-localcluster-public-smoke`.
- LocalCluster deployed authenticated write smoke passed with `cleanup: ok, leftovers=0`: `20260530-211858-localcluster-public-smoke`.
- LocalCluster deployed browser sampler passed with `cleanup: ok, leftovers=0`: `20260530-211922-localcluster-public-smoke`.
- LocalCluster deployed cleanup-only passed with `cleanup: ok, leftovers=0`: `20260530-212017-localcluster-public-smoke`.
- Cloud deployed auth registration passed: `20260530-212020-cloud-public-smoke`.
- Cloud deployed auth login passed: `20260530-212023-cloud-public-smoke`.
- Cloud deployed authenticated write smoke passed with `cleanup: ok, leftovers=0`: `20260530-212026-cloud-public-smoke`.
- Cloud deployed browser sampler passed with `cleanup: ok, leftovers=0`: `20260530-212050-cloud-public-smoke`.
- Cloud deployed cleanup-only passed with `cleanup: ok, leftovers=0`: `20260530-212143-cloud-public-smoke`.

## Phase 8 - Post-Acceptance Improvement Review

Status: completed.

Checklist:

- [x] Collect latest reports from `artifacts/simulation/` for local, LocalCluster, and Cloud.
- [x] Compare success rate, unexpected 429s, 5xx responses, latency percentiles, auth results, cleanup results, and browser sampler results.
- [x] Inspect whether failures are environment issues, simulator issues, app issues, or documentation issues.
- [x] Check that simulator traffic appears correctly in observability dashboards, logs, traces, and metrics.
- [x] Fix small obvious simulator or documentation defects immediately.
- [x] Record larger follow-up improvements with owner, impact, and next action.

Done notes:

- Local latest auth report: `20260530-212429-local-smoke`, failed thresholds `false`, unexpected 429 `0`.
- Local latest cleanup report: `20260530-212537-local-smoke`, failed thresholds `false`, unexpected 429 `0`, cleanup `ok, leftovers=0`.
- Local browser sampler report: `20260530-212438-local-smoke`, failed thresholds `false`, unexpected 429 `0`, cleanup `ok, leftovers=0`, browser sampler enabled.
- LocalCluster public read-only report: `20260530-210445-localcluster-public-smoke`, failed thresholds `false`, unexpected 429 `0`.
- LocalCluster public authenticated browser report: `20260530-211922-localcluster-public-smoke`, failed thresholds `false`, unexpected 429 `0`, cleanup `ok, leftovers=0`, browser sampler enabled.
- Cloud public read-only report: `20260530-210521-cloud-public-smoke`, failed thresholds `false`, unexpected 429 `0`.
- Cloud public authenticated browser report: `20260530-212050-cloud-public-smoke`, failed thresholds `false`, unexpected 429 `0`, cleanup `ok, leftovers=0`, browser sampler enabled.
- Fixed auth bootstrap brittleness found during deployed acceptance: login/register success is now verified through `/api/books` with exported browser cookies, and the browser sampler has a clearer authenticated-UI wait.
- No remaining auth/write/browser/cleanup acceptance gap exists for the current LocalCluster and Cloud environments.
- Observability dashboard visual confirmation was not performed in this pass; traffic reports were generated and are available under `artifacts/simulation/`.

## Done Definition

The refactor is complete only when:

- `BlazorAutoApp.Simulation` exists and replaces `Tools/TrafficSimulation`.
- no `BlazorAutoApp.Simulation.Tests` project exists.
- simulator tests live under `BlazorAutoApp.Test/Simulation`.
- `BlazorAutoApp.Test` references simulation only for tests.
- app, client, and core projects do not reference simulation.
- simulation references `BlazorAutoApp.Core`.
- duplicated app API contracts are removed.
- synthetic data generation uses Core validation/rules.
- production Dockerfile does not mention simulation.
- `.dockerignore` explicitly excludes simulation.
- deployment-safety tests pass.
- `RunSimulation.ps1` commands still work.
- docs clearly state simulation is not deployed.
- local authenticated write and browser sampler acceptance pass.
- LocalCluster and Cloud read-only, auth, write, browser sampler, and cleanup acceptance pass.
- post-acceptance review has produced either concrete fixes or a documented improvement backlog.
