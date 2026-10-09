# LocalCluster Scripts

Top-level `*.sh` files are the commands used by the deployment guide and workflows.

`Component/` contains implementation helpers called by top-level commands or CI.

`Component/lib/` contains Python helpers used by top-level commands, CI, and the deployment audit.

`Component/node-db/` contains backup and restore scripts copied onto the database node by Ansible.

`deploy.sh <git-sha> [--digest sha256:<digest>] [--migrate <bundle>]` deploys a selected app image from a control machine and optionally runs the matching EF migration bundle once before starting the app servers. `--digest` pins the exact image. It skips the CI and release-manifest checks that CD performs, so prefer the CD workflow.

`summary.sh` prints the concrete deployment target without contacting remote nodes.

`validate-machines.sh` checks `machines.yml` and deployment settings without writing generated inventory files.

`doctor.sh` is the main read-only readiness check for the current phase.

`acceptance-check.sh` verifies a completed deployment end to end.

`report-nodes.sh` prints read-only node facts for troubleshooting.

`check-port-collisions.sh` is called by deploy preflight to protect side-by-side apps from reusing another app's published ports.

`prepare-existing-localcluster-app.sh` installs this app's deploy key on nodes that were already prepared by another LocalCluster app.

`list-deployed-apps.sh` reads LocalCluster app ownership markers from the nodes.

`validate-side-by-side.sh` checks current settings against known deployed app markers.

`verify-backup.sh` verifies backup gzip integrity and basic SQL content without restoring anything.

`check-github-runner.sh` optionally verifies the expected self-hosted GitHub runner through the GitHub API.

`check-cloudflare-tunnel.sh` optionally verifies Cloudflare tunnel, DNS, and ingress settings through the Cloudflare API.

`validate-rendered-templates.sh` renders representative deployment templates and runs optional local validators when available.

`install-ansible.sh` wraps the shared installer in `Deployment/Common/Scripts/install-ansible.sh`. `--provision` (the default) installs missing OS packages with bounded, retried apt calls and publishes a validated Ansible generation under `~/.local/share/books-ansible/current`. `--check` validates that generation without apt or sudo; CI and CD use only `--check`.

`with-deploy-lock.sh` is the workflow-facing wrapper for serialized node-main deploys.

`audit-deployment.sh` runs the static deployment consistency audit used by CI.

`read-deploy-setting.sh` and `validate-deploy-settings.sh` are thin wrappers around internal Python helpers.

`find-successful-ci-run.sh` wraps the shared GitHub Actions helper in `Deployment/Common`.

`ensure-actions-runner-prereqs.sh` verifies (`--check`, used by CI) or installs (`--provision`, the default) self-hosted CI prerequisites on `node-main`. If CI reports a missing tool, run it with `--provision` on `node-main` as an administrator.

`prune-docker-residue.sh` removes dangling images labelled by this repository's CI and old unused tags of this app's image, then frees more with low-disk fallbacks when still below `--min-free-mb`. Host-wide prunes (stopped containers, dangling images, build cache, networks) run only with `--include-unlabelled-host-residue`, because they affect every app on the Docker host. Docker volumes are never pruned. Exit codes: `0` done, `1` failure, `2` still below the reserve, `75` deferred (protected candidates skipped, with `--defer-if-skipped`).

`release-deploy-lock.sh` inspects (`--inspect`) or manually releases (`--release --token <token>`) the shared `node-main` deployment lock after verifying the owner is gone. The lock is never released automatically.

`validate-inventory-dns.sh` checks that each inventory host resolves to its inventory IP. It runs from `preflight.sh` and is skipped unless `inventory_dns_suffix` is set in `group_vars/all.yml`.

`ci-docker-smoke.sh` starts the freshly built image with disposable, labelled PostgreSQL and Redis containers on tmpfs, checks `/health/ready`, the SSR home page and the anonymous API 401, then runs the browser smoke tests. It removes only the resources it created. CI runs it for pull requests and before every `main` publish.

`check-node-main-capacity.sh` checks the `/opt` reserve on `node-main` (defaults in `localcluster-capacity-thresholds.sh`: 20 GiB and 5 % free inodes; 2 GiB on app nodes, 4 GiB on the database node). Exit codes: `0` ok, `1` cannot measure, `2` below the reserve.

`run-localcluster-maintenance.sh [--capacity-only]` runs the maintenance stages under the deployment lock: runner residue, finished-CI residue, node-main Docker, app/db node Docker, a volume inventory (report only) and the capacity check. Exit codes: `0` done, `1` failure, `2` below the reserve, `75` deferred. The `LocalCluster Docker Maintenance` workflow calls it.

`prune-actions-runner-residue.sh` removes old Actions runner versions and stale `_work/_update`, `_work/_temp` and `_diag` entries, keeping the active version and every workspace.

`prune-ci-residue.py [--apply]` removes this repository's labelled CI containers and networks whose GitHub run attempt finished more than 24 hours ago. Read-only without `--apply`; with it, it must run under the deployment lock on `node-main`. It never removes volumes.

`prune-cluster-docker-residue.sh` copies `prune-docker-residue.sh` to the app and database nodes and runs the same scoped cleanup there. It requires every node's SSH host key to be in `known_hosts` already.

`verify-release-identity.sh <app-image> <sha256-digest>` checks that the web container on every app node runs the released image digest. CD runs it after the acceptance check.

`Tests/` holds fixture tests for these scripts (deploy lock, Ansible check-only setup, Docker smoke lifecycle, release identity, maintenance, Docker and runner cleanup, CI residue); CI runs all of them.

`Deployment/Common/Scripts/prune-actions-artifacts.sh` prunes old GitHub Actions artifacts by exact artifact name; `--protect-run-id <id>` keeps the artifacts of deployed CI runs. The maintenance workflow runs it.

`Component/with-deploy-lock.sh` serializes deploys that run on the same `node-main` runner host.

`Component/with-node-main-deploy-lock.sh` lets manual deploys from a control machine use that same `node-main` lock.
