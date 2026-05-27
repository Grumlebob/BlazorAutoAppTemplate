# Modern .NET 10 Review

Status: review created on 2026-05-25; executable modernization phases completed on 2026-05-25.

This document is a review and execution plan only. It records modernization findings for the current repository and must not be treated as permission to change application code, deployment scripts, generated assets, or test behavior until execution is explicitly requested.

## Non-Destructive Rules

- Do not remove features, docs, deployment files, migrations, generated CSS, vault files, or tests during review.
- Do not rewrite formatting, line endings, generated assets, Dockerfiles, package versions, or project files during review.
- Execution must happen in small phases with verification after each phase.
- Preserve the template purpose: this repo should stay easy to fork and customize.
- Avoid fork-hostile architecture tests that ban future domains or product choices.

## Evidence Snapshot

Commands run during this review:

- `dotnet --info`
  - SDK: `10.0.300`
  - Host runtime: `10.0.8`
  - `global.json`: `10.0.300`, `rollForward: latestFeature`, `allowPrerelease: false`
- `dotnet list .\BlazorAutoApp.sln package --vulnerable --include-transitive`
  - No vulnerable packages found.
- `dotnet list .\BlazorAutoApp.sln package --deprecated`
  - No deprecated packages found.
- `dotnet list .\BlazorAutoApp.sln package --outdated --include-transitive`
  - No direct top-level outdated packages found after the Redis client update.
  - Remaining outdated packages are transitive, mainly Roslyn/MSBuild/design-time tooling, `System.Composition`, `Newtonsoft.Json`, `System.IO.Hashing`, and Microsoft Testing Platform internals.
- `npm outdated --json`
  - No outdated npm dependencies.
