# Deployment Common

Shared deployment behavior lives here only when it works independently of a target. Target-specific inventory, firewall, Compose and bootstrap stay in each target folder.

- `release.yml` and the [release contract](ReleaseContract.md) own artifact names, provenance and target release checks.
- [SSH host trust](SshTrust.md) owns manual host-fingerprint verification.
- The [public tunnel helper](Scripts/setup-public-tunnel.sh) is integrated by [LocalSingleNode public setup](../LocalSingleNode/PublicSetup.md).
- `Scripts/` holds shared release, toolchain, settings, lock, runner and cleanup helpers. Target guides own their invocation steps.
- `pin_release_payload.py` validates exact GHCR release bytes before storing a repository-scoped local pin. LocalCluster and LocalSingleNode recover by explicit pin key without Actions or GHCR access; their existing locked maintenance owners protect the current and previous release, retain the newest three other pins per profile, and cap unprotected bytes at 1 GiB.
- `Scripts/registry-inventory.py` measures payload packages without downloading layers or changing registry state. It verifies the configured package's repository linkage and visibility, manifest/config hashes and lengths, and the exact CI attempt behind each payload. Pass `--repository owner/repository --username user --package ghcr.io/owner/app-release-payload=private` with an existing `GITHUB_TOKEN` or `GH_TOKEN` in the environment. Unknown ownership, aliases, or incomplete descriptor graphs stop the inventory; a storage report does not classify releases as disposable or authorize deletion.
- Runner residue cleanup requires `--runner-root`, `--app-name` or `--all-localcluster-runners`; it never infers target settings.
- `ansible/roles/` holds reusable host building blocks; target-specific roles stay with their target.
- `caddy/Caddyfile` imports each app-owned site. `observability/` holds shared dashboards, alerting configuration, helpers and runbooks.

Shared Ansible roles use optional guards instead of assuming one target's topology.
