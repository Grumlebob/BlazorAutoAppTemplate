[CmdletBinding()]
param(
    [ValidateSet('Quick', 'Full')][string]$Mode = 'Full',
    [ValidateSet('BlazorAuto', 'React', 'Both')][string]$FrontendProfile = 'Both',
    [switch]$Candidate,
    [switch]$KeepServerRunning,
    [string]$SettingsPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($Mode -eq 'Quick' -and ($Candidate -or $KeepServerRunning)) {
    throw '-Candidate and -KeepServerRunning are available only with -Mode Full.'
}
if ($Mode -eq 'Full' -and $env:RunSonarAnalyzers -eq 'true') {
    throw 'RunSonarAnalyzers=true is active. Clear it before a Full audit.'
}

$modulePath = Join-Path $PSScriptRoot 'SonarQuality.psm1'
Import-Module -Name $modulePath -Force -DisableNameChecking
$invokingRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$profiles = if ($FrontendProfile -eq 'Both') { @('BlazorAuto', 'React') } else { @($FrontendProfile) }
$context = Get-QualityContext -RepoRoot $invokingRoot -SettingsPath $SettingsPath

if ($Mode -eq 'Quick') {
    $quickScript = Join-Path $PSScriptRoot 'Invoke-SonarAnalyzerBuild.ps1'
    $quick = & $quickScript -FrontendProfile $FrontendProfile -RepoRoot $invokingRoot -Context $context
    if ($quick.outcome -ne 'succeeded') { throw "Quick audit failed: $($quick.failureReason)" }
    return $quick
}

if (-not $context.DockerExecutable) { throw 'Full audit requires the Docker CLI.' }
if (-not $IsWindows) { throw 'Full audit credentials use Windows DPAPI; run Full mode with PowerShell 7 on Windows.' }
$git = [string]$context.GitExecutable
$runId = "full-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))-$([guid]::NewGuid().ToString('N'))"
$lock = Enter-QualityLock -Context $context -Operation 'FullAudit' -RunId $runId
$startedUtc = [DateTime]::UtcNow
$runDirectory = $null
$batch = $null
$sourceSha = $null
$driverSha = $null
$worktrees = [Collections.Generic.List[object]]::new()
$archiveVerified = $false
$serverWasRunning = $false
$serverStartedByCommand = $false
$serverStartAttempted = $false
$failureMessages = [Collections.Generic.List[string]]::new()

function Invoke-AuditGit {
    param([Parameter(Mandatory)][string[]]$Arguments, [string]$WorkingDirectory = $invokingRoot)
    $result = Invoke-QualityProcess -FilePath $git -ArgumentList (@('-c', 'core.longpaths=true') + $Arguments) `
        -WorkingDirectory $WorkingDirectory -TimeoutSeconds 120
    if ($result.TimedOut -or $result.ExitCode -ne 0) {
        $detail = Protect-QualityText -Text (($result.Stderr + ' ' + $result.Stdout).Trim())
        throw "Git $($Arguments[0]) failed (exit $($result.ExitCode), timeout $($result.TimedOut)): $detail"
    }
    return $result.Stdout.Trim()
}

function Write-AuditJson {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Value)
    $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    }
    finally { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
}

function Get-OwnedSonarContainer {
    $environment = @{
        SONARQUBE_DB_PASSWORD = 'quality-compose-inspection'
        SONARQUBE_HOST_PORT = [string]$context.HostPort
        SONARQUBE_IDENTITY_HASH = $context.IdentityHash
        SONARQUBE_NETWORK_NAME = $context.ComposeNetwork
        SONARQUBE_COMPOSE_PROJECT = $context.ComposeProject
    }
    $arguments = @('compose', '--project-name', $context.ComposeProject, '--file', $context.ComposePath, 'ps', '-q', 'sonarqube')
    $result = Invoke-QualityProcess -FilePath $context.DockerExecutable -ArgumentList $arguments `
        -WorkingDirectory $context.BaseDirectory -TimeoutSeconds 30 -Environment $environment
    if ($result.TimedOut -or $result.ExitCode -ne 0) {
        throw 'Could not establish ownership of the repository-scoped SonarQube container.'
    }
    return $result.Stdout.Trim()
}

function Invoke-ServerAction {
    param([Parameter(Mandatory)][string]$Script, [Parameter(Mandatory)][hashtable]$Parameters)
    $Parameters.RepoRoot = $context.RepoRoot
    $Parameters.Context = $context
    & $Script @Parameters | Out-Host
}

function ConvertTo-AuditSafeMessage {
    param([AllowEmptyString()][string]$Text)
    $safe = Protect-QualityText -Text $Text
    foreach ($privatePath in @($invokingRoot, $context.BaseDirectory, $runDirectory, $context.RepoRoot) | Where-Object { $_ }) {
        $safe = $safe.Replace([string]$privatePath, '[LOCAL_PATH]', [StringComparison]::OrdinalIgnoreCase)
    }
    $safe = [regex]::Replace($safe, '(?i)\bfile:/{2,3}[A-Z]:/[^\s"<>]+', '[LOCAL_PATH]')
    $safe = [regex]::Replace($safe, '(?i)(?:[A-Z]:\\|\\\\)[^\s"<>]+', '[LOCAL_PATH]')
    $safe = [regex]::Replace($safe, '(?<!\w)/(?:home|users|mnt|tmp)/[^\s"<>]+', '[LOCAL_PATH]')
    $safe = [regex]::Replace($safe, '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[EMAIL]')
    return $safe
}

function Protect-AuditJsonValue {
    param([Parameter(Mandatory)][AllowNull()]$Value)
    if ($Value -is [string]) { return ConvertTo-AuditSafeMessage -Text $Value }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in @($Value.Keys)) { $Value[$key] = Protect-AuditJsonValue -Value $Value[$key] }
        return $Value
    }
    if ($Value -is [System.Collections.IList]) {
        for ($index = 0; $index -lt $Value.Count; $index++) { $Value[$index] = Protect-AuditJsonValue -Value $Value[$index] }
        return ,$Value
    }
    return $Value
}

