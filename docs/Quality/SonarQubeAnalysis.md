# On-demand source quality audit

SonarQube reviews source, test results, and coverage. Lighthouse measures a running page; see [Lighthouse](../Test.md#lighthouse-performance). Audits run only when invoked. They do not run in builds, CI, pull requests, app startup, deployment, or schedules. The quality gate is informational; normal build and test checks remain authoritative.

## Requirements and modes

Full mode is supported on Windows with PowerShell 7, Docker Desktop using Linux containers, Git, the .NET SDK, Python, and the pinned Node/npm runtime when React is included. It provisions a repository-scoped local SonarQube stack. The first free port in `9200`–`9299` is selected and saved in ignored local settings; another port owner is never stopped. Pinned versions are in [`tool-versions.json`](../../Scripts/Quality/tool-versions.json).

Quick mode runs the opt-in `SonarAnalyzer.CSharp` build analyzer. It needs no SonarQube server or Node/npm, accepts dirty source, and restores the normal selected-profile NuGet graph before it exits. Quick mode does not upload analysis or provide Full-mode coverage and server reports.

Full mode fetches `origin/main` and analyzes that commit in detached worktrees by default. Use `-Candidate` for a clean, committed tooling candidate; candidate projects do not count as trusted baselines. Both modes run `BlazorAuto` and `React` sequentially by default. Choose one with `-FrontendProfile BlazorAuto` or `-FrontendProfile React`.

## Run an audit

Run PowerShell commands from the repository root. Quick mode is the fast analyzer pass. Wrapper options are declared in [`Invoke-CodeQualityAudit.ps1`](../../Scripts/Quality/Invoke-CodeQualityAudit.ps1).

```powershell
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Mode Quick
```

Run Full mode for both profiles:

```powershell
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1
```

For pre-merge analysis, commit the candidate, ensure the checkout is clean, then run:

```powershell
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Candidate
```

Use `-KeepServerRunning` to leave the owned dashboard available after Full mode. Without it, the wrapper stops the stack only if that invocation started it. A stack that was already running stays up.

## Server controls

Full mode starts and initializes the local stack as needed. To control it directly, use these commands from the repository root. Available controls are declared in [`SonarQubeServer.ps1`](../../Scripts/Quality/SonarQubeServer.ps1).

```powershell
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Start -Initialize
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Status
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Logs
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Stop
```

Open the loopback URL reported by the command. Stop only this repository's stack; its database history remains in named Docker volumes. The dashboard project key appears in the archived profile summary. Do not guess a port from another repository.

## Read results

Full reports are in the private per-user `reports/<runId>/` directory. `summary.json` and `batch.md` link to profile summaries, reports, and logs. Quick reports are in ignored `artifacts/quality/quick/`.

Each Full profile report binds results to one analysis, source SHA, project, profile, version, and settings digest. The Markdown report summarizes findings; `report.json` contains validated issue and measure data. The batch report compares profiles; do not add their shared LOC or average their coverage.

Reports state source scope, exclusions, test counts, coverage evidence, security-hotspot status, and gate result. C# tests use Microsoft XML coverage. React runs `npm ci`, API contract validation, typecheck, and ordinary Vitest coverage tests before analysis. Both .NET profiles validate approved suite counts and direct collector reports. Missing or unresolved coverage fails the scan instead of appearing as zero or passing.

File risk is a ranking heuristic based on cognitive complexity, 180-day churn, uncovered lines, and reliability/security issues. It is not a defect probability. A failed SonarQube gate remains an observation; inspect source before planning a change.

## Optional read-only MCP

The MCP launcher connects to an already-running repository stack. It does not start SonarQube. It uses the pinned official image, read-only mode, and an encrypted profile reader token. Do not place the token in command history or client configuration; see [SonarQube maintenance](SonarQubeMaintenance.md#private-identity-and-settings).

The launcher options are declared in [`Start-SonarQubeMcp.ps1`](../../Scripts/Quality/Start-SonarQubeMcp.ps1). Run interactively from the repository root:

```powershell
pwsh -NoProfile -File Scripts/Quality/Start-SonarQubeMcp.ps1 -FrontendProfile BlazorAuto
```

To verify MCP without a desktop client, pass the project key from the profile summary:

```powershell
$projectKey = "paste-project-key-from-profile-summary"
python Scripts/Quality/probe_sonar_mcp.py `
  --launcher Scripts/Quality/Start-SonarQubeMcp.ps1 `
  --profile BlazorAuto `
  --project-key $projectKey
```

The probe times out after 60 seconds. It lists tools, checks that write tools are absent, and tests issue, rule, measure, coverage, and gate access. It uses the same launcher and token store. A stopped stack causes a diagnostic; the probe does not start it.

For a personal MCP client, register a stdio command that invokes `pwsh -NoProfile -File Scripts/Quality/Start-SonarQubeMcp.ps1 -FrontendProfile BlazorAuto` from this repository's root. Keep the entry disabled until selected if the client starts processes automatically. Do not register MCP as a build or deployment hook.

## Local settings

Copy [`quality-settings.example.json`](../../Scripts/Quality/quality-settings.example.json) to the ignored `Scripts/Quality/quality-settings.local.json` to set a private port override or explicit Node/Python executable. `-SettingsPath` accepts another file with the same schema. Remote server URLs and project-key overrides are rejected. For repository identity, encrypted credentials, backup, and upgrade procedures, use [SonarQube maintenance](SonarQubeMaintenance.md).
