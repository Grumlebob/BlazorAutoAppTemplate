# The Big Fix Up Before People Use It

## Decision

This is a template app. Cleanup should remove stale leftovers from this repository, but it must not add permanent guardrails that prevent forks from intentionally adding uploads, images, inspections, media, different domains, or different folder conventions later.

Do not add banned-word architecture tests for terms like `Upload`, `ImageSharp`, `Inspection`, `Tus`, or `SixLabors`. It is fine to use those terms as one-time cleanup search evidence for this repository. It is not fine to make future users fight tests because they intentionally built one of those features.

The template itself should be modern and should not keep legacy compatibility surface. Old routes, shims, branding, unfinished docs, stale migration history, and old folder conventions should be removed unless they are part of the current .NET 10 template story.

Deployment is part of this template. `Deployment/LocalCluster`, `.github/workflows/cd-localcluster.yml`, and the deployment-aware parts of `.github/workflows/ci.yml` must be preserved unless the user explicitly requests a deployment refactor.

The durable tests should verify the template's current behavior:

- Movies is the first screen and works in Interactive Auto.
- Identity works as authentication/account management.
- The current repo layout is clean and understandable.
- The app builds, tests, runs locally, and passes visible E2E.

## Review Snapshot

Status: execution started on 2026-05-24. Items are checked only after the corresponding work and phase testing pass.

Checks already run during review:

- `git status --short`: clean before this plan file was added.
- Targeted `rg` scans for stale references: inspections, upload/TUS, ImageSharp/SixLabors, IdentityShowcase, Grumlebet branding, TODO/FIXME/HACK, and .NET 9 references.
- `dotnet package list --project .\BlazorAutoApp.sln --outdated`
- `dotnet package list --project .\BlazorAutoApp.sln --deprecated`
- `dotnet package list --project .\BlazorAutoApp.sln --vulnerable --include-transitive`
- `npm outdated` and `npm audit` in `BlazorAutoApp.Client`.
- `git check-ignore` for local generated folders and runtime data.

Dependency result:

- No NuGet updates reported.
- No deprecated NuGet packages reported.
- No vulnerable NuGet packages reported.
- No npm updates reported in `BlazorAutoApp.Client`.
- `npm audit` reports zero vulnerabilities.

Current cleanup evidence:

- No active `Tus` or `TUS` source references found outside ignored local storage.
- No active `ImageSharp` or `SixLabors` references found.
- No active `IdentityShowcase` references found.
- Inspection references are mostly historical EF migration files, not active feature code.

## Standard Phase Exit Test Gate

Run this after every phase before marking that phase done. It is intentionally larger than a normal quick check because this refactor is template-shaping work.

- [x] `dotnet restore .\BlazorAutoApp.sln`
- [x] `dotnet build .\BlazorAutoApp.sln --no-restore`
- [x] `dotnet test .\BlazorAutoApp.sln --no-build`
- [x] `docker compose config`
- [x] `docker compose up -d --build web`
- [x] Verify the app responds at `https://localhost:7186/health`.
- [x] Run visible Playwright E2E:
  - `$env:RUN_E2E='1'`
  - `$env:E2E_BASE_URL='https://localhost:7186'`
  - `Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue`
  - `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"`
- [x] Watch the headed browser enough to confirm the flow is actually behaving, not merely passing invisibly.
- [x] If a phase changes migrations or Docker, also run the EF migration bundle command listed in final verification.
- [x] If a phase changes Tailwind/static CSS, also run `npm audit` and the CSS build command.

## Phase 0 - Baseline And Template Boundaries

- [x] Run the Standard Phase Exit Test Gate before cleanup.
- [x] Treat migration reset/squash as the default template cleanup path.
  - Decision: this repo is being cleaned as a template, so old feature migration history should not be preserved as a compatibility artifact.
  - Risk: deleting historical migrations requires dropping/recreating local/dev databases.
  - Acceptance: document the required local database reset if migrations are squashed.
