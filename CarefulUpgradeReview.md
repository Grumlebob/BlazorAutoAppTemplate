# Careful Upgrade Review

Status: executed.

## Goal

Review upgrade opportunities without weakening Cloudflare safety or breaking LocalCluster deployment, now including approved destructive major upgrades for disposable PostgreSQL and Redis state.

This is a findings-and-execution plan. It separates:

- safe repo/tooling upgrades
- local-only convenience upgrades
- production deployment upgrades that require controlled rollout
- approved reset-based PostgreSQL and Redis major upgrades
- still-deferred major upgrades that would break local contributors or move to previews
- accepted Cloudflare safety tradeoffs

## Non-Goals

- Do not disable Cloudflare JavaScript Detections, Bot Fight Mode, challenge behavior, WAF, or other Cloudflare safety settings.
- Do not chase a perfect Lighthouse best-practices score by weakening Cloudflare.
- Do not major-upgrade PostgreSQL or Redis as a blind image tag bump. These are now approved only through an explicit disposable-state reset path.
- Do not preserve existing PostgreSQL or Redis data. The current local and production DB/cache contents are considered disposable.
- Do not major-upgrade Node or deployment infrastructure in the same PR as the PostgreSQL/Redis reset unless a phase explicitly calls for it.
- Do not change real LocalCluster inventory, hostnames, tunnel names, database names, ports, vault files, or deployment tokens unless the phase explicitly says so.
- Do not replace deployment values like `ship` just because this is a template; this deployment is active.
- Do not update floating production infrastructure opportunistically without a rollback path.

## Evidence Collected

Status: done.

Commands and sources checked:

```powershell
dotnet --info
dotnet list .\BlazorAutoApp.sln package --outdated
dotnet list .\BlazorAutoApp.sln package --vulnerable --include-transitive
dotnet list .\BlazorAutoApp.sln package --deprecated
dotnet tool list --local
dotnet tool search dotnet-ef --take 3
npm --prefix .\BlazorAutoApp.Client outdated
npm --prefix .\BlazorAutoApp.Client audit --audit-level=moderate
```

Additional version checks:

- .NET 10 release metadata: latest SDK `10.0.300`, latest runtime `10.0.8`, release date `2026-05-12`, support phase `active`, EOL `2028-11-14`.
- GitHub public tags:
  - `actions/checkout`: latest tag `v6.0.2`
  - `actions/setup-dotnet`: latest tag `v5.2.0`
  - `actions/setup-node`: latest tag `v6.4.0`
  - `actions/upload-artifact`: latest tag `v7.0.1`
  - `actions/download-artifact`: latest tag `v8.0.1`
  - `docker/login-action`: latest tag `v4.2.0`
- Node release index:
  - latest current: `v26.2.0`
  - latest LTS: `v24.16.0` (`Krypton`)
  - latest Node 22: `v22.22.3` (`Jod`)
  - latest Node 20: `v20.20.2` (`Iron`)
- Docker Hub tags:
  - `postgres:16.14-alpine3.23` is current for PostgreSQL 16.
  - `postgres:18.4-alpine3.23` is the current PostgreSQL 18 Alpine target.
  - PostgreSQL 18 Docker images use a version-specific default data directory, so the compose volume mount must be reviewed instead of only changing the image tag.
  - `redis:7.4.9-alpine3.21` is current for Redis 7.4.
  - `redis:8.8.0-alpine3.23` is the current Redis 8 Alpine target.
  - `redis/redisinsight:2.70` is behind current RedisInsight `3.4.2`.
  - `datalust/seq:2025.2` is current stable; `2026.1` tags are preview.
  - `docker/dockerfile:1.7-labs` is old; current stable frontend line is `1.24`.
- Cloudflare:
  - `cloudflared_version` is pinned to `2026.5.0`.
  - Latest `cloudflare/cloudflared` release checked through GitHub API: `2026.5.2`.

Current working tree note:

- `LighthousePerformance.md` and `TESTING.md` already contain production Lighthouse findings.
- `StackExchange.Redis` was updated from `2.13.1` to `2.13.17` after the final outdated-package check found the newer patch.
- `Npgsql.EntityFrameworkCore.PostgreSQL` was updated from `10.0.1` to `10.0.2`.

