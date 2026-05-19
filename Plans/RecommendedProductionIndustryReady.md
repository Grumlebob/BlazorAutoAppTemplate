# Recommended Production Industry-Ready Plan

This plan focuses on what this repository should improve to be robust, secure, and maintainable in production.

## Current Snapshot (Repo-Specific)

1. Strong baseline already exists:
   - Single `AppDbContext` with Identity integrated.
   - Docker Compose stack with PostgreSQL, Redis, and Seq.
   - Vertical slice architecture and architecture tests.
   - Serilog structured logging and Redis-backed caching.
2. Highest-impact gaps to close next:
   - App-level rate limiting is planned but not implemented yet.
   - Identity is still in dev-friendly mode (`RequireConfirmedAccount = false`) and first-user auto-admin logic is risky for production.
   - Database migrations run automatically at app startup.
   - No health/readiness endpoints for orchestration and uptime monitoring.
   - CI pipeline is basic (build + test only), no security scanning/lint/coverage gates.
   - Container/runtime hardening is not complete (non-root, limits, web healthcheck).

## Phase 0 (Must-Do Before Public Exposure)

## 1) Security Hardening

1. Implement rate limiting from [RateLimiting.md](./RateLimiting.md).
2. Add lockout/throttling for login/register flows.
3. Move toward confirmed account and optional MFA for privileged roles.
4. Restrict admin assignment:
   - Replace "first registered user becomes Admin" with explicit bootstrap flow.
5. Ensure cookie/auth settings are explicit for production:
   - secure cookies, strict same-site policy where possible, sliding expiration policy.

Implementation targets:
- `BlazorAutoApp/Program.cs`
- `BlazorAutoApp/Data/AppDbContext.cs`
- `BlazorAutoApp/Features/IdentityShowcase/*` (for role demo + auth behavior validation)

Definition of done:
- Abuse traffic receives `429` with `Retry-After`.
- Brute-force login attempts get locked out.
- Admin role assignment is explicit and auditable.

## 2) Secrets And Key Management

1. Keep real credentials out source control and examples.
2. Add `secrets.env.example` with placeholders only.
3. Use a production secret store (Azure Key Vault / AWS Secrets Manager / Doppler / 1Password Connect).
4. Rotate any previously exposed API keys immediately.
5. Keep DataProtection keys persisted and encrypted with managed cert/keys in production.

Implementation targets:
- `.gitignore`
- `HowToRunLocally.md`
- deployment environment configuration

Definition of done:
- No real secrets in repo or docs.
- Secret rotation process is documented and tested.

## 3) Safe Database Migration Strategy (Expanded)

This is the highest-risk area in the current codebase because `BlazorAutoApp/Program.cs` applies EF migrations during app startup. That is fine for local development, but unsafe in production.

## Why Current Behavior Is Risky

1. Startup coupling:
   - If migration fails, app boot fails.
   - Deployment and schema evolution are tightly coupled, reducing recovery options.
2. Multi-instance race risk:
   - In scaled deployments, multiple app instances may attempt migration at the same time.
3. Blast radius:
   - A bad migration can take the entire app down instead of failing in a controlled pre-deploy job.
4. Limited auditability:
   - Harder to prove exactly when and by which pipeline/identity schema changes were applied.

## Should You Add A Separate Migration Project?

Short answer: yes for long-term maturity, but there is a practical staged path.

Use this decision matrix:

1. Option A: Keep startup migration in web app.
   - Good for: local dev only.
   - Not acceptable for: production.
2. Option B: EF migrations bundle (`dotnet ef migrations bundle`) run in pipeline/job.
   - Good for: most teams, fastest move to safe production.
   - Pros: no new project required, deterministic artifact, easy to automate.
   - Cons: less customization for locks, richer pre-checks, and complex data migrations.
3. Option C: Dedicated `BlazorAutoApp.Migrator` console project.
   - Good for: enterprise process, strict controls, data backfills, richer safety checks.
   - Pros: full control (advisory lock, dry-run checks, destructive-change guardrails, richer logging).
   - Cons: more code and maintenance.

Recommended approach for this repo:

1. Immediately move to Option B (bundle-based migration step) and disable production startup migrations.
2. Add Option C once migrations become more complex (data backfills, zero-downtime expand/contract, multi-env governance).

## Target End-State Architecture

1. App startup:
   - Production web app does not execute `Database.Migrate()`.
   - Dev/Docker can keep opt-in auto migrate for convenience.
2. CI artifact:
   - Build migration artifact from the same commit as the app image.
3. CD order:
   - Run migration job once.
   - Verify success and readiness checks.
   - Deploy/roll out app.
4. Audit:
   - Pipeline logs and release metadata record migration artifact version and outcome.

## Detailed Implementation Plan (Executable)

