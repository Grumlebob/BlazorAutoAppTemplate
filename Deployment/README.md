# Choose a deployment target

All targets use the same application image, migration bundle and verified main-push release manifest. Choose the topology, then follow its guide.

| Target | Machines | Needs | Downtime per deploy | Backups | Pick it when |
| --- | --- | --- | --- | --- | --- |
| `localsinglenode` | One PC | Native Linux Mint and a LAN | Short interruption during migration/start | Nightly local PostgreSQL dump and protected secrets copy | Demos, hobby apps and a first deployment |
| `localcluster` | Four PCs | Linux Mint, prepared cluster and Cloudflare | Rolling app update without migrations; see the guide for migrations | Follow the cluster guide | Several app instances at home |
| `cloud` | Four Hetzner servers | Cloud/Cloudflare accounts and infrastructure cost | Follow the cloud guide | Follow the cloud guide | Public production with managed infrastructure |

- [LocalSingleNode guide](LocalSingleNode/HowToDeployLocalSingleNode.md): agent setup on the selected native PC, with one operator sudo command.
- [LocalCluster guide](LocalCluster/HowToDeployLocalCluster.md): cluster preparation, inventory, Cloudflare and deployment.
- [Cloud guide](Cloud/HowToDeployCloud.md): OpenTofu infrastructure, Ansible and Cloudflare.
- [Fork guide](../docs/HowToForkThisRepo.md): application identity and shared release settings.

## Enable targets

Set the GitHub **repository variable** `DEPLOY_TARGETS` to a comma-separated list. It is not a secret.

```bash
gh variable set DEPLOY_TARGETS --body localsinglenode
# Or enable more than one target deliberately:
gh variable set DEPLOY_TARGETS --body localcluster,localsinglenode
```

Every deployment and maintenance workflow checks its target in the first step and stops when it is disabled. Enabling a target grants no permission to deploy it: obtain the operator's authorization before dispatch. CI remains common to all targets.

Single-node setup sets `LOCALSINGLENODE_HOST` and `LOCALSINGLENODE_RUNNER_LABEL`. A one-PC fork without any registered CI runner also registers its runner with a CI label and sets `CI_RUNNER_LABEL`/`CI_RUNNER_HOST`. The template keeps its existing CI runner; a separate demo node handles single-node CD only.

## Keep the unused folders

Keep all target folders in a fork. You can ignore an unused target's inventory, provisioning, secrets and operating guide, and leave it out of `DEPLOY_TARGETS`. Do not delete its folder: CI still validates all targets, and shared audit/render/Docker smoke entry points currently live under `Deployment/LocalCluster`.

`Deployment/Common` is always required. It holds release settings, shared host roles, tool pins, observability assets and the lock/prerequisite/cleanup helpers. A new target must use Common instead of reaching into another target's implementation.

## Shared hosts

Several apps can share a machine. Each owns its Compose project, runtime root, Caddy site and selected ports/subnet. Docker, Caddy and `/tmp/localcluster-deploy.lockdir` are shared. Use each target's ownership checks and scoped scripts. Never run an unscoped prune, remove another app's resources, or pass `--volumes` to Compose down on a deployment node.
