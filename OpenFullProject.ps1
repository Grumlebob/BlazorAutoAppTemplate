Param(
    [switch]$Wait
)

$urls = @(
    "http://localhost:8080",   # App (HTTP)
    "https://localhost:8443",  # App (HTTPS)
    "http://localhost:8081",   # Seq UI
    "http://localhost:5540"    # Redis Insight UI
)

Write-Host "Opening URLs:" -ForegroundColor Cyan
foreach ($u in $urls) {
    Write-Host "  -> $u"
    try {
        Start-Process $u
    }
    catch {
        $msg = ($_ | Select-Object -ExpandProperty Exception).Message
        Write-Warning ("Failed to open {0}: {1}" -f $u, $msg)
    }
}

if ($Wait) {
    Write-Host "Press Enter to exit..." -ForegroundColor Yellow
    [void][System.Console]::ReadLine()
}
