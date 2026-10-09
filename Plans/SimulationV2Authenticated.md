# Authenticated Traffic Simulation V2 Plan

Status: V2 implemented and locally accepted on 2026-05-30. Optional deployed acceptance remains not started.

Last updated: 2026-05-30.

Important repo note: `/Plans/` is currently ignored by `.gitignore`. This file is intentionally created where requested, but it will not be committed unless the repo's ignore rules are changed or the plan is moved into `docs/`.

## Executive Summary

V1 of `Tools/TrafficSimulation` is a read-only HTTP simulator. V2 should add safe authenticated traffic for the Books app without changing the deployment topology, adding permanent services, bypassing authentication, or creating unbounded test data.

The recommended V2 design is:

```text
Playwright auth bootstrap
  -> log in or explicitly register one persistent simulator account
  -> export real application cookies

Existing HTTP simulator engine
  -> reuse those cookies in HttpClient
  -> run low-rate authenticated book list/create/update/delete scenarios
  -> track every synthetic book
  -> clean up and verify zero leftovers

Optional browser sampler
  -> one browser user
  -> one low-frequency add/edit/delete UI journey
  -> proves the real Blazor UI path without using browsers for load
```

The simulator remains an observability and confidence tool. It is not a capacity test, bot, background worker, or stress-testing framework.

## Main Decisions

Decision 1: Keep the simulator in `Tools/TrafficSimulation`.

Reason: V1 already exists, builds with the solution, and has the right role as an operator/developer tool. V2 should extend it rather than creating a separate project with duplicated target/profile/report logic.

Decision 2: Use Playwright only for auth bootstrap and the optional UI sampler.

Reason: ASP.NET Identity login/register pages use real form behavior and antiforgery details that are brittle to hand-code. Browser login gives a real session. After that, HTTP traffic is cheaper, easier to pace, easier to report, and safer than browser-generated volume.

Decision 3: Use one persistent simulator account per target.

Reason: a fresh account per run would pollute deployed databases. There is no clean app-level account deletion path suitable for this simulator. Books can be cleaned safely; user accounts should not be created repeatedly.

Decision 4: Writes are always gated and cleanup is the default.

Reason: authenticated traffic mutates real databases. Local, LocalCluster, and Cloud may be disposable today, but the tool should still be safe by default.

Decision 5: No Cloudflare, Hetzner, Ansible, OpenTofu, or deployment changes are part of V2.

Reason: the simulator targets already running apps. V2 should not alter infrastructure, firewall rules, tunnels, DNS, dashboards, or deployment pipelines.

## Non-Goals

Do not implement these in V2:

- permanent background traffic generation.
- hosted services inside the production app.
- production-only auth bypasses or hidden testing endpoints.
- database inserts for normal simulation traffic.
- deleting simulator user accounts after every run.
- creating a fresh simulator account for each run by default.
- many synthetic users to multiply the app's per-user rate limit.
- `X-Forwarded-For` spoofing.
- high-volume deployed load testing.
- Cloudflare API automation.
- Hetzner API automation.
- public observability ports.
- new nodes, new containers, or new deployment roles.

## Current Repo Facts

Verified from the repo on 2026-05-30:

Authentication:

```text
Login route:    /Account/Login
Register route: /Account/Register
Login fields:   #Input\.Email, #Input\.Password
Register fields:#Input\.Email, #Input\.Password, #Input\.ConfirmPassword
Login button:   role button, exact name "Log in"
Register button:role button, exact name "Register"
```

Known local seeded user used by existing E2E tests:

```text
user@user.com / User123
```

Book UI selectors already exist:

```text
add-book
book-modal
book-page-editor
book-title
book-author
book-url
book-save
book-page-view
book-edit-pencil
book-delete
book-delete-confirm
book-back
user-bookcase-title
user-book-empty-state
```

Existing V1 simulator already has reserved flags:

```text
--writes
--cleanup
--cleanup-only
--browser-sampler
--auth-write-rps-budget
```

Existing wrapper already exposes matching switches:

```powershell
.\RunSimulation.ps1 -Writes -Cleanup -CleanupOnly -BrowserSampler -AllowWrite
```

This means V2 should reuse and complete the existing CLI shape instead of inventing unrelated names.

## Safety Model

There are three independent safety gates:

```text
deployed target gate:
  required for localcluster-edge and cloud-edge
  required for authenticated writes against origin-via-tunnel unless its --base-url is clearly local
  satisfied by --allow-deployed or SIMULATION_ALLOW_DEPLOYED=1

write gate:
  required for registration, book create/update/delete, and cleanup
  satisfied by --allow-write or SIMULATION_ALLOW_WRITE=1

dangerous override gate:
  required only for keep-data or unusual destructive cleanup modes
  satisfied by --yes
```

