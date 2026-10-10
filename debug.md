# Public deployment coordination

## Current diagnosis

The dedicated Cloudflare connector could not execute its binary under systemd's restricted service identity. systemd reported an execution failure, no connector replica connected, and public readiness returned HTTP 530. This diagnosis does not explain the earlier public acceptance HTTP 403.

## Main-PC work

A reviewed fix is being prepared to install the checksum-pinned executable in an app-specific, traversable system path, keep `DynamicUser` and the protected token file, and require systemd to report `active/running` before public acceptance.

## Node-agent handoff

Do not edit the service, token, tunnel, DNS, or Caddy configuration manually while the PR is in progress. The authorized LocalSingleNode deployment workflow will apply the merged fix on its registered deployment runner.

After the deployment workflow runs, report the dedicated connector's active/substate and restart count, whether Cloudflare reports a connected replica, and any sanitized public acceptance result. Do not include credentials or machine-specific addresses in this tracked file. If the workflow fails and requests native action, send the exact required action to the operator before proceeding.