function Copy-SanitizedJson {
    param([Parameter(Mandatory)][string]$Source, [Parameter(Mandatory)][string]$Destination)
    $document = Get-Content -LiteralPath $Source -Raw | ConvertFrom-Json -AsHashtable
    Write-AuditJson -Path $Destination -Value (Protect-AuditJsonValue -Value $document)
}

function Get-SecretValuesForArchive {
    $values = [Collections.Generic.List[string]]::new()
    foreach ($profile in $profiles) {
        $suffix = $profile.ToLowerInvariant()
        $names = @("reader-$suffix-token")
        if ($Candidate) {
            $names += "analysis-$suffix-candidate-$($sourceSha.Substring(0, 12))"
        }
        else { $names += "analysis-$suffix-main" }
        foreach ($name in $names) {
            $value = Get-QualitySecret -Context $context -Name $name -Optional
            if ($value) { $values.Add($value) }
        }
    }
    return @($values)
}

function Add-AuditJsonStrings {
    param([AllowNull()]$Value, [Parameter(Mandatory)][AllowEmptyCollection()][Collections.Generic.List[string]]$Strings)
    if ($null -eq $Value) { return }
    if ($Value -is [string]) { $Strings.Add($Value); return }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            $Strings.Add([string]$key)
            Add-AuditJsonStrings -Value $Value[$key] -Strings $Strings
        }
        return
    }
    if ($Value -is [System.Collections.IList]) {
        foreach ($item in $Value) { Add-AuditJsonStrings -Value $item -Strings $Strings }
    }
}

