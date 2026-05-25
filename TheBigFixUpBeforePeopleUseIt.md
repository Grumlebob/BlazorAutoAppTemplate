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

## Second Whole-Repo Review - 2026-05-24

Status: second review backlog executed on 2026-05-24. The phases below were implemented and checked with the larger test gates requested by the user, including headed Playwright E2E.

This review treats the repository as a .NET 10 Blazor template with a real Movies-first sample app, real Identity authentication, and a real LocalCluster deployment flow. Deployment is part of the template and must be preserved, tested, and documented. The goal is not to add tests that block forks from building new products; the goal is to remove stale assumptions, sharpen defaults, and make the template reliable before people use it.

### Review Evidence

- [x] `dotnet package list --project .\BlazorAutoApp.sln --outdated` reports no package updates.
- [x] `dotnet package list --project .\BlazorAutoApp.sln --deprecated` reports no deprecated packages.
- [x] `dotnet package list --project .\BlazorAutoApp.sln --vulnerable --include-transitive` reports no vulnerable packages.
- [x] `npm outdated` in `BlazorAutoApp.Client` reports no outdated npm packages.
- [x] `npm audit` in `BlazorAutoApp.Client` reports zero vulnerabilities.
- [x] `bash Deployment/LocalCluster/Scripts/audit-deployment.sh` passes.
- [x] `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh` passes.
- [x] `docker compose config --quiet` passes for the local root Compose file.
- [x] `docker compose -f Deployment/LocalCluster/compose/node-db/docker-compose.yml config --quiet` parses, but warns when deployment env vars are absent.
- [x] `docker compose -f Deployment/LocalCluster/compose/app-server/docker-compose.yml config --quiet` fails when run bare because required deployment env vars are absent. That is acceptable only if the deployment docs/scripts always generate and load the env file before validation.
- [x] Docker build context probe shows a small context, but `.dockerignore` still has a broad `!docker/**` include while `docker/https/aspnetapp.pfx` exists locally.
- [x] Targeted scans found remaining template issues worth reviewing: all-forwarded-header trust, query string logging, local moving Docker tags, Bootstrap Identity leftovers, hidden `ReleaseYear` drift, broad global usings, environment-variable mutation in tests, and a few docs/tooling consistency gaps.

Execution note: the broad Docker include and the other findings above were addressed during phases 9-18. The local Docker context now excludes local certs/secrets/data, Docker restore copies central MSBuild props, and headed E2E caught and verified the Blazor Auto hydration fix.

### Priority Order

- [x] First priority: deployment preservation and security defaults.
- [x] Second priority: local development reproducibility and .NET 10 repo hygiene.
- [x] Third priority: Movies/Identity polish and broader visible E2E coverage.
- [x] Fourth priority: docs, onboarding, and final clean-clone acceptance.

## Phase 8 - Deployment Preservation And CD Quality

- [x] Treat `Deployment/LocalCluster` and `.github/workflows/cd-localcluster.yml` as template-owned assets.
  - Finding: these files are part of the working template, not stale local experiments.
  - Fix: make future cleanup language say "review deployment" instead of "remove local deployment".
  - Acceptance: deployment files remain present, documented, and covered by CI checks.

- [x] Expand `.gitattributes` beyond `*.sh text eol=lf` if needed.
  - Finding: Bash scripts are sensitive to CRLF on Windows checkouts.
  - Consider: `*.sh`, `*.yml`, `*.yaml`, `*.j2`, and Python scripts with consistent text normalization.
  - Acceptance: deployment scripts execute through Bash after a fresh Windows checkout.

- [x] Add `shellcheck` coverage for deployment shell scripts.
  - Scope: `Deployment/LocalCluster/Scripts/**/*.sh` plus root/local Docker shell scripts if any are added later.
  - Acceptance: CI runs shellcheck or a documented equivalent without creating fork-hostile policy checks.

- [x] Add `actionlint` coverage for `.github/workflows/*.yml`.
  - Finding: workflow regressions are easy to miss locally.
  - Acceptance: CI or docs include a repeatable workflow lint command.

- [x] Review CI runner image pinning.
  - Finding: CI uses `ubuntu-latest`; auto-merge uses `ubuntu-24.04`.
  - Decision: either pin CI to `ubuntu-24.04` for reproducibility or document why `latest` is intentional.
  - Acceptance: both workflows use a deliberate runner strategy.

- [x] Review Dependabot coverage for deployment Docker files and Compose files.
  - Finding: Dependabot has `docker` at `/`, but deployment Docker/Compose assets live under nested directories.
  - Fix: confirm coverage or add explicit entries for `BlazorAutoApp`, `Deployment/LocalCluster/compose/app-server`, and `Deployment/LocalCluster/compose/node-db`.
  - Acceptance: pinned deployment images are update-visible without hand scanning.

- [x] Review Dependabot auto-merge policy.
  - Finding: successful Dependabot PRs are auto-approved and merged.
  - Risk: package, action, or image changes can flow to `main`, publish images, and become deployment candidates.
  - Fix: decide whether to exclude major updates, Docker image updates, or deployment-affecting changes from auto-merge.
  - Acceptance: auto-merge is explicit and safe enough for a deployable template.

- [x] Add deployment artifact checks to docs.
  - Include EF migration bundle name, artifact upload name, GHCR image tag, and CD download step.
  - Acceptance: local docs explain how CI and CD connect for one commit.

### Phase 8 Testing Gate

- [x] Do full testing.
  - Phase 8 result: deployment assets remain present; CI now runs shellcheck, actionlint, deployment audit, rendered-template validation, and yamllint on `ubuntu-24.04`; Dependabot covers nested deployment Docker/Compose surfaces; Dependabot auto-merge skips major, workflow, Docker, and deployment-surface changes; deployment docs now describe the CI image and migration bundle artifact handoff. `bash Deployment/LocalCluster/Scripts/audit-deployment.sh`, `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh`, `python -m yamllint .github Deployment/LocalCluster`, Docker actionlint, Docker shellcheck, and Bash syntax checks passed.


## Phase 9 - Security, Headers, Logging, And Secrets

- [x] Replace trust-all forwarded headers with configured proxy trust.
  - Finding: `ForwardingExtensions` clears `KnownIPNetworks` and `KnownProxies`.
  - Risk: any direct client can spoof `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host`.
  - Fix: configure known proxies/networks for local Docker, Caddy, Cloudflare tunnel, and deployment.
  - Acceptance: direct spoofed forwarded headers are ignored unless they come through trusted infrastructure.

- [x] Add tests for forwarded-header trust boundaries.
  - Include spoofed `X-Forwarded-For` against rate limiting.
  - Include expected forwarded behavior behind the configured proxy path.
  - Acceptance: forwarded headers cannot be used to bypass per-IP rate limiting.

- [x] Stop logging raw query strings by default.
  - Finding: `ObservabilityExtensions` logs `QueryString`.
  - Risk: Identity confirmation/reset links carry sensitive tokens in query parameters.
  - Fix: remove query strings from request logs or log only a scrubbed allowlist.
  - Acceptance: password reset, email confirmation, external login, and passkey requests do not leak tokens into Seq/console logs.

- [x] Add typed options validation for security-sensitive settings.
  - Scope: forwarded headers, rate limiting, database, Redis, app name, external auth providers.
  - Acceptance: invalid production config fails with a clear startup error.

- [x] Review rate limiting defaults and partitioning.
  - Current: global, API, and account POST policies exist.
  - Check: authenticated user partitioning, anonymous IP partitioning, forwarded headers, `Retry-After`, and error shape.
  - Acceptance: limits are useful locally and not easy to bypass in deployment.

