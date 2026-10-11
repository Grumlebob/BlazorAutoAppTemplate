# Controller-driven native readiness

Use the existing native runner for read-only Docker checks when the original install user's SSH login lacks Docker access. This does not grant that login new privileges. Complete [controller SSH pairing](ControllerSsh.md) first and use SSH for checks its existing privileges permit.

The `LocalSingleNode read-only readiness` workflow runs only from trusted main on the existing LocalSingleNode runner. It verifies the native hostname against protected candidate input and recorded machine facts, requires the existing non-root `deploy` account, runs configured doctor and Docker inspection, and runs the ordinary collision check without bootstrap. It reports only sanitized readiness categories. It performs no sudo, bootstrap, backup creation, restore, deployment, restart, cleanup, or runner registration.

## Protected candidate input

Prepare a private JSON file outside tracked files with exactly these keys:

- `expected_host`: the verified native hostname, matching the authenticated host repository's `LOCALSINGLENODE_HOST` variable.
- `source_repo_url`: the candidate checkout's canonical HTTPS GitHub repository URL, without `.git`.
- `settings_yaml`: the complete contents of that checkout's `Deployment/LocalSingleNode/inventory/group_vars/all.yml`.

Publish this file as the host repository's `LOCALSINGLENODE_READINESS_CANDIDATE` Actions secret through authenticated GitHub CLI input. Use a secret even though these settings are not credentials: this prevents GitHub's automatic step environment display from exposing private installation values. Never paste the JSON into chat, tracked documentation, PR text, workflow inputs, or a command logged publicly. Do not copy application secrets or runner credentials.

After the workflow code has merged and main CI is green, dispatch `localsinglenode-readiness.yml` from main. Record the run ID immediately and inspect that run to completion. Identity verification failure stops the job before Docker checks. Missing access, invalid input, collision, unhealthy existing services, stale/unknown backup, or inadequate capacity fails readiness. Do not treat a failed or unavailable check as a pass.

The candidate settings pass through the production parser and validation in an owner-only temporary file under the runner's existing temporary directory. The file is removed on success and failure. The collision CLI also accepts `--settings-file <existing-file>` for an explicit inventory; its default still uses the current checkout's inventory.

## Capacity and subsequent gates

Planning floors require four logical CPUs, five-minute load below 75% of that CPU count, 7 GiB usable total memory, 4 GiB available memory and 40 GiB free disk on the app, workspace and actual Docker storage filesystems. These are conservative policy thresholds, not reported machine capacities. They allow planning for one sequential build alongside a small additional application. Real CI/image builds, existing application health and the deployment lock remain required before deployment. If the floor fails, inspect resource use privately and prepare a measured, bounded workload plan; do not silently lower the threshold.

Recheck close to an authorized setup or deployment because workload, capacity and backup freshness can change. This workflow does not establish runner registration scope: verify that separately through the authenticated GitHub runner API. Adding or moving a runner needs the owner's applicable authorization.

Remove the temporary readiness secret and obsolete private JSON when coordination and setup are complete. Retain required sanitized evidence in the plan or PR description. Preserve controller keys, pinned trust and reusable tooling.
