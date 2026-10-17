# LocalCluster settings

Set target values in [inventory/prod/group_vars/all.yml](inventory/prod/group_vars/all.yml). That file and the validators are source of truth for allowed keys and defaults: [deploy_settings.py](Scripts/Component/lib/deploy_settings.py) and [validate-deploy-settings.sh](Scripts/validate-deploy-settings.sh).

Keep shared image and migration settings in [Deployment/Common/release.yml](../Common/release.yml). Do not add `app_image`, `migration_bundle_name`, `migration_runtime`, or `migration_artifact_name` to all.yml. migration_artifact_name is derived from the bundle name and runtime.

## Settings in all.yml

These are the settings currently used by the target. Keep committed defaults unless the target needs a deliberate change.

| Key | Purpose |
| --- | --- |
| `app_name` | Lowercase app identity. Must be unique on shared nodes. |
| `app_port` | Public app HTTP port on app nodes. Keep unique per app. |
| `postgres_port` | PostgreSQL host port on node-db. Keep unique per app. |
| `redis_port` | Redis host port on node-db. Keep unique per app. |
| `public_hostname` | Hostname in a Cloudflare-managed zone. Keep unique per app. |
| `deploy_root` | App runtime directory under /opt. Keep unique per app. |
| `cloudflare_tunnel_name` | Tunnel used by this app. Apps can share one tunnel. |
| `cloudflared_version` | Pinned Cloudflared release. Keep the same version across apps sharing a host. |
| `accounts_enabled` | Enable application accounts. Defaults to false. |
| `accounts_registration_enabled` | Allow public registration; requires accounts, public origin, SMTP host and sender. Defaults to false. |
| `accounts_admin_seed_enabled` | Create the configured initial Admin account. Defaults to false. |
| `accounts_admin_seed_email` | Email address for the optional initial Admin account. |
| `accounts_public_origin` | Public HTTPS origin used in account email links. |
| `accounts_email_host` | SMTP host for account confirmation and recovery messages. |
| `accounts_email_port` | SMTP port; defaults to 587. |
| `accounts_email_security` | SMTP transport mode: `StartTls` or `SslOnConnect`. |
| `accounts_email_from` | Sender address for account messages. |
| `data_protection_legacy_key_store` | Optional one-time import source: `None`, `Redis`, or `FileSystem`. Defaults to `None`. |
| `data_protection_legacy_redis_key` | Exact old Redis XML repository key; required only when the store is `Redis`. |
| `observability_enabled` | Deploy the LocalCluster telemetry stack when true. |
| `observability_root` | Telemetry runtime directory under /opt. |
| `observability_docker_network` | Docker network shared by this app's telemetry and app containers. |
| `observability_trace_sample_ratio` | Trace sampling ratio from 0 through 1. |
| `observability_grafana_port` | Grafana host port. |
| `observability_alertmanager_port` | Alertmanager host port. |
| `observability_prometheus_port` | Prometheus host port. |
| `observability_loki_port` | Loki host port. |
| `observability_tempo_http_port` | Tempo HTTP port. |
| `observability_tempo_otlp_grpc_port` | Tempo OTLP/gRPC port. |
| `observability_tempo_otlp_http_port` | Tempo OTLP/HTTP port. |
| `observability_alloy_http_port` | Alloy health and metrics port. |
| `observability_node_exporter_port` | Node exporter port. |
| `observability_postgres_exporter_port` | PostgreSQL exporter port. |
| `observability_redis_exporter_port` | Redis exporter port. |
| `observability_prometheus_retention_time` | Prometheus time retention. |
| `observability_prometheus_retention_size` | Prometheus size limit. |
| `observability_loki_retention_period` | Loki retention. |
| `observability_tempo_retention_period` | Tempo retention. |

The source file remains authoritative; review its values for your own host and account. Keep observability paths, network, and published ports unique when apps deploy separate telemetry stacks on the same nodes. Increase retention only after checking disk use.

Account settings are opt-in on both LocalCluster and Cloud. An Admin seed can be enabled without SMTP by setting `accounts_enabled`, `accounts_admin_seed_enabled`, and `accounts_admin_seed_email`; store its password as `vault_accounts_admin_seed_password` in the encrypted LocalCluster vault. Public registration also needs `accounts_public_origin`, `accounts_email_host`, and `accounts_email_from`. Set both `vault_accounts_email_username` and `vault_accounts_email_password` when the SMTP server requires authentication. See [vault.example.yml](inventory/prod/vault.example.yml) for the optional secret names. Keep account credentials out of all.yml.