- [x] Harden Data Protection key handling.
  - Finding: Redis persistence is used when configured; file system fallback is used otherwise; Docker certificate protection is best-effort.
  - Fix: document and configure production key protection clearly for Linux/LocalCluster.
  - Acceptance: deployed apps do not silently store unprotected keys in an unexpected place.

- [x] Replace startup `Console.WriteLine` for Data Protection certificate failures.
  - Finding: `AppCachingExtensions` writes directly to console in a catch block.
  - Fix: use structured logging or fail clearly based on environment.
  - Acceptance: startup diagnostics are visible and consistent.

- [x] Clarify dev-only secrets.
  - Scope: default Postgres password, Redis password, Kestrel dev certificate password, `.env.example`, appsettings.
  - Acceptance: new users know which values are local-only and which must be changed for deployment.

### Phase 9 Testing Gate

- [x] Full testing
  - Phase 9 result: forwarded headers now trust only configured proxies/networks, spoofing coverage was added through `ForwardedHeadersTests`, raw query-string request logging was removed, security-sensitive options are validated, rate-limiting behavior remains deterministic, Data Protection fallback/Redis behavior is documented, and certificate failures use structured logging. Restore, build, tests, Docker health, deployment checks, and headed E2E passed.

## Phase 10 - Local Development And Docker

- [x] Bind local infrastructure ports to loopback by default.
  - Finding: root Compose exposes Postgres, Redis, Seq, and Redis Insight using host-wide bindings.
  - Fix: use `127.0.0.1:5432:5432`, etc., unless wide binding is explicitly needed.
  - Acceptance: local dev services are not exposed to the LAN by accident.

- [x] Pin or deliberately manage local Docker image tags.
  - Finding: root Compose uses `postgres:16-alpine`, `redis:7-alpine`, `datalust/seq:latest`, and `redis/redisinsight:latest`.
  - Decision: use exact pins for reproducibility or document moving dev tags and monitor them.
  - Acceptance: local stack behavior is predictable for template users.

- [x] Tighten `.dockerignore` around local certificates and secrets.
  - Finding: `.dockerignore` has `!docker/**`, while `docker/https/aspnetapp.pfx` exists locally.
  - Fix: explicitly ignore `docker/https/*.pfx`, `.env`, generated data, test output, and local secrets even if current context is small.
  - Acceptance: Docker context cannot accidentally include local certificates or secret files.

- [x] Review Docker build context with an intentional command.
  - Acceptance: docs or CI include a way to see context size and confirm no secret files are sent.

- [x] Review root Dockerfile input assumptions.
  - Check: solution references, project paths, client npm build, Tailwind output, `.dockerignore` allowlist, runtime image.
  - Acceptance: Docker build works from a clean clone without depending on local generated CSS, so Tailwind works basically.

- [x] Make local setup scripts idempotent.
  - Scope: `docker/setup-local.ps1`, `docker/create-dev-cert.ps1`, and `docker/local-status.py`.
  - Acceptance: running setup repeatedly does not overwrite meaningful local choices unless requested.

- [x] Expand `docker/local-status.py`.
  - Check .NET SDK from `global.json`, Node/npm presence, Docker availability, Compose config, HTTPS certificate presence, `.env` required keys, port availability, and deployment docs link.
  - Acceptance: it reports actionable blockers before users hit runtime errors.

- [x] Document and test port conflict behavior.
  - Include app ports `7186`/`5025`, Postgres `5432`, Redis `6379`, Seq `8081`/`5341`, Redis Insight `5540`.
  - Acceptance: users get clear instructions when ports are busy.

- [x] Clarify `/app/Storage` ownership.
  - Finding: root Compose mounts `./data/storage:/app/Storage`.
  - Fix: document that this is Data Protection/local runtime storage, not upload functionality.
  - Acceptance: no one confuses the storage mount with a removed upload feature.

### Phase 10 Testing Gate

- [x] Run `docker compose config --quiet`.
- [x] Run `docker compose up -d --build`.
- [x] Verify `https://localhost:7186/health/live` and `/health/ready`.
- [x] Verify Seq receives logs if Seq is enabled.
- [x] Verify Redis and Postgres health checks.
- [x] Run visible Playwright E2E against the Docker-hosted app.
- [x] Stop the stack and confirm volumes/data behavior is documented.
  - Phase 10 result: local Compose now binds infrastructure to loopback with configurable `*_HOST_PORT` values, Docker images are pinned, Docker context excludes local certs/secrets/data, setup scripts are idempotent, `local-status.py` reports SDK/tooling/ports/config, Docker build was fixed to copy central MSBuild props, and the stack is running at `https://localhost:7186` with Postgres on local host port `5433` because this machine already owns `5432`.

## Phase 11 - .NET 10 Build, Solution, And Dependency Hygiene

- [x] Add `Directory.Packages.props` for centralized NuGet versions.
  - Finding: package versions are repeated across projects.
  - Acceptance: updates are one-file changes and Dependabot still works.

- [x] Add `Directory.Build.props` for repo-wide build defaults.
  - Consider: nullable, implicit usings, analysis level, deterministic builds, warnings policy, test exclusions.
  - Acceptance: project files only carry project-specific settings.

- [x] Review `BlazorDisableThrowNavigationException`.
  - Finding: client project sets it explicitly.
  - Acceptance: keep only if still needed with .NET 10 behavior and documented.

- [x] Review `RequiresAspNetWebAssets`.
  - Finding: server project sets it explicitly.
  - Acceptance: keep only if required for the current Blazor Auto setup.

- [x] Keep package check commands current in docs.
  - Correct syntax: `dotnet package list --project .\BlazorAutoApp.sln --outdated`, `--deprecated`, and `--vulnerable --include-transitive`.
  - Acceptance: docs do not contain old CLI syntax.

### Phase 11 Testing Gate

- [x] Run `dotnet restore`.
- [x] Run `dotnet build --configuration Release --no-restore`.
- [x] Run `dotnet test --configuration Release --no-build`.
- [x] Run `dotnet package list --project .\BlazorAutoApp.sln --outdated`.
- [x] Run `dotnet package list --project .\BlazorAutoApp.sln --deprecated`.
- [x] Run `dotnet package list --project .\BlazorAutoApp.sln --vulnerable --include-transitive`.
- [x] Run `npm ci`, `npm audit`, and `npm run css:build`.
- [x] Run visible Playwright E2E after any render-mode or project-property change.
  - Phase 11 result: central package/build props are in place, project files carry only project-specific settings, `BlazorDisableThrowNavigationException` was removed, `RequiresAspNetWebAssets` was deliberately kept because Docker publish otherwise 404s `_framework/blazor.web.js` and prevents Blazor Auto hydration, package-check docs use the current CLI syntax, and Debug/Release build/test plus headed E2E passed.

## Phase 12 - Configuration, EF, Caching, And Health

- [x] Align `settings.defaults.json` with actual configuration binding.
  - Finding: it contains `Serilog:SeqUrl`, but Serilog is configured through `Serilog:WriteTo`.
  - Fix: remove unused keys or wire them intentionally.
  - Acceptance: every default setting is read by code or documented as placeholder-only, or removed.

- [x] Fix placeholder type mismatches.
  - Finding: `Database:Port` in `settings.defaults.json` is a string placeholder while `DatabaseOptions.Port` is an `int`.
  - Fix: avoid binding failures with clearer defaults or explicit validation.
  - Acceptance: missing database settings fail with a clear message.

