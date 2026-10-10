# Website Traffic Simulation Plan

Status: V1 read-only implementation completed on 2026-05-30. Authenticated write traffic and browser sampling remain future phases.

V2 authenticated simulation plan: `Plans/SimulationV2Authenticated.md`.

Last updated: 2026-05-30.

Accepted recommendation: build an in-repo .NET console tool at `Tools/TrafficSimulation` as the primary traffic simulator. Use HTTP-level traffic for volume, and add a small optional Playwright browser sampler only for realistic user journeys that need a real browser.

This document is intended to be detailed enough that another agent can implement the simulator without re-deciding the architecture.

Important repo note: `/Plans/` is currently ignored by `.gitignore`. This file is intentionally created where requested, but it will not be committed unless the repo's ignore rules are changed or the plan is moved into `docs/`.

## Executive Summary

The simulator should make the Books app look alive in Grafana and help prove that local, LocalCluster, and Cloud deployments handle normal traffic. It is not a DDoS tool and it is not a formal capacity test in V1.

The best first version is:

```text
repo root
  Tools/
    TrafficSimulation/
      TrafficSimulation.csproj
      Program.cs
      ...
```

It should be added to `BlazorAutoApp.sln` so compile errors are caught by normal builds:

```powershell
dotnet sln .\BlazorAutoApp.sln add .\Tools\TrafficSimulation\TrafficSimulation.csproj
```

The normal user-facing command should be a wrapper script, not a raw `dotnet run`:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke
```

The first impressive demo command should be:

```powershell
.\RunLocal.ps1 -NoBrowser -Observability -TimeoutSeconds 240
.\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
```

After that, Grafana should show fresh app requests, logs, traces, app-node labels, PostgreSQL activity, Redis activity, and eventually book-specific CRUD metrics.

The underlying `dotnet run --project .\Tools\TrafficSimulation -- ...` command should still work, but it is the implementation detail. Users should normally use `RunSimulation.ps1`, just like they use `RunLocal.ps1` for local startup.

## Handoff Instructions

If another agent implements this plan, it must follow these instructions:

1. Read this whole file before editing.
2. Do not replace the chosen V1 architecture with k6, NBomber, JMeter, a bash loop, a hosted service, or a permanent background bot.
3. Do not add servers, nodes, Cloudflare API requirements, public observability ports, or deployment topology changes.
4. Do not add a production-only test backdoor or bypass authentication.
5. Do not run high-volume traffic against LocalCluster or Cloud unless a later guide explicitly says to do that.
6. Do not commit generated reports, cookies, credentials, state files, screenshots, trace dumps, local `.env` files, or simulator temp files.
7. Do not use synthetic run IDs, book IDs, user IDs, URLs, emails, trace IDs, IP addresses, or user agents as Prometheus labels, Loki labels, or OpenTelemetry resource attributes.
8. Before editing, run `git status --short` and preserve unrelated user changes.
9. Every implementation phase must end with a verification command and a result note.
10. If a check fails, fix the implementation or update this plan before moving to the next phase.

## Current Repo Structure

The simulator should fit beside the existing projects, not inside the production app:

```text
BlazorAutoApp/
  BlazorAutoApp/              # server app
  BlazorAutoApp.Client/       # Blazor client UI
  BlazorAutoApp.Core/         # shared domain/contracts
  BlazorAutoApp.Test/         # unit/integration/E2E tests
  Deployment/                 # LocalCluster, Cloud, Common deployment assets
  docker/                     # local observability and Docker support
  docs/                       # operator docs intended for source control
  Plans/                      # local planning docs, currently gitignored
  Tools/                      # proposed developer/operator tools
    TrafficSimulation/        # proposed simulator console app
  RunSimulation.ps1           # proposed friendly PowerShell wrapper
  RunSimulation.cmd           # optional Windows cmd wrapper matching RunLocal.cmd style
```

The simulator is not:

- a new application layer.
- a Blazor project.
- a production runtime dependency.
- a deployment role.
- an observability backend component.

It is:

- a source-controlled developer/operator tool.
- buildable through the solution.
- runnable from CurrentPC, WSL, PowerShell, CI, or a control machine if needed.
- target-aware for local, LocalCluster, and Cloud.

The wrapper script is:

- the recommended user entrypoint.
- responsible for friendly parameter names, repo-root detection, common presets, and clear errors.
- not responsible for implementing simulation behavior. The .NET tool owns the behavior.

## Current App Facts

The app already has enough reachable surfaces for meaningful traffic.

Public UI routes discovered from the app:

```text
/
/books
/books/{Id:int}
/books/author/{SeedKey}
/books/design-demos
/books/design-demos/{DesignId}
/Account/Login
/Account/Register
/not-found
```

Anonymous read API:

```text
GET /api/author-books/
GET /api/author-books/{id:int}
```

Authenticated user-book API:

```text
GET    /api/books/
GET    /api/books/{id:int}
POST   /api/books/
PUT    /api/books/{id:int}
DELETE /api/books/{id:int}
```

Health endpoints:

```text
GET /health/live
GET /health/ready
GET /health
```

Telemetry already available:

- ASP.NET Core request metrics and traces through OpenTelemetry.
- Serilog logs forwarded into Loki when observability is enabled.
- custom books telemetry from `BooksTelemetry`:
  - `books_operations_total`
  - `books_operation_duration_milliseconds`
- target/node/service labels in observability dashboards.
- PostgreSQL and Redis exporter metrics when observability is enabled.

Rate limiting already available:

- global limiter:
  - default `600` requests per `60` seconds.
  - fixed window.
  - partitioned by authenticated user ID or remote IP.
- API limiter:
  - default `60` requests per `60` seconds.
  - sliding window.
  - applies to `/api/books` and `/api/author-books`.
  - partitioned by authenticated user ID or remote IP.
- authentication write limiter:
  - default `120` non-GET `/Account` requests per `300` seconds.
  - fixed window.
  - partitioned by authenticated user ID or remote IP.
- all current limiter queues are `0`.
- rejected requests return `429 Too Many Requests` with `Retry-After`.

Authentication facts:

- local `Development` and `Docker` environments seed local login users.
- deployed environments do not seed local login users.
- registration currently does not require email confirmation.
- `/api/books` requires a real authenticated application cookie.
- `/api/author-books` is anonymous.

Important implication:

- V1 should be anonymous/read-only first.
- Authenticated write traffic should be a later gated phase.
- Browser automation is the cleanest way to create or log in a synthetic user without hand-rolling antiforgery details.
- The simulator must not treat `MaxRps` as one undifferentiated budget. API, auth, and general page traffic need separate pacing so the simulator does not get stopped by the app's own limiter.

## Accepted Architecture

The simulator should have three layers:

```text
Command line
  parses target/profile/options
  applies safety gates
  prints resolved plan before running

