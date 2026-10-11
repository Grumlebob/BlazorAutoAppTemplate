# React public delivery from one repository

## Owner requirements and current state

The owner confirmed on 2026-10-11: keep both public apps on the existing native demo node, using this repository and its existing runner. Do not create another hosted repository or runner service. The template default stays `BlazorAuto`; both frontend profiles remain supported. Existing Blazor services, data, release source and public access must remain healthy.

P0-P7 frontend implementation is complete; retain its evidence in [ReactFrontendProfile.md](ReactFrontendProfile.md#14-evidence-and-completion). Public React delivery and P9 operational/fresh-clone acceptance remain incomplete. Cleanup is complete: the extra hosted repository is absent, its temporary readiness secret is absent, and operator cleanup removed the retired local clone, eight scratch files, three log directories and its own script. PR #163 merged as `310dca9610419523c9f07412ed8ea6c0cb665ef4`, with exact-head run `38152925871` and successful main run `38153407171`. Persistent controller SSH still works. Do not restore the retired repository or installation notes.

## Release design

Keep one source history and one normal main release pipeline. A clone normally publishes only the profile selected by `frontend-profile.txt`, with the existing image and migration artifact names. Existing LocalCluster/Cloud consumers and the primary LocalSingleNode path retain that behavior.

Add an explicit optional repository setting for additional frontend publication, initially unset. For this installation it will enable `React` alongside the selected Blazor profile after the publishing implementation is merged and validated. Validate the allowed profile names, reject duplicates/invalid values, and always include the selected profile. Do not interpolate raw variable values into shell commands or filesystem paths. New clones inherit no extra publication requirement.

Publish enabled profiles sequentially in the trusted main publishing job. Retain the required `build-test-push` check and fail main publishing if any requested profile fails. Reuse existing validation, migration staging, smoke, labeling and manifest production rather than creating another independent CI pipeline. PRs continue to validate both frontends; PR images remain ineligible for deployment.

The selected profile keeps `app_image:<main-sha>` and its existing artifact name. Additional React uses a distinct configured/derived GHCR image repository and artifact name, with the same source main SHA and CI run/attempt. Each image has its own registry digest and manifest with the actual baked frontend and acceptance profile. Shared migration bytes may be reused only after existing staging hash/provenance validation; manifests remain profile-specific. Never overwrite the primary image/artifact, use a mutable tag for deployment, toggle the tracked default back and forth, or treat a generic successful CI run as proof that an optional React release exists.

## Deployment and application identity

Extend the existing LocalSingleNode deployment path to select an explicitly configured application instance; default dispatch remains the primary app. Resolve the instance through validated protected configuration, not an arbitrary input path or untrusted manifest. Keep host connection values, ports, roots, subnet, origins and app secrets outside tracked files/public logs. No real installation values belong in this plan.

The primary instance continues to derive its expected frontend from the target main commit and use existing release settings. The additional React instance binds its own application identity, React frontend, `ReactPublicV1` acceptance, image/artifact identity and inventory settings. Verify expected frontend/image/source before migrations or mutation; do not infer the expected identity from the artifact under verification. Reject missing/unknown instances, profile/image mismatches and cross-app roots or resources.

Both instances use this repository's existing native runner registration. GitHub environment and application secret isolation must be explicit. Generate new React database/cache secrets and data-protection storage; never copy the Blazor application's credentials or user data. Keep repository/native ownership markers distinct by app while allowing the same canonical source repository.

Keep trusted main-only dispatch, exact main SHA ancestry, successful exact-source CI, immutable registry digest, manifest/bundle hashes, image labels, native identity, shared deployment lock and scoped app ownership checks. Update affected deployment audits and negative fixtures in the same code packets. This is a LocalSingleNode extension; do not dispatch Cloud or LocalCluster.

## Existing-node setup and readiness

Use persistent controller SSH where existing privileges suffice. Use the existing deployment runner for Docker-backed checks and authorized privileged app setup. Do not grant root/deploy SSH, install-user Docker membership or new sudoers access.

Before mutation, run the reusable read-only readiness workflow with this repository as the candidate source and validated private React instance settings. Require configured ownership, actual native host, ordinary collision checks without bootstrap, Docker access, healthy existing workloads, fresh protected backup and measured capacity. Readiness may use a temporary masked Actions secret; remove it when finished. Record a dispatch once and inspect that run rather than dispatching again after observation interruptions.

Add an owned-app-only setup route for this already configured native node. It must verify protected host/current ownership, selected instance and collision/readiness immediately before mutation under the shared lock. Create only the React app's roots, ownership marker, fresh app secrets and backup integration. Reuse existing scoped public setup scripts for its Caddy/tunnel/DNS configuration after gates pass. Never rerun the full machine bootstrap, hostname/SSH/group changes, shared dependency provisioning or unconditional shared-service restarts to add this app. Preserve the current runner and Blazor app.

The old private target-intent note was intentionally removed. Obtain required React origin and installation preferences through current private configuration or an operator answer before dependent live setup; do not reconstruct the deleted repository/configuration or guess host values. Continue independent release/tooling work while a target preference is pending.

## Work packets and acceptance

| Packet | Deliverable | Required evidence |
| --- | --- | --- |
| SR1 | Optional additional-profile publication in existing CI, unique image/artifact identities and release validation | Default selected-only output unchanged; both-profile optional publication succeeds; invalid/duplicate profiles and mismatched manifests fail; no primary artifact overwrite; full local gate and exact-head/main CI |
| SR2 | Validated per-app LocalSingleNode selection using existing workflow and runner | Primary default unchanged; private instance settings validated; React image/profile/acceptance pinned independently; wrong app/source/profile/artifact rejected before mutation; affected audit/fixtures pass |
| SR3 | Owned-app-only existing-node setup | No host bootstrap, second runner, privilege expansion or foreign-resource mutation; lock/ownership/collision/failure fixtures prove scope; own roots/secrets/backups only |
| SR4 | Private React installation readiness and immutable release | Native collision/Docker/workload/capacity/backup all pass; expected React package/manifest/digest from this repository's exact successful main run; Blazor baseline healthy |
| SR5 | Owned React public setup and LocalSingleNode deployment | Single recorded authorized dispatch; running digest/profile/source match release; normal LAN/public HTTPS and public browser/denial checks pass; no accounts or anonymous writes |
| SR6 | Persistence, operations, template walkthrough and final cleanup | Public seed survives one scoped React restart; Blazor stays healthy; backup/doctor/recovery and brief observation recorded; fresh-clone/default/React/extension/release docs verified; temporary secrets/notes/worktrees removed |

SR1-SR3 may be implemented independently of missing private public-origin preferences. SR4 depends on merged green implementation, and SR5 depends on readiness plus the exact immutable React release. SR6 is required for delivery completion. Keep .NET build/test sequential in each checkout and use the repository's full local gate for code/configuration. Markdown-only packets use review and `git diff --check`, plus required PR/main CI.

## Completion and authorization

Continue the original public-only React delivery through these replacement packets. The owner's confirmation retains both public apps on the existing node and reuses its runner; repository deletion withdrew only the separate-repository/runner method. Existing authorization covers implementation, required gates, normal PR creation/merge after exact-head success, owned React public setup, LocalSingleNode deployment of a verified main release and one scoped React restart. It excludes accounts/providers, paid services, bootstrap of this Windows/WSL controller, Cloud/LocalCluster dispatch, foreign-resource deletion and unrelated shared-service disruption.

Mark full delivery complete only when SR1-SR6 and the profile plan's applicable R01-R16/final acceptance have authoritative evidence. Cleanup alone, a green build, image smoke or homepage response is insufficient. Record every packet's PR/head/check, merge/main run, release/dispatch and sanitized operational evidence. Private facts and credentials remain private.

## Ledger

- Planning packet: documents the owner's confirmed single-repository/two-app outcome and verified completed cleanup. No publishing setting, app configuration, readiness secret, node resource or deployment has changed in this packet. Required PR/head/merge/main evidence will be recorded in its PR description.
- Next: SR1 release/profile contract and optional publication implementation. Preserve the existing default pipeline and runner.

### SR1 implementation evidence

Optional publication now uses the validated `ADDITIONAL_FRONTEND_PROFILES` repository variable in the existing trusted-main publishing job. Unset preserves selected-only publication and primary image/artifact names. The additional profile has a distinct derived image/artifact, its own manifest/digest, a fresh profile-specific browser build, staging hash/source/run validation, smoke before push and scoped cleanup. The shared manifest writer also verifies ownership labels and refuses existing output. No repository setting or deployment was changed during implementation.

Local validation passed: formatting; both complete solution suites (Blazor 211 passed/13 expected skips, React 203 passed/13 expected skips); 55 CI fixtures including 16 new release fixtures with zero skips on Linux; all single-node/common/cluster and shell fixtures; release/cloud/observability validation; deployment audit; template rendering; YAML, shell and Actions lint; and single-node Ansible syntax. A transient local syntax-check working-directory failure passed after the gate explicitly re-anchored each subprocess to its checkout. Full gate passed before pushing; integration from current main added only Markdown. Required PR/head/merge/main evidence belongs in the implementation PR description. Live optional publication remains to be enabled and verified after merged main is green.

### SR2 implementation

The existing LocalSingleNode workflow now accepts `primary` (default) or `additional`. Protected additional configuration binds app settings and expected frontend before release download, uses a distinct environment, derives separate release names, rejects primary/cross-app roots, ports, subnets and LAN names, and requires protected native repository/root ownership. Runtime verification and privileged collision checks share the selected settings. Public metadata is explicit per instance; temporary configuration is exclusively created with mode `0600` and cleaned on failure or success. See [ApplicationInstances.md](../Deployment/LocalSingleNode/ApplicationInstances.md). This packet does not create an application or runner and does not dispatch deployment. Local and required PR/main validation evidence will be recorded after checks complete.

SR2 full local gate passed: both profile suites retained 211/203 passing tests with 13 expected skips each; all Python and shell fixtures, validators, audit, rendering, lint and single-node playbook syntax passed. All 15 new instance fixtures passed. No application configuration, runner, native resource or deployment changed. Required exact-head/main CI remains pending.


### SR3 implementation

The new existing-runner additional-app setup workflow requires trusted enabled main, a distinct protected environment, exact-source successful main CI and primary native ownership. Under the shared lock it repeats native workload/backup/capacity readiness and ordinary collisions. A privileged read-only guard refuses foreign app containers/networks/data volumes, backup units and symlinked roots before the app-only playbook creates owned roots, fresh retained secrets, persisted settings, scoped backup integration and one LAN HTTP firewall allowance. Backup integration skips deploy group and shared reboot-helper changes for this route. No full bootstrap, additional runner, host package/identity/SSH changes or shared-service restart occurs.

Public configuration publishing also accepts a validated additional environment and protected instance file, verifies provider state and token binding, and writes only that environment's public variables and secrets. Primary public configuration stays intact. Setup and public publication have offline scope/failure fixtures and deployment audit coverage. Live readiness, setup and public deployment remain pending.

SR3 local gate passed before push: Blazor 211/13 and React 203/13 passed/expected skips; 55 CI, 130 single-node (17 new scoped-setup/public-publication checks), 69 common and 23 cluster fixtures; all shell fixtures, validators, audit, rendering and lint; and syntax for all three native playbooks. Actions lint caught masked command-substitution exit statuses in two exports; assignments now fail correctly before export, and lint plus relevant gates passed again. Installation settings remain private; no node resources or deployment changed.

Provider preflight subsequently found that Cloudflare returns `config: null` for a newly created remotely managed tunnel. The protected ownership state recorded the created tunnel before this response stopped setup; no DNS record or connector credential was created. The shared helper now treats an absent configuration as empty only after recorded tunnel ownership matches the account inventory. It still refuses malformed non-object configuration and foreign ingress. Three offline regressions cover initialization without duplicate resources, read-only refusal without mutation and malformed configuration refusal. The deployment audit requires these checks. Final local gate and exact-head/main CI evidence are recorded in the SR3 PR description.