Normal V2 commands should fail fast before opening a browser when a required gate is missing.

Rules:

- Read-only V1 commands must keep their current gate behavior.
- `--auth-check` requires credentials, but does not require write gate unless it also registers a user.
- `--register-synthetic-user` requires the write gate because it mutates the database.
- `--writes` requires the write gate.
- `--cleanup-only` requires the write gate.
- Deployed `--writes` requires both deployed and write gates.
- `origin-via-tunnel` read-only behavior should not be changed just because V2 exists.
- `origin-via-tunnel` authenticated writes should require `--allow-deployed` unless the base URL host is `localhost`, `127.0.0.1`, or `::1`.
- `--keep-synthetic-data` requires `--writes`, write gate, and `--yes`.
- `--browser-sampler` should be rejected unless `--writes` is also enabled, because the UI sampler creates, updates, and deletes a synthetic book.

## Mode Matrix

This matrix is the quickest way to check whether the implementation is coherent.

```text
mode                    auth required  writes data  cleanup default  requires AllowWrite  requires AllowDeployed
read-only V1             no             no           no               no                   only existing V1 target rules
auth-check               yes            no           no               no                   for deployed targets
auth-check + register    yes            account      no               yes                  for deployed targets
writes smoke/demo        yes            books        yes              yes                  for deployed targets
cleanup-only             yes            deletes      n/a              yes                  for deployed targets
browser sampler only     invalid        n/a          n/a              n/a                  n/a
writes + browser sampler yes            books        yes              yes                  for deployed targets
keep synthetic data      yes            books        no               yes + --yes          for deployed targets
```

If implementation behavior disagrees with this table, fix the implementation or explicitly update the plan before continuing.

## Target Behavior

The four current targets stay the source of truth:

```text
local               https://localhost:7186
localcluster-edge   https://books.jacobgrum.com
cloud-edge          https://bookscloud.jacobgrum.com
origin-via-tunnel   requires --base-url
```

Default auth account resolution:

```text
local:
  if SIMULATION_AUTH_EMAIL and SIMULATION_AUTH_PASSWORD exist, use them
  otherwise use seeded user@user.com / User123

localcluster-edge:
  require SIMULATION_AUTH_EMAIL and SIMULATION_AUTH_PASSWORD

cloud-edge:
  require SIMULATION_AUTH_EMAIL and SIMULATION_AUTH_PASSWORD

origin-via-tunnel:
  require SIMULATION_AUTH_EMAIL and SIMULATION_AUTH_PASSWORD unless --base-url is localhost
```

No target should create accounts automatically. Account creation is allowed only with explicit `--register-synthetic-user`.

## CLI Contract

Keep all V1 commands working.

Add these tool options:

```text
--auth-check
--auth-email <email>
--auth-password-env <environment variable name>
--register-synthetic-user
--keep-synthetic-data
--playwright-browser <chromium>
--headed-browser
--install-browsers
```

Defaults:

```text
--auth-password-env SIMULATION_AUTH_PASSWORD
--playwright-browser chromium
```

Do not add `--auth-password <password>` unless there is a later explicit decision to accept command-line password exposure.

PowerShell wrapper additions:

```powershell
-AuthCheck
-AuthEmail <email>
-AuthPasswordEnv <name>
-RegisterSyntheticUser
-KeepSyntheticData
-InstallBrowsers
-HeadedBrowser
```

User-facing commands should look like this:

Read-only V1 smoke:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke
```

Browser/auth bootstrap check only:

```powershell
.\RunSimulation.ps1 -Target local -AuthCheck
```

Local authenticated write smoke:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
```

Local cleanup-only:

```powershell
.\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
```

Local authenticated write smoke plus browser UI sampler:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -BrowserSampler -Duration 60s
```

Cloud authenticated write smoke:

```powershell
$env:SIMULATION_AUTH_EMAIL = "bookscloud-sim@example.com"
$env:SIMULATION_AUTH_PASSWORD = "<secret>"

.\RunSimulation.ps1 -Target cloud-edge -Profile smoke -Writes -Cleanup -AllowDeployed -AllowWrite -Duration 60s
```

First-time Cloud simulator account creation:

```powershell
$env:SIMULATION_AUTH_EMAIL = "bookscloud-sim@example.com"
$env:SIMULATION_AUTH_PASSWORD = "<secret>"

