# Deployment Common

Shared deployment files live here only when they are independent of a specific target.

Current shared ownership:

- `release.yml` defines the build artifact names used by CI, LocalCluster CD, and Cloud CD.
- `Scripts/read-release-setting.sh` reads one value from `release.yml`.
- `Scripts/validate-common-release.sh` validates `release.yml`.
- `migration_artifact_name` is derived by the reader as `<migration_bundle_name>-<migration_runtime>`.
- `Scripts/install-ansible.sh` installs the pinned Ansible toolchain used by deployment runners/control machines.
- `Scripts/Component/lib/find-successful-ci-run.py` selects the newest trusted CI run for a commit (main branch, push or dispatch, this repository, current attempt) and fails unless it succeeded. `--json` prints the run id and attempt for CD.
- `Scripts/validate_release_manifest.py` validates the `release-manifest.json` that CI publishes next to the migration bundle: repository, commit, CI run id and attempt, the image's registry digest, ordered migration ids, bundle SHA-256 and .NET SDK. CD deploys the digest it prints.
- `Scripts/Component/lib/prune-actions-artifacts.py` keeps the newest release artifacts and never deletes those of protected (deployed) CI runs.
- `ci-python-constraints.txt` pins the Python packages CI installs into its per-run virtual environment.
- `Scripts/Tests/` holds unit tests for the provenance, manifest and retention helpers; CI runs them.
- `Scripts/Component/lib/simple_yaml.py` is the shared parser for the simple top-level YAML files used by deployment settings.
- `observability/grafana` contains target-neutral Grafana datasource and dashboard provisioning.
- `observability/alertmanager` contains target-neutral Alertmanager routing defaults.
- `observability/prometheus/rules` contains target-neutral Prometheus alert rules.
- `observability/runbooks` contains short operator runbooks referenced by alerts.
- `observability/scripts` contains shared validation/cardinality/resource helper scripts.
- `observability/scripts/test-alertmanager-route.sh` sends a short-lived synthetic alert to prove Alertmanager accepts routed alerts.

Keep this folder small. Do not move LocalCluster inventory, Caddy, firewall, compose, or bootstrap logic here until LocalCluster and Cloud have both proven the shared boundary.
