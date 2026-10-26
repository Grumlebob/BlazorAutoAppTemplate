# Cloudflared connector follow-ups

## Goal

Keep every LocalSingleNode and LocalCluster connector on a current, checksum-verified cloudflared release, without changing a host unless the owner has approved the deploy and the host state is verified.

## Status (2026-10-26)

- The pin on main is `PINNED_VERSION = "2026.10.0"` in `Deployment/LocalSingleNode/Scripts/lib/public_config.py`. The current release is 2026.10.4. Its linux-amd64 checksum is `sha256:ae5e8add7884b0531d66bbca4570d1de491ff6da51e4ebe7eb160cdf241d9e42`, verified against the release body and the downloaded binary.
- The Books and Books-react connectors on the single-node host shared with CarbonCalculator still run 2026.10.0. The owner holds their deploy. Template main was 81 commits past its last CD target `6b104590` (2026-10-16), including migration files.
- The CarbonCalculator connector deploy is blocked by its pre-migration backup. Its handoff is `Plans/Support/CarbonCalculator/Handoff-2026-10-26-Cloudflared.md` in the CarbonCalculator repository.
- Cloud is out of scope. The owner confirmed on 2026-10-26 that there is no cloud deployment. Do not work on Cloud inventories, OpenTofu state or pins.
- Whether the LocalCluster hosts exist is unconfirmed. They did not answer SSH scans, and no host key is pinned.

## Steps

1. **Bump the connector pin.** Set `PINNED_VERSION` and `PINNED_CHECKSUM` in `Deployment/LocalSingleNode/Scripts/lib/public_config.py` to 2026.10.4 and the checksum above, and update the version assertion in `Deployment/LocalSingleNode/Scripts/Tests/test_public.py`. Verify with the Linux unit run (`python3 -m unittest discover -s Deployment/LocalSingleNode/Scripts/Tests`) and `bash Deployment/Common/Scripts/audit-deployment.sh`. This is a code change, so the full PR gate applies. It deploys nothing by itself.
2. **Restart the connector on version change.** `Deployment/Common/ansible/roles/cloudflared/tasks/main.yml` installs the package when `cloudflared_version` changes, but its only service action is "enable and start", so a running connector keeps the old binary. Add a restart on version change, and update `Deployment/Common/Scripts/Component/lib/audit_deployment.py` in the same PR, as AGENTS requires. Verify with the audit and a syntax check of the role. Run this before any LocalCluster pin bump, and check on a test host that the new binary takes effect.
3. **Check the pre-migration backup coverage.** `Deployment/LocalSingleNode/Scripts/lib/backup.py` has no document-storage handling. CarbonCalculator's copy archives its app storage volume. If the template apps store files on a volume, those files are outside the pre-migration backup. Verify by reading how the apps store files, and by reading the backup code, before any template CD with migrations.
4. **Books decision (owner).** Either deploy template main with the fixes from steps 1 to 3 merged and the publish run green, or keep holding Books. Any Books deploy is an owner-approved CD dispatch from main, using the SHA whose publish run is green.
5. **LocalCluster (owner).** Confirm whether the hosts exist. If they do, apply step 2 first, then follow `Deployment/Common/SshTrust.md` before any connection: read each host's own Ed25519 fingerprint from its console and compare it. Do not pin from a scan alone.

## Decisions and reasons

- **Connector bumps ride planned app deploys.** The public role runs from the same target SHA as the app, and that deploy restarts the app. No connector-only deploy exists. Reason: the CD workflow deploys one SHA end to end, so a pin change ships every commit since the last deploy.
- **Checksums come from the release body and the downloaded binary.** Reason: a summary can misreport a digest.
- **Cloud stays out of scope.** Reason: the owner said there is no cloud deployment, and the OpenTofu state has no resources.
- **The template plan keeps its rule against dispatching `CD - Deploy LocalCluster` or `CD - Cloud`.** Reason: the existing operator decision for this plan.
