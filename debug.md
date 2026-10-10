# Public deployment diagnosis

Checked on 2026-10-10 from `node-demo`.

- Checkout was clean on `main`; `HEAD` and `origin/main` were both `e9058539d9f16b0c7f2af210eff59dba57e99218`.
- `setup-status.sh --node node-demo --json --expected-address 192.168.0.212` confirmed native hostname `node-demo` and detected LAN address `192.168.0.212`.
- `cloudflared-books.service` was in `activating/auto-restart`, with `Result=exit-code`, `ExecMainStatus=203`, and 211 restarts.
- Recent journal entries repeatedly reported: `Failed to execute /opt/books/cloudflared/2026.10.0/cloudflared: Permission denied`, followed by `status=203/EXEC`.
- The unit runs with `DynamicUser=cloudflared-books` and `Group=cloudflared-books`. `/opt/books` is mode `0750`, so the service identity cannot traverse that directory to execute the binary. The connector never starts; there is no tunnel connection or authentication error in the journal. This aligns with Cloudflare showing zero replicas and the main PC receiving HTTP 530. The local evidence does not establish the specific source of the CD's HTTP 403.
- Token metadata only: `/etc/books/cloudflare-token`, mode `0600`, size 185 bytes, modified 2026-10-10 16:01:01 CEST. Its contents were not read or recorded.
- Journal access worked without sudo.
- Runbook status returned the agent `deploy` action. It was not run because the request prohibited `/etc` edits and service restarts. No host changes or CD dispatch occurred.
- The findings were sent to the earlier main-PC setup thread.

Use this file for follow-up notes and communication.