Scenario runner
  schedules scenario execution
  enforces duration, max RPS, users, think time, cancellation, and stop conditions
  records per-scenario latency/status/error results

Scenario clients
  anonymous HTTP client for public pages and author-book API
  authenticated HTTP client later for /api/books
  optional Playwright sampler later for real browser journeys
```

Recommended implementation folders:

```text
Tools/TrafficSimulation/
  TrafficSimulation.csproj
  Program.cs
  Options/
    SimulationOptions.cs
    TargetProfile.cs
    TrafficProfile.cs
    SafetyOptions.cs
  Running/
    ScenarioRunner.cs
    ScenarioSchedule.cs
    RateLimiter.cs
    RateLimitBudget.cs
    RetryAfterBackoff.cs
    StopConditions.cs
  Scenarios/
    ScenarioCatalog.cs
    AnonymousPageScenarios.cs
    AuthorBookApiScenarios.cs
    HealthScenarios.cs
    AuthenticatedBookScenarios.cs
  Http/
    HttpScenarioClient.cs
    HttpResult.cs
    AuthorBookContracts.cs
    UserBookContracts.cs
  Auth/
    SyntheticUserSession.cs
    CookieJar.cs
  Data/
    SyntheticBookTracker.cs
    SyntheticBookNaming.cs
  Reporting/
    SimulationReport.cs
    SummaryJsonWriter.cs
    SummaryMarkdownWriter.cs
  Safety/
    SafetyGate.cs
    TargetSafety.cs
  Scripts/
    RunSimulationExamples.md
  README.md
```

Do not over-abstract the first implementation. Keep the public types small and only split files when each file has a clear responsibility.

## Why This Architecture

This is the right first option because:

- The repo is a .NET app, so a .NET console tool fits the existing toolchain.
- The first goal is observable realistic traffic, not maximum throughput.
- HTTP-level traffic is cheap enough to run for demos and smoke checks.
- Playwright is valuable, but it is too heavy to be the main volume generator.
- k6 and NBomber are good tools, but they add toolchain and licensing decisions before we need them.
- The simulator can use existing deployment URLs without changing LocalCluster or Cloud.
- The implementation can be incremental: read-only first, auth later, browser sampler later.

Design principle:

```text
Use HTTP for traffic volume.
Use Playwright for user authenticity.
Use Grafana for observing the result.
Do not fake telemetry.
Stay below normal rate limits unless explicitly testing them.
```

## Non-Goals

Do not build these in V1:

- a DDoS tool.
- a high-RPS production load test.
- a new public endpoint only for simulation.
- a permanent traffic bot.
- fake metrics inserted directly into Prometheus.
- direct database writes for normal scenarios.
- a fifth Cloud node or dedicated load generator server.
- a Cloudflare API integration.
- browser-only load generation.
- a simulator that requires real user data.
- a tool that edits deployment state.

## Tool Alternatives

### Option A: Custom .NET HTTP Simulator

Decision: accepted for V1.

What it is:

- A small console app that sends HTTP requests using `HttpClient`.
- It models user journeys with scenario weights, think time, max RPS, duration, and hard stop conditions.
- It writes JSON and Markdown summaries under an ignored artifacts folder.

Strengths:

- Fits the repo and existing .NET build.
- No extra load-test product dependency.
- No new service to deploy.
- Easy to run from PowerShell, WSL, CI, or a control machine.
- Good enough for local demos, deployed smoke traffic, observability verification, and low-rate soak-lite runs.
- Can use simple DTOs for API responses while avoiding deep coupling to app internals.

Weaknesses:

- We must implement scheduling, summaries, and thresholds.
- It will not be as feature-rich as a dedicated load-testing product.
- It does not prove browser rendering unless paired with Playwright.

Use for:

- V1 traffic simulation.
- dashboard warmup.
- low-rate deployed smoke checks.
- local observability confidence.

### Option B: k6

Decision: good later option, not V1.

What it is:

- A mature load and performance testing tool from Grafana Labs.
- Scripts are JavaScript or TypeScript.
- It supports scenarios, executors, thresholds, and browser modules.

Strengths:

- Excellent HTTP load-testing model.
- Strong thresholds and executors.
- Natural Grafana ecosystem fit.
- Easy to run from Docker.

Weaknesses:

- Adds JavaScript/TypeScript test scripts to a C# repo.
- Adds install/documentation work.
- The current k6 repository is AGPL-3.0 licensed, which should be reviewed before company adoption.
- Browser testing through k6 should still not be used as the default high-volume path.

Use later if:

- we need formal performance testing beyond demo/smoke traffic.
- the team accepts the license/toolchain.
- a standard load-test report is more important than keeping the implementation small.

### Option C: NBomber

Decision: technically strong, but not V1 because licensing matters.

What it is:

- A code-first .NET load-testing framework.
- It supports open and closed workload models, thresholds, reports, and scenario composition.

Strengths:

- C# fits the repo.
- Good scenario and load model.
- Built-in reports and thresholds.
- Good for formal .NET performance tests.

Weaknesses:

- NBomber documentation says the free version is personal-use only and organizational use requires a business or enterprise license.
- It is more machinery than needed for the first simulator.
- It adds a specialized dependency where a small tool is enough.

Use later if:

- the company wants formal C# load testing.
- a license decision has been made.
- reports and thresholds become more important than minimal dependency footprint.

### Option D: Playwright-Only Simulation

Decision: do not use as the main simulator.

What it is:

- Browser automation that drives real Chromium/Firefox/WebKit pages.

Strengths:

- Best for realistic user journeys.
- Exercises Blazor rendering, forms, navigation, auth cookies, and client-side behavior.
- Existing E2E patterns already use Playwright.

Weaknesses:

- Too heavy for traffic volume.
- Slower than HTTP traffic.
- More fragile than HTTP-level scenarios.
- Can create noisy and expensive runs if misused.

Use for:

- optional V1.2 browser sampler.
- auth bootstrap.
- one or two real UI CRUD journeys.

### Option E: Bash/curl Loop

Decision: do not use except for tiny manual checks.

Strengths:

- Fast to write.
- No project setup.

Weaknesses:

- Poor state handling.
- Poor reporting.
- Poor cleanup.
- Easy to accidentally create unsafe loops.
- Hard to maintain once auth, cookies, randomization, cleanup, or profiles are needed.

## Target Modes

The simulator should support these target modes.

### local

Default base URL:

```text
https://localhost:7186
```

Purpose:

- default development target.
- observability dashboard warmup.
- smoke testing.
- local write traffic after explicit gate.

Rules:

- default target if none is supplied.
- write traffic still requires `SIMULATION_ALLOW_WRITE=1`.
- should tolerate local dev certificates or document how to trust them.

### localcluster-edge

Default base URL:

```text
https://books.example.com
```

Purpose:

- exercise Cloudflare, cloudflared, Caddy, app nodes, PostgreSQL, Redis, logs, metrics, and traces.
- demo deployed observability on the LocalCluster environment.

Rules:

- requires `SIMULATION_ALLOW_DEPLOYED=1`.
- defaults to low RPS.
- writes disabled unless explicitly enabled.
- should detect Cloudflare challenge pages and stop cleanly.

### cloud-edge

Default base URL:

```text
https://bookscloud.example.com
```

Purpose:

- exercise Hetzner Cloud deployment through the public edge.
- demo the separate cloud environment.

Rules:

- requires `SIMULATION_ALLOW_DEPLOYED=1`.
- defaults to low RPS.
- writes disabled unless explicitly enabled.
- should keep traffic short because Cloud is cost-sensitive and disposable.

### origin-via-tunnel

Default base URL:

```text
http://127.0.0.1:<local-forwarded-port>
```

Purpose:

- optional later diagnostic mode.
- useful when public Cloudflare behavior interferes with CurrentPC or CI checks.
- should still hit Caddy, not individual app containers, unless diagnosing app-node imbalance.

Rules:

- requires the operator to create an SSH tunnel first.
- should clearly print that this bypasses public Cloudflare edge behavior.
- should not become the default deployed mode.

## Traffic Profiles

Profiles are presets. Operators can override duration, users, and max RPS, but safety gates still apply.

Important: profile `max_rps` is the total requested pace, not permission to exceed route-specific limiter budgets. The scheduler must apply a second layer of budgets for API and authentication traffic.

Current safe default budgets derived from app defaults:

```text
global limiter default:
  app default: 600 / 60s = 10 requests/sec per IP or user
  simulator normal budget: <= 50 percent of this unless overridden

