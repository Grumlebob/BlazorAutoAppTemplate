# Update To Newest .NET And Dependencies Plan

Research snapshot: 2026-05-24.

Goal: move this repo from the current .NET 9 stack to the newest production-stable .NET stack, update direct NuGet packages and deployment/runtime dependencies, and prove the result through local tests, container build, CI, and LocalCluster CD acceptance.

## Recommendation

Use .NET 10 LTS as the upgrade target.

Do not target .NET 11 preview for this app unless the explicit goal is preview testing. Official .NET metadata currently lists .NET 11 as preview, while .NET 10 is active LTS with latest runtime `10.0.8`, latest SDK `10.0.300`, and end of support `2028-11-14`.

Current repo facts:

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

- [ ] Confirm official .NET release metadata still says .NET 10 is the latest stable/LTS channel before executing.
- [ ] Confirm `https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json` still lists latest .NET 10 SDK/runtime targets.
- [ ] Run `dotnet list BlazorAutoApp.sln package --outdated` again immediately before edits.
- [ ] Run `dotnet --info` and confirm the active SDK is valid and compatible.
- [ ] Decide whether this pass includes only app/.NET dependencies or also database/Redis major upgrades.

Recommended scope for first execution:

- [ ] Update .NET SDK, target frameworks, Microsoft packages, EF provider/tool, test packages, Docker app images, and CI.
- [ ] Do not upgrade PostgreSQL major, Redis major, or local-only observability images in the same pass unless the .NET upgrade is already green.

## Phase 1 - Baseline Before Changing Anything

- [ ] Create a branch named `update-dotnet-10`.
- [ ] Record `git status --short --untracked-files=all`.
- [ ] Run `dotnet --info`.
- [ ] Run `dotnet restore`.
- [ ] Run `dotnet build --configuration Release --no-restore`.
- [ ] Run `dotnet test --configuration Release --no-build`.
- [ ] Run `dotnet tool restore`.
- [ ] Run `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`.
- [ ] Run `docker build -f BlazorAutoApp/Dockerfile -t blazorautoapp-update-baseline .`.
- [ ] Run `bash Deployment/LocalCluster/Scripts/audit-deployment.sh`.
- [ ] Run `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh`.
- [ ] Save any current failures separately; do not mix existing failures with upgrade regressions.

## Phase 2 - Fix SDK Pinning First

Reason: `global.json` currently has an invalid SDK version and allows prerelease/latest-major roll-forward. That is risky because a machine with .NET 11 preview installed could silently build the app with preview tooling.

- [ ] Change `global.json` SDK version from `10.0.0` to `10.0.300`.
- [ ] Set `allowPrerelease` to `false`.
- [ ] Change `rollForward` from `latestMajor` to either `latestFeature` or `latestPatch`.
- [ ] Preferred default: `latestFeature`, because it permits future .NET 10 feature-band SDKs while blocking .NET 11.
- [ ] Re-run `dotnet --info` and confirm `global.json` is valid.
- [ ] If local SDK `10.0.300` is missing, install it or temporarily use CI for final proof.

Acceptance gate:

- [ ] `dotnet --info` no longer reports invalid `global.json`.
- [ ] `dotnet restore` succeeds.

## Phase 3 - Retarget Projects To .NET 10

Files:

- [ ] `BlazorAutoApp/BlazorAutoApp.csproj`
- [ ] `BlazorAutoApp.Client/BlazorAutoApp.Client.csproj`
- [ ] `BlazorAutoApp.Core/BlazorAutoApp.Core.csproj`
- [ ] `BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`

Changes:

- [ ] Replace every `<TargetFramework>net9.0</TargetFramework>` with `<TargetFramework>net10.0</TargetFramework>`.
- [ ] Check for implicit language-version changes and warnings.
- [ ] Keep nullable and implicit usings as-is.

Acceptance gate:

- [ ] `rg -n "net9.0|dotnet-version: 9.0|aspnet:9.0|sdk:9.0" .` only finds intentional historical notes, or finds nothing.
- [ ] `dotnet restore` succeeds.

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

- [ ] Update package references in the app, client, and test projects.
- [ ] Update `.config/dotnet-tools.json` to `dotnet-ef` `10.0.8`.
- [ ] Run `dotnet tool restore`.
- [ ] Run `dotnet restore`.
- [ ] Run `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`.
- [ ] Build the EF migration bundle locally:
  `dotnet ef migrations bundle --project BlazorAutoApp/BlazorAutoApp.csproj --startup-project BlazorAutoApp/BlazorAutoApp.csproj --configuration Release --self-contained --runtime linux-x64 --output artifacts/migrations/test-migrate`

Risks to inspect:

- [ ] EF Core 10 model snapshot and SQL generation changes.
- [ ] Npgsql provider behavior changes for PostgreSQL.
- [ ] Identity UI and authentication package behavior changes.
- [ ] Hybrid cache API changes.
- [ ] WebAssembly static asset behavior changes.

Acceptance gate:

- [ ] No mixed Microsoft `9.x` packages remain in direct references.
- [ ] EF migrations list succeeds.
- [ ] Migration bundle builds.

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
| `xunit` | `2.9.2` | `2.9.3` | Low |
| `xunit.runner.visualstudio` | `2.8.2` | `3.1.5` | Medium/high, runner major upgrade |

Recommended order:

- [ ] First update low-risk patch/minor packages.
- [ ] Then update test infrastructure packages and run all tests.
- [ ] Then update ImageSharp `4.0.0` and run image upload/processing tests carefully.
- [ ] Keep any package that breaks tests temporarily pinned and document why.

Acceptance gate:

- [ ] `dotnet list BlazorAutoApp.sln package --outdated` has no direct updates left, except intentionally deferred packages with notes.
- [ ] No vulnerable package warnings appear during restore/build.

## Phase 6 - Consider Package Management Cleanup

The repo currently repeats package versions across project files. This can drift during a large upgrade.

- [ ] Decide whether to introduce `Directory.Packages.props`.
- [ ] If introduced, move direct package versions into one central file.
- [ ] Keep `<PrivateAssets>` and `<IncludeAssets>` metadata in project files where needed.
- [ ] Do this only after the .NET 10 upgrade is green, or in a separate commit, to keep regressions easy to isolate.

Recommended default:

- [ ] Do not introduce central package management in the same commit as the .NET 10 migration unless package drift becomes confusing during implementation.

## Phase 7 - Update Docker App Build And Runtime

Files:

- [ ] `BlazorAutoApp/Dockerfile`
- [ ] `docker-compose.yml`
- [ ] `.dockerignore` if build context warnings appear

Changes:

- [ ] Change `FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base` to `aspnet:10.0`.
- [ ] Change `FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build` to `sdk:10.0`.
- [ ] Verify Docker build still restores the web app graph only.
- [ ] Confirm `ASPNETCORE_URLS` and exposed ports remain unchanged.

Acceptance gate:

- [ ] `docker build -f BlazorAutoApp/Dockerfile -t blazorautoapp-dotnet10 .`
- [ ] Local compose starts with `docker compose up -d --build`.
- [ ] `curl -k https://localhost:7186/health/ready` succeeds for local Docker, if local cert setup is present.
- [ ] App storage volume behavior still works.

## Phase 8 - Update CI/CD Workflows

Files:

- [ ] `.github/workflows/ci.yml`
- [ ] `.github/workflows/cd-localcluster.yml`

CI changes:

- [ ] Update `actions/setup-dotnet@v4` to `actions/setup-dotnet@v5`.
- [ ] Update `dotnet-version: 9.0.x` to `10.0.x`.
- [ ] Keep restore/build/test order unchanged at first.
- [ ] Keep migration bundle build in CI and verify it uses .NET 10.
- [ ] Keep Docker image build and GHCR push unchanged except for the Dockerfile base image change.

CD changes:

- [ ] Usually no CD workflow change is needed beyond artifact compatibility.
- [ ] Verify the self-hosted runner can run the updated repo and Docker image.
- [ ] Ensure CD downloads the migration bundle created by the .NET 10 CI run.

Acceptance gate:

- [ ] CI passes on pull request.
- [ ] CI passes on main.
- [ ] Docker image is pushed to GHCR with the commit SHA.
- [ ] Migration bundle artifact exists and is executable after download.

## Phase 9 - Audit App Code For .NET 10 Breaking Changes

Search and inspect:

- [ ] `Program.cs` startup, auth, Identity, cookies, antiforgery, health checks.
- [ ] EF Core `DbContext`, migrations, model snapshot, query warnings.
- [ ] Redis cache and Data Protection key persistence.
- [ ] Blazor WebAssembly client package/static asset behavior.
- [ ] File upload and TUS endpoints.
- [ ] Image processing paths using ImageSharp.
- [ ] Integration test host setup in `BlazorAutoApp.Test/TestingSetup/WebAppFactory.cs`.

Commands:

- [ ] `dotnet build --configuration Release`
- [ ] Treat new compiler/analyzer warnings as upgrade findings, not noise.
- [ ] Fix real warnings before moving to deployment.

## Phase 10 - Test Matrix

Local fast checks:

- [ ] `dotnet restore`
- [ ] `dotnet build --configuration Release --no-restore`
- [ ] `dotnet test --configuration Release --no-build`
- [ ] `dotnet tool restore`
- [ ] `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`

Local integration checks:

- [ ] Start Docker Desktop.
- [ ] Run `docker compose up -d --build`.
- [ ] Run `python ./docker/local-status.py`.
- [ ] Run app health endpoint checks.
- [ ] Exercise login page and Google auth configuration does not crash startup.
- [ ] Exercise image upload/thumbnail flow.
- [ ] Exercise TUS upload flow.
- [ ] Confirm Redis cache and Data Protection do not throw at startup.

Deployment checks:

- [ ] `bash Deployment/LocalCluster/Scripts/audit-deployment.sh`
- [ ] `bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh`
- [ ] `bash Deployment/LocalCluster/Scripts/summary.sh`
- [ ] `bash Deployment/LocalCluster/Scripts/preflight.sh deploy` on control machine.
- [ ] CI workflow green.
- [ ] CD workflow with migrations enabled.
- [ ] `bash Deployment/LocalCluster/Scripts/acceptance-check.sh`

## Phase 11 - Database And Migration Safety

Before deploying:

- [ ] Confirm CI produces the .NET 10 migration bundle.
- [ ] Confirm CD runs pre-migration backup before the bundle.
- [ ] Confirm no new EF migration is generated unless model changes are intentional.
- [ ] If EF reports model changes, inspect them before deployment.

Deployment:

- [ ] Deploy with migrations enabled for the first .NET 10 deployment.
- [ ] Verify `/health/ready` after app start.
- [ ] Verify backup file exists on `node-db`.
- [ ] If migration fails, stop and restore from backup rather than retrying blindly.

## Phase 12 - Local Runtime Images After .NET Upgrade

Handle these after the app is green on .NET 10.

Local-only Docker Compose:

- [ ] Consider `postgres:17-alpine` for local dev.
- [ ] Consider `redis:8-alpine` for local dev.
- [ ] Replace `datalust/seq:latest` with a pinned Seq tag.
- [ ] Replace `redis/redisinsight:latest` with a pinned RedisInsight tag.

LocalCluster production-like compose:

- [ ] Keep `postgres:16.14-alpine3.23` during the .NET upgrade.
- [ ] Keep `redis:7.4.9-alpine3.21` during the .NET upgrade.
- [ ] Plan PostgreSQL major upgrade as a separate maintenance task with dump/restore or `pg_upgrade` testing.
- [ ] Plan Redis major upgrade separately with persistence compatibility checks.

Acceptance gate:

- [ ] Local dev compose works after optional local image changes.
- [ ] Production LocalCluster data containers are not major-upgraded as a side effect of app dependency updates.

## Phase 13 - Deployment Dependency Review

- [ ] Confirm `cloudflared_version` remains current. Latest observed GitHub release was `2026.5.0`, matching `all.yml`.
- [ ] Confirm GitHub runner installer still resolves latest `actions/runner`.
- [ ] Do not pin GitHub runner in this pass unless reproducibility becomes more important than auto-updating.
- [ ] Confirm Caddy install still uses the stable apt repository.
- [ ] Confirm Docker apt repository role still uses supported Linux Mint/Ubuntu codename handling.
- [ ] Run LocalCluster audit after any deployment script change.

## Phase 14 - Security And Public Repo Review

- [ ] Run `rg -n "password|secret|token|eyJ|BEGIN .*PRIVATE|ANSIBLE_VAULT" .`
- [ ] Confirm `Deployment/LocalCluster/inventory/prod/vault.yml` is encrypted and safe to commit only if it contains Ansible Vault ciphertext.
- [ ] Confirm no local `.env` files are tracked.
- [ ] Confirm no Docker build output, migration bundle, or backup file is tracked.
- [ ] Confirm package updates do not introduce deprecated/vulnerable package warnings.

## Phase 15 - Rollback Plan

If local build/test fails:

- [ ] Revert the smallest package group that caused the failure.
- [ ] Keep `global.json` fixed if possible, because it is currently invalid.
- [ ] Document deferred packages in this file.

If CI fails:

- [ ] Compare local SDK version and CI SDK version.
- [ ] Check whether `global.json` and `setup-dotnet` disagree.
- [ ] Check migration bundle build first, then Docker build.

If CD fails:

- [ ] Do not rerun repeatedly without reading the failing stage.
- [ ] If migration failed, use the pre-migration backup path.
- [ ] If app health failed, inspect app logs on both app nodes.
- [ ] If Caddy/public health failed, run `acceptance-check.sh` manually and inspect its diagnostics.

If production behavior is wrong after deployment:

- [ ] Roll back by dispatching CD from the previous known-good commit/image.
- [ ] Restore database only if migrations made incompatible data changes.
- [ ] Keep Cloudflare tunnel and runner unchanged unless the failure clearly involves ingress or runner setup.

## Phase 16 - Final Completion Criteria

The update is not done until all of these are true:

- [ ] Every project targets `net10.0`.
- [ ] `global.json` is valid and blocks preview/latest-major surprise upgrades.
- [ ] CI uses .NET 10.
- [ ] Docker app image uses .NET 10 SDK/runtime.
- [ ] `dotnet-ef` is on the EF 10 line.
- [ ] Direct NuGet package updates are either fully current or explicitly deferred with a reason.
- [ ] `dotnet restore` passes.
- [ ] `dotnet build --configuration Release` passes.
- [ ] `dotnet test --configuration Release` passes.
- [ ] EF migration bundle builds.
- [ ] Docker image builds.
- [ ] Deployment audit passes.
- [ ] Rendered deployment template validation passes.
- [ ] CI passes.
- [ ] CD passes.
- [ ] `acceptance-check.sh` passes against `shipinspection.jacobgrum.com`.
- [ ] No secrets or generated artifacts are accidentally included.

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
