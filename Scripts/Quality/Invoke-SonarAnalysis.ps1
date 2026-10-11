[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('BlazorAuto', 'React')][string]$FrontendProfile,
    [Parameter(Mandatory)][string]$ProjectKey,
    [Parameter(Mandatory)][string]$AnalyzedSha,
    [Parameter(Mandatory)][string]$RunDirectory,
    [Parameter(Mandatory)][object]$Context,
    [DateTime]$DeadlineUtc = [DateTime]::UtcNow.AddMinutes(90),
    [switch]$Candidate,
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module -Name (Join-Path $PSScriptRoot 'SonarQuality.psm1') -Force -DisableNameChecking
$repoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$runDirectory = [IO.Path]::GetFullPath($RunDirectory)
if (-not (Test-QualityPathWithinRoot -Path $repoRoot -Root $Context.RunsDirectory)) {
    throw 'Full analysis must run from a detached worktree inside this private audit run.'
}
if (-not (Test-QualityPathWithinRoot -Path $runDirectory -Root $Context.RunsDirectory) -or
    $runDirectory.Equals([IO.Path]::GetFullPath($Context.RunsDirectory), [StringComparison]::OrdinalIgnoreCase)) {
    throw "Profile output must be a child of this repository's private run directory."
}
$logDirectory = Join-Path $runDirectory 'logs'
$summaryPath = Join-Path $runDirectory 'summary.json'
$scannerStatePath = Join-Path $repoRoot '.sonarqube'
$scannerStateOwned = $false
$profileStarted = [DateTime]::UtcNow
$failure = $null
$analysisToken = $null
$readerToken = $null
$summary = [ordered]@{
    schema = 'blazorautoapp.sonar-analysis/1'
    repositoryIdentity = $Context.RepositoryIdentity
    frontendProfile = $FrontendProfile
    projectKey = $ProjectKey
    sha = $AnalyzedSha
    candidate = [bool]$Candidate
    baselineEligible = -not [bool]$Candidate
    configuration = 'Release'
    configurationDigest = $Context.SettingsDigest
    settings = $Context.SettingsSnapshot | ConvertFrom-Json -AsHashtable
    startedUtc = $profileStarted.ToString('o')
    finishedUtc = $null
    outcome = 'running'
    failureReason = $null
    scannerVersion = [string]$Context.ToolVersions.scanner.version
    serverVersion = $null
    projectVersion = $null
    tests = [ordered]@{ frontendTests = $null; dotnet = $null }
    coverage = [ordered]@{ reactLcov = $null; reactSummary = $null; lines = $null; dotnet = $null }
    ceTaskId = $null
    analysisId = $null
    qualityGate = $null
    reportComplete = $false
    reportJson = 'report.json'
    reportMarkdown = 'report.md'
    steps = [Collections.Generic.List[object]]::new()
}

function Write-ProfileSummary {
    $summary.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $temporary = "$summaryPath.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        [IO.File]::WriteAllText($temporary, ($summary | ConvertTo-Json -Depth 24), [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $summaryPath -Force
    }
    finally { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
}

function Get-RemainingTimeoutSeconds {
    param([ValidateRange(1, 5400)][int]$MaximumSeconds = 1200)
    $remaining = [int][Math]::Floor(($DeadlineUtc - [DateTime]::UtcNow).TotalSeconds)
    if ($remaining -lt 1) { throw 'The full-audit deadline expired before this stage could start.' }
    return [Math]::Min($MaximumSeconds, $remaining)
}

