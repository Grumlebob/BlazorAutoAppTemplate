# Testing

This project has four test layers:

- Feature/integration tests for the vertical slices.
- Architecture tests for repo structure and endpoint behavior.
- Infrastructure/hosting behavior tests.
- Headed Playwright E2E tests for real browser render mode, Books, and Identity flows.

## Normal Test Run

E2E tests are skipped unless `RUN_E2E=1` is set.

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
```

Integration tests use Testcontainers and PostgreSQL, so Docker must be running.

## Cross-Node Cache Invalidation Tests

Books cross-node cache invalidation tests start two in-memory app hosts against one shared PostgreSQL Testcontainer and one shared Redis Testcontainer. These tests verify the production shape where multiple app servers share Redis and need Redis pub/sub to invalidate each other's in-process `HybridCache` entries.

Run them directly with:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "FullyQualifiedName~BooksCrossNodeCacheInvalidationTests"
```

The shared fixture lives under `TestSupport/Integration`. Normal integration tests keep Redis disabled with `Redis:AllowMissing=true` unless the test explicitly opts into shared Redis.

## Vertical Slice Rules

Every Core feature slice should have a matching test slice with a one-to-one naming and namespace mapping.

Layout:

- Core slice: `BlazorAutoApp.Core/Features/{Feature}/{Slice}Request.cs`
- Test slice: `BlazorAutoApp.Test/Features/{Feature}/{Slice}Tests.cs`
- Feature test data: `BlazorAutoApp.Test/Features/{Feature}/TestData/*`
- Test integration support: `BlazorAutoApp.Test/TestSupport/Integration/*`
- Architecture checks: `BlazorAutoApp.Test/Architecture/{Concern}/*`
- Infrastructure checks: `BlazorAutoApp.Test/Infrastructure/{Concern}/*`
- Browser E2E: `BlazorAutoApp.Test/E2E/{Concern}/*`

Conventions:

- Test namespace: `BlazorAutoApp.Test.Features.{Feature}`
- Test class name: `{Slice}Tests`
- Each feature test class must contain at least one `[Fact]` or `[Theory]`.
- HTTP/API integration tests should use `[Collection("IntegrationTestCollection")]` and `WebAppFactory`.

## Architecture Enforcement

- `Architecture/Slices` scans Core for public `*Request` classes under `Features.{Feature}` and asserts matching feature test classes exist.
- `Architecture/Boundaries` verifies project references, DTO placement, HTTP client usage, and infrastructure namespace boundaries.
- `Architecture/Composition` verifies DI wiring.
- `Architecture/Endpoints` verifies current API endpoint behavior without banning future template users from adding new domains.
- `Architecture/Persistence` verifies EF model and entity configuration placement.
- `Architecture/Support` contains shared reflection/source-search helpers for architecture tests.

## Infrastructure Hosting Tests

`BlazorAutoApp.Test/Infrastructure/Hosting/RateLimitingTests.cs` verifies that the Books API returns `429 Too Many Requests` and a `Retry-After` header when the configured API limit is exceeded.

`BlazorAutoApp.Test/Infrastructure/Hosting/ForwardedHeadersTests.cs` verifies that the app does not ship trust-all forwarded headers and that configured proxy/network trust is applied explicitly.

## Headed Browser E2E

Playwright E2E tests are intentionally headed by default. The browser opens visibly so you can watch the flow and diagnose UI issues.

Start or rebuild the app stack:

```powershell
docker compose up -d --build web
```

Confirm the app is reachable:

```powershell
Invoke-WebRequest -Uri https://localhost:7186/health -SkipCertificateCheck
```

Install Chromium once after building the test project:

```powershell
pwsh .\BlazorAutoApp.Test\bin\Debug\net10.0\playwright.ps1 install chromium
```

Run visible E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
$env:E2E_SLOW_MO_MS='450'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
```

For local `dotnet run` verification on `http://127.0.0.1:5099`, start the app with local-only higher rate limits before running headed E2E. This keeps the real rate limiter enabled by default while preventing visible desktop plus mobile browser passes from exhausting the template limits:

