# LocalCluster operations

Use this guide after initial setup. It covers routine releases, diagnosis, backup and recovery, and shared-host maintenance. For the settings and task-specific commands, use [LocalCluster settings](Settings.md).

## Routine deployments

Run on GitHub:

1. Push or merge code to main.
2. Require CI to pass for the selected commit.
3. Run CD - Deploy LocalCluster from main.
4. Set run_migrations to true when that commit includes EF migrations.
5. Run the acceptance check.

Useful control-machine commands:

```bash
bash ./Deployment/LocalCluster/Scripts/doctor.sh deploy
bash ./Deployment/LocalCluster/Scripts/preflight.sh deploy
bash ./Deployment/LocalCluster/Scripts/summary.sh
bash ./Deployment/LocalCluster/Scripts/report-nodes.sh
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
bash ./Deployment/LocalCluster/Scripts/observability-doctor.sh
bash ./Deployment/LocalCluster/Scripts/check-github-runner.sh
# Optional; requires Cloudflare API credentials:
bash ./Deployment/LocalCluster/Scripts/check-cloudflare-tunnel.sh
```

Doctor checks prerequisites. Preflight checks the selected deploy. Acceptance checks app, data services, Caddy, Cloudflared, and public readiness. Observability doctor checks telemetry after acceptance succeeds.

Runner policy: CI and deployment workflows use the configured LocalCluster self-hosted runner on node-main. External fork pull requests are skipped before a runner is allocated. Never add GitHub-hosted runner labels; the deployment audit rejects them. Do not run untrusted pull request code on the self-hosted runner.

## Diagnose a failed deploy

Start with doctor, then preflight and node report:

```bash
bash ./Deployment/LocalCluster/Scripts/doctor.sh deploy
bash ./Deployment/LocalCluster/Scripts/preflight.sh deploy
bash ./Deployment/LocalCluster/Scripts/report-nodes.sh
```

Check service logs from the control machine:

```bash
ansible app_servers -i Deployment/LocalCluster/inventory/prod/hosts.yml -m ansible.builtin.shell -a "cd <deploy-root> && docker compose logs --tail=100"
ansible node_db -i Deployment/LocalCluster/inventory/prod/hosts.yml -m ansible.builtin.shell -a "cd <deploy-root> && docker compose logs --tail=100"
ansible load_balancer -i Deployment/LocalCluster/inventory/prod/hosts.yml -a "journalctl -u caddy --no-pager -n 100"
ansible load_balancer -i Deployment/LocalCluster/inventory/prod/hosts.yml -a "journalctl -u cloudflared --no-pager -n 100"
```

If public health fails, run acceptance-check.sh. If local Caddy health fails, inspect app-node health and Caddy logs. If local Caddy health passes but public health fails, check the Cloudflare hostname service URL is 127.0.0.1:80 and verify the tunnel. A Caddy 503 with healthy app nodes can occur during restart; acceptance-check.sh retries it. Use its rendered Caddy site and logs if the retry still fails.

## Backup and restore

Deployment migrations create a backup first. Verify the latest backup before relying on it:

```bash
bash ./Deployment/LocalCluster/Scripts/verify-backup.sh
bash ./Deployment/LocalCluster/Scripts/verify-backup.sh <deploy-root>/backups/<backup-file>.sql.gz
```

To verify one file, pass its full backup path. To restore, identify the exact file and confirm its app/database identity. Restore is manual and can lose writes made after the backup:

```bash
ansible node_db -i Deployment/LocalCluster/inventory/prod/hosts.yml -a "<deploy-root>/restore-db.sh <deploy-root>/backups/<backup-file>.sql.gz --confirm <app_name>/<postgres_database_name>"
```

Do not run a restore until the backup passes verify-backup.sh and the expected data-loss point is understood.

## Rollback

Before a database migration, run CD - Deploy LocalCluster for the prior main commit with run_migrations=false. CD checks that commit's CI and release provenance. The last two successful deployment releases are retained.

After a migration, prefer a forward-fix migration. Restoring an older backup loses later writes; verify the file and confirm the data-loss decision first. See [the shared release contract](../Common/ReleaseContract.md) for the artifact and image checks.

Manual deployment is an exception. The deploy.sh wrapper uses the same deployment lock and strict SSH host-key checking. Compare fingerprints through [SSH host trust](../Common/SshTrust.md). It skips some successful-CI and manifest checks that CD performs, so use CD for normal releases.

If manual deployment is required, pin the selected commit and image digest. For migrations, provide the matching local bundle:

```bash
bash ./Deployment/LocalCluster/Scripts/deploy.sh <git-sha> --digest sha256:<digest>
bash ./Deployment/LocalCluster/Scripts/deploy.sh <git-sha> --migrate <path-to-migration-bundle> --digest sha256:<digest>
```