For a one-time legacy Data Protection import, set `data_protection_legacy_key_store` to `Redis` and provide the exact `data_protection_legacy_redis_key`, or set it to `FileSystem`. For FileSystem, copy the old XML key files to `/etc/<app_name>/data-protection/legacy` on both app nodes, owned by `root:deploy` with mode `0440`; the directory must be `root:deploy` mode `0750`. The app mounts this directory read-only at `/run/legacy-data-protection`. Dispatch the first account/key-store transition with `run_migrations=true`: this stops both app replicas before schema changes and keeps old-store and PostgreSQL-store versions from serving together. Wait for both app nodes to become healthy so each imports and validates the same source. Then set the store back to `None`, clear the Redis key, and deploy again. Keep the source until the PostgreSQL key ring and existing authentication cookies have been verified. Do not remove or rotate the app Data Protection certificate during this process.

The optional `inventory_dns_suffix` setting enables a preflight check that each generated inventory address matches the corresponding node name published by local DNS. Set it only when the router publishes matching node DNS names. Regenerate `hosts.yml` from `machines.yml` after an address change. Do not add undocumented keys; the validator rejects unknown settings.

The database Compose file pins PostgreSQL and Redis to exact versioned image tags. Upgrade those tags deliberately in [compose/node-db/docker-compose.yml](compose/node-db/docker-compose.yml), after reviewing upstream release notes.

## Shared-host choices

If this is the only app on these four nodes, keep the default ports and continue.

For a second app on prepared nodes, use [ForkExistingCluster.md](ForkExistingCluster.md). Choose a unique app identity, hostname, runtime root, app/database/Redis ports, release image and migration bundle. Keep the same machine IPs. Reuse the existing Cloudflare tunnel name and token only when the apps intentionally share a tunnel in the same Cloudflare account. Keep Cloudflared version consistent across apps on shared nodes.

If the second app enables observability, use unique telemetry runtime paths, Docker network, and host ports. Otherwise set observability_enabled to false deliberately. Do not bootstrap or prepare already-prepared nodes again.

## GitHub variables and secrets

Set repository variables in:

Repository -> Settings -> Secrets and variables -> Actions -> Variables

For a new fork without an inherited runner, install and verify the runner before the first PR. Then set CI_RUNNER_LABEL and LOCALCLUSTER_RUNNER_LABEL to the configured runner label, and CI_RUNNER_HOST to node-main. These values let CI select the runner before checkout. Setup order is in [Setup.md](Setup.md#10-install-the-github-actions-runner).

Set LOCALCLUSTER_ENVIRONMENT only when using a separate deployment environment name. The default environment is localcluster and must allow deployments from main.

Store the Ansible Vault encryption password as the repository secret ANSIBLE_VAULT_PASSWORD. This secret is the Ansible Vault password. setup-secrets.sh sets it when GitHub CLI is authenticated. If setting it manually, use this secret name:

Name: ANSIBLE_VAULT_PASSWORD

Add it under Repository -> Settings -> Secrets and variables -> Actions -> Secrets.

Do not put plaintext secrets in all.yml. Keep the encrypted vault in inventory/prod/vault.yml. See [the shared release contract](../Common/ReleaseContract.md) for registry credentials and image provenance.

## Validate and commit target files

Run both validators from the repository root:

```bash
bash ./Deployment/Common/Scripts/validate-common-release.sh
bash ./Deployment/LocalCluster/Scripts/validate-deploy-settings.sh
```

Generated hosts.yml must contain reserved node IPs before the first deployment. Keep machines.yml and bootstrap-hosts.yml local and ignored. The workflow needs committed `all.yml` settings and committed `hosts.yml` inventory.

Check all deployment files that GitHub Actions will read:

```bash
git status --short Deployment/LocalCluster/inventory/prod/group_vars/all.yml Deployment/LocalCluster/inventory/prod/hosts.yml Deployment/LocalCluster/inventory/prod/vault.yml
```

Commit intended configuration explicitly, including settings and generated production inventory:

```bash
git add Deployment/LocalCluster/inventory/prod/group_vars/all.yml
git add Deployment/Common/release.yml
git add Deployment/LocalCluster/inventory/prod/hosts.yml
```