- `npm audit --json`
  - No npm vulnerabilities.
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal`
  - Failed. Main issue is line-ending and formatting drift; many `.cs`, `.razor`, `.json`, `.yml`, and project files use CRLF despite `.editorconfig` requesting LF.
- `dotnet build .\BlazorAutoApp.sln --configuration Release --no-restore`
  - Passed with 0 warnings and 0 errors when run by itself.
- `dotnet test .\BlazorAutoApp.sln --configuration Release --no-build`
  - Passed: 53 passed, 4 skipped E2E.
- `git status --short`
  - Clean before this plan file was added.

Official references used:

- ASP.NET Core Blazor render modes: https://learn.microsoft.com/en-us/aspnet/core/blazor/components/render-modes?view=aspnetcore-10.0
- ASP.NET Core .NET 10 release notes, including Minimal API validation: https://learn.microsoft.com/en-us/aspnet/core/whats-new
- Minimal API responses and `TypedResults`: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis/responses?view=aspnetcore-10.0
- HybridCache: https://learn.microsoft.com/en-us/aspnet/core/performance/caching/hybrid?view=aspnetcore-10.0
- EF Core 10 what's new: https://learn.microsoft.com/en-us/ef/core/what-is-new/ef-core-10.0/whatsnew
- `global.json`: https://learn.microsoft.com/en-us/dotnet/core/tools/global-json
- NuGet package auditing: https://learn.microsoft.com/en-us/nuget/concepts/auditing-packages
- .NET container images: https://learn.microsoft.com/en-us/dotnet/core/docker/container-images
- .NET 10 default container image distro change: https://learn.microsoft.com/en-us/dotnet/core/compatibility/containers/10.0/default-images-use-ubuntu
- .NET container non-root user guidance: https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-8/containers
- Forwarded Headers hardening: https://learn.microsoft.com/en-us/aspnet/core/breaking-changes/8/forwarded-headers-unknown-proxies?view=aspnetcore-10.0

## Executive Summary

The repo is already broadly modern:

- It targets `net10.0` everywhere through `Directory.Build.props`.
- It uses central package management.
- It uses Blazor Web App with Interactive Auto support.
- It uses `MapStaticAssets`, `ResourcePreloader`, `ImportMap`, `Assets[...]`, and render-mode diagnostics.
- It uses .NET 10 component Identity patterns, including passkeys and Identity schema version 3.
- It uses EF Core 10 and Npgsql 10.
- It uses `HybridCache` with Redis and explicit local-cache fallback behavior.
- It has headed Playwright E2E, Testcontainers, architecture tests, deployment validation, Dependabot, and LocalCluster deployment.

The main modernization gaps are not old frameworks. They are template polish and .NET 10 idiom gaps:

1. Replace custom Minimal API validation with built-in .NET 10 Minimal API validation.
2. Move API responses toward `TypedResults`, `ProblemDetails`, and optionally OpenAPI metadata.
3. Fix repo-wide line ending/format drift and add a non-invasive formatting verification gate.
4. Make container runtime more modern: non-root app user, modern port variables, and explicit .NET image tags/digests.
5. Consider package lock files and explicit audit checks for reproducibility.
6. Improve EF/Npgsql production resilience with retry strategy review.
7. Reduce test-host process environment coupling where possible.
8. Clean release-facing docs by archiving old mega-plan documents before users fork the template.

## Phase 1: Formatting And Repo Hygiene

Status: done.

Priority: high.

Findings:

- `.editorconfig` says `end_of_line = lf`, but many C#, Razor, JSON, YAML, and project files currently contain CRLF.
- `dotnet format --verify-no-changes` fails.
- `.gitattributes` currently forces LF for shell/YAML/Python/templates, but not for `.cs`, `.razor`, `.json`, `.csproj`, `.props`, `.targets`, or `.md`.
- Formatting drift is not a functional bug, but it is bad template hygiene and creates noisy diffs.

Plan:

1. Add or review `.gitattributes` entries for:
   - `*.cs text eol=lf`
   - `*.razor text eol=lf`
   - `*.csproj text eol=lf`
   - `*.props text eol=lf`
   - `*.targets text eol=lf`
   - `*.json text eol=lf`
   - `*.md text eol=lf` only if the repo wants Markdown normalized too.
2. Run `dotnet format` once deliberately, not mixed with behavioral changes.
3. Review the diff as a pure formatting diff.
4. Add CI verification only after the one-time normalization lands.

Done when:

- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore` passes.
- `git diff --check` passes without formatting errors.
- Tracked text-like files were normalized to LF according to `.gitattributes`.
- CI now has a verify-only formatting gate after restore and before build.
- The formatting changes are line-ending/whitespace-only outside the targeted Minimal API and CI edits.

## Phase 2: .NET 10 Minimal API Modernization

Status: done.

Priority: high.

Findings:

- `BlazorAutoApp/Features/Books/Validation/DataAnnotationsValidateFilter.cs` is a custom validation filter.
- ASP.NET Core 10 has built-in Minimal API validation via `AddValidation`.
- The Books endpoints currently use `Results.Ok`, `Results.Created`, `Results.NoContent`, and `Results.Problem` instead of `TypedResults`.
- There is no central `AddProblemDetails`/`IProblemDetailsService` customization.
- There is no OpenAPI output for the API surface. That is optional for a UI-first template, but modern Minimal API templates often expose it in Development.

Plan:

1. Add `Microsoft.Extensions.Validation` only if required by the current ASP.NET Core 10 package graph.
2. Register `builder.Services.AddValidation()`.
3. Remove the custom Books `DataAnnotationsValidateFilter<T>` if built-in validation covers the same request DTOs.
4. Convert Books endpoints to `TypedResults` where the return shape is stable:
   - list: `TypedResults.Ok`
   - get by id: typed `Ok` or `Problem`/`NotFound`
   - create: `TypedResults.Created`
   - update/delete: `TypedResults.NoContent`
5. Add `AddProblemDetails` if the API wants consistent validation and domain errors.
6. Consider Development-only `AddOpenApi`/`MapOpenApi` if the template should expose a discoverable API contract.
7. Update API tests to assert the exact validation/problem response shape.