Execution result:

- Repo changes have been applied.
- Local Docker was destructively reset with `.\RunLocal.ps1 -ResetDatabase -NoBrowser`.
- Local PostgreSQL now reports `PostgreSQL 18.4`.
- Local Redis now reports `Redis server v=8.8.0`.
- RedisInsight `3.4.2` responds on `http://127.0.0.1:5540`.
- Local app readiness responds `200` on `https://127.0.0.1:7186/health/ready`.
- Production has not been reset from this workstation; the guarded deployment path is implemented for GitHub Actions/manual deployment.

## Repository Coverage Matrix

Status: done.

This review must cover every upgrade-sensitive surface, not only package manifests.

Covered surfaces:

- Solution-level .NET configuration:
  - `BlazorAutoApp.sln`
  - `global.json`
  - `Directory.Packages.props`
  - `Directory.Build.props`
- App projects:
  - `BlazorAutoApp/BlazorAutoApp.csproj`
  - `BlazorAutoApp.Client/BlazorAutoApp.Client.csproj`
  - `BlazorAutoApp.Core/BlazorAutoApp.Core.csproj`
  - `BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- Server/runtime code:
  - EF Core/Npgsql persistence and migrations
  - ASP.NET Identity
  - Redis-backed Data Protection
  - HybridCache and Redis pub/sub invalidation
  - health checks and forwarded headers
- Frontend/tooling:
  - `BlazorAutoApp.Client/package.json`
  - `BlazorAutoApp.Client/package-lock.json`
  - Tailwind generated CSS checks
  - Lighthouse tooling
- Local runtime:
  - root `docker-compose.yml`
  - `BlazorAutoApp/Dockerfile`
  - `RunLocal.ps1`
  - `RunLocal.cmd`
  - `.env.example`
  - `docker/setup-local.ps1`
  - `docker/local-status.py`
- CI/CD:
  - `.github/workflows/ci.yml`
  - `.github/workflows/cd-localcluster.yml`
  - `.github/workflows/auto-merge-dependabot.yml`
  - `.github/dependabot.yml`
- Deployment:
  - `Deployment/LocalCluster/compose/app-server/docker-compose.yml`
  - `Deployment/LocalCluster/compose/node-db/docker-compose.yml`
  - `Deployment/LocalCluster/ansible/playbooks/site.yml`
  - PostgreSQL/Redis Ansible roles
  - Caddy/cloudflared roles
  - deployment scripts, validators, audit script, and acceptance checks
  - deployment docs and examples
- Test infrastructure:
  - PostgreSQL Testcontainers images
  - Redis Testcontainers images
  - Ryuk image pin
  - integration, cross-node cache, and headed Playwright E2E paths

Gaps found by this second pass:

- Testcontainers still pin `postgres:16.14-alpine3.23` and `redis:7.4.9-alpine3.21`; they must move with the runtime upgrade.
- The test support pin for `testcontainers/ryuk` is `0.12.0`; current Docker Hub tag check found `0.14.0`.
- The plan needs an explicit deployment automation phase for destructive node-db volume reset across CLI, GitHub Actions, Ansible, docs, audit, and rendered-template validation.
- The full verification gate needs a final repo-wide stale-pin search so old image/action/tooling pins cannot survive accidentally.

## Finding Summary

Status: done.

Safe/no-op findings:

- .NET SDK is current: `10.0.300`.
- ASP.NET Core, EF Core, Identity, Playwright, xUnit, Testcontainers, and Serilog had no outdated packages according to NuGet. `StackExchange.Redis` and `Npgsql.EntityFrameworkCore.PostgreSQL` had newer patches and were updated.
- NuGet vulnerability and deprecation scans are clean.
- Local `dotnet-ef` tool is current at `10.0.8`.
- npm dependencies are current and have no moderate-or-higher audit findings.
- PostgreSQL 16 image is current for the pinned major line.
- Redis 7.4 image is current for the pinned major line.
- Seq is on latest stable; do not move to preview.

Real upgrade opportunities:

- CI uses `actions/download-artifact@v4` while latest major is `v8`.
- CI uses `rhysd/actionlint:1.7.7`; latest is `1.7.12`.
- CI pins Node `20`, while current LTS is Node `24`.
- `BlazorAutoApp/Dockerfile` uses `# syntax=docker/dockerfile:1.7-labs`; current stable frontend is `1.24`, and this Dockerfile does not appear to need labs syntax.
- Docker builds do not use `--pull`, so CI can reuse stale base images even when `mcr.microsoft.com/dotnet/*:10.0` receives a patched image.
- Local RedisInsight is on `2.70`; latest is `3.4.2`.
- Production `cloudflared` is pinned to `2026.5.0`; latest patch is `2026.5.2`.
- Local and production PostgreSQL can move from `16.14-alpine3.23` to `18.4-alpine3.23` because the current data can be discarded.
- Local and production Redis can move from `7.4.9-alpine3.21` to `8.8.0-alpine3.23` because cache/runtime data can be discarded.
- Testcontainers PostgreSQL/Redis image pins must move to the same versions as local and production.
- Testcontainers Ryuk is pinned to `0.12.0`; current checked Docker Hub tag is `0.14.0`.

