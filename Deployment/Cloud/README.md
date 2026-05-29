# Deployment Cloud

Cloud deployment files for `bookscloud.jacobgrum.com` live here.

`HowToDeployCloud.md` is the only cloud deployment plan and runbook.

Target architecture:

- Option A: multi-VPS Hetzner Cloud deployment with Cloudflare Tunnel.
- OpenTofu manages Hetzner infrastructure resources.
- Ansible manages host configuration and app deployment.
- `cloud-main` runs Caddy, cloudflared, and acts as SSH bastion.
- `cloud-app1` and `cloud-app2` run app containers.
- `cloud-db` runs PostgreSQL and Redis containers.
- Public IPv4 is enabled on all nodes for v1 outbound reliability; public inbound is restricted by Hetzner Cloud Firewalls.
- Private-network service restrictions are enforced by host firewalls because Hetzner Cloud Firewalls do not secure private-network traffic.

This folder must not import from `Deployment/LocalCluster`. Shared target-independent helpers belong in `Deployment/Common`.