function Assert-ArchiveSanitized {
    param([Parameter(Mandatory)][string]$Directory)
    $secrets = @(Get-SecretValuesForArchive)
    $privateValues = @($invokingRoot, $context.BaseDirectory) | Where-Object { $_ }
    foreach ($file in Get-ChildItem -LiteralPath $Directory -File -Recurse) {
        $content = [IO.File]::ReadAllText($file.FullName)
        $textValues = [Collections.Generic.List[string]]::new()
        if ($file.Extension -eq '.json') {
            try {
                $document = ConvertFrom-Json -InputObject $content -AsHashtable
                Add-AuditJsonStrings -Value $document -Strings $textValues
            }
            catch { throw "Archive hygiene check found invalid JSON in '$($file.Name)'." }
        }
        else { $textValues.Add($content) }
        foreach ($textValue in $textValues) {
            foreach ($secret in $secrets) {
                if ($textValue.Contains($secret, [StringComparison]::Ordinal)) { throw "Archive hygiene check found a credential in '$($file.Name)'." }
            }
            foreach ($privateValue in $privateValues) {
                if ($textValue.Contains($privateValue, [StringComparison]::OrdinalIgnoreCase)) { throw "Archive hygiene check found a machine-local path in '$($file.Name)'." }
            }
            if ($textValue -match '(?i)\bfile:/{2,3}[A-Z]:/[^\s"<>]+') { throw "Archive hygiene check found a Windows path in '$($file.Name)'." }
            if ($textValue -match '(?i)(?:[A-Z]:\\|\\\\)[^\s"<>]+') { throw "Archive hygiene check found a Windows path in '$($file.Name)'." }
            if ($textValue -match '(?<!\w)/(?:home|users|mnt|tmp)/[^\s"<>]+') { throw "Archive hygiene check found a Unix user or temporary path in '$($file.Name)'." }
            if ($textValue -match '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b') { throw "Archive hygiene check found an email address in '$($file.Name)'." }
        }
    }
}

function Write-BatchMarkdown {
    if (-not $batch) { return }
    $lines = [Collections.Generic.List[string]]::new()
    $lines.Add('# SonarQube audit')
    $lines.Add('')
    $lines.Add("- Outcome: **$($batch.outcome)**")
    $lines.Add("- Mode: $($batch.mode)")
    $lines.Add("- Repository: $($batch.repositoryIdentity)")
    $lines.Add("- SHA: ``$($batch.analyzedSha)``")
    $lines.Add("- Candidate: $($batch.candidate)")
    $lines.Add("- Baseline eligible: $($batch.baselineEligible)")
    $lines.Add('')
    $lines.Add('| Profile | Outcome | Project | Tests | Coverage | Gate | Report |')
    $lines.Add('|---|---|---|---|---|---|---|')
    foreach ($profile in $batch.profiles) {
        $report = if ($profile.archiveReport) { "[report]($($profile.archiveReport))" } else { 'unavailable' }
        $tests = if ($profile.dotnetTests) { "$($profile.dotnetTests.passed) passed, $($profile.dotnetTests.skipped) skipped" } else { 'unavailable' }
        $coverage = if ($profile.coverageStatus) { $profile.coverageStatus } else { 'unavailable' }
        $gate = if ($profile.qualityGate) { $profile.qualityGate } else { 'unavailable' }
        $lines.Add("| $($profile.frontendProfile) | $($profile.outcome) | ``$($profile.projectKey)`` | $tests | $coverage | $gate | $report |")
    }
    $lines.Add('')
    if ($batch.failureReason) { $lines.Add("Failure: $($batch.failureReason)"); $lines.Add('') }
    $lines.Add('The SonarQube quality gate is informational. Existing build and test checks remain authoritative.')
    [IO.File]::WriteAllLines((Join-Path $runDirectory 'batch.md'), $lines, [Text.UTF8Encoding]::new($false))
}