.\RunSimulation.ps1 -Target cloud-edge -AuthCheck -RegisterSyntheticUser -AllowDeployed -AllowWrite
```

The first-time registration command should create or verify the account, then stop. It should not also run book traffic unless `--writes` is explicitly supplied.

## Credentials

Preferred environment variables:

```text
SIMULATION_AUTH_EMAIL
SIMULATION_AUTH_PASSWORD
```

Optional advanced password environment variable:

```powershell
$env:BOOKSCLOUD_SIM_PASSWORD = "<secret>"
.\RunSimulation.ps1 -Target cloud-edge -AuthCheck -AuthEmail "bookscloud-sim@example.com" -AuthPasswordEnv BOOKSCLOUD_SIM_PASSWORD -AllowDeployed
```

Rules:

- Never print the password.
- Never print cookies.
- Never print bearer/auth headers.
- Never write raw Playwright storage state into `summary.json` or `summary.md`.
- If the report needs to identify the account, include only:
  - email domain, if useful.
  - short stable SHA-256 hash of normalized email.
- Do not write `.env` files as part of V2.
- Do not add secrets to GitHub Actions as part of V2.

## Synthetic User Lifecycle

Normal flow:

1. Resolve email/password.
2. Try login.
3. If login succeeds, continue.
4. If login fails and `--register-synthetic-user` is not set, fail before traffic starts.
5. If login fails and `--register-synthetic-user` is set, register that exact email/password once.
6. After registration, verify logged-in state.
7. Continue only if the requested mode needs further work.

Registration rules:

- `--register-synthetic-user` requires write gate.
- It must not generate a random email by default.
- It must not silently create `sim+timestamp@...` accounts.
- It may offer a clear generated suggestion in the error message, but the user must provide it.
- If registration fails because the account already exists, retry login once.

Recommended persistent accounts:

```text
local:
  user@user.com, seeded, no extra setup needed

localcluster-edge:
  books-localcluster-sim@example.com, or a real address controlled by the operator

cloud-edge:
  bookscloud-sim@example.com, or a real address controlled by the operator