- [x] Keep cleanup commits scoped by area:
  - Stale files and branding.
  - Identity cleanup.
  - Program/config/EF cleanup.
  - Frontend/static assets.
  - Docs/CI/deployment.
- [x] Keep the cleanup template-friendly:
  - Do not add banned-word source tests.
  - Do not forbid future upload/image/domain features.
  - Do document the current app intent and current slice convention.
  - Do keep tests focused on behavior and local template quality.

### Phase 0 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] Record any failing baseline behavior before touching code, so later cleanup does not hide pre-existing issues.
  - Baseline result: restore, build, non-E2E tests, Docker config, Docker app startup, health check, and visible E2E all passed before cleanup.

## Phase 1 - Remove Current Stale Leftovers

- [x] Reset old EF migration history to the current template schema.
  - Finding: `BlazorAutoApp/Data/Migrations/**` still contains removed inspection, hull image, company, vessel, and image table history.
  - Fix: replace the long history with a clean initial migration containing only the current Identity and Movies schema.
  - Acceptance: a fresh database migrates cleanly to the current schema, and old removed-domain migration names are gone from tracked source.

- [x] Remove stale static image/test assets.
  - Finding: `BlazorAutoApp/wwwroot/test-assets/test-image.PNG` is tracked and no longer referenced.
  - Fix: remove it and the folder if nothing current uses it.
  - Acceptance: current app and tests do not depend on stale image assets.

- [x] Remove local ignored upload runtime residue.
  - Finding: local `data/storage/Tus` exists even though upload functionality is not part of this template now.
  - Fix: delete the local runtime folder.
  - Acceptance: normal app startup does not recreate that folder.

- [x] Remove old app branding.
  - Finding: `BlazorAutoApp.Client/wwwroot/grumlebet_gb_logo.svg` is still referenced by `BlazorAutoApp.Client/Layout/NavMenu.razor`.
  - Fix: replace it with neutral template branding, likely a simple text/logo treatment for Movies.
  - Acceptance: the shell no longer looks like a previous branded product.

- [x] Clean empty and stale folders.
  - Findings include empty `BlazorAutoApp/Areas`, `BlazorAutoApp/wwwroot/js`, `BlazorAutoApp.Test/TestingSetup/Assets`, local `Runtime`, and local `.ansible` skeleton folders.
  - Fix: remove empty tracked folders where applicable and ignore/remove local generated folders if they are not part of the template workflow.
  - Acceptance: root and project folders are easier to scan.

### Phase 1 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] If migrations were reset, verify a fresh database can be created and migrated from zero.
- [x] Confirm Movies still loads as the home page after deleting stale assets.
- [x] Confirm visible E2E covers home render mode, Movies navigation, and Identity register/login.
  - Phase 1 result: clean initial migration applied successfully after resetting the local Postgres Docker volume; visible E2E passed.

## Phase 2 - Identity Cleanup

- [x] Remove Identity UI package-era leftovers from app code.
  - Findings:
    - `BlazorAutoApp/Features/Login/Account/IdentityNoOpEmailSender.cs` imports `Microsoft.AspNetCore.Identity.UI.Services`.
    - `EnableAuthenticator.razor` uses `Microsoft.AspNetCore.Identity.UI` as the authenticator issuer.
  - Fix: use a local sender implementation and use the app name from config for authenticator issuer.
  - Acceptance: Identity remains fully functional without stale Identity UI naming.

- [x] Make the email story explicit.
  - Finding: `IdentityNoOpEmailSender` has a temporary comment about removing a register confirmation branch later.
  - Fix: document no-op email as intentional for local/template development, or wire a real provider behind configuration.
  - Acceptance: register, confirm, reset-password, and external-login flows behave predictably in dev and tests.

- [x] Keep the current account UI grouped under the login feature.
  - Current shape is mostly good: server Identity components live under `BlazorAutoApp/Features/Login/Account`.
  - Fix: remove empty old `Areas` folder and keep docs aligned with `/Account/*`.
  - Acceptance: this repo's current layout is sliced and understandable. Do not add broad guardrails that prevent future forks from reorganizing.

