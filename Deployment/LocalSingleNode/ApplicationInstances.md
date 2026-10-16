# Application instances on one native node

This repository supports a `primary` app and one optional `additional` app using the other frontend profile. Both use the existing native runner. The primary app uses tracked settings and the selected profile; the additional app uses separate protected environment settings.

## Prepare an additional app on an existing node

Obtain operator authorization for setup and deployment. Run controller commands from the repository root.

1. Confirm the primary app is healthy, its ownership is recorded, and its backup is fresh. Use [readiness](Readiness.md) when evaluating candidate settings. Reuse the existing runner; do not bootstrap the node or install another runner.
2. Enable publication of the other profile through [ADDITIONAL_FRONTEND_PROFILES](../../docs/FrontendProfiles.md#publish-the-other-profile). Choose a successful publishing run on `main` containing that profile's image and migration artifact; see the [release contract](../Common/ReleaseContract.md).
3. Create a protected GitHub environment with deployment restricted to `main`. Set repository variable `LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT` to its name. It must differ from `LOCALSINGLENODE_ENVIRONMENT` (default `localsinglenode`). Keep the existing host and runner variables.
4. Store the JSON below as that environment's `LOCALSINGLENODE_APP_INSTANCE` secret. Keep the source file private; do not paste installation values into workflow inputs, logs, PRs, or tracked files.
5. Dispatch [LocalSingleNode additional app setup](../../.github/workflows/localsinglenode-app-setup.yml) from trusted `main`. Record its run ID and inspect that run until it succeeds. Setup uses the [operation source gate](Operations.md#setup-and-maintenance-source), rechecks ownership, collisions, workload, backups and capacity under the shared lock, and prepares app-owned roots, fresh secrets and backup integration. It does not adopt existing data, restart shared services, publish DNS or start the app. On failure, inspect the reported phase and fix the cause; preserve owned files and volumes.
6. For public HTTPS, complete [Public setup](PublicSetup.md#agent-execution) with the additional-environment options before deployment. For LAN-only use, leave `public` empty. Dispatch **CD - Deploy LocalSingleNode** from `main` with `app_instance=additional`, `run_migrations=true` for the new database, and `target_sha` set to the full publishing SHA chosen in step 2. Setup success alone is not a deployment. Require workflow and selected-profile acceptance success; inspect the same recorded run if watching stops.

## Instance settings

This example assumes the primary profile is `BlazorAuto`. Select `BlazorAuto` here when the primary is `React`. Values illustrate the schema; choose actual values after native collision and capacity checks.

```json
{
  "schema_version": 1,
  "frontend_profile": "React",
  "settings": {
    "app_name": "catalog",
    "app_port": 18080,
    "postgres_port": 15432,
    "redis_port": 16379,
    "deploy_root": "/opt/catalog",
    "docker_subnet": "172.30.20.0/24",
    "lan_http_port": 18081,
    "lan_hostnames": ["catalog.local"],
    "backup_root": "/opt/catalog-backups",
    "backup_keep_days": 7,
    "observability_enabled": false
  },
  "public": {}
}
```

Settings must match the current [LocalSingleNode settings schema](inventory/group_vars/all.yml). The app name and LAN names must differ from the primary. None of its four ports may match any primary service port. Docker subnets must not overlap. App and backup roots must be disjoint and cannot contain one another. Keep observability disabled. Duplicate/unknown keys, unsupported profiles and repeating the primary profile are rejected. Never copy primary credentials or data into the additional app. Optional legacy Data Protection import settings belong to the target app; for FileSystem imports, stage its source files under `/etc/<app-name>/data-protection/legacy` on the node before deploying.

For public HTTPS, the helper in [Public setup](PublicSetup.md#agent-execution) fills `public` with `hostname`, `tunnel_id` and integer `origin_port`, then stores the matching `LOCALSINGLENODE_PUBLIC_TUNNEL_TOKEN` in the additional environment. Pass both `--environment <additional-environment>` and `--instance-config-file <private-instance.json>` to its configuration command. The private instance file requires current-user ownership, a mode-0700 parent directory and mode-0600 file. Public identity comes from this instance, never the primary app. An already published app cannot silently clear its recorded public configuration.

Additional release names derive from shared settings: `<app_image>-<lowercase-profile>` and `<migration_artifact_name>-<lowercase-profile>`. CD checks the selected profile independently of the downloaded manifest and requires the matching immutable image and artifact for the exact publishing source.

## Maintain and verify an application

Use [Operations](Operations.md) for releases, diagnosis, maintenance, backups and recovery. Select `app_instance=additional` deliberately in CD and maintenance; both use the same protected environment. Additional-app operations cannot reboot the shared host. The [maintenance options](Operations.md#maintenance) describe normal backup and optional persistence/connector checks.

On-node scripts default to the primary settings. For the additional app, explicitly select its persisted `/etc/<app_name>/settings.yml` through `LOCALSINGLENODE_SETTINGS_FILE`; see the [restore example](Operations.md#backups-and-recovery). Keep installation files private. Restore only this app's owned backup, and preserve the primary app's services, credentials and data.

The [instance resolver](Scripts/resolve-app-instance.py) and [setup workflow](../../.github/workflows/localsinglenode-app-setup.yml) define validation and ownership checks when changing this procedure.
