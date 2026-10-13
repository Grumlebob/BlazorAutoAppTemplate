# Fork This Repository

Use this page to choose the fork's identity, decide what to do with the sample feature, and enter the deployment guide for each target. For target capabilities and `DEPLOY_TARGETS`, start with the [deployment chooser](../Deployment/README.md).

## Choose the target route

- **One native Linux PC:** follow [LocalSingleNode setup](../Deployment/LocalSingleNode/AgentSetup.md) and [deployment](../Deployment/LocalSingleNode/HowToDeployLocalSingleNode.md).
- **Four prepared LocalCluster nodes:** follow [Fork onto an existing LocalCluster](../Deployment/LocalCluster/ForkExistingCluster.md).
- **New LocalCluster nodes:** follow [LocalCluster setup](../Deployment/LocalCluster/HowToDeployLocalCluster.md).
- **Cloud:** follow [Cloud setup](../Deployment/Cloud/HowToDeployCloud.md).

For a multi-target fork, keep all target folders and customize only the targets you enable. A clone intended to support only LocalSingleNode can remove the other targets by following [Single-node-only clone](../Deployment/LocalSingleNode/SingleNodeOnlyClone.md); deleting their folders alone leaves CI dependencies behind.

CI uses a self-hosted Linux x64 runner. Register an online runner and set the repository variables `CI_RUNNER_LABEL` (a label on that runner) and `CI_RUNNER_HOST` before the first PR; otherwise required checks queue or fail. Workflows fall back to the template's own runner labels (`localcluster-books`, `localsinglenode-books`) when a label variable is unset, so a fork without `CI_RUNNER_LABEL` waits in the queue rather than failing. Set `LOCALSINGLENODE_RUNNER_LABEL` or `LOCALCLUSTER_RUNNER_LABEL` the same way for the targets you enable. LocalSingleNode setup can register its runner with [AgentSetup `--ci-runner`](../Deployment/LocalSingleNode/AgentSetup.md). For prepared LocalCluster nodes, follow the existing-cluster route, which installs its runner before the PR. Cloud CD also requires a runner on a host named `node-main`; the Cloud guide assumes that runner already exists.

## Choose shared identity

Choose these values once and use them consistently:

| Value | Rule |
| --- | --- |
| `APP_SLUG` | Lowercase deployment name; start with a letter and use only letters, numbers, and hyphens. |
| `APP_IDENTITY_NAME` | Usually the same as `APP_SLUG`; choose it before users exist because it scopes Data Protection and cache channels. |
| `GITHUB_OWNER` and `GITHUB_REPO` | The owner and repository name for the fork. |
| `APP_IMAGE` | Lowercase GHCR image owned by the fork. |
| `PUBLIC_HOSTNAME` | The hostname configured for the selected target. |
| `MIGRATION_BUNDLE_NAME` | Unique name for the fork's migration bundle. |

Update the first README paragraph and the local settings in `.env.example`, `BlazorAutoApp/appsettings.json`, and `BlazorAutoApp/appsettings.Docker.json`. Keep internal project and namespace names unless you are doing a planned rebrand. See [running locally](HowToRunLocally.md) for creating the ignored `.env` file.

## Choose the frontend and sample feature

The template selects Blazor Auto in `frontend-profile.txt`. For a public-only React product, set `React` and run the profile resolver:

```bash
printf 'React\n' > frontend-profile.txt
python3 Scripts/Frontend/resolve_frontend_profile.py
```

The sample Books feature can stay while the fork is deployed, then be replaced in small slices using [How to add a feature](HowToAddANewFeature.md). Remove sample data and update the feature's server, client, tests, documentation, and observability together when replacing it.

## Set shared release settings

Edit `Deployment/Common/release.yml` with the fork's `app_image`, `migration_bundle_name`, and the supported `linux-x64` migration runtime. Validate it with:

```bash
bash ./Deployment/Common/Scripts/validate-common-release.sh
```

Read the [release contract](../Deployment/Common/ReleaseContract.md) before choosing a commit to deploy. A pull request check validates the fork but does not publish a deployable release.

## Make and verify the fork changes

Make customization changes on a branch. Run the [local gate](Test.md#local-gate), open a pull request, and merge only after `build-test-push` succeeds on that exact head. Merging alone does not deploy; enter the selected target's guide after main CI publishes the release.
