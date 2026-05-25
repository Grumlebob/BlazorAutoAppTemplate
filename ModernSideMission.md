# Modern Side Mission: Fresh Migration And Deployment Recovery

Status: plan created on 2026-05-25; deployment error captured on 2026-05-25; repo-side migration recovery executed on 2026-05-25.

Purpose: fix the deployment migration failure and deliberately reset the current deployment database because there is no real data in it right now.

Important boundary: this plan is intentionally destructive to the current deployment database only when executed. It must not be treated as a general migration strategy for later, real production data.

## Current Situation

- Deployment failed during EF migrations.
- The exact failure is now known:
  - Ansible task: `Run migration bundle`
  - Host: `node-db`
  - Bundle: `./migrations/ship-migrate`
  - Migration being applied: `20260524175426_InitialTemplateSchema`
  - Failed SQL: `CREATE TABLE "AspNetRoles" (...)`
  - PostgreSQL error: `42P07: relation "AspNetRoles" already exists`
- The migration bundle command connected successfully and started applying EF migrations. This was not a chmod, copy, network, or PostgreSQL authentication problem.
- The repo currently has one EF migration:
  - `BlazorAutoApp/Infrastructure/Persistence/Migrations/20260524175426_InitialTemplateSchema.cs`
- That migration contains only the current template schema:
  - ASP.NET Core Identity tables, including passkeys.
  - `Books`.
- No `Inspections`, TUS, upload, or old image tables are present in the current migration files.
- The LocalCluster deployment keeps PostgreSQL data in the `postgres_data` Docker volume.
- If the deployed database already contains older tables and older `__EFMigrationsHistory` rows from previous app versions, a squashed/fresh initial migration can fail by trying to create tables that already exist.

## Working Theory

Status: confirmed by deployment error.

The failure is not that the current migration still contains old app features. The mismatch is:

- The repo was squashed down to a fresh initial migration.
- The deployed PostgreSQL volume still has an older schema/history from before that squash.
- EF sees the current initial migration as not applied and tries to apply it against a non-empty database.
- PostgreSQL rejects the first Identity table creation because `"AspNetRoles"` already exists.

Because there is no real data right now, the cleanest fix is to reset the deployed database and generate a fresh baseline migration from the current model.

Important consequence: regenerating the migration alone will not fix this deployment. The deployed database must be made fresh, or EF must be told that an equivalent migration already exists. Because this database is disposable right now, use the fresh database/reset path instead of stamping old schema history.

## Phase 1: Capture The Actual Error

Status: done.

Steps:

1. Collect the failed GitHub Actions job log or Ansible migration output.
2. Record the exact migration bundle command that failed.
3. Record whether the failure happened during:
   - backup creation
   - copying/chmod of the migration bundle
   - connecting to PostgreSQL
   - applying EF migration SQL
   - later app startup health checks
4. Add the exact error under this section before executing code or deployment changes.

Done when:

- The failure has a concrete message and stack trace, not only "migration failed".
- Captured root error: `42P07: relation "AspNetRoles" already exists`.
- Captured migration: `20260524175426_InitialTemplateSchema`.
- Captured failed task: `Deployment/LocalCluster/ansible/playbooks/site.yml`, task `Run migration bundle`.

## Phase 2: Confirm The Intended Reset Scope

Status: partially done; remote database name is encrypted in Ansible Vault.

Steps:

1. Confirm the reset is only for the current LocalCluster/template deployment database.
2. Confirm Redis should not be reset unless runtime state also needs a clean start.
3. Confirm the app is stopped before resetting PostgreSQL.
4. Keep a backup step even though the database is considered disposable, because it protects against a mistaken environment target.

Done when:

- The target deploy root, app name, database name, and node-db host are known.
- A one-line confirmation token is written down in the shape `<app_name>/<postgres_database_name>`.

Execution notes:

- Known target app: `ship`.
- Known deploy root: `/opt/ship`.
- Known node-db host from inventory: `node-db`, `192.168.0.169`.
- Known migration bundle name: `ship-migrate`.
- Database name is stored in `Deployment/LocalCluster/inventory/prod/vault.yml`, which is encrypted. The final confirmation token must be `ship/<POSTGRES_DB from vault or /opt/ship/.env>`.
- This workstation cannot perform the remote reset directly because Ansible is not installed here and `~/.ssh/ship_deploy` is not present.

## Phase 3: Regenerate A Fresh EF Baseline Migration

Status: done.

Note: the current repo already has a single clean initial migration with only Identity/passkeys and Books. This phase is still valid if the goal is a new timestamp/name and a completely freshly generated baseline, but it is not the fix for the observed deployment failure by itself. Phase 6 is required because the deployed database already has tables.

Steps:

