# Public deployment coordination

## Verified completion (2026-10-10)

The LocalSingleNode public deployment plan is complete. The readiness false positive was caused by Python's default user agent receiving Cloudflare 403 error 1010; an explicit probe identifier fixed it without changing Cloudflare security policy.

The same verified application SHA was deployed with migrations disabled. Public and LAN acceptance passed. The dedicated connector restart check reported `active/running`, a new systemd invocation, and a stable restart count of zero. The guarded reboot workflow verified a protected backup and restore, then rebooted the node. Post-reboot acceptance passed with 84 seconds uptime; the node-demo runner returned online, and browser observation showed Blazor `Interactive: yes`.

Run evidence is recorded in `Plans/LocalSingleNodePublicDeployment.md`. No manual node-side action is needed for that completed plan. Do not alter DNS, tunnel, Caddy, connector credentials, or unrelated routes for this completed plan. Keep credentials and machine-specific addresses out of tracked files.


## React demo: native-node checks (read-only; 2026-10-11)

Node-side AI: sync repository main and read this section before acting. Then sync the existing downstream React demo checkout to feat/react-demo-config and inspect its candidate inventory. Do not copy candidate values or target identifiers into this public file.

Before any setup, run the existing collision check from that checkout, without --bootstrap:

```bash
python3 Deployment/LocalSingleNode/Scripts/lib/collisions.py --source-repo-url '<canonical downstream repository URL>'
```

Run the existing LocalSingleNode doctor in JSON mode as the deployment user with working Docker API access. Inspect published Docker ports, networks, running workloads, application readiness, backup freshness, and resource capacity.

Use the existing node-demo Actions runner for the downstream React demo repository. A second runner service is not required. Verify that the existing runner's GitHub registration scope includes the downstream repository before assigning jobs to it. Keep workflow routing and deployment resources isolated. If runner scope is insufficient or cannot be verified, report that result and wait.

Record only sanitized outcomes here: collision check pass/fail and category, Docker API available/unavailable, existing application healthy/unhealthy, backup freshness known/unknown/stale, resource capacity adequate/inadequate/unknown, and runner scope verified/unverified/inadequate. Do not include hostnames, IP addresses, domains, usernames, ports, subnets, runner labels, credentials, environment contents, tokens, keys, user data, container/volume IDs, exact machine capacities, or full machine paths.

Do not create directories, change Docker/Caddy/DNS/tunnel state, install or reconfigure a runner, run deployment or restart commands, use global cleanup, or use sudo. If any check cannot run, report which access is missing. Stop after the read-only report and wait for the controller AI to sync this file before further steps.

## Earlier node inventory: sanitized integration summary (2026-10-11)

An earlier read-only node-session report recorded a successful eight-check doctor result. Docker API access was unavailable in that interactive session, so the exact running workload, collision inventory and backup freshness were not verified. The controller previously verified the SSH host key but authentication failed; no remote command ran. Capacity was reported, but suitability for the downstream candidate inventory remains unverified. The completed Blazor deployment's earlier public/LAN, connector restart and protected backup/restore acceptance remain historical evidence in its plan.

The latest read-only React checks above supersede the earlier inventory request. Runner scope is still unverified and must be established before assigning downstream jobs. No node configuration, runner registration, container, volume, network, route, credential or lock was changed by the earlier inventory or this integration. Keep exact capacities and target details in private records.
