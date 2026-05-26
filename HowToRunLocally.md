# How To Run Locally

Use Docker Compose for normal local development. It runs the app, PostgreSQL, Redis, Redis Insight, and Seq.

## Prerequisites

- Docker Desktop running.
- .NET SDK 10 matching `global.json`.
- Node.js 20 or newer if you rebuild Tailwind CSS.
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
SEQ_UI_HOST_PORT=8081
SEQ_INGESTION_HOST_PORT=5341
REDIS_INSIGHT_HOST_PORT=5540

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=app

Database__Host=postgres
Database__Port=5432
Database__Name=app
Database__Username=postgres
Database__Password=postgres

Redis__Configuration=redis:6379

Authentication__Google__ClientId=
Authentication__Google__ClientSecret=

ACCEPT_EULA=Y
SEQ_FIRSTRUN_ADMINPASSWORD=ChangeMe123!
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

Start without opening the browser:

```powershell
.\RunLocal.ps1 -NoBrowser
```

Manual equivalent:

```powershell
docker compose up -d --build web
```

Open:

- App: `https://localhost:7186`
- Health: `https://localhost:7186/health`
- Seq UI: `http://localhost:8081`
- Redis Insight: `http://localhost:5540`

Docker publishes app, PostgreSQL, Redis, Seq, and Redis Insight ports on `127.0.0.1` only. They are reachable from your machine, not from the LAN.

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
docker compose down --volumes
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
8081 Seq UI
5341 Seq ingestion
5540 Redis Insight
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
dotnet ef migrations add <MigrationName> --project BlazorAutoApp --startup-project BlazorAutoApp --output-dir Data\Migrations
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

Visible E2E is documented in `BlazorAutoApp.Test/TESTING.md`.

Deployment validation without deploying:

```powershell
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
python -m yamllint .github Deployment/LocalCluster
docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:1.7.7
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
docker compose down --volumes
```

If the app exits while applying a fresh initial migration and the logs mention an existing table such as `AspNetRoles`, the local Docker database volume is from an older template version. Reset the local Docker volumes:

```powershell
.\RunLocal.ps1 -ResetDatabase
```
