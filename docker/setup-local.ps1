param(
  [switch]$SkipCertificate
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$examplePath = Join-Path $repoRoot '.env.example'

if (-not (Test-Path $envPath)) {
  Copy-Item -Path $examplePath -Destination $envPath
  Write-Host "Created .env from .env.example"
}
else {
  Write-Host ".env already exists"
  $existingKeys = @{}
  Get-Content -Path $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=') {
      $existingKeys[$matches[1].Trim()] = $true
    }
  }

  $missingLines = @()
  Get-Content -Path $examplePath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=') {
      $key = $matches[1].Trim()
      if (-not $existingKeys.ContainsKey($key)) {
        $missingLines += $_
      }
    }
  }

  if ($missingLines.Count -gt 0) {
    Add-Content -Path $envPath -Value ""
    Add-Content -Path $envPath -Value "# Added by docker/setup-local.ps1 from .env.example"
    Add-Content -Path $envPath -Value $missingLines
    Write-Host "Added missing .env key(s): $($missingLines.Count)"
  }
}

if (-not $SkipCertificate) {
  & (Join-Path $PSScriptRoot 'create-dev-cert.ps1')
}

python (Join-Path $PSScriptRoot 'local-status.py')