1. Remove the current migration files from `BlazorAutoApp/Infrastructure/Persistence/Migrations`.
2. Generate a new initial migration from the current model:

   ```powershell
   dotnet ef migrations add InitialTemplateSchema `
     --project .\BlazorAutoApp\BlazorAutoApp.csproj `
     --startup-project .\BlazorAutoApp\BlazorAutoApp.csproj `
     --output-dir Infrastructure\Persistence\Migrations
   ```

3. Review the generated migration carefully.
4. Verify it contains only:
   - Identity schema version 3/passkey-capable Identity tables.
   - `Books`.
5. Verify it contains no:
   - Inspections.
   - uploads.
   - TUS.
   - ImageSharp/image processing tables.
   - stale feature tables.

Done when:

- `dotnet ef migrations list` shows exactly one intended initial migration.
- The generated snapshot matches the current `AppDbContext` model.

Execution notes:

- Removed old baseline migration `20260524175426_InitialTemplateSchema`.
- Generated fresh baseline migration `20260525172002_InitialTemplateSchema`.
- Verified the generated migration contains Identity/passkey tables and `Books`.
- Verified no generated migration content contains `Inspection`, `Tus`, `Upload`, or stale image-processing tables.
- `dotnet ef migrations list --project .\BlazorAutoApp\BlazorAutoApp.csproj --startup-project .\BlazorAutoApp\BlazorAutoApp.csproj` shows exactly:
  - `20260525172002_InitialTemplateSchema (Pending)`

## Phase 4: Test The Fresh Migration Locally Before Deployment

Status: done.

Steps:

1. Start a disposable local PostgreSQL database or use the test/container setup.
2. Apply the new migration to an empty database.
3. Verify the schema:
   - `Books`
   - Identity tables
   - `__EFMigrationsHistory`
4. Run the app against that fresh database.
5. Run integration tests that cover Identity startup and Books endpoints.

Done when:

- The fresh migration applies cleanly to an empty PostgreSQL database.
- The app starts cleanly.
- The relevant tests pass.

Execution notes:

- Started a disposable `postgres:16.14-alpine3.23` container.
- Applied the fresh migration with `dotnet ef database update`.
- Verified expected tables:
  - `__EFMigrationsHistory`
  - `AspNetRoles`
  - `AspNetUsers`
  - `AspNetUserPasskeys`
  - `Books`

## Phase 5: Build And Test The Migration Bundle

Status: done.

Steps:

1. Build the bundle with the same shape as CI:

   ```powershell
   dotnet ef migrations bundle `
     --project .\BlazorAutoApp\BlazorAutoApp.csproj `
     --startup-project .\BlazorAutoApp\BlazorAutoApp.csproj `
     --configuration Release `
     --self-contained `
     --runtime linux-x64 `
     --output .\artifacts\migrations\<migration_bundle_name>
   ```

2. Test the bundle against a disposable empty PostgreSQL database.
3. Confirm the bundle is executable in Linux deployment.

Done when:

- The migration bundle applies the fresh initial migration to an empty database.

Execution notes:

- Built the deployment-shaped Linux bundle inside `mcr.microsoft.com/dotnet/sdk:10.0`, not from the Windows SDK, so the result is an ELF Linux executable.
- Output bundle: `artifacts/migrations/ship-migrate`.
- Tested that Linux bundle inside `mcr.microsoft.com/dotnet/runtime-deps:10.0` against a fresh PostgreSQL container.
- Verified the bundle applied `20260525172002_InitialTemplateSchema` and created the expected Identity/passkey, Books, and EF history tables.

## Phase 6: Reset The Current Deployment Database

Status: tooling done; remote reset blocked on control-machine prerequisites.

This phase is destructive to the current deployment database. It is acceptable only because the user stated on 2026-05-25 that there is no real data right now.

Recommended option for this exact failure:

1. Use a fresh database name if you want maximum reversibility:
   - Change `vault_postgres_db` to a new database name.
   - Keep `vault_postgres_user` and password if desired.
   - Re-render/deploy node-db config.
   - Run the migration bundle against the new empty database.

Alternative options:

1. Drop and recreate the current database inside the existing PostgreSQL container.
2. Remove the LocalCluster `postgres_data` Docker volume for this app.

Avoid:

- Do not retry the current migration bundle against the same non-empty database. It will fail again at `"AspNetRoles"` unless the database is reset or migration history/schema are manually reconciled.
- Do not manually insert the new migration ID into `__EFMigrationsHistory` for this case. That hides the mismatch and is inappropriate when a fresh database is acceptable.

Required safety steps:

1. Stop app containers before the reset.
2. Run the existing backup script if PostgreSQL is healthy enough:

   ```bash
   ./backup-db.sh
   ```

3. Print the target app/database before any destructive command.
4. Require explicit confirmation token `<app_name>/<postgres_database_name>`.
5. Reset only the intended app's PostgreSQL data.

Done when:

- The deployment database is empty/fresh.
- PostgreSQL health check passes.
- `__EFMigrationsHistory` is empty or absent before the new migration bundle runs.
- `"AspNetRoles"` and other app tables are absent before the new initial migration runs.

Execution notes:

- Added guarded node-db reset script:
  - `Deployment/LocalCluster/Scripts/Component/node-db/reset-db.sh`
- Added `deploy.sh --reset-db <app-name>/<database-name>` support.
- `deploy.sh` refuses `--reset-db` unless `--migrate` is also supplied, so the fresh database is immediately migrated.
- The Ansible playbook now stops app containers before reset, creates a backup, runs the guarded reset, then runs the migration bundle.
- The remote reset itself was not run from this workstation because Ansible is unavailable here and the configured SSH deploy key is missing.

Command to run from the GitHub runner/control machine that has Ansible, the vault password, and the deploy key:

```bash
bash Deployment/LocalCluster/Scripts/deploy.sh <git-sha> \
  --migrate artifacts/migrations/ship-migrate \
  --reset-db ship/<POSTGRES_DB>
