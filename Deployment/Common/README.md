# Deployment Common

Shared deployment files live here only when they are independent of a specific target.

Current shared ownership:

- `release.yml` defines the build artifact names used by CI, LocalCluster CD, and future Cloud CD.
- `Scripts/read-release-setting.sh` reads one value from `release.yml`.
- `Scripts/validate-common-release.sh` validates `release.yml` and checks that the current LocalCluster compatibility values still match.

Keep this folder small. Do not move LocalCluster inventory, Caddy, firewall, compose, or bootstrap logic here until LocalCluster and Cloud have both proven the shared boundary.
