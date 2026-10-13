# Release Contract

`Deployment/Common/release.yml` names the image and migration artifact built by CI. A deployable release is tied to one full source SHA and one successful publishing attempt for that SHA on `main`. CI can run from a `push` or `workflow_dispatch` on `main`; a pull request check does not publish a release. CI publishes the GHCR image and migration bundle only when the run is for `refs/heads/main`. CD requires a successful `publish-main` job on the same run attempt selected by the target workflow. LocalSingleNode's initial AgentSetup checkpoint still requires a main push; this is a one-time bootstrap rule, separate from later release selection.

Schema v2 `release-manifest.json` binds the repository and source SHA to the CI run ID and attempt, frontend and acceptance profile pair, registry image digest, ordered migration IDs, migration bundle SHA-256, and .NET SDK. LocalCluster and LocalSingleNode CD validate that manifest against the selected source, downloaded artifact, registry digest, and image labels before migration. They verify the deployed image identity after acceptance. Legacy schema v1 is limited to verified `BlazorAuto`/`BlazorAutoV1` releases; it cannot describe React.

Cloud CD currently selects a successful CI publishing attempt and checks that the SHA-tagged image exists. It does not validate `release-manifest.json`, pin the registry digest, or verify the migration bundle hash before migration. Follow [the Cloud deployment guide](../Cloud/HowToDeployCloud.md) for its current checks. The stronger LocalCluster and LocalSingleNode checks described above do not apply to Cloud yet.

GitHub Actions `Workflow permissions: Read and write permissions` must allow package publishing. No GitHub token goes into the vault. Manual deployment credentials, when needed for a private image, need only `read:packages`.

If the migration bundle artifact is missing or expired, stop. Run CI again for the selected source SHA and deploy only after that run publishes a fresh artifact successfully.

## Select a published source

A documentation-only commit using `[skip ci]` creates no release. LocalCluster and LocalSingleNode can dispatch from current `main` with `target_sha` set to a full, previously published SHA on `main`; leave it empty only when the dispatched commit has its own successful publishing run. Cloud has no `target_sha` input and deploys the dispatched `main` commit. If that commit has no release, manually dispatch CI on `main` and require successful publication before Cloud CD. Do not substitute a PR artifact or an ancestor's artifact for the selected source.

Sources: [CI workflow](../../.github/workflows/ci.yml), [successful-run selector](Scripts/Component/lib/find-successful-ci-run.py), [manifest validator](Scripts/validate_release_manifest.py), [LocalSingleNode CD](../../.github/workflows/cd-localsinglenode.yml), [LocalCluster CD](../../.github/workflows/cd-localcluster.yml), and [Cloud CD](../../.github/workflows/cd-cloud.yml).
