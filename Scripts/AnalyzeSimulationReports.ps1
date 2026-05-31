param(
    [string] $ReportRoot = "artifacts/simulation",
    [int] $Latest = 30,
    [string[]] $Report,
    [switch] $Help
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot

function Show-Help {
    Write-Host @"
AnalyzeSimulationReports.ps1

Reads traffic simulation summary.json files and prints a compact Markdown table.

Examples:
  .\Scripts\AnalyzeSimulationReports.ps1 -Latest 15
  .\Scripts\AnalyzeSimulationReports.ps1 -Report artifacts/simulation/20260530-215221-cloud-public-smoke

The script reads local artifacts only. It does not call deployed targets and it
does not require credentials.
"@
}

if ($Help) {
    Show-Help
    exit 0
}

function Format-Number {
    param([double] $Value)

    return $Value.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
}

function Escape-Markdown {
    param([string] $Value)

    return ($Value -replace '\|', '\|')
}

function Get-SummaryPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not [System.IO.Path]::IsPathRooted($Path)) {
        $Path = Join-Path $repoRoot $Path
    }

    if (Test-Path $Path -PathType Container) {
        return Join-Path $Path "summary.json"
    }

    return $Path
}

if ($Report -and $Report.Count -gt 0) {
    $summaryPaths = @($Report | ForEach-Object { Get-SummaryPath -Path $_ })
}
else {
    if (-not [System.IO.Path]::IsPathRooted($ReportRoot)) {
        $ReportRoot = Join-Path $repoRoot $ReportRoot
    }

    if (-not (Test-Path $ReportRoot)) {
        throw "Report root was not found: $ReportRoot"
    }

    $summaryPaths = @(Get-ChildItem -Path $ReportRoot -Directory |
        Where-Object { $_.Name -match '^\d{8}-\d{6}-(local|localcluster-public|cloud-public)-' } |
        Sort-Object Name -Descending |
        Select-Object -First $Latest |
        ForEach-Object { Join-Path $_.FullName "summary.json" })
}

$rows = foreach ($path in $summaryPaths) {
    if (-not (Test-Path $path)) {
        throw "summary.json was not found: $path"
    }

    $summary = Get-Content $path -Raw | ConvertFrom-Json
    $status = ($summary.statusCodes.PSObject.Properties |
        Sort-Object Name |
        ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ", "

    $alerts = [System.Collections.Generic.List[string]]::new()
    if ($summary.failedThresholds) {
        $alerts.Add("failed")
    }

    if ([int]$summary.rateLimit.unexpected429 -gt 0) {
        $alerts.Add("unexpected429")
    }

    $has5xx = $summary.statusCodes.PSObject.Properties |
        Where-Object { $_.Name -match '^5\d\d$' -and [int]$_.Value -gt 0 }
    if ($has5xx) {
        $alerts.Add("5xx")
    }

    if ($summary.writes.enabled -and [int]$summary.writes.leftoverSyntheticBooks -gt 0) {
        $alerts.Add("leftovers")
    }

    if ($summary.browserSampler.enabled -and [int]$summary.browserSampler.journeysFailed -gt 0) {
        $alerts.Add("browser")
    }

    [pscustomobject]@{
        Report = Split-Path -Leaf (Split-Path -Parent $path)
        Target = $summary.target
        Requests = $summary.requestCount
        Status = $status
        P50Ms = Format-Number ([double]$summary.latency.p50Ms)
        P95Ms = Format-Number ([double]$summary.latency.p95Ms)
        P99Ms = Format-Number ([double]$summary.latency.p99Ms)
        Unexpected429 = $summary.rateLimit.unexpected429
        Auth = if ($summary.auth.enabled) { $summary.auth.mode } else { "disabled" }
        AuthApi = if ($summary.auth.enabled) { [string]$summary.auth.authenticatedApiCheckSucceeded } else { "" }
        Writes = [string]$summary.writes.enabled
        Cleanup = $summary.writes.cleanupStatus
        Browser = if ($summary.browserSampler.enabled) { "$($summary.browserSampler.journeysSucceeded)/$($summary.browserSampler.journeysStarted)" } else { "" }
        Alerts = if ($alerts.Count -eq 0) { "" } else { $alerts -join ", " }
    }
}

$headers = @(
    "Report",
    "Target",
    "Requests",
    "Status",
    "P50Ms",
    "P95Ms",
    "P99Ms",
    "Unexpected429",
    "Auth",
    "AuthApi",
    "Writes",
    "Cleanup",
    "Browser",
    "Alerts"
)

"| " + ($headers -join " | ") + " |"
"| " + (($headers | ForEach-Object { "---" }) -join " | ") + " |"
foreach ($row in $rows) {
    "| " + (($headers | ForEach-Object { Escape-Markdown ([string]$row.$_) }) -join " | ") + " |"
}