```

## Synthetic Book Lifecycle

Every V2 synthetic book must be safe to identify and delete.

Title:

```text
[sim-v2:<target>:<runId>] <scenario> <sequence>
```

Author:

```text
Traffic Simulation
```

URL:

```text
https://simulation.invalid/books/<target>/<runId>/<sequence>
```

Example:

```text
title:  [sim-v2:local:20260530T211500Z-ab12cd34] smoke 0001
author: Traffic Simulation
url:    https://simulation.invalid/books/local/20260530T211500Z-ab12cd34/0001
```

Run ID:

```text
yyyyMMddTHHmmssZ-8hex
```

Deletion is allowed only when all of these are true:

- the authenticated API can see the book in the simulator user's own book list.
- title starts with `[sim-v2:`.
- title target matches the current target unless an explicit future cleanup-all-targets mode exists.
- URL starts with `https://simulation.invalid/books/`.
- the book was either recorded in the current run ledger or found by cleanup-only scan.

Never delete:

- public author books.
- books from another user.
- books without the V2 prefix.
- books with the V2 prefix but a non-simulation URL.
- user-created books that happen to contain similar words.

Cleanup defaults:

```text
--writes:
  cleanup enabled by default

--cleanup:
  explicit cleanup after run

--keep-synthetic-data:
  skip cleanup only for debugging, requires --yes

--cleanup-only:
  no traffic, login, scan current simulator user's books, delete safe V2 synthetic books, verify zero leftovers
```

Exit code:

```text
4 cleanup failed or synthetic data was left behind
```

## Ledger And Artifacts

The simulator needs an in-memory ledger and a persisted ledger.

In-memory ledger tracks:

```text
run ID
target
synthetic user email hash
created book IDs
created titles
updated titles
delete attempts
cleanup result
```

Persisted ledger path:

```text
artifacts/simulation/<timestamp>-<target>-<profile>/synthetic-ledger.json
```

Persisted ledger must not contain:

- password.
- cookies.
- auth headers.
- raw Playwright storage state.

It may contain:

- run ID.
- target.
- email hash.
- synthetic book IDs.
- synthetic titles.
- synthetic URLs.

Reason: if a run is interrupted, the operator can inspect the ledger and run cleanup-only.

## Rate-Limit And Backoff Design

The app limits relevant traffic roughly as follows:

```text
global app traffic: 600 requests/minute per user or IP
Books APIs:         60 requests/minute per user or IP
Account POSTs:      120 requests/5 minutes per user or IP
```

V2 should use central token buckets:

```text
total request budget
anonymous API budget
authenticated read API budget
authenticated write budget
browser journey budget
auth bootstrap budget
```

Recommended defaults:

```text
local auth write budget:       0.20 writes/sec
deployed auth write budget:    0.05 writes/sec
browser sampler budget:        one journey every 60-120 seconds
auth bootstrap retries:        at most 1 login retry, at most 1 register attempt
```

Important accounting:

- `POST /api/books` consumes authenticated write budget.
- `PUT /api/books/{id}` consumes authenticated write budget.
- `DELETE /api/books/{id}` consumes authenticated write budget.
- `GET /api/books` consumes authenticated read API budget.
- Login/register happens before the main simulation window and is separately reported.
- Browser sampler create/update/delete consumes browser journey budget and should also be counted in write totals.

On `429`:

- honor `Retry-After` if present.
- pause that scenario class, not the entire process unless global limits are hit.
- increment expected or unexpected rate-limit counters.
- fail smoke/demo on unexpected `429` unless `--allow-rate-limit` is explicit.

Do not solve rate limiting by:

- creating extra simulator accounts.
- spoofing forwarded IP headers.
- raising RPS silently.
- retrying mutating requests in a tight loop.

## Package And Browser Installation

Add this central package version:

```xml
<PackageVersion Include="Microsoft.Playwright" Version="1.60.0" />
```

The version should match the existing `Microsoft.Playwright.Xunit.v3` version unless the repo updates both together.

Update:

```text
Tools/TrafficSimulation/TrafficSimulation.csproj
```

with:

```xml
<PackageReference Include="Microsoft.Playwright" />
```

Add a friendly browser install path:

```powershell
.\RunSimulation.ps1 -InstallBrowsers
```

Expected behavior:

1. Build `Tools/TrafficSimulation`.
2. Locate the generated `playwright.ps1`.
3. Install Chromium only.
4. Print a concise success message.

If browsers are missing and the user runs auth/browser mode:

- fail with a clear message.
- tell the user to run `.\RunSimulation.ps1 -InstallBrowsers`.
- do not fail halfway through a write run after creating data.

## Proposed Code Structure

Add:

```text
Tools/TrafficSimulation/Auth/AuthenticatedSession.cs
Tools/TrafficSimulation/Auth/AuthBootstrapOptions.cs
Tools/TrafficSimulation/Auth/AuthBootstrapResult.cs
Tools/TrafficSimulation/Auth/BrowserAuthBootstrap.cs
Tools/TrafficSimulation/Auth/CookieContainerFactory.cs
Tools/TrafficSimulation/Auth/RedactedIdentity.cs

Tools/TrafficSimulation/Books/AuthenticatedBooksClient.cs
Tools/TrafficSimulation/Books/BookWriteResult.cs
Tools/TrafficSimulation/Books/SyntheticBook.cs
Tools/TrafficSimulation/Books/SyntheticBookCleanup.cs
Tools/TrafficSimulation/Books/SyntheticBookLedger.cs
Tools/TrafficSimulation/Books/SyntheticBookNaming.cs

Tools/TrafficSimulation/Browser/BrowserSampler.cs
Tools/TrafficSimulation/Browser/BrowserSamplerResult.cs

Tools/TrafficSimulation/Running/AuthenticatedScenarioRunner.cs
Tools/TrafficSimulation/Running/CancellationCleanupCoordinator.cs
Tools/TrafficSimulation/Running/TokenBucketBudget.cs

Tools/TrafficSimulation/Options/AuthOptions.cs
Tools/TrafficSimulation/Options/WriteOptions.cs
```

Update:

```text
Tools/TrafficSimulation/Program.cs
Tools/TrafficSimulation/HelpText.cs
Tools/TrafficSimulation/Options/SimulationOptions.cs
Tools/TrafficSimulation/Reporting/SimulationReport.cs
Tools/TrafficSimulation/Reporting/SimulationReportWriter.cs
RunSimulation.ps1
RunSimulation.cmd
```

Avoid:

- adding app references from `Tools/TrafficSimulation` to production projects unless needed for DTOs.
- copying large pieces of E2E test infrastructure into the tool.
- making implementation types public only for tests.

If tests need internals:

```csharp
[assembly: InternalsVisibleTo("TrafficSimulation.Tests")]
```

## HTTP Contract Handling

Before implementing writes, confirm the actual API contracts from:

```text
BlazorAutoApp/Features/Books/Endpoints/BooksEndpoints.cs
BlazorAutoApp.Core/Features/Books/UseCases
BlazorAutoApp.Client/Features/Books/BooksClientService.cs
```

Implementation rules:

- Use the same DTO shape that the app expects.
- Use `System.Net.Http.Json` for JSON.
- Treat `401` and `403` as auth failures, not transient HTTP failures.
- Treat `404` after delete as success when verifying deletion.
- Do not retry creates blindly after timeout; first search by exact synthetic title.
- Do not retry updates blindly after timeout; first re-read the book.
- Do not retry deletes blindly after timeout; first re-read the book.

## Browser Auth Bootstrap Flow

Login:

1. Resolve target base URL.
2. Resolve credentials.
3. Check Playwright Chromium is installed.
4. Start browser in headless mode unless `--headed-browser`.
5. Navigate to `/Account/Login`.
6. Fill `#Input\.Email`.
7. Fill `#Input\.Password`.
8. Click button with exact name `Log in`.
9. Wait for document load.
10. Navigate to `/books`.
11. Wait for `add-book` or `user-bookcase-title`.
12. Export cookies into an `HttpClientHandler` `CookieContainer`.

Registration fallback:

1. Only run if login failed and `--register-synthetic-user` is set.
2. Navigate to `/Account/Register`.
3. Fill email, password, confirm password.
4. Click button with exact name `Register`.
5. Wait for logged-in state.
6. Export cookies.

Failure handling:

- If login fails without registration flag, exit before traffic.
- If registration fails because the account already exists, retry login once.
- If registration fails for validation reasons, print the validation summary without printing the password.
- If logged-in marker never appears, save a failure screenshot under artifacts and exit.

## Auth-Check Mode

Add explicit auth-check mode so the auth bootstrap can be tested without writes.

Command:

```powershell
.\RunSimulation.ps1 -Target local -AuthCheck
```

Behavior:

1. Resolve credentials.
2. Login or explicitly register if requested.
3. Export cookies.
4. Make authenticated `GET /api/books`.
5. Write a small report.
6. Exit.

Auth-check must not:

- create books.
- update books.
- delete books.
- run anonymous traffic.
- run browser sampler.

This mode makes the implementation incremental and avoids the contradiction where `-Writes` would be needed before writes exist.

## Authenticated HTTP Scenarios

Scenario names:

```text
authenticated_book_list
authenticated_book_create
authenticated_book_verify_created
authenticated_book_update
authenticated_book_verify_updated
authenticated_book_delete
authenticated_book_verify_deleted
authenticated_book_cleanup
```

Smoke profile with writes:

1. Auth bootstrap.
2. Authenticated `GET /api/books`.
3. Create one synthetic book.
4. Verify it appears.
5. Update its title.
6. Verify update appears.
7. Delete it.
8. Verify it is gone.
9. Cleanup scan for current run.
10. Report zero leftovers.

Demo profile with writes:

1. Continue V1 anonymous traffic.
2. Add authenticated book list traffic.
3. Keep a small working set of 1-5 synthetic books.
4. Create/update/delete at the write budget.
5. Delete all working-set books before run end.
6. Cleanup scan.
7. Report zero leftovers.

Soak-lite with writes:

- Allowed only at conservative write budgets.
- Prefer longer read traffic with occasional create/update/delete.
- Cleanup at the end is mandatory.

Burst:

- Remains local-only.
- Writes should be disabled in burst unless a later explicit decision changes this.

## Browser Sampler

Browser sampler default:

```text
disabled
```

When enabled:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -BrowserSampler -Duration 60s
```

Rules:

- One browser context.
- One browser user.
- No browser-generated load.
- Browser journey frequency is separate from HTTP RPS.
- Browser sampler failure fails the run.
- Failure screenshots are written under the run artifact directory.

Journey:

1. Reuse authenticated browser context when possible.
2. Navigate to `/books`.
3. Assert `user-bookcase-title`.
4. Click `add-book`.
5. Assert `book-page-editor`.
6. Fill `book-title`.
7. Fill `book-author`.
8. Fill `book-url`.
9. Click `book-save`.
10. Open created book by role link name `<title> details`.
11. Assert `book-page-view`.
12. Click `book-edit-pencil`.
13. Update title.
14. Click `book-save`.
15. Open updated book.
16. Click `book-delete`.
17. Click `book-delete-confirm`.
18. Assert updated book link is hidden.
19. Run HTTP cleanup scan.

The browser-created book must use the same synthetic naming rules and be included in cleanup totals.

## Report Schema

Extend `summary.json` without breaking V1 readers.

Add top-level sections:

```json
{
  "auth": {
    "enabled": true,
    "mode": "browser-login",
    "target": "local",
    "emailHash": "12-char-hash",
    "loginSucceeded": true,
    "registeredUser": false,
    "bootstrapDurationMs": 1234,
    "authenticatedApiCheckSucceeded": true
  },
  "writes": {
    "enabled": true,
    "runId": "20260530T211500Z-ab12cd34",
    "created": 3,
    "updated": 3,
    "deleted": 3,
    "verifiedCreated": 3,
    "verifiedUpdated": 3,
    "verifiedDeleted": 3,
    "cleanupAttempted": true,
    "cleanupDeleted": 0,
    "leftoverSyntheticBooks": 0,
    "cleanupSucceeded": true,
    "keptSyntheticData": false
  },
  "browserSampler": {
    "enabled": true,
    "journeysStarted": 1,
    "journeysSucceeded": 1,
    "journeysFailed": 0,
    "screenshotDirectory": "redacted-or-relative-path"
  }
}
```

Markdown report must include:

- target.
- profile.
- base URL.
- auth mode.
- redacted account identity.
- whether registration happened.
- write mode status.
- run ID.
- created, updated, deleted, and cleanup counts.
- leftover count.
- unexpected `429` count.
- `5xx` count.
- browser sampler result.
- report artifact location.
- recommended Grafana time range.

Reports must not include:

- password.
- cookies.
- auth headers.
- raw storage state.
- full local absolute paths if they reveal usernames and are not needed.

## Observability Expectations

After a successful V2 demo run, Grafana should show:

- request traffic on anonymous pages and APIs.
- authenticated `GET /api/books`.
- authenticated `POST`, `PUT`, and `DELETE` for `/api/books`.
- traces for authenticated book operations.
- logs for created, updated, and deleted books.
- PostgreSQL activity from real app writes.
- Redis activity from cache invalidation and reads.
- app-node labels across whichever deployment is targeted.

Do not add high-cardinality labels for:

- run ID.
- synthetic title.
- synthetic URL.
- book ID.
- user ID.
- email.
- trace ID.

Keep run-level detail in simulator reports, not in Prometheus labels.

## Tests

Add a test project if the implementation grows beyond trivial option parsing:

```text
Tools/TrafficSimulation.Tests/TrafficSimulation.Tests.csproj
```

Recommended tests:

```text
SimulationOptionsAuthTests
  auth-check parses
  writes require write gate
  cleanup-only requires write gate
  deployed writes require deployed and write gates
  keep-synthetic-data requires --yes
  auth password is never accepted as plain CLI value

SyntheticBookNamingTests
  generated titles include target and run ID
  generated URLs use simulation.invalid
  invalid titles are refused for deletion

SyntheticBookCleanupTests
  deletes only safe synthetic books
  refuses non-synthetic books
  refuses synthetic title with non-simulation URL
  returns cleanup failure on leftovers

RateBudgetTests
  write operations consume write budget
  reads consume API budget
  retry-after pauses the scenario class

ReportRedactionTests
  password never appears
  cookies never appear
  email hash appears instead of raw email
```

Gated integration tests:

- Only run with an explicit environment variable such as `RUN_SIMULATION_E2E=1`.
- Use local target only.
- May verify auth-check and one create/update/delete cleanup cycle.

## Documentation Updates

Update:

```text
docs/SimulationGuide.md
Tools/TrafficSimulation/README.md
docs/ObservabilityGuide.md
RunSimulation.ps1 -Help output
```

Docs must explain:

- V1 read-only mode.
- V2 auth-check mode.
- how to install Playwright browsers.
- how to set simulator credentials.
- how to create one persistent simulator account.
- how to run local write smoke.
- how to run cleanup-only.
- deployed gates.
- why the simulator does not bypass rate limits.
- what artifacts are written.
- what to do if cleanup fails.

Do not bury safety gates in a later section. Commands that mutate data must show `-AllowWrite`.

## Implementation Phases

Each phase should be completed, tested, and marked done before starting the next.

### Phase 0 - Audit And Baseline

Status: done on 2026-05-30.

Purpose: confirm the code still matches this plan before editing.

Checklist:

- [x] Run `git status --short` and identify unrelated changes.
- [x] Confirm auth selectors.
- [x] Confirm book selectors.
- [x] Confirm API DTOs and endpoints.
- [x] Confirm V1 read-only simulator still builds.
- [x] Confirm `artifacts/` is ignored.

Verification:

```powershell
rg -n "data-testid=\"add-book\"|data-testid=\"book-save\"|data-testid=\"book-delete-confirm\"|#Input" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Test
dotnet build .\BlazorAutoApp.sln --no-restore
.\RunSimulation.ps1 -Help
```

Done when:

- selectors and endpoints are confirmed.
- V1 commands still work.

### Phase 1 - CLI, Gates, And Tests

Status: done on 2026-05-30.

Purpose: add the safe command shape before adding browser or write behavior.

Checklist:

- [x] Add `--auth-check`.
- [x] Add `--auth-email`.
- [x] Add `--auth-password-env`.
- [x] Add `--register-synthetic-user`.
- [x] Add `--keep-synthetic-data`.
- [x] Add `--install-browsers`.
- [x] Add wrapper switches.
- [x] Implement validation gates.
- [x] Add unit tests for option validation.
- [x] Keep reserved V2 modes non-destructive until their implementation exists.

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
.\RunSimulation.ps1 -Help
.\RunSimulation.ps1 -Target cloud-edge -Writes
.\RunSimulation.ps1 -Target local -CleanupOnly
```

Expected:

- help shows new options.
- cloud write command fails before traffic because gates are missing.
- cleanup-only fails before traffic because write gate is missing.
- V1 parse/help behavior still works. Full read-only smoke is verified in Phase 6 when the local app is running.

### Phase 2 - Playwright Install And Auth-Check

Status: done on 2026-05-30.

Purpose: prove real login and authenticated API access without creating books.

Checklist:

- [x] Add `Microsoft.Playwright`.
- [x] Add browser install command.
- [x] Implement browser login.
- [x] Implement explicit registration fallback.
- [x] Export cookies into authenticated `HttpClient`.
- [x] Implement `--auth-check`.
- [x] Add failure screenshots under artifacts.
- [x] Redact credentials and cookies.

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln --no-restore
.\RunSimulation.ps1 -InstallBrowsers
.\RunSimulation.ps1 -Target local -AuthCheck
dotnet test .\BlazorAutoApp.sln --no-build
```

Expected:

- browser install succeeds or prints exact fix.
- auth-check logs in as local seeded user.
- authenticated `GET /api/books` succeeds.
- no books are created, updated, or deleted.

### Phase 3 - Authenticated CRUD And Cleanup

Status: done on 2026-05-30.

Purpose: add safe synthetic book writes through the real API.

Checklist:

- [x] Add authenticated books client.
- [x] Add synthetic naming.
- [x] Add ledger.
- [x] Add create scenario.
- [x] Add verify-created scenario.
- [x] Add update scenario.
- [x] Add verify-updated scenario.
- [x] Add delete scenario.
- [x] Add verify-deleted scenario.
- [x] Add cleanup scan.
- [x] Add cleanup-only mode.
- [x] Add cancellation cleanup best effort.
- [x] Return exit code `4` on leftovers.
- [x] Add tests for deletion safety.

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln --no-restore
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
.\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
dotnet test .\BlazorAutoApp.sln --no-build
```

Expected:

- write smoke creates, verifies, updates, verifies, deletes, and verifies deletion.
- cleanup-only reports zero leftovers.
- unexpected `429` equals zero.
- `5xx` equals zero.
- report contains auth/write/cleanup sections.

### Phase 4 - Browser Sampler

Status: done on 2026-05-30.

Purpose: prove the real UI add/edit/delete journey at low frequency.

Checklist:

- [x] Implement `--browser-sampler`.
- [x] Reuse auth browser context when possible.
- [x] Add one UI journey using existing selectors.
- [x] Include browser-created book in ledger.
- [x] Capture screenshot only on failure.
- [x] Add browser sampler report section.

Verification:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -BrowserSampler -Duration 60s
.\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
```

Expected:

- UI journey succeeds.
- browser-created book is deleted.
- cleanup-only reports zero leftovers.

### Phase 5 - Reports And Docs

Status: done on 2026-05-30.

Purpose: make the feature usable without reading source code.

Checklist:

- [x] Update `summary.json`.
- [x] Update `summary.md`.
- [x] Update `docs/SimulationGuide.md`.
- [x] Update `Tools/TrafficSimulation/README.md`.
- [x] Update `docs/ObservabilityGuide.md`.
- [x] Update help text.
- [x] Document failure recovery.

Verification:

```powershell
.\RunSimulation.ps1 -Help
rg -n "AuthCheck|CleanupOnly|SIMULATION_AUTH_EMAIL|SIMULATION_AUTH_PASSWORD|InstallBrowsers|BrowserSampler" docs Tools RunSimulation.ps1
```

Expected:

- docs contain direct copyable commands.
- mutating commands show `-AllowWrite`.
- deployed commands show `-AllowDeployed`.
- cleanup recovery is documented.

### Phase 6 - Full Local Acceptance

Status: done on 2026-05-30.

Purpose: prove V2 locally before deployed use.

Commands:

```powershell
.\RunLocal.ps1 -NoBrowser -Observability
.\RunSimulation.ps1 -Target local -Profile smoke
.\RunSimulation.ps1 -Target local -AuthCheck
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -BrowserSampler -Duration 60s
.\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
```

Expected:

- V1 read-only still passes.
- auth-check passes.
- write smoke passes.
- browser sampler passes.
- cleanup-only reports zero leftovers.
- tests and build pass.
- Grafana shows authenticated book activity.

### Phase 7 - Optional Deployed Acceptance

Status: not started.

Purpose: prove Cloud or LocalCluster only after local acceptance passes.

Cloud commands:

```powershell
$env:SIMULATION_AUTH_EMAIL = "bookscloud-sim@example.com"
$env:SIMULATION_AUTH_PASSWORD = "<secret>"

.\RunSimulation.ps1 -Target cloud-edge -AuthCheck -AllowDeployed
.\RunSimulation.ps1 -Target cloud-edge -Profile smoke -Writes -Cleanup -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target cloud-edge -CleanupOnly -AllowDeployed -AllowWrite
```

LocalCluster commands:

```powershell
$env:SIMULATION_AUTH_EMAIL = "books-localcluster-sim@example.com"
$env:SIMULATION_AUTH_PASSWORD = "<secret>"

.\RunSimulation.ps1 -Target localcluster-edge -AuthCheck -AllowDeployed
.\RunSimulation.ps1 -Target localcluster-edge -Profile smoke -Writes -Cleanup -AllowDeployed -AllowWrite -Duration 60s
.\RunSimulation.ps1 -Target localcluster-edge -CleanupOnly -AllowDeployed -AllowWrite
```

Expected:

- no deployed write happens without gates.
- deployed auth-check passes.
- deployed write smoke leaves zero leftovers.
- reports contain no secrets.
- unexpected `429` equals zero.
- `5xx` equals zero.

## Failure Modes And Required Behavior

Missing browser:

```text
exit before login
message: run .\RunSimulation.ps1 -InstallBrowsers
no writes attempted
```

Missing deployed gate:

```text
exit before login
message: target requires -AllowDeployed or SIMULATION_ALLOW_DEPLOYED=1
```

Missing write gate:

```text
exit before login
message: writes/cleanup/register require -AllowWrite or SIMULATION_ALLOW_WRITE=1
```

Bad credentials:

```text
exit before traffic
no password in output
if register flag absent, tell user to verify account or use -RegisterSyntheticUser
```

Registration validation error:

```text
exit before traffic
show validation text without password
no retry loop
```

Create timeout:

```text
search by exact synthetic title before retry
avoid duplicate book creation
```

Delete timeout:

```text
re-read book list
if gone, count as deleted
if still present, retry within budget
```

Cleanup leftovers:

```text
write report
print cleanup-only command
exit code 4
```

Ctrl+C:

```text
stop scheduling new work
attempt cleanup for ledger books
write partial report
exit success only if cleanup verified and thresholds passed
```

## Done Definition

V2 is complete only when all are true:

- V1 read-only smoke still works.
- `-AuthCheck` works locally without writes.
- `-Writes -AllowWrite` works locally.
- `-BrowserSampler` works locally.
- `-CleanupOnly -AllowWrite` leaves zero V2 synthetic books.
- Missing gates fail before browser startup and before writes.
- Deployed write mode requires both deployed and write gates.
- Reports include auth, write, cleanup, and browser sampler sections.
- Reports contain no passwords, cookies, or raw auth state.
- Documentation has copyable commands.
- Tests cover option gates, naming safety, cleanup safety, report redaction, and rate budgets.
- Full local acceptance commands pass.

## Handoff Rules For Implementation

Any agent implementing this plan must:

1. Read this whole file first.
2. Preserve V1 behavior.
3. Implement one phase at a time.
4. Run the verification commands for each phase.
5. Mark phase status as done only after verification.
6. Never run deployed writes without explicit user intent.
7. Never store or print secrets.
8. Never broaden cleanup beyond the safe V2 synthetic filters.
9. Stop and fix the plan if the app behavior no longer matches the assumptions above.
