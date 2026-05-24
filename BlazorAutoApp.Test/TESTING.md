# Testing

This project has four test layers:

- Feature/integration tests for the vertical slices.
- Architecture tests for repo structure and endpoint behavior.
- Rate-limiting behavior tests.
- Headed Playwright E2E tests for real browser render mode, Movies, and Identity flows.

## Normal Test Run

E2E tests are skipped unless `RUN_E2E=1` is set.

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
```

Integration tests use Testcontainers and PostgreSQL, so Docker must be running.

## Vertical Slice Rules

Every Core feature slice should have a matching test slice with a one-to-one naming and namespace mapping.

Layout:

- Core slice: `BlazorAutoApp.Core/Features/{Feature}/{Slice}Request.cs`
- Test slice: `BlazorAutoApp.Test/Features/{Feature}/{Slice}Tests.cs`
- Test infra: `BlazorAutoApp.Test/TestingSetup/*`
- Architecture checks: `BlazorAutoApp.Test/Architecture/*`
- Browser E2E: `BlazorAutoApp.Test/E2E/*`

Conventions:

- Test namespace: `BlazorAutoApp.Test.Features.{Feature}`
- Test class name: `{Slice}Tests`
- Each feature test class must contain at least one `[Fact]` or `[Theory]`.
- HTTP/API integration tests should use `[Collection("IntegrationTestCollection")]` and `WebAppFactory`.

## Architecture Enforcement

- `FeatureSlicesArchitectureTests` scans Core for public `*Request` classes under `Features.{Feature}` and asserts matching test classes exist.
- `ArchitectureTests` enforces that each Core `*Api` interface has both client and server implementations under feature namespaces.
- Endpoint tests verify current API behavior without banning future template users from adding new domains.

## Rate Limiting

`BlazorAutoApp.Test/Security/RateLimitingTests.cs` verifies that the Movies API returns `429 Too Many Requests` and a `Retry-After` header when the configured API limit is exceeded.

The test sends a unique `X-Forwarded-For` value so it does not consume the same limiter partition as other integration tests.

## Scaffolding Helper

From repo root:

```powershell
pwsh -File .\BlazorAutoApp.Test\tools\NewFeatureTests.ps1 -Feature Movies
```

The scaffolder scans `BlazorAutoApp.Core/Features/{Feature}` for `*Request` classes and creates missing stub test files under `BlazorAutoApp.Test/Features/{Feature}`.

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

## E2E Environment Variables

- `RUN_E2E=1`: enables the Playwright tests.
- `E2E_BASE_URL`: target app URL. Defaults to `https://localhost:7186`.
- `E2E_SLOW_MO_MS`: visible delay between browser actions. Defaults to `300`.
- `E2E_HEADLESS=1`: runs without a visible browser. Use only for CI-style runs.

Clear local E2E environment variables when done:

```powershell
Remove-Item Env:\RUN_E2E -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_SLOW_MO_MS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
```

## E2E Coverage

Current E2E tests verify:

- Home render-mode diagnostics hydrate to an interactive renderer.
- Movies can create, view, navigate back, open edit, and cancel.
- Identity can register, logout, login, and open the profile page.

Guidelines:

- Do not depend on seeded database rows; create unique data inside the test.
- Prefer `data-testid` for workflow controls that are hard to select reliably.
- Keep E2E tests behind `RUN_E2E=1`.
- Do not make headless the default local behavior.

## Failure Artifacts

On E2E failure, screenshots are written to:

```text
TestResults/Playwright
```

Successful E2E runs do not create screenshots. `TestResults` is generated output and can be deleted.

## Troubleshooting

- Browser does not open: remove `E2E_HEADLESS` from the current shell.
- Playwright says the browser executable is missing: rerun the Chromium install command above.
- App is unreachable: run `docker compose ps` and check `https://localhost:7186/health`.
- Port `7186` is already in use: stop the old app process/container or change `E2E_BASE_URL` to the port you are actually using.
- HTTPS certificate warnings are ignored by the E2E context through `IgnoreHTTPSErrors`.
