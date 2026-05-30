param(
  [switch]$NoBuild,
  [switch]$NoBrowser,
  [switch]$ResetDatabase,
  [switch]$SkipCertificate,
  [switch]$FollowLogs,
  [switch]$StatusOnly,
  [switch]$Observability,
  [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$previousObservabilityEnabled = $env:OBSERVABILITY_ENABLED
$previousObservabilityEndpoint = $env:OBSERVABILITY_OTLP_ENDPOINT
$previousObservabilityProtocol = $env:OBSERVABILITY_OTLP_PROTOCOL
$previousObservabilitySampleRatio = $env:OBSERVABILITY_TRACE_SAMPLE_RATIO

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

function Get-ListeningProcessIds {
  param([int]$Port)

  try {
    return @(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction Stop |
      Select-Object -ExpandProperty OwningProcess -Unique)
  }
  catch {
    return @()
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
  if ($StatusOnly) {
    Write-Host "Preparing and checking local Docker setup..."
    $statusSetupArgs = @('-File', './docker/setup-local.ps1')
    if ($SkipCertificate) {
      $statusSetupArgs += '-SkipCertificate'
    }
    & pwsh @statusSetupArgs
    if ($LASTEXITCODE -ne 0) {
      throw "Local setup status failed."
    }
    return
  }

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
  $grafanaUrl = "http://localhost:$($envValues['GRAFANA_HOST_PORT'] ?? '3000')"
  $alertmanagerUrl = "http://localhost:$($envValues['ALERTMANAGER_HOST_PORT'] ?? '9093')"
  $prometheusUrl = "http://localhost:$($envValues['PROMETHEUS_HOST_PORT'] ?? '9090')"
  $lokiUrl = "http://localhost:$($envValues['LOKI_HOST_PORT'] ?? '3100')"
  $tempoUrl = "http://localhost:$($envValues['TEMPO_HOST_PORT'] ?? '3200')"
  $dotnetDevPids = Get-ListeningProcessIds -Port 5099
  if ($dotnetDevPids.Count -gt 0) {
    Write-Warning "A local dotnet app is already listening on 127.0.0.1:5099 (PID(s): $($dotnetDevPids -join ', ')). The Docker stack can still start on its configured app port; use E2E_BASE_URL intentionally when testing."
  }

  if ($ResetDatabase) {
    Write-Host "Resetting local Docker database and service volumes..."
    docker compose down --volumes --remove-orphans
  }

  if ($Observability) {
    $env:OBSERVABILITY_ENABLED = 'true'
    $env:OBSERVABILITY_OTLP_ENDPOINT = 'http://alloy:4317'
    $env:OBSERVABILITY_OTLP_PROTOCOL = 'Grpc'
    $env:OBSERVABILITY_TRACE_SAMPLE_RATIO = '1.0'
  }

  $composeArgs = @('compose')
  if ($Observability) {
    $composeArgs += @('--profile', 'observability')
  }
  $composeArgs += @('up', '-d')
  if (-not $NoBuild) {
    $composeArgs += '--build'
  }
  if ($Observability) {
    $composeArgs += '--force-recreate'
  }
  $composeArgs += '--remove-orphans'
  $composeServices = @('web')
  if ($Observability) {
    $composeServices += @('prometheus', 'alertmanager', 'loki', 'tempo', 'alloy', 'grafana')
  }
  $composeArgs += $composeServices

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

  if ($Observability) {
    Write-Host "Waiting for Grafana health: $grafanaUrl/api/health"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $grafanaReady = $false
    while ((Get-Date) -lt $deadline) {
      if (Invoke-HealthCheck -Url "$grafanaUrl/api/health") {
        $grafanaReady = $true
        break
      }

      Start-Sleep -Seconds 2
    }

    if (-not $grafanaReady) {
      throw "Grafana health check failed: $grafanaUrl/api/health"
    }
  }

  Write-Host ""
  Write-Host "Local stack is ready."
  Write-Host "Runtime:      Docker Compose web container"
  Write-Host "App:          $appUrl"
  Write-Host "Health:       $healthUrl"
  Write-Host "RedisInsight: http://localhost:$($envValues['REDIS_INSIGHT_HOST_PORT'] ?? '5540')"
  if ($Observability) {
    Write-Host "Grafana:      $grafanaUrl"
    Write-Host "Alertmanager: $alertmanagerUrl"
    Write-Host "Prometheus:   $prometheusUrl"
    Write-Host "Loki:         $lokiUrl"
    Write-Host "Tempo:        $tempoUrl"
    Write-Host "Smoke check:  pwsh -File .\docker\observability\smoke-local-observability.ps1"
  }
  else {
    Write-Host "Observability: disabled; run .\RunLocal.ps1 -Observability to start the local Grafana stack."
  }
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
  $env:OBSERVABILITY_ENABLED = $previousObservabilityEnabled
  $env:OBSERVABILITY_OTLP_ENDPOINT = $previousObservabilityEndpoint
  $env:OBSERVABILITY_OTLP_PROTOCOL = $previousObservabilityProtocol
  $env:OBSERVABILITY_TRACE_SAMPLE_RATIO = $previousObservabilitySampleRatio
  Pop-Location
}
