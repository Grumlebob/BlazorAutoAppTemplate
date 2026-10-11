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

## Node-side inventory results (2026-10-11)

Read-only checks from the node session:

- Linux Mint 22.3; 8 logical CPUs; 7.4 GiB RAM total, with 4.7 GiB available at inspection; about 183 GiB free on the application storage filesystem.
- The read-only node doctor passed all eight checks: native Linux, configured runner, deployment-service Docker access, firewall, Caddy, protected runtime-secret permissions, more than 20 GiB free application storage, and mDNS.
- SSH is active. The controller previously verified the host key, but login authentication was rejected; no remote command ran. If SSH is needed, use the configured node install account with its matching authorized public key. No account, key, or SSH configuration was changed.
- Docker is active, but this interactive session cannot access the Docker API. Exact current container, volume, network, and backup-freshness inventory could not be verified from this session.
- The earlier public deployment handoff records successful public and LAN acceptance, connector restart verification, protected backup and restore through the guarded reboot workflow, and post-reboot application acceptance.

The existing application's containers, storage, networks, backups, and ingress can remain untouched when the new app uses its own Compose project and data resources, its own backup configuration, and a distinct ingress configuration if public access is required. Do not change the completed application's route, tunnel, connector, or Caddy configuration as part of this handoff.

Operator direction: one runner per computer is acceptable even when that computer hosts multiple apps. One runner service is active and the node doctor passes its configured runner check. Before assigning another repository's jobs to it, the controller should verify that its GitHub registration scope covers that repository. Keep each app's workflow routing and deployment resources isolated; add another runner service only if the required GitHub scope cannot support the shared node runner.

Main-PC follow-up: use the capacity figures for a modest demo plan and verify its resource limits against the app's needs; correct the SSH login account/key authorization only if remote shell access is required; confirm the runner scope for the new repository; and provision separate app data, backup, and ingress resources. An authorized operator can repeat the read-only Docker and backup inventory under the node's deployment context if exact live resource counts or backup freshness are needed. No node configuration or deployment resources were changed for this inventory.