api limiter default:
  app default: 60 / 60s = 1 request/sec per IP or user
  simulator normal budget: <= 80 percent of this, so 0.8 API requests/sec

authentication write limiter default:
  app default: 120 / 300s = 0.4 auth write requests/sec per IP or user
  simulator normal budget: <= 50 percent of this, so 0.2 auth writes/sec
```

This means a local demo can run `MaxRps 3`, but the API subset must still be paced below roughly `0.8 RPS` unless the operator explicitly chooses a rate-limit test. Extra traffic should shift toward normal page browsing instead of hammering `/api/*`.

### smoke

Purpose:

- prove the simulator works.
- populate dashboards enough to confirm signal flow.
- safe for local and CI if the app is already running.

Defaults:

```text
duration: 90 seconds
max_rps: 1
api_rps_budget: 0.5
auth_write_rps_budget: 0.1
virtual_users: 1-2
writes: disabled
browser_sampler: disabled
stop_on_first_5xx: true
```

Expected result:

- zero unexpected 5xx responses.
- no synthetic data left behind.
- basic request metrics, logs, and traces appear.

### demo

Purpose:

- make Grafana dashboards look alive before showing the system.
- exercise read paths, cache paths, ingress, app nodes, PostgreSQL, Redis, logs, metrics, and traces.

Defaults:

```text
duration: 10-15 minutes
max_rps: 3 local, 2 deployed
api_rps_budget: 0.8 local, 0.5 deployed
auth_write_rps_budget: 0.2 local, 0.1 deployed
virtual_users: 3-8
writes: disabled by default
browser_sampler: optional, 1 browser user
stop_on_5xx_rate: > 1 percent for 60 seconds
```

Expected result:

- Grafana Command Center shows request rate, latency, logs, traces, and app instances.
- Infrastructure dashboard shows app/data resource movement.
- Application and Books dashboard shows book metrics when authenticated write mode is enabled.

### soak-lite

Purpose:

- run longer low-rate traffic without pretending to be a full production capacity test.

Defaults:

```text
duration: 30-60 minutes
max_rps: 2 local, 1 deployed
api_rps_budget: 0.5 local, 0.3 deployed
auth_write_rps_budget: 0.1 local, 0.05 deployed
virtual_users: 2-5
writes: optional, very low rate
browser_sampler: disabled
```

Expected result:

- no container restarts.
- no OOMKilled containers.
- no memory growth crossing alert thresholds.
- active Prometheus series and Loki streams stay within guardrails.

### burst

Purpose:

- verify rate limiting, dashboards, and failure visibility during a short spike.

Defaults:

```text
duration: 30-90 seconds
max_rps: 10 local only by default
api_rps_budget: intentionally overrideable only with SIMULATION_ALLOW_BURST=1
virtual_users: 10-25
writes: disabled
requires: SIMULATION_ALLOW_BURST=1
```

Expected result:

- no app crash.
- 429 responses are acceptable if rate limiting is active.
- unexpected 5xx responses fail the run.

## Scenario Mix

The simulator should model realistic behavior by mixing scenarios, not by hitting one endpoint in a tight loop.

Suggested V1 read-only weights:

```text
anonymous_page_home_or_books:       25
anonymous_author_book_list_api:     15
anonymous_author_book_detail_api:   15
anonymous_author_page:              15
design_demo_page:                   10
login_or_register_page:             10
health_readiness:                    5
expected_not_found:                  5
```

These weights are starting points, not hard promises. The scheduler must downshift API scenarios when the API budget would be exceeded and fill the remaining total RPS with page scenarios.

Suggested V1.1 authenticated weights when writes are enabled:

```text
authenticated_book_list:            25
authenticated_book_detail:          20
synthetic_book_create:              10
synthetic_book_update:              10
synthetic_book_delete:               5
anonymous_author_book_list_api:     15
anonymous_pages:                    15
```

### Anonymous Page Browsing

Requests:

```text
GET /
GET /books
GET /books/author/{SeedKey}
GET /books/design-demos
GET /books/design-demos/{DesignId}
GET /Account/Login
GET /Account/Register
GET /not-found
```

Behavior:

- use realistic think time.
- discover valid author seed keys from `GET /api/author-books/`.
- choose design IDs from a static allowlist found during implementation.
- include a small amount of expected 404 traffic.
- classify expected 404s separately from failures.

### Anonymous Author Book API

Requests:

```text
GET /api/author-books/
GET /api/author-books/{id:int}
```

Behavior:

- fetch the list first.
- choose IDs from the returned list.
- ask for one impossible ID at a very low rate to prove clean not-found behavior.
- do not hammer the list endpoint so hard that it hides other signals.

### Health And Readiness

Requests:

```text
GET /health/live
GET /health/ready
```

Behavior:

- low weight only.
- readiness failures should trip a hard stop.
- health traffic should not dominate logs or metrics.

### Authenticated User Book Read

Requests:

```text
GET /api/books/
GET /api/books/{id:int}
```

Behavior:

- requires a synthetic user session.
- if the user has no books and writes are disabled, report a skipped scenario instead of failing.
- if writes are enabled, create one seed synthetic book for the run.

### Authenticated Synthetic CRUD

Requests:

```text
POST   /api/books/
PUT    /api/books/{id:int}
DELETE /api/books/{id:int}
```

Required gate:

```text
SIMULATION_ALLOW_WRITE=1
```

Synthetic prefix:

```text
[sim:{run_id}] Book {sequence}
```

Rules:

- create only synthetic books.
- update only books created by the current run or owned by the configured synthetic user and matching the synthetic prefix.
- delete only books matching the synthetic prefix.
- never modify author-seeded books.
- never modify books without the synthetic prefix.
- run cleanup on normal exit.
- support `--cleanup-only` for leftovers.

### Browser Journey Sampler

Required gate:

```text
SIMULATION_BROWSER=1
```

Use cases:

- auth bootstrap.
- one real UI browse journey.
- one low-rate create/edit/delete journey.

Rules:

- default to 1 browser user.
- hard cap at 3 browser users.
- use robust locators.
- only save screenshots/videos on failure.
- store artifacts under ignored paths.
- do not use browser journeys as the main traffic generator.

## Authentication Strategy

V1 must not solve auth. It starts anonymous and read-only.

V1.1 auth should work like this:

1. Use Playwright to register or log in through the real UI.
2. Use a generated synthetic email:

```text
sim+{target}-{run_id}@example.test
```

3. Generate a password per run unless a persistent synthetic account is explicitly configured.
4. Keep the password out of logs and reports.
5. Keep browser cookies in a temp directory.
6. If HTTP-level authenticated CRUD is needed, extract cookies from Playwright and pass them into the HTTP simulator for the current run only.
7. Delete synthetic books before exit.

Why not hand-roll login with `HttpClient` in V1:

- Identity forms use antiforgery behavior.
- Razor form details can change.
- Browser login proves the same path a real user uses.
- It avoids a brittle simulator that knows too much about auth internals.

## Safety Guardrails

The simulator must refuse unsafe defaults.

Required environment gates:

```text
SIMULATION_ALLOW_DEPLOYED=1       # required for localcluster-edge or cloud-edge
SIMULATION_ALLOW_WRITE=1          # required for POST/PUT/DELETE
SIMULATION_ALLOW_BURST=1          # required for burst profile
SIMULATION_BROWSER=1              # required for Playwright sampler
SIMULATION_ACCEPT_DATA_LOSS=1     # required only if a future broad cleanup exists
```

Hard stop conditions:

- unexpected 5xx in smoke.
- 5xx rate above 1 percent for 60 seconds in demo.
- `/health/ready` fails twice in a row.
- latency p95 exceeds configured threshold for 2 consecutive reporting windows.
- target returns repeated Cloudflare managed challenge responses.
- cleanup ownership cannot be proven for a book scheduled for deletion.
- cancellation is requested.

Rate-limit behavior:

- Normal `smoke`, `demo`, and `soak-lite` profiles should avoid `429`, not rely on it.
- API calls must be paced by an API-specific token budget below the app's `RateLimiting:Api` limit.
- account POST/register/login flows must be paced by an auth-write-specific budget below `RateLimiting:Authentication`.
- if a `429` happens anyway, the simulator must read `Retry-After`, pause that scenario class, and record the event.
- a single unexpected `429` in `smoke` should fail the run after writing the report.
- repeated unexpected `429` responses in `demo` should fail the run because the simulator is no longer producing normal traffic.
- `429` is expected only when `--allow-rate-limit` or `burst` mode is explicitly enabled.
- `burst` mode should report `429` separately and should not count it as app failure unless the operator did not opt into rate-limit testing.

Deployed safety budgets:

```text
localcluster-edge smoke:
  max_rps <= 1
  duration <= 2m

localcluster-edge demo:
  max_rps <= 2
  duration <= 15m

cloud-edge smoke:
  max_rps <= 1
  duration <= 2m

cloud-edge demo:
  max_rps <= 2
  duration <= 15m

deployed burst:
  disabled unless explicitly added in a later plan
```

The simulator must print this before sending traffic:

```text
target
base URL
profile
duration
max RPS
virtual users
write mode
browser mode
cleanup mode
report directory
resolved safety gates
```

For deployed targets, it should require an explicit typed confirmation if either of these is true:

  - `--writes` is enabled.
  - `--max-rps` exceeds the default deployed profile limit.

## Rate Limiting Strategy

The simulator must be friendly to the app's own rate limiting. Otherwise it will mostly measure `429 Too Many Requests`, not real app behavior.

Current app defaults:

```text
global:
  600 requests / 60 seconds
  fixed window
  applies broadly
  partition: authenticated user ID, otherwise remote IP

api:
  60 requests / 60 seconds
  sliding window
  applies to /api/books and /api/author-books
  partition: authenticated user ID, otherwise remote IP

authentication:
  120 non-GET /Account requests / 300 seconds
  fixed window
  partition: authenticated user ID, otherwise remote IP

queue:
  0 for all policies
```

Design requirements:

- Keep separate budgets for:
  - total traffic.
  - API traffic.
  - authentication write traffic.
  - deployed public edge traffic.
- The scheduler must not let a high total `MaxRps` accidentally exceed the API budget.
- Use a central rate-budget component, not per-scenario `Task.Delay` guesses.
- Back off based on the `Retry-After` header if `429` is returned.
- Report `429` counts separately:
  - expected `429` from burst/rate-limit tests.
  - unexpected `429` from normal demo/smoke traffic.
- Normal dashboard demo traffic should keep `429` at zero.

Implementation sketch:

```text
Scenario is selected
  -> classify as page, api, auth_write, health, browser
  -> acquire total budget token
  -> acquire class-specific budget token when applicable
  -> send request
  -> if 429:
       read Retry-After
       pause that class budget
       record rate-limit event
       decide whether run fails based on profile
```

Suggested default budget calculations:

```text
api_budget_per_second = min(
  user_supplied_api_budget,
  configured_api_permit_limit / configured_api_window_seconds * 0.8)

auth_write_budget_per_second = min(
  user_supplied_auth_write_budget,
  configured_auth_permit_limit / configured_auth_window_seconds * 0.5)

global_budget_per_second = min(
  max_rps,
  configured_global_permit_limit / configured_global_window_seconds * 0.5)
```

If the simulator cannot read the target's runtime rate-limit config, it must use conservative defaults:

```text
api_budget_per_second: 0.5 deployed, 0.8 local
auth_write_budget_per_second: 0.1 deployed, 0.2 local
global_budget_per_second: min(max_rps, 5 local, 2 deployed)
```

Important: do not evade the limiter by creating many synthetic users or spoofing `X-Forwarded-For`. The simulator should model real users, not bypass protection. Multiple users are allowed for realistic browser/session behavior later, but not to multiply API throughput.

Run summary should include:

```text
rate_limit:
  expected_429: count
  unexpected_429: count
  retry_after_backoffs: count
  max_retry_after_seconds: number
  api_budget_rps: number
  auth_write_budget_rps: number
```

## Observability Expectations

Each run should produce a local report with:

- generated `run_id`.
- target.
- base URL.
- profile.
- start/end time.
- duration.
- max RPS.
- write mode.
- browser mode.
- scenario counts.
- status code counts.
- expected 4xx count.
- unexpected 4xx count.
- 5xx count.
- p50/p95/p99 latency by scenario and overall.
- sanitized error samples.
- synthetic users created.
- synthetic books created, updated, deleted, and left behind.
- cleanup result.
- suggested Grafana time range.

Report paths:

```text
artifacts/simulation/{yyyyMMdd-HHmmss}-{target}-{profile}/summary.json
artifacts/simulation/{yyyyMMdd-HHmmss}-{target}-{profile}/summary.md
```

`artifacts/` is already ignored by `.gitignore`.

The run ID may appear in:

- local report files.
- synthetic book titles.
- normal log message text if useful.

The run ID must not become:

- a Prometheus label.
- a Loki label.
- an OpenTelemetry resource attribute.
- a high-cardinality span attribute.

Expected Grafana result after a demo run:

- Command Center:
  - non-empty request rate.
  - latency panels show recent data.
  - app instances are visible.
  - logs and traces have recent entries.
- Application and Books:
  - read-only mode shows ASP.NET request traffic.
  - write mode shows `books_operations_total`.
- Infrastructure and Data:
  - app containers show CPU/memory/network movement.
  - PostgreSQL exporter shows activity.
  - Redis exporter shows activity.
- Logs and Traces:
  - recent traces exist for app requests.
  - health-check noise does not dominate.

## Proposed CLI

The preferred user entrypoint is `RunSimulation.ps1`.

PowerShell wrapper examples:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke

.\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3

$env:SIMULATION_ALLOW_WRITE = "1"
.\RunSimulation.ps1 -Target local -Profile demo -Writes -Cleanup

$env:SIMULATION_ALLOW_DEPLOYED = "1"
.\RunSimulation.ps1 -Target cloud-edge -Profile smoke

$env:SIMULATION_ALLOW_DEPLOYED = "1"
$env:SIMULATION_BROWSER = "1"
.\RunSimulation.ps1 -Target localcluster-edge -Profile demo -BrowserSampler
```

Bash examples:

```bash
pwsh ./RunSimulation.ps1 -Target local -Profile smoke

SIMULATION_ALLOW_WRITE=1 \
pwsh ./RunSimulation.ps1 -Target local -Profile demo -Writes -Cleanup

SIMULATION_ALLOW_DEPLOYED=1 \
pwsh ./RunSimulation.ps1 -Target cloud-edge -Profile smoke
```

Raw tool examples should still work for automation:

```powershell
dotnet run --project .\Tools\TrafficSimulation -- --target local --profile smoke
dotnet run --project .\Tools\TrafficSimulation -- --target local --profile demo --duration 10m --max-rps 3
```

CLI options:

```text
--target local|localcluster-edge|cloud-edge|origin-via-tunnel
--base-url https://...
--profile smoke|demo|soak-lite|burst
--duration 90s|10m|60m
--max-rps 2
--users 4
--seed 12345
--writes
--cleanup
--cleanup-only
--browser-sampler
--report-dir artifacts/simulation
--fail-on-5xx
--allow-rate-limit
--api-rps-budget 0.8
--auth-write-rps-budget 0.2
--yes
```

Exit codes:

```text
0  success
1  simulation completed but failed thresholds
2  invalid options or missing safety gate
3  target unavailable before traffic started
4  cleanup failed or left synthetic data behind
5  unexpected runtime error
```

## Configuration Rules

Configuration priority:

1. CLI arguments.
2. environment variables.
3. target profile defaults.
4. hardcoded safe defaults.

Environment variables:

```text
SIMULATION_ALLOW_DEPLOYED
SIMULATION_ALLOW_WRITE
SIMULATION_ALLOW_BURST
SIMULATION_BROWSER
SIMULATION_BASE_URL
SIMULATION_TARGET
SIMULATION_PROFILE
SIMULATION_MAX_RPS
SIMULATION_API_RPS_BUDGET
SIMULATION_AUTH_WRITE_RPS_BUDGET
SIMULATION_DURATION
SIMULATION_REPORT_DIR
SIMULATION_SYNTHETIC_EMAIL
SIMULATION_SYNTHETIC_PASSWORD
```

Do not read app deployment secrets directly. The simulator should not need database passwords, Redis passwords, Cloudflare tokens, Hetzner tokens, or GitHub tokens.

## RunSimulation Script

Add a root-level script:

```text
RunSimulation.ps1
```

Optional convenience wrapper:

```text
RunSimulation.cmd
```

Purpose:

- make simulation easy to run from the repo root.
- hide long `dotnet run --project` commands.
- validate common mistakes before invoking the .NET tool.
- match the ergonomics of `RunLocal.ps1`.

Required `RunSimulation.ps1` behavior:

- resolve the repo root from the script location, not from the current working directory.
- verify `Tools/TrafficSimulation/TrafficSimulation.csproj` exists.
- verify `dotnet` is available and print the SDK version.
- default `-Target local`.
- default `-Profile smoke`.
- pass through advanced options to the .NET tool.
- print the final command it will run.
- create `artifacts/simulation` if needed.
- refuse deployed targets unless `SIMULATION_ALLOW_DEPLOYED=1` is set or `-AllowDeployed` is passed.
- refuse write mode unless `SIMULATION_ALLOW_WRITE=1` is set or `-AllowWrite` is passed.
- warn when `-MaxRps` is above the safe default for the selected target.
- expose explicit rate-budget parameters so users do not have to know the raw CLI names.

Suggested parameters:

```powershell
param(
    [ValidateSet("local", "localcluster-edge", "cloud-edge", "origin-via-tunnel")]
    [string] $Target = "local",

    [ValidateSet("smoke", "demo", "soak-lite", "burst")]
    [string] $Profile = "smoke",

    [string] $BaseUrl,
    [string] $Duration,
    [double] $MaxRps,
    [int] $Users,
    [double] $ApiRpsBudget,
    [double] $AuthWriteRpsBudget,
    [switch] $Writes,
    [switch] $Cleanup,
    [switch] $CleanupOnly,
    [switch] $BrowserSampler,
    [switch] $AllowDeployed,
    [switch] $AllowWrite,
    [switch] $AllowRateLimit,
    [switch] $Yes
)
```

User-friendly examples:

```powershell
.\RunSimulation.ps1
.\RunSimulation.ps1 -Profile demo -Duration 10m
.\RunSimulation.ps1 -Target local -Profile demo -MaxRps 3 -ApiRpsBudget 0.8
.\RunSimulation.ps1 -Target cloud-edge -Profile smoke -AllowDeployed
.\RunSimulation.ps1 -Target local -Profile demo -Writes -Cleanup -AllowWrite
```

The script should not duplicate simulator logic. It should validate, translate, and invoke:

```powershell
dotnet run --project .\Tools\TrafficSimulation\TrafficSimulation.csproj -- @args
```

## Implementation Quality Bar

The implementation should:

- use `IHttpClientFactory` only if it provides clear value; otherwise one well-configured `HttpClient` per run is fine.
- set a clear user agent such as `BooksTrafficSimulation/1.0`.
- use cancellation tokens everywhere.
- use bounded concurrency.
- enforce total max RPS centrally.
- enforce API and auth-write budgets centrally.
- classify expected 404/429 responses separately from failures.
- honor `Retry-After` on `429` responses.
- never swallow cleanup failures.
- print a concise live progress line every reporting interval.
- write a final report even when the run is cancelled.
- keep generated artifacts under ignored directories.
- avoid sleeping in many scattered places; centralize pacing/think time.
- avoid global mutable state except for run-level cancellation/reporting.
- avoid introducing a new logging framework unless needed.

HTTP client guidance:

- reuse clients during a run.
- do not create a new client per request.
- set reasonable timeouts.
- do not buffer huge responses unnecessarily.
- follow redirects by default for normal page traffic.
- record final status code and whether redirects happened.
- keep cookies isolated per synthetic session.
- do not spoof `X-Forwarded-For` to bypass app rate limits.

## Implementation Phases

### Phase 0: Contract And Safety Review

Status: not started.

Work:

- [ ] Confirm route/API list still matches the current repo.
- [ ] Confirm registration still does not require email confirmation.
- [ ] Confirm deployed synthetic user policy is acceptable.
- [ ] Confirm rate limiter behavior for API endpoints.
- [ ] Record current global/API/auth rate-limit defaults in the simulator README.
- [ ] Confirm `artifacts/simulation` is ignored.
- [ ] Decide whether this plan should stay under ignored `/Plans/` or move to `docs/`.

Verification:

```powershell
rg -n "Map(Get|Post|Put|Delete)|@page|BooksTelemetry" BlazorAutoApp BlazorAutoApp.Client
rg -n "RequireConfirmedAccount|SeedLocalLoginAccounts|RequireAuthorization" BlazorAutoApp
git status --short
```

Acceptance:

- current repo facts are still valid.
- no implementation starts until safety gates are understood.

### Phase 1: Read-Only .NET Simulator

Status: not started.

Work:

- [ ] Create `Tools/TrafficSimulation`.
- [ ] Add it to `BlazorAutoApp.sln`.
- [ ] Create `RunSimulation.ps1`.
- [ ] Optionally create `RunSimulation.cmd`.
- [ ] Add CLI parsing.
- [ ] Add target profiles.
- [ ] Add `smoke` and `demo` profiles.
- [ ] Add total/API/auth-write rate budgets.
- [ ] Add anonymous page scenarios.
- [ ] Add anonymous author-book API scenarios.
- [ ] Add low-weight health scenario.
- [ ] Add status/latency tracking.
- [ ] Add expected 404 classification.
- [ ] Add unexpected/expected 429 classification.
- [ ] Add `Retry-After` backoff.
- [ ] Add JSON and Markdown reports.
- [ ] Add strict local defaults.

Verification:

```powershell
dotnet build .\Tools\TrafficSimulation\TrafficSimulation.csproj
.\RunSimulation.ps1 -Target local -Profile smoke
dotnet test .\BlazorAutoApp.sln --no-restore
```

Acceptance:

- local smoke completes.
- no unexpected 5xx responses.
- no unexpected 429 responses.
- report is created under `artifacts/simulation`.
- solution tests still pass.

### Phase 2: Observability Integration

Status: not started.

Work:

- [ ] Add suggested Grafana time range to summary output.
- [ ] Add optional local Prometheus checks if observability is enabled.
- [ ] Verify logs, traces, and metrics after read-only traffic.
- [ ] Document the exact local demo flow.

Verification:

```powershell
.\RunLocal.ps1 -NoBrowser -Observability -TimeoutSeconds 240
.\RunSimulation.ps1 -Target local -Profile demo -Duration 5m -MaxRps 2
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

Acceptance:

- Grafana dashboards show fresh traffic.
- local observability smoke passes.
- no observability container reports OOMKilled.

### Phase 3: Browser Auth Bootstrap

Status: not started.

Work:

- [ ] Add Playwright helper for register/login through the real UI.
- [ ] Generate synthetic email and password.
- [ ] Keep password out of logs.
- [ ] Store cookies only in a temp path.
- [ ] Export cookies to the HTTP simulator only for the current run if needed.
- [ ] Ensure tests skip unless explicitly enabled.

Verification:

```powershell
$env:RUN_E2E = "1"
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "FullyQualifiedName~Simulation"
```

Acceptance:

- synthetic user can register or log in locally.
- cookies are not committed.
- test skips cleanly unless enabled.

### Phase 4: Synthetic User-Book CRUD

Status: not started.

Work:

- [ ] Add authenticated `GET /api/books/`.
- [ ] Add gated create/update/delete scenarios.
- [ ] Add synthetic book ownership tracking.
- [ ] Add cleanup on normal exit.
- [ ] Add cleanup on cancellation where possible.
- [ ] Add `--cleanup-only`.
- [ ] Refuse write traffic unless `SIMULATION_ALLOW_WRITE=1`.
- [ ] Add a clear warning before deployed writes.

Verification:

```powershell
$env:SIMULATION_ALLOW_WRITE = "1"
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -Cleanup
.\RunSimulation.ps1 -Target local -CleanupOnly
```

Acceptance:

- created synthetic books are deleted.
- cleanup-only leaves zero synthetic leftovers for the configured synthetic user/run.
- non-synthetic books are never modified.
- `books_operations_total` is populated when observability is enabled.

### Phase 5: Deployed Edge Smoke

Status: not started.

Work:

- [ ] Add deployed target gates.
- [ ] Add LocalCluster and Cloud examples.
- [ ] Keep deployed smoke read-only by default.
- [ ] Detect Cloudflare managed challenge pages.
- [ ] Identify whether traffic went through public edge or origin tunnel.
- [ ] Keep generated reports local.

Verification:

```bash
SIMULATION_ALLOW_DEPLOYED=1 pwsh ./RunSimulation.ps1 -Target localcluster-edge -Profile smoke

SIMULATION_ALLOW_DEPLOYED=1 pwsh ./RunSimulation.ps1 -Target cloud-edge -Profile smoke
```

Acceptance:

- low-rate deployed smoke completes from CurrentPC.
- public health remains healthy.
- no deployed write traffic happens accidentally.

### Phase 6: Optional Browser Journey Sampler

Status: not started.

Work:

- [ ] Add `--browser-sampler`.
- [ ] Run one browser journey in parallel with HTTP traffic.
- [ ] Cap browser users at 3.
- [ ] Record screenshots/videos only on failure.
- [ ] Store browser artifacts under ignored paths.
- [ ] Reuse existing E2E guard patterns.

Verification:

```powershell
$env:SIMULATION_BROWSER = "1"
.\RunSimulation.ps1 -Target local -Profile demo -BrowserSampler -Duration 3m
```

Acceptance:

- browser journey completes locally.
- background HTTP traffic continues.
- artifacts are ignored.

### Phase 7: CI And Documentation

Status: not started.

Work:

- [ ] Add `Tools/TrafficSimulation/README.md`.
- [ ] Add a dedicated `docs/SimulationGuide.md`.
- [ ] Add a short `docs/ObservabilityGuide.md` section explaining how to generate demo traffic before opening Grafana.
- [ ] Add a short `README.md` entry pointing to `docs/SimulationGuide.md`.
- [ ] Add a short `HowToRunLocally.md` section showing `RunSimulation.ps1` after `RunLocal.ps1`.
- [ ] Add simulator build to CI.
- [ ] Do not run deployed simulation in normal CI.
- [ ] Consider local smoke simulation in CI only if it is stable and fast.

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln
dotnet build .\Tools\TrafficSimulation\TrafficSimulation.csproj
dotnet test .\BlazorAutoApp.sln --no-restore
```

Acceptance:

- docs explain safe demo traffic.
- users can run local smoke without reading this long plan.
- docs warn that deployed targets require `SIMULATION_ALLOW_DEPLOYED=1` or `-AllowDeployed`.
- docs explain why API RPS is lower than total RPS because of app rate limiting.
- normal CI remains reliable.
- no CI job sends traffic to public domains unless manually dispatched.

Required documentation content:

```text
README.md:
  one short Simulation entry under the tooling or observability section.

HowToRunLocally.md:
  how to start local app with observability.
  how to run local smoke.
  how to run local demo.
  where reports are written.

docs/ObservabilityGuide.md:
  how to warm dashboards with RunSimulation.
  expected Grafana time range.
  note that 429 should normally be zero outside burst/rate-limit tests.

docs/SimulationGuide.md:
  quick start.
  target modes.
  profiles.
  safety gates.
  rate-limit behavior.
  report format.
  cleanup behavior.
  deployed examples.

Tools/TrafficSimulation/README.md:
  concise developer reference.
  raw dotnet command.
  CLI options.
  troubleshooting.
```

## Report Format

Minimum `summary.json`:

```json
{
  "runId": "20260530-traffic-abc123",
  "target": "local",
  "baseUrl": "https://localhost:7186",
  "profile": "smoke",
  "startedAtUtc": "2026-05-30T18:00:00Z",
  "endedAtUtc": "2026-05-30T18:01:30Z",
  "durationSeconds": 90,
  "maxRps": 1,
  "apiRpsBudget": 0.5,
  "authWriteRpsBudget": 0.1,
  "virtualUsers": 2,
  "writesEnabled": false,
  "browserSamplerEnabled": false,
  "requestCount": 92,
  "statusCodes": {
    "200": 90,
    "404_expected": 2
  },
  "latency": {
    "p50Ms": 42,
    "p95Ms": 184,
    "p99Ms": 260
  },
  "createdSyntheticUsers": 0,
  "createdSyntheticBooks": 0,
  "updatedSyntheticBooks": 0,
  "deletedSyntheticBooks": 0,
  "leftoverSyntheticBooks": 0,
  "rateLimit": {
    "expected429": 0,
    "unexpected429": 0,
    "retryAfterBackoffs": 0,
    "maxRetryAfterSeconds": 0
  },
  "errors": []
}
```

Minimum `summary.md`:

```text
# Traffic Simulation Summary

target: local
profile: smoke
base URL: https://localhost:7186
duration: 90s
requests: 92
unexpected failures: 0
p95: 184 ms
api budget: 0.5 rps
unexpected 429: 0
writes: disabled
browser sampler: disabled
cleanup: not needed
Grafana range: last 15 minutes
```

## What Good Looks Like

Local demo:

```powershell
.\RunLocal.ps1 -NoBrowser -Observability -TimeoutSeconds 240
.\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
```

Expected terminal result:

```text
Traffic simulation completed
target: local
profile: demo
requests: 1800
2xx: 1710
4xx expected: 90
4xx unexpected: 0
5xx: 0
p95: 160 ms
api budget: 0.8 rps
unexpected 429: 0
writes: disabled
cleanup: not needed
Grafana range: last 15 minutes
report: artifacts/simulation/...
```

Cloud smoke:

```bash
SIMULATION_ALLOW_DEPLOYED=1 pwsh ./RunSimulation.ps1 -Target cloud-edge -Profile smoke
```

Expected terminal result:

```text
Traffic simulation completed
target: cloud-edge
profile: smoke
requests: 92
2xx: 90
4xx expected: 2
4xx unexpected: 0
5xx: 0
p95: 184 ms
api budget: 0.5 rps
unexpected 429: 0
writes: disabled
cleanup: not needed
Grafana range: last 15 minutes
```

## Risks And Mitigations

Risk: accidental deployed load.

Mitigation:

- require `SIMULATION_ALLOW_DEPLOYED=1`.
- keep deployed defaults low.
- print resolved target before starting.
- require confirmation for deployed writes or high RPS overrides.

Risk: synthetic data pollution.

Mitigation:

- writes disabled by default.
- strict synthetic prefix.
- synthetic ownership tracking.
- cleanup on exit.
- cleanup-only command.

Risk: fragile auth automation.

Mitigation:

- start read-only.
- use Playwright for real login/register.
- keep browser sampler low rate.
- avoid hand-rolled antiforgery posts.

Risk: false confidence from read-only traffic.

Mitigation:

- report whether writes were enabled.
- report skipped authenticated scenarios.
- add CRUD only as a gated later phase.

Risk: high-cardinality telemetry.

Mitigation:

- run IDs stay in local reports and synthetic titles only.
- no run ID labels.
- no per-book labels.
- no per-user labels.

Risk: Cloudflare challenge or rate limiting.

Mitigation:

- detect challenge pages and stop.
- keep public edge traffic low.
- allow origin-via-tunnel as a later diagnostic mode.
- classify 429 separately from app failures when rate limiting is expected.
- pace API and auth-write scenarios below app defaults.
- honor `Retry-After` and back off instead of retrying aggressively.

Risk: the friendly script and raw CLI drift apart.

Mitigation:

- keep `RunSimulation.ps1` thin.
- document raw CLI options in `Tools/TrafficSimulation/README.md`.
- add a smoke test or CI command that exercises the wrapper at least enough to print help/version.

Risk: documentation becomes stale.

Mitigation:

- treat docs as part of Phase 7 acceptance.
- include `RunSimulation.ps1` examples in `README.md`, `HowToRunLocally.md`, `docs/ObservabilityGuide.md`, and `docs/SimulationGuide.md`.
- keep this plan as implementation detail and keep user-facing docs short.

Risk: simulator becomes a second application nobody maintains.

Mitigation:

- keep V1 small.
- use public HTTP contracts only.
- keep docs short in the actual tool README.
- keep this long file as the implementation handoff.

## Open Questions

- Should deployed authenticated simulation create a fresh synthetic account per run or use one persistent simulator account per target?
- Should deployed write mode be allowed at all, or kept local-only until cleanup reporting is proven?
- Should reports be uploaded as CI artifacts for manual workflow runs?
- Should simulator failures ever block CI, or should the simulator remain manual/operator-triggered?
- Should `/Plans/Simulation.md` move to `docs/Simulation.md` before implementation so it can be committed?

Recommended V1 answers:

- fresh synthetic account per write-enabled deployed run.
- deployed writes disabled by default and manually gated.
- local reports only at first.
- CI builds the simulator but does not run deployed simulation.
- move this plan to `docs/` only if it should become a versioned project guide.

## Senior Review Checklist

Before marking V1 complete, verify:

- [ ] simulator is under `Tools/TrafficSimulation`.
- [ ] project is included in `BlazorAutoApp.sln`.
- [ ] `RunSimulation.ps1` exists and is the documented entrypoint.
- [ ] optional `RunSimulation.cmd` exists or the plan explicitly says why it was skipped.
- [ ] default target is local.
- [ ] deployed targets require `SIMULATION_ALLOW_DEPLOYED=1`.
- [ ] writes require `SIMULATION_ALLOW_WRITE=1`.
- [ ] API traffic is paced below API rate-limit defaults.
- [ ] auth write traffic is paced below auth rate-limit defaults.
- [ ] normal smoke/demo runs report zero unexpected 429 responses.
- [ ] `Retry-After` is honored.
- [ ] reports are written under ignored `artifacts/simulation`.
- [ ] read-only smoke works locally.
- [ ] read-only demo creates visible Grafana traffic.
- [ ] README, HowToRunLocally, ObservabilityGuide, SimulationGuide, and tool README are updated.
- [ ] tests still pass.
- [ ] no secrets or cookies are written to git-tracked paths.
- [ ] no high-cardinality labels were added.
- [ ] no deployment architecture changed.

## Official References Reviewed

- Grafana k6 overview: https://grafana.com/oss/k6/
- Grafana k6 scenarios and executors: https://grafana.com/docs/k6/latest/using-k6/scenarios/
- Grafana k6 thresholds: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- NBomber load simulation: https://nbomber.com/docs/nbomber/load-simulation
- NBomber thresholds: https://nbomber.com/docs/nbomber/asserts_and_thresholds
- NBomber license: https://nbomber.com/docs/getting-started/license
- Playwright documentation: https://playwright.dev/
- Microsoft ASP.NET Core rate limiting: https://learn.microsoft.com/en-us/aspnet/core/performance/rate-limit
- Microsoft HttpClient guidance: https://learn.microsoft.com/en-us/dotnet/fundamentals/runtime-libraries/system-net-http-httpclient
