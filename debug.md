# Public deployment coordination

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