Accepted destructive major upgrades and still-deferred items:

- PostgreSQL 16 to 18: approved through a fresh-volume reset, not an in-place upgrade.
- Redis 7.4 to 8.8: approved through a fresh-volume reset, not an in-place data compatibility assumption.
- Node engine hard-requirement from `>=20` to `>=24`: good eventual target, but it will break local machines that still have Node 22 unless the local script/docs are updated first.
- Cloudflare safety feature changes: explicitly rejected. Keep them enabled.

## Phase 1: Safe CI Tooling Updates

Status: done.

Tasks:

- Update the actionlint container in `.github/workflows/ci.yml` from `rhysd/actionlint:1.7.7` to `rhysd/actionlint:1.7.12`.
- Evaluate `actions/download-artifact@v4` to `@v8` in `.github/workflows/cd-localcluster.yml`.
- If updating `download-artifact`, update `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` because it currently asserts the old `@v4` string.
- Keep these as separate commits if possible:
  - actionlint patch update
  - artifact action major update
- Do not change `checkout@v6`, `setup-dotnet@v5`, `setup-node@v6`, `upload-artifact@v7`, or `docker/login-action@v4` just to chase minor tags; major tags already float within their major line.

Acceptance:

- CI lint still passes.
- Deployment audit still passes.
- CD can still download the migration bundle from a successful CI run by run ID.
- No deployment inventory or secret changes.

Verification:

```powershell
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:1.7.12
```

CI verification after push:

- CI completes successfully.
- CD dry path reaches artifact download preparation on a safe test dispatch if feasible.

## Phase 2: CI Node LTS Modernization

Status: done.

Finding:

CI uses Node `20`, while the current LTS is Node `24`. Local machine currently has Node `22.19.0`.

Tasks:

- Update CI `actions/setup-node` from `node-version: 20` to `node-version: 24`.
- Keep `BlazorAutoApp.Client/package.json` at `"node": ">=20"` for now to avoid breaking local contributors on Node 22.
- Add a plan note or local-status warning that Node 24 is recommended for CI parity.
- In a later phase, after local scripts and docs clearly guide Node 24, decide whether to raise `engines.node` to `>=24`.

Acceptance:

- `npm ci`, `npm audit`, `npm run css:build`, and Lighthouse tooling work under Node 24.
- Existing local Node 22 developers are warned but not blocked yet.

Verification:

```powershell
npm --prefix .\BlazorAutoApp.Client ci
npm --prefix .\BlazorAutoApp.Client audit --audit-level=moderate
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
```

## Phase 3: Docker Build Frontend And Base-Image Freshness

Status: done.

Findings:

- Dockerfile frontend `docker/dockerfile:1.7-labs` is old.
- Current stable Dockerfile frontend is `1.24`.
- The Dockerfile does not appear to use labs-only features.
- CI `docker build` does not use `--pull`.

Tasks:

- Change Dockerfile syntax from `# syntax=docker/dockerfile:1.7-labs` to a stable current frontend, expected target `# syntax=docker/dockerfile:1.24`.
- Build locally to prove no labs syntax is required.
- Add `--pull` to CI Docker build so `mcr.microsoft.com/dotnet/sdk:10.0` and `mcr.microsoft.com/dotnet/aspnet:10.0` are refreshed on CI builds.
- Consider adding `--pull` to local explicit rebuild docs, but do not force it on every quick local run.

