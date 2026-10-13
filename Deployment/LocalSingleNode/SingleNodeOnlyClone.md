# Make a single-node-only clone

Use this after forking when the product will support one native Linux node. The original repository remains a multi-target template; this guide describes how to simplify a clone without leaving CI or documentation tied to removed deployment targets.

## Safe removal sequence

1. Start from a clean branch based on the fork's latest `main`. Keep the app, its LocalSingleNode deployment, and shared `Deployment/Common` components that LocalSingleNode workflows still use.
2. Inventory every reference to `Deployment/LocalCluster`, `Deployment/Cloud`, `localcluster`, and `cloud` in workflows, scripts, tests, audits, settings, and docs. Classify each match as required by LocalSingleNode, shared by a remaining target, or a removal candidate.
3. Update CI and audit entry points before deleting target folders. Keep checks that still protect LocalSingleNode; replace target-specific checks with single-node checks instead of deleting the audit wholesale. Update tests and local-gate documentation in the same change.
4. Remove the unused Cloud and LocalCluster deployment folders and target-specific maintenance only after all live references are handled. Preserve shared roles and scripts used by LocalSingleNode, including release provenance, Caddy, runner prerequisites, lock handling, backup and acceptance support.
5. Update the fork guide, deployment chooser, README and product docs so they describe one node. Keep machine names, addresses, domains, credentials and runtime paths in ignored/private settings.
6. Search again for stale paths and target names. Resolve unintended matches; retain intentional references only when a remaining source or guide depends on them.
7. Run the repository's local gate from `docs/Test.md`, open a PR, require `build-test-push` on its exact head, then merge only after green CI.
