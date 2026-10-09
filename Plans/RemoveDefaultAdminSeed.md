# Remove the Default Admin Seed

Status: Implementation complete.

Last updated: 2026-10-09.

Local gate passed: format verification, Release build, 173 tests, and deployment audit.

## Goal

Stop application startup from creating an Admin account with a published password. Keep the `Admin` role available for explicitly provisioned accounts. Preserve the existing local User demo account unless its separate credential risk is addressed in another change.

## Findings

- The deployment issue recorded as D15 is already fixed. `appsettings.Docker.json` disables local account seeding and contains no seeded passwords. LocalCluster and Cloud compose files set `LocalAccounts__Enabled` to `false`, and the deployment audit checks both settings.
- A known Admin login remains in `appsettings.Development.json` and as a fallback in `LocalLoginAccountSeedExtensions`. Root `docker-compose.yml` enables that seed for the local developer stack.
- The local app ports bind to `127.0.0.1`, which limits network reach, but source and local setup still publish a reusable Admin credential.
- `docs/HowToRunLocally.md` publishes that credential. `E2ELocalAdminCredentials` also falls back to it, and `BooksE2ETests` uses it to test an authenticated user flow.
- The seeder writes the local password hash directly. That path intentionally bypasses normal Identity password validation for local demo credentials, so it should not remain an Admin provisioning path.
- Deployment startup locks existing accounts that still use published default passwords and invalidates their sessions. Development startup does not currently lock an old default-password Admin, so disabling the seed alone would leave older local databases exposed.

## Plan

1. Remove Admin creation from application startup. Remove the Admin email and password from `appsettings.Development.json`, remove the Admin fallback and seeding branch from `LocalLoginAccountSeedExtensions`, and keep the `Admin` role supported. Do not replace the published password with another built-in credential.
2. Handle existing databases. On startup in every environment, lock a legacy `admin@admin.com` account only when it still matches the published default password, enable lockout, and update its security stamp. Preserve accounts whose password has changed. Keep Docker's existing lock for both published demo accounts.
3. Keep the local User demo account behavior unchanged. Root `docker-compose.yml` may continue enabling local account seeding for that account. Production compose flags and deployment audit rules remain in force.
4. Remove E2E dependence on the seeded Admin. Change the Books browser test to register a unique ordinary test user. Remove `E2ELocalAdminCredentials`, its fallback tests, and `LoginAsLocalAdminAsync` if no other callers remain. Update E2E documentation to describe the unique-user flow.
5. Update local-login documentation. Remove the Admin credentials and state that startup does not create an Admin account. Document that Admin accounts require an explicit operator-controlled provisioning action; do not add a replacement startup bootstrap flow in this change.
6. Add focused tests: startup seeding does not create the default Admin; a legacy Admin with the published password is locked and signed out in Development and Docker; a changed-password Admin remains usable; Docker still locks the published User account; the User local seed still works.
7. Run the repository local gate: `dotnet format BlazorAutoApp.sln --verify-no-changes`, Release build, Release tests, and deployment audit. Keep build and test sequential. Open a PR and merge only after `build-test-push` passes on the exact PR head.

## Acceptance criteria

- No app startup path creates or resets an Admin account using a source-controlled default password.
- Existing local default-password Admin accounts cannot sign in after startup; changed-password accounts remain intact.
- Local Docker and Development workflows still support the User demo account.
- E2E browser tests pass without the default Admin credentials.
- LocalCluster and Cloud remain audited with seeding disabled.
