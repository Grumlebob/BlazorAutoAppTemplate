[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$qualityRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$audit = Join-Path $qualityRoot 'Invoke-CodeQualityAudit.ps1'
$quick = Join-Path $qualityRoot 'Invoke-SonarAnalyzerBuild.ps1'
$server = Join-Path $qualityRoot 'SonarQubeServer.ps1'

function Assert-ThrowsWith {
    param([Parameter(Mandatory)][scriptblock]$Action, [Parameter(Mandatory)][string]$Pattern)
    try {
        & $Action
        throw "Expected failure matching '$Pattern'."
    }
    catch {
        if ($_.Exception.Message -like "Expected failure matching '$Pattern'.") { throw }
        if ($_.Exception.Message -notmatch $Pattern) { throw "Unexpected failure: $($_.Exception.Message)" }
    }
}

$previousRunAnalyzers = [Environment]::GetEnvironmentVariable('RunSonarAnalyzers', 'Process')
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) "quality-audit-contract-$([guid]::NewGuid().ToString('N'))"
$privateRoot = "$temporaryRoot-private"
try {
    [Environment]::SetEnvironmentVariable('RunSonarAnalyzers', 'TrUe', 'Process')
    Assert-ThrowsWith -Pattern 'RunSonarAnalyzers=true' -Action { & $audit -Mode Full }

    [Environment]::SetEnvironmentVariable('RunSonarAnalyzers', $null, 'Process')
    Assert-ThrowsWith -Pattern 'available only with -Mode Full' -Action { & $audit -Mode Quick -Candidate }

    New-Item -ItemType Directory -Force -Path (Join-Path $temporaryRoot '.sonarqube') | Out-Null
    $sentinelPath = Join-Path $temporaryRoot '.sonarqube/ownership-sentinel.txt'
    [IO.File]::WriteAllText($sentinelPath, 'preserve')
    Assert-ThrowsWith -Pattern 'existing .sonarqube directory' -Action {
        & $quick -FrontendProfile BlazorAuto -RepoRoot $temporaryRoot -Context ([pscustomobject]@{})
    }
    if ([IO.File]::ReadAllText($sentinelPath) -ne 'preserve') { throw 'Quick mode changed an unowned scanner sentinel.' }
    Remove-Item -LiteralPath (Join-Path $temporaryRoot '.sonarqube') -Recurse -Force

    New-Item -ItemType Directory -Force -Path $temporaryRoot | Out-Null
    $git = (Get-Command git.exe, git -CommandType Application | Select-Object -First 1).Source
    $powershell = (Get-Command pwsh.exe, pwsh -CommandType Application | Select-Object -First 1).Source
    foreach ($relative in @('BlazorAutoApp.sln', 'Directory.Build.props', 'Directory.Build.targets',
            'Directory.Packages.props', 'frontend-profile.txt', 'Scripts/Quality/tool-versions.json')) {
        $path = Join-Path $temporaryRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path) | Out-Null
        [IO.File]::WriteAllText($path, $(if ($relative -eq 'frontend-profile.txt') { 'React' } else { 'fixture' }))
    }
    # Fixture git commands must not follow inherited GIT_* variables into the caller's repository.
    Get-ChildItem Env: | Where-Object { $_.Name -like 'GIT_*' } | ForEach-Object { Remove-Item -Path "Env:$($_.Name)" }
    & $git -C $temporaryRoot init --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize the temporary Quick-driver fixture repository.' }
    & $git -C $temporaryRoot config user.name 'Quality Test'
    & $git -C $temporaryRoot config user.email 'quality-test@example.invalid'
    & $git -C $temporaryRoot add -- .
    & $git -C $temporaryRoot commit --quiet -m 'test fixture'
    if ($LASTEXITCODE -ne 0) { throw 'Could not commit the temporary Quick-driver fixture.' }

    New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null
    $serverContext = [pscustomobject]@{
        RepositoryIdentity = 'github.com/quality-test/fixture'
        ComposeProject = 'sonarqube-quality-test-01234567'
        ComposeNetwork = 'sonarqube-quality-test-01234567-network'
        ComposePath = Join-Path $temporaryRoot 'docker/sonarqube/compose.yaml'
        BaseDirectory = $privateRoot
        SecretsDirectory = Join-Path $privateRoot 'secrets'
        LockPath = Join-Path $privateRoot 'audit.lock'
        IdentityHash = 'a' * 64
        HostPort = 9299
        BaseUrl = 'http://127.0.0.1:9299'
        DockerExecutable = $git
    }
    Assert-ThrowsWith -Pattern 'Choose exactly one action' -Action {
        & $server -Status -Stop -RepoRoot $temporaryRoot -Context $serverContext
    }
    Assert-ThrowsWith -Pattern 'Use only one of -Initialize' -Action {
        & $server -Start -Initialize -ApplyProfile -RepoRoot $temporaryRoot -Context $serverContext
    }
    Assert-ThrowsWith -Pattern 'Docker command failed' -Action {
        & $server -Status -RepoRoot $temporaryRoot -Context $serverContext
    }

    $fakeContext = [pscustomobject]@{
        BaseDirectory = $privateRoot
        LockPath = Join-Path $privateRoot 'audit.lock'
        GitExecutable = $git
        DotnetExecutable = $powershell
        RepositoryIdentity = 'github.com/quality-test/fixture'
        ToolVersions = [pscustomobject]@{ analyzer = [pscustomobject]@{ version = '10.35.0.4138' } }
    }
    $failedQuick = & $quick -FrontendProfile Both -RepoRoot $temporaryRoot -Context $fakeContext
    if ($failedQuick.outcome -ne 'failed' -or @($failedQuick.profiles).Count -ne 2) {
        throw 'Quick failure fixture did not retain both profile outcomes.'
    }
    if (@($failedQuick.profiles | Where-Object { $_.restore.exitCode -eq 0 }).Count -ne 0) {
        throw 'Quick failure fixture unexpectedly accepted a failed analyzer restore.'
    }
    if ($failedQuick.normalRestore.profile -ne 'React' -or $failedQuick.normalRestore.exitCode -eq 0) {
        throw 'Quick failure fixture did not record the final selected-profile normal restore attempt.'
    }
}
finally {
    [Environment]::SetEnvironmentVariable('RunSonarAnalyzers', $previousRunAnalyzers, 'Process')
    foreach ($path in @($temporaryRoot, $privateRoot)) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    }
}

Write-Host 'Sonar quality audit contract checks passed.'
