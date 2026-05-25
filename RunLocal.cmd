@echo off
setlocal

where pwsh >nul 2>nul
if errorlevel 1 (
  echo PowerShell 7 ^(pwsh^) is required to run the local Docker stack script.
  echo Install it from https://learn.microsoft.com/powershell/ or run: winget install Microsoft.PowerShell
  exit /b 1
)

pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0RunLocal.ps1" %*
exit /b %ERRORLEVEL%