- [x] Remove legacy Identity redirect endpoints.
  - Finding: `Program.cs` redirects `/Identity/Account/Login`, `/Identity/Account/Register`, and `/Identity/Account/Manage`.
  - Fix: remove the old `/Identity/Account/*` compatibility redirects entirely.
  - Acceptance: docs, navigation, and tests use canonical `/Account/*` paths only.

### Phase 2 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] In visible E2E, watch register, logout, login, account manage, and any password/email pages touched by the phase.
- [x] Verify E2E and docs use `/Account/*` only.
- [x] Verify no template UI links to `/Identity/Account/*`.
  - Phase 2 result: old Identity UI namespace and `/Identity/Account/*` redirects were removed; visible E2E passed.

## Phase 3 - Program, Configuration, And EF Modernization

- [x] Split `Program.cs` into clearer composition pieces.
  - Finding: `Program.cs` owns configuration, Serilog, Redis, Data Protection, EF, Identity, auth providers, migrations, redirects, health checks, and helper classes.
  - Fix:
    - Move auth registration to `Features/Login/Account`.
    - Keep Movies registration and endpoint mapping in Movies composition files.
    - Move persistence setup into a persistence extension.
    - Move health checks into dedicated files.
    - Move Serilog setup into an observability extension.
  - Acceptance: top-level startup reads as application assembly rather than subsystem implementation.

- [x] Remove compatibility flags or shims that are not needed for a modern .NET 10 app.
  - Finding: the project already moved to .NET 10, but startup and project files should still be reviewed for old compatibility switches or workaround comments.
  - Fix: keep only current-template .NET 10 settings, and remove obsolete compatibility comments/shims after verifying behavior.
  - Acceptance: project and startup configuration read as intentional .NET 10, not a stack of migration workarounds.

- [x] Replace direct environment-variable string assembly with typed configuration.
  - Finding: connection string fallback reads individual `Database__*` variables directly with `Environment.GetEnvironmentVariable`.
  - Fix: bind and validate database options, then build the Npgsql connection string from typed options.
  - Acceptance: missing configuration fails with a clear validation message.

- [x] Remove the EF pending-model warning suppression if possible.
  - Finding: EF ignores `RelationalEventId.PendingModelChangesWarning`.
  - Fix: fix the model snapshot and Identity schema setup so the warning is not needed.
  - Acceptance: suppression is removed and migration commands still work cleanly.

- [x] Review EF registration lifetimes.
  - Finding: `AddDbContext<AppDbContext>(..., optionsLifetime: ServiceLifetime.Singleton)` is unusual.
  - Fix: use standard EF lifetimes unless a verified .NET 10/Identity reason requires otherwise.
  - Acceptance: feature tests, app startup, and visible E2E pass without custom lifetime surprises.

- [x] Remove unnecessary package pins after verification.
  - Finding: `Microsoft.EntityFrameworkCore.Relational` is explicitly pinned with a dependency-unification comment.
  - Fix: remove it if current .NET 10 packages resolve correctly without it.
  - Acceptance: restore, build, tests, E2E, and EF migration bundle still pass.

- [x] Revisit startup migrations and dev role seeding.
  - Findings:
    - Development defaults to `Database:RunMigrationsAtStartup=true`.
    - Admin/Viewer roles are seeded in development but not used by visible features.
  - Fix: make startup migrations intentional and remove role seeding unless a current feature uses roles.
  - Acceptance: local startup behavior is predictable, and the template does not create unused roles.

- [x] Rename stale test collection names.
  - Finding: tests still use `MediaTestCollection`, which reads like old upload/media functionality.
  - Fix: rename to `AppTestCollection`, `DatabaseTestCollection`, or `IntegrationTestCollection`.
  - Acceptance: test naming describes the current test purpose.

