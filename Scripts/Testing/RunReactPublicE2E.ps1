[CmdletBinding()]
param(
    [ValidateSet('chromium', 'firefox', 'webkit')]
    [string] $Browser = 'chromium',

    [ValidateSet('broad', 'smoke')]
    [string] $Suite = 'broad',

    [ValidateSet('Debug', 'Release')]
    [string] $Configuration = 'Release',

    [switch] $ReuseFrontendBuild
)

$ErrorActionPreference = 'Stop'

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)] [string] $FilePath,
        [Parameter(Mandatory)] [string[]] $Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        $argumentsText = $Arguments -join ' '
        if ($databasePassword) {
            $argumentsText = $argumentsText.Replace($databasePassword, '[redacted]')
        }

        throw "Command failed with exit code $LASTEXITCODE`: $FilePath $argumentsText"
    }
}

function Get-DockerMappedPort {
    param(
        [Parameter(Mandatory)] [string] $ContainerName,
        [Parameter(Mandatory)] [int] $ContainerPort
    )

    $mapping = @(& docker port $ContainerName "$ContainerPort/tcp")
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($mapping | Select-Object -First 1))) {
        throw "Could not find the host port for $ContainerName."
    }

    $portText = (($mapping | Select-Object -First 1) -split ':')[-1]
    return [int] $portText
}

function Wait-DockerHealthy {
    param([Parameter(Mandatory)] [string] $ContainerName)

    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $state = & docker inspect --format '{{.State.Health.Status}}' $ContainerName 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Container $ContainerName stopped before becoming healthy."
        }

        if ($state -eq 'healthy') {
            return
        }

        Start-Sleep -Seconds 1
    }

    throw "Container $ContainerName did not become healthy within 60 seconds."
}

