# Cloud Ansible

Cloud Ansible playbooks and roles live here.

Ansible owns host configuration and deployment only. Hetzner infrastructure resources belong in `Deployment/Cloud/infra/opentofu`.

Playbooks:

- `playbooks/provision.yml` provisions hosts after OpenTofu creates them.
- `playbooks/deploy.yml` deploys PostgreSQL, Redis, Caddy, cloudflared, migrations, and app containers.
