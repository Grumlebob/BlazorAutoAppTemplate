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
- `docs/ENV.md`
- `HowToRun.md`
- deployment environment configuration

Definition of done:
- No real secrets in repo or docs.
- Secret rotation process is documented and tested.

## 3) Safe Database Migration Strategy

1. Disable automatic `db.Database.Migrate()` in production app startup.
2. Run migrations in a controlled deploy step/job before app rollout.
3. Add rollback guidance for failed migrations.

Implementation targets:
- `BlazorAutoApp/Program.cs`
- CI/CD workflow files (`.github/workflows/*`)
- `README.md` and `HowToRun.md`

Definition of done:
- Production app boot does not run schema changes automatically.
- Migration process is repeatable and documented.

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
- `.github/workflows/BuildAndTest.yml`
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

