# Update To Newest .NET And Dependencies Plan

Research snapshot: 2026-05-24.

Goal: move this repo from the current .NET 9 stack to the newest production-stable .NET stack, update direct NuGet packages and deployment/runtime dependencies, and prove the result through local tests, container build, CI, and LocalCluster CD acceptance.

## Execution Notes - 2026-05-24

Executed on branch `update-dotnet-10`.

Completed locally:

- Confirmed the official .NET release metadata target for this pass remains .NET 10 LTS with SDK `10.0.300` and runtime `10.0.8`.
- Retargeted the app, client, core, and test projects to `net10.0`.
- Fixed `global.json` to pin SDK `10.0.300`, disable prerelease SDK selection, and prevent latest-major roll-forward.
- Updated Microsoft, ASP.NET Core, EF Core, Npgsql, Serilog, tusdotnet, test infrastructure, CI setup-dotnet, `dotnet-ef`, and Docker app images to the .NET 10 package/tooling band.
- Removed unused direct EF SQL Server and SQLite provider references after code search found no `UseSqlServer` or `UseSqlite` usage.
- Added direct private NuGet package overrides for `NuGet.Packaging` and `NuGet.Protocol` to eliminate the transitive low-severity advisory introduced by code generation tooling.
- Migrated tests from legacy `xunit` 2.x to `xunit.v3` `3.2.2`; kept `xunit.runner.visualstudio` `3.1.5`.
- Built the EF migration bundle for `linux-x64`.
- Rebuilt and started the local Docker Compose stack, verified `/health/ready`, verified the login page returns `200 OK`, and confirmed clean web logs.
- Ran deployment audit, rendered template validation, deployment summary, local status, package vulnerability scan, generated artifact tracking check, and secret/audit scan.

Deferred or externally gated:

- `SixLabors.ImageSharp` `4.0.0` was tested and deferred because the app build fails without the new Six Labors license configuration required by ImageSharp 4. The app and tests are pinned to current 3.x `3.1.12`.
- PostgreSQL and Redis major image upgrades remain deferred as planned; production-like data containers were not major-upgraded as part of the .NET migration.
- Ansible was later installed in a side-by-side Ubuntu 24.04 WSL 2 distro on this Windows 10 developer machine, and local `ansible-inventory` parsing passed. This machine is not the LocalCluster control PC from `HowToDeployLocalCluster.md`, so production SSH/vault/node checks were intentionally not treated as required local upgrade gates.
- CI, CD, `preflight.sh deploy`, and `acceptance-check.sh` still need to run in their intended environments. `preflight.sh deploy` and `acceptance-check.sh` are control-machine/CD-runner checks because they decrypt the vault, use the deploy key, SSH to the nodes, inspect ports, and verify live services.

## Recommendation

Use .NET 10 LTS as the upgrade target.

Do not target .NET 11 preview for this app unless the explicit goal is preview testing. Official .NET metadata currently lists .NET 11 as preview, while .NET 10 is active LTS with latest runtime `10.0.8`, latest SDK `10.0.300`, and end of support `2028-11-14`.

Baseline repo facts before execution:

| Area | Current state | Target / action |
| --- | --- | --- |
| App target frameworks | `net9.0` in app, client, core, and test projects | `net10.0` everywhere |
| `global.json` | Invalid SDK version `10.0.0`, `rollForward: latestMajor`, `allowPrerelease: true` | Pin valid SDK `10.0.300`, use non-preview roll-forward |
| Local installed SDK | `10.0.202` installed here | Install/use `10.0.300` or let CI install latest `10.0.x` |
| CI .NET setup | `actions/setup-dotnet@v4`, `dotnet-version: 9.0.x` | `actions/setup-dotnet@v5`, `dotnet-version: 10.0.x` |
| Docker app images | `mcr.microsoft.com/dotnet/aspnet:9.0`, `sdk:9.0` | `aspnet:10.0`, `sdk:10.0` |
| EF tool | `dotnet-ef` `9.0.12` | `10.0.8` |
| Cloudflared | `2026.5.0` | Already latest from GitHub latest release check |
| GitHub runner script | Dynamically pulls latest `actions/runner` | Keep behavior; latest observed `v2.334.0` |
| Local Postgres | `postgres:16-alpine` | Consider `postgres:17-alpine` after backup/restore validation |
| LocalCluster Postgres | `postgres:16.14-alpine3.23` | Keep during .NET upgrade; plan DB major separately |
| Redis local | `redis:7-alpine` | Consider `redis:8-alpine` after app tests |
| LocalCluster Redis | `redis:7.4.9-alpine3.21` | Keep during .NET upgrade; plan Redis major separately |

