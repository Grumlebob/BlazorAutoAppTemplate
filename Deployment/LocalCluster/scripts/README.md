# LocalCluster Scripts

Top-level `*.sh` files are the commands used by the deployment guide.

`support/` contains shell helpers called by commands or CI.

`lib/` contains Python helpers used by those commands, CI, and the deployment audit.

`node-db/` contains maintenance scripts copied onto the database node by Ansible.

`summary.sh` prints the concrete deployment target without contacting remote nodes.

`doctor.sh` is the main read-only readiness check for the current phase.

`acceptance-check.sh` verifies a completed deployment end to end.

`report-nodes.sh` prints read-only node facts for troubleshooting.

`check-port-collisions.sh` is called by deploy preflight to protect side-by-side apps from reusing another app's published ports.

`list-deployed-apps.sh` reads LocalCluster app ownership markers from the nodes.

`validate-side-by-side.sh` checks current settings against known deployed app markers.

`verify-backup.sh` verifies backup gzip integrity and basic SQL content without restoring anything.

`check-github-runner.sh` optionally verifies the expected self-hosted GitHub runner through the GitHub API.

`check-cloudflare-tunnel.sh` optionally verifies Cloudflare tunnel, DNS, and ingress settings through the Cloudflare API.

`validate-rendered-templates.sh` renders representative deployment templates and runs optional local validators when available.

`support/with-deploy-lock.sh` serializes deploys that run on the same `node-main` runner host.

`support/with-node-main-deploy-lock.sh` lets manual deploys from a control machine use that same `node-main` lock.
