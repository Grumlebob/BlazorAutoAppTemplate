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
