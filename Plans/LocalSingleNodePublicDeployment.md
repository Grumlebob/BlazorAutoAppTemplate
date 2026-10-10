# LocalSingleNode public deployment

Status: complete (2026-10-10). The operator requested agent-owned public DNS and tunnel setup, public end-to-end verification, and reusable scripts for cloned sites. This extends the completed LAN upgrade; it supersedes its Q6 exclusion for this work only. LocalCluster and Cloud live deployment remain unauthorized.

## Outcome

A fork can opt into public HTTPS with a configurable hostname and a dedicated remotely managed Cloudflare tunnel. The setup agent creates the tunnel and DNS, deploys a persistent native connector through LocalSingleNode CD, and verifies the application through its public URL. Operator tasks are authentication and any policy-required confirmation, not manual DNS or tunnel construction.

## Design

- Keep real account IDs, zone IDs, hostnames, tokens and resource state in private configuration or repository variables/secrets. Tracked examples use reserved example names.
- Use a dedicated tunnel and per-app connector service. Never join another topology's tunnel as an origin replica. Preserve all existing account resources.
- Provide a dependency-free Cloudflare API script with explicit apply/check modes, pagination, ownership state, conflict refusal, private credential files and no secret output. Save resource IDs immediately after creation. Never blindly retry an ambiguous creation request.
- Use a separate loopback-only Caddy listener for the tunnel's public hostname. Preserve LAN HTTP. Set the forwarded HTTPS scheme only on this listener; preserve the app's explicit Docker proxy trust. Keep data ports private.
- Pin and checksum the connector binary in an app-owned directory rather than upgrade another app's shared connector package. The service reads its token from a protected file, not command-line arguments.
- Configure deployment through validated LocalSingleNode repository variables and a connector secret. Repeated CD reuses the same resources and service. Disabling an already-public deployment requires an explicit removal procedure; never silently reclaim foreign resources.
- Public mode has public readiness and HTTP form acceptance in addition to LAN acceptance. HTTPS certificate validation stays enabled. Verify body content, redirects, cookie security and interactive Blazor behavior.

## Execution

- [x] P14.1 Update the upgrade plan and historical goal to identify this extension, preserving P1–P13 evidence.
- [x] P14.2 Implement reusable Cloudflare creation/check scripts, private configuration example, ownership/conflict checks and offline fixtures.
- [x] P14.3 Implement the isolated connector, loopback ingress, validated workflow configuration, HTTPS acceptance and deployment audit rules.
- [x] P14.4 Document agent setup, cloned-site usage, credential handling, interruption recovery and explicit removal. Run the full local gate and script fixtures before pushing. Merge only on exact-head green `build-test-push`, then wait for green main validation and publication.
- [x] P14.5 Inspect the authenticated account and zone, provision the dedicated tunnel and proxied DNS through the reusable script when protected API credentials are available, or through the authenticated dashboard for browser-based setup. Configure protected deployment inputs and deploy only to the authorized LocalSingleNode target. Keep resource IDs private and record each workflow ID before watching.
- [x] P14.6 Verify DNS, valid public TLS, exact readiness, independent controller form acceptance, cookies/redirects and real browser interaction. Prove repeatability and public recovery after connector restart and an authorized native reboot. Preserve LAN acceptance and existing account routes.
- [x] P14.7 Record merge/main CI, resource IDs, image digest, deployment and maintenance workflow URLs, public acceptance and browser evidence. Mark complete only when all required evidence passes.

## Current execution context

Implementation and repository gates run from the operator's controller PC and its prepared WSL checkout. The native LocalSingleNode deployment host is a separate PC. Its hostname, address and requested public hostname stay in private execution notes and private configuration; this tracked plan records reusable behavior. The operator is signed into Cloudflare and authorized this plan's execution on 2026-10-10.

Initial account inspection found that no existing DNS route or tunnel matched the requested demo hostname. Existing production routes remain unchanged. The dedicated tunnel route and DNS record were then created through the authenticated Cloudflare dashboard. A public resolver now returns proxied Cloudflare edge addresses, while the connector remains inactive until its service starts. Initial LAN readiness returned `Healthy`; an unmatched public Host returned an empty 200, so status alone did not prove application readiness. The acceptance script has been extended for HTTPS.