## Source Of Truth Checks

- [x] Confirm official .NET release metadata still says .NET 10 is the latest stable/LTS channel before executing.
- [x] Confirm `https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json` still lists latest .NET 10 SDK/runtime targets.
- [x] Run `dotnet list BlazorAutoApp.sln package --outdated` again immediately before edits.
- [x] Run `dotnet --info` and confirm the active SDK is valid and compatible.
- [x] Decide whether this pass includes only app/.NET dependencies or also database/Redis major upgrades.

Recommended scope for first execution:

- [x] Update .NET SDK, target frameworks, Microsoft packages, EF provider/tool, test packages, Docker app images, and CI.
- [x] Do not upgrade PostgreSQL major, Redis major, or local-only observability images in the same pass unless the .NET upgrade is already green.

## Phase 1 - Baseline Before Changing Anything

- [x] Create a branch named `update-dotnet-10`.
- [x] Record `git status --short --untracked-files=all`.
- [x] Run `dotnet --info`.
- [x] Run `dotnet restore`.
- [x] Run `dotnet build --configuration Release --no-restore`.
- [x] Run `dotnet test --configuration Release --no-build`.
- [x] Run `dotnet tool restore`.
- [x] Run `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`.
- [x] Run `docker build -f BlazorAutoApp/Dockerfile -t blazorautoapp-update-baseline .`.
- [x] Run `bash Deployment/LocalCluster/Scripts/audit-deployment.sh`.
- [x] Run `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh`.
- [x] Save any current failures separately; do not mix existing failures with upgrade regressions.

## Phase 2 - Fix SDK Pinning First

Reason: `global.json` currently has an invalid SDK version and allows prerelease/latest-major roll-forward. That is risky because a machine with .NET 11 preview installed could silently build the app with preview tooling.

- [x] Change `global.json` SDK version from `10.0.0` to `10.0.300`.
- [x] Set `allowPrerelease` to `false`.
- [x] Change `rollForward` from `latestMajor` to either `latestFeature` or `latestPatch`.
- [x] Preferred default: `latestFeature`, because it permits future .NET 10 feature-band SDKs while blocking .NET 11.
- [x] Re-run `dotnet --info` and confirm `global.json` is valid.
- [x] If local SDK `10.0.300` is missing, install it or temporarily use CI for final proof.

Acceptance gate:

- [x] `dotnet --info` no longer reports invalid `global.json`.
- [x] `dotnet restore` succeeds.

## Phase 3 - Retarget Projects To .NET 10

Files:

- [x] `BlazorAutoApp/BlazorAutoApp.csproj`
- [x] `BlazorAutoApp.Client/BlazorAutoApp.Client.csproj`
- [x] `BlazorAutoApp.Core/BlazorAutoApp.Core.csproj`
- [x] `BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`

Changes:

- [x] Replace every `<TargetFramework>net9.0</TargetFramework>` with `<TargetFramework>net10.0</TargetFramework>`.
- [x] Check for implicit language-version changes and warnings.
- [x] Keep nullable and implicit usings as-is.

Acceptance gate:

- [x] `rg -n "net9.0|dotnet-version: 9.0|aspnet:9.0|sdk:9.0" .` only finds intentional historical notes, or finds nothing.
- [x] `dotnet restore` succeeds.

## Phase 4 - Update Microsoft, ASP.NET, EF, And Tooling Packages

Use one coherent .NET 10 package band. Avoid mixed `9.x`/`10.x` Microsoft packages unless a package has no .NET 10 release.

Direct package targets from `dotnet list package --outdated`:

| Package | Current | Target |
| --- | --- | --- |
| `Microsoft.AspNetCore.Authentication.Google` | `9.0.12` | `10.0.8` |
| `Microsoft.AspNetCore.Components.WebAssembly` | `9.0.8` | `10.0.8` |
| `Microsoft.AspNetCore.Components.WebAssembly.Server` | `9.0.8` | `10.0.8` |
| `Microsoft.AspNetCore.DataProtection.StackExchangeRedis` | `9.0.12` | `10.0.8` |
| `Microsoft.AspNetCore.Identity.EntityFrameworkCore` | `9.0.12` | `10.0.8` |
| `Microsoft.AspNetCore.Identity.UI` | `9.0.12` | `10.0.8` |
| `Microsoft.AspNetCore.Mvc.Testing` | `9.0.12` | `10.0.8` |
| `Microsoft.EntityFrameworkCore` | `9.0.12` | `10.0.8` |
| `Microsoft.EntityFrameworkCore.Design` | `9.0.12` | `10.0.8` |
| `Microsoft.EntityFrameworkCore.Relational` | `9.0.12` | `10.0.8` |
| `Microsoft.EntityFrameworkCore.Sqlite` | `9.0.12` | `10.0.8` |
| `Microsoft.EntityFrameworkCore.SqlServer` | `9.0.12` | `10.0.8` |
| `Microsoft.EntityFrameworkCore.Tools` | `9.0.12` | `10.0.8` |
| `Microsoft.Extensions.Caching.Hybrid` | `9.3.0` | `10.6.0` |
| `Microsoft.Extensions.Caching.StackExchangeRedis` | `9.0.8` | `10.0.8` |
| `Microsoft.VisualStudio.Web.CodeGeneration.Design` | `9.0.12` | `10.0.2` |
| `Npgsql.EntityFrameworkCore.PostgreSQL` | `9.0.4` | `10.0.1` |
| local tool `dotnet-ef` | `9.0.12` | `10.0.8` |

Steps:

- [x] Update package references in the app, client, and test projects.
- [x] Update `.config/dotnet-tools.json` to `dotnet-ef` `10.0.8`.
- [x] Run `dotnet tool restore`.
- [x] Run `dotnet restore`.
- [x] Run `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`.
- [x] Build the EF migration bundle locally:
  `dotnet ef migrations bundle --project BlazorAutoApp/BlazorAutoApp.csproj --startup-project BlazorAutoApp/BlazorAutoApp.csproj --configuration Release --self-contained --runtime linux-x64 --output artifacts/migrations/test-migrate`

Risks to inspect:

- [x] EF Core 10 model snapshot and SQL generation changes.
- [x] Npgsql provider behavior changes for PostgreSQL.
- [x] Identity UI and authentication package behavior changes.
- [x] Hybrid cache API changes.
- [x] WebAssembly static asset behavior changes.

Acceptance gate:

- [x] No mixed Microsoft `9.x` packages remain in direct references.
- [x] EF migrations list succeeds.
- [x] Migration bundle builds.

## Phase 5 - Update Third-Party Packages Deliberately

Direct package targets from current NuGet data:

| Package | Current | Target | Risk |
| --- | --- | --- | --- |
| `Bogus` | `35.6.3` | `35.6.5` | Low |
| `Serilog.AspNetCore` | `9.0.0` | `10.0.0` | Medium |
| `Serilog.Settings.Configuration` | `9.0.0` | `10.0.0` | Medium |
| `Serilog.Sinks.Console` | `6.0.0` | `6.1.1` | Low |
| `Serilog.Sinks.Seq` | `9.0.0` | `9.1.0` | Low |
| `SixLabors.ImageSharp` | `3.1.11` | `4.0.0` | High, major image-processing upgrade |
| `tusdotnet` | `2.10.0` | `2.11.1` | Low/medium |
| `Microsoft.NET.Test.Sdk` | `17.11.1` | `18.5.1` | Medium |
| `Respawn` | `6.2.1` | `7.0.0` | Medium/high, major test reset upgrade |
| `Testcontainers` | `4.7.0` | `4.12.0` | Medium |
| `Testcontainers.PostgreSql` | `4.7.0` | `4.12.0` | Medium |
| `xunit` | `2.9.2` | `xunit.v3` `3.2.2` | Medium, package migration |
| `xunit.runner.visualstudio` | `2.8.2` | `3.1.5` | Medium/high, runner major upgrade |

