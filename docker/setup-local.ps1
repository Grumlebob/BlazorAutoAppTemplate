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
}

if (-not $SkipCertificate) {
  & (Join-Path $PSScriptRoot 'create-dev-cert.ps1')
}

python (Join-Path $PSScriptRoot 'local-status.py')
