# Public deployment coordination

## Current diagnosis

The dedicated Cloudflare connector previously could not execute its binary under systemd's restricted service identity. The merged repair moved the checksum-pinned binary to the app-owned executable path while preserving `DynamicUser` and the protected token file.

The first deployment of that repair passed the LocalSingleNode deployment step and LAN acceptance. Public readiness then failed because Python `urllib` used its default `Python-urllib` user agent, which Cloudflare returned as HTTP 403 error 1010. The main-PC browser and curl worked; an explicit `BlazorAutoApp-Deployment-Readiness/1.0` probe also returned `200 Healthy`. Public PowerShell acceptance passed registration, login, secure cookies, and cleanup. This is a probe user-agent false positive; do not change DNS, tunnel, Caddy, or Cloudflare security policy.

## Main-PC work

A small follow-up updates the readiness probe user agent, adds an offline test, and adds an opt-in maintenance action that restarts only this app's connector, verifies a new healthy systemd invocation, and then runs full acceptance. The next authorized workflow run will deploy the same application SHA with migrations disabled and rerun public acceptance.

## Node-agent handoff

After that workflow, report the dedicated connector service `ActiveState`, `SubState`, `ExecMainStatus`, and restart count, plus a recent successful tunnel connection from the service journal. Keep credentials and machine-specific addresses out of this tracked file. Do not restart or reboot the node manually; the main-PC plan controls the recovery checks. If node-side diagnostics require a privilege or operator action that the workflow cannot perform, report the exact command and why before acting.