Recommended order:

- [x] First update low-risk patch/minor packages.
- [x] Then update test infrastructure packages and run all tests.
- [x] Attempt ImageSharp `4.0.0` and run image upload/processing tests carefully; deferred 4.0.0 because it requires Six Labors license configuration, kept `3.1.12`, and added thumbnail endpoint coverage.
- [x] Keep any package that breaks tests temporarily pinned and document why.

Acceptance gate:

- [x] `dotnet list BlazorAutoApp.sln package --outdated` has no direct updates left, except intentionally deferred packages with notes.
- [x] No vulnerable package warnings appear during restore/build.

## Phase 6 - Consider Package Management Cleanup

The repo currently repeats package versions across project files. This can drift during a large upgrade.

- [x] Decide whether to introduce `Directory.Packages.props`.
- [x] If introduced, move direct package versions into one central file. Not introduced in this pass.
- [x] Keep `<PrivateAssets>` and `<IncludeAssets>` metadata in project files where needed.
- [x] Do this only after the .NET 10 upgrade is green, or in a separate commit, to keep regressions easy to isolate.

Recommended default:

- [x] Do not introduce central package management in the same commit as the .NET 10 migration unless package drift becomes confusing during implementation.

## Phase 7 - Update Docker App Build And Runtime

Files:

- [x] `BlazorAutoApp/Dockerfile`
- [x] `docker-compose.yml`
- [x] `.dockerignore` if build context warnings appear

Changes:

- [x] Change `FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base` to `aspnet:10.0`.
- [x] Change `FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build` to `sdk:10.0`.
- [x] Verify Docker build still restores the web app graph only.
- [x] Confirm `ASPNETCORE_URLS` and exposed ports remain unchanged.

Acceptance gate:

- [x] `docker build -f BlazorAutoApp/Dockerfile -t blazorautoapp-dotnet10 .`
- [x] Local compose starts with `docker compose up -d --build`.
- [x] `curl -k https://localhost:7186/health/ready` succeeds for local Docker, if local cert setup is present.
- [x] App storage volume behavior still works.

## Phase 8 - Update CI/CD Workflows

Files:

- [x] `.github/workflows/ci.yml`
- [x] `.github/workflows/cd-localcluster.yml`

CI changes:

- [x] Update `actions/setup-dotnet@v4` to `actions/setup-dotnet@v5`.
- [x] Update `dotnet-version: 9.0.x` to `10.0.x`.
- [x] Keep restore/build/test order unchanged at first.
- [x] Keep migration bundle build in CI and verify it uses .NET 10.
- [x] Keep Docker image build and GHCR push unchanged except for the Dockerfile base image change.

CD changes:

- [x] Usually no CD workflow change is needed beyond artifact compatibility.
- [ ] Verify the self-hosted runner can run the updated repo and Docker image. External: real self-hosted runner/control environment.
- [x] Ensure CD downloads the migration bundle created by the .NET 10 CI run. Workflow contract reviewed; runtime proof remains in CD.

Acceptance gate:

- [ ] CI passes on pull request. External: requires GitHub Actions run.
- [ ] CI passes on main. External: requires GitHub Actions run after merge.
- [ ] Docker image is pushed to GHCR with the commit SHA. External: requires CI on `main`.
- [ ] Migration bundle artifact exists and is executable after download. External: requires CI artifact and CD download.

## Phase 9 - Audit App Code For .NET 10 Breaking Changes

Search and inspect:

- [x] `Program.cs` startup, auth, Identity, cookies, antiforgery, health checks.
- [x] EF Core `DbContext`, migrations, model snapshot, query warnings.
- [x] Redis cache and Data Protection key persistence.
- [x] Blazor WebAssembly client package/static asset behavior.
- [x] File upload and TUS endpoints.
- [x] Image processing paths using ImageSharp.
- [x] Integration test host setup in `BlazorAutoApp.Test/TestingSetup/WebAppFactory.cs`.

Commands:

- [x] `dotnet build --configuration Release`
- [x] Treat new compiler/analyzer warnings as upgrade findings, not noise.
- [x] Fix real warnings before moving to deployment.

## Phase 10 - Test Matrix

Local fast checks:

- [x] `dotnet restore`
- [x] `dotnet build --configuration Release --no-restore`
- [x] `dotnet test --configuration Release --no-build`
- [x] `dotnet tool restore`
- [x] `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`

Local integration checks:

- [x] Start Docker Desktop.
- [x] Run `docker compose up -d --build`.
- [x] Run `python ./docker/local-status.py`.
- [x] Run app health endpoint checks.
- [x] Exercise login page and Google auth configuration does not crash startup.
- [x] Exercise image upload/thumbnail flow.
- [x] Exercise TUS upload flow.
- [x] Confirm Redis cache and Data Protection do not throw at startup.

Deployment checks:

- [x] `bash Deployment/LocalCluster/Scripts/audit-deployment.sh`
- [x] `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh`
- [x] `bash Deployment/LocalCluster/Scripts/summary.sh`
- [ ] `bash Deployment/LocalCluster/Scripts/preflight.sh deploy` on control machine. External: do not run target-node checks from this Windows developer PC.
- [ ] CI workflow green. External: requires GitHub Actions.
- [ ] CD workflow with migrations enabled. External: requires real self-hosted/control runner.
- [ ] `bash Deployment/LocalCluster/Scripts/acceptance-check.sh`. External: live-node/public-host acceptance check.

## Phase 11 - Database And Migration Safety

Before deploying:

- [ ] Confirm CI produces the .NET 10 migration bundle. External: local bundle and workflow command verified; actual CI artifact requires CI.
- [x] Confirm CD runs pre-migration backup before the bundle. Playbook inspection confirms backup precedes migration bundle execution.
- [x] Confirm no new EF migration is generated unless model changes are intentional.
- [x] If EF reports model changes, inspect them before deployment.

Deployment:

- [ ] Deploy with migrations enabled for the first .NET 10 deployment. External: run from CD/control environment after merge.
- [ ] Verify `/health/ready` after app start. External for production deployment; local Docker health passed.
- [ ] Verify backup file exists on `node-db`. External: requires deployed migration run on node-db.
- [x] If migration fails, stop and restore from backup rather than retrying blindly. Rollback rule remains documented; no migration failure occurred locally.

## Phase 12 - Local Runtime Images After .NET Upgrade

Handle these after the app is green on .NET 10.

Local-only Docker Compose:

- [x] Consider `postgres:17-alpine` for local dev. Considered and deferred; database major upgrades stay separate.
- [x] Consider `redis:8-alpine` for local dev. Considered and deferred; Redis major upgrades stay separate.
- [x] Replace `datalust/seq:latest` with a pinned Seq tag. Considered and deferred as local-only observability image cleanup.
- [x] Replace `redis/redisinsight:latest` with a pinned RedisInsight tag. Considered and deferred as local-only tooling cleanup.

LocalCluster production-like compose:

- [x] Keep `postgres:16.14-alpine3.23` during the .NET upgrade.
- [x] Keep `redis:7.4.9-alpine3.21` during the .NET upgrade.
- [x] Plan PostgreSQL major upgrade as a separate maintenance task with dump/restore or `pg_upgrade` testing.
- [x] Plan Redis major upgrade separately with persistence compatibility checks.

Acceptance gate:

- [x] Local dev compose works after optional local image changes.
- [x] Production LocalCluster data containers are not major-upgraded as a side effect of app dependency updates.

## Phase 13 - Deployment Dependency Review

- [x] Confirm `cloudflared_version` remains current. Latest observed GitHub release was `2026.5.0`, matching `all.yml`.
- [x] Confirm GitHub runner installer still resolves latest `actions/runner`.
- [x] Do not pin GitHub runner in this pass unless reproducibility becomes more important than auto-updating.
- [x] Confirm Caddy install still uses the stable apt repository.
- [x] Confirm Docker apt repository role still uses supported Linux Mint/Ubuntu codename handling.
- [x] Run LocalCluster audit after any deployment script change.

## Phase 14 - Security And Public Repo Review

