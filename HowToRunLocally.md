# How To Run Locally

Use Docker Compose for the normal local development setup. It runs the app, PostgreSQL, Redis, Redis Insight, and Seq.

## Prerequisites

- Docker Desktop running.
- .NET SDK 9.

## Start

From the repository root:

```powershell
pwsh -File ./docker/create-dev-cert.ps1
docker compose up --build
```

## Local URLs

- App: `https://localhost:7186`
- Seq UI: `http://localhost:8081`
- Redis Insight: `http://localhost:5540`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Local Behavior

Local Docker uses:

- `docker-compose.yml`
- `BlazorAutoApp/appsettings.Docker.json`
- `ASPNETCORE_ENVIRONMENT=Docker`
- `Database__RunMigrationsAtStartup=true`

That means local Docker applies EF migrations on startup. Production does not do this; production migrations are run once through the deployment flow.

## Run Without Docker

Only use this if you already have compatible PostgreSQL and Redis services available:

```powershell
dotnet run --project BlazorAutoApp
```

Useful overrides:

```powershell
$env:ConnectionStrings__DefaultConnection = "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres"
$env:Redis__Configuration = "localhost:6379"
$env:Database__RunMigrationsAtStartup = "true"
```

## Configuration Files

- `BlazorAutoApp/settings.defaults.json` contains required config keys and placeholders.
- `BlazorAutoApp/appsettings.json` contains normal app defaults.
- `BlazorAutoApp/appsettings.Docker.json` contains local Docker settings.
- `docker-compose.yml` wires local services and environment variables.

Environment variables override JSON config with double underscores, for example `Database__Host`.

## Tests

```powershell
dotnet test
```
