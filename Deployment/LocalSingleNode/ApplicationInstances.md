# Application instances on one native node

The default `CD - Deploy LocalSingleNode` dispatch selects `primary`. It keeps the tracked application settings, selected frontend, image repository and migration artifact names. Existing clones need no additional configuration. The existing runner registration can deploy both applications from this repository.

An optional `additional` instance uses the other supported frontend and a separate protected GitHub environment. Set the repository variable `LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT` to that environment's name; it must differ from `LOCALSINGLENODE_ENVIRONMENT` (default `localsinglenode`). Configure environment protection and deployment branch restrictions before use. Keep the existing runner label and host selection. Do not install another runner.

Store a `LOCALSINGLENODE_APP_INSTANCE` environment secret containing this JSON schema:

```json
{
  "schema_version": 1,
  "frontend_profile": "React",
  "settings": {
    "app_name": "catalog",
    "app_port": 18080,
    "postgres_port": 15432,
    "redis_port": 16379,
    "deploy_root": "/opt/catalog",
    "docker_subnet": "172.30.20.0/24",
    "lan_http_port": 18081,
    "lan_hostnames": ["catalog.local"],
    "backup_root": "/opt/catalog-backups",
    "backup_keep_days": 7,
    "observability_enabled": false
  },
  "public": {}
}
```

Values above illustrate the schema; they are not installation recommendations. Choose private installation values after native collision, ownership and capacity checks. Settings use the ordinary LocalSingleNode parser. App names, all four service ports, subnets, LAN names and all app/backup roots must be distinct from the primary application. Roots cannot contain one another. Duplicate or unknown JSON keys, unsupported profiles, selected-profile repetition and unsafe values fail before release download or node mutation.

For a public additional app, replace `public: {}` with a JSON object containing `hostname`, `tunnel_id` and integer `origin_port`. Store its matching connector token as `LOCALSINGLENODE_PUBLIC_TUNNEL_TOKEN` in the additional environment. Public inputs come from this explicit instance object instead of inheriting the primary app's hostname, tunnel and origin port. The existing public validator binds the token to the selected tunnel, and native ownership/collision checks still apply. Empty `public` explicitly disables public setup for this instance; an already published instance cannot silently disable its recorded public configuration.

The expected frontend comes from protected configuration, independently of the downloaded manifest. Its acceptance profile and additional release names are derived from trusted code and release settings: `<app_image>-<lowercase-profile>` and `<migration_artifact_name>-<lowercase-profile>`. A successful main release must actually contain that additional artifact; publication is separately enabled through `ADDITIONAL_FRONTEND_PROFILES`. Missing artifacts and image/profile/source/run/digest/hash mismatches fail before migrations or replacement.

The configured app must already have a protected root-owned ownership marker matching this repository and both roots. This dispatch does not provision an application. It preserves trusted-main dispatch and source ancestry, exact-source successful CI, immutable registry digest, shared lock, scoped collision checks, migrations and HTTP/release acceptance. Temporary settings and Ansible variables are created exclusively with mode `0600`, used consistently by Python scripts and privileged collision checks, and removed on success or failure. Never manually copy the primary application's credentials or data into another instance.

For operator commands outside this workflow, an explicit `LOCALSINGLENODE_SETTINGS_FILE` selects a validated settings file; an explicit parser path takes precedence. Leave the variable unset for primary defaults. Store installation files privately, and use only the repository's scoped setup/maintenance procedures.

## Maintain and verify an application

The **LocalSingleNode maintenance** workflow accepts the same `primary` (default) or protected `additional` selection. It requires green main CI for the dispatched code and validates native ownership before backup, maintenance, restart or acceptance. The additional app uses its own protected environment and settings throughout. Doctor and runner residue checks use the existing primary runner registration. Temporary settings are removed on every outcome. Additional-app operations cannot request a shared host reboot.

Setup and maintenance pin the dispatched main checkout and require full Git history. Normally they require its exact successful main-push CI. If the repository's documentation exception skipped CI, the operational gate may traverse first-parent ordinary documentation commits to the nearest green exact-code source. It checks the complete diff, both sides of renames and regular non-executable file modes. Source/configuration changes, disguised Markdown under implementation directories, shallow/missing history, or an actual failed/pending CI run stop the operation. The gate records both dispatched and validated code SHAs. This exception never selects release artifacts: CD still requires the exact target source's successful publishing run, immutable digest, manifest and bundle hashes.

For normal operations, leave `acceptance_only=false` and `backup_now=true`. The workflow creates and reports a fresh protected app backup, verifies an isolated restore, performs existing scoped maintenance and runs doctor plus LAN/public acceptance. Backup recovery uses this app's persisted `/etc/<app_name>/settings.yml` and its documented backup root; see [HowToDeployLocalSingleNode.md](HowToDeployLocalSingleNode.md). Never restore primary credentials or live data into the additional app.

To check persistence, select the intended app, `acceptance_only=true`, `restart_app=true`, and leave `restart_connector=false` and `reboot_check=false`. Under the shared lock, the check requires the verified immutable deployed release, ownership of all three Compose services and a nonempty public catalog. It restarts only `web`, verifies catalog equality and a new process, retains image/container/storage identity, and checks backing services, restart counts and the primary sibling remain unchanged. HTTP acceptance follows. A failed check stops for inspection without an automatic restart retry. Connector recovery remains a separate explicit selection; never combine both restart checks.

## Prepare an additional app on an existing node

After merged tooling and exact-main CI are green, configure the distinct protected environment and `LOCALSINGLENODE_APP_INSTANCE` secret. Dispatch **LocalSingleNode additional app setup** from trusted main and record the run ID before observing it. Reuse the existing native runner. The workflow requires green main CI for the dispatched code, recorded primary ownership and native deployment-user identity. The strict ordinary-documentation exception above applies to setup as well.

Under the existing shared deployment lock, setup repeats ordinary candidate collisions and measures existing workload health, protected backup freshness and capacity. Privileged guards reject foreign containers, networks, persistent volumes, backup units, ownership markers and symlinked roots before any app mutation. They never adopt existing data for a new app. The playbook creates only the additional ownership marker, roots, fresh app secrets, persisted settings, app backup integration and its one LAN HTTP firewall allowance. It requires the existing firewall and deploy backup-group membership; it does not grant privileges or install a runner, host packages, SSH, mDNS, Docker or shared Caddy. Existing shared services are not restarted.

App secrets are generated only when absent and retained on retries. Each app's Compose project creates its own PostgreSQL, Redis and data-protection volumes during the later verified deployment. Setup does not copy primary credentials or data, publish DNS, start the app or dispatch CD. Failed setup retains owned files for inspection and repair; it does not delete data or reclaim locks. Native app settings remain at `/etc/<app_name>/settings.yml` for scoped operator commands. Temporary workflow configuration is removed on every outcome.

For the additional public app, run the existing protected public setup tooling with `configure-public-deployment.py --environment <additional-environment> --instance-config-file <private-instance.json>` plus the normal config/state/token/repository/node arguments. Both options are required together. The helper validates the instance and provider state/token identity, refuses changed public values, writes only environment-scoped public variables and connector credentials, and updates that environment's instance secret with its explicit public metadata. It preserves primary repository variables and secrets. The private instance file must meet the documented current-user ownership and `0700` directory/`0600` file policy. Provider ownership checks and native readiness remain required before public deployment.
