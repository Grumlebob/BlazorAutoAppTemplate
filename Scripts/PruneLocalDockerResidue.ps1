param(
  [switch]$DryRun,
  [switch]$Aggressive,
  [ValidateRange(0, 87600)]
  [int]$DanglingImageUntilHours = 0,
  [ValidateRange(0, 87600)]
  [int]$BuilderCacheUntilHours = 48,
  [ValidateRange(0, 87600)]
  [int]$StoppedContainerUntilHours = 24,
  [ValidateRange(0, 87600)]
  [int]$NetworkUntilHours = 24,
  [switch]$SkipBuilderCache,
  [switch]$SkipStoppedContainers,
  [switch]$SkipNetworks
)

$ErrorActionPreference = 'Stop'

if ($Aggressive) {
  $DanglingImageUntilHours = 0
  $BuilderCacheUntilHours = 0
  $StoppedContainerUntilHours = 0
  $NetworkUntilHours = 0
}

function Format-Command {
  param([string[]]$Arguments)

  return (($Arguments | ForEach-Object {
      if ($_ -match '\s') {
        "`"$_`""
      }
      else {
        $_
      }
    }) -join ' ')
}

function Invoke-Docker {
  param([string[]]$Arguments)

  $display = "docker $(Format-Command -Arguments $Arguments)"
  Write-Host "+ $display"

  if ($DryRun) {
    return
  }

  & docker @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$display failed with exit code $LASTEXITCODE."
  }
}

function Get-DockerLineCount {
  param([string[]]$Arguments)

  $output = @(& docker @Arguments 2>$null)
  if ($LASTEXITCODE -ne 0) {
    return 0
  }

  return @($output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count
}

function Write-Heading {
  param([string]$Text)

  Write-Host ""
  Write-Host "== $Text =="
}

function Write-DockerReport {
  param([string]$Label)

  Write-Heading $Label
  Write-Host "mode: $(if ($DryRun) { 'dry-run' } else { 'apply' })"
  Write-Host "hostname: $env:COMPUTERNAME"
  Write-Host "whoami: $env:USERNAME"
  docker system df
  Write-Host "total images: $(Get-DockerLineCount -Arguments @('image', 'ls', '-q'))"
  Write-Host "dangling images: $(Get-DockerLineCount -Arguments @('image', 'ls', '--filter', 'dangling=true', '-q'))"
  Write-Host "containers: $(Get-DockerLineCount -Arguments @('ps', '-a', '-q'))"
  Write-Host "volumes: $(Get-DockerLineCount -Arguments @('volume', 'ls', '-q'))"
}

function Assert-DockerAvailable {
  if ($null -eq (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is not available on PATH."
  }

  & docker info *> $null
  if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not ready or the Docker daemon is not reachable."
  }
}

Write-Heading "Local Docker residue cleanup"
Write-Host "This script never prunes Docker volumes."
Write-Host "Use .\Scripts\RunLocal.ps1 -ResetDatabase only when you intentionally want to delete local service volumes."

Assert-DockerAvailable
Write-DockerReport -Label "Before cleanup"

if (-not $SkipStoppedContainers) {
  Invoke-Docker -Arguments @('container', 'prune', '-f', '--filter', "until=$($StoppedContainerUntilHours)h")
}
else {
  Write-Host "stopped container cleanup skipped"
}

Invoke-Docker -Arguments @('image', 'prune', '-f', '--filter', "until=$($DanglingImageUntilHours)h")

if (-not $SkipBuilderCache) {
  Invoke-Docker -Arguments @('builder', 'prune', '-af', '--filter', "until=$($BuilderCacheUntilHours)h")
}
else {
  Write-Host "builder cache cleanup skipped"
}

if (-not $SkipNetworks) {
  Invoke-Docker -Arguments @('network', 'prune', '-f', '--filter', "until=$($NetworkUntilHours)h")
}
else {
  Write-Host "network cleanup skipped"
}

Write-DockerReport -Label "After cleanup"

Write-Heading "Not touched"
Write-Host "Docker volumes were not pruned."
Write-Host "Tagged images were not pruned by image cleanup; only dangling images are removed."
Write-Host "Local bind-mounted files such as ./data/storage were not deleted."
Write-Host "Local Docker residue cleanup complete."