### Phase 3 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] Run the EF migration bundle command.
- [x] Verify `docker compose up -d --build web` starts from a clean app process.
- [x] In visible E2E, specifically watch first load, hydration, Movies CRUD, and Identity login after the composition/config changes.
  - Phase 3 result: startup composition is split into focused extensions; EF uses standard factory/scoped registrations; the warning suppression and package pins are gone; the clean initial migration now includes the .NET 10 Identity passkey schema; restore, build, tests, Docker startup, health, EF bundle, and visible E2E passed.

## Phase 4 - Frontend And Static Asset Cleanup

- [x] Consolidate the Tailwind pipeline.
  - Findings:
    - `BlazorAutoApp/Styles/input.css` and `BlazorAutoApp.Client/Styles/input.css` both exist.
    - `BlazorAutoApp/node_modules` exists locally even though the server project has no `package.json`.
    - Tailwind packages are under `dependencies` instead of `devDependencies`.
  - Fix:
    - Keep one Tailwind input, preferably `BlazorAutoApp.Client/Styles/input.css`.
    - Delete local server `node_modules`.
    - Move Tailwind packages to `devDependencies`.
    - Add `css:build` and `css:watch` npm scripts.
  - Acceptance: one documented CSS build path regenerates `BlazorAutoApp/wwwroot/tailwind.css`.

- [x] Remove stale scoped CSS from the old template shell.
  - Findings:
    - `BlazorAutoApp.Client/Layout/NavMenu.razor.css` contains unused Bootstrap/default-template classes and embedded icons.
    - `BlazorAutoApp.Client/Layout/MainLayout.razor.css` contains unused sidebar/top-row styles that do not match current markup.
  - Fix: remove unused scoped CSS or rewrite it to match current components.
  - Acceptance: visual checks pass on desktop and mobile, and CSS reflects current markup.

- [x] Normalize Identity UI styling.
  - Finding: Identity pages still use many Bootstrap-style classes while the app shell uses Tailwind.
  - Fix: convert Identity pages to Tailwind and remove Bootstrap-style compatibility styling from the template.
  - Acceptance: login, register, manage, 2FA, passkeys, and validation states look consistent.

- [x] Remove unused client configuration if confirmed unused.
  - Finding: `BlazorAutoApp.Client/wwwroot/appsettings.json` exists with logging settings and no obvious consumer.
  - Fix: remove it if client code does not read it.
  - Acceptance: WASM boot and render-mode E2E still pass.

### Phase 4 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] Run `npm audit` in `BlazorAutoApp.Client`.
- [x] Run the CSS build command after `css:build` exists.
- [x] Watch headed E2E on desktop-sized viewport and manually inspect mobile layout as part of the visible browser pass.
- [x] Confirm render-mode diagnostics remain visible and correct on the Movies home page.
  - Phase 4 result: Tailwind has a single client-side input and npm scripts; stale scoped CSS and unused client appsettings files are removed; Identity pages use template-owned account styles instead of Bootstrap class names; npm audit, CSS build, restore, build, tests, Docker startup, health, and visible E2E passed.

## Phase 5 - Docker, CI, Deployment, And Secrets Hygiene

- [x] Fix Docker ignore drift.
  - Finding: `.dockerignore` whitelists `!BlazorAutoApp/docker/Dockerfile`, but the actual Dockerfile is `BlazorAutoApp/Dockerfile`.
  - Fix: update the whitelist or simplify Docker ignore rules.
  - Acceptance: `docker build -f BlazorAutoApp/Dockerfile .` succeeds and no stale Dockerfile path remains.

- [x] Modernize `docker-compose.yml`.
  - Findings:
    - Compose `version: "3.9"` is legacy in modern Docker Compose.
    - `web` logs to Seq config but does not depend on `seq`.
    - local HTTPS password is hardcoded for dev.
  - Fix:
    - Remove obsolete `version` if Compose accepts it cleanly.
    - Decide whether Seq is required or optional for the `web` service.
    - Keep local cert password only as clearly documented dev-only config.
  - Acceptance: `docker compose config` is clean or any warning is understood and documented.

