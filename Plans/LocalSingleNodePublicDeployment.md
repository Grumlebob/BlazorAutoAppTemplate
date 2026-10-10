# LocalSingleNode public deployment

Status: in progress (2026-10-10). The operator requested agent-owned public DNS and tunnel setup, public end-to-end verification, and reusable scripts for cloned sites. This extends the completed LAN upgrade; it supersedes its Q6 exclusion for this work only. LocalCluster and Cloud live deployment remain unauthorized.

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

- [ ] P14.1 Update the upgrade plan and historical goal to identify this extension, preserving P1–P13 evidence.
- [ ] P14.2 Implement reusable Cloudflare creation/check scripts, private configuration example, ownership/conflict checks and offline fixtures.
- [ ] P14.3 Implement the isolated connector, loopback ingress, validated workflow configuration, HTTPS acceptance and deployment audit rules.
- [ ] P14.4 Document agent setup, cloned-site usage, credential handling, interruption recovery and explicit removal. Run the full local gate and script fixtures before pushing. Merge only on exact-head green `build-test-push`, then wait for green main validation and publication.
- [ ] P14.5 Inspect the authenticated account and zone, provision the dedicated tunnel and proxied DNS through the reusable script when protected API credentials are available, or through the authenticated dashboard for browser-based setup. Configure protected deployment inputs and deploy only to the authorized LocalSingleNode target. Keep resource IDs private and record each workflow ID before watching.
- [ ] P14.6 Verify DNS, valid public TLS, exact readiness, independent controller form acceptance, cookies/redirects and real browser interaction. Prove repeatability and public recovery after connector restart and an authorized native reboot. Preserve LAN acceptance and existing account routes.
- [ ] P14.7 Record merge/main CI, resource IDs, image digest, deployment and maintenance workflow URLs, public acceptance and browser evidence. Mark complete only when all required evidence passes.

## Current execution context

Implementation and repository gates run from the operator's controller PC and its prepared WSL checkout. The native LocalSingleNode deployment host is a separate PC. Its hostname, address and requested public hostname stay in private execution notes and private configuration; this tracked plan records reusable behavior. The operator is signed into Cloudflare and authorized this plan's execution on 2026-10-10.

Initial account inspection found that no existing DNS route or tunnel matched the requested demo hostname. Existing production routes remain unchanged. The dedicated tunnel route and DNS record were then created through the authenticated Cloudflare dashboard. A public resolver now returns proxied Cloudflare edge addresses, while the connector remains inactive until its service starts. Initial LAN readiness returned `Healthy`; an unmatched public Host returned an empty 200, so status alone did not prove application readiness. The acceptance script has been extended for HTTPS.

## Verified blocker and recovery plan (2026-10-10)

The reusable implementation is merged in PR #127 at `e9058539d9f16b0c7f2af210eff59dba57e99218`. PR CI `38056678309` and main CI `38057209236` passed. The first public deployment, `38057854524`, deployed that SHA and passed LAN acceptance, but public acceptance failed with HTTP 403 after its 180-second deadline. Release identity verification was skipped. Do not treat that run as successful or dispatch the same failing SHA again.

The latest main commit is `c84bf2177c4f4f33e932904d929506de4fd3ed42`. Its CI run `38059446086` completed successfully. WSL and Docker preflight also passed (`docker info` reported `linux`). The controller's public readiness probe returned HTTP 530 with successful TLS verification. Node-side diagnostics found the connector in `activating/auto-restart`, with systemd result `203/EXEC`; its journal reports an executable permission failure. The unit uses `DynamicUser`, while the connector binary sits below the private app deploy root, which the dynamic account cannot traverse. Cloudflare reported zero connector replicas. This explains why the tunnel is down. It does not establish the source of the deployment's earlier HTTP 403; investigate that separately after the connector is healthy.

The repository has two online repository-level self-hosted runners: one idle runner for LocalSingleNode deployment and one busy runner for CI/LocalCluster work. Current jobs are pinned by labels and hostname checks. Do not add laptops under either existing label: they could take jobs that require a specific host and then fail, or expose persistent runner state to more machines.

Complete the remaining work in this order:

1. Record the successful main CI run `38059446086` against `c84bf2177c4f4f33e932904d929506de4fd3ed42`. This and the earlier failed deployment evidence are now recorded above.
2. Move exact node diagnostics to ignored `Plans.local/` notes and sanitize tracked `debug.md`, the upgrade goal/plan history, old runner plan, deployment docs and simulation guides. These edits are prepared in the current change; do not rewrite published history.
3. Remove the CI workflow's tracked machine-host fallback. Set the required `CI_RUNNER_HOST` repository variable from the verified runner host, then update workflow fixtures and the deployment audit. The variable is now configured; the workflow change is prepared in this branch. Keep the LocalSingleNode deployment runner on its deployment node.
4. Move the connector to `/usr/local/libexec/cloudflared-<app_name>/<version>/`, keeping the private app deploy root, `DynamicUser`, protected token file and checksum pinning. The service template, Ansible tasks, ownership collision checks, offline fixtures, deployment audit and `PublicSetup.md` now contain this fix.
5. Add a bounded systemd check after starting the unit. Require `ActiveState=active`, `SubState=running` and `ExecMainStatus=0` before public acceptance. This check and offline fixtures are prepared in this branch.
6. Run the required local gate sequentially from the verified WSL/Linux environment. Push the PR, require green `build-test-push` on its exact head, merge it, and wait for green main validation and publication. Do not weaken any audit rule or skip a check.
7. Deploy only the verified merged SHA to the authorized LocalSingleNode target. Verify the connector stays active, its restart count stays stable, and Cloudflare shows a connected replica before public acceptance.
8. Re-run public readiness and the full independent HTTPS acceptance. If HTTP 403 remains after the tunnel connects, capture the response headers, body classification, and Cloudflare request ID. Compare edge behavior with the local Caddy origin, then inspect Access, cache, and security policies without changing them until the source is identified.
9. Confirm valid public TLS, exact `Healthy` readiness, redirects, secure cookies, form acceptance, and interactive Blazor behavior from the main PC. Then prove a same-SHA deployment with migrations disabled, connector restart recovery, and public recovery after the authorized native reboot. Preserve LAN acceptance and all unrelated Cloudflare routes.
10. Record PR and merge SHAs, CI and CD run URLs, running image digest, connector recovery evidence, public acceptance, and browser evidence. Keep account IDs, tunnel IDs, tokens, node addresses, and hostnames in private configuration or ignored `Plans.local/` notes. Mark P14 complete only when every public and recovery check passes.

## Runner capacity decision

Keep the LocalSingleNode deployment runner on the deployment node. It is already online under the dedicated LocalSingleNode label; CD checks out the verified main SHA there and deploys locally. The CI runner remains separate and has its hostname in the required `CI_RUNNER_HOST` repository variable.

Eight laptops could each run a self-hosted runner: GitHub currently charges no Actions minutes for self-hosted runners, but the owner pays for hardware, power and maintenance. Each runner handles one job at a time, so eight online runners can offer at most eight simultaneous jobs when labels, workflow dependencies and concurrency allow it. For this public repository, standard GitHub-hosted `ubuntu-24.04` jobs are also free and unlimited. Recommendation: evaluate moving ordinary CI to GitHub-hosted Linux and keep self-hosted runners only where a job needs the deployment node or its private network. This avoids adding eight machines just to get free CI capacity. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners), [runner concurrency](https://docs.github.com/en/actions/get-started/understand-github-actions).

For eight independent site clones, one dedicated deployment runner per site host is reasonable; each clone must have its own repository-level runner, exact label and host setting. Do not add laptops under an existing shared label. Keep deployment credentials off general CI runners. GitHub warns that untrusted pull-request code can compromise self-hosted runners on public repositories; the current workflows skip external fork PRs before runner allocation. This repository is owned by a personal account; custom runner groups are an organization/enterprise feature, so consider an organization only if stronger runner access boundaries become necessary. Artifacts and caches have separate storage quotas even where runner minutes are free. [Runner access guidance](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).

## Tracked diagnostic hygiene

The current change moves exact node diagnostics to ignored `Plans.local/` notes and replaces live machine identities, addresses, controller paths and external domains in tracked history and setup docs with generic examples. `debug.md` remains a sanitized handoff for the node agent. Published history is unchanged. A separate inventory/configuration follow-up is still needed: the existing Cloud/LocalCluster production inventories and simulation target profile contain live public hostnames in tracked runtime files. Move those values to validated repository/private settings without dispatching either deployment; that change is outside this LocalSingleNode repair.

## Follow-up diagnosis (2026-10-10)

The merged connector repair was deployed to the LocalSingleNode target in workflow `38063118011` with migrations disabled. The Ansible deployment step passed; LAN readiness and the complete LAN account acceptance passed. Public readiness from the node runner then received Cloudflare HTTP 403 error 1010 because Python `urllib` sent its default `Python-urllib` user agent. Reproducing that request from the controller produced the same Cloudflare response. The same request with the explicit `BlazorAutoApp-Deployment-Readiness/1.0` user agent returned `200 Healthy`; public PowerShell acceptance from the controller passed DNS, HTTPS, readiness, Blazor script, anonymous API, registration, login, secure cookies, and temporary-account cleanup. Browser observation also reached Blazor Server interactive mode. This identifies a deployment-probe false positive rather than an application or tunnel outage. No Cloudflare security policy change is needed.

A follow-up change now gives readiness probes this explicit identifier, covers the request with an offline test, and adds an opt-in maintenance action that restarts only this app's connector and verifies a new healthy systemd invocation. After it merges, rerun the same application SHA with migrations disabled. Then verify connector stability, repeat deployment, connector restart recovery, and public recovery after the planned native reboot before marking P14 complete.

## Evidence

Implementation and live evidence will be recorded here or in the verified phase PR description. No public completion is claimed yet.
