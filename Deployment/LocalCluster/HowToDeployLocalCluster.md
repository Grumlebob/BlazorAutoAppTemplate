# How To Deploy LocalCluster

This file is the LocalCluster entry point. Select one route:

- New four-node target: follow [LocalCluster setup](Setup.md) in order.
- Settings and defaults: use [LocalCluster settings](Settings.md).
- Existing prepared nodes: use [Fork Onto An Existing LocalCluster](ForkExistingCluster.md).
- Releases, diagnosis, backups, recovery, and maintenance: use [LocalCluster operations](Operations.md).

Before any first SSH connection, follow [SSH host trust](../Common/SshTrust.md). Use [the shared release contract](../Common/ReleaseContract.md) for CI provenance and artifacts.

### Deployment lock

Deployment scripts link here for lock recovery. Read [the full recovery procedure](Operations.md#deployment-lock). Never delete the lock automatically or by age. Inspect the owner and release only after proving it is gone.
