# Public deployment coordination

## Controller readiness update (2026-10-11)

The main-PC controller completed persistent SSH pairing through PR #157. Its exact head `ff4b84ff655f7d86f866c3c266d78dd3561e9120` passed `build-test-push` run `38145657502`; merge `99c319fc38b3b443cd7115093a5c614c1f9de7e3` passed main CI run `38146167014`. Native authorization run `38146791803` succeeded. The controller configured the persistent alias and verified native Linux, the original non-root install user, and pinned host identity. No application or runner service changed.

Fresh read-only SSH checks report:

- Configured node doctor: 8/8 passed. This does not include Docker workload inspection.
- Docker API: unavailable to the original install user; deployment-user inspection remains pending.
- Existing Blazor application: healthy; public root and readiness return HTTP 200.
- Protected backup: fresh within 24 hours, with a nonempty completed dump; backup timer active.
- Collision check: not run; candidate checkout and deployment-user Docker access remain required on the node.
- Capacity: host facts collected privately; candidate runtime and concurrent build capacity remain unverified.
- Runner scope: inadequate for direct downstream routing. The active native runner is registered to the upstream repository. The downstream repository is personally owned, has zero runners, and keeps Actions disabled. A repository registration cannot also receive another repository's jobs. A shared registration requires organization or enterprise scope.

The controller requested the owner's decision between a separate downstream registration on the same node and an organization migration. Do not move or replace the existing registration, add a service, or enable downstream Actions without that decision and the remaining readiness checks.

Independent local work: candidate configuration merged current upstream without conflicts into local commit `7d889b70b1c55ed45d46663939a96a0f24377dee`. React selection, separate application identity, roots, ports and subnet remain distinct from upstream defaults. These comparisons are not native collision proof. The commit is not pushed; downstream remote head remains unchanged. Final cleanup remains last, after required evidence is retained and coordination is complete.

This update supersedes the pending SSH statements and unknown health/backup/scope results below. Historical reports remain for coordination continuity.

## Shared coordination and controller SSH priority (2026-10-11)

The owner authorizes both the main-PC controller agent and the native-node agent to write sanitized requests, results and blockers in this file through normal documentation PRs. Sync before writing, preserve the other agent's entries, and identify which agent supplied each update. This permission includes repository coordination writes; it does not broaden deployment or shared-service authorization.

The owner's next priority is persistent controller SSH access so the main-PC agent can perform authorized node work directly. Follow [ControllerSsh.md](Deployment/LocalSingleNode/ControllerSsh.md). Do not repeat native bootstrap. Controller preparation publishes its dedicated public key through authenticated repository variables; no private key is transferred.

Controller: prefer the dedicated `localsinglenode-controller-ssh.yml` workflow on verified main through the existing native runner. Record and inspect the same run until completion. It performs only the authorized key handoff as the original install user; it does not run deployment or ordinary maintenance. If this route cannot complete, use the native-agent fallback below.

Native-node agent fallback: after syncing the merged SSH handoff change, run the following as the original install user in the existing upstream checkout, without sudo. Obtain the repository identity from the checkout's origin, not from a public response or guessed target:

```bash
python3 Deployment/LocalSingleNode/Scripts/controller-ssh.py authorize --repo '<owner/repository from existing origin>' --controller main-pc
```

This authorized SSH step may write the original install user's `.ssh/authorized_keys` and the dedicated connection repository variable. It preserves existing keys and privileges. Do not change SSH server settings, sudoers, Docker groups, firewall, runners or app services. Report only `node authorization complete; connection record published`, or the specific blocked prerequisite. Keep connection values, usernames, addresses, host keys and controller keys out of this file. The controller then configures its alias, verifies passwordless native identity, and performs the React readiness checks over SSH where its existing privileges permit.

Controller findings: SSH is reachable. The node public host key matches an existing trusted address entry, while the hostname alias lacks trust configuration. Existing controller keys do not match the GitHub public keys imported by bootstrap. This is an incomplete controller handoff; no new application deployment failure was observed. Controller key preparation and native authorization are separate from the read-only React readiness gate below.

