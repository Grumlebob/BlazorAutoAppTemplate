# Testing

The full test guide lives at:

```text
BlazorAutoApp.Test/TESTING.md
```

Use this quick local gate from the repository root:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
```

Visible browser E2E is headed by default:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
```

## Lighthouse Performance

Lighthouse is pinned in the client npm toolchain and writes generated reports under `TestResults/Lighthouse`.

Run local mobile and desktop reports against the Docker app:

```powershell
.\RunLocal.ps1 -NoBrowser
.\RunLighthouse.ps1 -BaseUrl https://127.0.0.1:7186 -Paths "/", "/books/design-demos", "/Account/Login" -Profile both -IgnoreCertificateErrors
```

Run an authenticated local home-page report with the seeded Docker/Development user:

```powershell
.\RunLighthouse.ps1 -BaseUrl https://127.0.0.1:7186 -Paths "/" -Profile both -IgnoreCertificateErrors -AuthenticatedLocalUser
```

For production, omit `-IgnoreCertificateErrors` and point `-BaseUrl` at the deployed domain.

When testing a local `dotnet run` app on `http://127.0.0.1:5099`, start that app with higher local-only rate limits so headed desktop and mobile runs do not trip the template limiter:

```powershell
$env:RateLimiting__Global__PermitLimit='10000'
$env:RateLimiting__Api__PermitLimit='1000'
$env:RateLimiting__Authentication__PermitLimit='1000'
$env:E2E_BASE_URL='http://127.0.0.1:5099'
```

For a mobile viewport pass, set:

```powershell
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
```
