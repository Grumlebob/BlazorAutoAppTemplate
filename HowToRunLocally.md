# How To Run Locally

Use Docker Compose for normal local development. It runs the app, PostgreSQL, Redis, Redis Insight, and Seq.

## Local Principle

Write local settings once in:

```text
.env
```

Do not edit `docker-compose.yml` for normal local values. `docker-compose.yml` reads `.env` and wires those values into every local container.

## Files You Will Edit

- `.env`: your local Docker environment values. This file is ignored by git.

## Useful Files

- `.env.example`: committed template for `.env`.
- `docker-compose.yml`: local Docker stack.
- `docker/setup-local.ps1`: creates `.env` if missing, exports the HTTPS dev certificate, and checks local readiness.
- `docker/local-status.py`: validates local setup.
- `docker/create-dev-cert.ps1`: exports the ASP.NET Core HTTPS dev certificate to `docker/https/aspnetapp.pfx`.
- `BlazorAutoApp/appsettings.Docker.json`: app settings used when `ASPNETCORE_ENVIRONMENT=Docker`.
- `BlazorAutoApp/settings.defaults.json`: required configuration keys and placeholder defaults.

## Prerequisites

- Docker Desktop running.
- .NET SDK 10.
- Node.js 20 or newer if you rebuild Tailwind CSS locally.
- Python available as `python`.
- PowerShell available as `pwsh` or Windows PowerShell.

## First Setup

From the repository root:

```powershell
pwsh -File ./docker/setup-local.ps1
```

This creates `.env` from `.env.example` if it does not exist, exports the HTTPS dev certificate, and runs the local status check.

If you prefer manual setup:

```powershell
Copy-Item .env.example .env
pwsh -File ./docker/create-dev-cert.ps1
python ./docker/local-status.py
```

## What To Put In `.env`

The defaults in `.env.example` are enough for normal local development.

Important values:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=app

Database__Host=postgres
Database__Port=5432
Database__Name=app
Database__Username=postgres
Database__Password=postgres

Redis__Configuration=redis:6379

ACCEPT_EULA=Y
SEQ_FIRSTRUN_ADMINPASSWORD=ChangeMe123!
```

Optional values can stay blank unless you are testing those integrations:

```env
Authentication__Google__ClientId=
Authentication__Google__ClientSecret=
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=
SENDGRID_FROM_ALIAS=Ship Local
```

## Check Local Readiness

Run this before starting the stack if something feels off:

```powershell
python ./docker/local-status.py
```

It checks:

- `.env` exists.
- Required `.env` keys are present.
- Placeholder values are not still present.
- HTTPS dev certificate exists.
- Docker Compose config parses.
- `docker` and `dotnet` are available.

## Start

From the repository root:

```powershell
docker compose up --build
```

## Local URLs

- App: `https://localhost:7186`
- Seq UI: `http://localhost:8081`
- Redis Insight: `http://localhost:5540`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Redis Insight connection:

```text
redis://redis:6379
```

## Local Behavior

Local Docker uses:

- `.env`
- `docker-compose.yml`
- `BlazorAutoApp/appsettings.Docker.json`
- `ASPNETCORE_ENVIRONMENT=Docker`
- `Database__RunMigrationsAtStartup=true`

Local Docker applies EF migrations on startup. Production does not do this; production migrations are run once through the deployment flow.

Local app storage is persisted here:

```text
data/storage
```

Docker volumes persist:

```text
pgdata
seqdata
redisinsight
```

## Stop

Stop containers but keep local data:

```powershell
docker compose down
```

Stop containers and delete Docker volumes:

```powershell
docker compose down --volumes
```

Delete local application storage:

```powershell
Remove-Item -Recurse -Force ./data/storage -ErrorAction SilentlyContinue
```

## Run Without Docker

Only use this if you already have compatible PostgreSQL and Redis services available outside Docker.

Set environment variables in PowerShell:

```powershell
$env:ConnectionStrings__DefaultConnection = "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres"
$env:Redis__Configuration = "localhost:6379"
$env:Database__RunMigrationsAtStartup = "true"
dotnet run --project BlazorAutoApp
```

## Tests

Docker must be running because integration tests use Testcontainers.

```powershell
dotnet test
```

## Troubleshooting

Check local setup:

```powershell
python ./docker/local-status.py
```

Check container status:

```powershell
docker compose ps
```

Check app logs:

```powershell
docker compose logs web --tail=100
```

Check database logs:

```powershell
docker compose logs postgres --tail=100
```

Recreate the HTTPS certificate:

```powershell
pwsh -File ./docker/create-dev-cert.ps1
```

If ports conflict, stop the conflicting local service or change the host port mapping in `docker-compose.yml`.