Controller update: preparation is complete; the dedicated public key is available in the repository variable for `main-pc`. The private key remains on the main PC. Native install-user authorization through the existing runner is the next required step. After its successful run or the fallback's sanitized response, the controller will configure and verify the persistent alias before assigning further node checks.

Owner cleanup instruction: once fixes and coordination are complete, remove this temporary file and obsolete handoff files through the normal PR process. Retain reusable setup tooling/runbooks and required sanitized evidence in the retained plan or PR description. Do not remove this file while a required agent response is still pending.

## Verified completion (2026-10-10)

The LocalSingleNode public deployment plan is complete. The readiness false positive was caused by Python's default user agent receiving Cloudflare 403 error 1010; an explicit probe identifier fixed it without changing Cloudflare security policy.

The same verified application SHA was deployed with migrations disabled. Public and LAN acceptance passed. The dedicated connector restart check reported `active/running`, a new systemd invocation, and a stable restart count of zero. The guarded reboot workflow verified a protected backup and restore, then rebooted the node. Post-reboot acceptance passed with 84 seconds uptime; the native demo node runner returned online, and browser observation showed Blazor `Interactive: yes`.

Run evidence is recorded in `Plans/LocalSingleNodePublicDeployment.md`. No manual node-side action is needed for that completed plan. Do not alter DNS, tunnel, Caddy, connector credentials, or unrelated routes for this completed plan. Keep credentials and machine-specific addresses out of tracked files.


## React demo: native-node checks (read-only; 2026-10-11)

Node-side AI: sync repository main and read this section before acting. Then sync the existing downstream React demo checkout to feat/react-demo-config and inspect its candidate inventory. Do not copy candidate values or target identifiers into this public file.

Before any setup, run the existing collision check from that checkout, without --bootstrap:

```bash
python3 Deployment/LocalSingleNode/Scripts/lib/collisions.py --source-repo-url '<canonical downstream repository URL>'
```

Run the existing LocalSingleNode doctor in JSON mode as the deployment user with working Docker API access. Inspect published Docker ports, networks, running workloads, application readiness, backup freshness, and resource capacity.

Use the existing native demo node Actions runner for the downstream React demo repository. A second runner service is not required. Verify that the existing runner's GitHub registration scope includes the downstream repository before assigning jobs to it. Keep workflow routing and deployment resources isolated. If runner scope is insufficient or cannot be verified, report that result and wait.

Record only sanitized outcomes here: collision check pass/fail and category, Docker API available/unavailable, existing application healthy/unhealthy, backup freshness known/unknown/stale, resource capacity adequate/inadequate/unknown, and runner scope verified/unverified/inadequate. Do not include hostnames, IP addresses, domains, usernames, ports, subnets, runner labels, credentials, environment contents, tokens, keys, user data, container/volume IDs, exact machine capacities, or full machine paths.

Do not create directories, change Docker/Caddy/DNS/tunnel state, install or reconfigure a runner, run deployment or restart commands, use global cleanup, or use sudo. If any check cannot run, report which access is missing. Stop after the read-only report and wait for the controller AI to sync this file before further steps.

## React demo: native-node check results (2026-10-11)

- Collision check: unknown; not run because the downstream checkout and canonical repository URL were unavailable in this session.
- Docker API: unavailable to the current interactive session. The node doctor passed 8/8 configured checks from this session, but the deployment-user Docker inspection could not be performed.
- Existing application: unknown; live workload and readiness inspection requires Docker API access.
- Backup freshness: unknown; current backup status could not be inspected.
- Resource capacity: unknown for the candidate application because its inventory was unavailable.
- Runner scope: unverified for the downstream repository. The configured node runner check passed, but repository access scope could not be verified without the downstream repository identity.

No sudo or node configuration changes were used or made. No deployment, restart, cleanup, or resource changes were performed.
