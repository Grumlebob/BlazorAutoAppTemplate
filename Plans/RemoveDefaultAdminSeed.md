# Remove the Default Admin Seed

Status: Follow-up PR pending.

Last updated: 2026-10-09.

Local gate passed: format verification, Release build, 174 tests (11 opt-in skips), deployment validators, rendered templates, yamllint, shellcheck, and actionlint.

## Goal

Stop application startup from creating an Admin account with a published password. Keep the `Admin` role available for explicitly provisioned accounts. Preserve the existing local User demo account unless its separate credential risk is addressed in another change.

## Findings

- The deployment issue recorded as D15 is already fixed. `appsettings.Docker.json` disables local account seeding and contains no seeded passwords. LocalCluster and Cloud compose files set `LocalAccounts__Enabled` to `false`, and the deployment audit checks both settings.
- A known Admin login remains in `appsettings.Development.json` and as a fallback in `LocalLoginAccountSeedExtensions`. Root `docker-compose.yml` enables that seed for the local developer stack.
- The local app ports bind to `127.0.0.1`, which limits network reach, but source and local setup still publish a reusable Admin credential.
- `docs/HowToRunLocally.md` publishes that credential. `E2ELocalAdminCredentials` also falls back to it, and `BooksE2ETests` uses it to test an authenticated user flow.
- The seeder writes the local password hash directly. That path intentionally bypasses normal Identity password validation for local demo credentials, so it should not remain an Admin provisioning path.
- Deployment startup locks existing accounts that still use published default passwords. Development startup does not currently lock an old default-password Admin, so disabling the seed alone would leave older local databases exposed.

## Plan

1. Remove Admin creation from application startup. Remove the Admin email and password from `appsettings.Development.json`, remove the Admin fallback and seeding branch from `LocalLoginAccountSeedExtensions`, and keep the `Admin` role supported. Do not replace the published password with another built-in credential.
2. Handle existing databases. On startup in every environment, lock a legacy `admin@admin.com` account only when it still matches the published default password, enable lockout, and update its security stamp. This blocks new logins immediately; existing sessions expire when Identity next validates the stamp. Preserve accounts whose password has changed. Keep Docker's existing lock for both published demo accounts. Fail startup if Identity cannot verify or lock a published default account.
3. Keep the local User demo account behavior unchanged. Root `docker-compose.yml` may continue enabling local account seeding for that account. Production compose flags and deployment audit rules remain in force.
4. Remove E2E dependence on the seeded Admin. Change the Books browser test to register a unique ordinary test user. Remove `E2ELocalAdminCredentials`, its fallback tests, and `LoginAsLocalAdminAsync` if no other callers remain. Update E2E documentation to describe the unique-user flow.
5. Update local-login documentation. Remove the Admin credentials and state that startup does not create an Admin account or provide an Admin provisioning workflow. Do not add a replacement startup bootstrap flow in this change.
6. Add focused tests: startup does not create the default Admin and creates only the configured local User; a later startup locks a legacy default-password Admin; a changed-password account remains usable; Docker still locks the published User account; repeated locking is idempotent; and startup fails if it cannot verify a published account.
7. Run the repository local gate: `dotnet format BlazorAutoApp.sln --verify-no-changes`, Release build, Release tests, and deployment audit. Keep build and test sequential. Open a PR and merge only after `build-test-push` passes on the exact PR head.

## Acceptance criteria

- No app startup path creates or resets an Admin account using a source-controlled default password.
- Existing local default-password Admin accounts cannot sign in after startup; changed-password accounts remain intact.
- Local Docker and Development workflows still support the User demo account.
- E2E browser tests pass without the default Admin credentials.
- LocalCluster and Cloud remain audited with seeding disabled.

## Review hardening

The follow-up review found that legacy account verification errors were logged and swallowed, allowing startup to continue with an account that might still accept the published password. The lock path now logs at critical level and rethrows. Its unused lock count was removed, seed-only implementation details were made private, and integration coverage now exercises both no-Admin seeding and legacy Admin locking through Development startup. The test factory runs migrations before startup checks; configuration-only host tests use an empty Identity store. Documentation now describes security-stamp session expiry accurately and does not imply that this template includes an Admin provisioning workflow.
