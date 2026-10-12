[CmdletBinding()]
param(
    [ValidateSet('BlazorAuto', 'React', 'Both')][string]$FrontendProfile = 'Both',
    [ValidateSet('Debug', 'Release')][string]$Configuration = 'Release',
    [ValidateRange(1, 60)][int]$TimeoutMinutes = 20,
    [string]$OutputRoot = 'artifacts/quality/quick',
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [object]$Context
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module -Name (Join-Path $PSScriptRoot 'SonarQuality.psm1') -Force
$repoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$standalone = $null -eq $Context
$profiles = if ($FrontendProfile -eq 'Both') { @('BlazorAuto', 'React') } else { @($FrontendProfile) }
if (-not $Context) {
    $Context = Get-QualityContext -RepoRoot $repoRoot
}
if (Test-Path -LiteralPath (Join-Path $repoRoot '.sonarqube')) {
    throw 'An existing .sonarqube directory makes scanner ownership unclear. Preserve it and inspect it before running Quick mode.'
}

$lock = $null
$ownsLock = $false
$lock = Enter-QualityLock -Context $Context -Operation 'Quick' -RunId ([guid]::NewGuid().ToString('N'))
$ownsLock = $true

function Get-GitValue {
    param([string[]]$Arguments)
    $result = Invoke-QualityProcess -FilePath $Context.GitExecutable -ArgumentList $Arguments `
        -WorkingDirectory $repoRoot -TimeoutSeconds 15
    if ($result.ExitCode -ne 0 -or $result.TimedOut) { throw "Git command failed: $($result.Stderr.Trim())" }
    return $result.Stdout.Trim()
}

function Get-QuickConfigurationDigest {
    param([string]$Profile)
    $files = @(
        'Directory.Build.props',
        'Directory.Build.targets',
        'Directory.Packages.props',
        'Scripts/Quality/tool-versions.json'
    )
    $entries = foreach ($relative in $files) {
        $path = Join-Path $repoRoot $relative
        $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($path))).ToLowerInvariant()
        "$relative=$digest"
    }
    $material = "profile=$Profile`nconfiguration=$Configuration`n$($entries -join "`n")"
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($material))).ToLowerInvariant()
}