- [x] Prefer options validation over manual scattered validation.
  - Scope: `DatabaseOptions`, Redis, Movies cache, rate limiting, app name, forwarded headers.
  - Acceptance: startup validation reports all relevant config errors clearly.

- [x] Clarify `ConnectionStrings:DefaultConnection` versus `Database:*`.
  - Finding: both patterns exist.
  - Decision: support both deliberately or choose one public template convention.
  - Acceptance: docs and code do not make users guess.

- [x] Review startup migrations by environment.
  - Current: default true in Development, configured true in Docker, deployment uses EF migration bundle.
  - Acceptance: local, Docker, test, and LocalCluster migration paths are explicit and non-overlapping.

- [x] Add cancellation tokens through Movies endpoints and service calls.
  - Finding: read paths use cache callbacks with cancellation; create/update/delete do not pass request cancellation.
  - Acceptance: request aborts can cancel database work where reasonable.

- [x] Log cache invalidation failures.
  - Finding: Movies cache invalidation catches and ignores all exceptions.
  - Fix: use structured warning logs without surfacing cache errors to API consumers.
  - Acceptance: hidden cache problems are observable.

- [x] Review HybridCache usage and serializer expectations.
  - Scope: nullable cached responses, item/list keys, invalidation, TTLs, Redis backing.
  - Acceptance: cache behavior is tested and documented.

- [x] Review health check response shape.
  - Current: health checks exist for live/ready.
  - Decision: plain status is fine for probes, but docs should state it.
  - Acceptance: Docker, CI, deployment, and docs all use the same health paths.

- [x] Review EF model source of truth.
  - Finding: domain attributes and EF configuration can drift.
  - Decision: keep attributes for validation visibility or move constraints fully into EF configuration/DTO validation.
  - Acceptance: validation and database constraints tell the same story.

### Phase 12 Testing Gate

- [x] Run tests with Redis disabled.
- [x] Run local Docker with Redis enabled.
- [x] Run migration bundle generation.
- [x] Run health checks for live and ready paths.
- [x] Run Movies integration tests after cache/config changes.
- [x] Run deployment audit after config key changes.
  - Phase 12 result: defaults now align with actual binding, placeholder type drift was removed, database/app/forwarded-header options are validated, startup migration paths are documented, Movies endpoints/services pass cancellation tokens, cache invalidation failures are logged, health paths are consistent, `ReleaseYear` was removed from the model/migration/test generator, and Redis-enabled Docker plus Redis-disabled test paths passed.

## Phase 13 - Identity Feature Quality

- [x] Verify all login/account server code stays under `BlazorAutoApp/Features/Login`.
  - Finding: most server Identity code is now grouped there.
  - Acceptance: login-related code is not scattered outside the feature unless there is a clear shared reason.

- [x] Decide whether `BlazorAutoApp.Client/Features/Login/Components/RedirectToLogin.razor` is the right client-side location.
  - This may be correct because it is a client route helper.
  - Acceptance: the client/server split is documented and intentional.

- [x] Remove Bootstrap leftovers from Identity components.
  - Findings: `glyphicon glyphicon-warning-sign` and `text-info` remain in manage pages.
  - Fix: convert to Tailwind/account CSS classes.
  - Acceptance: Identity UI has no dead Bootstrap class assumptions.

- [x] Review account CSS for old framework residue.
  - Some validation classes may be Blazor conventions, not Bootstrap.
  - Acceptance: only useful classes remain.

- [x] Review passkey support end to end.
  - Scope: schema version 3, `IdentityUserPasskey`, passkey JS, manage pages, HTTPS requirement, browser support.
  - Acceptance: passkey UI works locally in a visible browser or is clearly documented as conditional.

- [x] Expand Identity visible E2E coverage.
  - Include register, login, logout, manage profile, password change/set, forgot password outbox/log behavior, and access denied.
  - Acceptance: Identity component routes are proven, not just compiled.

- [x] Review account status-cookie messages.
  - Scope: message content, cookie lifetime, sensitive data, styling.
  - Acceptance: status messages are useful without leaking sensitive data.

- [x] Confirm only canonical `/Account/*` routes remain.
  - No legacy `/Identity/Account/*` compatibility route should be restored.
  - Acceptance: the template is modern and does not carry old route shims.

### Phase 13 Testing Gate

- [x] Run Identity unit/integration tests.
- [x] Run visible Playwright E2E for register/login/logout/manage.
- [x] Test forgot password behavior with the chosen local email approach.
- [x] Test passkey page behavior on HTTPS.
- [x] Search for Bootstrap leftovers and legacy Identity routes.
  - Phase 13 result: login/account code remains under `BlazorAutoApp/Features/Login` with the client redirect helper documented as a client-side feature helper, Bootstrap leftovers were removed, passkey pages compile and open over HTTPS, Identity headed E2E now covers register/logout/login/profile/passkeys/forgot-password, and no legacy `/Identity/Account/*` route remains.

## Phase 14 - Movies Feature And API Polish

- [x] Fix client 404 semantics for `GetByIdAsync`.
  - Finding: `MoviesClientService.GetByIdAsync` uses `GetFromJsonAsync`, which throws on 404.
  - Risk: direct navigation after hydration shows a raw error instead of "Movie not found."
  - Acceptance: server prerender and interactive client paths both return null for 404.

- [x] Decide what to do with `ReleaseYear`.
  - Finding: domain, migration, and test generator include `ReleaseYear`, but Create/Update DTOs and UI do not expose it.
  - Options: remove it from the template or make it first-class across DTOs, EF, forms, details, list, tests, and migration.
  - Acceptance: Movies data model has no hidden field drift. Remove it.

- [x] Improve empty state on the Movies home page.
  - Current: an empty table renders when there are no movies.
  - Acceptance: first-run template experience is clear without explanatory marketing copy.

- [x] Add delete confirmation or undo behavior.
  - Current: delete is immediate.
  - Acceptance: accidental destructive clicks are harder.

- [x] Avoid raw exception messages in UI.
  - Finding: Movies pages display `ex.Message`.
  - Fix: show user-safe messages and log details server-side.
  - Acceptance: UI errors are clean and do not expose internals.

- [x] Standardize API error responses.
  - Finding: route/body ID mismatch returns a plain string.
  - Fix: use ProblemDetails for validation, mismatch, rate limit, and unexpected API errors.
  - Acceptance: API consumers get consistent machine-readable errors.

- [x] Add cancellation tokens to API endpoints.
  - Acceptance: endpoint handlers accept `CancellationToken` and services pass it to EF/cache where useful.

- [x] Review "Back" navigation behavior in details/edit pages.
  - User-observed issue: clicking back from view appeared to do nothing earlier.
  - Acceptance: browser back, explicit Back link, and route transitions work in interactive Auto mode.

- [x] Add fuller Movies visible E2E.
  - Include create, details, explicit Back, browser Back, edit save, edit cancel, delete, not found, empty state, mobile width.
  - Acceptance: the whole sample app flow is visibly verified.

### Phase 14 Testing Gate

- [x] Run Movies integration tests.
- [x] Run visible Playwright Movies E2E against local `dotnet run`.
- [x] Run visible Playwright Movies E2E against Docker-hosted app.
- [x] Verify API 404s remain API responses and do not render Blazor not-found pages.
- [x] Verify generated migration/model snapshot if `ReleaseYear` changes.
  - Phase 14 result: Movies client 404s return null, API errors use ProblemDetails where appropriate, hidden `ReleaseYear` drift is gone, empty/delete/error states were polished, back navigation is covered, cancellation tokens flow through endpoints/services, and headed E2E verifies create/view/explicit Back/browser Back/edit/cancel/delete/not-found.

