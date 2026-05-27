# BlazorAutoApp

BlazorAutoApp is a .NET 10 Blazor Web App template using Interactive Auto render mode. The first screen is the Books feature, with server prerendering, WebAssembly hydration, PostgreSQL persistence, Redis-backed caching/Data Protection, ASP.NET Core Identity, Seq logging, Docker Compose, and visible Playwright E2E tests.

## Start Here

- `HowToRunLocally.md` explains Docker, direct `dotnet run`, local URLs, and port conflicts.
- `Deployment/LocalCluster/HowToDeployLocalCluster.md` explains the existing LocalCluster deployment flow.
- `overview.md` explains the render-mode and vertical-slice architecture.
- `TESTING.md` links to the full unit/integration and headed Playwright E2E guide.
- `TemplateCustomization.md` lists the first things to rename or configure in a fork.

## Tech Stack

- .NET 10 Blazor Web App with `InteractiveAuto`.
- EF Core 10 and Npgsql for PostgreSQL.
- ASP.NET Core Identity with component account pages and .NET 10 passkeys schema support.
- Redis for HybridCache and Data Protection keys.
- Built-in ASP.NET Core rate limiting for API and account endpoints.
- Tailwind CSS generated from `BlazorAutoApp.Client/Styles/input.css`.
- Serilog console logging and Seq in local Docker.
- GitHub Actions CI for deployment audit, restore, build, tests, EF migration bundle artifact publishing, Docker image build, and GHCR push on `main`.
- Centralized NuGet package versions in `Directory.Packages.props`.

## Repository Layout

- `BlazorAutoApp.Core/Features/*` contains shared feature contracts, domain types, and request/response DTOs.
- `BlazorAutoApp/Features/*` contains server-side feature implementations and endpoint mapping.
- `BlazorAutoApp/Infrastructure/*` contains server host/platform concerns such as persistence, caching, Data Protection, rate limiting, forwarded headers, and health checks.
- `BlazorAutoApp.Client/Features/*` contains client UI slices and WASM service implementations.
- `BlazorAutoApp.Client/Features/AppShell` contains layout, reconnect UI, not-found UI, and template render-mode diagnostics.
- `BlazorAutoApp/Features/Login/Account` contains Identity account components and account endpoint helpers.
- `BlazorAutoApp.Test` contains xUnit integration, architecture, rate-limiting, and Playwright E2E tests.
- `Deployment/LocalCluster` contains the Ansible, compose, inventory, and helper scripts for the existing LocalCluster deployment.
- `docker-compose.yml` runs the local app stack.
- `docs/plans` contains historical planning notes that are not required for normal template use.

## LocalCluster Deployment

The LocalCluster deployment flow is intentionally kept in this repository. It uses:

- `.github/workflows/ci.yml` to run deployment checks, build the migration bundle, build the Docker image, and push the image to GHCR on `main`.
- `.github/workflows/cd-localcluster.yml` to deploy from the self-hosted LocalCluster runner.
- `Deployment/LocalCluster/Scripts/audit-deployment.sh` and `validate-rendered-templates.sh` as deployment safety checks.
- `Deployment/LocalCluster/HowToDeployLocalCluster.md` as the operating guide.

## URLs

When running the Docker stack:

- App: `https://localhost:7186`
- Health: `https://localhost:7186/health`
- Seq UI: `http://localhost:8081`
- Redis Insight: `http://localhost:5540`

Local Docker publishes these ports on `127.0.0.1` only.

If a default port is already in use, change the matching `*_HOST_PORT` value in `.env`; for example `POSTGRES_HOST_PORT=5433` or `APP_HTTPS_HOST_PORT=7286`.

Canonical account routes:

- Login: `/Account/Login`
- Register: `/Account/Register`
- Manage profile: `/Account/Manage`

## Common Commands

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
dotnet package list --project .\BlazorAutoApp.sln --outdated
dotnet package list --project .\BlazorAutoApp.sln --deprecated
dotnet package list --project .\BlazorAutoApp.sln --vulnerable --include-transitive
```

Run the app stack:

```powershell
.\RunLocal.ps1
```

Build Tailwind output:

```powershell
cd BlazorAutoApp.Client
npm install
npm audit
npm run css:build
```

Run visible E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
```

## Current Behavior

The Books page is the home page and shows render-mode diagnostics so template users can see the transition from prerendered server output to an interactive renderer. Books have a title, optional author, and optional URL. Anonymous users see the public SVG author bookcase; logged-in users also see `Add Book` and their own editable SVG bookcase. View, edit, add, and delete all happen through the book modal flow. Books data access is abstracted behind the shared `IBooksApi` contract: the server uses EF Core during prerender, and the hydrated WASM client calls `/api/books`.

Local development seeds fixed template books (`Ship`, `TraceBack`, `ImprovedDb`, `KinoJoin`) plus common classics after startup migrations when `Books:SeedLocalDefaults=true`. The seed is disabled in base configuration and enabled for Development/Docker local runs.

Redis is required outside development/test environments. It backs distributed `HybridCache`, Data Protection keys, and cross-node book cache invalidation. The default invalidation strategy uses Redis pub/sub with short local-cache TTLs; if strict freshness matters more than in-process cache speed, set `Cache__Books__DisableLocalCache=true` on every app node. Durable invalidation, such as Redis Streams or a database outbox, should be added by apps that need guaranteed delivery.

Rate limiting is enabled by default:

- Global app limit: `600` requests per minute per user/IP.
- Books API limit: `60` requests per minute per user/IP.
- Account POST endpoint limit: `120` requests per five minutes per user/IP.

Override these values under the `RateLimiting` configuration section when building a real product from the template.

Forwarded headers are trusted only from configured proxies or networks. LocalCluster injects the Caddy node IP into the app-server environment; direct public clients cannot choose their own `X-Forwarded-For` value by default.
