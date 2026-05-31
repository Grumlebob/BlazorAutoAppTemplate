param(
    [switch] $Local,
    [switch] $LocalCluster,
    [switch] $Cloud,
    [switch] $All,
    [switch] $IncludeWrites,
    [switch] $RegisterSyntheticUsers,
    [switch] $AllowDeployedWrites,
    [string] $Duration = "60s",
    [switch] $SkipReadOnly,
    [switch] $Help
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$simulationRoot = Join-Path $repoRoot "artifacts/simulation"
$runSimulation = Join-Path $scriptRoot "RunSimulation.ps1"

function Show-Help {
    Write-Host @"
RunSimulationMatrix.ps1

Runs a safe traffic-simulation matrix and stops immediately on the first failed
simulation command.

Examples:
  .\Scripts\RunSimulationMatrix.ps1 -All
  .\Scripts\RunSimulationMatrix.ps1 -Local -IncludeWrites
  .\Scripts\RunSimulationMatrix.ps1 -LocalCluster -Cloud -IncludeWrites -RegisterSyntheticUsers -AllowDeployedWrites

Safety:
  - Read-only deployed simulation is allowed with -LocalCluster/-Cloud/-All.
  - Deployed writes require -IncludeWrites and -AllowDeployedWrites.
  - Deployed registration requires -RegisterSyntheticUsers.
  - Passwords are generated in memory when -RegisterSyntheticUsers is used and
    are never printed.
"@
}

if ($Help) {
    Show-Help
    exit 0
}

if (-not (Test-Path $runSimulation)) {
    throw "RunSimulation.ps1 was not found at $runSimulation"
}

if (-not ($Local -or $LocalCluster -or $Cloud -or $All)) {
    $Local = $true
}

$targets = [System.Collections.Generic.List[string]]::new()
if ($All -or $Local) {
    $targets.Add("local")
}

if ($All -or $LocalCluster) {
    $targets.Add("localcluster-public")
}

if ($All -or $Cloud) {
    $targets.Add("cloud-public")
}

if ($IncludeWrites -and ($targets | Where-Object { $_ -ne "local" }) -and -not $AllowDeployedWrites) {
    throw "Deployed write simulation requires -AllowDeployedWrites."
}

function New-SimulationPassword {
    return "Sim!" + [Guid]::NewGuid().ToString("N") + "aA1"
}

function New-SimulationEmail {
    param([Parameter(Mandatory = $true)][string] $Target)

    $prefix = switch ($Target) {
        "localcluster-public" { "simlc" }
        "cloud-public" { "simcl" }
        default { "simlo" }
    }

    $stamp = Get-Date -Format "MMddHHmmss"
    $suffix = [Guid]::NewGuid().ToString("N").Substring(0, 6)
    return "$prefix$stamp$suffix@example.com"
}

function Get-ReportDirectories {
    if (-not (Test-Path $simulationRoot)) {
        return @()
    }

    return @(Get-ChildItem -Path $simulationRoot -Directory |
        Where-Object { $_.Name -match '^\d{8}-\d{6}-(local|localcluster-public|cloud-public)-' } |
        Select-Object -ExpandProperty FullName)
}

function Invoke-SimulationStrict {
    param(
        [Parameter(Mandatory = $true)][hashtable] $Parameters,
        [Parameter(Mandatory = $true)][string] $Label
    )

    $before = Get-ReportDirectories
    $display = ($Parameters.GetEnumerator() | Sort-Object Name | ForEach-Object {
        if ($_.Value -is [bool]) {
            if ($_.Value) { "-$($_.Name)" }
        }
        else {
            "-$($_.Name) $($_.Value)"
        }
    }) -join " "

    Write-Host "Running [$Label]: .\Scripts\RunSimulation.ps1 $display"
    & $runSimulation @Parameters | ForEach-Object { Write-Host $_ }
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "RunSimulation failed with exit code $exitCode for [$Label]: $display"
    }

    $after = Get-ReportDirectories
    $newReports = @($after | Where-Object { $before -notcontains $_ })
    foreach ($report in $newReports) {
        [pscustomobject]@{
            Target = $Parameters.Target
            Label = $Label
            Report = $report
        }
    }
}

