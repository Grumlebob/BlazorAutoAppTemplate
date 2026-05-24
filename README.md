# Ship

Ship is a Blazor Web App using Interactive Auto render mode, EF Core with PostgreSQL, Redis-backed caching/Data Protection, Serilog with Seq, Docker Compose for local development, and Ansible for the local Linux Mint production cluster.

## Start Here

- `HowToRunLocally.md` explains local Docker and developer setup.
- `Deployment/LocalCluster/HowToDeployLocalCluster.md` explains the practical deployment steps and where to enter machine-specific values.
- `overview.md` is the deeper architecture walkthrough.

## Tech Stack

- .NET 10 Blazor Web App with `InteractiveAuto`.
- EF Core 10 and Npgsql for PostgreSQL.
- ASP.NET Core Identity on the application `AppDbContext`.
- Redis for HybridCache and production Data Protection keys.
- Serilog console logging and Seq in local Docker.
- GitHub Actions CI, migration bundle build, GHCR image publish, and LAN deployment workflow.

## Repository Layout

- `BlazorAutoApp.Core/Features/*` contains vertical slices with contracts, entities, requests, and responses.
- `BlazorAutoApp` is the server host, EF Core owner, Minimal API owner, and SSR/prerender runtime.
- `BlazorAutoApp.Client` is the WASM client loaded after hydration.
- `BlazorAutoApp.Test` contains xUnit tests and architecture checks.
- `Deployment/LocalCluster` contains Ansible, compose files, deployment scripts, and production inventory for the local Linux Mint cluster.
- `.github/workflows/ci.yml` is the single CI workflow.
- `.github/workflows/deploy-lan.yml` deploys a selected image tag through the self-hosted LAN runner.
- `docker-compose.yml` runs the local app stack.

## Architecture

Core defines shared feature contracts such as `IMoviesApi`. The server implements those contracts with EF Core and exposes Minimal API endpoints. The WASM client implements the same contracts with `HttpClient`.

Pages depend on the Core contracts, so the same UI works during server prerender and after WASM hydration. Pages use `PersistentComponentState` to avoid duplicate fetches when transitioning from SSR to interactive rendering.

Identity endpoints:

- Login: `/Identity/Account/Login`
- Register: `/Identity/Account/Register`
- Public showcase: `/api/identity-showcase/public`
- Authorized showcase: `/api/identity-showcase/secure`

## CI And Deployment

`.github/workflows/ci.yml` runs the deployment audit, restore, build, tests, EF migration bundle build, Docker image build, and GHCR push for non-PR runs.

`.github/workflows/auto-merge-dependabot.yml` only merges Dependabot PRs after `CI` succeeds.

Production uses four Linux Mint nodes by default: `node-main` for Cloudflare Tunnel, Caddy, the self-hosted runner, and deployment/control responsibilities; `node-app1` and `node-app2` for app containers; and `node-db` for PostgreSQL and Redis. `node-main` can optionally become a third app server later, but that is not the recommended first-deployment layout.

## Testing

```powershell
dotnet test
```

Architecture tests enforce that public Core interfaces ending in `Api` have both server and client implementations, and that feature requests have matching tests.
