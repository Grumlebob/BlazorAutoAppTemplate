# Traffic Simulation Guide

This guide explains how to generate safe synthetic traffic for the Books app.

The simulator is a `BlazorAutoApp.Simulation` operator tool for observability demos and confidence checks. It is built and tested by CI, but it is not deployed with the app and is not a high-volume production load test.

## Quick Start

Start the local app and observability stack:

```powershell
.\Scripts\RunLocal.ps1 -NoBrowser -Observability
```

Run a short local smoke:

```powershell
.\Scripts\RunSimulation.ps1
```

Run a dashboard warmup:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
```

Install the browser used for authenticated checks and the optional UI sampler:

```powershell
.\Scripts\RunSimulation.ps1 -InstallBrowsers
```

Run an authenticated local check without writes:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -AuthCheck
```

Open Grafana:

```text
http://localhost:3000
```

Use the last 15 minutes as the time range.

## Targets

```text
local               https://localhost:7186
localcluster-public https://books.jacobgrum.com
cloud-public        https://bookscloud.jacobgrum.com
origin-via-tunnel   requires -BaseUrl
```

Deployed targets require an explicit gate:

```powershell
.\Scripts\RunSimulation.ps1 -Target cloud-public -Profile smoke -AllowDeployed
```

or:

```powershell
$env:SIMULATION_ALLOW_DEPLOYED = "1"
.\Scripts\RunSimulation.ps1 -Target cloud-public -Profile smoke
```

## Profiles

```text
smoke       short, low-rate, should have zero unexpected 429/5xx responses
demo        dashboard warmup for Grafana
soak-lite   longer low-rate check
burst       local-only rate-limit experiment, requires -AllowBurst
```

Read-only traffic is the default. Authenticated writes and browser journeys are available only behind explicit gates.

## Rate Limits

The app has built-in rate limiting:

```text
global app traffic: 600 requests/minute per user or IP
Books APIs:         60 requests/minute per user or IP
Account POSTs:      120 requests/5 minutes per user or IP
```

The simulator keeps separate budgets for total traffic, API traffic, and authenticated write traffic. A demo can use `-MaxRps 3`, but API calls are still paced below the app's API limit by default.

Normal smoke and demo runs should report:

```text
unexpected 429: 0
```

If a `429` happens, the simulator honors `Retry-After`, backs off that scenario class, and records the event in the report.

## Common Commands

Local smoke:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke
```

Local demo:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
```

Lower API traffic further:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile demo -MaxRps 3 -ApiRpsBudget 0.5
```

Cloud read-only smoke:

```powershell
.\Scripts\RunSimulation.ps1 -Target cloud-public -Profile smoke -AllowDeployed
```

Local authenticated smoke:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -AuthCheck
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
.\Scripts\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
```