## Verified blocker and recovery plan (2026-10-10)

The reusable implementation is merged in PR #127 at `e9058539d9f16b0c7f2af210eff59dba57e99218`. PR CI `38056678309` and main CI `38057209236` passed. The first public deployment, `38057854524`, deployed that SHA and passed LAN acceptance, but public acceptance failed with HTTP 403 after its 180-second deadline. Release identity verification was skipped. Do not treat that run as successful or dispatch the same failing SHA again.

The latest main commit is `c84bf2177c4f4f33e932904d929506de4fd3ed42`. Its CI run `38059446086` completed successfully. WSL and Docker preflight also passed (`docker info` reported `linux`). The controller's public readiness probe returned HTTP 530 with successful TLS verification. Node-side diagnostics found the connector in `activating/auto-restart`, with systemd result `203/EXEC`; its journal reports an executable permission failure. The unit uses `DynamicUser`, while the connector binary sits below the private app deploy root, which the dynamic account cannot traverse. Cloudflare reported zero connector replicas. This explained why the tunnel was down at that point; the later connector repair restored it. It did not establish the source of the deployment's earlier HTTP 403, which was diagnosed below.

At the time of the initial diagnosis, the repository had two online repository-level self-hosted runners: one idle runner for LocalSingleNode deployment and one busy runner for CI/LocalCluster work. Current jobs are pinned by labels and hostname checks. Do not add laptops under either existing label: they could take jobs that require a specific host and then fail, or expose persistent runner state to more machines.

## Recovery sequence completed (2026-10-10)

The recovery steps were completed in order: historical and runner configuration were sanitized; the connector executable path and bounded systemd health gate were repaired; the probe's Cloudflare-blocked default user agent was identified and fixed; the same application SHA was redeployed with migrations disabled; connector restart and guarded native reboot recovery both passed. No Cloudflare security policy or unrelated tunnel route was changed. See the final evidence below.

## Runner capacity decision

Keep the LocalSingleNode deployment runner on the deployment node. It is already online under the dedicated LocalSingleNode label; CD checks out the verified main SHA there and deploys locally. The CI runner remains separate and has its hostname in the required `CI_RUNNER_HOST` repository variable.

