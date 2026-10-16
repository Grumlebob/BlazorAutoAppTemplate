# LocalSingleNode operations

Use this guide for an already prepared native node. Workflow dispatches, reboot, restore and app removal require operator authorization. Use [AgentSetup](AgentSetup.md) for authorized first setup or resume, [ApplicationInstances](ApplicationInstances.md) for a second app, and [PublicSetup](PublicSetup.md) for tunnel and HTTPS changes. Commands that say “on the node” require its repository checkout.

## Release and rollback

From GitHub Actions, dispatch **CD - Deploy LocalSingleNode** from `main`. Require a successful publishing CI run for the exact selected SHA and record the workflow run ID before watching. If watching stops, inspect the same run; never dispatch another run to replace a watcher.

- Leave `target_sha` empty only when the dispatched `main` commit has a published release, or supply a full publishing SHA on `main`. A `[skip ci]` documentation commit has no release; see [source selection](../Common/ReleaseContract.md#select-a-published-source).
- Set `run_migrations=true` for the first deployment or a schema update. Use `false` when the selected release does not need a migration.
- The default `app_instance` is `primary`. Use `additional` only for a configured instance; see [ApplicationInstances](ApplicationInstances.md).

The deployment verifies the release manifest, immutable image digest, GHCR migration payload and acceptance profile before applying migrations. From the node's repository checkout, run the independent LAN check when needed:

```bash
bash ./Deployment/LocalSingleNode/Scripts/acceptance-check.sh
```

For a one-time legacy Data Protection import, set `data_protection_legacy_key_store` in the app settings to `Redis` and provide `data_protection_legacy_redis_key`, or select `FileSystem`. For FileSystem, copy the source XML key files to `/etc/<app-name>/data-protection/legacy`, owned by `root:deploy` mode `0440` inside a `root:deploy` mode `0750` directory. The app mounts that directory read-only at `/run/legacy-data-protection`. Deploy the first account/key-store transition with `run_migrations=true` to stop the app before schema changes. Wait for readiness, then set the store to `None`, clear the Redis key, and deploy again. Keep the source until the PostgreSQL key ring and existing authentication cookies have been verified.

For an app rollback before a migration, dispatch the prior verified `main` SHA with `run_migrations=false`; that SHA still needs its successful publishing run. After a migration, prefer a forward fix. Restoring an older backup loses later writes, and rolling back the app image does not roll back database changes. See [the release contract](../Common/ReleaseContract.md).

## Diagnose a running node

`doctor.sh --json` is read-only. Run it from the node's repository checkout:

```bash
bash ./Deployment/LocalSingleNode/Scripts/doctor.sh --json
```

Use its reported checks to identify what needs attention. Run `acceptance-check.sh` to verify LAN readiness and the configured HTTP acceptance profile. Use [Readiness](Readiness.md) for a pre-setup candidate check; it does not bootstrap, back up, deploy, restart or repair the node.

## Maintenance

The **LocalSingleNode maintenance** workflow runs against the selected app and uses the shared deployment lock. `backup_now` defaults to true; it creates a fresh protected backup and verifies an isolated restore. Keep `acceptance_only=false` for normal maintenance. Host maintenance stays manual; release artifact retention runs daily at 03:17 UTC for the primary app and 03:27 UTC for a configured additional app, and also runs on manual dispatch. It also prunes expired runner-local CI reports. GitHub artifact deletion stays in dry-run mode unless the repository variable `ACTIONS_ARTIFACT_RETENTION_ENABLED` is exactly `true`; leave it unset until current accepted/recovery pins and live operations are verified.

Use these options only when needed:

- `acceptance_only=true` runs HTTP acceptance without routine maintenance.
- `restart_app=true` requires `acceptance_only=true`; it restarts this app's web container and checks persistence.
- `restart_connector=true` also requires `acceptance_only=true` and checks this app's public connector. Keep it separate from an app restart.
- `reboot_check=true` reboots after the whole workflow succeeds. Additional app operations cannot reboot the shared host.

Select `app_instance=primary` or `additional` deliberately. See [ApplicationInstances](ApplicationInstances.md) for additional-app guards and host-wide operation limits. Public tunnel ownership, credential rotation and removal belong to [PublicSetup](PublicSetup.md).

### Setup and maintenance source

Additional-app setup and maintenance use [verify-operation-source.py](../Common/Scripts/verify-operation-source.py). They pin trusted `main` with full history. When ordinary documentation descendants skipped CI, the gate can use the nearest successful main CI only after proving the operation code is unchanged. Source/configuration changes, disguised Markdown in implementation directories, incomplete history, or an actual failed/pending run stop the operation. This exception validates operation code; it never selects release artifacts or relaxes CD's exact-source checks.

## Deployment lock recovery

Single-node workflows run on this node's self-hosted `deploy` runner. They use the shared `/tmp/localcluster-deploy.lockdir` to serialize app changes. The wrapper releases the lock after its command exits; it does not reclaim a lock left by an interrupted command.

If a workflow times out waiting for the lock, inspect it from the node's repository checkout:

```bash
sudo -u deploy bash ./Deployment/Common/Scripts/release-deploy-lock.sh --inspect
```

Confirm the owner process is gone and no `ansible-playbook` process runs as `deploy`. Release only the exact token printed by inspection:

```bash
sudo -u deploy bash ./Deployment/Common/Scripts/release-deploy-lock.sh --release --token <exact-token>
```

If the owner is on another host, confirm no deployment is active there and add `--owner-host-checked`. If the lock contains another app's metadata, stop and use that app's recovery tool. Never remove the lock by hand.

## Backups and recovery

The node creates a protected PostgreSQL backup nightly. Maintenance also creates and verifies a fresh backup by default. Each backup contains the database dump, `secrets.yml` (including the certificate passphrase), and `data-protection.pem` (the matching encrypted certificate/private key). Keep these files together in protected off-host storage. Verify the host key through [Controller SSH](ControllerSsh.md) before copying.

To verify the newest dump, run this from the node checkout as an account with Docker access:

```bash
bash ./Deployment/LocalSingleNode/Scripts/verify-backup.sh
```

To verify a specific dump, add `--file <backup-root>/<backup-file>.dump`. Verification restores it into an isolated, network-disabled temporary PostgreSQL container and removes only that container. This verifies database restore; retain the matching certificate and passphrase for app recovery.

Copy the configured backup directory to another machine or encrypted storage. Substitute the actual install user, node address, configured `backup_root`, and protected destination:

```bash
scp -r <install-user>@<node-ip>:<backup-root> <protected-destination>
```

Manual restore requires an operator decision. It creates a new `<database>_restore_<suffix>` database; it refuses the live or an existing target and does not switch application connections. Use the app's exact slug for confirmation and replace hyphens with underscores in the database name:

```bash
APP_NAME="your-app-slug"
DATABASE_NAME="${APP_NAME//-/_}"
sudo bash ./Deployment/LocalSingleNode/Scripts/verify-backup.sh \
  --restore-into "${DATABASE_NAME}_restore_recovery" \
  --confirm-restore "$APP_NAME"
```

Keep the complete target database name at 63 characters or fewer. The suffix must use lowercase letters, digits or underscores.

Add `--file <backup-root>/<backup-file>.dump` before the confirmation option to select a specific owned dump. For an additional app, select its persisted settings explicitly:

```bash
APP_NAME="your-app-slug"
DATABASE_NAME="${APP_NAME//-/_}"
sudo env LOCALSINGLENODE_SETTINGS_FILE="/etc/${APP_NAME}/settings.yml" \
  bash ./Deployment/LocalSingleNode/Scripts/verify-backup.sh \
  --restore-into "${DATABASE_NAME}_restore_recovery" \
  --confirm-restore "$APP_NAME"
```

For recovery on another node, restore `secrets.yml` to `/etc/<app-name>/secrets.yml` with owner `deploy` and mode `0600`, and restore `data-protection.pem` to `/etc/<app-name>/data-protection/certificate.pem` with owner `root`, group `deploy`, and mode `0440` before starting the app. Keep the same app name and Data Protection application discriminator. Database-only restore cannot decrypt stored keys, authentication cookies, or encrypted mail jobs.

Validate recovered data before planning a separate reviewed cutover. A failed partial replacement is left for operator inspection.

## Remove an application

Removal requires an explicit operator decision. Copy a verified backup off the node and record the exact app resources first. Disable this app's backup timer. Remove a runner only if it is dedicated to the removed app and no other app needs it.

Stop only this app's Compose project:

```bash
sudo docker compose --project-directory <deploy-root> --env-file <deploy-root>/.compose.env -p <app-name> down
```

Never add `--volumes`. Keep its PostgreSQL, Redis and app-storage volumes until the operator identifies the exact owned volume, verifies the off-host backup and removes that volume manually. Remove only this app's Caddy site; validate the shared Caddy configuration before reloading it. Retain protected backups and secrets until their removal is separately authorized. Do not uninstall shared host services or alter another app.
