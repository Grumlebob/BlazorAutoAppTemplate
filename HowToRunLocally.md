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
App__Url=https://localhost:7186

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

```powershell
docker compose up -d --build web
```

Open:

- App: `https://localhost:7186`
- Health: `https://localhost:7186/health`
- Seq UI: `http://localhost:8081`
- Redis Insight: `http://localhost:5540`

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
pwsh -File ./docker/create-dev-cert.ps1
```

Stop containers while keeping volumes:

```powershell
docker compose down
```

Stop containers and delete local Docker volumes:

```powershell
docker compose down --volumes
```
