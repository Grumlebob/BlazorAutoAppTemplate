# Thorough Review

Status: done.

## Goal

Find and fix real repo smells before this template is used by other people.

This plan is intentionally broader than a single feature cleanup. It reviews the app as a .NET 10 Blazor Web App template with:

- Books as the home feature
- Identity authentication and passkeys
- render-mode diagnostics
- local Docker development
- visible Playwright E2E
- LocalCluster deployment
- PostgreSQL, Redis, HybridCache, and cross-node invalidation

The plan should identify bad smells, stale files, non-standard patterns, fragile tests, slow paths, and confusing template defaults without destroying working deployment behavior.

## Non-Goals

- Do not remove LocalCluster deployment.
- Do not rename or reset real deployment inventory values without an explicit deployment migration step.
- Do not remove Identity or passkey support.
- Do not remove render-mode diagnostics.
- Do not add heavy architecture guardrails that make the template annoying to fork.
- Do not make Playwright headless by default.
- Do not redesign the book covers unless a review phase proves a concrete quality or performance problem.
- Do not squash or rewrite migrations unless the database reset strategy is explicitly approved for the target environment.

## Baseline Evidence To Reconfirm

Status: done.

Current scan signals that should be reviewed before making changes:

- `TemplateCustomization.md` still says client pages live under `Features/{Feature}/Pages`, while the Books feature uses `Features/Books/Routes`.
- `BlazorAutoApp.Client/Routes.razor` imports `Features.AppShell.Pages`.
- `BlazorAutoApp/Components/Pages/Error.razor` exists on the server project as a default app shell page.
- `BlazorAutoApp/Features/Login/Account/Pages` exists for Identity component pages.
- `BlazorAutoApp.Client/Program.cs` manually registers scoped `HttpClient`.
- `BlazorAutoApp.Client/Features/Login/Components/RedirectToLogin.razor` and `BookModalHost.razor` use `forceLoad: true` for login redirects.
- `BlazorAutoApp.Test/E2E/Features/Login/IdentityE2ETests.cs` contains a fixed `Task.Delay(250)`.
- `BlazorAutoApp/Features/Login/Account/Shared/PasskeySubmit.razor` injects `IServiceProvider`.
- LocalCluster inventory still contains instance-specific `ship` values and hostname values.
- `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` contains old comparison names such as `improveddb` and `ship`.
- The root `Plans` directory may still exist as an empty locked folder on Windows.
- No direct `ForceRefresh`, `GetBooksRequest`, browser `confirm()`, Movies, Inspections, TUS, ImageSharp, or upload implementation references were found in current app/test code during the scan, but this must be rechecked during execution.

Baseline commands:

```powershell
git status --short
rg -n "TODO|HACK|workaround|temporary|ForceRefresh|GetBooksRequest|confirm\(|window\.confirm|Thread\.Sleep|Task\.Delay|forceLoad|IServiceProvider|new HttpClient|AddHttpClient|Pages|Movies|movies|Inspections|Tus|TUS|ImageSharp|SixLabors|upload|Upload" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Core BlazorAutoApp.Test Deployment README.md HowToRunLocally.md TESTING.md TemplateCustomization.md -S
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

Execution notes:

- Reconfirmed the repo state before making changes.
- No current app/test implementation references remain for `ForceRefresh`, `GetBooksRequest`, browser `confirm()`, Movies, Inspections, TUS, ImageSharp, SixLabors, or upload flows.
- The root `Plans` directory still exists because Windows reports it as locked by another process; it is empty and now ignored.

## Phase 1: Documentation And Naming Drift

Status: done.

Finding:

Some docs and tests still speak in old generic terms like `Pages`, while the actual Books feature is now using `Routes`. Deployment docs also intentionally still contain `ship` examples and current inventory values, which are valuable if they reflect the user's real deployment but confusing if they are meant to be template defaults.

Tasks:

- Decide the canonical route folder name for client feature slices: `Routes` or `Pages`.
- Update `TemplateCustomization.md`, testing docs, and architecture test messages to match the chosen name.
- Keep Identity server pages under `Features/Login/Account/Pages` if that matches the .NET Identity component template.
- Keep `Components/Pages/Error.razor` only if it is still the cleanest app-shell location; otherwise move it into an app shell feature.
- Review every `ship` deployment reference and classify it as:
  - active user deployment value
  - example value
  - stale template residue
  - audit comparison value
- Do not change real inventory values unless a deployment migration note is written.
- Update docs so template users understand which deployment files are examples and which are instance-specific.

Execution notes:

- Chose `Routes` as the canonical client feature route folder name.
- Moved the AppShell client not-found route from `Features/AppShell/Pages` to `Features/AppShell/Routes`.
- Updated route imports, root docs, local-run docs, and architecture test messages to use `Routes`.
- Left server Identity pages under `Features/Login/Account/Pages`, matching the Identity component-page shape.
- Preserved `Components/Pages/Error.razor` as the server app-shell framework error page.
- Kept active LocalCluster deployment values intact and documented that `Deployment/LocalCluster/inventory/prod/*` is active instance configuration.

Acceptance:

- Docs and tests use one vocabulary for client route components.
- Deployment naming is clear and no valuable `ship` deployment configuration is accidentally removed.
- Root docs do not point at archived implementation plans as current guidance.

Verification:

```powershell
rg -n "Features/\{Feature\}/Pages|BlazorAutoApp.Client/Pages|Movies|Inspections|Tus|TUS|ImageSharp|SixLabors" README.md HowToRunLocally.md TESTING.md TemplateCustomization.md BlazorAutoApp.Test Deployment -S
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~FeatureSlicesArchitectureTests"
```

## Phase 2: Vertical Slice Boundaries

Status: done.

Finding:

Books are mostly sliced well, but the repo has several shared areas that should be intentionally reviewed:

- `BlazorAutoApp.Client/Features/Books/Shared` contains reusable book rendering primitives and cover catalog data.
- `BlazorAutoApp/Infrastructure/Hosting` contains broad hosting, caching, forwarding, observability, and rate limiting.
- Identity has both server-side components and a small client redirect component.
- Server `Components` still hosts app shell pieces.

Tasks:

- Review whether Books `Shared` should be split into `Bookcase`, `BookCover`, and `BookPage` subfolders or left as-is.
- Review whether `BookCoverDesignCatalog.cs` has grown too large and should be split by design family. Actually it is fine large
- Review whether app shell server components should move under `Features/AppShell` for consistency.
- Keep infrastructure cross-cutting pieces in `Infrastructure` only when they are truly cross-cutting.
- Confirm no feature-specific logic is hiding in infrastructure or app shell.
- Confirm no infrastructure dependency leaks into Core.
- Confirm Client, Core, Server, and Test project structure remains understandable for a new fork.

Execution notes:

- Reviewed Books client subslices and kept the existing `AuthorBookcase`, `UserBookcase`, `BookModal`, `BookPage`, `DesignDemos`, `Routes`, and `Shared` split.
- Honored the user note that `BookCoverDesignCatalog.cs` is acceptable as a large catalog file.
- Added architecture coverage so client feature route folders are named `Routes`, not `Pages`.
- No cross-project dependency leaks were found by architecture tests.

Acceptance:

- Feature slices are easy to navigate.
- Shared folders contain genuinely shared concepts, not mixed leftovers.
- No slicing change is made purely for aesthetics if it increases friction.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~Architecture|FullyQualifiedName~Boundaries|FullyQualifiedName~Slices"
```

## Phase 3: Books UI And Rendering Performance

Status: skipped.

Execution notes:

- User marked this phase skipped before execution.
- No book-cover redesign, animation, or rendering behavior changes were made.

## Phase 4: Books State, CRUD, And Cache Freshness

Status: done.

Finding:

Books now use user-owned integer IDs, HybridCache, Redis pub/sub invalidation, and client-side state updates. This area is high value because old disappearing-book bugs came from state/cache mismatch.

Tasks:

- Review every create/update/delete path from UI to API to database to cache invalidation to UI state.
- Confirm no hidden cache bypass or force-refresh concept remains.
- Confirm local state updates and server cache invalidation cannot diverge after failed saves/deletes.
- Confirm delete and save cannot double-submit or leave stale busy states.
- Confirm cross-node invalidation uses the same Redis connection as cache and Data Protection.
- Confirm missed Redis pub/sub messages are bounded by local cache TTL.
- Confirm cache keys cannot collide between users, environments, or apps.
- Confirm seeded local users and registered users resolve ownership consistently.

Execution notes:

- Verified Books cache, Redis invalidation, API, ownership, and E2E flows.
- No force-refresh workaround or stale `GetBooksRequest` path remains.
- CRUD survived visible desktop and mobile E2E refresh/navigation paths.

Acceptance:

- CRUD survives refresh/navigation/login/logout.
- Cross-node cache freshness behavior is explicit and tested.
- No code path relies on a UI workaround to mask stale cache.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BooksCachingTests|FullyQualifiedName~BooksCrossNodeCacheInvalidationTests|FullyQualifiedName~RedisConnectionReuseTests|FullyQualifiedName~BooksE2ETests"
```

## Phase 5: Identity And Authentication Modernity

Status: done.

Finding:

Identity component pages and passkeys are valuable for a .NET 10 template, but generated Identity code can look unlike the rest of the app. Some patterns, such as `IServiceProvider` in `PasskeySubmit.razor` and `forceLoad` login redirects, may be official-template patterns, but they should be explicitly confirmed.

Tasks:

- Compare the Identity component setup against the current .NET 10 template behavior.
- Confirm passkey endpoints and antiforgery validation follow current ASP.NET Core guidance.
- Decide whether `PasskeySubmit.razor` should keep `IServiceProvider` because it matches framework/component constraints or be refactored to explicit dependencies.
- Review `CurrentUserAccessor` fallback to `AuthenticationStateProvider` and prove whether Interactive Auto still requires it.
- Confirm logout, register, login, seeded users, passkeys, and profile navigation work.
- Review account pages for stale styling or layout conflicts with the rest of the template.

Execution notes:

- Compared against a fresh .NET 10 Blazor Individual Auth template locally.
- Confirmed the official template still uses service-provider lookup in `PasskeySubmit.razor`, then refactored this app to explicit `IAntiforgery` injection because antiforgery is always registered here.
- Verified Identity/Login tests and visible login/register/logout/profile E2E.

Acceptance:

- Identity remains modern and functional.
- Any non-standard dependency resolution has a documented reason or is removed.
- Login-related files remain under Login feature slices.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~Identity|FullyQualifiedName~Login|FullyQualifiedName~Books"
```

## Phase 6: API, Validation, Problem Details, And OpenAPI Shape

Status: done.

Finding:

The Books endpoints use `TypedResults`, `ProblemDetails`, and built-in validation. This should be kept modern, but endpoint metadata and validation behavior should be reviewed end to end.

Tasks:

- Confirm every API endpoint returns typed results consistently.
- Confirm validation failures return `HttpValidationProblemDetails`.
- Confirm not-found and id-mismatch responses use consistent `ProblemDetails`.
- Review whether endpoint route names, response metadata, and OpenAPI metadata should be added for template clarity.
- Confirm request DTOs are meaningful and no empty DTO remains.
- Confirm `BookUrlValidation` handles null, whitespace, invalid schemes, and long URLs consistently.
- Confirm API tests cover anonymous access, cross-user access, invalid payloads, and ownership boundaries.

Execution notes:

- Confirmed Books endpoints already use typed result patterns and named routes.
- Strengthened endpoint surface tests to assert endpoint names as well as route/method shape.
- API and endpoint tests pass.

Acceptance:

- API behavior is modern .NET 10 Minimal API style.
- DTOs are meaningful and not fake architecture artifacts.
- Error responses are predictable for template users.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.Features.Books.Api|FullyQualifiedName~EndpointSurfaceTests"
```

## Phase 7: Tests And E2E Quality

Status: done.

Finding:

The test project is structured well, but a fixed `Task.Delay(250)` remains in login E2E. Visible Playwright is preferred for manual confidence, while CI skips E2E unless explicitly enabled.

Tasks:

- Replace fixed E2E delays with locator/state-based waits where practical.
- Confirm E2E test-created objects are always cleaned up, including failure paths.
- Review whether skipped E2E output is obvious enough in CI.
- Confirm mobile and desktop visible E2E commands are documented and still work.
- Confirm visual snapshot tests write useful artifacts and do not pollute git.
- Review whether test fixture startup is slower than necessary after the Redis/Testcontainers additions.
- Review test names and folders after the latest Books refactors.

Execution notes:

- Replaced the remaining fixed `Task.Delay(250)` in login E2E with a next-animation-frame wait.
- Confirmed E2E-created Books are cleaned up by existing E2E cleanup paths.
- Visible desktop and mobile E2E passed against the local Docker app.

Acceptance:

- No test relies on arbitrary sleep when a deterministic wait is possible.
- E2E remains visible by default when manually enabled.
- CI test output is predictable and not misleading.

Verification:

```powershell
dotnet test .\BlazorAutoApp.sln -c Release --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~E2E"
```

## Phase 8: Local Development Experience

Status: done.

Finding:

Local Docker and Rider run scripts exist and are valuable, but port conflicts, Docker Desktop readiness, certificates, and existing containers should be reviewed for a smooth template experience.

Tasks:

- Run `RunLocal.cmd` and `RunLocal.ps1` from a normal Windows shell.
- Confirm behavior when Docker Desktop is not running.
- Confirm behavior when ports 7186, 5025, 5433, 6379, 8081, 5341, or 5540 are occupied.
- Confirm local status warnings are actionable and not false failures.
- Confirm `.env.example` and `.env` generation stay in sync.
- Confirm generated dev certificates are reusable and documented.
- Confirm local seed accounts and seeded books are Development/Docker-only.
- Confirm no upload/media storage is implied by `data/storage`.

Execution notes:

- Added `RunLocal.ps1 -StatusOnly` for quick Rider/local diagnostics without starting containers.
- Changed the extra local `127.0.0.1:5099` dotnet listener from a hard failure to an actionable warning because Docker uses the configured app port.
- Verified local status and Docker health.
- Clarified that `data/storage` is runtime storage such as Data Protection keys, not upload/media storage.

Acceptance:

- A Rider user can click one script and get a working local stack.
- Port and Docker failures produce clear messages.
- Local scripts do not accidentally touch deployment state.

Verification:

```powershell
.\RunLocal.cmd
.\RunLocal.ps1 -StatusOnly
docker compose ps
Invoke-WebRequest -Uri https://127.0.0.1:7186/health/ready -SkipCertificateCheck
```

## Phase 9: Deployment Safety And Template Defaults

Status: skipped.

Execution notes:

- User marked this phase skipped before execution.
- No deployment inventory values, Ansible roles, scripts, hostnames, ports, or LocalCluster behavior were changed.


## Phase 10: Dependency And Toolchain Review

Status: done.

Finding:

Central package management is in use and the project targets .NET 10. Dependency versions should be reviewed against current stable package families without blindly updating.

Current notable versions:

- .NET SDK pinned to `10.0.300` with `rollForward: latestFeature`
- ASP.NET Core and EF packages at `10.0.8`
- HybridCache package at `10.6.0`
- Npgsql EF provider at `10.0.1`
- Playwright at `1.60.0`
- Testcontainers at `4.12.0`
- StackExchange.Redis at `2.13.1`
- Tailwind CSS v4 through npm

Tasks:

- Run `dotnet list package --outdated` and review each update.
- Run `npm --prefix BlazorAutoApp.Client outdated`.
- Confirm package version families are compatible with .NET 10.
- Avoid updating deployment-critical packages without targeted tests.
- Confirm no unused packages remain after removing uploads/images/movies/inspections.
- Confirm no ImageSharp, TUS, upload, or stale media dependencies exist.
- Review Docker base image tags and pinning strategy.

Execution notes:

- Updated only `Microsoft.NET.Test.Sdk` from `18.5.1` to `18.6.0`.
- `dotnet list package --outdated` now reports no package updates.
- `npm --prefix .\BlazorAutoApp.Client outdated` reports no npm updates.
- No upload/image/movie dependencies were found.

Acceptance:

- Dependencies are modern and deliberate.
- No obsolete upload/image/movie dependency remains.
- Updates are tested, not bulk-applied blindly.

Verification:

```powershell
dotnet list .\BlazorAutoApp.sln package --outdated
npm --prefix .\BlazorAutoApp.Client outdated
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
```

## Phase 11: Security, Privacy, And Secrets Hygiene

Status: done.

Finding:

The template includes Identity, local seeded users, deployment vault files, Cloudflare tunnel setup, Data Protection keys, Redis, and PostgreSQL. This deserves a focused hygiene pass.

Tasks:

- Verify local seeded accounts are disabled outside Development/Docker.
- Verify `.env`, data folders, certificates, and generated artifacts are ignored correctly.
- Review tracked deployment vault files and ensure no secret material is exposed.
- Confirm `vault.example.yml` is safe and complete enough for template users.
- Confirm antiforgery is active for Identity endpoints that need it.
- Confirm forwarded headers are not trust-all by default in production.
- Confirm rate limiting defaults are sane for API and authentication endpoints.
- Confirm secure cookie/Data Protection behavior in local Docker and deployment.

Acceptance:

- No accidental secret/template leak.
- Local convenience accounts cannot appear in production.
- Security defaults are explicit and tested.

Verification:

```powershell
rg -n "password|secret|token|apikey|api_key|cloudflare|vault|Admin123|User123" . --glob '!bin/**' --glob '!obj/**' --glob '!artifacts/**' --glob '!TestResults/**' -S
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~ForwardedHeadersTests|FullyQualifiedName~RateLimitingTests|FullyQualifiedName~Identity"
```

Review results manually before changing anything.

Execution notes:

- Reviewed secret-related search output manually.
- Local seeded passwords remain only in Development/Docker configuration and seeding code is environment-gated.
- Encrypted Ansible vault remains encrypted; no plaintext vault material was exposed by the scan.
- Forwarded headers, rate limiting, and Identity tests pass.

## Phase 12: Artifact And Repository Cleanliness

Status: done.

Finding:

Historical plans have been archived, but the repo still needs a general artifact pass. The empty `Plans` folder may remain on Windows if a process holds it open.

Tasks:

- Remove the empty root `Plans` folder once no process holds the handle.
- Confirm `docs/plans/archive` is intentionally retained or move it out of the template if history is not wanted by fork users.
- Review `artifacts`, `TestResults`, `.vs`, `.idea`, `data`, and generated certificate folders for tracked files.
- Confirm `.gitignore` covers all generated outputs.
- Confirm root docs are current and concise.
- Confirm no stale plan file remains in the root besides active plans.

Execution notes:

- Moved stale root `FixSmells.md` to `docs/plans/archive/FixSmells.md`.
- Moved old active-looking `docs/plans/Strategy.md` and `docs/plans/TheBigFixUpBeforePeopleUseIt.md` into `docs/plans/archive`.
- Added `/Plans/` to `.gitignore`; the existing empty `Plans` directory is still locked by another process and could not be removed during this run.
- `git status` no longer shows generated local artifact folders.

Acceptance:

- Repo root is clean for template consumers.
- Generated artifacts do not show up in normal `git status`.
- Historical plans are clearly archival or removed.

Verification:

```powershell
git status --short
Get-ChildItem -Force
Get-ChildItem -Directory -Recurse | Where-Object { $_.FullName -notmatch '\\(bin|obj|\.git|\.vs|artifacts|TestResults)(\\|$)' -and -not (Get-ChildItem -LiteralPath $_.FullName -Force) } | Select-Object FullName
```

## Phase 13: Final Verification Gate

Status: done.

Run after all accepted fixes:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
docker compose up -d --build web
Invoke-WebRequest -Uri https://127.0.0.1:7186/health/ready -SkipCertificateCheck
```

Run visible desktop E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~E2E"
```

Run visible mobile Books E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.E2E.Features.Books.BooksE2ETests"
```

Manual smoke checks:

- Anonymous home page loads Books.
- Render-mode badge shows assigned and hydrated mode.
- Author book opens view modal.
- User login works with local seeded user in Development/Docker.
- Add, view, edit, delete, refresh, logout, and login preserve expected Books state.
- Design demos open if still public.
- Logout does not produce HTTP 400.
- Local Docker stack health checks pass.

Execution notes:

- `dotnet restore`, Release build, full non-E2E test suite, formatting verification, Tailwind generation verification, CSS diff gate, and whitespace diff check passed.
- Docker web image rebuilt, then Docker returned a late engine pipe/deadline warning after export. Recreating the web container from the produced image succeeded.
- Local Docker health check passed at `https://127.0.0.1:7186/health/ready`.
- Visible desktop E2E passed: 5/5.
- Visible mobile Books E2E passed: 2/2.

## Recommended Execution Order

Status: done.

1. Baseline evidence.
2. Documentation and naming drift.
3. Artifact and repository cleanliness.
4. Books state/cache review.
5. Books UI/render performance review.
6. Identity/authentication review.
7. API/validation review.
8. Tests/E2E review.
9. Local development review.
10. Deployment review.
11. Dependency/toolchain review.
12. Security/secrets hygiene review.
13. Final verification gate.

## Done Criteria

Status: done.

- Current docs match the actual app structure.
- No stale Movies, Inspections, upload, TUS, or ImageSharp implementation remains.
- Feature slices are easy to navigate and not over-abstracted.
- Books CRUD/cache/UI flows are tested and free of force-refresh style workarounds.
- Identity remains modern and verified.
- Deployment remains preserved and clearly separated from template examples.
- Local run scripts are smooth for Rider/Windows users.
- Test suite uses deterministic waits where practical.
- Full build/test/format/CSS/Docker/visible-E2E verification passes.
