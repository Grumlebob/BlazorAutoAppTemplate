@echo off
REM Open App, Seq UI, and Redis Insight in the default browser
setlocal
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%OpenFullProject.ps1"
endlocal