Acceptance:

- Docker build succeeds.
- Docker image still starts.
- Local and CI continue to use .NET 10 images.
- No app behavior changes.

Verification:

```powershell
docker compose build --pull web
docker compose up -d --no-build web
Invoke-WebRequest -Uri https://127.0.0.1:7186/health/ready -SkipCertificateCheck
```

## Phase 4: Local-Only Tooling Image Review

Status: done.

Finding:

- `redis/redisinsight:2.70` is local-only and behind `3.4.2`.

Tasks:

- Review RedisInsight 2.x to 3.x volume compatibility and UI port behavior.
- If compatible, update local `docker-compose.yml` to `redis/redisinsight:3.4.2`.
- Do not touch deployment compose, because RedisInsight is not part of production.
- Document that users may need to recreate the local `redisinsight` volume if RedisInsight major-version data migration fails.

Acceptance:

- Local Docker stack starts.
- RedisInsight UI is reachable at the configured local port.
- No production files changed.

Verification:

```powershell
docker compose up -d redisinsight
docker compose ps redisinsight
Invoke-WebRequest -Uri http://127.0.0.1:5540
```

## Phase 5: cloudflared Patch Upgrade

Status: done.

Finding:

- Deployment pins `cloudflared_version: 2026.5.0`.
- Latest release checked: `2026.5.2`.
- This does not disable Cloudflare safety. It updates the connector binary.

Tasks:

- Review Cloudflare release notes for `2026.5.1` and `2026.5.2`.
- If no tunnel-breaking issue is found, update `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` to `cloudflared_version: 2026.5.2`.
- Keep the existing Cloudflare tunnel token and tunnel name unchanged.
- Run deployment preflight and audit.
- Deploy during a controlled window because the role may reinstall/restart the connector.
- After deployment, verify Caddy and cloudflared services plus public `/health/ready`.

Acceptance:

- Cloudflare safety features remain enabled.
- Same tunnel name, token, public hostname, and app deployment values.
- Public app remains reachable.

Verification:

```powershell
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/preflight.sh deploy
bash Deployment/LocalCluster/Scripts/check-cloudflare-tunnel.sh
```

Post-deploy:

```bash
bash Deployment/LocalCluster/Scripts/acceptance-check.sh
curl -fsS https://shipinspection.jacobgrum.com/health/ready
```

## Phase 6: PostgreSQL 18 Disposable-State Upgrade

Status: done.

Finding:

- PostgreSQL 16.14 is current for PostgreSQL 16.
- PostgreSQL 18.4 is the current PostgreSQL 18 release target.
- Current local and production database contents are disposable.
- PostgreSQL 18 Docker images use a version-specific default `PGDATA`, so the named volume mount must be aligned with the image instead of left at the old generic `/var/lib/postgresql/data` path.
- The existing `reset-db.sh` is enough for a fresh schema inside a running compatible PostgreSQL instance, but it is not enough for a major image/data-directory change because the old volume can prevent the new container from starting correctly.

Decision:

- Upgrade PostgreSQL directly to `postgres:18.4-alpine3.23`.
- Use a destructive fresh-volume reset for local and production.
- Run the existing EF migration bundle against the fresh PostgreSQL 18 database after the container starts.

Implementation tasks:

- Update root `docker-compose.yml` PostgreSQL image to `postgres:18.4-alpine3.23`.
- Update `Deployment/LocalCluster/compose/node-db/docker-compose.yml` PostgreSQL image to `postgres:18.4-alpine3.23`.
- Change the PostgreSQL named volume mount in both compose files to `/var/lib/postgresql`, matching the PostgreSQL 18 Docker image `VOLUME` while letting `PGDATA` live under the version-specific `/var/lib/postgresql/18/docker` directory.
- Add or update deployment automation so a major DB reset can run before the node-db compose stack is brought up on the new PostgreSQL image.
- Add a guarded deployment switch for destructive node-db volume reset, separate from the existing schema-only `--reset-db` path.
- The production reset path should be guarded by a confirmation value, for example `<app_name>/postgres18-redis8-reset`, and should run `docker compose down -v` on `node-db` before the new compose file starts.
- Wire the reset switch through the local deploy script, CD workflow inputs, and Ansible playbook vars so CLI and GitHub Actions use the same explicit path.
- In Ansible, stop app containers before the node-db volume reset, reset the node-db compose project, then let the normal PostgreSQL/Redis role render the new compose file and start fresh containers.
- Keep `reset-db.sh` for normal fresh-schema resets and migration-failure recovery, but do not rely on it as the only PostgreSQL major-upgrade reset mechanism.
- Update deployment audit checks that enforce exact pinned image tags so `postgres:18.4-alpine3.23` is accepted.
- Update deployment documentation to state that this upgrade intentionally discards the existing `postgres_data` volume.
- Update local documentation with the simple local reset command: `docker compose down -v --remove-orphans` before restarting the local stack.

Acceptance:

- Local PostgreSQL starts on version 18.4.
- Production node-db starts on version 18.4 after the destructive volume reset.
- EF migrations apply cleanly against an empty PostgreSQL 18 database.
- Identity registration/login and Books CRUD work after reset.
- Deployment acceptance checks pass.
- No Cloudflare safety settings change.

Verification:

```powershell
docker compose down -v --remove-orphans
docker compose up -d --build
docker compose exec postgres postgres --version
dotnet test .\BlazorAutoApp.sln -c Release --no-build
```

Production verification:

```bash
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/preflight.sh deploy
# Deploy with the explicit destructive node-db reset and migrations enabled.
bash Deployment/LocalCluster/Scripts/acceptance-check.sh
```

## Phase 7: Redis 8 Disposable-State Upgrade

Status: done.

Finding:

- Redis 7.4.9 is current for Redis 7.4.
- Redis 8.8.0 is the current Redis 8 release target.
- Redis is used for distributed cache, cache invalidation pub/sub, HybridCache distributed behavior, and Data Protection keys when Redis is configured.
- Current Redis contents are disposable. Resetting Redis will invalidate any Redis-backed Data Protection keys and can sign users out.

Decision:

- Upgrade Redis directly to `redis:8.8.0-alpine3.23`.
- Use the same destructive node-db reset window as PostgreSQL 18 so the app restarts with a fresh cache and fresh distributed key state.

Implementation tasks:

- Update root `docker-compose.yml` Redis image to `redis:8.8.0-alpine3.23`.
- Update `Deployment/LocalCluster/compose/node-db/docker-compose.yml` Redis image to `redis:8.8.0-alpine3.23`.
- Keep exact image tags; do not use `redis:8`, `redis:alpine`, or `latest`.
- Keep `--requirepass` in production deployment compose.
- Decide whether local Redis should remain passwordless for convenience or match production more closely in a separate security/local-parity phase.
- Update deployment audit checks that enforce exact pinned image tags so `redis:8.8.0-alpine3.23` is accepted.
- Run the cross-node cache invalidation tests against Redis 8.
- Run login/logout/profile and Books CRUD checks after app restart to verify Data Protection and cache behavior.

Acceptance:

- Local Redis reports version 8.8.
- Production Redis reports version 8.8 after the destructive volume reset.
- Health checks pass.
- Cross-node Books cache invalidation tests pass.
- Login cookies work after fresh sign-in.

Verification:

```powershell
docker compose exec redis redis-server --version
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BooksCrossNode|FullyQualifiedName~Redis"
```

## Phase 8: Seq Stable Upgrade Watch

Status: deferred.

Finding:

- `datalust/seq:2025.2` is latest stable.
- `2026.1` exists only as preview tags.

Decision:

- Do not move local Seq to preview.
- Re-check when `2026.1` stable is released.

## Phase 9: Test Infrastructure Runtime Alignment

Status: done.

Finding:

- `BlazorAutoApp.Test/TestSupport/Integration/SharedIntegrationEnvironment.cs` pins PostgreSQL 16 and Redis 7 for cross-node tests.
- `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs` pins PostgreSQL 16 for integration tests.
- `WebAppFactory.cs` pins `testcontainers/ryuk:0.12.0`; current checked Docker Hub tag is `0.14.0`.
- If these stay old, CI can pass while proving the previous database/cache runtime instead of the upgraded stack.