function Write-QuickSummary {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Value)
    $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        $json = $Value | ConvertTo-Json -Depth 20
        [IO.File]::WriteAllText($temporary, $json, [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    }
    finally { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
}

$summary = $null
$optInRestoreAttempted = $false
$failureMessages = [Collections.Generic.List[string]]::new()
try {
    $sha = Get-GitValue -Arguments @('rev-parse', 'HEAD')
    if ($sha -notmatch '^[0-9a-f]{40}$') { throw "Git returned an invalid HEAD SHA: $sha" }
    $dirty = -not [string]::IsNullOrWhiteSpace((Get-GitValue -Arguments @('status', '--porcelain', '--untracked-files=normal')))
    $runId = "quick-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))-$($sha.Substring(0, 12))-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
    $outputBase = if ([IO.Path]::IsPathRooted($OutputRoot)) { $OutputRoot } else { Join-Path $repoRoot $OutputRoot }
    $outputBase = Assert-QualitySafeChildPath -Path $outputBase -Root $repoRoot
    $runDirectory = Join-Path $outputBase $runId
    if (Test-Path -LiteralPath $runDirectory) { throw "Quick run output already exists: $runDirectory" }
    New-Item -ItemType Directory -Force -Path $runDirectory | Out-Null

    $summary = [ordered]@{
        schema = 'blazorautoapp.sonar-quick-audit/1'
        mode = 'Quick'
        runId = $runId
        repositoryIdentity = $Context.RepositoryIdentity
        driverSha = $sha
        analyzedSha = $sha
        dirty = $dirty
        frontendProfiles = $profiles
        configuration = $Configuration
        analyzerVersion = [string]$Context.ToolVersions.analyzer.version
        startedUtc = [DateTime]::UtcNow.ToString('o')
        finishedUtc = $null
        outcome = 'running'
        failureReason = $null
        baselineEligible = $false
        normalRestore = $null
        outputs = [ordered]@{ root = [IO.Path]::GetRelativePath($repoRoot, $runDirectory).Replace('\', '/') }
        profiles = [Collections.Generic.List[object]]::new()
    }

    $environment = @{
        FrontendProfile = $null
        RunSonarAnalyzers = $null
    }
    foreach ($profile in $profiles) {
        $profileDirectory = Join-Path $runDirectory $profile
        $sarifDirectory = Join-Path $profileDirectory 'sarif'
        $logDirectory = Join-Path $profileDirectory 'logs'
        New-Item -ItemType Directory -Force -Path $sarifDirectory, $logDirectory | Out-Null
        $sarifArgument = $sarifDirectory.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        $record = [ordered]@{
            frontendProfile = $profile
            status = 'failed'
            startedUtc = [DateTime]::UtcNow.ToString('o')
            finishedUtc = $null
            restore = $null
            build = $null
            findings = $null
            configurationDigest = Get-QuickConfigurationDigest -Profile $profile
            failureReason = $null
            summaryJson = $null
            summaryMarkdown = $null
            sarifFiles = @()
        }
        try {
            if (Test-Path -LiteralPath (Join-Path $repoRoot '.sonarqube')) {
                throw 'An active or stale .sonarqube directory appeared before Quick build; refusing to overlap scanner state.'
            }
            $optInRestoreAttempted = $true
            $restoreArgs = @(
                'restore', (Join-Path $repoRoot 'BlazorAutoApp.sln'), '--verbosity', 'minimal',
                "-p:FrontendProfile=$profile", '-p:RunSonarAnalyzers=true', "-p:SonarErrorLogDirectory=$sarifArgument"
            )
            $restore = Invoke-QualityProcess -FilePath $Context.DotnetExecutable -ArgumentList $restoreArgs `
                -WorkingDirectory $repoRoot -TimeoutSeconds ($TimeoutMinutes * 60) -Environment $environment `
                -OutputDirectory $logDirectory -StepName 'restore' -RedactValues @()
            $record.restore = [ordered]@{ exitCode = $restore.ExitCode; timedOut = $restore.TimedOut; durationSeconds = $restore.DurationSeconds }
            if ($restore.TimedOut -or $restore.ExitCode -ne 0) { throw "Analyzer restore failed (exit $($restore.ExitCode), timeout $($restore.TimedOut))." }

            $buildArgs = @(
                'build', (Join-Path $repoRoot 'BlazorAutoApp.sln'), '--configuration', $Configuration,
                '--no-restore', '--no-incremental', '--disable-build-servers', '-nr:false',
                "-p:FrontendProfile=$profile", '-p:RunSonarAnalyzers=true', "-p:SonarErrorLogDirectory=$sarifArgument"
            )
            $build = Invoke-QualityProcess -FilePath $Context.DotnetExecutable -ArgumentList $buildArgs `
                -WorkingDirectory $repoRoot -TimeoutSeconds ($TimeoutMinutes * 60) -Environment $environment `
                -OutputDirectory $logDirectory -StepName 'build' -RedactValues @()
            $record.build = [ordered]@{ exitCode = $build.ExitCode; timedOut = $build.TimedOut; durationSeconds = $build.DurationSeconds }
            if ($build.TimedOut -or $build.ExitCode -ne 0) { throw "Analyzer build failed (exit $($build.ExitCode), timeout $($build.TimedOut))." }

            $sarifFiles = @(Get-ChildItem -LiteralPath $sarifDirectory -Filter '*.sarif' -File)
            if ($sarifFiles.Count -eq 0 -or @($sarifFiles | Where-Object { $_.Length -eq 0 }).Count -gt 0) {
                throw 'Analyzer build produced missing or empty SARIF output.'
            }
            $record.sarifFiles = @($sarifFiles | ForEach-Object { [IO.Path]::GetRelativePath($repoRoot, $_.FullName).Replace('\', '/') })
            $summarizer = Join-Path $PSScriptRoot 'summarize_sarif.py'
            $summaryJson = Join-Path $profileDirectory 'summary.json'
            $summaryArgs = @(
                $summarizer, '--sarif-dir', $sarifDirectory, '--repo-root', $repoRoot,
                '--out-dir', $profileDirectory, '--repository-identity', $Context.RepositoryIdentity,
                '--frontend-profile', $profile, '--sha', $sha, '--configuration', $Configuration,
                '--configuration-digest', $record.configurationDigest,
                '--analyzer-version', [string]$Context.ToolVersions.analyzer.version, '--run-id', $runId
            )
            if ($dirty) { $summaryArgs += '--dirty' }
            $summarize = Invoke-QualityProcess -FilePath $Context.PythonExecutable -ArgumentList $summaryArgs `
                -WorkingDirectory $repoRoot -TimeoutSeconds 120 -OutputDirectory $logDirectory -StepName 'summarize'
            if ($summarize.TimedOut -or $summarize.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $summaryJson -PathType Leaf)) {
                throw "SARIF summary failed (exit $($summarize.ExitCode), timeout $($summarize.TimedOut))."
            }
            $profileSummary = Get-Content -LiteralPath $summaryJson -Raw | ConvertFrom-Json
            if ($profileSummary.schema -ne 'blazorautoapp.sonar-quick-summary/1' -or
                $profileSummary.sha -ne $sha -or $profileSummary.frontendProfile -ne $profile -or
                $profileSummary.dirty -ne $dirty -or $profileSummary.configurationDigest -ne $record.configurationDigest) {
                throw 'SARIF summary identity does not match the Quick run.'
            }
            $record.findings = $profileSummary.totals
            $record.summaryJson = [IO.Path]::GetRelativePath($repoRoot, $summaryJson).Replace('\', '/')
            $record.summaryMarkdown = [IO.Path]::GetRelativePath($repoRoot, (Join-Path $profileDirectory 'summary.md')).Replace('\', '/')
            $record.status = 'succeeded'
        }
        catch {
            $record.failureReason = Protect-QualityText -Text $_.Exception.Message
            [void]$failureMessages.Add("${profile}: $($record.failureReason)")
        }
        finally {
            $record.finishedUtc = [DateTime]::UtcNow.ToString('o')
            [void]$summary.profiles.Add([pscustomobject]$record)
        }
    }

    if ($failureMessages.Count -gt 0) {
        $summary.outcome = 'failed'
        $summary.failureReason = $failureMessages -join ' '
    }
    else { $summary.outcome = 'succeeded' }
}
catch {
    $message = Protect-QualityText -Text $_.Exception.Message
    if ($null -eq $summary) {
        $summary = [ordered]@{
            schema = 'blazorautoapp.sonar-quick-audit/1'
            mode = 'Quick'
            runId = $null
            repositoryIdentity = $Context.RepositoryIdentity
            driverSha = $null
            analyzedSha = $null
            dirty = $null
            frontendProfiles = $profiles
            configuration = $Configuration
            analyzerVersion = [string]$Context.ToolVersions.analyzer.version
            startedUtc = [DateTime]::UtcNow.ToString('o')
            finishedUtc = $null
            outcome = 'failed'
            failureReason = $message
            baselineEligible = $false
            normalRestore = $null
            outputs = @{}
            profiles = @()
        }
    }
    else {
        $summary.outcome = 'failed'
        $summary.failureReason = if ($summary.failureReason) { "$($summary.failureReason) $message" } else { $message }
    }
}
finally {
    if ($optInRestoreAttempted) {
        try {
            $selectedProfile = (Get-Content -LiteralPath (Join-Path $repoRoot 'frontend-profile.txt') -Raw).Trim()
            if ($selectedProfile -notin @('BlazorAuto', 'React')) { throw "Invalid tracked frontend profile '$selectedProfile'." }
            $normalArgs = @(
                'restore', (Join-Path $repoRoot 'BlazorAutoApp.sln'), '--verbosity', 'minimal',
                "-p:FrontendProfile=$selectedProfile", '-p:RunSonarAnalyzers=false'
            )
            $normalRestore = Invoke-QualityProcess -FilePath $Context.DotnetExecutable -ArgumentList $normalArgs `
                -WorkingDirectory $repoRoot -TimeoutSeconds ($TimeoutMinutes * 60) -Environment $environment `
                -OutputDirectory $(if ($summary -and $summary.outputs.root) { Join-Path $repoRoot $summary.outputs.root } else { $repoRoot }) `
                -StepName 'normal-restore'
            $summary.normalRestore = [ordered]@{ profile = $selectedProfile; exitCode = $normalRestore.ExitCode; timedOut = $normalRestore.TimedOut; durationSeconds = $normalRestore.DurationSeconds }
            if ($normalRestore.TimedOut -or $normalRestore.ExitCode -ne 0) {
                $summary.outcome = 'failed'
                $summary.failureReason = if ($summary.failureReason) { "$($summary.failureReason) Normal restore failed." } else { 'Normal restore failed after Quick mode.' }
            }
        }
        catch {
            $summary.outcome = 'failed'
            $restoreError = Protect-QualityText -Text $_.Exception.Message
            $summary.failureReason = if ($summary.failureReason) { "$($summary.failureReason) Normal restore failed: $restoreError" } else { "Normal restore failed: $restoreError" }
        }
    }
    if ($summary) {
        $summary.finishedUtc = [DateTime]::UtcNow.ToString('o')
        if ($summary.runId -and $summary.outputs.root) {
            try { Write-QuickSummary -Path (Join-Path (Join-Path $repoRoot $summary.outputs.root) 'quick-audit.json') -Value $summary }
            catch { $summary.outcome = 'failed'; $summary.failureReason = 'Could not write Quick audit summary.' }
        }
    }
    if ($ownsLock -and $lock) { Exit-QualityLock -Lock $lock }
}

if ($standalone -and $summary.outcome -ne 'succeeded') { throw "Quick quality audit failed: $($summary.failureReason)" }
return [pscustomobject]$summary
