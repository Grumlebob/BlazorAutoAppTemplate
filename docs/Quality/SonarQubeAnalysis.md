# On-demand source quality audit

SonarQube inspects source code, rules, test results, and coverage. Lighthouse measures a running page in a browser. Use SonarQube to plan source improvements; use [Lighthouse](../Test.md#lighthouse) to investigate runtime performance and page quality. Neither tool starts the other.

Audits run only when a developer invokes them. They do not run from builds, CI, pull requests, application startup, deployment, timers, or schedules. The SonarQube quality gate is informational; existing build and test checks stay authoritative. Findings are evidence for review, not authorization to change application behavior.

## Requirements and output

Full mode requires Windows, PowerShell 7, Docker Desktop using Linux containers, Git, the .NET SDK, Python, and the pinned Node/npm runtime when React is included. It uses a private, repository-identity-scoped Community Build stack at loopback port 9200 by default. If that first port is occupied during first setup, it chooses an available port from 9200–9299 and stores the choice in the private settings file. It never stops another port owner. Database history lives in this repository's named Docker volumes and survives a normal stop.

Quick mode uses the opt-in `SonarAnalyzer.CSharp` build analyzer. It needs no SonarQube server or Node/npm runtime and accepts dirty source because it does not upload analysis. It always restores the normal selected-profile NuGet graph before returning.

Full mode fetches `origin/main` and analyzes that exact fetched commit by default. It runs each requested profile in its own detached worktree. `-Candidate` instead requires a clean, committed checkout and writes to SHA-specific candidate projects. Candidate reports never count as trusted baselines. Both modes process `BlazorAuto` and `React` sequentially by default.

Full reports are archived under the private per-user `reports/<runId>/` directory. The root `summary.json` and `batch.md` link to profile summaries and reports. Run details, test files, and scanner logs remain in the private run directory. Quick reports stay in ignored `artifacts/quality/quick/`.

## Run an audit

From the repository root, run Quick mode for a fast C# analyzer pass:

```powershell
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Mode Quick
```

Run the full source audit for both profiles:

```powershell
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1
```

Choose one profile with `-FrontendProfile BlazorAuto` or `-FrontendProfile React`. A dirty Quick run is labeled in its summary. Full mode rejects dirty candidate input; the default Full mode uses fetched `origin/main`, regardless of the invoking branch.

For pre-merge validation, commit the tooling candidate, ensure the checkout is clean, then run:

```powershell
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Candidate
```

The wrapper creates a distinct candidate project for each profile. It never removes candidate analysis history. Use `-KeepServerRunning` with Full mode to leave the owned dashboard available after the reports are archived. Without it, the wrapper stops the server only when that invocation started the repository-owned stack. A server that was already running stays up.

## Start and inspect the local server

The Full wrapper starts and initializes the private stack as needed. To start it manually:

```powershell
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Start -Initialize
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Status
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Logs
```

Open the loopback URL shown by the command. The dashboard project key appears in the archived profile summary. Do not infer a port from another repository or SonarQube instance.

Stop only this repository's stack; history volumes remain:

```powershell
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Stop
```

The stack is intentionally separate from application and deployment Compose files. It does not share the unrelated `sonarqube-improveddb` stack.

## Read results

Each profile report binds to one exact CE task, analysis ID, source SHA, project, profile, project version, and settings digest. Export fails if another analysis changes the latest-view data during collection. The Markdown report summarizes findings; `report.json` keeps the full validated issue and measure data. Use the batch report to compare profile outcomes, not to add their shared LOC or average their coverage.

The report states the actual source scope, exclusions, test counts, coverage evidence, security-hotspot status, and informational gate. C# tests run with Microsoft XML coverage. React runs `npm ci`, API contract validation, typecheck, and all ordinary Vitest coverage tests before scanner begin. Both .NET profile runs validate the approved suite counts and direct collector reports. Missing or unresolved coverage fails the scan rather than appearing as zero or as a passing percentage.

The file risk score is a ranking heuristic using cognitive complexity, 180-day churn, uncovered lines, and reliability/security issues. It is not a defect probability. Missing coverage stays visibly unavailable; a fallback is used only for ordering files. Read source and inspect the issue before planning a fix. A failed quality gate remains an observation and does not fail an otherwise complete audit.

## Optional read-only MCP

The MCP launcher connects only to the already-running repository-owned stack. It does not start SonarQube. It loads the selected profile's encrypted reader token, uses the pinned official MCP image, and sets read-only mode with investigation toolsets. The reader account is scoped to that profile's main and explicitly provisioned candidate projects. No Docker socket or source tree is mounted.

Run interactively from the repository root and select a profile:

```powershell
pwsh -NoProfile -File Scripts/Quality/Start-SonarQubeMcp.ps1 -FrontendProfile BlazorAuto
```

To verify MCP headlessly after an analysis, pass the project's key from its profile summary. The probe negotiates the MCP protocol, lists tools, checks that write tools are absent, and calls issue, rule, measure, coverage, and gate tools:

```powershell
python Scripts/Quality/probe_sonar_mcp.py `
  --launcher Scripts/Quality/Start-SonarQubeMcp.ps1 `
  --profile BlazorAuto `
  --project-key <project-key-from-summary>
```

The default timeout is 60 seconds. This probe uses the same launcher and encrypted token store; it does not require a desktop client or a separate credential. A stopped stack causes the launcher to fail with a diagnostic. It does not start the server automatically.

For a personal MCP client, register a stdio command that invokes `pwsh -NoProfile -File Scripts/Quality/Start-SonarQubeMcp.ps1 -FrontendProfile <profile>` from this repository's root. Add one entry per desired profile. Keep the entry disabled until selected if the client starts MCP processes automatically at launch. Do not put tokens or private paths in tracked files, and do not register the server as a build or deployment hook. No personal client is configured as part of this feature.

## Local settings and identity

The tracked example is `Scripts/Quality/quality-settings.example.json`. For a private port override or explicit Node/Python executable, copy it to the ignored `Scripts/Quality/quality-settings.local.json` and edit only those values. `-SettingsPath` can name another local JSON file with the same schema. Remote server URLs and project-key overrides are rejected.

Compose and secret namespaces derive from normalized Git `origin`, not the worktree folder. Clones of one repository share local history; a fork gets a separate namespace. A rename or fork never moves or deletes the old namespace. DPAPI-encrypted credentials are available only to the Windows user who created them. Full-mode provisioning on Linux/macOS is unsupported; Quick mode and offline Python tests remain cross-platform.

## Credentials and recovery

The scripts generate the database, admin, project analysis, and profile reader credentials. They store them encrypted under the current user's local application data. Never print secret files, put credentials in documented commands or shell history, or copy the secret directory into the repository. SonarQube documents that `SONAR_TOKEN` is not supported by the .NET scanner, so the pinned scanner receives its analysis token as a transient process argument; the scripts redact it from console output and retained logs. See [SonarQube analysis parameter guidance](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/analysis-parameters/parameters-not-settable-in-ui).

To rotate one generated token, remove only its local encrypted token record, then run initialization. Hold the repository quality lock while removing the record and provisioning its replacement. The server helper revokes and replaces only its exact owned token name. For example, rotate the BlazorAuto reader token:

```powershell
$repo = (git rev-parse --show-toplevel).Trim()
Import-Module "$repo/Scripts/Quality/SonarQuality.psm1" -Force
$context = Get-QualityContext -RepoRoot $repo
$lock = Enter-QualityLock -Context $context -Operation 'RotateReaderToken' -RunId ([guid]::NewGuid().ToString('N'))
try {
  Remove-QualitySecret -Context $context -Name 'reader-blazorauto-token'
  & "$repo/Scripts/Quality/SonarQubeServer.ps1" -Start -Initialize -RepoRoot $repo -Context $context
}
finally {
  Exit-QualityLock -Lock $lock
}
```

Use the corresponding `analysis-blazorauto-main` or `analysis-react-main` name for a main analysis token. Candidate token names include `candidate-<sha12>`. Do not delete the database password or admin credential to force recovery. If an existing volume lacks its encrypted database password, or stored admin credentials do not authenticate on a non-fresh stack, the helper stops safely; recover the original credential before proceeding. Never delete a named volume to fix an authentication problem.

If a run fails, inspect its private `summary.json` and sanitized step logs. A partial two-profile run retains completed reports and Sonar history, returns nonzero, and is not baseline-eligible. Fix the cause and run a new complete batch. If report archival fails, the wrapper leaves its worktrees in the private run directory. Confirm their exact run path and SHA before manual cleanup.

## Back up and upgrade

Keep a database backup and preserve the four identity-scoped named volumes (`database`, `data`, `extensions`, and `logs`) plus the encrypted local secret/settings directory. Store backups outside the repository and restrict access to the same user. For a logical PostgreSQL backup, load the encrypted database password only into the process environment and stream `pg_dump` from the owned database container to a private backup file:

```powershell
$repo = (git rev-parse --show-toplevel).Trim()
Import-Module (Join-Path $repo 'Scripts/Quality/SonarQuality.psm1') -Force
$context = Get-QualityContext -RepoRoot $repo
$databasePassword = Get-QualitySecret -Context $context -Name 'database-password'
$backupDirectory = Join-Path $context.BaseDirectory 'backups'
New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null
$backupFile = Join-Path $backupDirectory "sonar-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')).sql"
$names = @('SONARQUBE_DB_PASSWORD', 'SONARQUBE_HOST_PORT', 'SONARQUBE_IDENTITY_HASH', 'SONARQUBE_NETWORK_NAME', 'SONARQUBE_COMPOSE_PROJECT')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
  $env:SONARQUBE_DB_PASSWORD = $databasePassword
  $env:SONARQUBE_HOST_PORT = [string]$context.HostPort
  $env:SONARQUBE_IDENTITY_HASH = $context.IdentityHash
  $env:SONARQUBE_NETWORK_NAME = $context.ComposeNetwork
  $env:SONARQUBE_COMPOSE_PROJECT = $context.ComposeProject
  docker compose --project-name $context.ComposeProject --file $context.ComposePath `
    exec -T database sh -c 'PGPASSWORD=$POSTGRES_PASSWORD pg_dump -U sonar -d sonar' > $backupFile
  if ($LASTEXITCODE -ne 0) { throw 'Database backup failed; preserve logs and do not upgrade.' }
}
finally {
  foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
  $databasePassword = $null
}
```

Stop the owned stack before any file-level volume backup. To upgrade, review the SonarQube release notes, change the pinned image in a pull request, create and verify a backup, stop the stack, then start it with `SonarQubeServer.ps1 -Start`. Follow any migration prompt in the loopback UI. Never remove volumes or prune Docker resources as part of an upgrade. Keep a verified backup until the new version has started and the history is readable.

Run all quality commands with PowerShell 7 (`pwsh`). The scanner uses command-line switches beginning with `/`; shell wrappers that rewrite them can break analysis.

## Validate the tooling

Run focused offline tests from the repository root:

```powershell
python -m unittest discover -s Scripts/Quality/tests -p 'test_*.py'
pwsh -NoProfile -File Scripts/Quality/tests/Test-SonarQualityModule.ps1
pwsh -NoProfile -File Scripts/Quality/tests/Test-SonarQualityFoundation.ps1
pwsh -NoProfile -File Scripts/Quality/tests/Test-SonarQualityAuditContract.ps1
```

The complete repository gate remains required for code or configuration changes. See [Test.md](../Test.md#local-gate) and validate the SonarQube Compose file with `yamllint docker/sonarqube/compose.yaml`.
