# Public deployment coordination

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

## Controller continuation: runner decision (2026-10-11)

The owner has explicitly approved a separate downstream repository runner registration on the same native node, preserving the existing upstream runner. This supersedes the earlier default against adding a second service for this delivery only. Native collision, Docker-backed workload/doctor and capacity checks must still pass before registration or owned app setup. It does not authorize moving the existing runner, broader SSH privileges, shared-service disruption, or bypassing release gates.

PR #158 merged persistent SSH/readiness evidence and profile-aware test instructions as `ef6c844cb323897a4ae251b97aaffd72ac420e72`, after exact-head required run `38148042847` succeeded. Main run `38148508808` remains pending at this checkpoint. PR #160 isolates offline fixtures from customized deployment settings; local template and candidate checks pass, and exact-head CI is pending. Both candidate application profiles and React package checks pass locally. The candidate remains unpushed. Use the new read-only native readiness workflow only after its own merge and green main CI. Final cleanup remains last.
