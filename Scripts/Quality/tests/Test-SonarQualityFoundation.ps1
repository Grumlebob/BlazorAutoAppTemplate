[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Import-Module (Join-Path $PSScriptRoot '../SonarQuality.psm1') -Force -DisableNameChecking

function Assert-Equal {
    param([object]$Actual, [object]$Expected, [string]$Name)
    if ($Actual -cne $Expected) { throw "$Name expected '$Expected', got '$Actual'." }
}

function Assert-Throws {
    param([scriptblock]$Action, [string]$Name)
    try { & $Action; throw "$Name did not fail." }
    catch { if ($_.Exception.Message -eq "$Name did not fail.") { throw } }
}

$identityCases = @(
    @{ Input = 'https://github.com/Owner/Repo.git/'; Expected = 'github.com/owner/repo' },
    @{ Input = 'git@github.com:Owner/Repo.git'; Expected = 'github.com/owner/repo' },
    @{ Input = 'ssh://git@github.com/Owner/Repo.git'; Expected = 'github.com/owner/repo' },
    @{ Input = 'https://user:secret@example.com/Owner/Repo.git'; Expected = 'example.com/Owner/Repo' }
)
foreach ($case in $identityCases) {
    Assert-Equal (ConvertTo-RepositoryIdentity -OriginUrl $case.Input) $case.Expected "identity $($case.Input)"
}
Assert-Throws { ConvertTo-RepositoryIdentity -OriginUrl 'file:///tmp/repo' } 'unsupported origin scheme'
Assert-Throws { ConvertTo-RepositoryIdentity -OriginUrl 'https://github.com/owner' } 'incomplete origin'
if ((ConvertTo-RepositoryIdentity 'https://github.com/fork-a/repo.git') -ceq (ConvertTo-RepositoryIdentity 'git@github.com:fork-b/repo.git')) {
    throw 'Distinct GitHub forks resolved to one repository identity.'
}
if ((ConvertTo-RepositoryIdentity 'https://user:secret@example.com/Owner/Repo.git').Contains('secret')) {
    throw 'Origin credentials leaked into normalized repository identity.'
}

$toolVersions = Get-QualityToolVersions -RepoRoot $repoRoot
Assert-Equal $toolVersions.schema 'grumplates.sonar-tools/1' 'tool manifest schema'
Assert-Equal $toolVersions.node.version '24.21.0' 'pinned Node version'
Assert-Equal $toolVersions.node.npmVersion '12.2.0' 'pinned npm version'
if ($toolVersions.node.windowsArchiveSha256 -notmatch '^[0-9a-f]{64}$') { throw 'Node archive checksum must be 64 lowercase hex characters.' }

$settings = Get-QualitySettingsDocument -Path (Join-Path $repoRoot 'Scripts/Quality/quality-settings.example.json')
Assert-Equal $settings.schema 'grumplates.sonar-settings/1' 'settings schema'
Assert-Equal $settings.hostPort $null 'default host port'

$sentinel = 'quality-secret-sentinel-123456789'
$redacted = Protect-QualityText -Text "prefix $sentinel suffix Authorization: Bearer $sentinel" -Secrets @($sentinel)
if ($redacted.Contains($sentinel)) { throw 'Secret sentinel survived text redaction.' }
if (-not $redacted.Contains('[REDACTED]')) { throw 'Redaction marker is missing.' }

$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) "quality-path-test-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
try {
    $child = Join-Path $temporaryRoot 'safe/report.json'
    Assert-Equal (Test-QualityPathWithinRoot -Path $child -Root $temporaryRoot) $true 'child path containment'
    Assert-Equal (Test-QualityPathWithinRoot -Path (Join-Path $temporaryRoot '../escape') -Root $temporaryRoot) $false 'parent path rejection'
    Assert-Throws { Assert-QualitySafeChildPath -Path (Join-Path $temporaryRoot 'CON.txt') -Root $temporaryRoot } 'reserved path'

    $validSettingsPath = Join-Path $temporaryRoot 'quality-settings.json'
    Set-Content -LiteralPath $validSettingsPath -Value '{"schema":"grumplates.sonar-settings/1","hostPort":9231,"nodeToolchainDirectory":null,"pythonExecutable":null}' -Encoding utf8
    $parsedSettings = Get-QualitySettingsDocument -Path $validSettingsPath
    Assert-Equal $parsedSettings.hostPort 9231 'configured numeric host port'
    Set-Content -LiteralPath $validSettingsPath -Value '{"schema":"grumplates.sonar-settings/1","hostPort":null,"nodeToolchainDirectory":null,"pythonExecutable":null,"serverUrl":"https://example.com"}' -Encoding utf8
    Assert-Throws { Get-QualitySettingsDocument -Path $validSettingsPath } 'unknown setting rejection'

    $privatePath = Join-Path $temporaryRoot 'settings.json'
    $privateContext = [pscustomobject]@{
        BaseDirectory = $temporaryRoot
        PrivateSettingsPath = $privatePath
        PrivateSettings = $null
        RepositoryIdentity = 'github.com/example/repo'
        IdentityHash = 'a' * 64
        HostPort = 9231
    }
    Save-QualityPrivateSettings -Context $privateContext
    $savedPrivateSettings = Get-QualityPrivateSettings -Path $privatePath -RepositoryIdentity $privateContext.RepositoryIdentity -IdentityHash $privateContext.IdentityHash
    Assert-Equal $savedPrivateSettings.hostPort 9231 'persisted host port'
    Assert-Throws { Get-QualityPrivateSettings -Path $privatePath -RepositoryIdentity 'github.com/other/repo' -IdentityHash ('b' * 64) } 'private namespace collision'

    if ($IsWindows) {
        $secretContext = [pscustomobject]@{ SecretsDirectory = Join-Path $temporaryRoot 'secrets' }
        $secretValue = 'dpapi-test-secret-sentinel'
        Set-QualitySecret -Context $secretContext -Name 'test-analysis-token' -Value $secretValue
        $secretFile = Get-QualitySecretPath -Context $secretContext -Name 'test-analysis-token'
        if ((Get-Content -LiteralPath $secretFile -Raw).Contains($secretValue)) { throw 'Encrypted secret file contains plaintext.' }
        Assert-Equal (Get-QualitySecret -Context $secretContext -Name 'test-analysis-token') $secretValue 'DPAPI secret round trip'
        Set-QualitySecret -Context $secretContext -Name 'test-analysis-token' -Value 'replacement-secret'
        Assert-Equal (Get-QualitySecret -Context $secretContext -Name 'test-analysis-token') 'replacement-secret' 'atomic secret replacement'
        Remove-QualitySecret -Context $secretContext -Name 'test-analysis-token'
    }
}
finally { Remove-Item -LiteralPath $temporaryRoot -Recurse -Force }

