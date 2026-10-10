# Deploy LocalSingleNode

Deploy web, PostgreSQL and Redis to one native Linux Mint PC. Host Caddy exposes plain HTTP on the LAN; database, Redis and web ports bind only to loopback. There is a short interruption when the web container stops for migrations or starts a new release. Observability and internet tunnels are outside this target's setup.

## Start with the local agent

Use the existing clone on the intended deployment PC and update it to the verified `origin/main`. Preserve local changes; never clone over the directory or reset them. Start Codex or Claude Code in that clone and give it this prompt:

> You are running on the native Linux deployment PC. Set up this current machine as a LocalSingleNode node. Follow Deployment/LocalSingleNode/AgentSetup.md. Use the current hostname unless I provide a node name. Detect and confirm the LAN address before changes. Complete agent steps; ask me only for GitHub authentication or the printed sudo command. Deploy LocalSingleNode only. Report the site URL, CD run URL, deployed SHA and image digest.

If you have a reserved address or intended node name, add them to the prompt. The canonical [AgentSetup.md](AgentSetup.md) contains the execution loop and boundaries; this guide explains operation and recovery. Windows and WSL are controller/test environments and cannot be deployment nodes.

| Stage | Operator | Local agent |
| --- | --- | --- |
| Native host | Confirm this is the PC to provision; connect it to the LAN | Show hostname, default-route IPv4 and detected LAN CIDR; stop if a supplied address differs |
| Repository and tools | Preserve any uncommitted work | Validate clean main, install the checksum-verified user-local GitHub CLI if missing |
| GitHub | Authenticate in the browser when requested, using repository-admin access | Check authentication and admin access; never ask for or handle a password/token |
| Fork and CI | Choose an app name only if customization needs one | Follow the fork PR/local-gate/exact-head-CI/green-main process; defer until runner capacity exists when necessary |
| Root bootstrap | Run the single complete `sudo bash ...bootstrap-node.sh ... --yes` command printed by status; type the password yourself | Never run sudo or edit `/etc` manually; resume after the operator reports completion |
| Variables, runner, deployment | Nothing further unless status reports a human blocker | Set authorized variables, wait for the app runner, reuse/record the initial CD run, then run HTTP acceptance |
| Independent acceptance | Use the main PC/controller session | Main-PC agent runs its own LAN HTTP check and records the result |

Bootstrap installs packages, approved hostname, machine facts, Ansible, Docker/Caddy/UFW, protected secrets/backups and an app-specific Actions service. It imports the operator's public GitHub SSH keys before hardening SSH; no imported keys means password SSH stays enabled. It preserves existing matching registrations, secrets and data volumes. Each numbered failure prints the same operator command to rerun.

Caddy uses the official GitHub release Debian package, with its version and architecture-specific SHA-256 checksums pinned in `Deployment/Common/ansible/roles/caddy_install/defaults/main.yml`. Update the version and checksums together through a PR to upgrade it through provisioning. Bootstrap and shared provisioning retire only the exact legacy Cloudsmith source created by this repository, preserving it as `caddy-stable.list.disabled` before apt updates. Foreign source contents or conflicting backups stop setup for operator inspection.

The runner's `deploy` account has Docker group access and passwordless sudo. Both confer root-equivalent power. The install user gets no sudoers change. A fresh one-PC fork can explicitly enable `--ci-runner`, which also grants the install user Docker group access for its local gates; use a fresh group session afterwards. The template's existing CI capacity stays on its current runner.

## Portable settings

Edit `inventory/group_vars/all.yml` through the normal PR process. Keep the internal app slug consistent with the fork settings used by CI. The shared image and migration identity lives in `../Common/release.yml`.

| Setting | Default | Rule |
| --- | --- | --- |
| `app_name` | `books` | Lowercase slug; unique per app on the host |
| `deploy_root` | `/opt/books` | This app's runtime directory below `/opt` |
| `app_port` / `postgres_port` / `redis_port` | `8080` / `5432` / `6379` | Distinct unused host ports, loopback only |
| `docker_subnet` | `172.30.10.0/24` | Private IPv4 subnet; no overlap with LAN or another Docker network |
| `lan_http_port` | `80` | First app can use 80; another app needs its own port, such as 8081 |
| `lan_hostnames` | `[]` | Optional names already resolving to this PC; setup does not create DNS aliases |
| `backup_root` / `backup_keep_days` | `/opt/books-backups` / `7` | Separate protected directory; positive retention |
| `observability_enabled` | `false` | Remains false for this target |

