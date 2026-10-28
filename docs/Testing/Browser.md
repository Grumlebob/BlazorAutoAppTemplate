# Browser and performance tests

Browser checks are separate from the ordinary test run. Blazor Playwright E2E is opt-in and headed by default. React public browser suites use a dedicated runner and only read public data.

## Blazor Playwright E2E

For the Docker app, start the stack without opening a second browser. Clear `RUN_E2E` after the run so later test commands do not start browsers unexpectedly.

```powershell
.\Scripts\RunLocal.ps1 -NoBrowser
dotnet build .\GrumPlates.Test\GrumPlates.Test.csproj
pwsh .\GrumPlates.Test\bin\Debug\net10.0\playwright.ps1 install chromium
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
dotnet test .\GrumPlates.Test\GrumPlates.Test.csproj --filter "Category=E2E"
Remove-Item Env:\RUN_E2E,Env:\E2E_BASE_URL -ErrorAction SilentlyContinue
```

The browser is visible by default. Set `E2E_HEADLESS=1` only for a CI-style run. `E2E_BASE_URL` defaults to `https://localhost:7186`. For a direct .NET run, use its URL and follow [the local service setup](../HowToRunLocally.md#run-without-docker).

Important settings: `E2E_SLOW_MO_MS` controls visible delay; `E2E_NAVIGATION_TIMEOUT_MS` and `E2E_ACTION_TIMEOUT_MS` set timeouts; `E2E_VIEWPORT_WIDTH` and `E2E_VIEWPORT_HEIGHT` set the viewport. `E2E_CLEANUP_CONNECTION_STRING` is an optional PostgreSQL connection for cleanup; without it, cleanup uses the app connection or local Docker values. For a direct run with several visible desktop and mobile flows, raise `RateLimiting__Global__PermitLimit` to `10000`, `RateLimiting__Api__PermitLimit` to `1000`, and `RateLimiting__Authentication__PermitLimit` to `1000` for that app process only.

Current examples: [Books flows](../../GrumPlates.Test/E2E/Features/Books/BooksE2ETests.cs), [Identity flows](../../GrumPlates.Test/E2E/Features/Login/IdentityE2ETests.cs), and [pre-hydration controls](../../GrumPlates.Test/E2E/AppShell/PreHydrationControlsE2ETests.cs). Test files are the coverage inventory. Use shared cleanup for created users and data; tests must clean up after failures. Failure screenshots and traces are under `TestResults/Playwright`; videos are under `TestResults/Playwright/Videos`. Paths are defined in [E2EArtifactPaths](../../GrumPlates.Test/E2E/Support/E2EArtifactPaths.cs). `TestResults` is generated output and can be deleted.

## React public browser checks

The broad Chromium suite is run by CI. Firefox and WebKit smoke checks are useful before release:

```powershell
pwsh .\Scripts\Testing\RunReactPublicE2E.ps1 -Browser chromium -Suite broad -Configuration Release
pwsh .\Scripts\Testing\RunReactPublicE2E.ps1 -Browser firefox -Suite smoke -Configuration Release -ReuseFrontendBuild
pwsh .\Scripts\Testing\RunReactPublicE2E.ps1 -Browser webkit -Suite smoke -Configuration Release -ReuseFrontendBuild
```

The React runner builds a React-profile host and its own disposable services. The public browser checks do not create accounts or send writes. Each suite validates its expected discovery and result count. Install the matching Playwright browsers if the runner reports a missing binary. React package unit checks are in [Frontend/React](../Frontend/React.md).

## Lighthouse Performance

The client npm lockfile pins Lighthouse. Reports are generated under `TestResults/Lighthouse`. Start the Docker app, then run:

```powershell
.\Scripts\RunLocal.ps1 -NoBrowser
.\Scripts\RunLighthouse.ps1 -BaseUrl https://127.0.0.1:7186 -Paths "/", "/books" -Profile both -IgnoreCertificateErrors
```

For production, omit `-IgnoreCertificateErrors` and set `-BaseUrl` to the deployed origin. A fixture proxy can be passed with `-BrowserProxy`; it must be a loopback proxy and enforce the public-route allowlist. See `Scripts/RunLighthouse.ps1` for current options.

Add `-Minimum "performance=90,accessibility=100,best-practices=100,seo=100"` to fail the run when a median score is below a minimum, or summarize earlier runs with `Scripts/Quality/summarize_lighthouse.py` ([details](../Quality/QualityTools.md#summarize-lighthouse-runs)).