- [x] Review tracked Ansible vault material without breaking the existing deployment.
  - Finding: `Deployment/LocalCluster/inventory/prod/vault.yml` is tracked as an encrypted vault file.
  - Decision: this file is part of the current LocalCluster deployment workflow and must stay restored as long as it remains encrypted.
  - Acceptance: `vault.yml` exists where the deployment expects it and begins with the Ansible Vault header.

- [x] Restore and preserve the existing LocalCluster deployment workflow.
  - Finding: the deployment tree is actively used.
  - Fix: restore `Deployment/LocalCluster`, `.github/workflows/cd-localcluster.yml`, and the deployment-aware CI workflow.
  - Acceptance: the deployment audit, rendered-template validation, and YAML lint checks pass against the refactored app.
  - Correction: the earlier removal was wrong. Deployment is part of the template.

- [x] Undo the accidental deployment destruction and double-check no valuable deployment workflow was lost.
  - Fix: restore all deleted `Deployment/LocalCluster` files, restore `.github/workflows/cd-localcluster.yml`, restore CI's GHCR image push and named migration bundle artifact flow, and keep the new npm/Tailwind CI checks alongside the deployment steps.
  - Review: confirm there are no remaining deleted files under `Deployment/LocalCluster` or `.github/workflows/cd-localcluster.yml`.
  - Review: confirm the only intentional deployment content change is updating `audit_deployment.py` to look for Redis Data Protection, health endpoints, and migration startup guard in the new split startup files instead of only in `Program.cs`.
  - Review: keep `.gitattributes` with `*.sh text eol=lf` so deployment shell scripts run under Bash consistently.
  - Acceptance: `bash Deployment/LocalCluster/Scripts/audit-deployment.sh`, `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh`, and `python -m yamllint .github Deployment/LocalCluster` pass.

- [x] Expand dependency automation.
  - Finding: Dependabot covers GitHub Actions, Docker, and NuGet, but not npm in `BlazorAutoApp.Client`.
  - Fix: add npm ecosystem updates for `/BlazorAutoApp.Client`.
  - Acceptance: Dependabot can update Tailwind packages.

- [x] Add CI checks for frontend tooling if Tailwind output is generated.
  - Fix: add npm install/audit/CSS build verification if generated CSS must stay committed.
  - Acceptance: CI catches stale `tailwind.css` when classes change.

### Phase 5 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] Run `docker build -f BlazorAutoApp/Dockerfile .` directly.
- [x] Confirm Docker app startup logs show migrations/configuration behavior clearly.
- [x] Confirm visible E2E runs against the Docker-hosted app, not a stale local `dotnet run` process.
  - Phase 5 result: Docker ignore now points at the real Dockerfile, Compose uses modern syntax and starts Seq with the app, LocalCluster deployment material was restored because it is part of the template, npm dependency automation and CI frontend checks were added without removing the deployment artifact/image flow, and restore, build, tests, direct Docker build, Docker startup, health, npm checks, deployment audit, rendered-template validation, YAML lint, and visible E2E passed.

## Phase 6 - Documentation, Plans, And Rate Limiting

- [x] Remove `Plans/GoogleLoginGuideThatNeedsFinishing.md`.
  - Finding: file name and content explicitly say it needs finishing and has TODOs.
  - Decision: remove it rather than ship an unfinished guide in a template.
  - Acceptance: no visible doc advertises itself as unfinished.

- [x] Implement rate limiting, then remove `Plans/RateLimiting.md`.
  - Finding: rate limiting is planned but not implemented.
  - Decision: implement the useful app-level rate limiting, document the result in the real docs, then delete the standalone plan file.
  - Acceptance: docs describe implemented behavior, not an unfinished plan.