Local authenticated smoke with the UI sampler:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -BrowserSampler -Duration 60s
```

Cloud authenticated smoke:

```powershell
$env:SIMULATION_AUTH_EMAIL = "bookscloud-sim@example.com"
$env:SIMULATION_AUTH_PASSWORD = "<secret>"
.\Scripts\RunSimulation.ps1 -Target cloud-public -AuthCheck -AllowDeployed
.\Scripts\RunSimulation.ps1 -Target cloud-public -Profile smoke -Writes -Cleanup -AllowDeployed -AllowWrite -Duration 60s
.\Scripts\RunSimulation.ps1 -Target cloud-public -CleanupOnly -AllowDeployed -AllowWrite
```

Show tool help:

```powershell
.\Scripts\RunSimulation.ps1 -Help
```

## Three-Environment Matrix

Use `Scripts/RunSimulationMatrix.ps1` when you want one operator command to run the
same safe checks across local, LocalCluster, and Cloud. It stops immediately if
any simulator command exits nonzero and prints the report directories it
created.

Read-only matrix for all targets:

```powershell
.\Scripts\RunSimulationMatrix.ps1 -All
```

Local read/write/browser/cleanup matrix:

```powershell
.\Scripts\RunSimulationMatrix.ps1 -Local -IncludeWrites
```

Deployed read/write/browser/cleanup matrix with disposable generated users:

```powershell
.\Scripts\RunSimulationMatrix.ps1 -LocalCluster -Cloud -IncludeWrites -RegisterSyntheticUsers -AllowDeployedWrites
```

Safety rules are intentionally duplicated in the wrapper:

- deployed writes require `-AllowDeployedWrites`.
- deployed registration requires `-RegisterSyntheticUsers`.
- generated passwords stay in memory and are not printed.
- cleanup-only runs after write/browser passes.

## Report Analysis

Use `Scripts/AnalyzeSimulationReports.ps1` to turn local `summary.json` files into a
compact Markdown table:

```powershell
.\Scripts\AnalyzeSimulationReports.ps1 -Latest 15
```

Analyze a specific run:

```powershell
.\Scripts\AnalyzeSimulationReports.ps1 -Report .\artifacts\simulation\20260530-215221-cloud-public-smoke
```

The analyzer reads local artifacts only. It does not call deployed targets and
does not require credentials. The `Alerts` column highlights failed thresholds,
unexpected `429`, `5xx`, browser failures, and cleanup leftovers.

## Reports

Reports are written under:

```text
artifacts/simulation/<timestamp>-<target>-<profile>/
```

Each run writes:

```text
summary.json
summary.md
synthetic-ledger.json when synthetic books were touched
```

`artifacts/` is gitignored.

The summary includes:

- request count.
- status code counts.
- expected and unexpected `429` counts.
- p50/p95/p99 latency.
- scenario breakdown.
- authenticated check status.
- synthetic book create/update/delete/cleanup counts.
- browser sampler result when enabled.
- suggested Grafana time range.

## Cleanup Recovery

If a write run exits with cleanup failure or reports `leftovers` greater than `0`, run cleanup-only for the same target:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
```

For Cloud:

```powershell
.\Scripts\RunSimulation.ps1 -Target cloud-public -CleanupOnly -AllowDeployed -AllowWrite
```

Cleanup-only logs in as the configured simulator user, lists that user's books, and deletes only books that match both V2 safety markers:

```text
title starts with [sim-v2:<target>:
url starts with https://simulation.invalid/books/
```

Cleanup for `localcluster-public` and `cloud-public` also recognizes the old
`localcluster-edge` and `cloud-edge` markers so older synthetic books are not
stranded by the target rename.

It does not delete public author books, books from another user, or ordinary user-created books. If cleanup-only still reports leftovers, inspect the run's `summary.md` and `synthetic-ledger.json` under `artifacts/simulation/`.

## Safety Rules

- Deployed traffic is read-only by default.
- Deployed traffic requires `-AllowDeployed` or `SIMULATION_ALLOW_DEPLOYED=1`.
- Write traffic, cleanup, and registration require `-AllowWrite` or `SIMULATION_ALLOW_WRITE=1`.
- Passwords must come from `SIMULATION_AUTH_PASSWORD` or the variable named by `-AuthPasswordEnv`.
- Local auth defaults to the seeded `user@user.com` account when no simulation credentials are set.
- Deployed auth requires `SIMULATION_AUTH_EMAIL` and `SIMULATION_AUTH_PASSWORD`.
- Cleanup deletes only V2 synthetic books for the authenticated simulator user.
- The browser sampler requires `-Writes`; it creates, updates, and deletes one synthetic book through the UI.
- Do not use burst mode against deployed targets.
- Do not spoof `X-Forwarded-For` to bypass rate limiting.
- Do not commit generated reports.

## Raw Tool

The friendly wrapper runs the .NET tool:

```powershell
dotnet run --project .\BlazorAutoApp.Simulation -- --target local --profile smoke
```

Prefer `Scripts/RunSimulation.ps1` for normal use.