$originalEmail = [Environment]::GetEnvironmentVariable("SIMULATION_AUTH_EMAIL", "Process")
$originalPassword = [Environment]::GetEnvironmentVariable("SIMULATION_AUTH_PASSWORD", "Process")
$results = [System.Collections.Generic.List[object]]::new()

try {
    foreach ($target in $targets) {
        $isDeployed = $target -ne "local"
        Write-Host "=== $target ==="

        if (-not $SkipReadOnly) {
            $readOnly = @{
                Target = $target
                Profile = "smoke"
                Duration = $Duration
            }
            if ($isDeployed) {
                $readOnly.AllowDeployed = $true
            }

            foreach ($result in Invoke-SimulationStrict -Parameters $readOnly -Label "read-only") {
                $results.Add($result)
            }
        }

        if (-not $IncludeWrites) {
            continue
        }

        $generatedCredentials = $false
        if ($isDeployed) {
            if ($RegisterSyntheticUsers) {
                $env:SIMULATION_AUTH_EMAIL = New-SimulationEmail -Target $target
                $env:SIMULATION_AUTH_PASSWORD = New-SimulationPassword
                $generatedCredentials = $true
            }
            elseif ([string]::IsNullOrWhiteSpace($env:SIMULATION_AUTH_EMAIL) -or [string]::IsNullOrWhiteSpace($env:SIMULATION_AUTH_PASSWORD)) {
                throw "$target writes require SIMULATION_AUTH_EMAIL/SIMULATION_AUTH_PASSWORD or -RegisterSyntheticUsers."
            }
        }

        try {
            $registerOrAuth = @{
                Target = $target
                AuthCheck = $true
            }
            if ($isDeployed) {
                $registerOrAuth.AllowDeployed = $true
                $registerOrAuth.AllowWrite = $true
            }
            if ($generatedCredentials) {
                $registerOrAuth.RegisterSyntheticUser = $true
            }

            foreach ($result in Invoke-SimulationStrict -Parameters $registerOrAuth -Label "auth") {
                $results.Add($result)
            }

            if ($generatedCredentials) {
                $loginCheck = @{
                    Target = $target
                    AuthCheck = $true
                    AllowDeployed = $true
                }

                foreach ($result in Invoke-SimulationStrict -Parameters $loginCheck -Label "auth-login") {
                    $results.Add($result)
                }
            }

            $write = @{
                Target = $target
                Profile = "smoke"
                Duration = $Duration
                Writes = $true
                Cleanup = $true
                BrowserSampler = $true
                AllowWrite = $true
            }
            if ($isDeployed) {
                $write.AllowDeployed = $true
            }

            foreach ($result in Invoke-SimulationStrict -Parameters $write -Label "browser-write-cleanup") {
                $results.Add($result)
            }

            $cleanup = @{
                Target = $target
                CleanupOnly = $true
                AllowWrite = $true
            }
            if ($isDeployed) {
                $cleanup.AllowDeployed = $true
            }

            foreach ($result in Invoke-SimulationStrict -Parameters $cleanup -Label "cleanup-only") {
                $results.Add($result)
            }
        }
        finally {
            if ($generatedCredentials) {
                if ($null -eq $originalEmail) {
                    Remove-Item Env:SIMULATION_AUTH_EMAIL -ErrorAction SilentlyContinue
                }
                else {
                    $env:SIMULATION_AUTH_EMAIL = $originalEmail
                }

                if ($null -eq $originalPassword) {
                    Remove-Item Env:SIMULATION_AUTH_PASSWORD -ErrorAction SilentlyContinue
                }
                else {
                    $env:SIMULATION_AUTH_PASSWORD = $originalPassword
                }
            }
        }
    }
}
finally {
    if ($null -eq $originalEmail) {
        Remove-Item Env:SIMULATION_AUTH_EMAIL -ErrorAction SilentlyContinue
    }
    else {
        $env:SIMULATION_AUTH_EMAIL = $originalEmail
    }

    if ($null -eq $originalPassword) {
        Remove-Item Env:SIMULATION_AUTH_PASSWORD -ErrorAction SilentlyContinue
    }
    else {
        $env:SIMULATION_AUTH_PASSWORD = $originalPassword
    }
}

Write-Host ""
Write-Host "Simulation matrix reports"
$results |
    Sort-Object Target, Label, Report |
    Format-Table -AutoSize Target, Label, Report
