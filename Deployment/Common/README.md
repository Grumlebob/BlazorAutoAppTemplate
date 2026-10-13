# Deployment Common

Shared deployment behavior lives here only when it works independently of a target. Target-specific inventory, firewall, Compose and bootstrap stay in each target folder.

- `release.yml` and the [release contract](ReleaseContract.md) own artifact names, provenance and target release checks.
- [SSH host trust](SshTrust.md) owns manual host-fingerprint verification.
- The [public tunnel helper](Scripts/setup-public-tunnel.sh) is integrated by [LocalSingleNode public setup](../LocalSingleNode/PublicSetup.md).
- `Scripts/` holds shared release, toolchain, settings, lock, runner and cleanup helpers. Target guides own their invocation steps.
- Runner residue cleanup requires `--runner-root`, `--app-name` or `--all-localcluster-runners`; it never infers target settings.
- `ansible/roles/` holds reusable host building blocks; target-specific roles stay with their target.
- `caddy/Caddyfile` imports each app-owned site. `observability/` holds shared dashboards, alerting configuration, helpers and runbooks.

Shared Ansible roles use optional guards instead of assuming one target's topology.