function Invoke-QualityStep {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Executable,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [hashtable]$Environment = @{},
        [string[]]$Secrets = @(),
        [ValidateRange(1, 5400)][int]$MaximumSeconds = 1200,
        [switch]$AllowFailure
    )
    $safeArguments = ConvertTo-QualityDisplayArguments -Arguments $Arguments
    Write-Host "[$FrontendProfile] ${Name}: $Executable $($safeArguments -join ' ')"
    $result = Invoke-QualityProcess -FilePath $Executable -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory -TimeoutSeconds (Get-RemainingTimeoutSeconds -MaximumSeconds $MaximumSeconds) `
        -Environment $Environment -RedactValues $Secrets -OutputDirectory $logDirectory -StepName $Name
    $step = [ordered]@{
        name = $Name
        exitCode = $result.ExitCode
        timedOut = $result.TimedOut
        startedUtc = $result.StartedUtc
        finishedUtc = $result.FinishedUtc
        durationSeconds = $result.DurationSeconds
        stdoutLog = "logs/$Name.stdout.log"
        stderrLog = "logs/$Name.stderr.log"
    }
    [void]$summary.steps.Add($step)
    if (($result.TimedOut -or $result.ExitCode -ne 0) -and -not $AllowFailure) {
        $message = $result.Stderr.Trim()
        if ([string]::IsNullOrWhiteSpace($message)) { $message = $result.Stdout.Trim() }
        $message = Protect-QualityText -Text $message -Secrets $Secrets
        if ($message.Length -gt 1600) { $message = $message.Substring(0, 1600) }
        throw "Stage '$Name' failed (exit $($result.ExitCode), timeout $($result.TimedOut)): $message"
    }
    return $result
}

function Get-GitValue {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $result = Invoke-QualityStep -Name "git-$([guid]::NewGuid().ToString('N').Substring(0, 6))" `
        -Executable $Context.GitExecutable -Arguments $Arguments -WorkingDirectory $repoRoot -MaximumSeconds 30
    return $result.Stdout.Trim()
}