```powershell
$env:ASPNETCORE_ENVIRONMENT='Development'
$env:ASPNETCORE_URLS='http://127.0.0.1:5099'
$env:ConnectionStrings__DefaultConnection='Host=localhost;Port=5433;Database=app;Username=postgres;Password=postgres;GSS Encryption Mode=Disable'
$env:Redis__Configuration='localhost:6379'
$env:Redis__AllowMissing='true'
$env:RateLimiting__Global__PermitLimit='10000'
$env:RateLimiting__Api__PermitLimit='1000'
$env:RateLimiting__Authentication__PermitLimit='1000'
dotnet run --project .\BlazorAutoApp\BlazorAutoApp.csproj --urls http://127.0.0.1:5099
```

## E2E Environment Variables

- `RUN_E2E=1`: enables the Playwright tests.
- `E2E_BASE_URL`: target app URL. Defaults to `https://localhost:7186`.
- `E2E_CLEANUP_CONNECTION_STRING`: optional PostgreSQL connection string used only for E2E cleanup fallback. When omitted, cleanup uses `ConnectionStrings__DefaultConnection` or local `.env` PostgreSQL values.
- `E2E_SLOW_MO_MS`: visible delay between browser actions. Defaults to `300`.
- `E2E_VIEWPORT_WIDTH` and `E2E_VIEWPORT_HEIGHT`: browser viewport. Defaults to `1280x900`.
- `E2E_HEADLESS=1`: runs without a visible browser. Use only for CI-style runs.
- `RateLimiting__Global__PermitLimit`, `RateLimiting__Api__PermitLimit`, and `RateLimiting__Authentication__PermitLimit`: app-start variables, not test variables. Raise them only for local headed E2E runs when exercising several browser flows against one app process.

Clear local E2E environment variables when done:

```powershell
Remove-Item Env:\RUN_E2E -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_SLOW_MO_MS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
```

Run the same visible E2E flow at a mobile viewport:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
```

## E2E Coverage

Current E2E tests verify:

- Home render-mode diagnostics hydrate to an interactive renderer.
- Anonymous Books home shows **The Authors Bookcase** and the login CTA while hiding Add Book and the saved-books table.
- Authenticated Books users see **The Authors Bookcase** plus their own bookcase, then can create, view, use explicit Back, use browser Back, edit, cancel, delete with confirmation, and show not found.
- Identity can register, logout, login, open the profile page, open passkeys, and use the local forgot-password flow.
- Visual snapshots are captured for homepage, Books create/details/edit, login/register, account manage, and not-found screens.

E2E layout:

- `E2E/AppShell`: template/app-shell browser checks such as render-mode diagnostics.
- `E2E/Features/Login`: Identity browser flows.
- `E2E/Features/Books`: Books browser flows.
- `E2E/VisualRegression`: screenshot capture tests.
- `E2E/Support`: shared Playwright base classes and guards.

Guidelines:

- Do not depend on seeded database rows; create unique data inside the test.
- Track every E2E-created user/book with the shared cleanup helpers so records are deleted even when a test fails midway.
- Prefer `data-testid` for workflow controls that are hard to select reliably.
- Keep E2E tests behind `RUN_E2E=1`.
- Do not make headless the default local behavior.

## Failure Artifacts

On E2E failure, screenshots are written to:

```text
TestResults/Playwright
```

Failed E2E runs also retain a Playwright trace zip, and browser videos are written under `TestResults/Playwright/Videos`. `TestResults` is generated output and can be deleted.
Normal snapshot runs write page screenshots under `TestResults/Playwright/Snapshots`.

## Deployment Checks

Run these before changing LocalCluster deployment files:

```powershell
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
python -m yamllint .github Deployment/LocalCluster
docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:1.7.7
docker run --rm -v "${PWD}:/mnt" -w /mnt koalaman/shellcheck-alpine:stable sh -c "find Deployment/LocalCluster/Scripts -type f -name '*.sh' -print0 | xargs -0 shellcheck --severity=warning"
```

## Troubleshooting

- Browser does not open: remove `E2E_HEADLESS` from the current shell.
- Playwright says the browser executable is missing: rerun the Chromium install command above.
- App is unreachable: run `docker compose ps` and check `https://localhost:7186/health`.
- Port `7186` is already in use: stop the old app process/container or change `E2E_BASE_URL` to the port you are actually using.
- HTTPS certificate warnings are ignored by the E2E context through `IgnoreHTTPSErrors`.
