# Cloud Scripts

Top-level scripts provide Cloud setup and operations commands. `Component/` holds Cloud-specific implementation helpers.

`Component/lib/cloud-env.sh` adds `~/.local/bin` to `PATH` and loads missing Cloud tokens from repo-root `.env.cloud`.

Start with [Setup](../Setup.md) or [Operations](../Operations.md); use shared helpers from [Deployment Common](../../Common/README.md). Cloud helpers must not import code from LocalCluster.
