# Public deployment coordination

## Verified completion (2026-10-10)

The LocalSingleNode public deployment plan is complete. The readiness false positive was caused by Python's default user agent receiving Cloudflare 403 error 1010; an explicit probe identifier fixed it without changing Cloudflare security policy.

The same verified application SHA was deployed with migrations disabled. Public and LAN acceptance passed. The dedicated connector restart check reported `active/running`, a new systemd invocation, and a stable restart count of zero. The guarded reboot workflow verified a protected backup and restore, then rebooted the node. Post-reboot acceptance passed with 84 seconds uptime; the node-demo runner returned online, and browser observation showed Blazor `Interactive: yes`.

Run evidence is recorded in `Plans/LocalSingleNodePublicDeployment.md`. No manual node-side action is needed. Do not alter DNS, tunnel, Caddy, connector credentials, or unrelated routes for this completed plan. Keep credentials and machine-specific addresses out of tracked files.

## Node-side inventory handoff (2026-10-11)

The controller is preparing a separate React demo on the existing LocalSingleNode. Strict SSH host-key verification succeeded through an existing Windows trust entry, but login authentication was rejected; no remote command ran.

Please use the node's local session to report a sanitized, read-only inventory for the controller AI:

- OS family/version, CPU and memory capacity, and free storage suitable for a separate app.
- Whether the existing application, containers, volumes, networks, routes, and backups can remain untouched while adding an independent app.
- Whether an existing runner can safely deploy a separate repository without sharing the existing app's runner identity or deployment resources.
- Whether SSH access from the controller is the supported path, and what login account or key authorization is needed.

Do not include hostnames, IP addresses, domains, usernames, repository names, ports, subnets, runner labels, credentials, environment values, tokens, or keys in this file. Do not change configuration, add keys, restart services, touch containers or volumes, or alter locks. Record only sanitized findings here, then tell the controller AI the inventory is ready.