- [x] Run `rg -n "password|secret|token|eyJ|BEGIN .*PRIVATE|ANSIBLE_VAULT" .`
- [x] Confirm `Deployment/LocalCluster/inventory/prod/vault.yml` is encrypted and safe to commit only if it contains Ansible Vault ciphertext.
- [x] Confirm no local `.env` files are tracked.
- [x] Confirm no Docker build output, migration bundle, or backup file is tracked.
- [x] Confirm package updates do not introduce deprecated/vulnerable package warnings.

## Phase 15 - Rollback Plan

If local build/test fails:

- [x] Revert the smallest package group that caused the failure. Not needed after final green build/test; ImageSharp 4 was the only failed package group and was kept pinned.
- [x] Keep `global.json` fixed if possible, because it is currently invalid.
- [x] Document deferred packages in this file.

If CI fails:

- [x] Compare local SDK version and CI SDK version. `global.json` pins `10.0.300`; CI installs `10.0.x`.
- [x] Check whether `global.json` and `setup-dotnet` disagree. They agree on .NET 10.
- [x] Check migration bundle build first, then Docker build.

If CD fails:

- [x] Do not rerun repeatedly without reading the failing stage.
- [x] If migration failed, use the pre-migration backup path. Rollback rule remains documented; no deployment migration was run here.
- [x] If app health failed, inspect app logs on both app nodes. Rollback rule remains documented; no production app health failure was created here.
- [x] If Caddy/public health failed, run `acceptance-check.sh` manually and inspect its diagnostics. Rollback rule remains documented; no production ingress check was run here.

If production behavior is wrong after deployment:

- [x] Roll back by dispatching CD from the previous known-good commit/image. Rollback rule documented; not executed because no production deployment was run here.
- [x] Restore database only if migrations made incompatible data changes. Rollback rule documented; not executed because no production migration was run here.
- [x] Keep Cloudflare tunnel and runner unchanged unless the failure clearly involves ingress or runner setup.

## Phase 16 - Final Completion Criteria

The update is not done until all of these are true:

- [x] Every project targets `net10.0`.
- [x] `global.json` is valid and blocks preview/latest-major surprise upgrades.
- [x] CI uses .NET 10.
- [x] Docker app image uses .NET 10 SDK/runtime.
- [x] `dotnet-ef` is on the EF 10 line.
- [x] Direct NuGet package updates are either fully current or explicitly deferred with a reason.
- [x] `dotnet restore` passes.
- [x] `dotnet build --configuration Release` passes.
- [x] `dotnet test --configuration Release` passes.
- [x] EF migration bundle builds.
- [x] Docker image builds.
- [x] Deployment audit passes.
- [x] Rendered deployment template validation passes.
- [ ] CI passes. External: requires GitHub Actions.
- [ ] CD passes. External: requires real self-hosted/control runner.
- [ ] `acceptance-check.sh` passes against `shipinspection.jacobgrum.com`. External: live production acceptance gate.
- [x] No secrets or generated artifacts are accidentally included.

## Useful Commands

```bash
dotnet --info
dotnet list BlazorAutoApp.sln package --outdated
dotnet tool restore
dotnet restore
dotnet build --configuration Release --no-restore
dotnet test --configuration Release --no-build
dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp
dotnet ef migrations bundle \
  --project BlazorAutoApp/BlazorAutoApp.csproj \
  --startup-project BlazorAutoApp/BlazorAutoApp.csproj \
  --configuration Release \
  --self-contained \
  --runtime linux-x64 \
  --output artifacts/migrations/test-migrate
docker build -f BlazorAutoApp/Dockerfile -t blazorautoapp-dotnet10 .
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
bash Deployment/LocalCluster/Scripts/acceptance-check.sh
```

## References

- Official .NET release metadata: `https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json`
- Official .NET support policy: `https://dotnet.microsoft.com/en-us/platform/support/policy`
- Official .NET 10 download page: `https://dotnet.microsoft.com/en-us/download/dotnet/10.0`
- ASP.NET Core Docker image guidance: `https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/docker/building-net-docker-images`
- GitHub Actions setup-dotnet: `https://github.com/actions/setup-dotnet`
