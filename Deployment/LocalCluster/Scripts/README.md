# LocalCluster Scripts

Top-level `*.sh` files are the commands used by the deployment guide and workflows.

`Component/` contains implementation helpers called by top-level commands or CI.

`Component/lib/` contains Python helpers used by top-level commands, CI, and the deployment audit.

`Component/node-db/` contains backup and restore scripts copied onto the database node by Ansible.

`deploy.sh <git-sha> --migrate <bundle>` deploys a selected app image and optionally runs the matching EF migration bundle once before starting the app servers.

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

`install-ansible.sh` wraps the shared installer in `Deployment/Common/Scripts/install-ansible.sh`.

`with-deploy-lock.sh` is the workflow-facing wrapper for serialized node-main deploys.

`audit-deployment.sh` runs the static deployment consistency audit used by CI.

`read-deploy-setting.sh` and `validate-deploy-settings.sh` are thin wrappers around internal Python helpers.

`find-successful-ci-run.sh` wraps the shared GitHub Actions helper in `Deployment/Common`.

`Component/with-deploy-lock.sh` serializes deploys that run on the same `node-main` runner host.

`Component/with-node-main-deploy-lock.sh` lets manual deploys from a control machine use that same `node-main` lock.