- [x] Refresh README, overview, local workflow, and testing docs as a set.
  - Fix:
    - README: current app name, Movies-first behavior, canonical auth paths, .NET 10, local URLs, current workflow names.
    - overview: keep Auto render-mode explanation, update account paths, remove stale migration/runtime claims.
    - HowToRunLocally: document port-conflict behavior and Docker/local run options.
    - TESTING: keep headed Playwright default and rename stale test collection references.
    - TypicalWorkflow: merge into HowToRunLocally or remove.
  - Acceptance: a new person can run the app and tests from docs without tribal knowledge.

### Phase 6 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] If rate limiting is implemented, add behavior tests for representative `429` responses without making local E2E flaky.
- [x] Confirm headed E2E still passes under normal human-paced flows.
- [x] Manually follow README and TESTING commands from a clean shell as a doc smoke test.
  - Phase 6 result: unfinished standalone plans were removed; rate limiting is implemented for global app traffic, Movies API endpoints, and account POST endpoints; the new integration test verifies `429` plus `Retry-After`; README, overview, local run docs, and testing docs now describe the current .NET 10 Movies-first template; restore, build, tests, Docker config/startup, health, docs smoke, and visible E2E passed.

## Phase 7 - Final Verification Without Product Guardrails

- [x] Keep tests focused on current template behavior.
  - Build and unit/integration tests should continue to pass.
  - Existing architecture tests should enforce real current architecture contracts, not banned future concepts.
  - Do not add source-scanning tests that fail because a fork intentionally adds uploads, images, inspections, or a different product domain.

- [x] Keep useful targeted behavior tests.
  - API 404s should remain API responses, not Blazor not-found pages.
  - Health endpoints should stay machine-readable.
  - Canonical `/Account/*` routes should work.
  - Legacy `/Identity/Account/*` redirects should not remain.
  - Rate limiting should return predictable `429` responses if implemented in Phase 6.

- [x] Run final one-time cleanup scans for this repository.
  - These are manual/release checks, not permanent fork guardrails.
  - Search for old brand names, unfinished docs, stale migration decisions, and local generated junk.
  - Fix any accidental leftovers found.

### Phase 7 Testing Gate

- [x] Complete the Standard Phase Exit Test Gate.
- [x] Run the EF migration bundle command:
  - `dotnet ef migrations bundle --project BlazorAutoApp\BlazorAutoApp.csproj --startup-project BlazorAutoApp\BlazorAutoApp.csproj --configuration Release --self-contained --runtime linux-x64 --output artifacts\migrations\verify-migrate`
- [x] Run npm checks:
  - `npm install` in `BlazorAutoApp.Client`
  - `npm audit` in `BlazorAutoApp.Client`
  - `npm run css:build` in `BlazorAutoApp.Client`
- [x] Run visible Playwright E2E one final time and watch the browser flow.
- [x] Confirm `git status --short` contains only intentional changes.
  - Phase 7 result: final restore, build, tests, Docker config/startup, health, EF migration bundle, npm install/audit/CSS build, visible E2E, stale-reference scans, Client slicing check, whitespace check, and git status review all passed. The remaining working-tree changes are the intentional template refactor, deletions, regenerated migration/CSS/package metadata, and this plan.

## Done Criteria

- [x] The current repo no longer ships accidental leftovers from removed features.
- [x] Old migration history is reset for template use.
- [x] Legacy `/Identity/Account/*` compatibility redirects are removed.
- [x] Home page is Movies-first and template-appropriate.
- [x] Identity is real authentication/account management only, grouped under the login feature in this repo.
- [x] Program/config/EF setup is understandable and modern for .NET 10.
- [x] Static assets and CSS have one clear pipeline.
- [x] Rate limiting is implemented and documented without an unfinished plan file.
- [x] The existing encrypted LocalCluster Ansible vault file is restored because this repository's deployment flow uses it.
- [x] Docs match the app people will actually run.
- [x] CI and local test docs cover .NET, npm/Tailwind, Docker config, integration tests, and visible Playwright E2E.
- [x] No permanent guardrails prevent future forks from intentionally adding new domains, uploads, images, or capabilities.