function Write-AppLogTail {
    param([Parameter(Mandatory)] [string] $Path)

    if (Test-Path -LiteralPath $Path) {
        Get-Content -LiteralPath $Path -Tail 35 | ForEach-Object {
            $line = $_
            if ($databasePassword) {
                $line = $line.Replace($databasePassword, '[redacted]')
            }

            Write-Host $line
        }
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$npmCommand = if ($IsWindows) { 'npm.cmd' } else { 'npm' }
$npxCommand = if ($IsWindows) { 'npx.cmd' } else { 'npx' }
$reactRoot = Join-Path $repoRoot 'BlazorAutoApp.React'
$clientRoot = Join-Path $repoRoot 'BlazorAutoApp.Client'
$testProject = Join-Path $repoRoot 'BlazorAutoApp.Test\BlazorAutoApp.Test.csproj'
$playwrightScript = Join-Path $repoRoot "BlazorAutoApp.Test\bin\$Configuration\net10.0\playwright.ps1"
$appDll = Join-Path $repoRoot "BlazorAutoApp\bin\$Configuration\net10.0\BlazorAutoApp.dll"
$staticRoot = Join-Path $reactRoot 'build\client'
$suffix = [Guid]::NewGuid().ToString('N')
$postgresName = "react-public-e2e-pg-$suffix"
$redisName = "react-public-e2e-redis-$suffix"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "react-public-e2e-$suffix"
$tempRootFullPath = [System.IO.Path]::GetFullPath($tempRoot)
$tempPrefix = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$comparison = if ($IsWindows) { [System.StringComparison]::OrdinalIgnoreCase } else { [System.StringComparison]::Ordinal }
$isSafeTempPath = $tempRootFullPath.StartsWith($tempPrefix, $comparison) `
    -and [System.IO.Path]::GetFileName($tempRootFullPath) -eq "react-public-e2e-$suffix"
if (-not $isSafeTempPath) {
    throw 'Temporary test output path failed its safety check.'
}

$null = New-Item -ItemType Directory -Path $tempRootFullPath
$databasePasswordBytes = [byte[]]::new(32)
[System.Security.Cryptography.RandomNumberGenerator]::Fill($databasePasswordBytes)
$databasePassword = [Convert]::ToHexString($databasePasswordBytes).ToLowerInvariant()
$appProcess = $null
$axeAssetCreated = $false
$axeAssetDirectory = Join-Path $staticRoot '__e2e'
$axeAssetPath = Join-Path $axeAssetDirectory 'axe.min.js'
$axeAssetFullPath = [System.IO.Path]::GetFullPath($axeAssetPath)
$previousEnvironment = [ordered]@{}

try {
    if ($ReuseFrontendBuild) {
        Write-Host 'Reusing the existing React build and npm installations.'
        foreach ($requiredPath in @(
                (Join-Path $staticRoot 'index.html'),
                (Join-Path $reactRoot 'node_modules'),
                (Join-Path $clientRoot 'node_modules\axe-core\axe.min.js')
            )) {
            if (-not (Test-Path -LiteralPath $requiredPath)) {
                throw "The requested React build reuse is incomplete: $requiredPath"
            }
        }
    }
    else {
        Write-Host "Installing and building the React package for the $Suite suite."
        $nodeVersion = (& node --version 2>$null | Select-Object -First 1)
        $nodeExitCode = $LASTEXITCODE
        $npmVersion = (& $npmCommand --version 2>$null | Select-Object -First 1)
        $npmExitCode = $LASTEXITCODE
        $usePinnedNodeToolchain = $nodeExitCode -eq 0 -and $npmExitCode -eq 0 -and $nodeVersion -eq 'v24.21.0' -and $npmVersion -eq '12.2.0'
        if (-not $usePinnedNodeToolchain) {
            Write-Host 'Using the package-declared Node 24.21.0 and npm 12.2.0 toolchain.'
        }

        $npmSteps = @(
            @{ Arguments = @('--prefix', $reactRoot, 'ci'); Command = "npm --prefix `"$reactRoot`" ci" },
            @{ Arguments = @('--prefix', $reactRoot, 'run', 'build'); Command = "npm --prefix `"$reactRoot`" run build" },
            @{ Arguments = @('--prefix', $clientRoot, 'ci'); Command = "npm --prefix `"$clientRoot`" ci" }
        )
        foreach ($npmStep in $npmSteps) {
            if ($usePinnedNodeToolchain) {
                $npmArguments = $npmStep.Arguments
                & $npmCommand @npmArguments
            }
            else {
                & $npxCommand --yes --package=node@24.21.0 --package=npm@12.2.0 -c $npmStep.Command
            }

            if ($LASTEXITCODE -ne 0) {
                throw "React E2E npm setup/build step failed with exit code $LASTEXITCODE."
            }
        }
    }

    Invoke-CheckedCommand -FilePath 'dotnet' -Arguments @('build', $testProject, '--configuration', $Configuration, '-p:FrontendProfile=React')

    if (-not (Test-Path -LiteralPath $staticRoot -PathType Container)) {
        throw "React build output was not found: $staticRoot"
    }

    $axeSource = Join-Path $clientRoot 'node_modules\axe-core\axe.min.js'
    $staticRootPrefix = [System.IO.Path]::GetFullPath($staticRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    $isSafeAxePath = $axeAssetFullPath.StartsWith($staticRootPrefix, $comparison) `
        -and [System.IO.Path]::GetFileName($axeAssetFullPath) -eq 'axe.min.js'
    if (-not $isSafeAxePath) {
        throw 'Temporary axe asset path failed its safety check.'
    }

    if (-not (Test-Path -LiteralPath $axeSource -PathType Leaf)) {
        throw "axe-core script was not found: $axeSource"
    }

    if (Test-Path -LiteralPath $axeAssetPath) {
        throw "A stale test-only axe asset already exists: $axeAssetPath"
    }

    $null = New-Item -ItemType Directory -Path $axeAssetDirectory
    Copy-Item -LiteralPath $axeSource -Destination $axeAssetPath
    $axeAssetCreated = $true

    if (-not (Test-Path -LiteralPath $playwrightScript -PathType Leaf)) {
        throw "Playwright installer was not found: $playwrightScript"
    }

    Write-Host "Installing the Playwright $Browser browser."
    Invoke-CheckedCommand -FilePath 'pwsh' -Arguments @('-File', $playwrightScript, 'install', $Browser)

    $postgresImage = 'postgres:18.4-alpine3.23'
    $redisImage = 'redis:8.8.0-alpine3.23'
    Invoke-CheckedCommand -FilePath 'docker' -Arguments @(
        'run', '--detach', '--rm', '--name', $postgresName,
        '--publish', '127.0.0.1::5432',
        '--env', "POSTGRES_USER=postgres",
        '--env', "POSTGRES_PASSWORD=$databasePassword",
        '--env', 'POSTGRES_DB=app',
        '--health-cmd', 'pg_isready -U postgres -d app',
        '--health-interval', '2s', '--health-timeout', '2s', '--health-retries', '30',
        $postgresImage
    ) | Out-Null
    Invoke-CheckedCommand -FilePath 'docker' -Arguments @(
        'run', '--detach', '--rm', '--name', $redisName,
        '--publish', '127.0.0.1::6379',
        '--health-cmd', 'redis-cli ping',
        '--health-interval', '2s', '--health-timeout', '2s', '--health-retries', '30',
        $redisImage
    ) | Out-Null

    Wait-DockerHealthy -ContainerName $postgresName
    Wait-DockerHealthy -ContainerName $redisName
    $postgresPort = Get-DockerMappedPort -ContainerName $postgresName -ContainerPort 5432
    $redisPort = Get-DockerMappedPort -ContainerName $redisName -ContainerPort 6379

    $portListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $portListener.Start()
    $appPort = ([System.Net.IPEndPoint] $portListener.LocalEndpoint).Port
    $portListener.Stop()
    $baseUrl = "http://127.0.0.1:$appPort"
    $appOutputPath = Join-Path $tempRootFullPath 'app.stdout.log'
    $appErrorPath = Join-Path $tempRootFullPath 'app.stderr.log'
    $environment = [ordered]@{
        ASPNETCORE_ENVIRONMENT = 'Development'
        ASPNETCORE_URLS = $baseUrl
        ConnectionStrings__DefaultConnection = "Host=127.0.0.1;Port=$postgresPort;Database=app;Username=postgres;Password=$databasePassword;GSS Encryption Mode=Disable"
        Database__RunMigrationsAtStartup = 'true'
        Redis__Configuration = "127.0.0.1:$redisPort"
        Redis__AllowMissing = 'false'
        Frontend__React__StaticRoot = $staticRoot
        E2E_AXE_URL = "$baseUrl/__e2e/axe.min.js"
        RUN_E2E = '1'
        E2E_BASE_URL = $baseUrl
        E2E_HEADLESS = '1'
        BROWSER = $Browser
    }
    foreach ($name in $environment.Keys) {
        $previousEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name, 'Process')
        [System.Environment]::SetEnvironmentVariable($name, [string] $environment[$name], 'Process')
    }

    $quotedAppDll = '"' + $appDll + '"'
    $startProcessOptions = @{
        FilePath = 'dotnet'
        ArgumentList = @($quotedAppDll, '--urls', $baseUrl)
        WorkingDirectory = (Join-Path $repoRoot 'BlazorAutoApp')
        RedirectStandardOutput = $appOutputPath
        RedirectStandardError = $appErrorPath
        PassThru = $true
    }
    if ($IsWindows) {
        $startProcessOptions.WindowStyle = 'Hidden'
    }

    $appProcess = Start-Process @startProcessOptions

    $appReady = $false
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        $appProcess.Refresh()
        if ($appProcess.HasExited) {
            Write-AppLogTail -Path $appErrorPath
            Write-AppLogTail -Path $appOutputPath
            throw "React test host exited with code $($appProcess.ExitCode)."
        }

        try {
            $health = Invoke-WebRequest -Uri "$baseUrl/health" -TimeoutSec 2
            if ($health.StatusCode -eq 200) {
                $appReady = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    if (-not $appReady) {
        Write-AppLogTail -Path $appErrorPath
        Write-AppLogTail -Path $appOutputPath
        throw 'React test host did not become healthy within 90 seconds.'
    }

    $filter = if ($Suite -eq 'broad') { 'Category=ReactPublicBroad' } else { 'Category=ReactPublicSmoke' }
    $resultsPath = Join-Path $tempRootFullPath 'results'
    $null = New-Item -ItemType Directory -Path $resultsPath
    Write-Host "Running the $Suite React public E2E suite in $Browser."
    Invoke-CheckedCommand -FilePath 'dotnet' -Arguments @(
        'test', $testProject, '--configuration', $Configuration, '--no-build', '-p:FrontendProfile=React',
        '--filter', $filter,
        '--logger', 'console;verbosity=detailed',
        '--logger', 'trx;LogFileName=react-public-e2e.trx',
        '--results-directory', $resultsPath
    )

    $trxPath = Join-Path $resultsPath 'react-public-e2e.trx'
    if (-not (Test-Path -LiteralPath $trxPath -PathType Leaf)) {
        throw "The React public E2E result file was not created: $trxPath"
    }

    [xml] $testResults = Get-Content -LiteralPath $trxPath -Raw
    $counters = $testResults.SelectSingleNode("//*[local-name()='Counters']")
    if ($null -eq $counters) {
        throw 'The React public E2E result file has no test counters.'
    }

    $total = [int] $counters.GetAttribute('total')
    $executed = [int] $counters.GetAttribute('executed')
    $passed = [int] $counters.GetAttribute('passed')
    $failed = [int] $counters.GetAttribute('failed')
    $notExecuted = [int] $counters.GetAttribute('notExecuted')
    if ($total -ne 1 -or $executed -ne 1 -or $passed -ne 1 -or $failed -ne 0 -or $notExecuted -ne 0) {
        throw "React public E2E suite count mismatch: total=$total executed=$executed passed=$passed failed=$failed notExecuted=$notExecuted; expected exactly one passed test and no skips."
    }

    Write-Host "React public E2E passed: $passed/$total tests; no failures or skips."
}
finally {
    if ($appProcess) {
        $appProcess.Refresh()
        if (-not $appProcess.HasExited) {
            Stop-Process -Id $appProcess.Id -Force -ErrorAction SilentlyContinue
            $appProcess.WaitForExit(10000) | Out-Null
        }
    }

    foreach ($name in @($redisName, $postgresName)) {
        & docker rm --force $name 2>$null | Out-Null
    }

    foreach ($name in $previousEnvironment.Keys) {
        [System.Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }

    if ($axeAssetCreated -and (Test-Path -LiteralPath $axeAssetFullPath -PathType Leaf)) {
        Remove-Item -LiteralPath $axeAssetFullPath -Force
    }

    if (Test-Path -LiteralPath $axeAssetDirectory -PathType Container) {
        $directoryContents = Get-ChildItem -LiteralPath $axeAssetDirectory -Force | Select-Object -First 1
        if (-not $directoryContents) {
            Remove-Item -LiteralPath $axeAssetDirectory -Force
        }
    }

    if (Test-Path -LiteralPath $tempRootFullPath) {
        Remove-Item -LiteralPath $tempRootFullPath -Recurse -Force
    }
}
