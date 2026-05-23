# LocalCluster Scripts

Top-level `*.sh` files are the commands used by the deployment guide.

`support/` contains shell helpers called by commands or CI.

`lib/` contains Python helpers used by those commands, CI, and the deployment audit.

`node-db/` contains maintenance scripts copied onto the database node by Ansible.

`check-port-collisions.sh` is called by deploy preflight to protect side-by-side apps from reusing another app's published ports.

`support/with-deploy-lock.sh` serializes deploys that run on the same `node-main` runner host.

`support/with-node-main-deploy-lock.sh` lets manual deploys from a control machine use that same `node-main` lock.