Tasks:

- Introduce a single test image constants location if it keeps the test support cleaner, for example `TestSupport/Integration/TestContainerImages.cs`.
- Update PostgreSQL Testcontainers to `postgres:18.4-alpine3.23`.
- Update Redis Testcontainers to `redis:8.8.0-alpine3.23`.
- Update Ryuk to `testcontainers/ryuk:0.14.0` after confirming Testcontainers .NET `4.12.0` works with it.
- Run integration tests that exercise EF migrations, Respawn cleanup, Identity, Redis connection reuse, and cross-node cache invalidation.
- Run a repo search to prove no old PostgreSQL/Redis test image pins remain.

Acceptance:

- Testcontainers start reliably on the upgraded images.
- EF migrations apply in PostgreSQL 18 Testcontainers.
- Respawn cleanup still works against PostgreSQL 18.
- Redis 8 works with StackExchange.Redis, distributed cache, Data Protection, and cache invalidation tests.
- No stale `postgres:16.14-alpine3.23`, `redis:7.4.9-alpine3.21`, or `testcontainers/ryuk:0.12.0` test pins remain.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~Integration|FullyQualifiedName~Redis|FullyQualifiedName~BooksCrossNode"
rg -n "postgres:16\.14|redis:7\.4\.9|testcontainers/ryuk:0\.12\.0" BlazorAutoApp.Test
```

## Phase 10: Deployment Automation And Audit Coverage

Status: done.

Finding:

- The PostgreSQL/Redis major upgrade touches more than compose image tags.
- Deployment has multiple entry points and validators that must stay in agreement:
  - `Deployment/LocalCluster/Scripts/deploy.sh`
  - `.github/workflows/cd-localcluster.yml`
  - `Deployment/LocalCluster/ansible/playbooks/site.yml`
  - `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py`
  - `Deployment/LocalCluster/Scripts/validate-rendered-templates.sh`
  - `Deployment/LocalCluster/Scripts/acceptance-check.sh`
  - `Deployment/LocalCluster/HowToDeployLocalCluster.md`
  - `Deployment/LocalCluster/Scripts/README.md`

Tasks:

- Add the destructive node-db reset option to the shell deploy wrapper with a confirmation token distinct from normal schema reset.
- Add matching GitHub Actions workflow inputs in `cd-localcluster.yml`.
- Wire those inputs into Ansible variables.
- Add Ansible tasks that stop app containers first, run node-db `docker compose down -v`, render the new node-db compose file, start PostgreSQL/Redis, then run migrations.
- Update audit checks so the new reset path is required to be guarded and cannot run without an explicit confirmation token.
- Update rendered-template validation so PostgreSQL 18 volume paths and Redis 8 image tags are validated from generated compose output.
- Keep `acceptance-check.sh` focused on post-deploy health, but make sure it verifies DB/Redis compose services and version commands if the major-upgrade flag was used.
- Update docs with the exact destructive-production sequence and the expected user-facing effect: existing database data gone, existing Redis keys gone, users signed out.
- Keep Cloudflare tunnel, deployment inventory, app hostnames, ports, and vault values unchanged unless a phase explicitly says otherwise.

Acceptance:

- CLI deployment and GitHub Actions deployment use the same reset semantics.
- Audit fails if a destructive reset can run without confirmation.
- Audit passes after the guarded reset path is implemented.
- Rendered-template validation proves deployment compose contains PostgreSQL 18, Redis 8, and the PostgreSQL 18 data path.
- Acceptance check passes after deployment.

Verification:

```powershell
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
bash Deployment/LocalCluster/Scripts/preflight.sh deploy
```

## Phase 11: Server Compatibility Review

Status: done.

Finding:

- The server relies on PostgreSQL for Identity and Books, Redis for cache/distributed behavior, and Redis-backed Data Protection when Redis is available.
- A reset-based upgrade removes old data but still needs server compatibility proof.

Tasks:

- Confirm EF Core migrations create a clean PostgreSQL 18 schema from zero.
- Confirm integer identity columns and Npgsql-generated migration SQL are still correct.
- Confirm local seeded users are recreated after reset only when local account seeding is enabled.
- Confirm production does not run migrations at app startup and uses the migration bundle path.
- Confirm Redis-backed Data Protection works after Redis reset; old cookies may become invalid, which is acceptable.
- Confirm HybridCache and Redis pub/sub invalidation still behave correctly across two app hosts.
- Confirm health readiness includes PostgreSQL and Redis after the upgrade.
- Confirm forwarded headers and Caddy/cloudflared production routing are unaffected.

Acceptance:

- `dotnet build` and `dotnet test` pass.
- Books CRUD works locally after a full Docker volume reset.
- Identity register/login/logout/profile works locally after a full Docker volume reset.
- Readiness endpoint fails if PostgreSQL or Redis is unavailable and passes once both are healthy.

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "Category=E2E"
```

