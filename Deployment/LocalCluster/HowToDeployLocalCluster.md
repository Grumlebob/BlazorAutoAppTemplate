# How To Deploy LocalCluster

This file is the LocalCluster entry point. Select one route:

- New four-node target: follow [LocalCluster setup](Setup.md) in order.
- Settings and defaults: use [LocalCluster settings](Settings.md).
- Existing prepared nodes: use [Fork Onto An Existing LocalCluster](ForkExistingCluster.md).
- Releases, diagnosis, backups, recovery, and maintenance: use [LocalCluster operations](Operations.md).

Before any first SSH connection, follow [SSH host trust](../Common/SshTrust.md). Use [the shared release contract](../Common/ReleaseContract.md) for CI provenance and artifacts.

### Shared release wrapper

When a LocalCluster release is driven by the shared `DeployLocalCluster.ps1` wrapper from an ImprovedDb checkout, keep this repository as PowerShell's working directory and invoke the wrapper script from that checkout. The target working directory selects this repository and its release settings; the wrapper checkout supplies its implementation and shared helper. The wrapper passes this target's `app_name` to the payload pin/fetch helper, which stores exact CI payloads under `/opt/<app_name>/release-payloads` on the target host. Provide the full target SHA and preserve the migration, rank-refresh, and sync choices from the release plan.

### Deployment lock

Deployment scripts link here for lock recovery. Read [the full recovery procedure](Operations.md#deployment-lock). Never delete the lock automatically or by age. Inspect the owner and release only after proving it is gone.
