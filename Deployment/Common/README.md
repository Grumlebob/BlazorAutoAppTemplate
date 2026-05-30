# Deployment Common

Shared deployment files live here only when they are independent of a specific target.

Current shared ownership:

- `release.yml` defines the build artifact names used by CI, LocalCluster CD, and Cloud CD.
- `Scripts/read-release-setting.sh` reads one value from `release.yml`.
- `Scripts/validate-common-release.sh` validates `release.yml`.
- `migration_artifact_name` is derived by the reader as `<migration_bundle_name>-<migration_runtime>`.
- `Scripts/install-ansible.sh` installs the pinned Ansible toolchain used by deployment runners/control machines.
- `Scripts/Component/lib/find-successful-ci-run.py` finds the successful CI run for the selected commit before CD downloads artifacts.
- `Scripts/Component/lib/simple_yaml.py` is the shared parser for the simple top-level YAML files used by deployment settings.
- `observability/grafana` contains target-neutral Grafana datasource and dashboard provisioning.
- `observability/prometheus/rules` contains target-neutral Prometheus alert rules.
- `observability/runbooks` contains short operator runbooks referenced by alerts.
- `observability/scripts` contains shared validation/cardinality/resource helper scripts.

Keep this folder small. Do not move LocalCluster inventory, Caddy, firewall, compose, or bootstrap logic here until LocalCluster and Cloud have both proven the shared boundary.
