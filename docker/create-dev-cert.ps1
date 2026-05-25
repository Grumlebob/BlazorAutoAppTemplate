param(
  [string]$Password = "localdevpassword",
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$outDir = Join-Path $PSScriptRoot 'https'
if (-not (Test-Path $outDir)) {
  New-Item -ItemType Directory -Path $outDir | Out-Null
}

$pfxPath = Join-Path $outDir 'aspnetapp.pfx'

if ((Test-Path $pfxPath) -and -not $Force) {
  Write-Host "HTTPS dev certificate already exists: $pfxPath"
  Write-Host "Use -Force to recreate it."
  return
}

Write-Host "Exporting ASP.NET Core HTTPS dev cert to: $pfxPath"
& dotnet dev-certs https --trust | Out-Null
& dotnet dev-certs https -ep $pfxPath -p $Password

Write-Host "Done. Mounting this folder in docker-compose enables HTTPS on port 7186."