Machine values are detected on the node and stored in `/etc/localsinglenode/machine.yml`. The optional ignored `machine.yml` uses [machine.example.yml](machine.example.yml); it must agree with the intended host, user and address. Never commit real machine facts or runtime `.env`/secrets. CD refreshes the live address, warns if it changed, and preserves the install user. Use a DHCP reservation for a stable URL.

The site is `http://<node-name>.local:<lan_http_port>/` or `http://<node-ip>:<lan_http_port>/`; omit `:80` for port 80. mDNS is optional for controller access: use the fixed address when the controller cannot resolve `.local`. Browser “Not secure” is expected for LAN HTTP. Do not expose this HTTP target to the internet.

## Deployment and live acceptance sequence

The controller performs this live-test sequence when the operator has authorized it for this target. That authorization covers the listed repeat deployment, reboot, rollback and backup proof; no repeated approval is needed. Save each run ID before watching. If watching stops, inspect the same run; never dispatch another run because of a watcher failure. A failed step requires recorded diagnostics and a repository fix through a PR before resuming.

| Step | Operator | Agent action and pass condition |
| --- | --- | --- |
| 1 | Confirm native Mint is installed; an existing installation stays | Verify platform and LAN facts; no controller bootstrap |
| 2 | Authenticate and run the one printed root command | Local agent reaches done and reports initial CD URL/SHA/digest |
| 3 | No additional deployment if the local agent already did it | Controller verifies online `<node>-<app_name>` runner and app label; inspect initial successful CD, release manifest and running digest |
| 4 | Use the independent controller session | Run `Test-DeployedSite.ps1 -Address <node-ip> -Port <lan_http_port>`; require `RESULT: PASS`; record `.local` separately |
| 5 | No further action | Deploy the same verified SHA with `run_migrations=false`; acceptance passes again |
| 6 | No further action | Run maintenance with `reboot_check=true`; require success, then poll runner every 60 seconds for up to 15 minutes and run `acceptance_only=true`; uptime must be under 30 minutes |
| 7 | No further action | Select an older ancestor of main with successful push CI/publishing and identical migrations; deploy it, then deploy newest again; both pass |
| 8 | No further action | Run maintenance with `backup_now=true`; require a fresh dump, isolated restore with more than zero tables and exit 0 |

The main-PC check needs PowerShell 5.1 or 7, with no .NET SDK or browser:

```powershell
& .\Scripts\Test-DeployedSite.ps1 -Address <node-ip> -Port <lan_http_port>
```

It checks DNS/TCP, readiness, HTML/Blazor, anonymous API 401, registration, password login in a fresh session, the authenticated account page and rejected published admin credentials. A `finally` block deletes its test account and verifies the credentials no longer work.

Node acceptance first waits up to 180 seconds for LAN `/health/ready` to return 200. A runner can return before Docker services are ready after a reboot. Only that read-only readiness probe is retried; the full HTTP acceptance check runs once and any failure still fails the workflow.

From an authenticated controller in this repository:

```bash
gh workflow run cd-localsinglenode.yml --ref main \
  -f target_sha=<verified-main-sha> -f run_migrations=false
gh run list --workflow cd-localsinglenode.yml --event workflow_dispatch --limit 10
# Record the matching ID first, then watch that ID:
gh run watch <run-id> --interval 60 --exit-status

gh workflow run localsinglenode-maintenance.yml --ref main -f reboot_check=true
# Record/watch the maintenance ID. Reboot waits for whole-run success, then 30 seconds.
gh workflow run localsinglenode-maintenance.yml --ref main -f acceptance_only=true
gh workflow run localsinglenode-maintenance.yml --ref main -f backup_now=true
```