## Phase 15 - Blazor Auto Render Modes And Frontend Structure

- [x] Keep the homepage Movies-first.
  - Acceptance: `/` and `/movies` show the Movies experience, not an identity showcase or landing page.

- [x] Keep render-mode visibility on the homepage.
  - Current: `RenderModeBadge` shows configured, assigned, current renderer, and interactivity.
  - Improve: make it useful without visually dominating the Movies app.
  - Acceptance: template users can see whether Auto is prerendered/static/interactive.

- [x] Test render-mode transitions explicitly.
  - Scope: prerender state, hydration, server fallback, WebAssembly download path, interactive actions.
  - Acceptance: Playwright asserts both initial static/prerender info and eventual interactive state.

- [x] Review PersistentState usage.
  - Scope: Movies list/details state, cache coherence after create/update/delete, hydration behavior.
  - Acceptance: state persistence improves UX without stale data bugs.

- [x] Keep Client folder sliced.
  - Requirement: no generic `BlazorAutoApp.Client/Pages` folder.
  - Acceptance: pages live under feature slices like `Features/Movies/Pages` and `Features/AppShell/Pages`.

- [x] Reduce UI coupling from global imports.
  - Scope: client `_Imports.razor`, layout imports, feature imports.
  - Acceptance: adding a new feature does not inherit Movies-only symbols.

- [x] Review visual design consistency.
  - Current: simple Tailwind UI with some generic gray/blue styling.
  - Improve: buttons, tables, empty states, account screens, nav, focus states, mobile menu, and render badge.
  - Acceptance: screenshots look like a polished template app, not a half-converted sample.

- [x] Verify text/layout fit on mobile and desktop.
  - Include long movie titles, long email addresses in nav, account manage pages, and validation errors.
  - Acceptance: no overlapping or clipped UI in checked viewports.

### Phase 15 Testing Gate

- [x] Run visible Playwright E2E at desktop viewport.
- [x] Run visible Playwright E2E at mobile viewport.
- [x] Capture screenshots for homepage, Movies create/details/edit, login/register, account manage, and not-found.
- [x] Verify no `BlazorAutoApp.Client/Pages` folder exists.
- [x] Verify render-mode badge transitions from prerender/static to interactive.
  - Phase 15 result: `/` and `/movies` are Movies-first, render-mode diagnostics remain visible without dominating the page, the published Docker app now serves the Blazor Web App boot script and hydrates to interactive Auto, client pages remain sliced with no `BlazorAutoApp.Client/Pages`, Movies imports are feature-local, and desktop plus mobile headed E2E passed. The mobile menu was changed to native `<details>/<summary>` so it works on static Identity pages as well as hydrated pages.

## Phase 16 - Test Suite Reliability And Coverage

- [x] Keep Playwright visible by default for local E2E.
  - User preference: not headless by default.
  - Acceptance: docs and test defaults open a browser unless `E2E_HEADLESS=1` is explicitly set.

- [x] Add Playwright trace/video strategy.
  - Current: failure screenshots are captured.
  - Consider: retain trace/video on failure, and document where output is written.
  - Acceptance: failures are diagnosable without rerunning blindly.

- [x] Replace broad `NetworkIdle` waits where they can be flaky.
  - Finding: Blazor can keep connections active, and current E2E uses network idle in base navigation and Identity tests.
  - Fix: wait for specific selectors, render-mode badge interactivity, route content, or app state.
  - Acceptance: tests are stable in Blazor Auto.

- [x] Isolate `WebAppFactory` configuration.
  - Finding: tests mutate process-wide environment variables for database, Redis, and migrations.
  - Fix: prefer factory-specific configuration through `ConfigureAppConfiguration`.
  - Acceptance: tests can run without env leakage across collections.

- [x] Clean stale comments in test infrastructure.
  - Finding: comments like "Default!" and "THIS IS WHERE YOU CAN ADD SEED DATA" remain.
  - Acceptance: test setup reads like production-quality template code.

- [x] Pin or manage Testcontainers images.
  - Finding: tests use `postgres:16-alpine`.
  - Decision: use exact image pins or document moving test image policy.
  - Acceptance: test containers are reproducible enough for CI.

- [x] Make rate limiting tests deterministic.
  - Current tests use default-like limits and generated IP partitions.
  - Fix: use test-specific config and deterministic partition keys.
  - Acceptance: tests are fast and not sensitive to execution order.

- [x] Exclude generated folders from source-search helper.
  - Finding: `SourceSearch` recursively reads files and can include `bin`/`obj` if pointed broadly.
  - Acceptance: architecture tests do not fail on generated output.

- [x] Review architecture tests for fork-friendliness.
  - Keep tests that validate the current template's slicing.
  - Avoid tests that ban future domains, uploads, images, or product choices.
  - Acceptance: tests catch accidental current-regression without policing future apps.

- [x] Add deployment quality checks to the test docs.
  - Include audit, rendered templates, yamllint, actionlint, shellcheck, Compose validation.
  - Acceptance: deployment has a real testing story.

- [x] Add end-to-end phase testing after each future phase.
  - Requirement from user: larger testing after each phase includes E2E.
  - Acceptance: every phase in this second backlog has a visible E2E gate where UI behavior can be affected.

### Phase 16 Testing Gate

- [x] Run full `dotnet test`.
- [x] Run visible Playwright E2E with the browser open.
- [x] Run visible Playwright E2E against Docker-hosted app.
- [x] Run test suite twice to catch order/env leakage.
- [x] Inspect `TestResults/Playwright` artifacts after an intentional or real failure.
  - Phase 16 result: Playwright is headed by default, trace/video/screenshot artifacts are documented, broad network-idle waits were removed, test containers are pinned, generated folders are excluded from source searches, architecture tests remain fork-friendly, viewport-controlled headed E2E was added, and the suite was run multiple times in Debug/Release plus desktop/mobile E2E.

## Phase 17 - Documentation And Onboarding

- [x] Refresh README after the second cleanup pass.
  - Include Movies-first app, Identity authentication, render-mode badge, .NET 10 SDK, local Docker, tests, and LocalCluster deployment.
  - Acceptance: README reflects the actual template and deployment story.

- [x] Consider a root `TESTING.md` or link clearly to `BlazorAutoApp.Test/TESTING.md`.
  - Acceptance: users can find all test commands from the repo root.

- [x] Update `HowToRunLocally.md`.
  - Include port conflict handling, setup script, local HTTPS cert, Docker stack, plain `dotnet run`, visible E2E, and troubleshooting.
  - Acceptance: a new user can get to the Movies homepage without guessing.

- [x] Update `overview.md`.
  - Include project slicing, server/client/core/test roles, Identity location, Movies feature flow, cache/data paths, render modes, and deployment.
  - Acceptance: architecture docs match source layout.

- [x] Update deployment docs after any deployment workflow change.
  - Keep LocalCluster instructions complete.
  - Acceptance: docs preserve the working deployment flow instead of abstracting it away.

- [x] Add a template customization guide.
  - Scope: app name, domain, GHCR image, public hostname, database, Redis, Google auth, deployment runner label, Caddy/Cloudflare, package names.
  - Acceptance: people forking the template know what to rename and what to leave alone.

- [x] Document app name configuration.
  - Finding: app name appears in Data Protection and authenticator issuer fallback.
  - Fix: introduce or document `App:Name`.
  - Acceptance: renaming the template is not a source search exercise.