```

Replace `<POSTGRES_DB>` with the actual database name from the vault or from `/opt/ship/.env` on `node-db`.

## Phase 7: Deploy With The Fresh Migration Bundle

Status: pending; blocked from this workstation by missing Ansible/deploy key.

Steps:

1. Deploy with migrations enabled:

   ```bash
   bash Deployment/LocalCluster/Scripts/deploy.sh <git-sha> --migrate <path-to-migration-bundle>
   ```

2. Confirm the Ansible migration task runs on `node_db`.
3. Confirm the migration bundle connects through:

   ```text
   Host=localhost;Port=$POSTGRES_PORT;Database=$POSTGRES_DB;Username=$POSTGRES_USER;Password=$POSTGRES_PASSWORD
   ```

4. Confirm app servers start after the migration succeeds.

Done when:

- Migration bundle exits successfully.
- App containers are running.
- `/health/ready` passes through the deployed route.

## Phase 8: Post-Deployment Verification

Status: pending; blocked until Phase 7 runs on the deployment runner/control machine.

Steps:

1. Run deployment acceptance checks.
2. Open the deployed app.
3. Verify Books home page loads.
4. Create, view, edit, and delete a Book.
5. Register/login if Identity is expected to be active in this environment.
6. Confirm no startup migration is running in app containers:
   - production compose should keep `Database__RunMigrationsAtStartup: "false"`.
   - migrations should be performed by the migration bundle only.

Done when:

- Deployed app works on a fresh schema.
- No migration failure appears in app or deployment logs.

## Phase 9: Make The Template Safer For Future Squashes

Status: done for the deployment reset guardrail.

Steps:

1. Document that migration squashing requires a fresh database or a deliberate data migration path.
2. Add a deployment troubleshooting section for:
   - "relation already exists"
   - duplicate object/index errors
   - old `__EFMigrationsHistory` rows after a migration squash
   - connection failures from the bundle to PostgreSQL
3. Consider adding a guarded reset script for disposable LocalCluster template databases.
4. Ensure the reset script cannot run unless the confirmation token matches `<app_name>/<postgres_database_name>`.

Done when:

- Future template users understand the difference between:
  - normal additive migrations with real data
  - a destructive fresh baseline reset for disposable databases

Execution notes:

- Added a confirmation-token reset script that refuses to run unless the token matches `<APP_NAME>/<POSTGRES_DB>`.
- The reset script validates PostgreSQL identifiers and refuses to reset `postgres`, `template0`, or `template1`.
- `deploy.sh --reset-db` is intentionally coupled to `--migrate`.
- Deployment script docs now mention the guarded disposable reset command.

## Final Acceptance

Status: pending.

Required local checks:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --configuration Release --no-restore
dotnet test .\BlazorAutoApp.sln --configuration Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore
dotnet ef migrations list `
  --project .\BlazorAutoApp\BlazorAutoApp.csproj `
  --startup-project .\BlazorAutoApp\BlazorAutoApp.csproj
```

Required deployment checks:

```bash
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
bash Deployment/LocalCluster/Scripts/deploy.sh <git-sha> --migrate <path-to-migration-bundle>
bash Deployment/LocalCluster/Scripts/acceptance-check.sh
```

Execution status:

- There is exactly one fresh initial migration matching the current model.
- The Linux migration bundle applies cleanly to a fresh PostgreSQL database.
- Production startup migrations remain disabled.
- Deployment audit and rendered-template validation pass.
- The current disposable deployment database was not reset from this workstation because the workstation lacks Ansible and `~/.ssh/ship_deploy`.
- Deployment health and app workflows still need to be checked after running the guarded reset deploy command from the real deployment runner/control machine.
