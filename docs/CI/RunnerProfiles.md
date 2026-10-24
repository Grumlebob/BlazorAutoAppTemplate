# CI Runner Profiles

The template keeps its configured native runner as the default. Profile routing is optional and off until the repository variable `CI_RUNNER_ROUTING_ENABLED` is set to `true`.

In legacy mode, CI uses `CI_RUNNER_LABEL`, then `LOCALCLUSTER_RUNNER_LABEL`, then `localcluster-books`. It still requires `CI_RUNNER_HOST` and runs the native capacity check. Configure `CI_RUNNER_LABEL` and `CI_RUNNER_HOST` before the first code pull request.

Profile mode requires a native profile and may include one desktop profile for this repository. Set `CI_RUNNER_LABEL` to the native profile's dedicated CI label. Do not use a deployment label for the profile route. The reusable selector runs on the native route, verifies its identity, and reads only this repository's runner inventory. It prefers an approved online idle desktop runner. If inventory access is unavailable, it selects the configured native profile. Invalid or missing profile data fails closed.

To enable profile mode, configure these repository settings:

| Setting | Purpose |
| --- | --- |
| Variable `CI_RUNNER_ROUTING_ENABLED` | Set to `true` to enable automatic profile selection. |
| Variable `CI_RUNNER_LABEL` | Dedicated native CI label used by the selector and native fallback. |
| Variable `CI_RUNNER_HOST` | Exact expected native hostname. |
| Variable `CI_RUNNER_INVENTORY_APP_CLIENT_ID` | Client ID for an App installed on this repository. |
| Secret `CI_RUNNER_PROFILES_JSON` | Private schema-version-1 profile document. |
| Secret `CI_RUNNER_INVENTORY_APP_PRIVATE_KEY` | Private key for the inventory App. |

Grant the App only the repository Administration read permission needed to list self-hosted runners. Restrict its installation to repositories the operator approved. Install a runner separately in each personal repository, or configure organization runner access explicitly. Copying this workflow does not grant access to another repository's runners or to a shared desktop pool.

Keep profile JSON in the repository secret. It contains runner names, hostnames, filesystem paths, Docker identity and capacity thresholds. Schema version 1 has a top-level `profiles` array. Every profile declares:

- `id`, `kind` (`native` or `desktop`), `repository`, `runnerName`, `expectedHost` and `labels`;
- `runnerRoot`, `workspaceRoot`, `dockerEndpoint`, `dockerId`, `dockerDataRoot`, `reportRoot` and `temporaryRoot`;
- `capacityRoots`, with `path`, `minimumFreeBytes`, `minimumFreePercent` and `minimumFreeInodePercent` for each actual workspace, Docker, report and temporary root.

The verifier checks the local runner registration, Docker daemon and actual runtime paths. It checks every configured root and rejects Windows-mounted paths, linked paths, missing roots, wrong runner identity and insufficient capacity. Native jobs keep the existing deployment-volume reserve check. Desktop jobs check their configured worker roots instead.

Desktop profiles also declare `instance`, `ownerRepository`, `ownerTaskId`, `markerPath` and `service`. These bind the configured slot to its root-owned installation marker and system service. Native profiles do not need these desktop installation fields. A desktop profile contains exactly one `-desktop` label and one `-canary` label. They are alternatives: each runner registration may carry only one at a time, and its marker must declare the exact selected label.

The marker is a root-owned mode-`0644` JSON file with the repository and task identity, owner repository and task identity, runner root and name, numeric runner ID, service name, `state: "service-installed"`, and a `customLabels` list containing exactly the selected profile label. Provision and update this file through the runner owner's management process; this template does not install runner services or write desktop ownership markers.

Desktop profiles must have CI-only labels and no deployment labels. A repository can use at most one existing desktop slot. The selector requires a complete repository inventory, refuses ambiguous identities, and sends ordinary work to native when the desktop is busy, offline or unavailable. Main publication takes a fresh selection after validation.

The workflow dispatch `pool` input supports `auto`, `desktop-canary` and `native-canary`. Explicit canaries require a non-main dispatch and cannot publish. Fork pull requests do not allocate trusted self-hosted runners. Do not give public fork workflows the profile secret or inventory App key.