function Get-ScannerExecutable {
    $version = [string]$Context.ToolVersions.scanner.version
    $toolDirectory = Join-Path $Context.ToolsDirectory "dotnet-sonarscanner/$version"
    $executable = Join-Path $toolDirectory 'dotnet-sonarscanner.exe'
    if (Test-Path -LiteralPath $executable -PathType Leaf) {
        $probe = Invoke-QualityStep -Name 'scanner-version' -Executable $executable -Arguments @('--version') `
            -WorkingDirectory $repoRoot -MaximumSeconds 30
    if (($probe.Stdout + $probe.Stderr) -notmatch [regex]::Escape($version)) {
            throw "Pinned scanner path contains a mismatched version; expected $version. Preserve it and inspect $toolDirectory."
        }
        return $executable
    }
    $toolDirectoryExists = Test-Path -LiteralPath $toolDirectory -PathType Container
    $toolDirectoryHasFiles = @(Get-ChildItem -LiteralPath $toolDirectory -Force -ErrorAction SilentlyContinue).Count -gt 0
    if ($toolDirectoryExists -and $toolDirectoryHasFiles) {
        throw "Pinned scanner directory is incomplete: $toolDirectory. Preserve it and inspect before retrying."
    }
    New-Item -ItemType Directory -Force -Path $toolDirectory | Out-Null
    $null = Invoke-QualityStep -Name 'scanner-install' -Executable $Context.DotnetExecutable `
        -Arguments @('tool', 'install', '--tool-path', $toolDirectory, 'dotnet-sonarscanner', '--version', $version, '--verbosity', 'minimal') `
        -WorkingDirectory $repoRoot -MaximumSeconds 900
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw "Pinned scanner install omitted $executable." }
    $probe = Invoke-QualityStep -Name 'scanner-version' -Executable $executable -Arguments @('--version') `
        -WorkingDirectory $repoRoot -MaximumSeconds 30
    if (($probe.Stdout + $probe.Stderr) -notmatch [regex]::Escape($version)) { throw "Installed scanner did not report pinned version $version." }
    return $executable
}

function Get-QualityChildEnvironment {
    param([Parameter(Mandatory)][string]$Profile, [switch]$React)
    $environment = @{
        FrontendProfile = $Profile
        RunSonarAnalyzers = 'false'
        RUN_E2E = '0'
        RUN_TESTCONTAINERS = '0'
        SONAR_TOKEN = $null
        SONAR_HOST_URL = $null
        SONAR_REPORT_TOKEN = $null
    }
    if ($React) {
        $nodeDirectory = Split-Path -Parent $Context.NodeExecutable
        $environment.PATH = "$nodeDirectory;$env:PATH"
    }
    return $environment
}

function Get-ProfileExclusions {
    $settingsPath = Join-Path $repoRoot 'Scripts/Quality/SonarQube/SonarQube.Analysis.xml'
    [xml]$xml = Get-Content -LiteralPath $settingsPath -Raw
    $property = @($xml.SelectNodes("//*[local-name()='Property' and @Name='sonar.exclusions']")) | Select-Object -First 1
    if ($null -eq $property) { throw 'Common sonar.exclusions are missing from the tracked analysis settings.' }
    $exclusions = [Collections.Generic.List[string]]::new()
    foreach ($item in ([string]$property.InnerText -split ',')) {
        if (-not [string]::IsNullOrWhiteSpace($item)) { $exclusions.Add($item.Trim()) }
    }
    if ($FrontendProfile -eq 'BlazorAuto') {
        $exclusions.Add('BlazorAutoApp.React/**')
        $exclusions.Add('BlazorAutoApp.React/app/**/*.test.ts')
        $exclusions.Add('BlazorAutoApp.React/app/**/*.test.tsx')
    }
    else {
        $exclusions.Add('BlazorAutoApp.Client/**')
        $exclusions.Add('BlazorAutoApp/**/*.razor')
        $exclusions.Add('BlazorAutoApp/**/*.razor.js')
        $exclusions.Add('BlazorAutoApp/Features/Login/Account/Pages/Register.razor')
        $exclusions.Add('BlazorAutoApp/Features/Login/Account/Pages/RegisterConfirmation.razor')
        $exclusions.Add('BlazorAutoApp.React/app/**/*.test.ts')
        $exclusions.Add('BlazorAutoApp.React/app/**/*.test.tsx')
        $exclusions.Add('BlazorAutoApp.React/app/test/**')
        $exclusions.Add('BlazorAutoApp.React/app/**/*.typecheck.ts')
        $exclusions.Add('BlazorAutoApp.React/app/**/*.d.ts')
    }
    return ($exclusions | Select-Object -Unique) -join ','
}

function Get-ProfileCoverageExclusions {
    $settingsPath = Join-Path $repoRoot 'Scripts/Quality/SonarQube/SonarQube.Analysis.xml'
    [xml]$xml = Get-Content -LiteralPath $settingsPath -Raw
    $property = @($xml.SelectNodes("//*[local-name()='Property' and @Name='sonar.coverage.exclusions']")) | Select-Object -First 1
    if ($null -eq $property) { throw 'Common sonar.coverage.exclusions are missing from the tracked analysis settings.' }
    return [string]$property.InnerText
}

function Get-QualityScannerArguments {
    param(
        [Parameter(Mandatory)][string]$Token,
        [Parameter(Mandatory)][string]$ProjectVersion,
        [Parameter(Mandatory)][string]$ReactLcov,
        [Parameter(Mandatory)][string]$Exclusions
    )
    $settingsPath = (Resolve-Path -LiteralPath (Join-Path $repoRoot 'Scripts/Quality/SonarQube/SonarQube.Analysis.xml')).Path
    $testsDirectory = (Join-Path $runDirectory 'tests')
    $coverageGlob = Join-Path $testsDirectory '*/*.xml'
    $arguments = @(
        'begin',
        "/k:$ProjectKey",
        "/v:$ProjectVersion",
        "/s:$settingsPath",
        "/d:sonar.projectBaseDir=$repoRoot",
        "/d:sonar.scm.revision=$AnalyzedSha",
        "/d:sonar.host.url=$($Context.BaseUrl)",
        "/d:sonar.token=$Token",
        "/d:sonar.exclusions=$Exclusions",
        "/d:sonar.cs.vscoveragexml.reportsPaths=$coverageGlob",
        "/d:sonar.cs.vstest.reportsPaths=$(Join-Path $testsDirectory 'suite.trx')"
    )
    if ($FrontendProfile -eq 'React') { $arguments += "/d:sonar.javascript.lcov.reportPaths=$ReactLcov" }
    return $arguments
}

function Get-AnalysisFromServer {
    param([Parameter(Mandatory)][string]$AnalysisId, [Parameter(Mandatory)][string]$Token)
    $headers = Get-QualityApiHeaders -Token $Token
    $response = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Path 'api/project_analyses/search' `
        -Query @{ project = $ProjectKey; ps = 500 } -Headers $headers -RedactValues @($Token)
    $analysis = @($response.analyses | Where-Object { $_.key -eq $AnalysisId }) | Select-Object -First 1
    if ($null -eq $analysis) { throw 'The completed compute-engine analysis is missing from the project analysis history.' }
    if (-not $analysis.revision -or $analysis.revision -ne $AnalyzedSha) {
        throw 'The server analysis revision does not match the immutable source SHA.'
    }
    if (-not $analysis.projectVersion -or $analysis.projectVersion -ne $summary.projectVersion) {
        throw 'The server project version does not match this immutable run.'
    }
    return $analysis
}

function Protect-ProfileLogs {
    $secrets = @($analysisToken, $readerToken) | Where-Object { -not [string]::IsNullOrEmpty($_) }
    $found = $false
    if (-not (Test-Path -LiteralPath $logDirectory -PathType Container)) { return $false }
    foreach ($file in Get-ChildItem -LiteralPath $logDirectory -File -Recurse) {
        $content = [IO.File]::ReadAllText($file.FullName)
        $safe = Protect-QualityText -Text $content -Secrets $secrets
        if ($safe -ne $content) {
            $found = $true
            [IO.File]::WriteAllText($file.FullName, $safe, [Text.UTF8Encoding]::new($false))
        }
        foreach ($secret in $secrets) {
            if ($safe.Contains($secret, [StringComparison]::Ordinal)) {
                throw "A scanner credential remains in retained log '$($file.Name)' after sanitization."
            }
        }
    }
    return $found
}

try {
    if (Test-Path -LiteralPath $runDirectory) { throw "Profile run output already exists: $runDirectory" }
    New-Item -ItemType Directory -Force -Path $runDirectory, $logDirectory | Out-Null
    if ($AnalyzedSha -notmatch '^[0-9a-f]{40}$') { throw 'Analyzed SHA must be a full lowercase commit SHA.' }
    $expectedProjectKey = [string]$Context.ProjectKeys.$FrontendProfile
    if ($Candidate) { $expectedProjectKey = "$expectedProjectKey-candidate-$($AnalyzedSha.Substring(0, 12))" }
    if ($ProjectKey -ne $expectedProjectKey) { throw 'Project key does not match the repository identity, profile, and candidate SHA.' }
    if ($env:RunSonarAnalyzers -eq 'true') { throw 'RunSonarAnalyzers=true is active. Clear it before a Full audit.' }
    if ($FrontendProfile -eq 'React' -and (-not $Context.NodeExecutable -or -not $Context.NpmCli)) {
        throw 'React audit requires the exact pinned Node/npm toolchain resolved by the invoking checkout.'
    }
    if (Test-Path -LiteralPath $scannerStatePath) {
        throw 'An existing .sonarqube directory makes scanner ownership unclear. Preserve it and inspect it before running Full mode.'
    }

    $head = Get-GitValue -Arguments @('rev-parse', 'HEAD')
    if ($head -ne $AnalyzedSha) { throw "Worktree HEAD $head does not match requested SHA $AnalyzedSha." }
    $status = Get-GitValue -Arguments @('status', '--porcelain', '--untracked-files=normal')
    if (-not [string]::IsNullOrWhiteSpace($status)) { throw 'Full analysis source worktree is dirty before preparation.' }
    $commitDate = Get-GitValue -Arguments @('show', '-s', '--format=%cs', 'HEAD')
    if ($commitDate -notmatch '^\d{4}-\d{2}-\d{2}$') { throw 'Git did not return a valid commit date for the project version.' }
    $shortSha = $AnalyzedSha.Substring(0, 12)
    $summary.projectVersion = "$($commitDate.Replace('-', ''))-$shortSha"
    $serverStatus = (Invoke-RestMethod -Uri "$($Context.BaseUrl)/api/system/status" -TimeoutSec 10).status
    if ($serverStatus -ne 'UP') { throw "Owned SonarQube server is not UP (status '$serverStatus')." }
    $summary.serverVersion = (Invoke-RestMethod -Uri "$($Context.BaseUrl)/api/server/version" -TimeoutSec 10).ToString()
    $profileExclusions = Get-ProfileExclusions
    $coverageExclusions = Get-ProfileCoverageExclusions
    $analysisSettingsPath = Join-Path $repoRoot 'Scripts/Quality/SonarQube/SonarQube.Analysis.xml'
    $profileOverridesPath = Join-Path $repoRoot 'Scripts/Quality/SonarQube/profile-overrides.json'
    $effectiveSettings = [ordered]@{
        schema = 'blazorautoapp.sonar-effective-settings/1'
        repositoryIdentity = $Context.RepositoryIdentity
        frontendProfile = $FrontendProfile
        projectKey = $ProjectKey
        loopbackUrl = $Context.BaseUrl
        hostPort = $Context.HostPort
        scannerVersion = [string]$Context.ToolVersions.scanner.version
        analyzerVersion = [string]$Context.ToolVersions.analyzer.version
        serverVersion = $summary.serverVersion
        hostSettingsDigest = $Context.SettingsDigest
        analysisSettingsSha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($analysisSettingsPath))).ToLowerInvariant()
        profileOverridesSha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($profileOverridesPath))).ToLowerInvariant()
        sonarExclusions = $profileExclusions
        sonarCoverageExclusions = $coverageExclusions
        nodeVersion = if ($FrontendProfile -eq 'React') { $Context.NodeVersion } else { $null }
        npmVersion = if ($FrontendProfile -eq 'React') { $Context.NpmVersion } else { $null }
    }
    $settingsJson = $effectiveSettings | ConvertTo-Json -Depth 12 -Compress
    $summary.configurationDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($settingsJson))).ToLowerInvariant()
    $summary.settings = $effectiveSettings
    $settingsSnapshotPath = Join-Path $runDirectory 'effective-settings.json'
    [IO.File]::WriteAllText($settingsSnapshotPath, ($effectiveSettings | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))

    $scanner = Get-ScannerExecutable
    $testsDirectory = Join-Path $runDirectory 'tests'
    New-Item -ItemType Directory -Force -Path $testsDirectory | Out-Null
    $reactRoot = Join-Path $repoRoot 'BlazorAutoApp.React'
    $reactLcov = ''
    if ($FrontendProfile -eq 'React') {
        $reactCoverage = Join-Path $runDirectory 'react-coverage'
        New-Item -ItemType Directory -Force -Path $reactCoverage | Out-Null
        $reactEnvironment = Get-QualityChildEnvironment -Profile $FrontendProfile -React
        $node = [string]$Context.NodeExecutable
        $npmCli = [string]$Context.NpmCli
        $npmSteps = @(
            [pscustomobject]@{ Name = 'npm-ci'; Args = @($npmCli, 'ci') },
            [pscustomobject]@{ Name = 'react-api-check'; Args = @($npmCli, 'run', 'api:check') },
            [pscustomobject]@{ Name = 'react-typecheck'; Args = @($npmCli, 'run', 'typecheck') },
            [pscustomobject]@{ Name = 'react-coverage-tests'; Args = @($npmCli, 'run', 'test:coverage') }
        )
        foreach ($step in $npmSteps) {
            $null = Invoke-QualityStep -Name $step.Name -Executable $node -Arguments $step.Args `
                -WorkingDirectory $reactRoot -Environment $reactEnvironment -MaximumSeconds 1200
        }
        $vitestJson = Join-Path $reactRoot 'coverage/test-results.json'
        $coverageSummary = Join-Path $reactRoot 'coverage/coverage-summary.json'
        $vitestValidator = Join-Path $PSScriptRoot 'validate_vitest_results.py'
        $validateReactTests = Invoke-QualityStep -Name 'validate-react-tests' -Executable $Context.PythonExecutable `
            -Arguments @($vitestValidator, $vitestJson, '--expected-passed', '31', '--expected-skipped', '0',
                '--coverage-summary', $coverageSummary, '--react-root', $reactRoot) `
            -WorkingDirectory $repoRoot -MaximumSeconds 60
        $rawLcov = Join-Path $reactRoot 'coverage/lcov.info'
        $reactLcov = Join-Path $reactCoverage 'lcov.info'
        $normalizer = Join-Path $PSScriptRoot 'normalize_lcov_paths.py'
        $null = Invoke-QualityStep -Name 'normalize-react-lcov' -Executable $Context.PythonExecutable `
            -Arguments @($normalizer, '--input', $rawLcov, '--output', $reactLcov, '--repo-root', $repoRoot, '--source-root', $reactRoot) `
            -WorkingDirectory $repoRoot -MaximumSeconds 60
        $lcov = [IO.File]::ReadAllText($reactLcov)
        if ($lcov -notmatch '(?m)^SF:BlazorAutoApp\.React/app/.*\.(ts|tsx)$') { throw 'Normalized React LCOV contains no app source path.' }
        $coverageDocument = Get-Content -LiteralPath $coverageSummary -Raw | ConvertFrom-Json
        $frontendCounts = $validateReactTests.Stdout.Trim() | ConvertFrom-Json -AsHashtable
        $summary.tests.frontendTests = [ordered]@{
            passed = [int]$frontendCounts.tests.passed
            failed = [int]$frontendCounts.tests.failed
            skipped = [int]($frontendCounts.tests.pending + $frontendCounts.tests.todo)
            total = [int]$frontendCounts.tests.total
        }
        $summary.coverage = [ordered]@{
            reactLcov = 'react-coverage/lcov.info'
            reactSummary = 'validated'
            lines = $coverageDocument.total.lines
        }
        $afterPreparation = Get-GitValue -Arguments @('status', '--porcelain', '--untracked-files=normal')
        if (-not [string]::IsNullOrWhiteSpace($afterPreparation)) {
            throw 'React preparation changed tracked or non-ignored source files; scanner begin was not invoked.'
        }
    }

    $analysisSecretName = if ($Candidate) { "analysis-$($FrontendProfile.ToLowerInvariant())-candidate-$shortSha" } else { "analysis-$($FrontendProfile.ToLowerInvariant())-main" }
    $analysisToken = Get-QualitySecret -Context $Context -Name $analysisSecretName
    $readerToken = Get-QualitySecret -Context $Context -Name "reader-$($FrontendProfile.ToLowerInvariant())-token"

    $summary.tests.dotnet = $null
    $summary.coverage.dotnet = $null
    $scannerStateOwned = $true
    $environment = Get-QualityChildEnvironment -Profile $FrontendProfile
    $beginArguments = Get-QualityScannerArguments -Token $analysisToken -ProjectVersion $summary.projectVersion `
        -ReactLcov $reactLcov -Exclusions $profileExclusions
    $null = Invoke-QualityStep -Name 'scanner-begin' -Executable $scanner -Arguments $beginArguments `
        -WorkingDirectory $repoRoot -Environment $environment -Secrets @($analysisToken) -MaximumSeconds 1200

    $restoreArgs = @('restore', (Join-Path $repoRoot 'BlazorAutoApp.sln'), '--verbosity', 'minimal',
        "-p:FrontendProfile=$FrontendProfile", '-p:RunSonarAnalyzers=false')
    $null = Invoke-QualityStep -Name 'dotnet-restore' -Executable $Context.DotnetExecutable -Arguments $restoreArgs `
        -WorkingDirectory $repoRoot -Environment $environment -MaximumSeconds 1200
    $buildArgs = @('build', (Join-Path $repoRoot 'BlazorAutoApp.sln'), '--configuration', 'Release', '--no-restore',
        '--no-incremental', '--disable-build-servers', '-nr:false', "-p:FrontendProfile=$FrontendProfile", '-p:RunSonarAnalyzers=false')
    $null = Invoke-QualityStep -Name 'dotnet-build' -Executable $Context.DotnetExecutable -Arguments $buildArgs `
        -WorkingDirectory $repoRoot -Environment $environment -MaximumSeconds 1200

    $testArgs = @('test', (Join-Path $repoRoot 'BlazorAutoApp.Test/BlazorAutoApp.Test.csproj'),
        '--configuration', 'Release', '--no-build', '--no-restore', '--disable-build-servers', '-nr:false',
        "-p:FrontendProfile=$FrontendProfile", '-p:RunSonarAnalyzers=false',
        '--collect', 'Code Coverage;Format=Xml', '--logger', 'trx;LogFileName=suite.trx', '--results-directory', $testsDirectory)
    if ($FrontendProfile -eq 'React') { $testArgs += @('--filter', 'FrontendProfile!=BlazorAuto') }
    $null = Invoke-QualityStep -Name 'dotnet-tests' -Executable $Context.DotnetExecutable -Arguments $testArgs `
        -WorkingDirectory $repoRoot -Environment $environment -MaximumSeconds 1200

    $expectedPassed = if ($FrontendProfile -eq 'BlazorAuto') { 211 } else { 203 }
    $testValidator = Join-Path $repoRoot 'Scripts/CI/validate_dotnet_test_results.py'
    $testValidation = Invoke-QualityStep -Name 'validate-dotnet-tests' -Executable $Context.PythonExecutable `
        -Arguments @($testValidator, (Join-Path $testsDirectory 'suite.trx'), '--expected-passed', [string]$expectedPassed,
            '--expected-skipped', '13', '--suite', "$FrontendProfile .NET suite") `
        -WorkingDirectory $repoRoot -MaximumSeconds 60
    $dotnetTestCounts = $testValidation.Stdout.Trim()
    if ($dotnetTestCounts -notmatch '(?:^|:\s*)(?<passed>\d+) passed, (?<skipped>\d+) expected skips, (?<total>\d+) total') {
        throw 'TRX validator did not return its approved test counts.'
    }
    $summary.tests.dotnet = [ordered]@{
        passed = [int]$Matches.passed
        failed = 0
        skipped = [int]$Matches.skipped
        total = [int]$Matches.total
        result = 'tests/suite.trx'
    }

    $coverageValidator = Join-Path $PSScriptRoot 'validate_dotnet_coverage.py'
    $coverageJson = Join-Path $runDirectory 'tests/coverage-validation.json'
    $coverageResult = Invoke-QualityStep -Name 'validate-dotnet-coverage' -Executable $Context.PythonExecutable `
        -Arguments @($coverageValidator, '--tests-directory', $testsDirectory, '--repo-root', $repoRoot,
            '--frontend-profile', $FrontendProfile, '--output-json', $coverageJson) `
        -WorkingDirectory $repoRoot -MaximumSeconds 60
    $coverageDocument = Get-Content -LiteralPath $coverageJson -Raw | ConvertFrom-Json
    $summary.coverage.dotnet = [ordered]@{
        valid = [bool]$coverageDocument.valid
        directReportCount = [int]$coverageDocument.reportCount
        resolvedSourceFileCount = [int]$coverageDocument.sourceFileCount
        coveredProductionSources = @($coverageDocument.coveredProductionSources)
        productionModules = $coverageDocument.productionModules
        validation = 'tests/coverage-validation.json'
    }
    if ($FrontendProfile -eq 'BlazorAuto') {
        $summary.tests.frontendTests = [ordered]@{ status = 'not-applicable' }
    }
    $runEvidence = [ordered]@{
        tests = [ordered]@{
            frontendTests = $summary.tests.frontendTests
            dotnet = $summary.tests.dotnet
        }
        coverage = [ordered]@{
            reactLcov = if ($FrontendProfile -eq 'React') { 'validated' } else { 'not-applicable' }
            dotnet = $summary.coverage.dotnet
        }
    }
    $evidencePath = Join-Path $runDirectory 'quality-evidence.json'
    [IO.File]::WriteAllText($evidencePath, ($runEvidence | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))

    $endArgs = @('end', "/d:sonar.token=$analysisToken")
    $null = Invoke-QualityStep -Name 'scanner-end' -Executable $scanner -Arguments $endArgs `
        -WorkingDirectory $repoRoot -Environment $environment -Secrets @($analysisToken) -MaximumSeconds 1200
    $taskFile = Join-Path $scannerStatePath 'out/.sonar/report-task.txt'
    if (-not (Test-Path -LiteralPath $taskFile -PathType Leaf)) { throw 'Scanner end did not write report-task.txt.' }
    $taskProperties = @{}
    foreach ($line in Get-Content -LiteralPath $taskFile) {
        if ($line -match '^([^=]+)=(.*)$') { $taskProperties[$Matches[1]] = $Matches[2] }
    }
    if ($taskProperties.projectKey -and $taskProperties.projectKey -ne $ProjectKey) { throw 'Scanner task belongs to a different Sonar project.' }
    if (-not $taskProperties.ceTaskId) { throw 'Scanner report-task.txt has no compute-engine task ID.' }
    $summary.ceTaskId = $taskProperties.ceTaskId

    $analysisHeaders = Get-QualityApiHeaders -Token $analysisToken
    $ceDeadline = [DateTime]::UtcNow.AddMinutes(15)
    if ($ceDeadline -gt $DeadlineUtc) { $ceDeadline = $DeadlineUtc }
    $ceTask = $null
    do {
        $null = Get-RemainingTimeoutSeconds -MaximumSeconds 10
        $ceTask = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Path 'api/ce/task' `
            -Query @{ id = $summary.ceTaskId } -Headers $analysisHeaders -TimeoutSeconds 20 -RedactValues @($analysisToken)
        $task = $ceTask.task
        if ($task.componentKey -and $task.componentKey -ne $ProjectKey) { throw 'Compute-engine task belongs to a different Sonar project.' }
        if ($task.status -in @('SUCCESS', 'FAILED', 'CANCELED')) { break }
        Start-Sleep -Seconds 5
    } while ([DateTime]::UtcNow -lt $ceDeadline)
    if ($null -eq $task -or $task.status -ne 'SUCCESS') {
        $state = if ($task) { [string]$task.status } else { 'TIMEOUT' }
        $errorMessage = if ($task -and $task.PSObject.Properties['errorMessage']) { [string]$task.errorMessage } else { '' }
        throw "Compute-engine task ended as ${state}: $(Protect-QualityText -Text $errorMessage -Secrets @($analysisToken, $readerToken))"
    }
    if (-not $task.analysisId) { throw 'Successful compute-engine task did not return an analysis ID.' }
    $summary.analysisId = [string]$task.analysisId
    $null = Get-AnalysisFromServer -AnalysisId $summary.analysisId -Token $readerToken

    $reportArguments = @(
        (Join-Path $repoRoot 'Scripts/Quality/sonar_report.py'),
        '--base-url', $Context.BaseUrl,
        '--project', $ProjectKey,
        '--analysis-id', $summary.analysisId,
        '--repo-root', $repoRoot,
        '--repository-identity', $Context.RepositoryIdentity,
        '--frontend-profile', $FrontendProfile,
        '--sha', $AnalyzedSha,
        '--project-version', $summary.projectVersion,
        '--settings-digest', $summary.configurationDigest,
        '--settings-file', $settingsSnapshotPath,
        '--evidence-json', $evidencePath,
        '--server-version', $summary.serverVersion,
        '--out-dir', $runDirectory
    )
    $reportEnvironment = @{ SONAR_REPORT_TOKEN = $readerToken }
    $null = Invoke-QualityStep -Name 'export-report' -Executable $Context.PythonExecutable `
        -Arguments $reportArguments -WorkingDirectory $repoRoot -Environment $reportEnvironment `
        -Secrets @($analysisToken, $readerToken) -MaximumSeconds 180
    $reportPath = Join-Path $runDirectory 'report.json'
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) { throw 'Sonar report exporter did not write report.json.' }
    $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    if ($report.schema -ne 'blazorautoapp.sonar-report/1' -or
        $report.repositoryIdentity -ne $Context.RepositoryIdentity -or
        $report.frontendProfile -ne $FrontendProfile -or $report.projectKey -ne $ProjectKey -or
        $report.analysisId -ne $summary.analysisId -or $report.sha -ne $AnalyzedSha -or
        $report.settingsDigest -ne $summary.configurationDigest -or
        $report.complete -ne $true) {
        throw 'Exported report is incomplete or its repository/profile/project/analysis identity does not match this run.'
    }
    $summary.qualityGate = $report.qualityGate.status
    $summary.reportComplete = $true
    $summary.reportDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($reportPath))).ToLowerInvariant()
    $summary.outcome = 'succeeded'
}
catch {
    $failure = Protect-QualityText -Text $_.Exception.Message -Secrets @($analysisToken, $readerToken)
    if ($failure.Length -gt 2000) { $failure = $failure.Substring(0, 2000) }
    $summary.outcome = 'failed'
    $summary.failureReason = $failure
}
finally {
    try {
        $foundSecret = Protect-ProfileLogs
        if ($foundSecret) {
            $summary.logsSanitized = $true
        }
    }
    catch {
        $summary.outcome = 'failed'
        $summary.failureReason = if ($summary.failureReason) { "$($summary.failureReason) Log sanitization failed." } else { 'Log sanitization failed.' }
    }
    if ($scannerStateOwned) {
        try { Remove-QualityScannerState -RepoRoot $repoRoot -ExpectedRunRoot $repoRoot }
        catch {
            $summary.outcome = 'failed'
            $summary.failureReason = if ($summary.failureReason) { "$($summary.failureReason) Scanner-state cleanup failed." } else { 'Scanner-state cleanup failed.' }
        }
    }
    try { Write-ProfileSummary }
    catch {
        $summary.outcome = 'failed'
        $summary.failureReason = 'Could not write the profile audit summary.'
    }
}

if ($summary.outcome -ne 'succeeded') { throw "Full Sonar analysis failed for ${FrontendProfile}: $($summary.failureReason). Private run details: $runDirectory" }
return [pscustomobject]$summary
