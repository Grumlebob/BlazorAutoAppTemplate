# BlazorAutoApp

BlazorAutoApp is a .NET 10 Blazor Web App template using Interactive Auto render mode. The first screen is the Books feature, with server prerendering, WebAssembly hydration, PostgreSQL persistence, Redis-backed caching/Data Protection, ASP.NET Core Identity, OpenTelemetry-ready logging, Docker Compose, and visible Playwright E2E tests.

## Start Here

- `docs/HowToRunLocally.md` explains Docker, direct `dotnet run`, local URLs, and port conflicts.
- `Deployment/LocalCluster/HowToDeployLocalCluster.md` explains the existing LocalCluster deployment flow.
- `docs/HowToAddANewFeature.md` explains how to add a coherent vertical feature slice.
- `docs/Test.md` explains unit, integration, architecture, E2E, and Lighthouse testing.
- `docs/SimulationGuide.md` explains safe synthetic traffic for local and deployed observability demos.
- `docs/HowToForkThisRepo.md` explains how to customize a fork and deploy it quickly on the existing LocalCluster.
- `docs/MigrateProjectPlanningPrompt.md` is a copy-paste prompt for planning an incremental migration from an old Blazor Server app into a fork.

## Tech Stack

- .NET 10 Blazor Web App with `InteractiveAuto`.
- EF Core 10 and Npgsql for PostgreSQL.
- ASP.NET Core Identity with component account pages and .NET 10 passkeys schema support.
- Redis for HybridCache and Data Protection keys.
- Built-in ASP.NET Core rate limiting for API and account endpoints.
- Tailwind CSS generated from `BlazorAutoApp.Client/Styles/input.css`.
- Serilog console logging with OpenTelemetry trace/span correlation.
- GitHub Actions CI on the `node-main-books` self-hosted runner for deployment audit, restore, build, tests, EF migration bundle artifact publishing, Docker image build, and GHCR push on `main`.
- Centralized NuGet package versions in `Directory.Packages.props`.

## Observability

Local Docker can run the Grafana observability stack with `.\Scripts\RunLocal.ps1 -Observability`. LocalCluster deploys the stack on `node-main`, and Cloud deploys the stack on `cloud-main`; both targets use per-node collectors. `docs/ObservabilityGuide.md` is the operator guide and architecture reference:

- OpenTelemetry instruments the .NET app and correlates logs, metrics, and traces.
- Grafana is the dashboard and operator UI.
- Prometheus stores metrics and runs alert rules.
- Alertmanager receives Prometheus alerts for routing and silencing.
- Loki is centralized log aggregation.
- Tempo stores distributed traces from OpenTelemetry.
- Grafana Alloy is the per-node collector for logs, metrics, and OTLP telemetry.
- Exporters expose host, PostgreSQL, and Redis metrics; Alloy collects app container logs and app OTLP metrics/traces.

The LocalCluster and Cloud observability deployments use existing nodes; no extra observability node is part of the plan.

## Traffic Simulation

Use `Scripts/RunSimulation.ps1` to generate safe traffic for dashboard demos and smoke checks:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke
.\Scripts\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
.\Scripts\RunSimulation.ps1 -Target local -AuthCheck
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
```

Use `Scripts/RunSimulationMatrix.ps1` for a strict local/LocalCluster/Cloud evidence pass, and `Scripts/AnalyzeSimulationReports.ps1` to summarize generated reports. The simulator is a .NET console operator tool in `BlazorAutoApp.Simulation`. It is built and tested by CI, but it is not deployed with the app. It paces API and authenticated write traffic below the app's rate limits, reports unexpected `429` responses separately, cleans up V2 synthetic books, and writes run summaries under `artifacts/simulation`. See `docs/SimulationGuide.md`.

## Repository Layout

- `BlazorAutoApp.Core/Features/*` contains shared feature contracts, domain types, and request/response DTOs.
- `BlazorAutoApp/Features/*` contains server-side feature implementations and endpoint mapping.
- `BlazorAutoApp/Infrastructure/*` contains server host/platform concerns such as persistence, caching, Data Protection, rate limiting, forwarded headers, and health checks.
- `BlazorAutoApp.Client/Features/*` contains client UI slices and WASM service implementations.
- `BlazorAutoApp.Client/Features/AppShell` contains layout, reconnect UI, not-found UI, and template render-mode diagnostics.
- `BlazorAutoApp/Features/Login/Account` contains Identity account components and account endpoint helpers.
- `BlazorAutoApp.Test` contains xUnit integration, architecture, rate-limiting, and Playwright E2E tests.
- `BlazorAutoApp.Simulation` contains the synthetic traffic simulator.
- `Deployment/LocalCluster` contains the Ansible, compose, inventory, and helper scripts for the existing LocalCluster deployment.
- `docker-compose.yml` runs the local app stack.
- `docs/plans` contains historical planning notes that are not required for normal template use.

## LocalCluster Deployment

The LocalCluster deployment flow is intentionally kept in this repository. It uses:

- `.github/workflows/ci.yml` to run deployment checks on `node-main-books`, build the migration bundle, build the Docker image, push the image to GHCR on `main`, and prune old migration artifacts.
- `.github/workflows/cd-localcluster.yml` to deploy from the app-specific self-hosted LocalCluster runner.
- `Deployment/LocalCluster/Scripts/audit-deployment.sh` and `validate-rendered-templates.sh` as deployment safety checks.
- `Deployment/LocalCluster/HowToDeployLocalCluster.md` as the operating guide.

## URLs

When running the Docker stack:

- App: `https://localhost:7186`
- Health: `https://localhost:7186/health`
- Redis Insight: `http://localhost:5540`
- Grafana, with `.\Scripts\RunLocal.ps1 -Observability`: `http://localhost:3000`

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
.\Scripts\RunLocal.ps1
```

Run the local Grafana/Prometheus/Loki/Tempo/Alloy observability stack:

```powershell
.\Scripts\RunLocal.ps1 -Observability
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

For dashboard access, common checks, and troubleshooting queries, see `docs/ObservabilityGuide.md`.

Generate local demo traffic for Grafana:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
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