## Phase 12: Local Developer Parity And Docs

Status: done.

Finding:

- Local scripts need to make the destructive reset path easy and obvious for this disposable-data upgrade.
- Developers should not have to infer that old local Docker volumes must be removed before PostgreSQL 18 starts cleanly.

Tasks:

- Update `HowToRunLocally.md` with the local reset command for the PostgreSQL 18/Redis 8 upgrade.
- Update `TESTING.md` if test commands or image assumptions change.
- Update `RunLocal.ps1` or supporting local setup docs if a one-click “fresh local stack” mode is clearer than manual `docker compose down -v`.
- Keep normal `RunLocal.cmd` safe for day-to-day use; do not make it destroy volumes unless explicitly requested by a flag or separate command.
- Review `docker/local-status.py` for version reporting or warnings after the image upgrade.
- Confirm `.env.example` remains valid and does not require secret changes.

Acceptance:

- A developer can run the app locally from a clean or stale-volume state by following docs.
- The normal local script does not destroy data unexpectedly.
- Any destructive local command is explicitly named and documented.

Verification:

```powershell
.\RunLocal.cmd
docker compose ps
Invoke-WebRequest -Uri https://127.0.0.1:7186/health/ready -SkipCertificateCheck
```

## Phase 13: CI Policy And Automation Review

Status: done.

Finding:

- Dependabot already covers GitHub Actions, Docker, NuGet, and npm.
- `auto-merge-dependabot.yml` already refuses auto-merge for major or deployment/workflow surfaces, which is correct for PostgreSQL/Redis and CI/CD changes.
- CI still needs explicit stale-pin checks after major runtime upgrade.

Tasks:

- Keep Dependabot coverage as-is unless a new Dockerfile/compose path is added.
- Keep auto-merge guard behavior for deployment/workflow/Docker changes.
- Add a CI check or audit assertion that rejects old runtime pins after the upgrade:
  - `postgres:16.14-alpine3.23`
  - `redis:7.4.9-alpine3.21`
  - `testcontainers/ryuk:0.12.0`
  - `actions/download-artifact@v4`
  - `rhysd/actionlint:1.7.7`
  - `docker/dockerfile:1.7-labs`
- Ensure CI’s explicit PostgreSQL image pull uses PostgreSQL 18 after the runtime upgrade.
- Ensure Docker build still uses .NET 10 base images and `--pull`.

Acceptance:

- CI proves upgraded local/test/deployment runtime pins.
- Dependabot will not auto-merge risky runtime/deployment changes.
- No stale old-runtime pins remain except historical archived plans, if intentionally ignored.

Verification:

```powershell
rg -n "postgres:16\.14|redis:7\.4\.9|testcontainers/ryuk:0\.12\.0|download-artifact@v4|actionlint:1\.7\.7|docker/dockerfile:1\.7-labs" --glob "!docs/plans/archive/**" .
```

## Phase 14: .NET Package And SDK Watch

Status: no action now.

Findings:

- SDK `10.0.300` is current.
- Runtime `10.0.8` is current.
- NuGet package graph is current after updating `StackExchange.Redis` and `Npgsql.EntityFrameworkCore.PostgreSQL`.
- `dotnet-ef` local tool is current.

Tasks:

- `StackExchange.Redis` was updated to `2.13.17`.
- `Npgsql.EntityFrameworkCore.PostgreSQL` was updated to `10.0.2`.
- Keep Dependabot for NuGet enabled.
- Keep `global.json` at `10.0.300` until the next .NET SDK feature band/security patch is released.