Risks:

- Built-in validation must be tested carefully because request DTOs live in `BlazorAutoApp.Core`.
- If generated validation does not discover referenced assembly DTOs automatically, keep the custom filter until the generator configuration is verified.

Done when:

- `builder.Services.AddValidation()` is registered and the custom Books validation filter was removed.
- `builder.Services.AddProblemDetails()` is registered so Minimal API validation can use the platform problem details service.
- Books endpoints use `TypedResults`, explicit result unions, endpoint names, tags, and problem/validation response metadata.
- Create/update validation tests still pass.
- API response tests cover 400 validation, 400 domain mismatch, 404 problem responses, 201 create, and 204 update/delete.
- No custom validation code remains.

## Phase 3: Blazor Web App And Render Mode Review

Status: done.

Priority: medium.

Findings:

- Current setup is modern:
  - `AddRazorComponents`
  - `AddInteractiveServerComponents`
  - `AddInteractiveWebAssemblyComponents`
  - `AddAuthenticationStateSerialization`
  - `MapStaticAssets`
  - `AddInteractiveServerRenderMode`
  - `AddInteractiveWebAssemblyRenderMode`
  - `HeadOutlet` and `Routes` use Interactive Auto through `PageRenderMode`.
- `RenderModeBadge` uses `RendererInfo` and `AssignedRenderMode`, which is the current .NET 10 way to expose runtime render-mode diagnostics.
- The client project is sliced under `Features`, and no root `BlazorAutoApp.Client/Pages` folder exists.

Plan:

1. Keep the current Interactive Auto app-level render mode.
2. Keep render-mode diagnostics on the Books-first home page because this is a Blazor template.
3. Review whether any Identity/static SSR page accidentally depends on hydrated interactivity.
4. Keep headed Playwright render-mode tests as the acceptance gate.
5. Avoid moving server Identity pages into the client project unless adopting global client-side interactivity for all routes, which this app does not need.

Done when:

- Render-mode E2E verifies assigned mode, prerender/static phase, and hydrated renderer.
- Books pages continue working after browser Back and explicit Back navigation.
- Identity static SSR flows still work.

Execution notes:

- Kept the current Interactive Auto app-level render mode.
- Kept Books as the homepage and kept render-mode diagnostics visible there.
- Kept Identity under the server-side Login slice because those account pages are static SSR/server concerns.
- Existing headed E2E coverage remains the acceptance gate for render mode, Books navigation, and Identity.

## Phase 4: EF Core 10 And Persistence Modernization

Status: done.

Priority: medium.

Findings:

- EF Core 10 and Npgsql 10 are current.
- Migrations are in the server infrastructure slice and startup migrations are disabled in production deployment.
- `AddDbContextFactory<AppDbContext>` is appropriate for Blazor/server component usage.
- The app does not configure an Npgsql retry strategy.
- Mutations currently load tracked entities and call `SaveChangesAsync`. This is simple and correct for a template, but EF has modern bulk APIs for some cases.

Plan:

1. Review adding Npgsql retry behavior, such as `EnableRetryOnFailure`, for production transient network issues.
2. Keep tracked entity updates for clarity unless performance pressure appears.
3. Consider `ExecuteUpdateAsync`/`ExecuteDeleteAsync` only for obvious single-row operations where it simplifies code without harming domain clarity.
4. Keep migration bundle deployment as the production path.
5. Add a small test or deployment check that startup migrations remain disabled in LocalCluster app servers.

Done when:

- Persistence setup remains understandable to template users.
- Production has a documented transient-failure strategy.
- Migration behavior remains explicit and test-covered.

Execution notes:

- Added Npgsql `EnableRetryOnFailure()` to the EF Core context configuration.
- Kept simple tracked mutations instead of changing to bulk APIs; that is clearer for this template.
- Kept migration bundle deployment as the production migration path.
- Added architecture coverage that LocalCluster app servers keep `Database__RunMigrationsAtStartup: "false"`.
- The side mission regenerated the fresh baseline migration and tested it against PostgreSQL.

