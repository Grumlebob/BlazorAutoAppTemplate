# Deployment Cloud

Cloud deployment files for `bookscloud.example.com` live here.

`HowToDeployCloud.md` is the only cloud deployment plan and runbook.

Target architecture:

- Option A: multi-VPS Hetzner Cloud deployment with Cloudflare Tunnel.
- OpenTofu manages Hetzner infrastructure resources.
- Ansible manages host configuration and app deployment.
- `cloud-main` runs Caddy, cloudflared, acts as SSH bastion, and hosts Grafana/Prometheus/Alertmanager/Loki/Tempo.
- `cloud-app1` and `cloud-app2` run app containers and observability agents.
- `cloud-db` runs PostgreSQL, Redis, database exporters, and an observability agent.
- Public networking is assigned only to `cloud-main` (IPv4 and IPv6 are configurable). `cloud-app1`, `cloud-app2`, and `cloud-db` have no public addresses and use `cloud-main` for outbound NAT. Public inbound traffic is restricted by Hetzner Cloud Firewalls.
- Private-network service restrictions are enforced by host firewalls because Hetzner Cloud Firewalls do not secure private-network traffic.
- Observability endpoints are private only; use `Scripts/open-observability-tunnel.sh` to reach Grafana.

This folder must not import from `Deployment/LocalCluster`. Shared target-independent helpers belong in `Deployment/Common`.
