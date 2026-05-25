param(
  [switch]$NoBuild,
  [switch]$NoBrowser,
  [switch]$ResetDatabase,
  [switch]$SkipCertificate,
  [switch]$FollowLogs,
  [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'

function Wait-Docker {
  param([int]$TimeoutSeconds = 90)

  Write-Host "Checking Docker Desktop..."
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      docker info --format '{{.ServerVersion}}' *> $null
      if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker Desktop is ready."
        return
      }
    }
    catch {
      # Docker is commonly still starting here; retry until the deadline.
    }

    Start-Sleep -Seconds 2
  }

  throw "Docker Desktop is not ready. Start Docker Desktop, wait until it finishes starting, and run .\RunLocal.ps1 again."
}

function Read-DotEnv {
  param([string]$Path)

  $values = @{}
  if (-not (Test-Path -LiteralPath $Path)) {
    return $values
  }

  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if ($line.Length -eq 0 -or $line.StartsWith('#') -or -not $line.Contains('=')) {
      return
    }

    $key, $value = $line.Split('=', 2)
    $values[$key.Trim()] = $value.Trim().Trim('"').Trim("'")
  }

  return $values
}

function Invoke-HealthCheck {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -SkipCertificateCheck -TimeoutSec 5
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
  }
  catch {
    return $false
  }
}

function Get-ComposeServiceState {
  param([string]$Service)

  $output = docker compose ps -a --format json $Service 2>$null
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
    return $null
  }

  try {
    $state = $output | ConvertFrom-Json
    if ($state -is [array]) {
      return $state | Select-Object -First 1
    }

    return $state
  }
  catch {
    return $null
  }
}

function Get-WebLogs {
  param([string]$Since)

  $logArgs = @('compose', 'logs', 'web', '--tail=160')
  if (-not [string]::IsNullOrWhiteSpace($Since)) {
    $logArgs += @('--since', $Since)
  }

  docker @logArgs 2>&1 | Out-String
}

function Write-StartupFailureHelp {
  param([string]$Logs)

  if ($Logs -match 'relation "AspNetRoles" already exists' -or $Logs -match '42P07') {
    Write-Host ""
    Write-Warning "The local Docker PostgreSQL volume contains an older schema. This repo now has a fresh initial migration, so the old local database must be reset."
    Write-Host "Run: .\RunLocal.ps1 -ResetDatabase"
  }
}

Push-Location $repoRoot
try {
  Wait-Docker

  Write-Host "Preparing local Docker setup..."
  $setupArgs = @('-File', './docker/setup-local.ps1')
  if ($SkipCertificate) {
    $setupArgs += '-SkipCertificate'
  }
  & pwsh @setupArgs

  if ($LASTEXITCODE -ne 0) {
    throw "Local setup failed."
  }

  $envValues = Read-DotEnv -Path $envPath
  $appUrl = $envValues['App__Url']
  if ([string]::IsNullOrWhiteSpace($appUrl)) {
    $appPort = $envValues['APP_HTTPS_HOST_PORT']
    if ([string]::IsNullOrWhiteSpace($appPort)) {
      $appPort = '7186'
    }
    $appUrl = "https://localhost:$appPort"
  }

  $healthUrl = "$($appUrl.TrimEnd('/'))/health/ready"

  if ($ResetDatabase) {
    Write-Host "Resetting local Docker database and service volumes..."
    docker compose down --volumes
  }

  $composeArgs = @('compose', 'up', '-d')
  if (-not $NoBuild) {
    $composeArgs += '--build'
  }
  $composeArgs += 'web'

  Write-Host "Starting local Docker stack..."
  $logSince = (Get-Date).ToUniversalTime().AddSeconds(-5).ToString('yyyy-MM-ddTHH:mm:ssZ')
  docker @composeArgs

  if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed to start the local stack."
  }

  Write-Host "Waiting for app health: $healthUrl"
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $isReady = $false
  while ((Get-Date) -lt $deadline) {
    if (Invoke-HealthCheck -Url $healthUrl) {
      $isReady = $true
      break
    }

    $webState = Get-ComposeServiceState -Service 'web'
    if ($null -ne $webState -and $webState.State -eq 'exited') {
      Write-Host ""
      Write-Host "The app container exited before it became ready. Recent web logs:"
      $logs = Get-WebLogs -Since $logSince
      Write-Host $logs
      Write-StartupFailureHelp -Logs $logs
      throw "Local app container exited with code $($webState.ExitCode)."
    }

    Start-Sleep -Seconds 2
  }

  if (-not $isReady) {
    Write-Host ""
    Write-Host "The app did not become ready before the timeout. Recent web logs:"
    $logs = Get-WebLogs -Since $logSince
    Write-Host $logs
    Write-StartupFailureHelp -Logs $logs
    throw "Local app health check failed: $healthUrl"
  }

  Write-Host ""
  Write-Host "Local stack is ready."
  Write-Host "App:          $appUrl"
  Write-Host "Health:       $healthUrl"
  Write-Host "Seq:          http://localhost:$($envValues['SEQ_UI_HOST_PORT'] ?? '8081')"
  Write-Host "RedisInsight: http://localhost:$($envValues['REDIS_INSIGHT_HOST_PORT'] ?? '5540')"
  Write-Host ""
  Write-Host "Stop with:    docker compose down"
  Write-Host "Reset with:   .\RunLocal.ps1 -ResetDatabase"

  if (-not $NoBrowser) {
    Start-Process $appUrl
  }

  if ($FollowLogs) {
    docker compose logs -f web
  }
}
finally {
  Pop-Location
}
