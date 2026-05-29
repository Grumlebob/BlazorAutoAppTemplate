# Cloud Scripts

Cloud helper scripts will live here.

Planned scripts:

Implemented local scripts:

- `check-currentpc-tools.sh` verifies local tool prerequisites.
- `read-cloud-setting.sh` reads one committed Cloud setting.
- `validate-cloud-settings.sh` validates committed Cloud settings.
- `summary.sh` prints shared release and Cloud deployment settings.

Planned scripts:

- `render-inventory-from-tofu.sh`
- `preflight.sh`
- `provision.sh`
- `deploy.sh`
- `acceptance-check.sh`
- `backup-db.sh`
- `restore-db.sh`

Scripts may use target-independent helpers from `Deployment/Common`. They must not import from `Deployment/LocalCluster`.