$contextWithoutReact = Get-QualityContext -RepoRoot $repoRoot
Assert-Equal $contextWithoutReact.NodeExecutable $null 'default context does not resolve Node'
Assert-Equal $contextWithoutReact.NpmCli $null 'default context does not resolve npm'

$context = $contextWithoutReact
# The identity comes from this checkout's origin remote, so assert its shape, not a particular repository.
if ($context.RepositoryIdentity -notmatch '^github\.com/[a-z0-9_.-]+/[a-z0-9_.-]+$') {
    throw "Resolved repository identity is not github.com/<owner>/<repo>: '$($context.RepositoryIdentity)'."
}
Assert-Equal $context.HostPort 9200 'default host port selection'
$nodeRuntime = Get-QualityNodeRuntime -ToolVersions $context.ToolVersions -ConfiguredDirectory $context.NodeToolchainDirectory
Assert-Equal $nodeRuntime.NodeVersion '24.21.0' 'resolved Node version'
Assert-Equal $nodeRuntime.NpmVersion '12.2.0' 'resolved npm version'
$npm = Invoke-QualityProcess -FilePath $nodeRuntime.NodeExecutable -ArgumentList @($nodeRuntime.NpmCli, '--version') -WorkingDirectory $repoRoot -TimeoutSeconds 15
Assert-Equal $npm.ExitCode 0 'pinned npm child exit code'
Assert-Equal $npm.Stdout.Trim() '12.2.0' 'pinned npm child version'

$processRoot = Join-Path ([IO.Path]::GetTempPath()) "quality-process-test-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $processRoot | Out-Null
try {
    $splitSecret = 'split-secret-token'
    $emitSplitSecret = "import sys,time;sys.stdout.write('split-');sys.stdout.flush();time.sleep(0.05);sys.stdout.write('secret-token');sys.stdout.flush()"
    $redactedProcess = Invoke-QualityProcess -FilePath $context.PythonExecutable -ArgumentList @('-c', $emitSplitSecret) `
        -WorkingDirectory $repoRoot -TimeoutSeconds 15 -RedactValues @($splitSecret) -OutputDirectory $processRoot -StepName 'redaction'
    Assert-Equal $redactedProcess.ExitCode 0 'redaction process exit code'
    if ($redactedProcess.Stdout.Contains($splitSecret)) { throw 'Split secret survived process redaction.' }
    $savedLog = Get-Content -LiteralPath (Join-Path $processRoot 'redaction.stdout.log') -Raw
    if ($savedLog.Contains($splitSecret)) { throw 'Split secret survived retained process log redaction.' }

    $failureProcess = Invoke-QualityProcess -FilePath $context.PythonExecutable -ArgumentList @('-c', 'raise SystemExit(7)') `
        -WorkingDirectory $repoRoot -TimeoutSeconds 15
    Assert-Equal $failureProcess.ExitCode 7 'nonzero process result'

    $escapedFile = Join-Path $processRoot 'must-not-exist.txt'
    $sleepAndWrite = 'import pathlib,sys,time;time.sleep(3);pathlib.Path(sys.argv[1]).write_text("escaped",encoding="utf-8")'
    $timedProcess = Invoke-QualityProcess -FilePath $context.PythonExecutable -ArgumentList @('-c', $sleepAndWrite, $escapedFile) `
        -WorkingDirectory $repoRoot -TimeoutSeconds 1
    Assert-Equal $timedProcess.TimedOut $true 'child timeout status'
    Start-Sleep -Seconds 3
    Assert-Equal (Test-Path -LiteralPath $escapedFile) $false 'timed out process tree termination'
}
finally { Remove-Item -LiteralPath $processRoot -Recurse -Force }

$lockRoot = Join-Path ([IO.Path]::GetTempPath()) "quality-lock-test-$([guid]::NewGuid().ToString('N'))"
$lockContext = [pscustomobject]@{ BaseDirectory = $lockRoot; LockPath = Join-Path $lockRoot 'audit.lock' }
$lock = Enter-QualityLock -Context $lockContext -Operation test -RunId lock-holder -TimeoutSeconds 2
try {
    Assert-Throws { Enter-QualityLock -Context $lockContext -Operation test -RunId lock-contender -TimeoutSeconds 1 } 'concurrent audit lock'
}
finally { Exit-QualityLock -Lock $lock }
$releasedLock = Enter-QualityLock -Context $lockContext -Operation test -RunId released-owner -TimeoutSeconds 2
Exit-QualityLock -Lock $releasedLock
Remove-Item -LiteralPath $lockRoot -Recurse -Force

Write-Host 'Sonar quality foundation checks passed.'
