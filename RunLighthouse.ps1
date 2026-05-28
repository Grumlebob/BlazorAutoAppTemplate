param(
  [string]$BaseUrl = "https://127.0.0.1:7186",
  [string[]]$Paths = @("/"),
  [ValidateSet("mobile", "desktop", "both")]
  [string]$Profile = "both",
  [string]$Label = "local",
  [switch]$IgnoreCertificateErrors,
  [switch]$AuthenticatedLocalUser,
  [string]$Email = "user@user.com",
  [string]$Password = "User123",
  [string]$OutputRoot = "TestResults/Lighthouse"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$clientRoot = Join-Path $repoRoot "BlazorAutoApp.Client"
$outputRootPath = Join-Path $repoRoot $OutputRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDirectory = Join-Path $outputRootPath "$Label-$timestamp"
$nodeCommand = "node"
$lighthouseCli = Join-Path $clientRoot "node_modules/lighthouse/cli/index.js"

function Join-AppUrl([string]$Base, [string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path) -or $Path -eq "/") {
    return $Base.TrimEnd("/")
  }

  return "$($Base.TrimEnd('/'))/$($Path.TrimStart('/'))"
}

function ConvertTo-SafeName([string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value) -or $Value -eq "/") {
    return "home"
  }

  $name = $Value.Trim("/").Replace("/", "-")
  return ($name -replace "[^a-zA-Z0-9._-]", "-").Trim("-").ToLowerInvariant()
}

function Get-HtmlInputValue([string]$Html, [string]$Name) {
  $pattern = "<input[^>]*name\s*=\s*[""']$([regex]::Escape($Name))[""'][^>]*value\s*=\s*[""']([^""']*)[""'][^>]*>"
  $match = [regex]::Match($Html, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if ($match.Success) {
    return [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value)
  }

  $reversePattern = "<input[^>]*value\s*=\s*[""']([^""']*)[""'][^>]*name\s*=\s*[""']$([regex]::Escape($Name))[""'][^>]*>"
  $reverseMatch = [regex]::Match($Html, $reversePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if ($reverseMatch.Success) {
    return [System.Net.WebUtility]::HtmlDecode($reverseMatch.Groups[1].Value)
  }

  return $null
}

function Get-AuthenticatedHeadersJson {
  $loginUrl = Join-AppUrl $BaseUrl "/Account/Login"
  $session = [Microsoft.PowerShell.Commands.WebRequestSession]::new()
  $loginPage = Invoke-WebRequest -Uri $loginUrl -WebSession $session -SkipCertificateCheck
  $token = Get-HtmlInputValue -Html $loginPage.Content -Name "__RequestVerificationToken"
  if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Could not find the login antiforgery token at $loginUrl."
  }

  $body = @{
    "_handler" = "login"
    "__RequestVerificationToken" = $token
    "Input.Email" = $Email
    "Input.Password" = $Password
  }

  $response = Invoke-WebRequest `
    -Uri $loginUrl `
    -Method Post `
    -WebSession $session `
    -Body $body `
    -Headers @{ Referer = $loginUrl; Origin = $BaseUrl.TrimEnd("/") } `
    -ContentType "application/x-www-form-urlencoded" `
    -SkipCertificateCheck

  if ($response.StatusCode -ne 200) {
    throw "Local Lighthouse login failed with HTTP $($response.StatusCode)."
  }

  $cookies = $session.Cookies.GetCookies([Uri]$BaseUrl)
  $cookieHeader = ($cookies | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join "; "
  if ([string]::IsNullOrWhiteSpace($cookieHeader) -or $cookieHeader -notmatch "Identity") {
    throw "Local Lighthouse login did not produce an Identity cookie."
  }

  return (@{ Cookie = $cookieHeader } | ConvertTo-Json -Compress)
}

function Get-ReportJsonPath([string]$OutputBase) {
  $candidates = @(
    "$OutputBase.report.json",
    "$OutputBase.json"
  )

  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }

  return $null
}

New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null

if (-not (Test-Path -LiteralPath $lighthouseCli)) {
  throw "Lighthouse CLI was not found at $lighthouseCli. Run npm install in $clientRoot first."
}

$profiles = if ($Profile -eq "both") { @("mobile", "desktop") } else { @($Profile) }
$extraHeadersPath = $null
if ($AuthenticatedLocalUser) {
  Write-Host "Creating authenticated local Lighthouse session for $Email..."
  $extraHeadersPath = Join-Path $runDirectory "authenticated-headers.json"
  Get-AuthenticatedHeadersJson | Set-Content -LiteralPath $extraHeadersPath -Encoding utf8
}

Write-Host "Writing Lighthouse reports to $runDirectory"

foreach ($path in $Paths) {
  foreach ($currentProfile in $profiles) {
    $url = Join-AppUrl $BaseUrl $path
    $safePath = ConvertTo-SafeName $path
    $outputBase = Join-Path $runDirectory "$safePath-$currentProfile"
    $arguments = @(
      $lighthouseCli,
      $url,
      "--output=html",
      "--output=json",
      "--output-path=$outputBase",
      "--quiet"
    )

    if ($currentProfile -eq "desktop") {
      $arguments += "--preset=desktop"
    }

    if ($IgnoreCertificateErrors) {
      $arguments += "--chrome-flags=--ignore-certificate-errors"
    }

    if ($extraHeadersPath) {
      $arguments += "--extra-headers=$extraHeadersPath"
    }

    Write-Host "Running Lighthouse $currentProfile for $url"
    & $nodeCommand @arguments
    if ($LASTEXITCODE -ne 0) {
      throw "Lighthouse failed for $url ($currentProfile)."
    }

    $jsonPath = Get-ReportJsonPath -OutputBase $outputBase
    if ($jsonPath) {
      $report = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json
      $scores = [ordered]@{}
      foreach ($category in @("performance", "accessibility", "best-practices", "seo")) {
        if ($report.categories.$category) {
          $scores[$category] = [int]($report.categories.$category.score * 100)
        }
      }

      $scoreText = ($scores.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ", "
      Write-Host "Scores: $scoreText"
    }
  }
}

Write-Host "Lighthouse run complete: $runDirectory"
