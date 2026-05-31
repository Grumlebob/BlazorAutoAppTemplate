# How To Run Locally

Use Docker Compose for normal local development. It runs the app, PostgreSQL, Redis, and Redis Insight. The optional observability profile adds Grafana, Prometheus, Alertmanager, Loki, Tempo, and Alloy.

## Prerequisites

- Docker Desktop running.
- .NET SDK 10 matching `global.json`.
- Node.js 20 or newer if you rebuild Tailwind CSS. Node.js 24 LTS is recommended because CI uses it.
- PowerShell.
- Python available as `python` for the local status helper.

## First Setup

From the repository root:

```powershell
pwsh -File ./docker/setup-local.ps1
```

This creates `.env` from `.env.example` if needed, exports the HTTPS dev certificate to `docker/https/aspnetapp.pfx`, and validates the local setup.

Manual equivalent:

```powershell
Copy-Item .env.example .env
pwsh -File ./docker/create-dev-cert.ps1
python ./docker/local-status.py
```

## Local Configuration

Local Docker values live in `.env`. Do not edit `docker-compose.yml` for normal machine-specific values.

The defaults in `.env.example` are enough for local development:

```env
App__Name=BlazorAutoApp
App__Url=https://localhost:7186

APP_HTTPS_HOST_PORT=7186
POSTGRES_HOST_PORT=5432
REDIS_HOST_PORT=6379
REDIS_INSIGHT_HOST_PORT=5540
GRAFANA_HOST_PORT=3000
ALERTMANAGER_HOST_PORT=9093
PROMETHEUS_HOST_PORT=9090
LOKI_HOST_PORT=3100
TEMPO_HOST_PORT=3200
ALLOY_HOST_PORT=12345

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=app

Database__Host=postgres
Database__Port=5432
Database__Name=app
Database__Username=postgres
Database__Password=postgres

Redis__Configuration=redis:6379

Observability__OpenTelemetry__Enabled=false
Observability__OpenTelemetry__Endpoint=http://alloy:4317
Observability__OpenTelemetry__Protocol=Grpc
Observability__OpenTelemetry__TraceSampleRatio=0.1
OBSERVABILITY_ENABLED=false
OBSERVABILITY_OTLP_ENDPOINT=http://alloy:4317
OBSERVABILITY_OTLP_PROTOCOL=Grpc
OBSERVABILITY_TRACE_SAMPLE_RATIO=1.0
OBSERVABILITY_DEPLOYMENT_TARGET=local

Authentication__Google__ClientId=
Authentication__Google__ClientSecret=

```

## Start The Stack

In Rider, use the shared run configuration:

```text
Local Docker Stack
```

It runs `RunLocal.ps1`, prepares `.env` and the HTTPS certificate, starts Docker Compose, waits for `/health/ready`, and opens the app.
The runner waits for Docker Desktop to be ready before it starts the stack.

From a terminal, the same one-click path is:

```powershell
.\RunLocal.ps1
```

Reset the local Docker database and service volumes before starting:

```powershell
.\RunLocal.ps1 -ResetDatabase
```

Use that reset path after major local PostgreSQL or Redis image upgrades. PostgreSQL 18 uses a version-specific data directory under the Docker volume, so stale PostgreSQL 16 volumes should be discarded instead of reused.

Start without opening the browser:

```powershell
.\RunLocal.ps1 -NoBrowser
```

Start the optional local Grafana observability stack:

```powershell
.\RunLocal.ps1 -Observability
pwsh -File .\docker\observability\smoke-local-observability.ps1
```

This starts Grafana, Prometheus, Alertmanager, Loki, Tempo, and Alloy with short local retention and explicit memory/CPU limits. It also enables app OTLP export for that Compose run. Without `-Observability`, OpenTelemetry stays disabled and the normal local stack is unchanged.

For dashboard usage, common queries, and troubleshooting, see `ObservabilityGuide.md`.

Generate safe synthetic traffic for dashboards:

```powershell
.\RunSimulation.ps1 -Target local -Profile smoke
.\RunSimulation.ps1 -Target local -Profile demo -Duration 10m -MaxRps 3
.\RunSimulation.ps1 -Target local -AuthCheck
.\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
```

Run a strict evidence matrix and summarize reports:

```powershell
.\RunSimulationMatrix.ps1 -All
.\AnalyzeSimulationReports.ps1 -Latest 15
```

Read-only simulation is the default. Authenticated writes require `-AllowWrite`, use real login cookies, and clean up V2 synthetic books by default. The simulator is the `BlazorAutoApp.Simulation` operator tool; it is built and tested by CI, but it is not deployed with the app. It paces `/api/*` and authenticated write requests below the app's rate limits, so normal smoke and demo runs should report `unexpected 429: 0`. Reports are written under `artifacts/simulation`.

Manual equivalent:

```powershell
docker compose up -d --build web
```

Open:

- App: `https://localhost:7186`
- Health: `https://localhost:7186/health`
- Redis Insight: `http://localhost:5540`
- Grafana, only with `-Observability`: `http://localhost:3000`
- Alertmanager, only with `-Observability`: `http://localhost:9093`
- Prometheus, only with `-Observability`: `http://localhost:9090`
- Loki, only with `-Observability`: `http://localhost:3100`
- Tempo, only with `-Observability`: `http://localhost:3200`