- [x] Remove stale comments from `.gitignore` or simplify it.
  - Finding: generated `.gitignore` is broad and has stock comments.
  - Acceptance: ignore rules are understandable and preserve deployment-sensitive ignores.

### Phase 17 Testing Gate

- [x] Follow README from a clean shell.
- [x] Follow `HowToRunLocally.md` from a clean shell.
- [x] Follow visible E2E docs exactly.
- [x] Follow deployment validation docs without deploying.
- [x] Search docs for stale feature names, old routes, old .NET versions, and unfinished-plan language.
  - Phase 17 result: README, root `TESTING.md`, detailed test docs, local run docs, overview, deployment docs, `.gitignore`, and the customization guide now describe the current .NET 10 Movies-first template, Identity/passkeys, render-mode diagnostics, configurable local ports, central package management, and LocalCluster deployment.

## Phase 18 - Final Acceptance Before People Use It

- [x] Run full dependency checks.
  - NuGet outdated, deprecated, vulnerable including transitive.
  - npm outdated and audit.
  - Docker/deployment image update visibility through Dependabot.

- [x] Run full .NET checks.
  - Restore, build Release, test Release, format check if adopted, migration bundle generation.

- [x] Run full frontend checks.
  - `npm ci`, `npm audit`, `npm run css:build`, generated CSS diff check.

- [x] Run full local Docker checks.
  - Compose config, build, startup, health live/ready, logs, visible E2E.

- [x] Run full deployment checks.
  - Deployment audit, rendered templates, yamllint, actionlint, shellcheck, Compose validation through env-loading path.

- [x] Run visible browser walkthrough.
  - Movies list, create, view, back, edit, delete, not found.
  - Register, login, logout, manage profile, forgot password local behavior.
  - Render-mode badge from prerender/static to interactive.

- [x] Review security-sensitive logs manually.
  - Confirm reset/confirm/passkey/external-login token values are not logged.

- [x] Review `git status --short`.
  - Acceptance: only intentional files are changed, and no generated local secrets are tracked.

- [x] Review `git diff`.
  - Acceptance: no deployment asset was deleted or weakened accidentally.

- [x] Tag the guide with final status.
  - Acceptance: every second-review phase is either completed, explicitly deferred with reason, or removed because it was invalid.

### Phase 18 Testing Gate

- [x] Final status: completed on 2026-05-24.
  - Final result: restore, Debug build/test, Release build/test, NuGet outdated/deprecated/vulnerable checks, npm outdated/audit/CSS build, EF migration bundle, Docker config/build/startup/health, Redis/Postgres/Seq checks, deployment audit, rendered-template validation, yamllint, actionlint, shellcheck, stale-reference scans, desktop headed E2E, mobile headed E2E, `git diff --check`, `git status --short --ignored`, and deployment diff review all completed. `git diff --check` reports only expected line-ending normalization warnings from Git attributes/autocrlf, not whitespace errors.

## Tripple Check Review - 2026-05-25

Status: completed on 2026-05-25. This was a fresh senior review pass over every already-completed plan point. A `Tripple checked` item is marked only after source review, command evidence, or both confirm the implementation is still good and not just historically marked done.

Tripple-check findings:

- Fixed: `WebAppFactory` still needed environment-variable precedence for minimal-hosting configuration, but now uses a scoped helper that restores previous values instead of leaking app test settings into the process.
- Fixed: server global usings were still broader than necessary; single-feature dependencies now live in the files that use them.
- Confirmed: removed Inspections, TUS upload flow, IdentityShowcase, ImageSharp/SixLabors, `ReleaseYear`, and legacy `/Identity/Account/*` references are absent outside this plan.
- Confirmed: `BlazorAutoApp.Client` has no root `Pages` folder; page folders are under feature slices.
- Verified: Debug and Release .NET builds/tests, NuGet outdated/deprecated/vulnerable checks, npm outdated/audit/CSS build, Docker config/build/startup/health, EF migration bundle, deployment audit/render validation, yamllint, actionlint, Dockerized ShellCheck, stale-reference scans, `git diff --check`, and headed Playwright E2E at desktop and mobile viewports all passed on 2026-05-25.
- Note: `git diff --check` reports Git line-ending normalization warnings only, not whitespace errors.

- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 53] `dotnet restore .\BlazorAutoApp.sln`
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 54] `dotnet build .\BlazorAutoApp.sln --no-restore`
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 55] `dotnet test .\BlazorAutoApp.sln --no-build`
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 56] `docker compose config`
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 57] `docker compose up -d --build web`
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 58] Verify the app responds at `https://localhost:7186/health`.
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 59] Run visible Playwright E2E:
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 64] Watch the headed browser enough to confirm the flow is actually behaving, not merely passing invisibly.
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 65] If a phase changes migrations or Docker, also run the EF migration bundle command listed in final verification.
- [x] Tripple checked: [Standard Phase Exit Test Gate, plan line 66] If a phase changes Tailwind/static CSS, also run `npm audit` and the CSS build command.
- [x] Tripple checked: [Phase 0 - Baseline And Template Boundaries, plan line 70] Run the Standard Phase Exit Test Gate before cleanup.
- [x] Tripple checked: [Phase 0 - Baseline And Template Boundaries, plan line 71] Treat migration reset/squash as the default template cleanup path.
- [x] Tripple checked: [Phase 0 - Baseline And Template Boundaries, plan line 75] Keep cleanup commits scoped by area:
- [x] Tripple checked: [Phase 0 - Baseline And Template Boundaries, plan line 81] Keep the cleanup template-friendly:
- [x] Tripple checked: [Phase 0 Testing Gate, plan line 89] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 0 Testing Gate, plan line 90] Record any failing baseline behavior before touching code, so later cleanup does not hide pre-existing issues.
- [x] Tripple checked: [Phase 1 - Remove Current Stale Leftovers, plan line 95] Reset old EF migration history to the current template schema.
- [x] Tripple checked: [Phase 1 - Remove Current Stale Leftovers, plan line 100] Remove stale static image/test assets.
- [x] Tripple checked: [Phase 1 - Remove Current Stale Leftovers, plan line 105] Remove local ignored upload runtime residue.
- [x] Tripple checked: [Phase 1 - Remove Current Stale Leftovers, plan line 110] Remove old app branding.
- [x] Tripple checked: [Phase 1 - Remove Current Stale Leftovers, plan line 115] Clean empty and stale folders.
- [x] Tripple checked: [Phase 1 Testing Gate, plan line 122] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 1 Testing Gate, plan line 123] If migrations were reset, verify a fresh database can be created and migrated from zero.
- [x] Tripple checked: [Phase 1 Testing Gate, plan line 124] Confirm Movies still loads as the home page after deleting stale assets.
- [x] Tripple checked: [Phase 1 Testing Gate, plan line 125] Confirm visible E2E covers home render mode, Movies navigation, and Identity register/login.
- [x] Tripple checked: [Phase 2 - Identity Cleanup, plan line 130] Remove Identity UI package-era leftovers from app code.
- [x] Tripple checked: [Phase 2 - Identity Cleanup, plan line 137] Make the email story explicit.
- [x] Tripple checked: [Phase 2 - Identity Cleanup, plan line 142] Keep the current account UI grouped under the login feature.
- [x] Tripple checked: [Phase 2 - Identity Cleanup, plan line 147] Remove legacy Identity redirect endpoints.
- [x] Tripple checked: [Phase 2 Testing Gate, plan line 154] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 2 Testing Gate, plan line 155] In visible E2E, watch register, logout, login, account manage, and any password/email pages touched by the phase.
- [x] Tripple checked: [Phase 2 Testing Gate, plan line 156] Verify E2E and docs use `/Account/*` only.
- [x] Tripple checked: [Phase 2 Testing Gate, plan line 157] Verify no template UI links to `/Identity/Account/*`.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 162] Split `Program.cs` into clearer composition pieces.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 172] Remove compatibility flags or shims that are not needed for a modern .NET 10 app.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 177] Replace direct environment-variable string assembly with typed configuration.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 182] Remove the EF pending-model warning suppression if possible.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 187] Review EF registration lifetimes.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 192] Remove unnecessary package pins after verification.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 197] Revisit startup migrations and dev role seeding.
- [x] Tripple checked: [Phase 3 - Program, Configuration, And EF Modernization, plan line 204] Rename stale test collection names.
- [x] Tripple checked: [Phase 3 Testing Gate, plan line 211] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 3 Testing Gate, plan line 212] Run the EF migration bundle command.
- [x] Tripple checked: [Phase 3 Testing Gate, plan line 213] Verify `docker compose up -d --build web` starts from a clean app process.
- [x] Tripple checked: [Phase 3 Testing Gate, plan line 214] In visible E2E, specifically watch first load, hydration, Movies CRUD, and Identity login after the composition/config changes.
- [x] Tripple checked: [Phase 4 - Frontend And Static Asset Cleanup, plan line 219] Consolidate the Tailwind pipeline.
- [x] Tripple checked: [Phase 4 - Frontend And Static Asset Cleanup, plan line 231] Remove stale scoped CSS from the old template shell.
- [x] Tripple checked: [Phase 4 - Frontend And Static Asset Cleanup, plan line 238] Normalize Identity UI styling.
- [x] Tripple checked: [Phase 4 - Frontend And Static Asset Cleanup, plan line 243] Remove unused client configuration if confirmed unused.
- [x] Tripple checked: [Phase 4 Testing Gate, plan line 250] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 4 Testing Gate, plan line 251] Run `npm audit` in `BlazorAutoApp.Client`.
- [x] Tripple checked: [Phase 4 Testing Gate, plan line 252] Run the CSS build command after `css:build` exists.
- [x] Tripple checked: [Phase 4 Testing Gate, plan line 253] Watch headed E2E on desktop-sized viewport and manually inspect mobile layout as part of the visible browser pass.
- [x] Tripple checked: [Phase 4 Testing Gate, plan line 254] Confirm render-mode diagnostics remain visible and correct on the Movies home page.
- [x] Tripple checked: [Phase 5 - Docker, CI, Deployment, And Secrets Hygiene, plan line 259] Fix Docker ignore drift.
- [x] Tripple checked: [Phase 5 - Docker, CI, Deployment, And Secrets Hygiene, plan line 264] Modernize `docker-compose.yml`.
- [x] Tripple checked: [Phase 5 - Docker, CI, Deployment, And Secrets Hygiene, plan line 275] Review tracked Ansible vault material without breaking the existing deployment.
- [x] Tripple checked: [Phase 5 - Docker, CI, Deployment, And Secrets Hygiene, plan line 280] Restore and preserve the existing LocalCluster deployment workflow.
- [x] Tripple checked: [Phase 5 - Docker, CI, Deployment, And Secrets Hygiene, plan line 286] Undo the accidental deployment destruction and double-check no valuable deployment workflow was lost.
- [x] Tripple checked: [Phase 5 - Docker, CI, Deployment, And Secrets Hygiene, plan line 293] Expand dependency automation.
- [x] Tripple checked: [Phase 5 - Docker, CI, Deployment, And Secrets Hygiene, plan line 298] Add CI checks for frontend tooling if Tailwind output is generated.
- [x] Tripple checked: [Phase 5 Testing Gate, plan line 304] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 5 Testing Gate, plan line 305] Run `docker build -f BlazorAutoApp/Dockerfile .` directly.
- [x] Tripple checked: [Phase 5 Testing Gate, plan line 306] Confirm Docker app startup logs show migrations/configuration behavior clearly.
- [x] Tripple checked: [Phase 5 Testing Gate, plan line 307] Confirm visible E2E runs against the Docker-hosted app, not a stale local `dotnet run` process.
- [x] Tripple checked: [Phase 6 - Documentation, Plans, And Rate Limiting, plan line 312] Remove `Plans/GoogleLoginGuideThatNeedsFinishing.md`.
- [x] Tripple checked: [Phase 6 - Documentation, Plans, And Rate Limiting, plan line 317] Implement rate limiting, then remove `Plans/RateLimiting.md`.
- [x] Tripple checked: [Phase 6 - Documentation, Plans, And Rate Limiting, plan line 322] Refresh README, overview, local workflow, and testing docs as a set.
- [x] Tripple checked: [Phase 6 Testing Gate, plan line 333] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 6 Testing Gate, plan line 334] If rate limiting is implemented, add behavior tests for representative `429` responses without making local E2E flaky.
- [x] Tripple checked: [Phase 6 Testing Gate, plan line 335] Confirm headed E2E still passes under normal human-paced flows.
- [x] Tripple checked: [Phase 6 Testing Gate, plan line 336] Manually follow README and TESTING commands from a clean shell as a doc smoke test.
- [x] Tripple checked: [Phase 7 - Final Verification Without Product Guardrails, plan line 341] Keep tests focused on current template behavior.
- [x] Tripple checked: [Phase 7 - Final Verification Without Product Guardrails, plan line 346] Keep useful targeted behavior tests.
- [x] Tripple checked: [Phase 7 - Final Verification Without Product Guardrails, plan line 353] Run final one-time cleanup scans for this repository.
- [x] Tripple checked: [Phase 7 Testing Gate, plan line 360] Complete the Standard Phase Exit Test Gate.
- [x] Tripple checked: [Phase 7 Testing Gate, plan line 361] Run the EF migration bundle command:
- [x] Tripple checked: [Phase 7 Testing Gate, plan line 363] Run npm checks:
- [x] Tripple checked: [Phase 7 Testing Gate, plan line 367] Run visible Playwright E2E one final time and watch the browser flow.
- [x] Tripple checked: [Phase 7 Testing Gate, plan line 368] Confirm `git status --short` contains only intentional changes.
- [x] Tripple checked: [Done Criteria, plan line 373] The current repo no longer ships accidental leftovers from removed features.
- [x] Tripple checked: [Done Criteria, plan line 374] Old migration history is reset for template use.
- [x] Tripple checked: [Done Criteria, plan line 375] Legacy `/Identity/Account/*` compatibility redirects are removed.
- [x] Tripple checked: [Done Criteria, plan line 376] Home page is Movies-first and template-appropriate.
- [x] Tripple checked: [Done Criteria, plan line 377] Identity is real authentication/account management only, grouped under the login feature in this repo.
- [x] Tripple checked: [Done Criteria, plan line 378] Program/config/EF setup is understandable and modern for .NET 10.
- [x] Tripple checked: [Done Criteria, plan line 379] Static assets and CSS have one clear pipeline.
- [x] Tripple checked: [Done Criteria, plan line 380] Rate limiting is implemented and documented without an unfinished plan file.
- [x] Tripple checked: [Done Criteria, plan line 381] The existing encrypted LocalCluster Ansible vault file is restored because this repository's deployment flow uses it.
- [x] Tripple checked: [Done Criteria, plan line 382] Docs match the app people will actually run.
- [x] Tripple checked: [Done Criteria, plan line 383] CI and local test docs cover .NET, npm/Tailwind, Docker config, integration tests, and visible Playwright E2E.
- [x] Tripple checked: [Done Criteria, plan line 384] No permanent guardrails prevent future forks from intentionally adding new domains, uploads, images, or capabilities.
- [x] Tripple checked: [Review Evidence, plan line 394] `dotnet package list --project .\BlazorAutoApp.sln --outdated` reports no package updates.
- [x] Tripple checked: [Review Evidence, plan line 395] `dotnet package list --project .\BlazorAutoApp.sln --deprecated` reports no deprecated packages.
- [x] Tripple checked: [Review Evidence, plan line 396] `dotnet package list --project .\BlazorAutoApp.sln --vulnerable --include-transitive` reports no vulnerable packages.
- [x] Tripple checked: [Review Evidence, plan line 397] `npm outdated` in `BlazorAutoApp.Client` reports no outdated npm packages.
- [x] Tripple checked: [Review Evidence, plan line 398] `npm audit` in `BlazorAutoApp.Client` reports zero vulnerabilities.
- [x] Tripple checked: [Review Evidence, plan line 399] `bash Deployment/LocalCluster/Scripts/audit-deployment.sh` passes.
- [x] Tripple checked: [Review Evidence, plan line 400] `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh` passes.
- [x] Tripple checked: [Review Evidence, plan line 401] `docker compose config --quiet` passes for the local root Compose file.
- [x] Tripple checked: [Review Evidence, plan line 402] `docker compose -f Deployment/LocalCluster/compose/node-db/docker-compose.yml config --quiet` parses, but warns when deployment env vars are absent.
- [x] Tripple checked: [Review Evidence, plan line 403] `docker compose -f Deployment/LocalCluster/compose/app-server/docker-compose.yml config --quiet` fails when run bare because required deployment env vars are absent. That is acceptable only if the deployment docs/scripts always generate and load the env file before validation.
- [x] Tripple checked: [Review Evidence, plan line 404] Docker build context probe shows a small context, but `.dockerignore` still has a broad `!docker/**` include while `docker/https/aspnetapp.pfx` exists locally.
- [x] Tripple checked: [Review Evidence, plan line 405] Targeted scans found remaining template issues worth reviewing: all-forwarded-header trust, query string logging, local moving Docker tags, Bootstrap Identity leftovers, hidden `ReleaseYear` drift, broad global usings, environment-variable mutation in tests, and a few docs/tooling consistency gaps.
- [x] Tripple checked: [Priority Order, plan line 411] First priority: deployment preservation and security defaults.
- [x] Tripple checked: [Priority Order, plan line 412] Second priority: local development reproducibility and .NET 10 repo hygiene.
- [x] Tripple checked: [Priority Order, plan line 413] Third priority: Movies/Identity polish and broader visible E2E coverage.
- [x] Tripple checked: [Priority Order, plan line 414] Fourth priority: docs, onboarding, and final clean-clone acceptance.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 418] Treat `Deployment/LocalCluster` and `.github/workflows/cd-localcluster.yml` as template-owned assets.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 423] Expand `.gitattributes` beyond `*.sh text eol=lf` if needed.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 428] Add `shellcheck` coverage for deployment shell scripts.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 432] Add `actionlint` coverage for `.github/workflows/*.yml`.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 436] Review CI runner image pinning.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 441] Review Dependabot coverage for deployment Docker files and Compose files.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 446] Review Dependabot auto-merge policy.
- [x] Tripple checked: [Phase 8 - Deployment Preservation And CD Quality, plan line 452] Add deployment artifact checks to docs.
- [x] Tripple checked: [Phase 8 Testing Gate, plan line 458] Do full testing.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 464] Replace trust-all forwarded headers with configured proxy trust.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 470] Add tests for forwarded-header trust boundaries.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 475] Stop logging raw query strings by default.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 481] Add typed options validation for security-sensitive settings.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 485] Review rate limiting defaults and partitioning.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 490] Harden Data Protection key handling.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 495] Replace startup `Console.WriteLine` for Data Protection certificate failures.
- [x] Tripple checked: [Phase 9 - Security, Headers, Logging, And Secrets, plan line 500] Clarify dev-only secrets.
- [x] Tripple checked: [Phase 9 Testing Gate, plan line 506] Full testing
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 511] Bind local infrastructure ports to loopback by default.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 516] Pin or deliberately manage local Docker image tags.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 521] Tighten `.dockerignore` around local certificates and secrets.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 526] Review Docker build context with an intentional command.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 529] Review root Dockerfile input assumptions.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 533] Make local setup scripts idempotent.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 537] Expand `docker/local-status.py`.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 541] Document and test port conflict behavior.
- [x] Tripple checked: [Phase 10 - Local Development And Docker, plan line 545] Clarify `/app/Storage` ownership.
- [x] Tripple checked: [Phase 10 Testing Gate, plan line 552] Run `docker compose config --quiet`.
- [x] Tripple checked: [Phase 10 Testing Gate, plan line 553] Run `docker compose up -d --build`.
- [x] Tripple checked: [Phase 10 Testing Gate, plan line 554] Verify `https://localhost:7186/health/live` and `/health/ready`.
- [x] Tripple checked: [Phase 10 Testing Gate, plan line 555] Verify Seq receives logs if Seq is enabled.
- [x] Tripple checked: [Phase 10 Testing Gate, plan line 556] Verify Redis and Postgres health checks.
- [x] Tripple checked: [Phase 10 Testing Gate, plan line 557] Run visible Playwright E2E against the Docker-hosted app.
- [x] Tripple checked: [Phase 10 Testing Gate, plan line 558] Stop the stack and confirm volumes/data behavior is documented.
- [x] Tripple checked: [Phase 11 - .NET 10 Build, Solution, And Dependency Hygiene, plan line 563] Add `Directory.Packages.props` for centralized NuGet versions.
- [x] Tripple checked: [Phase 11 - .NET 10 Build, Solution, And Dependency Hygiene, plan line 567] Add `Directory.Build.props` for repo-wide build defaults.
- [x] Tripple checked: [Phase 11 - .NET 10 Build, Solution, And Dependency Hygiene, plan line 571] Review `BlazorDisableThrowNavigationException`.
- [x] Tripple checked: [Phase 11 - .NET 10 Build, Solution, And Dependency Hygiene, plan line 575] Review `RequiresAspNetWebAssets`.
- [x] Tripple checked: [Phase 11 - .NET 10 Build, Solution, And Dependency Hygiene, plan line 579] Keep package check commands current in docs.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 585] Run `dotnet restore`.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 586] Run `dotnet build --configuration Release --no-restore`.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 587] Run `dotnet test --configuration Release --no-build`.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 588] Run `dotnet package list --project .\BlazorAutoApp.sln --outdated`.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 589] Run `dotnet package list --project .\BlazorAutoApp.sln --deprecated`.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 590] Run `dotnet package list --project .\BlazorAutoApp.sln --vulnerable --include-transitive`.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 591] Run `npm ci`, `npm audit`, and `npm run css:build`.
- [x] Tripple checked: [Phase 11 Testing Gate, plan line 592] Run visible Playwright E2E after any render-mode or project-property change.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 597] Align `settings.defaults.json` with actual configuration binding.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 602] Fix placeholder type mismatches.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 607] Prefer options validation over manual scattered validation.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 611] Clarify `ConnectionStrings:DefaultConnection` versus `Database:*`.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 616] Review startup migrations by environment.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 620] Add cancellation tokens through Movies endpoints and service calls.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 624] Log cache invalidation failures.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 629] Review HybridCache usage and serializer expectations.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 633] Review health check response shape.
- [x] Tripple checked: [Phase 12 - Configuration, EF, Caching, And Health, plan line 638] Review EF model source of truth.
- [x] Tripple checked: [Phase 12 Testing Gate, plan line 645] Run tests with Redis disabled.
- [x] Tripple checked: [Phase 12 Testing Gate, plan line 646] Run local Docker with Redis enabled.
- [x] Tripple checked: [Phase 12 Testing Gate, plan line 647] Run migration bundle generation.
- [x] Tripple checked: [Phase 12 Testing Gate, plan line 648] Run health checks for live and ready paths.
- [x] Tripple checked: [Phase 12 Testing Gate, plan line 649] Run Movies integration tests after cache/config changes.
- [x] Tripple checked: [Phase 12 Testing Gate, plan line 650] Run deployment audit after config key changes.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 655] Verify all login/account server code stays under `BlazorAutoApp/Features/Login`.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 659] Decide whether `BlazorAutoApp.Client/Features/Login/Components/RedirectToLogin.razor` is the right client-side location.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 663] Remove Bootstrap leftovers from Identity components.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 668] Review account CSS for old framework residue.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 672] Review passkey support end to end.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 676] Expand Identity visible E2E coverage.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 680] Review account status-cookie messages.
- [x] Tripple checked: [Phase 13 - Identity Feature Quality, plan line 684] Confirm only canonical `/Account/*` routes remain.
- [x] Tripple checked: [Phase 13 Testing Gate, plan line 690] Run Identity unit/integration tests.
- [x] Tripple checked: [Phase 13 Testing Gate, plan line 691] Run visible Playwright E2E for register/login/logout/manage.
- [x] Tripple checked: [Phase 13 Testing Gate, plan line 692] Test forgot password behavior with the chosen local email approach.
- [x] Tripple checked: [Phase 13 Testing Gate, plan line 693] Test passkey page behavior on HTTPS.
- [x] Tripple checked: [Phase 13 Testing Gate, plan line 694] Search for Bootstrap leftovers and legacy Identity routes.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 699] Fix client 404 semantics for `GetByIdAsync`.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 704] Decide what to do with `ReleaseYear`.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 709] Improve empty state on the Movies home page.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 713] Add delete confirmation or undo behavior.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 717] Avoid raw exception messages in UI.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 722] Standardize API error responses.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 727] Add cancellation tokens to API endpoints.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 730] Review "Back" navigation behavior in details/edit pages.
- [x] Tripple checked: [Phase 14 - Movies Feature And API Polish, plan line 734] Add fuller Movies visible E2E.
- [x] Tripple checked: [Phase 14 Testing Gate, plan line 740] Run Movies integration tests.
- [x] Tripple checked: [Phase 14 Testing Gate, plan line 741] Run visible Playwright Movies E2E against local `dotnet run`.
- [x] Tripple checked: [Phase 14 Testing Gate, plan line 742] Run visible Playwright Movies E2E against Docker-hosted app.
- [x] Tripple checked: [Phase 14 Testing Gate, plan line 743] Verify API 404s remain API responses and do not render Blazor not-found pages.
- [x] Tripple checked: [Phase 14 Testing Gate, plan line 744] Verify generated migration/model snapshot if `ReleaseYear` changes.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 749] Keep the homepage Movies-first.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 752] Keep render-mode visibility on the homepage.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 757] Test render-mode transitions explicitly.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 761] Review PersistentState usage.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 765] Keep Client folder sliced.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 769] Reduce UI coupling from global imports.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 773] Review visual design consistency.
- [x] Tripple checked: [Phase 15 - Blazor Auto Render Modes And Frontend Structure, plan line 778] Verify text/layout fit on mobile and desktop.
- [x] Tripple checked: [Phase 15 Testing Gate, plan line 784] Run visible Playwright E2E at desktop viewport.
- [x] Tripple checked: [Phase 15 Testing Gate, plan line 785] Run visible Playwright E2E at mobile viewport.
- [x] Tripple checked: [Phase 15 Testing Gate, plan line 786] Capture screenshots for homepage, Movies create/details/edit, login/register, account manage, and not-found.
- [x] Tripple checked: [Phase 15 Testing Gate, plan line 787] Verify no `BlazorAutoApp.Client/Pages` folder exists.
- [x] Tripple checked: [Phase 15 Testing Gate, plan line 788] Verify render-mode badge transitions from prerender/static to interactive.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 793] Keep Playwright visible by default for local E2E.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 797] Add Playwright trace/video strategy.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 802] Replace broad `NetworkIdle` waits where they can be flaky.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 807] Isolate `WebAppFactory` configuration.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 812] Clean stale comments in test infrastructure.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 816] Pin or manage Testcontainers images.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 821] Make rate limiting tests deterministic.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 826] Exclude generated folders from source-search helper.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 830] Review architecture tests for fork-friendliness.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 835] Add deployment quality checks to the test docs.
- [x] Tripple checked: [Phase 16 - Test Suite Reliability And Coverage, plan line 839] Add end-to-end phase testing after each future phase.
- [x] Tripple checked: [Phase 16 Testing Gate, plan line 845] Run full `dotnet test`.
- [x] Tripple checked: [Phase 16 Testing Gate, plan line 846] Run visible Playwright E2E with the browser open.
- [x] Tripple checked: [Phase 16 Testing Gate, plan line 847] Run visible Playwright E2E against Docker-hosted app.
- [x] Tripple checked: [Phase 16 Testing Gate, plan line 848] Run test suite twice to catch order/env leakage.
- [x] Tripple checked: [Phase 16 Testing Gate, plan line 849] Inspect `TestResults/Playwright` artifacts after an intentional or real failure.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 854] Refresh README after the second cleanup pass.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 858] Consider a root `TESTING.md` or link clearly to `BlazorAutoApp.Test/TESTING.md`.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 861] Update `HowToRunLocally.md`.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 865] Update `overview.md`.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 869] Update deployment docs after any deployment workflow change.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 873] Add a template customization guide.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 877] Document app name configuration.
- [x] Tripple checked: [Phase 17 - Documentation And Onboarding, plan line 882] Remove stale comments from `.gitignore` or simplify it.
- [x] Tripple checked: [Phase 17 Testing Gate, plan line 888] Follow README from a clean shell.
- [x] Tripple checked: [Phase 17 Testing Gate, plan line 889] Follow `HowToRunLocally.md` from a clean shell.
- [x] Tripple checked: [Phase 17 Testing Gate, plan line 890] Follow visible E2E docs exactly.
- [x] Tripple checked: [Phase 17 Testing Gate, plan line 891] Follow deployment validation docs without deploying.
- [x] Tripple checked: [Phase 17 Testing Gate, plan line 892] Search docs for stale feature names, old routes, old .NET versions, and unfinished-plan language.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 897] Run full dependency checks.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 902] Run full .NET checks.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 905] Run full frontend checks.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 908] Run full local Docker checks.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 911] Run full deployment checks.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 914] Run visible browser walkthrough.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 919] Review security-sensitive logs manually.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 922] Review `git status --short`.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 925] Review `git diff`.
- [x] Tripple checked: [Phase 18 - Final Acceptance Before People Use It, plan line 928] Tag the guide with final status.
- [x] Tripple checked: [Phase 18 Testing Gate, plan line 933] Final status: completed on 2026-05-24.
