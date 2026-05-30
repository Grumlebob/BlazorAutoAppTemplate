param(
  [string]$AppUrl = 'https://localhost:7186',
  [string]$GrafanaUrl = 'http://localhost:3000',
  [string]$PrometheusUrl = 'http://localhost:9090',
  [string]$AlertmanagerUrl = 'http://localhost:9093',
  [string]$LokiUrl = 'http://localhost:3100',
  [string]$TempoUrl = 'http://localhost:3200',
  [int]$TimeoutSeconds = 180,
  [int]$PrometheusSeriesWarningThreshold = 10000,
  [int]$LokiStreamWarningThreshold = 100
)

$ErrorActionPreference = 'Stop'

function Invoke-Json {
  param([string]$Url)

  Invoke-RestMethod -Uri $Url -TimeoutSec 10
}

function Wait-Until {
  param(
    [string]$Description,
    [scriptblock]$Probe,
    [int]$TimeoutSeconds = 180
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $lastError = $null
  while ((Get-Date) -lt $deadline) {
    try {
      $result = & $Probe
      if ($result) {
        Write-Host "OK    $Description"
        return
      }
    }
    catch {
      $lastError = $_
    }

    Start-Sleep -Seconds 3
  }

  if ($null -ne $lastError) {
    throw "$Description failed: $($lastError.Exception.Message)"
  }

  throw "$Description failed before timeout"
}

function Test-PrometheusQuery {
  param([string[]]$Queries)

  foreach ($query in $Queries) {
    $encodedQuery = [uri]::EscapeDataString($query)
    $result = Invoke-Json "$PrometheusUrl/api/v1/query?query=$encodedQuery"
    if ($result.status -eq 'success' -and $result.data.result.Count -gt 0) {
      return $query
    }
  }

  return $null
}

Push-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
try {
  Write-Host "Generating local app telemetry..."
  for ($i = 0; $i -lt 8; $i++) {
    Invoke-WebRequest -Uri $AppUrl -SkipCertificateCheck -TimeoutSec 10 *> $null
    Start-Sleep -Milliseconds 250
  }

  Wait-Until 'Grafana is reachable' {
    $health = Invoke-Json "$GrafanaUrl/api/health"
    $health.database -eq 'ok'
  } -TimeoutSeconds $TimeoutSeconds

  Wait-Until 'Alertmanager is reachable' {
    $response = Invoke-WebRequest -Uri "$AlertmanagerUrl/-/healthy" -TimeoutSec 10
    $response.StatusCode -eq 200
  } -TimeoutSeconds $TimeoutSeconds

  $prometheusQuery = Wait-Until 'Prometheus has app request metrics' {
    Test-PrometheusQuery @(
      'sum(http_server_request_duration_seconds_count)',
      'sum(http_server_request_duration_milliseconds_count)',
      'sum(http_server_request_duration_count)'
    )
  } -TimeoutSeconds $TimeoutSeconds

  Wait-Until 'Prometheus is connected to Alertmanager' {
    $alertmanagers = Invoke-Json "$PrometheusUrl/api/v1/alertmanagers"
    $alertmanagers.status -eq 'success' -and $alertmanagers.data.activeAlertmanagers.Count -gt 0
  } -TimeoutSeconds $TimeoutSeconds

  Wait-Until 'Prometheus has app instance versions' {
    $query = [uri]::EscapeDataString('target_info{deployment_target="local"}')
    $result = Invoke-Json "$PrometheusUrl/api/v1/query?query=$query"
    $instances = @($result.data.result | Where-Object { -not [string]::IsNullOrWhiteSpace($_.metric.service_version) })
    $instances.Count -gt 0
  } -TimeoutSeconds $TimeoutSeconds

  Wait-Until 'Loki has app container logs' {
    $query = [uri]::EscapeDataString('{service="web"}')
    $startNs = [DateTimeOffset]::UtcNow.AddMinutes(-15).ToUnixTimeMilliseconds() * 1000000
    $result = Invoke-Json "$LokiUrl/loki/api/v1/query_range?query=$query&start=$startNs&limit=1"
    $result.status -eq 'success' -and $result.data.result.Count -gt 0
  } -TimeoutSeconds $TimeoutSeconds

  Wait-Until 'Tempo has app traces' {
    $result = Invoke-Json "$TempoUrl/api/search?limit=20"
    $result.traces.Count -gt 0
  } -TimeoutSeconds $TimeoutSeconds

  $tsdb = Invoke-Json "$PrometheusUrl/api/v1/status/tsdb"
  $numSeries = [int]$tsdb.data.headStats.numSeries
  if ($numSeries -gt $PrometheusSeriesWarningThreshold) {
    throw "Prometheus active series $numSeries exceeds warning threshold $PrometheusSeriesWarningThreshold"
  }
  Write-Host "OK    Prometheus active series below threshold: $numSeries"

  $startNs = [DateTimeOffset]::UtcNow.AddMinutes(-15).ToUnixTimeMilliseconds() * 1000000
  $seriesQuery = [uri]::EscapeDataString('{deployment_target="local"}')
  $lokiSeries = Invoke-Json "$LokiUrl/loki/api/v1/series?match[]=$seriesQuery&start=$startNs"
  $streamCount = $lokiSeries.data.Count
  if ($streamCount -gt $LokiStreamWarningThreshold) {
    throw "Loki stream count $streamCount exceeds warning threshold $LokiStreamWarningThreshold"
  }
  Write-Host "OK    Loki streams below threshold: $streamCount"

  $containerIds = docker compose ps -q
  foreach ($containerId in $containerIds) {
    if ([string]::IsNullOrWhiteSpace($containerId)) {
      continue
    }

    $inspect = docker inspect $containerId | ConvertFrom-Json
    $name = $inspect[0].Name.TrimStart('/')
    if ($inspect[0].State.OOMKilled) {
      throw "Container $name was OOMKilled"
    }
  }
  Write-Host "OK    no Compose container reports OOMKilled"

  Write-Host ""
  Write-Host "local observability smoke ok"
}
finally {
  Pop-Location
}
