# Agent-driven public HTTPS setup

This optional extension publishes an existing native LocalSingleNode installation through Cloudflare. Each cloned site uses its own hostname, dedicated tunnel, app-owned connector service and distinct loopback origin port. Public setup runs from the controller; the connector is installed through the native deployment runner. Never bootstrap the controller or WSL as a node.

## Authentication and configuration

The agent asks for the intended domain, subdomain and native node. The operator signs in or supplies a scoped API credential through a protected file, never chat. The agent creates DNS and tunnel resources and verifies the site. Browser-based credential creation and public exposure may require confirmation under the agent's browser policy; the operator should not construct resources manually.

Use an API token with account Cloudflare Tunnel Edit and zone DNS Edit plus Zone Read, restricted to the intended account and zone. Keep it on the controller only, outside git, in a current-user-owned mode-0600 file under a private mode-0700 directory. The connector receives only its tunnel credential. Use an API token lifetime appropriate to the setup session; its expiration does not stop the installed connector.

Use the controller's Linux/WSL tools:

```bash
PUBLIC_DIRECTORY="$HOME/.local/share/my-site-public"
install -d -m 0700 "$PUBLIC_DIRECTORY"
cp Deployment/Common/cloudflare.example.json "$PUBLIC_DIRECTORY/config.json"
```

The agent edits this private JSON with the account ID, active zone, unique tunnel name, requested hostname and unused origin port. Tracked defaults contain no real installation values. Every app on a shared node needs a distinct origin port.

## Agent execution

1. Verify green main CI, the online LocalSingleNode runner and the intended `LOCALSINGLENODE_HOST`. Inspect existing Cloudflare DNS and routes.
2. After protected authentication, create or reconcile the resources:

   ```bash
   bash Deployment/Common/Scripts/setup-public-tunnel.sh \
     --config "$PUBLIC_DIRECTORY/config.json" \
     --token-file "$PUBLIC_DIRECTORY/api.token" \
     --state "$PUBLIC_DIRECTORY/state.json" \
     --connector-token-file "$PUBLIC_DIRECTORY/connector.token" --apply
   ```

   This creates the remotely managed tunnel, hostname ingress, catch-all 404 and proxied DNS CNAME. IDs are recorded immediately in private ownership state. Foreign tunnel names and conflicting DNS records of any type are refused. Credential outputs are atomic mode-0600 files; tokens never appear in output. Retain the state file.
3. Run the same command without `--apply` and `--connector-token-file` to check resources without mutation. Configuration success is not proof of a healthy connector or application.
4. Configure the intended repository:

   ```bash
   python3 Deployment/LocalSingleNode/Scripts/configure-public-deployment.py \
     --config "$PUBLIC_DIRECTORY/config.json" \
     --state "$PUBLIC_DIRECTORY/state.json" \
     --connector-token-file "$PUBLIC_DIRECTORY/connector.token" \
     --repo OWNER/REPOSITORY --node NATIVE-NODE
   ```

   This verifies ownership state, tunnel-token identity and the repository's native host. It refuses different existing public variables. It encrypts `LOCALSINGLENODE_PUBLIC_TUNNEL_TOKEN` through `gh secret set` using standard input and sets `LOCALSINGLENODE_PUBLIC_HOSTNAME`, `LOCALSINGLENODE_PUBLIC_TUNNEL_ID` and `LOCALSINGLENODE_PUBLIC_ORIGIN_PORT`. Tokens are not command arguments.
5. Dispatch **CD - Deploy LocalSingleNode** from verified main through the normal release provenance gate. Record the returned run ID before watching. Never redispatch because a watcher stops. LocalCluster and Cloud deployment are unnecessary.
6. CD installs the checksum-pinned binary in `/usr/local/libexec/cloudflared-<app_name>/<version>/`, with traversable root-owned parent directories, then enables `cloudflared-<app_name>.service`. A bounded systemd check requires the service to be active and running before public acceptance. It uses systemd credentials and a protected root-owned token file. Only `<app_name>-public.caddy` is added to shared Caddy, bound to the configured loopback port. HTTPS and Cloudflare client IP forwarding apply only there. The existing LAN listener remains unchanged.
7. Require LAN and public acceptance. From the independent controller:

   ```powershell
   powershell -NoProfile -File Scripts/Test-DeployedSite.ps1 -BaseUrl https://demo.example.com
   ```

   Certificate validation stays enabled. Require exact readiness, Blazor assets, registration, fresh login, account management, anonymous API denial, rejected default credentials, Secure/HttpOnly auth cookies and temporary-account deletion. Verify interactive Blazor and relevant live transport in a real browser. Prove public recovery after an authorized connector restart and native reboot. Record resource IDs, workflow IDs, release SHA/digest and public evidence before completion.

## Repeated setup and recovery

Re-run with the same private config and state. Owned resources are reused without duplicate tunnels or DNS records. Use a new private directory and unique names for another clone. Do not join another node's tunnel as a replica serving a different origin.

An ambiguous tunnel creation leaves a pending state and stops automatic retries/adoption. Inspect Cloudflare and prove the request outcome before deliberately repairing private state. Missing or changed recorded resource IDs also stop setup. Unexpected routes and origin settings are preserved and refused; empty defaults added by Cloudflare are accepted. Inspect edge cache and Access policies if public acceptance receives stale content, a challenge or an authentication gate.

Keep failed workflow IDs and volumes. Fix repository failures through PR/local-gate/exact-head CI/green main before resuming. The connector binary is isolated from other apps; no shared host package is upgraded.

## Explicit rotation and removal

Normal CD refuses changed connector credentials or public identity. Intentional rotation requires authorizing and recording the owned tunnel, replacing only this app's protected token through a reviewed maintenance procedure, updating its repository secret and restarting its dedicated service.

Removal requires explicit authorization and verified ownership IDs. Stop and disable only this app's connector, remove only its public Caddy site after validating the remaining configuration, and remove its owned Cloudflare resources and repository inputs. Preserve LAN deployment, volumes, backups and other apps. Clearing variables alone is refused for an already-published node. Never reclaim locks or run global Docker cleanup.

## References

- [Cloudflare API setup](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel-api/)
- [Tunnel token files](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/)
- [Caddy forwarded-header behavior](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#defaults)