function New-ArchiveManifest {
    param([Parameter(Mandatory)][string]$Directory)
    $entries = [Collections.Generic.List[object]]::new()
    foreach ($file in Get-ChildItem -LiteralPath $Directory -File -Recurse | Where-Object { $_.Name -ne 'manifest.json' }) {
        $relative = [IO.Path]::GetRelativePath($Directory, $file.FullName).Replace('\', '/')
        $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($file.FullName))).ToLowerInvariant()
        $entries.Add([ordered]@{ path = $relative; sha256 = $digest })
    }
    Write-AuditJson -Path (Join-Path $Directory 'manifest.json') -Value ([ordered]@{
        schema = 'blazorautoapp.sonar-archive/1'
        runId = $batch.runId
        files = @($entries)
    })
}

function Verify-ArchiveManifest {
    param([Parameter(Mandatory)][string]$Directory)
    $manifestPath = Join-Path $Directory 'manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema -ne 'blazorautoapp.sonar-archive/1' -or $manifest.runId -ne $batch.runId) { throw 'Archive manifest identity does not match the audit.' }
    foreach ($entry in $manifest.files) {
        $path = Join-Path $Directory ($entry.path.Replace('/', [IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Archived file is missing: $($entry.path)" }
        $actual = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($path))).ToLowerInvariant()
        if ($actual -ne $entry.sha256) { throw "Archived file digest mismatch: $($entry.path)" }
    }
    if (@(Get-ChildItem -LiteralPath $Directory -File -Recurse | Where-Object { $_.Name -ne 'manifest.json' }).Count -ne @($manifest.files).Count) {
        throw 'Archive contains files outside its verified manifest.'
    }
}

function Archive-Audit {
    $archive = Join-Path $context.ReportsDirectory $batch.runId
    if (Test-Path -LiteralPath $archive) { throw "Archive destination already exists; preserving it: $archive" }
    New-Item -ItemType Directory -Force -Path $archive | Out-Null
    foreach ($name in @('summary.json', 'batch.md')) {
        $source = Join-Path $runDirectory $name
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            if ($name.EndsWith('.json')) { Copy-SanitizedJson -Source $source -Destination (Join-Path $archive $name) }
            else { Copy-Item -LiteralPath $source -Destination (Join-Path $archive $name) }
        }
    }
    foreach ($profile in $batch.profiles) {
        $profileName = [string]$profile.frontendProfile
        $sourceDirectory = Join-Path $runDirectory $profileName
        $targetDirectory = Join-Path $archive $profileName
        if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) { continue }
        New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
        foreach ($name in @('report.json', 'report.md', 'effective-settings.json', 'summary.json')) {
            $source = Join-Path $sourceDirectory $name
            if (Test-Path -LiteralPath $source -PathType Leaf) {
                if ($name.EndsWith('.json')) { Copy-SanitizedJson -Source $source -Destination (Join-Path $targetDirectory $name) }
                else { Copy-Item -LiteralPath $source -Destination (Join-Path $targetDirectory $name) }
            }
        }
        $profileSummary = Join-Path $targetDirectory 'summary.json'
        $profileReport = Join-Path $targetDirectory 'report.json'
        if ((Test-Path -LiteralPath $profileSummary -PathType Leaf) -and (Test-Path -LiteralPath $profileReport -PathType Leaf)) {
            $summaryDocument = Get-Content -LiteralPath $profileSummary -Raw | ConvertFrom-Json -AsHashtable
            $summaryDocument.reportDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($profileReport))).ToLowerInvariant()
            Write-AuditJson -Path $profileSummary -Value $summaryDocument
        }
        if (Test-Path -LiteralPath (Join-Path $targetDirectory 'report.md')) { $profile.archiveReport = "$profileName/report.md" }
    }
    Assert-ArchiveSanitized -Directory $archive
    New-ArchiveManifest -Directory $archive
    Verify-ArchiveManifest -Directory $archive
    $batch.outputs.archive = [IO.Path]::GetRelativePath($context.ReportsDirectory, $archive).Replace('\', '/')
    $batch.archiveVerified = $true
    return $archive
}

