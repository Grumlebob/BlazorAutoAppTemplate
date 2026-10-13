# Cloud deployment

This folder contains the Cloud target. OpenTofu owns Hetzner infrastructure; Ansible owns host configuration and app deployment.

## Topology and boundaries

- `cloud-main` runs Caddy, Cloudflare Tunnel, SSH bastion, and the private observability backend.
- `cloud-app1` and `cloud-app2` run the app and observability agents.
- `cloud-db` runs PostgreSQL, Redis, exporters, and an observability agent.
- Only `cloud-main` receives public networking. Private nodes use its NAT for outbound traffic.
- Hetzner Cloud Firewalls protect public ingress; host firewalls enforce private-network service access.
- App, database, Redis, and observability ports stay private. Reach Grafana through `Scripts/open-observability-tunnel.sh`.
- Cloud CD uses a separate workflow and an existing self-hosted Linux x64 runner on `node-main`. The runner label comes from repository variable `LOCALCLUSTER_RUNNER_LABEL`; Cloud setup does not install it.

## Routes

- [First deployment](Setup.md)
- [Routine release, diagnosis, backups, restore, and teardown](Operations.md)
- [Cloud entry path](HowToDeployCloud.md)
- [Deployment target selection](../README.md)
