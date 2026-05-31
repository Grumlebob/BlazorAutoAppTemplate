param(
    [ValidateSet("local", "localcluster-public", "cloud-public", "origin-via-tunnel")]
    [string] $Target = "local",

    [ValidateSet("smoke", "demo", "soak-lite", "burst")]
    [string] $Profile = "smoke",

    [string] $BaseUrl,
    [string] $Duration,
    [double] $MaxRps = 0,
    [int] $Users = 0,
    [double] $ApiRpsBudget = -1,
    [double] $AuthWriteRpsBudget = -1,
    [string] $ReportDir,
    [switch] $AuthCheck,
    [string] $AuthEmail,
    [string] $AuthPasswordEnv,
    [switch] $RegisterSyntheticUser,
    [switch] $KeepSyntheticData,
    [switch] $InstallBrowsers,
    [switch] $HeadedBrowser,
    [switch] $Writes,
    [switch] $Cleanup,
    [switch] $CleanupOnly,
    [switch] $BrowserSampler,
    [switch] $AllowDeployed,
    [switch] $AllowWrite,
    [switch] $AllowBurst,
    [switch] $AllowRateLimit,
    [switch] $Yes,
    [switch] $Help
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$projectPath = Join-Path $repoRoot "BlazorAutoApp.Simulation/BlazorAutoApp.Simulation.csproj"

if ($Help) {
    dotnet run --project $projectPath -- --help
    exit $LASTEXITCODE
}

if (-not (Test-Path $projectPath)) {
    throw "BlazorAutoApp.Simulation project was not found at $projectPath"
}

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    throw "dotnet was not found on PATH."
}

if ($AllowDeployed) {
    $env:SIMULATION_ALLOW_DEPLOYED = "1"
}

if ($AllowWrite) {
    $env:SIMULATION_ALLOW_WRITE = "1"
}

if ($AllowBurst) {
    $env:SIMULATION_ALLOW_BURST = "1"
}

if ($Target -in @("localcluster-public", "cloud-public") -and $env:SIMULATION_ALLOW_DEPLOYED -ne "1") {
    throw "Target '$Target' requires -AllowDeployed or SIMULATION_ALLOW_DEPLOYED=1."
}

if (($Writes -or $Cleanup -or $CleanupOnly -or $RegisterSyntheticUser -or $KeepSyntheticData) -and $env:SIMULATION_ALLOW_WRITE -ne "1") {
    throw "Write or cleanup mode requires -AllowWrite or SIMULATION_ALLOW_WRITE=1."
}

if ($Profile -eq "burst" -and $env:SIMULATION_ALLOW_BURST -ne "1") {
    throw "Profile 'burst' requires -AllowBurst or SIMULATION_ALLOW_BURST=1."
}

$toolArgs = @("--target", $Target, "--profile", $Profile)

if ($BaseUrl) {
    $toolArgs += @("--base-url", $BaseUrl)
}

if ($Duration) {
    $toolArgs += @("--duration", $Duration)
}

if ($MaxRps -gt 0) {
    $toolArgs += @("--max-rps", ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $MaxRps)))
}

if ($Users -gt 0) {
    $toolArgs += @("--users", $Users.ToString([Globalization.CultureInfo]::InvariantCulture))
}

if ($ApiRpsBudget -ge 0) {
    $toolArgs += @("--api-rps-budget", ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $ApiRpsBudget)))
}

if ($AuthWriteRpsBudget -ge 0) {
    $toolArgs += @("--auth-write-rps-budget", ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $AuthWriteRpsBudget)))
}

if ($ReportDir) {
    $toolArgs += @("--report-dir", $ReportDir)
}

if ($AuthCheck) {
    $toolArgs += "--auth-check"
}

if ($AuthEmail) {
    $toolArgs += @("--auth-email", $AuthEmail)
}

if ($AuthPasswordEnv) {
    $toolArgs += @("--auth-password-env", $AuthPasswordEnv)
}

if ($RegisterSyntheticUser) {
    $toolArgs += "--register-synthetic-user"
}

if ($KeepSyntheticData) {
    $toolArgs += "--keep-synthetic-data"
}

if ($InstallBrowsers) {
    $toolArgs += "--install-browsers"
}

if ($HeadedBrowser) {
    $toolArgs += "--headed-browser"
}

if ($Writes) {
    $toolArgs += "--writes"
}

if ($Cleanup) {
    $toolArgs += "--cleanup"
}

if ($CleanupOnly) {
    $toolArgs += "--cleanup-only"
}

if ($BrowserSampler) {
    $toolArgs += "--browser-sampler"
}

if ($AllowRateLimit) {
    $toolArgs += "--allow-rate-limit"
}

if ($AllowDeployed) {
    $toolArgs += "--allow-deployed"
}

if ($AllowWrite) {
    $toolArgs += "--allow-write"
}

if ($AllowBurst) {
    $toolArgs += "--allow-burst"
}

if ($Yes) {
    $toolArgs += "--yes"
}

$artifactDir = Join-Path $repoRoot "artifacts/simulation"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

Write-Host "dotnet SDK: $(dotnet --version)"
Write-Host "Running traffic simulation from $repoRoot"
Write-Host "Command: dotnet run --project `"$projectPath`" -- $($toolArgs -join ' ')"

Push-Location $repoRoot
try {
    & dotnet run --project $projectPath -- @toolArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