## Step 1: Decouple Migrations From Web Startup

1. Add configuration flag: `Database:ApplyMigrationsAtStartup`.
2. In `BlazorAutoApp/Program.cs`:
   - Only run migration block when flag is true.
   - Default true in local dev, false in production.
3. Set defaults:
   - `appsettings.Development.json`: `Database:ApplyMigrationsAtStartup = true`
   - `appsettings.Docker.json`: choose based on local workflow; generally true for local compose, false for production-like environments.
   - Production config/secret store: force `false`.

Implementation targets:
- `BlazorAutoApp/Program.cs`
- `BlazorAutoApp/appsettings.Development.json`
- `BlazorAutoApp/appsettings.Docker.json`
- `HowToRunLocally.md`

Acceptance criteria:
- Production boot path never attempts schema mutation.
- Local developer experience remains simple.

## Step 2: Introduce Controlled Migration Artifact (Bundle First)

1. Build migration bundle in CI from the same commit:
   - `dotnet ef migrations bundle --project BlazorAutoApp --startup-project BlazorAutoApp --context AppDbContext --output ./artifacts/efbundle`
2. Store artifact with build metadata (commit SHA, timestamp).
3. In deploy pipeline, execute bundle with production connection string before app rollout.
4. Fail deployment if bundle exits non-zero.

Implementation targets:
- `.github/workflows/ci.yml`
- deployment pipeline definition
- release notes template

Acceptance criteria:
- Migrations are applied by pipeline job, not app startup.
- Same commit drives both schema and app binaries.

## Step 3: Add Migration Pre-Checks And Gates

1. Pending migration check in CI:
   - Fail if model changed but no migration was added.
2. SQL generation and review:
   - Generate idempotent SQL for review: `dotnet ef migrations script --idempotent`.
3. Destructive-change guard:
   - Require explicit approval if SQL contains `DROP`, `ALTER TYPE`, or non-null constraints without defaults/backfill.

Implementation targets:
- CI workflow scripts
- `docs/` migration review checklist

Acceptance criteria:
- Risky schema changes cannot merge silently.
- Every migration PR has reviewable SQL output.

## Step 4: Add Operational Locking (Critical In Multi-Instance Deployments)

1. Ensure only one migration process runs at a time per database.
2. If using dedicated migrator project, use PostgreSQL advisory lock (`pg_try_advisory_lock`) before applying migrations.
3. If lock cannot be acquired, fail fast with clear message.

Implementation targets:
- future `BlazorAutoApp.Migrator` project (recommended for this feature)
- deploy job orchestration

Acceptance criteria:
- No concurrent migration runners can mutate schema simultaneously.

## Step 5: Rollback And Forward-Fix Policy

1. Prefer forward-fix over down-migration in production.
2. Before migration job:
   - Validate backup recency.
   - Capture restore point/snapshot.
3. If migration fails:
   - Stop rollout.
   - Restore from snapshot only when necessary and rehearsed.
   - Otherwise deploy hotfix migration.
4. Document runbook with time limits and decision owners.

Implementation targets:
- `docs/` production runbook
- infrastructure backup job config

Acceptance criteria:
- Incident responders can execute a known recovery path under time pressure.

## Step 6: Zero-Downtime Migration Pattern (Expand/Contract)

Use this standard for potentially breaking changes:

1. Expand release:
   - Add new nullable columns/tables/indexes.
   - Keep old schema in use.
2. Compatibility release:
   - Dual-write or dual-read in app.
   - Backfill data in controlled batches.
3. Contract release:
   - Switch reads fully to new schema.
   - Drop old columns/tables only after verification.

Implementation targets:
- migration PR template
- coding guidelines in `README.md` or `docs/`

Acceptance criteria:
- No app version is deployed that depends on a schema shape unavailable during rollout.

## Step 7: Optional But Recommended `BlazorAutoApp.Migrator` Project

When you add this project, keep it minimal and purpose-built:

1. Create project:
   - `BlazorAutoApp.Migrator` (.NET console).
2. Reference:
   - `BlazorAutoApp` and required EF packages.
3. Features to include:
   - `--dry-run` (list pending migrations, no apply)
   - `--apply` (apply pending migrations)
   - advisory lock before apply
   - structured logging
   - clear exit codes
4. Pipeline usage:
   - Run migrator binary/container as a pre-deploy job.
   - Block app deploy on failure.

Recommended trigger to add this project:
- More than one environment with strict change windows.
- Data backfills and non-trivial schema rewrites.
- Need for explicit migration SLOs and audit controls.

## Suggested CI/CD Flow (Concrete)

1. PR pipeline:
   - build/test
   - verify migrations present when model changed
   - generate SQL artifact for review
2. Main branch pipeline:
   - build app image
   - build migration artifact (bundle or migrator)
