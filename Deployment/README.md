# Choose a deployment target

All targets use shared image and migration settings. CI can publish from a `main` push or manual dispatch; the [release contract](Common/ReleaseContract.md) describes what each target verifies. Choose the topology, then follow its guide.

| Target | Machines | Needs | Downtime per deploy | Backups | Pick it when |
| --- | --- | --- | --- | --- | --- |
| `localsinglenode` | One PC | Native Linux Mint and a LAN | Short interruption during migration/start | Nightly local PostgreSQL dump and protected secrets copy | Demos, hobby apps and a first deployment |
| `localcluster` | Four PCs | Linux Mint, prepared cluster and Cloudflare | Rolling app update without migrations; see the guide for migrations | Follow the cluster guide | Several app instances at home |
| `cloud` | Four Hetzner servers | Cloud/Cloudflare accounts and infrastructure cost | Follow the cloud guide | Follow the cloud guide | Public hosting without maintaining physical nodes |

- [LocalSingleNode guide](LocalSingleNode/HowToDeployLocalSingleNode.md): native setup and operations. To add an app on a prepared node, use [application instances](LocalSingleNode/ApplicationInstances.md).
- [LocalCluster guide](LocalCluster/HowToDeployLocalCluster.md): cluster preparation, inventory, Cloudflare and deployment.
- [Cloud guide](Cloud/HowToDeployCloud.md): OpenTofu infrastructure, Ansible and Cloudflare.
- [Fork guide](../docs/HowToForkThisRepo.md): application identity and target routing.
- [Release contract](Common/ReleaseContract.md): source, CI attempt, GHCR payload, image and target checks.

## Enable targets

Set the GitHub **repository variable** `DEPLOY_TARGETS` to a comma-separated list. It is not a secret.

```bash
gh variable set DEPLOY_TARGETS --body localsinglenode
# Or enable more than one target deliberately:
gh variable set DEPLOY_TARGETS --body localcluster,localsinglenode
```

Every deployment and maintenance workflow checks its target in the first step and stops when it is disabled. Enabling a target grants no permission to deploy it: obtain the operator's authorization before dispatch. CI remains common to all targets.

Single-node setup sets `LOCALSINGLENODE_HOST` and `LOCALSINGLENODE_RUNNER_LABEL`. A one-PC fork without any registered CI runner also registers its runner with a CI label and sets `CI_RUNNER_LABEL`/`CI_RUNNER_HOST`. Reuse an existing runner only when its host and labels meet the selected workflows' requirements.

## Keep the unused folders

For a multi-target fork, keep all target folders. Ignore an unused target's inventory, provisioning, secrets and guide, and leave it out of `DEPLOY_TARGETS`. CI validates every target, and shared audit, render and Docker smoke entry points currently live under `Deployment/LocalCluster`.

A fork intended to support only LocalSingleNode can remove Cloud and LocalCluster after replacing their CI, audit, test and documentation dependencies. Follow [Single-node-only clone](LocalSingleNode/SingleNodeOnlyClone.md); deleting the target folders alone breaks the build.

`Deployment/Common` is always required. It holds release settings, shared host roles, tool pins, observability assets and the lock/prerequisite/cleanup helpers. A new target must use Common instead of reaching into another target's implementation.

## Shared hosts

Several apps can share a machine. Each owns its Compose project, runtime root, Caddy site and selected ports/subnet. Docker, Caddy and `/tmp/localcluster-deploy.lockdir` are shared. Use each target's ownership checks and scoped scripts. Never run an unscoped prune, remove another app's resources, or pass `--volumes` to Compose down on a deployment node.
