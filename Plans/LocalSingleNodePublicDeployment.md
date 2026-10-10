# LocalSingleNode public deployment

Status: in progress (2026-10-10). The operator requested agent-owned public DNS and tunnel setup, public end-to-end verification, and reusable scripts for cloned sites. This extends the completed LAN upgrade; it supersedes its Q6 exclusion for this work only. LocalCluster and Cloud live deployment remain unauthorized.

## Outcome

A fork can opt into public HTTPS with a configurable hostname and a dedicated remotely managed Cloudflare tunnel. The setup agent creates the tunnel and DNS, deploys a persistent native connector through LocalSingleNode CD, and verifies the application through its public URL. Operator tasks are authentication and any policy-required confirmation, not manual DNS or tunnel construction.

## Design

- Keep real account IDs, zone IDs, hostnames, tokens and resource state in private configuration or repository variables/secrets. Tracked examples use reserved example names.
- Use a dedicated tunnel and per-app connector service. Never join another topology's tunnel as an origin replica. Preserve all existing account resources.
- Provide a dependency-free Cloudflare API script with explicit apply/check modes, pagination, ownership state, conflict refusal, private credential files and no secret output. Save resource IDs immediately after creation. Never blindly retry an ambiguous creation request.
- Use a separate loopback-only Caddy listener for the tunnel's public hostname. Preserve LAN HTTP. Set the forwarded HTTPS scheme only on this listener; preserve the app's explicit Docker proxy trust. Keep data ports private.
- Pin and checksum the connector binary in an app-owned directory rather than upgrade another app's shared connector package. The service reads its token from a protected file, not command-line arguments.
- Configure deployment through validated LocalSingleNode repository variables and a connector secret. Repeated CD reuses the same resources and service. Disabling an already-public deployment requires an explicit removal procedure; never silently reclaim foreign resources.
- Public mode has public readiness and HTTP form acceptance in addition to LAN acceptance. HTTPS certificate validation stays enabled. Verify body content, redirects, cookie security and interactive Blazor behavior.

## Execution

- [ ] P14.1 Update the upgrade plan and historical goal to identify this extension, preserving P1–P13 evidence.
- [ ] P14.2 Implement reusable Cloudflare creation/check scripts, private configuration example, ownership/conflict checks and offline fixtures.
- [ ] P14.3 Implement the isolated connector, loopback ingress, validated workflow configuration, HTTPS acceptance and deployment audit rules.
- [ ] P14.4 Document agent setup, cloned-site usage, credential handling, interruption recovery and explicit removal. Run the full local gate and script fixtures before pushing. Merge only on exact-head green `build-test-push`, then wait for green main validation and publication.
- [ ] P14.5 Inspect the authenticated account and zone, provision the dedicated tunnel and proxied DNS through the reusable script when protected API credentials are available, or through the authenticated dashboard for browser-based setup. Configure protected deployment inputs and deploy only to the authorized LocalSingleNode target. Keep resource IDs private and record each workflow ID before watching.
- [ ] P14.6 Verify DNS, valid public TLS, exact readiness, independent controller form acceptance, cookies/redirects and real browser interaction. Prove repeatability and public recovery after connector restart and an authorized native reboot. Preserve LAN acceptance and existing account routes.
- [ ] P14.7 Record merge/main CI, resource IDs, image digest, deployment and maintenance workflow URLs, public acceptance and browser evidence. Mark complete only when all required evidence passes.

## Current execution context

Implementation and repository gates run from the operator's controller PC and its prepared WSL checkout. The native LocalSingleNode deployment host is a separate PC. Its hostname, address and requested public hostname stay in private execution notes and private configuration; this tracked plan records reusable behavior. The operator is signed into Cloudflare and authorized this plan's execution on 2026-10-10.

Initial account inspection found five existing DNS records and three tunnels. None matched the requested demo route. `books-prod` is healthy and serves two existing apps; it remains unchanged. The tunnel route and DNS record were then created through the authenticated Cloudflare dashboard. A public resolver now returns proxied Cloudflare edge addresses, while the tunnel remains inactive until its connector is deployed. Initial LAN readiness returned `Healthy`; an unmatched public Host returned an empty 200, so status alone did not prove application readiness. The acceptance script has been extended for HTTPS.

## Evidence

Implementation and live evidence will be recorded here or in the verified phase PR description. No public completion is claimed yet.