## Phase 5: Caching And Cross-Node Runtime Review

Status: done.

Priority: medium.

Findings:

- `HybridCache` plus Redis is the modern .NET caching choice.
- The app now has Redis pub/sub invalidation and short local `HybridCache` TTL fallback.
- Redis fail-fast behavior outside development/test is now appropriate for multi-node correctness.
- Redis pub/sub is still at-most-once by design.

Plan:

1. Keep the current `HybridCache` abstraction and Books-owned keys/tags.
2. Add metrics or structured logs around:
   - invalidation publish failures
   - subscriber reconnects
   - invalidation apply failures
3. Document when template users should choose:
   - default local cache + pub/sub
   - `Cache__Books__DisableLocalCache=true`
   - durable invalidation with Redis Streams or a database outbox
4. Consider a later durable invalidation plan only if the template grows beyond simple Books demo data.

Done when:

- Existing cross-node invalidation tests pass.
- Operators can observe invalidation failures.
- Documentation makes the at-most-once tradeoff explicit.

Execution notes:

- Kept `HybridCache` plus Redis pub/sub invalidation.
- Added an operator-visible log when a Redis invalidation publish sees no subscriber acknowledgements.
- Existing warnings already cover publish failures, subscriber reconnect failures, malformed messages, and invalidation apply failures.
- README and LocalCluster deployment docs now explain Redis pub/sub at-most-once behavior and `Cache__Books__DisableLocalCache=true`.

## Phase 6: Container And Deployment Modernization

Status: done.

Priority: high.

Findings:

- `BlazorAutoApp/Dockerfile` uses `mcr.microsoft.com/dotnet/aspnet:10.0` and `sdk:10.0`.
- .NET 10 default tags are Ubuntu-based, which is modern, but the tags are still floating within the 10.0 channel.
- The Dockerfile does not set `USER app`.
- .NET container images include a non-root `app` user and official guidance recommends using it for better security.
- Local and production deployment use port 8080 shape, but production compose still uses `ASPNETCORE_URLS`.
- Modern ASP.NET container guidance recommends the simpler `ASPNETCORE_HTTP_PORTS`/`ASPNETCORE_HTTPS_PORTS` variables where possible.

Plan:

1. Decide the image pinning policy:
   - patch tag such as `10.0.8-noble`
   - digest pinning
   - keep `10.0` only if Dependabot/CI deliberately handles runtime patching
2. Test switching to `USER app`.
3. Review volume permissions for `/app/Storage` before enabling non-root in Docker and LocalCluster.
4. Switch production compose from `ASPNETCORE_URLS` to `ASPNETCORE_HTTP_PORTS` if it works with the Caddy/LocalCluster deployment.
5. Consider chiseled/composite images only after globalization and diagnostics needs are reviewed.

Done when:

- Docker build passes.
- Local Compose starts and health checks pass.
- LocalCluster rendered templates validate.
- Non-root container can read certs, write Data Protection fallback storage if needed, and bind configured ports.

Execution notes:

- Dockerfile now creates `/app/Storage`, copies published files with `--chown=app:app`, and runs as `USER app`.
- Production LocalCluster compose now uses `ASPNETCORE_HTTP_PORTS: ${APP_PORT}` instead of `ASPNETCORE_URLS`.
- Added tests that enforce non-root Dockerfile behavior and production startup-migration disablement.
- Docker build passed.
- A disposable local Compose project started on alternate host ports and `/health/ready` passed under the non-root image.
- LocalCluster deployment audit and rendered-template validation pass.

## Phase 7: Package And Supply Chain Reproducibility

Status: done.

Priority: medium.

Findings:

- Central package management is already in use.
- No direct top-level NuGet package is outdated.
- No NuGet vulnerabilities or deprecated packages were found.
- npm dependencies are current and audit-clean.
- There are no `packages.lock.json` files.
- CI restores packages but does not explicitly run `dotnet list package --vulnerable --include-transitive` or deprecated checks.
- .NET 10 NuGet restore audits transitive dependencies by default, but explicit CI checks make the template behavior easier to understand.

Plan:

1. Consider enabling NuGet lock files:
   - `RestorePackagesWithLockFile=true`
   - CI restore with locked mode after lock files are generated
2. Add explicit CI steps:
   - `dotnet list .\BlazorAutoApp.sln package --vulnerable --include-transitive`
   - `dotnet list .\BlazorAutoApp.sln package --deprecated`
3. Decide whether transitive outdated packages should be tracked only as informational.
4. Keep Dependabot daily, but ensure auto-merge remains conservative for major, Docker, deployment, and workflow surfaces.

Done when:

- Package resolution is reproducible or the repo deliberately documents why it is not locked.
- CI clearly fails on vulnerabilities/deprecated packages.
- Direct package updates remain covered by Dependabot.

Execution notes:

- Kept central package management.
- Did not enable NuGet lock files yet; for this template, explicit audit gates plus Dependabot are the chosen balance for now.
- Added CI steps for transitive NuGet vulnerability checks and deprecated package checks.
- Local NuGet vulnerable/deprecated checks pass.
- npm audit and npm outdated are clean.

## Phase 8: CI And Quality Gates

Status: done.

Priority: medium.

Findings:

- CI already runs deployment linting, actionlint, deployment audit, rendered-template validation, yamllint, build, tests, npm audit, Tailwind build, EF migration bundle, Docker build, and GHCR push.
- CI does not currently run `dotnet format --verify-no-changes`.
- CI does not explicitly run NuGet vulnerable/deprecated checks, although restore now audits transitive packages in .NET 10.
- Headed E2E tests are intentionally skipped unless `RUN_E2E=1`, which matches the user's requirement for visible local browser testing.

Plan:

1. Add formatting verification only after Phase 1 normalization.
2. Add explicit package audit/deprecation checks.
3. Keep default CI E2E skip behavior unless a separate visible/manual E2E workflow is added.
4. Consider uploading Playwright artifacts when E2E is manually run in CI.
5. Avoid running build and test concurrently against the same output directory on Windows because it can lock test output DLLs.

Done when:

- CI catches formatting drift and vulnerable/deprecated packages.
- The visible E2E workflow remains opt-in and documented.
- CI stays fast enough for Dependabot.

Execution notes:

- CI now runs `dotnet format --verify-no-changes`.
- CI now runs explicit NuGet vulnerable/deprecated package checks.
- Kept headed E2E opt-in through `RUN_E2E=1`; normal CI still skips browser E2E.
- Actionlint, yamllint, ShellCheck, deployment audit, and rendered template validation pass.

## Phase 9: Security Headers And HTTP Surface

Status: skipped by plan.

## Phase 10: Identity And Passkey Review

Status: done.

Priority: medium.

Findings:

- Component Identity is the modern .NET 10 direction for Blazor Web Apps.
- Passkeys and `IdentityUserPasskey<string>` are present.
- Identity schema version 3 is configured.
- Some Identity endpoints return or display messages containing user IDs or external provider errors. This mostly follows template patterns, but release-facing templates should review message sensitivity.
- Identity endpoint extension file uses the generated-template namespace style `Microsoft.AspNetCore.Routing`; acceptable but worth keeping intentional.

Plan:

1. Review user-facing Identity status/error messages for sensitive data.
2. Keep passkey flows covered by headed E2E.
3. Confirm Identity pages continue working as static SSR where expected.
4. Keep Identity code under `Features/Login/Account` unless a future restructure has a clear benefit.

Done when:

- Login/register/passkey/manual reset flows pass.
- No user-facing error leaks internal IDs unnecessarily.
- Identity remains isolated in the Login slice.

Execution notes:

- Kept component Identity and passkeys.
- Kept Identity under `Features/Login/Account`.
- Removed user-facing Identity messages that exposed user IDs or raw external-provider/passkey details.
- Identity E2E remains opt-in/headed and is skipped by default unless `RUN_E2E=1`.

## Phase 11: Test Infrastructure Modernization

Status: done.

Priority: medium.

Findings:

- xUnit v3, Testcontainers, Respawn, and Playwright are modern.
- Testcontainers use pinned PostgreSQL and Redis images.
- Integration tests disable parallelization globally.
- `WebAppFactory` uses scoped process environment overrides for startup-time settings. This is practical because minimal hosting reads some configuration early, but it is still a global-state smell.
- Full Release tests pass.

Plan:

1. Keep the current test support until a safer alternative is proven.
2. Investigate reducing process environment overrides with:
   - `UseSetting`
   - earlier host configuration hooks
   - a custom test app factory entry point
3. Preserve disabled test parallelization if process env overrides remain.
4. Add explicit comments in `WebAppFactory` explaining why env overrides exist.
5. Keep cross-node Redis tests because they protect real deployment behavior.

Done when:

- Test support remains deterministic.
- Any environment override is documented and isolated.
- Full suite still passes.

Execution notes:

- Kept xUnit v3, Testcontainers, Respawn, and Playwright.
- Preserved disabled test parallelization because process environment overrides are still used for startup-time configuration.
- Added an explicit comment in `WebAppFactory` explaining why scoped process environment overrides exist.
- Full Release suite passes.

## Phase 12: Documentation And Template Readiness

Status: done.

Priority: low.

Findings:

- Runtime docs are strong: README, local run docs, deployment guide, testing docs, and customization notes exist.
- Historical plan files are large and useful for development history, but they may confuse template consumers if shipped as first-class root docs:
  - `docs/plans/TheBigFixUpBeforePeopleUseIt.md`
  - `docs/plans/Strategy.md`
  - `Modern.md`
- The encrypted Ansible vault is present and appears to be an actual Ansible Vault file, not plaintext.

Plan:

1. Decide whether historical plans should stay at repo root, move to `docs/plans`, or be removed before template release.
2. Keep deployment docs prominent because deployment is part of the template.
3. Keep `TESTING.md` and `BlazorAutoApp.Test/TESTING.md` aligned.
4. Ensure README has the current modern defaults:
   - .NET 10 SDK
   - Redis required outside development/test
   - Interactive Auto homepage
   - visible E2E instructions

Done when:

- A new template user can find the normal docs without reading historical refactor plans.
- No deployment capability is hidden or accidentally removed.

Execution notes:

- Moved older historical plans to `docs/plans`.
- Left active plans `Modern.md` and `ModernSideMission.md` at repo root because they are still being used in this workflow.
- README now points normal users to runtime docs and notes where historical plans live.
- Deployment docs now include the guarded disposable database reset path for fresh baseline migration failures.

## Phase 13: Optional Future Modernization

Status: skipped by plan.
## Final Acceptance For Modernization Execution

When this plan is later executed, final verification should include:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --configuration Release --no-restore
dotnet test .\BlazorAutoApp.sln --configuration Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal
dotnet list .\BlazorAutoApp.sln package --vulnerable --include-transitive
dotnet list .\BlazorAutoApp.sln package --deprecated
```

Frontend and deployment checks:

```powershell
Push-Location .\BlazorAutoApp.Client
npm ci
npm audit
npm outdated
npm run css:build
Pop-Location
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
python -m yamllint .github Deployment/LocalCluster
```

Manual/visible browser gate:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
```

Final state:

- Release build passes with zero warnings.
- Full test suite passes, with headed E2E skipped only when not explicitly enabled.
- Visible headed E2E passes locally before declaring UI/render-mode changes done.
- Docker/local stack starts and `/health/ready` passes after container changes.
- Deployment audit and rendered-template validation pass after deployment changes.
- `git diff --check` passes.
- `git status --short` contains only intentional modernization changes.