Use `run_migrations=true` for the first deployment or an approved schema update. CD requires main ancestry, successful main-push CI/publishing, a matching release manifest and the exact registry digest. A workflow-dispatch CI run cannot replace that provenance. For rollback rehearsal, compare migration files before selecting the older SHA:

```bash
git diff --exit-code <older-main-sha> <newest-main-sha> -- BlazorAutoApp/Infrastructure/Persistence/Migrations
```

Do not assume an arbitrary application rollback reverses database schema changes.

## Backups and recovery

`<app_name>-backup.timer` runs nightly around 03:00 with jitter. Its service takes the shared deployment lock, writes a custom-format PostgreSQL dump, copies runtime secrets, keeps this app's dumps for `backup_keep_days`, and writes `last-success`. Backup files are mode 0640; the directory is 0750, owned by deploy and the install user's group. Runtime secrets remain 0600. Maintenance fails if the last successful backup is more than 36 hours old.

Manual maintenance waits for its backup service before taking the maintenance lock, avoiding a nested lock. It verifies the newest dump in a uniquely labeled, network-isolated tmpfs PostgreSQL container, then removes only that container. It preserves volumes and every image referenced by a container or the active release. Foreign/dangling resources are reported; only proven old app images and eligible runner residue can be removed.

When `backup_now=true`, maintenance requires a successful backup completion timestamp at or after the request, refuses stale/future or timezone-free markers, and prints the fresh nonempty dump's name, size and completion time. A previous backup within the normal 36-hour maintenance window cannot substitute for a newly requested backup. No dump or secret contents are printed.

**One disk is not a backup.** Copy the entire backup directory to another machine or encrypted storage. It includes database data and a secrets copy; protect the destination. For example, from the other machine after verifying the node's SSH host key:

```bash
scp -r <install-user>@<node-ip>:/opt/<app_name>-backups <protected-destination>
```

For a bootstrap failure, record the numbered step and rerun the same operator command. For deployment failure, record the CD run and named failing check; do not overwrite secrets, re-register the runner, reclaim the lock or delete volumes. `bash Deployment/LocalSingleNode/Scripts/doctor.sh --json` is read-only.

The doctor's mDNS check asks Avahi to resolve the node name on the interface owning the recorded LAN IPv4. An unrestricted lookup on the node can return a Docker bridge address first even while LAN mDNS works. Controller-side name resolution is checked independently; use the recorded IPv4 if the controller cannot resolve `.local`. The runner check reads service state, user and working directory through systemd so the install user does not need access to deploy's private home.

Manual restore is an operator action. It creates a **new replacement database**, never overwriting the live database. For app `recipes`, the database prefix is `recipes_restore_`; hyphens in an app slug become underscores. The operator runs:

```bash
sudo bash Deployment/LocalSingleNode/Scripts/verify-backup.sh \
  --restore-into recipes_restore_recovery --confirm-restore recipes
```

This uses the newest protected dump. Add `--file /opt/recipes-backups/<recipes-dump>.dump` to select another owned dump. It refuses a live/existing target, missing confirmation or a name longer than PostgreSQL's 63-character limit. Validate recovered data before planning a separate, reviewed cutover; the command does not switch application connections. A failed partial replacement is left for operator inspection.

## Remove the app

Removal is a separate operator decision. First record a verified off-machine backup and the exact app identity/resources. Disable this app's backup timer and stop its app-specific runner; remove only that runner's registration if it is no longer needed. Do not stop another app's runner or shared Docker/Caddy service.

From the runtime directory, the operator stops this Compose project:

```bash
sudo docker compose --project-directory /opt/<app_name> -p <app_name> down
```

Never add `--volumes`. Named PostgreSQL, Redis and app-storage volumes stay. Identify any later volume removal by exact app labels/name, verify the off-machine backup, and have the operator run `docker volume rm <exact-owned-volume>` by hand. Never prune volumes.

Remove only this app's Caddy site, validate the shared Caddy configuration before reload, and retain its protected backups/secrets until the operator explicitly chooses their removal. Uninstalling shared host services or deleting other apps' markers is outside app removal.