function Remove-AuditWorktrees {
    foreach ($entry in @($worktrees)) {
        $path = [IO.Path]::GetFullPath($entry.path)
        if (-not (Test-QualityPathWithinRoot -Path $path -Root (Join-Path $runDirectory 'worktrees'))) {
            throw "Refusing to remove a worktree outside this run: $path"
        }
        if (-not (Test-Path -LiteralPath $path -PathType Container)) { continue }
        $head = Invoke-AuditGit -Arguments @('-C', $path, 'rev-parse', 'HEAD')
        if ($head -ne $sourceSha) { throw "Worktree HEAD changed; preserving it: $path" }
        $status = Invoke-AuditGit -Arguments @('-C', $path, 'status', '--porcelain', '--untracked-files=normal')
        if (-not [string]::IsNullOrWhiteSpace($status)) { throw "Worktree has tracked or untracked changes; preserving it: $path" }
        $listed = Invoke-AuditGit -Arguments @('-C', $invokingRoot, 'worktree', 'list', '--porcelain')
        $pathLine = "worktree $($path.Replace('\', '/'))"
        $listedLines = @($listed -split "`r?`n")
        if ($pathLine -notin $listedLines) {
            $pathLineWindows = "worktree $path"
            if ($pathLineWindows -notin $listedLines) { throw "Git no longer identifies this run-created worktree: $path" }
        }
        $remove = Invoke-QualityProcess -FilePath $git -ArgumentList @('-c', 'core.longpaths=true', '-C', $invokingRoot, 'worktree', 'remove', '--force', $path) `
            -WorkingDirectory $invokingRoot -TimeoutSeconds 120
        if ($remove.TimedOut -or $remove.ExitCode -ne 0) { throw "Could not remove verified clean worktree '$path'." }
        $entry.removed = $true
    }
}

try {
    $driverSha = Invoke-AuditGit -Arguments @('-C', $invokingRoot, 'rev-parse', 'HEAD')
    if ($driverSha -notmatch '^[0-9a-f]{40}$') { throw 'Invoking checkout HEAD is not a full commit SHA.' }
    if ($Candidate) {
        $dirty = Invoke-AuditGit -Arguments @('-C', $invokingRoot, 'status', '--porcelain', '--untracked-files=normal')
        if (-not [string]::IsNullOrWhiteSpace($dirty)) { throw '-Candidate requires a clean committed checkout; ignored build output is allowed.' }
        $sourceSha = $driverSha
    }
    else {
        $null = Invoke-AuditGit -Arguments @('-C', $invokingRoot, 'fetch', 'origin', 'refs/heads/main')
        $sourceSha = Invoke-AuditGit -Arguments @('-C', $invokingRoot, 'rev-parse', 'FETCH_HEAD^{commit}')
    }
    if ($sourceSha -notmatch '^[0-9a-f]{40}$') { throw 'Selected audit source is not a full commit SHA.' }

    $requiredFiles = @(
        'Scripts/Quality/Invoke-CodeQualityAudit.ps1', 'Scripts/Quality/Invoke-SonarAnalyzerBuild.ps1',
        'Scripts/Quality/Invoke-SonarAnalysis.ps1', 'Scripts/Quality/SonarQuality.psm1',
        'Scripts/Quality/SonarQubeServer.ps1', 'Scripts/Quality/sonar_report.py',
        'Scripts/Quality/summarize_sarif.py', 'Scripts/Quality/probe_sonar_mcp.py',
        'Scripts/Quality/Start-SonarQubeMcp.ps1', 'Scripts/Quality/validate_dotnet_coverage.py',
        'Scripts/Quality/validate_vitest_results.py', 'Scripts/Quality/normalize_lcov_paths.py',
        'Scripts/Quality/tool-versions.json', 'Scripts/Quality/quality-settings.example.json',
        'Scripts/Quality/SonarQube/SonarQube.Analysis.xml', 'Scripts/Quality/SonarQube/profile-overrides.json',
        'BlazorAutoApp.React/package.json', 'BlazorAutoApp.React/package-lock.json',
        'BlazorAutoApp.React/vitest.config.ts', 'docker/sonarqube/compose.yaml'
    )
    foreach ($relative in $requiredFiles) {
        $check = Invoke-QualityProcess -FilePath $git -ArgumentList @('-C', $invokingRoot, 'cat-file', '-e', "$($sourceSha):$relative") `
            -WorkingDirectory $invokingRoot -TimeoutSeconds 15
        if ($check.ExitCode -ne 0) { throw "Selected commit $sourceSha does not contain required audit source '$relative'." }
    }

    $shortSha = $sourceSha.Substring(0, 12)
    $runId = "full-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))-$shortSha-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
    $runDirectory = Join-Path $context.RunsDirectory $runId
    New-Item -ItemType Directory -Force -Path (Join-Path $runDirectory 'worktrees') | Out-Null
    $batch = [ordered]@{
        schema = 'blazorautoapp.sonar-audit/1'
        mode = 'Full'
        runId = $runId
        repositoryIdentity = $context.RepositoryIdentity
        driverSha = $sourceSha
        invokingSha = $driverSha
        analyzedSha = $sourceSha
        frontendProfiles = $profiles
        candidate = [bool]$Candidate
        dirty = $false
        baselineEligible = -not [bool]$Candidate
        startedUtc = $startedUtc.ToString('o')
        finishedUtc = $null
        outcome = 'running'
        failureReason = $null
        settingsDigest = $context.SettingsDigest
        settings = $context.SettingsSnapshot
        toolVersions = $null
        server = [ordered]@{ wasRunning = $false; startedByCommand = $false; stoppedByCommand = $false; keepRequested = [bool]$KeepServerRunning }
        worktreeCleanup = 'pending'
        archiveVerified = $false
        outputs = [ordered]@{ run = $runId; archive = $null }
        profiles = [Collections.Generic.List[object]]::new()
    }

    foreach ($profile in $profiles) {
        $path = Join-Path (Join-Path $runDirectory 'worktrees') $profile
        $null = Invoke-AuditGit -Arguments @('-C', $invokingRoot, 'worktree', 'add', '--detach', $path, $sourceSha)
        $worktrees.Add([pscustomobject]@{ frontendProfile = $profile; path = $path; removed = $false })
    }

    $sourceRoot = [string]$worktrees[0].path
    $context.RepoRoot = $sourceRoot
    $context.ComposePath = Join-Path $sourceRoot 'docker/sonarqube/compose.yaml'
    $context.ToolVersions = Get-QualityToolVersions -RepoRoot $sourceRoot
    $batch.toolVersions = $context.ToolVersions
    if ($profiles -contains 'React') {
        $nodeRuntime = Get-QualityNodeRuntime -ToolVersions $context.ToolVersions -ConfiguredDirectory $context.NodeToolchainDirectory
        $context.NodeExecutable = $nodeRuntime.NodeExecutable
        $context.NpmCli = $nodeRuntime.NpmCli
        $context.NodeVersion = $nodeRuntime.NodeVersion
        $context.NpmVersion = $nodeRuntime.NpmVersion
    }

    $serverScript = Join-Path $sourceRoot 'Scripts/Quality/SonarQubeServer.ps1'
    $beforeContainer = Get-OwnedSonarContainer
    $batch.server.wasRunning = -not [string]::IsNullOrWhiteSpace($beforeContainer)
    $serverStartAttempted = $true
    Invoke-ServerAction -Script $serverScript -Parameters @{ Start = $true; Initialize = $true }
    $afterContainer = Get-OwnedSonarContainer
    $serverStartedByCommand = (-not $batch.server.wasRunning) -and (-not [string]::IsNullOrWhiteSpace($afterContainer))
    $batch.server.startedByCommand = $serverStartedByCommand
    $batch.settingsDigest = $context.SettingsDigest
    $batch.settings = $context.SettingsSnapshot

    $deadlineUtc = [DateTime]::UtcNow.AddMinutes(90)
    foreach ($entry in $worktrees) {
        $profile = [string]$entry.frontendProfile
        $profileOutput = Join-Path $runDirectory $profile
        $projectKey = [string]$context.ProjectKeys.$profile
        if ($Candidate) {
            $projectKey = "$projectKey-candidate-$shortSha"
        }
        $record = [ordered]@{
            frontendProfile = $profile
            projectKey = $projectKey
            outcome = 'running'
            startedUtc = [DateTime]::UtcNow.ToString('o')
            finishedUtc = $null
            failureReason = $null
            dotnetTests = $null
            coverageStatus = $null
            qualityGate = $null
            analysisId = $null
            ceTaskId = $null
            configurationDigest = $null
            frontendTests = $null
            reportComplete = $false
            archiveReport = $null
        }
        try {
            if ($Candidate) {
                Invoke-ServerAction -Script $serverScript -Parameters @{
                    Start = $true
                    EnsureCandidate = $true
                    FrontendProfile = $profile
                    CandidateSha = $sourceSha
                }
            }
            $analysisScript = Join-Path $entry.path 'Scripts/Quality/Invoke-SonarAnalysis.ps1'
            $analysis = & $analysisScript -FrontendProfile $profile -ProjectKey $projectKey -AnalyzedSha $sourceSha `
                -RunDirectory $profileOutput -Context $context -RepoRoot $entry.path -DeadlineUtc $deadlineUtc -Candidate:$Candidate
            $record.outcome = [string]$analysis.outcome
            $record.analysisId = $analysis.analysisId
            $record.ceTaskId = $analysis.ceTaskId
            $record.configurationDigest = $analysis.configurationDigest
            $record.reportComplete = [bool]$analysis.reportComplete
            $record.qualityGate = $analysis.qualityGate
            $record.dotnetTests = $analysis.tests.dotnet
            $record.frontendTests = $analysis.tests.frontendTests
            $record.coverageStatus = if ($analysis.coverage.dotnet.valid) { 'valid' } else { 'invalid' }
            if ($record.outcome -ne 'succeeded' -or -not $record.reportComplete) { throw 'Profile script returned without a complete report.' }
        }
        catch {
            $record.outcome = 'failed'
            $record.failureReason = ConvertTo-AuditSafeMessage -Text $_.Exception.Message
            [void]$failureMessages.Add("${profile}: $($record.failureReason)")
            $profileSummaryPath = Join-Path $profileOutput 'summary.json'
            if (Test-Path -LiteralPath $profileSummaryPath -PathType Leaf) {
                try {
                    $partial = Get-Content -LiteralPath $profileSummaryPath -Raw | ConvertFrom-Json
                    $record.analysisId = $partial.analysisId
                    $record.ceTaskId = $partial.ceTaskId
                    $record.configurationDigest = $partial.configurationDigest
                    $record.qualityGate = $partial.qualityGate
                    $record.reportComplete = [bool]$partial.reportComplete
                    $record.dotnetTests = $partial.tests.dotnet
                    $record.frontendTests = $partial.tests.frontendTests
                    $record.coverageStatus = if ($partial.coverage.dotnet.valid) { 'valid' } else { 'invalid' }
                }
                catch { }
            }
        }
        finally {
            $record.finishedUtc = [DateTime]::UtcNow.ToString('o')
            $batch.profiles.Add([pscustomobject]$record)
        }
    }
}
catch {
    $message = ConvertTo-AuditSafeMessage -Text $_.Exception.Message
    if ($message.Length -gt 2000) { $message = $message.Substring(0, 2000) }
    if (-not $failureMessages.Contains($message)) { $failureMessages.Add($message) }
}
finally {
    try {
        if ($serverStartAttempted -and -not $batch.server.wasRunning -and -not $serverStartedByCommand) {
            try { $serverStartedByCommand = -not [string]::IsNullOrWhiteSpace((Get-OwnedSonarContainer)) }
            catch { [void]$failureMessages.Add('Could not verify whether this audit started the owned SonarQube server; it was left untouched.') }
        }
        if ($serverStartAttempted -and $serverStartedByCommand -and -not $KeepServerRunning -and $worktrees.Count -gt 0) {
            $serverScript = Join-Path $worktrees[0].path 'Scripts/Quality/SonarQubeServer.ps1'
            Invoke-ServerAction -Script $serverScript -Parameters @{ Stop = $true }
            if ($batch) { $batch.server.stoppedByCommand = $true }
        }
    }
    catch {
        $stopError = ConvertTo-AuditSafeMessage -Text $_.Exception.Message
        [void]$failureMessages.Add("Owned server stop failed: $stopError")
    }

    if ($batch) {
        $batch.settingsDigest = $context.SettingsDigest
        $batch.settings = $context.SettingsSnapshot
        if ($failureMessages.Count -gt 0) {
            $batch.outcome = 'failed'
            $batch.baselineEligible = $false
            $batch.failureReason = $failureMessages -join ' '
        }
        else { $batch.outcome = 'succeeded' }
        $batch.finishedUtc = [DateTime]::UtcNow.ToString('o')
        if ($runDirectory) {
            try {
                Write-AuditJson -Path (Join-Path $runDirectory 'summary.json') -Value $batch
                Write-BatchMarkdown
                $archivePath = Archive-Audit
                $archiveVerified = $true
                $batch.archiveVerified = $true
                Write-AuditJson -Path (Join-Path $runDirectory 'summary.json') -Value $batch
                Write-BatchMarkdown
                Copy-SanitizedJson -Source (Join-Path $runDirectory 'summary.json') -Destination (Join-Path $archivePath 'summary.json')
                Copy-Item -LiteralPath (Join-Path $runDirectory 'batch.md') -Destination (Join-Path $archivePath 'batch.md') -Force
                New-ArchiveManifest -Directory $archivePath
                Verify-ArchiveManifest -Directory $archivePath
                Remove-AuditWorktrees
                $batch.worktreeCleanup = 'removed'
            }
            catch {
                $archiveError = ConvertTo-AuditSafeMessage -Text $_.Exception.Message
                [void]$failureMessages.Add("Archive or cleanup failed: $archiveError")
                $batch.worktreeCleanup = if ($archiveVerified) { 'failed; inspect retained paths' } else { 'retained because archive verification failed' }
            }

            if ($failureMessages.Count -gt 0) {
                $batch.outcome = 'failed'
                $batch.baselineEligible = $false
                $batch.failureReason = $failureMessages -join ' '
            }
            $batch.finishedUtc = [DateTime]::UtcNow.ToString('o')
            try {
                Write-AuditJson -Path (Join-Path $runDirectory 'summary.json') -Value $batch
                Write-BatchMarkdown
                if ($archiveVerified) {
                    $archivePath = Join-Path $context.ReportsDirectory $batch.runId
                    Copy-SanitizedJson -Source (Join-Path $runDirectory 'summary.json') -Destination (Join-Path $archivePath 'summary.json')
                    Copy-Item -LiteralPath (Join-Path $runDirectory 'batch.md') -Destination (Join-Path $archivePath 'batch.md') -Force
                    Assert-ArchiveSanitized -Directory $archivePath
                    New-ArchiveManifest -Directory $archivePath
                    Verify-ArchiveManifest -Directory $archivePath
                }
            }
            catch {
                [void]$failureMessages.Add('Could not finalize the audit batch summary.')
                $batch.outcome = 'failed'
                $batch.baselineEligible = $false
                $batch.failureReason = $failureMessages -join ' '
                try { Write-AuditJson -Path (Join-Path $runDirectory 'summary.json') -Value $batch } catch { }
            }
        }
    }
    Exit-QualityLock -Lock $lock
}

if (-not $batch) { throw "Full audit failed before run initialization: $($failureMessages -join ' ')" }
if ($batch.outcome -ne 'succeeded') {
    throw "Full quality audit failed. Summary: $(Join-Path $runDirectory 'summary.json'). $($batch.failureReason)"
}
Write-Host "Verified SonarQube reports: $($batch.outputs.archive)"
return [pscustomobject]$batch