Verification:

```powershell
dotnet list .\BlazorAutoApp.sln package --outdated
dotnet list .\BlazorAutoApp.sln package --vulnerable --include-transitive
dotnet list .\BlazorAutoApp.sln package --deprecated
dotnet tool list --local
```

## Phase 15: Cloudflare Safety Position

Status: accepted.

Finding:

- Production Lighthouse best-practices score is reduced by Cloudflare-injected challenge JavaScript.
- The user explicitly does not want to disable Cloudflare safety features.

Decision:

- Keep Cloudflare JavaScript Detections/Bot Fight Mode/security behavior enabled.
- Treat Lighthouse best-practices `77-81` as an accepted external security-product artifact.
- Do not add app code workarounds for Cloudflare challenge scripts.

Tasks:

- Keep `TESTING.md` note explaining this.
- Keep production Lighthouse reports as evidence.
- Future production performance work should focus on app payload, Blazor startup, and deployment latency, not disabling Cloudflare challenge scripts.

## Recommended Execution Order

Status: done.

1. Update actionlint image patch.
2. Update Dockerfile frontend from labs to stable and add CI `docker build --pull`.
3. Update CI Node to 24 while keeping package engine at `>=20`.
4. Evaluate and update `actions/download-artifact` from v4 to v8 with deployment audit changes.
5. Update local RedisInsight if volume compatibility is acceptable.
6. Update cloudflared from `2026.5.0` to `2026.5.2` in a controlled deployment window.
7. Implement deployment automation for the destructive node-db reset path before changing production images.
8. Update PostgreSQL/Redis local, deployment, CI, and Testcontainers image pins together.
9. Run the local destructive reset and prove the app from a fresh PostgreSQL 18/Redis 8 stack.
10. Run server compatibility, integration, cross-node Redis, and headed E2E verification.
11. Execute the production PostgreSQL 18 and Redis 8 disposable-state upgrade only through explicit confirmation.
12. Run stale-pin search and deployment acceptance checks.
13. Keep Seq preview upgrades deferred.

## Full Verification Gate

Status: done.

Run after any accepted repo upgrade batch:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
npm --prefix .\BlazorAutoApp.Client ci
npm --prefix .\BlazorAutoApp.Client audit --audit-level=moderate
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
docker compose build --pull web
docker compose up -d --no-build web
Invoke-WebRequest -Uri https://127.0.0.1:7186/health/ready -SkipCertificateCheck
rg -n "postgres:16\.14|redis:7\.4\.9|testcontainers/ryuk:0\.12\.0|download-artifact@v4|actionlint:1\.7\.7|docker/dockerfile:1\.7-labs" --glob "!docs/plans/archive/**" .
```

Run visible E2E after upgrades that touch frontend, Docker, Node, or runtime behavior:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~E2E"
```

Production verification after deployment-affecting upgrades:

```bash
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
bash Deployment/LocalCluster/Scripts/preflight.sh deploy
bash Deployment/LocalCluster/Scripts/acceptance-check.sh
curl -fsS https://shipinspection.jacobgrum.com/health/ready
```

Additional PostgreSQL/Redis major-upgrade verification:

```bash
cd /opt/ship
docker compose exec -T postgres postgres --version
docker compose exec -T redis redis-server --version
docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" ping
```

## Done Criteria

Status: done.

- Safe repo/tooling upgrades are applied separately from risky runtime major upgrades.
- Cloudflare safety remains enabled.
- Local and CI verification pass.
- Deployment audit and acceptance checks pass for deployment-affecting changes.
- PostgreSQL/Redis major upgrades are performed only through the explicit disposable-state reset path.
- Runtime image pins are aligned across local Docker, deployment Docker, CI, and Testcontainers.
- Deployment CLI, GitHub Actions, Ansible, docs, audit, and rendered-template validation all understand the same destructive node-db reset path.
- Server compatibility is proven for EF migrations, Identity, Redis Data Protection, HybridCache, Redis pub/sub invalidation, and health checks.
- Repo-wide stale-pin search passes outside archived historical plans.
