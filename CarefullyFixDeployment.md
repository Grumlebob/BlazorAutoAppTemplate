# Carefully Fix Deployment

## Context

Latest CD reaches healthy app containers, healthy PostgreSQL, healthy Redis, and a valid Redis `PONG`, then fails on the PostgreSQL version check:

```text
postgres (PostgreSQL) 18.4expected PostgreSQL 18.4
```

The database is not the problem in this failure. PostgreSQL reports `18.4`; the acceptance script failed because it checked for contiguous text `PostgreSQL 18.4`, but PostgreSQL's standard output is `postgres (PostgreSQL) 18.4`.

## Goal

Make LocalCluster CD acceptance reliable, readable, and easy to diagnose. Do not disable any deployment safety checks. Do not weaken version checks. Do not do another destructive PostgreSQL/Redis reset unless there is a separate verified reason.

## Phase 1 - Confirm The Exact Failure

Status: Completed

- Reproduce the current shell comparison locally with a static string:

  ```bash
  v="postgres (PostgreSQL) 18.4"
  case "$v" in *"PostgreSQL 18.4"*) echo ok ;; *) echo failed ;; esac
  ```

- Confirm that the quoted `case` pattern is the failing piece.
- Confirm the deployment log already proves the remote PostgreSQL container reports `postgres (PostgreSQL) 18.4`.
- Confirm Redis already passed `PONG` in the latest CD log, so Redis auth is not the current blocker.
- Result: confirmed the version string shape was the root cause. Redis auth and Redis `PONG` were not the blocker.

## Phase 2 - Fix Fragile Version Checks

Status: Completed

- Replace the PostgreSQL `case` comparison in `Deployment/LocalCluster/Scripts/acceptance-check.sh` with a fixed-string check:

  ```bash
  printf '%s\n' "$postgres_version" | grep -F "(PostgreSQL) 18.4"
  ```

- Replace the Redis `case` comparison with the same style:

  ```bash
  printf '%s\n' "$redis_version" | grep -F "v=8.8.0"
  ```

- Keep printing the detected versions before checking them, so GitHub Actions logs remain useful.
- Ensure error messages include clean newlines and name the detected value when a version check fails.
- Keep the existing split checks for:
  - running `postgres` service
  - running `redis` service
  - `pg_isready`
  - Redis `PONG`
  - PostgreSQL version
  - Redis version
- Result: replaced both version `case` checks with fixed-string checks and preserved visible version output.

## Phase 3 - Reduce Future Acceptance Check Brittleness

Status: Completed

- Review every remaining one-line shell check in `acceptance-check.sh`.
- Replace hidden `grep -q` checks with visible output where failure diagnosis matters.
- Keep checks strict where they protect correctness, but make failures explain what value was observed.
- Avoid shell pattern matching for version validation.
- Prefer `grep -F` for literal version checks.
- Result: changed the app service check to print `web` and kept database checks split by concern.

## Phase 4 - Update Deployment Audit

Status: Completed

- Update `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` so it requires the fixed-string version check style.
- Ensure the audit rejects the old fragile `case "$version"` pattern if practical.
- Keep audit coverage for:
  - PostgreSQL 18.4 image pin
  - Redis 8.8.0 image pin
  - PostgreSQL readiness
  - Redis `PONG`
  - visible PostgreSQL version output
  - visible Redis version output
- Result: audit now requires fixed-string version checks, visible app service output, and diagnostic version mismatch messages.

## Phase 5 - Validate Locally

Status: Completed

- Run syntax validation:

  ```bash
  bash -n Deployment/LocalCluster/Scripts/acceptance-check.sh
  ```

- Run deployment static checks:

  ```bash
  bash Deployment/LocalCluster/Scripts/audit-deployment.sh
  bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
  ```

- Run lint gates:

  ```bash
  shellcheck --severity=warning Deployment/LocalCluster/Scripts/acceptance-check.sh
  actionlint
  yamllint .github Deployment/LocalCluster
  git diff --check
  ```

- Test the replacement version matching with literal strings before trusting it.
- If Docker is available locally, also test against local PostgreSQL 18.4 and Redis 8.8.0 containers.
- Result: syntax validation, audit, rendered template validation, ShellCheck, actionlint, yamllint, and diff whitespace checks passed. Linux-container command checks passed. Local Docker reports PostgreSQL 18.4 and Redis 8.8.0.

## Phase 6 - Production Retry Guidance

Status: Completed

- After pushing the fix and waiting for CI, rerun CD from `main`.
- Use `run_migrations: false` if the previous deployment already ran migrations and only acceptance failed.
- Leave both reset inputs empty unless a fresh database reset is intentionally required.
- If using the schema-only reset later, use `ship/ship`.
- If using the destructive PostgreSQL/Redis reset later, use `ship/postgres18-redis8-reset`.
- Confirm the acceptance log reaches:

  ```text
  acceptance check ok
  ```
- Result: retry guidance is recorded. Since the previous CD already got through app/database startup and failed only in acceptance, prefer `run_migrations: false` and leave reset inputs empty for the next retry unless a new migration or intentional reset is needed.

## Phase 7 - Follow-Up Cleanup

Status: Completed

- Consider extracting repeated remote shell snippets into small named functions or a remote helper block for readability.
- Consider reading expected PostgreSQL/Redis versions from one source of truth instead of repeating them in compose, tests, audits, and acceptance checks.
- Keep this follow-up non-blocking; the urgent fix is replacing the broken comparison.
- Result: follow-up is noted as non-blocking. No broad deployment refactor was made during this urgent fix.
