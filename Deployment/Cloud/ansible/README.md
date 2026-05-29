# Cloud Ansible

Cloud Ansible playbooks and roles will live here.

Ansible owns host configuration and deployment only. Hetzner infrastructure resources belong in `Deployment/Cloud/infra/opentofu`.

Planned playbooks:

- provision hosts after OpenTofu creates them.
- deploy PostgreSQL and Redis on `cloud-db`.
- run the migration bundle once.
- deploy app containers on `cloud-app1` and `cloud-app2`.
- deploy Caddy and cloudflared on `cloud-main`.
- run acceptance checks.