Docker publishes app, PostgreSQL, Redis, Redis Insight, and optional observability ports on `127.0.0.1` only. They are reachable from your machine, not from the LAN.

Local login seeds:

- Email: `admin@admin.com`
- Password: `Admin123`
- Role: `Admin`
- Email: `user@user.com`
- Password: `User123`
- Role: `User`

These accounts are created only in `Development` and `Docker` environments after EF migrations run. The seed writes the local password hashes directly so these short local-only passwords work without weakening the normal Identity password rules for registration and password reset flows.

If one of the default host ports is busy, change the matching `*_HOST_PORT` value in `.env` and rerun `docker compose up -d --build`. Container-to-container settings such as `Database__Port=5432` and `Redis__Configuration=redis:6379` should stay on the container ports unless you also change the containers.

Redis Insight can connect to:

```text
redis://redis:6379
```

## Local Behavior

Docker uses:

- `.env`
- `docker-compose.yml`
- `BlazorAutoApp/appsettings.Docker.json`
- `ASPNETCORE_ENVIRONMENT=Docker`
- `Database__RunMigrationsAtStartup=true`

The `./data/storage:/app/Storage` mount is local runtime storage for fallback Data Protection keys inside Docker. Direct local runs use `data/storage/DataProtection-Keys`. Neither path is upload or media storage.

The Docker profile applies EF migrations on startup. If you reset the local database, recreate the stack with volumes removed:

```powershell
docker compose down --volumes --remove-orphans
docker compose up -d --build web
```

## Run Without Docker

Use this only when compatible PostgreSQL and Redis services already exist outside Docker.

```powershell
$env:ConnectionStrings__DefaultConnection = "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres"
$env:Redis__Configuration = "localhost:6379"
$env:Database__RunMigrationsAtStartup = "true"
dotnet run --project BlazorAutoApp
```

If port `7186` is already in use, stop the old process/container or run on another HTTPS URL:

```powershell
dotnet run --project BlazorAutoApp --urls "https://localhost:7286"
```

When changing the app URL for E2E, set `E2E_BASE_URL` to the same URL.

Local port checklist:

```text
7186 app HTTPS
5025 optional app HTTP
5432 PostgreSQL
6379 Redis
5540 Redis Insight
3000 Grafana, optional observability profile
9093 Alertmanager, optional observability profile
9090 Prometheus, optional observability profile
3100 Loki, optional observability profile
3200 Tempo, optional observability profile
12345 Alloy UI/API, optional observability profile
```

For Docker host-port conflicts, prefer changing `.env` values such as `POSTGRES_HOST_PORT=5433` or `APP_HTTPS_HOST_PORT=7286` instead of editing `docker-compose.yml`.

## Tailwind

```powershell
cd BlazorAutoApp.Client
npm install
npm run css:build
```

For active CSS work:

```powershell
npm run css:watch
```

Generated output is committed at `BlazorAutoApp/wwwroot/tailwind.css`.

## Migrations

Add a migration:

```powershell
dotnet ef migrations add <MigrationName> --project BlazorAutoApp --startup-project BlazorAutoApp --output-dir Infrastructure\Persistence\Migrations
```

Apply migrations:

```powershell
dotnet ef database update --project BlazorAutoApp --startup-project BlazorAutoApp
```

Build a migration bundle:

```powershell
dotnet ef migrations bundle --project BlazorAutoApp\BlazorAutoApp.csproj --startup-project BlazorAutoApp\BlazorAutoApp.csproj --configuration Release --self-contained --runtime linux-x64 --output artifacts\migrations\verify-migrate
```

The existing LocalCluster deployment flow builds its own named migration bundle and GHCR image from `.github/workflows/ci.yml`, then deploys them through `.github/workflows/cd-localcluster.yml`. See `Deployment/LocalCluster/HowToDeployLocalCluster.md`.

## Tests

Docker must be running because integration tests use Testcontainers.

```powershell
dotnet test
```

Visible E2E is documented in `Test.md`.

Deployment validation without deploying:

```powershell
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
python -m yamllint .github Deployment/LocalCluster
docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:1.7.12
docker run --rm -v "${PWD}:/mnt" -w /mnt koalaman/shellcheck-alpine:stable sh -c "find Deployment/LocalCluster/Scripts -type f -name '*.sh' -print0 | xargs -0 shellcheck --severity=warning"
```

## Troubleshooting

Check local setup:

```powershell
python ./docker/local-status.py
```

Check container status and logs:

```powershell
docker compose ps
docker compose logs web --tail=100
docker compose logs postgres --tail=100
```

Recreate the HTTPS certificate:

```powershell
pwsh -File ./docker/create-dev-cert.ps1 -Force
```

Stop containers while keeping volumes:

```powershell
docker compose down
```

Stop containers and delete local Docker volumes:

```powershell
docker compose down --volumes --remove-orphans
```

If the app exits while applying a fresh initial migration and the logs mention an existing table such as `AspNetRoles`, the local Docker database volume is from an older template version. Reset the local Docker volumes:

```powershell
.\RunLocal.ps1 -ResetDatabase
```
