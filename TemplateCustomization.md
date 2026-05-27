# Template Customization

Use this checklist when forking the template.

## App Identity

- Set `App__Name` in `.env`, deployment env files, and production configuration.
- Keep `App:Name` short and stable; it is used for Data Protection isolation and authenticator-app issuer names.

## Local Development

- Keep local ports loopback-bound unless you deliberately need LAN access.
- Change `.env` values instead of editing `docker-compose.yml` for machine-specific local settings.
- `./data/storage:/app/Storage` is local runtime storage for Docker Data Protection fallback keys. Direct local runs use `data/storage/DataProtection-Keys`. Neither path is upload storage.

## Domain And Features

- The current sample domain is Books with `Title`, optional `Author`, and optional `Url`.
- Replace or extend it under `Features/{Feature}` slices.
- Keep shared request/response contracts in `BlazorAutoApp.Core`.
- Keep client routable components under `BlazorAutoApp.Client/Features/{Feature}/Routes`.
- Books create/update/delete are authenticated actions; anonymous users only see the public author bookcase.

## WebAssembly Payload

- The client project uses invariant globalization to avoid shipping ICU data in the WebAssembly payload.
- Remove `InvariantGlobalization` from `BlazorAutoApp.Client/BlazorAutoApp.Client.csproj` if your fork needs culture-specific formatting, parsing, sorting, or localization in the hydrated client.

## Identity

- Account UI and server Identity code live under `BlazorAutoApp/Features/Login/Account`.
- Canonical account routes are `/Account/*`.
- Configure real email delivery before requiring confirmed accounts or relying on password reset email in production.

## Deployment

- Update `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` for `app_name`, `app_image`, `public_hostname`, ports, `deploy_root`, `cloudflare_tunnel_name`, and `migration_bundle_name`.
- Treat `Deployment/LocalCluster/inventory/prod/*` as the active LocalCluster instance configuration in this repository, not generic template defaults. Start new deployments from the documented examples and change values deliberately.
- Update GitHub repository variables if you use a custom LocalCluster runner label or environment name.
- Keep secrets in Ansible Vault or GitHub Secrets, never plaintext tracked files.