Eight laptops could each run a self-hosted runner: GitHub currently charges no Actions minutes for self-hosted runners, but the owner pays for hardware, power and maintenance. Each runner handles one job at a time, so eight online runners can offer at most eight simultaneous jobs when labels, workflow dependencies and concurrency allow it. For this public repository, standard GitHub-hosted `ubuntu-24.04` jobs are also free and unlimited. Recommendation: evaluate moving ordinary CI to GitHub-hosted Linux and keep self-hosted runners only where a job needs the deployment node or its private network. This avoids adding eight machines just to get free CI capacity. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners), [runner concurrency](https://docs.github.com/en/actions/get-started/understand-github-actions).

For eight independent site clones, one dedicated deployment runner per site host is reasonable; each clone must have its own repository-level runner, exact label and host setting. Do not add laptops under an existing shared label. Keep deployment credentials off general CI runners. GitHub warns that untrusted pull-request code can compromise self-hosted runners on public repositories; the current workflows skip external fork PRs before runner allocation. This repository is owned by a personal account; custom runner groups are an organization/enterprise feature, so consider an organization only if stronger runner access boundaries become necessary. Artifacts and caches have separate storage quotas even where runner minutes are free. [Runner access guidance](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).

## Tracked diagnostic hygiene

The current change moves exact node diagnostics to ignored `Plans.local/` notes and replaces live machine identities, addresses, controller paths and external domains in tracked history and setup docs with generic examples. `debug.md` remains a sanitized handoff for the node agent. Published history is unchanged. A separate inventory/configuration follow-up is still needed: the existing Cloud/LocalCluster production inventories and simulation target profile contain live public hostnames in tracked runtime files. Move those values to validated repository/private settings without dispatching either deployment; that change is outside this LocalSingleNode repair.

## Follow-up diagnosis and resolution (2026-10-10)

The merged connector repair was deployed in workflow `38063118011` with migrations disabled. The Ansible deployment step and complete LAN acceptance passed. Public readiness then received Cloudflare HTTP 403 error 1010 because Python `urllib` sent its default `Python-urllib` user agent. Reproducing that request from the controller returned the same response; the explicit `BlazorAutoApp-Deployment-Readiness/1.0` user agent returned `200 Healthy`. Public PowerShell acceptance from the controller passed DNS, TLS, readiness, Blazor script, anonymous API, registration, login, secure cookies, same-origin navigation, and temporary-account cleanup. The issue was the probe's user-agent signature, not an app or tunnel outage. Cloudflare documents error 1010 as a browser-signature block ([Cloudflare error 1010](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/)). No Cloudflare policy change was needed.

PR #129 added the explicit probe identity, its offline test, and an opt-in app-scoped connector restart check. After merge, the same app SHA was redeployed with migrations disabled. The connector restart check proved a new active systemd invocation and stable restart count; a protected backup, maintenance validation, and guarded native reboot then completed. Post-reboot public and LAN acceptance passed.

## Final evidence (2026-10-10)

### Repository and CI

- [PR #127](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/127) merged the reusable public tunnel setup at `e9058539d9f16b0c7f2af210eff59dba57e99218`.
- [PR #128](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/128) merged the connector executable-path and systemd startup repair at `e3270d0b5f29dd5263d0cfe2f0dcf05c1dac5ea7`.
- [PR #129](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/129) merged the readiness user-agent fix and connector restart check at `52ad9aefdaf47c3e51fbcc8bcc5e1000542fb2c3`.
- PR #129 exact-head `build-test-push` [run 38064118538](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38064118538) and main CI [run 38064629554](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38064629554) passed.
- The local gate passed: format verification; Release build with zero warnings/errors; .NET tests (175 passed, 11 opt-in skipped); 72 LocalSingleNode Python fixtures; deployment audit; ShellCheck; and actionlint.

### Deployment and public acceptance

- [Successful LocalSingleNode deployment run 38065310862](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38065310862) used app SHA `e3270d0b5f29dd5263d0cfe2f0dcf05c1dac5ea7` with migrations disabled. LAN and public HTTP acceptance passed, and the running release identity matched digest `sha256:dd67fa2c034d545574268a27451baca657abbaff2b01f03e9efcf6e9202db7c3`. The required CI artifact came from run `38062355358`.
- Independent controller checks resolved DNS, verified TLS, received exact `Healthy` readiness, and observed HTTP 301 redirect to HTTPS followed by HTTP 200. The Cloudflare edge response included `via: 1.1 Caddy`.
- Full public acceptance passed registration, login, authenticated account access, secure/HttpOnly cookies, same-origin navigation, disabled default credentials, and cleanup of each temporary test account.
- The public browser reported configured `Interactive Auto`, assigned/current `WebAssembly`, and `Interactive: yes` after reboot.

### Connector and reboot recovery

- [Connector restart run 38065406977](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38065406977) passed: systemd returned `active/running` with exit status 0, a new invocation, and `NRestarts=0` stable through the check. LAN and public acceptance passed afterward.
- [Guarded reboot run 38065492542](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38065492542) verified a fresh protected backup and a 12-table isolated restore before scheduling reboot.
- [Post-reboot acceptance run 38065679204](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38065679204) passed LAN and public acceptance with uptime `84` seconds. The node-demo runner returned online, and the public HTTPS readiness endpoint returned `200 Healthy` with TLS verification successful.
- The dedicated LocalSingleNode runner is `node-demo-books` with its own `localsinglenode-books` label. The separate CI/LocalCluster runner is `node-main-books`; the two roles remain isolated.

No manual node-side action remains. Account IDs, tunnel IDs, tokens, node addresses and real hostnames remain in private configuration or ignored `Plans.local/` notes. The separate tracked Cloud/LocalCluster inventory-hostname cleanup remains outside this LocalSingleNode plan; neither deployment target was dispatched.
