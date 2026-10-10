# Public deployment coordination

## Verified completion (2026-10-10)

The LocalSingleNode public deployment plan is complete. The readiness false positive was caused by Python's default user agent receiving Cloudflare 403 error 1010; an explicit probe identifier fixed it without changing Cloudflare security policy.

The same verified application SHA was deployed with migrations disabled. Public and LAN acceptance passed. The dedicated connector restart check reported `active/running`, a new systemd invocation, and a stable restart count of zero. The guarded reboot workflow verified a protected backup and restore, then rebooted the node. Post-reboot acceptance passed with 84 seconds uptime; the node-demo runner returned online, and browser observation showed Blazor `Interactive: yes`.

Run evidence is recorded in `Plans/LocalSingleNodePublicDeployment.md`. No manual node-side action is needed. Do not alter DNS, tunnel, Caddy, connector credentials, or unrelated routes for this completed plan. Keep credentials and machine-specific addresses out of tracked files.