3. Deploy pipeline:
   - pre-check DB connectivity and backup freshness
   - run migration artifact once
   - run smoke query + health checks
   - deploy app
   - monitor error/latency/DB signals for rollback window

## Repo Files To Add/Update For This Plan

1. Update:
   - `BlazorAutoApp/Program.cs` (gate startup migrations by config/environment)
   - `BlazorAutoApp/appsettings*.json` (new migration flag)
   - `HowToRunLocally.md` (developer flow)
   - `Plans/DEPLOYMENT_PLAN.md` (production flow)
2. Add:
   - `docs/DatabaseMigrationRunbook.md`
   - optional `BlazorAutoApp.Migrator/` project
   - CI workflow or scripts for migration artifact generation and execution

## Definition Of Done (Detailed)

1. Production app process never applies migrations on startup.
2. Migration apply step is explicit, automated, and logged in pipeline.
3. Risky migration SQL requires human approval.
4. Backup/restore procedure is documented and tested at least once.
5. A junior developer (or weaker AI) can apply the runbook end-to-end without tribal knowledge.

## Phase 1 (Reliability And Operations)

## 4) Health, Readiness, And Resilience

1. Add health endpoints:
   - `/health/live`
   - `/health/ready` (checks PostgreSQL + Redis)
2. Add timeouts/retries/circuit breakers for external calls where relevant.
3. Add graceful shutdown behavior and startup probes for containers/orchestrators.

Implementation targets:
- `BlazorAutoApp/Program.cs`
- `docker-compose.yml`
- Kubernetes/host config (if used later)

Definition of done:
- Orchestrator can accurately decide startup/readiness.
- Temporary dependency failures degrade gracefully.

## 5) Observability And Alerts

1. Keep Serilog but add OpenTelemetry traces/metrics.
2. Standardize correlation IDs across logs and responses.
3. Create alert thresholds:
   - 5xx spike
   - high latency
   - rate-limit violations
   - auth failures spike
4. Add a concise incident runbook.

Implementation targets:
- `BlazorAutoApp/Program.cs`
- `BlazorAutoApp/appsettings*.json`
- `docs/` runbooks

Definition of done:
- Dashboards exist for latency/error/auth/rate-limit signals.
- Alerts route to on-call channel.

## 6) Docker And Host Hardening

1. Run app container as non-root user.
2. Add web container healthcheck.
3. Set CPU/memory limits in deployment manifests.
4. Pin image tags where reproducibility matters.
5. Add image vulnerability scanning in CI.

Implementation targets:
- `BlazorAutoApp/Dockerfile`
- `docker-compose.yml`
- `.github/workflows/*`

Definition of done:
- Containers run with least privilege and pass vulnerability policy.

## Phase 2 (Engineering Quality And Scale)

## 7) CI/CD Quality Gates

1. Expand CI beyond build/test:
   - formatting and analyzer checks
   - warnings-as-errors for CI
   - test coverage report + minimum threshold
   - dependency and container scanning
2. Add protected branch rules:
   - required status checks
   - CODEOWNERS review for security-sensitive files.

Implementation targets:
- `.github/workflows/ci.yml`
- `.github/dependabot.yml`
- repo settings / `CODEOWNERS`

Definition of done:
- Pull requests fail fast on quality/security regressions.

## 8) API Robustness And Contract Maturity

1. Standardize error responses with `ProblemDetails`.
2. Add endpoint versioning strategy (if public consumers are expected).
3. Add integration tests for auth/roles/rate-limits and negative paths.
4. Consider OpenAPI generation for API consumers.

Implementation targets:
- endpoint files under `BlazorAutoApp/Features/*/Endpoints.cs`
- `BlazorAutoApp.Test/*`

Definition of done:
- API behavior is predictable, documented, and regression-tested.

## 9) Data Governance And Recovery

1. Add backup/restore automation for PostgreSQL.
2. Define RPO/RTO targets.
3. Test restore quarterly.
4. Add retention and cleanup policy for uploaded files in `Storage`.

Implementation targets:
- deployment scripts/infra
- `docs/` operational playbooks

Definition of done:
- Team can restore data reliably within agreed targets.

## Delivery Order (Recommended)

1. Phase 0: Security + secrets + migration safety.
2. Phase 1: Health/readiness + observability + container hardening.
3. Phase 2: CI/CD gates + API maturity + backup/DR excellence.

## 30/60/90 Day Suggested Milestones

1. First 30 days:
   - Complete Phase 0.
   - Ship rate limiting and production-safe identity defaults.
2. By 60 days:
   - Complete health/readiness and alerting baseline.
   - Harden Docker/runtime and add vulnerability scans.
3. By 90 days:
   - Enforce CI quality gates, finalize API error contracts, and complete backup/restore drills.