## Runtime and data boundaries

Caddy and Cloudflared run on node-main. App containers run on the app nodes. PostgreSQL and Redis run on node-db and accept traffic only from app nodes. Public ingress goes through Cloudflare Tunnel to Caddy on 127.0.0.1:80. Do not add router port forwarding for app, database, Redis, or observability ports.

PostgreSQL and Redis use persistent Docker volumes. Do not prune Docker volumes. They contain database and runtime state. The deployment playbook applies firewall rules, handles database backup and optional migrations, starts app nodes, then checks readiness. See the playbook at ansible/playbooks/site.yml for exact order.

## Replace an app identity

Use this only when intentionally replacing an app identity on the same nodes. It creates a new deploy key, runner, runtime root, Caddy site, Compose project, and ownership marker. Plan data retention or migration before continuing. Review the helper's dry run:

```bash
bash ./Deployment/LocalCluster/Scripts/prepare-renamed-localcluster-app.sh --old-app-name <old-app-name>
```

After committing the new settings and inventory, prepare the replacement and confirm the cutover:

```bash
OLD_APP_NAME="<old-app-name>"
bash ./Deployment/LocalCluster/Scripts/prepare-renamed-localcluster-app.sh \
  --old-app-name "$OLD_APP_NAME" \
  --setup-control-machine \
  --install-new-key \
  --existing-key "$HOME/.ssh/${OLD_APP_NAME}_deploy" \
  --configure-runner \
  --stop-old-runtime \
  --remove-old-marker \
  --preflight \
  --confirm-cutover
```

After acceptance-check.sh passes, remove only the old app's owned runtime resources:

```bash
bash ./Deployment/LocalCluster/Scripts/cleanup-renamed-localcluster-app.sh --old-app-name <old-app-name> --confirm-cleanup
```

Keep the old deploy key while it may be needed for rollback. Add --remove-old-deploy-key only when the old key is no longer needed.

## Deployment lock

Every mutating deploy holds one lock directory on node-main. Apps on the same nodes share it. The lock is never removed automatically, even when old. A cancelled job may leave ansible-playbook running.

If a deploy waits on the lock, inspect its owner on node-main:

```bash
bash ./Deployment/Common/Scripts/release-deploy-lock.sh --inspect
```

Release only after proving the owner process is gone. The release script refuses a mismatched token, a live owner, a running ansible-playbook, or another app's lock metadata. For a manual deploy, check the control machine first and then pass --owner-host-checked:

```bash
bash ./Deployment/Common/Scripts/release-deploy-lock.sh --release --token <token-from-inspect> --owner-host-checked
```

Never delete the lock directory directly.

## Low Runner Disk

CI reports disk use but does not prune the shared Docker daemon on node-main. If CI reports that node-main is below its capacity reserve, inspect first:

```bash
bash ./Deployment/LocalCluster/Scripts/check-node-main-capacity.sh
bash ./Deployment/LocalCluster/Scripts/prune-docker-residue.sh --dry-run --force
docker system df
du -xh --max-depth=1 /opt | sort -h
```

The dry run lists old unused LocalCluster image tags. The helper removes only resources it can identify as safe. Host-wide cleanup can affect every app on node-main; inspect candidates before using --include-unlabelled-host-residue. Never prune Docker volumes.

### Runner And Docker Storage Maintenance

The LocalCluster Docker Maintenance workflow runs on node-main under the shared deployment lock. It is manual by default. Review its stages in .github/workflows/localcluster-docker-maintenance.yml and the called run-localcluster-maintenance.sh before changing its schedule.

The cleanup is scoped to this repository's runner files, CI residue, and app image tags. It keeps active runner versions, workspaces in use, running/deployed images, persistent mounts, and volumes. It also reports volume use without deleting volumes. The artifact job keeps recent releases and those behind the last two successful deployments.

Low-disk recovery on node-main:

```bash
bash ./Deployment/LocalCluster/Scripts/check-node-main-capacity.sh
bash ./Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh --capacity-only
bash ./Deployment/LocalCluster/Scripts/prune-docker-residue.sh --dry-run --force
```

The capacity-only script needs GITHUB_WORKSPACE; prefer the maintenance workflow for normal use. Recheck capacity after cleanup.

### Tool provisioning: --check versus --provision

CI, CD, and maintenance only check the toolchain. They run install-ansible.sh --check and ensure-actions-runner-prereqs.sh --check, which do not call apt or sudo. Install or upgrade tools deliberately on the control machine with setup-control-machine.sh, which calls install-ansible.sh --provision. If a workflow reports a missing or invalid Ansible generation, provision through the supported script and rerun the workflow.
