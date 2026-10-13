# SonarQube maintenance

Use this guide for private local identity, credentials, backup, recovery, and upgrades. For audit commands and report reading, use [On-demand source quality audit](SonarQubeAnalysis.md).

## Private identity and settings

Compose and secret namespaces derive from normalized Git `origin`, not the worktree folder. Clones of one repository share local history; a fork gets a separate namespace. A fork or rename does not move or delete the old namespace.

Copy [`quality-settings.example.json`](../../Scripts/Quality/quality-settings.example.json) to the ignored `Scripts/Quality/quality-settings.local.json` for a private port override or explicit Node/Python executable. `-SettingsPath` accepts the same schema. Remote server URLs and project-key overrides are rejected. SonarQube credentials use DPAPI encryption and are available only to the Windows user who created them.

## Credentials and recovery

The scripts create the database, admin, project-analysis, and profile-reader credentials. They store them encrypted under the current user's local application data. Never print secret files, put credentials in commands or shell history, or copy the secret directory into the repository. The .NET scanner receives its token as a transient process argument because it does not support `SONAR_TOKEN`; scripts redact the token from console output and retained logs. See [SonarQube analysis parameters](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/analysis-parameters/parameters-not-settable-in-ui).

Rotate one generated token by removing only its encrypted local record, then initialize the owned stack. Hold the repository quality lock while replacing the token. The server helper revokes and replaces only its exact owned token name. Set `$profile` to `BlazorAuto` or `React`:

```powershell
$repo = (git rev-parse --show-toplevel).Trim()
$profile = "BlazorAuto"
$readerTokenName = "reader-$($profile.ToLowerInvariant())-token"
Import-Module "$repo/Scripts/Quality/SonarQuality.psm1" -Force
$context = Get-QualityContext -RepoRoot $repo
$lock = Enter-QualityLock -Context $context -Operation 'RotateReaderToken' -RunId ([guid]::NewGuid().ToString('N'))
try {
  Remove-QualitySecret -Context $context -Name $readerTokenName
  & "$repo/Scripts/Quality/SonarQubeServer.ps1" -Start -Initialize -RepoRoot $repo -Context $context
}
finally {
  Exit-QualityLock -Lock $lock
}
```

For a main analysis token, use `analysis-<profile>-main`; candidate token names use `candidate-<sha12>`. Do not delete the database password or admin credential to force recovery. If an existing volume lacks its encrypted database password, or stored admin credentials fail on a non-fresh stack, recover the original credential. Never delete a named volume to fix authentication.

A partial two-profile run retains completed reports and Sonar history, returns nonzero, and is not baseline-eligible. Fix the cause and run a complete batch. If report archival fails, the wrapper keeps worktrees in the private run directory. Confirm their exact path and SHA before manual cleanup.

## Back up and upgrade

Keep a database backup and preserve the four identity-scoped named volumes (`database`, `data`, `extensions`, and `logs`) plus the encrypted local secret/settings directory. Store backups outside the repository and restrict access to the same user. The following PowerShell streams `pg_dump` from the owned database container to a private file. It loads the encrypted database password only into the current process and restores previous environment values afterward.

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
  if (-not (Test-Path -LiteralPath $backupFile) -or (Get-Item -LiteralPath $backupFile).Length -eq 0) {
    throw 'Database backup is missing or empty; do not upgrade.'
  }
}
finally {
  foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
  $databasePassword = $null
}
```

Before a file-level volume backup, stop the owned stack. To upgrade, review SonarQube release notes, change the pinned image in a pull request, create and verify a backup, stop the stack, then start it with `SonarQubeServer.ps1 -Start`. Follow any migration prompt in the loopback UI. Never remove volumes or prune Docker resources during an upgrade. Keep a verified backup until the new version starts and its history is readable. Pinned server, database, MCP, scanner, analyzer, and Node versions live in [`Scripts/Quality/tool-versions.json`](../../Scripts/Quality/tool-versions.json).

## Validate maintenance changes

Run the offline checks from the repository root. They do not contact a SonarQube server:

```powershell
python -m unittest discover -s Scripts/Quality/tests -p 'test_*.py'
pwsh -NoProfile -File Scripts/Quality/tests/Test-SonarQualityModule.ps1
pwsh -NoProfile -File Scripts/Quality/tests/Test-SonarQualityFoundation.ps1
pwsh -NoProfile -File Scripts/Quality/tests/Test-SonarQualityAuditContract.ps1
```

Code or configuration changes also need the [repository local gate](../Test.md#local-gate). Validate the SonarQube Compose file with `yamllint docker/sonarqube/compose.yaml`.
