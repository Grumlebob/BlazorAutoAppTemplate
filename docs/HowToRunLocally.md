# Run locally

Use the repository wrapper for the normal local setup. It prepares Docker, local configuration, and the HTTPS certificate, then starts the profile selected by `frontend-profile.txt`.

## Prerequisites

- Docker Desktop running for the normal stack and integration tests.
- .NET SDK selected by `global.json` for direct runs and migrations.
- PowerShell and Python 3 for the setup/status scripts.
- Node/npm only when changing React or rebuilding Tailwind; use each package's manifest and lockfile.

## First setup and run

From the repository root, create local configuration and a development certificate:

```powershell
pwsh -File ./docker/setup-local.ps1
```

Then start the app:

```powershell
.\Scripts\RunLocal.ps1
```

Use `-NoBrowser` to keep the browser closed, `-Observability` to start the optional local telemetry stack, and `-StopStack` to stop containers while retaining their volumes. Local Docker values belong in `.env`; use [`.env.example`](../.env.example) as the authority and do not commit `.env`. It contains the default host ports and service settings.

The app is normally at `https://localhost:7186`. Docker exposes ports on loopback only. Postgres uses host port `5432`, Redis `6379`, and Redis Insight `5540` by default. Change a busy host port in `.env`, then rerun the wrapper. Keep container-to-container ports (Postgres `5432` and Redis `6379`) unchanged. The optional observability URLs and ports are defined in `.env.example`; usage is in [Observability](ObservabilityGuide.md).

Development can seed a local User account. Values are in [appsettings.Development.json](../GrumPlates/appsettings.Development.json); use them only for local development. Startup migrations run in the Docker profile.

## Reset local data

```powershell
.\Scripts\RunLocal.ps1 -ResetDatabase -NoBrowser
```

Reset removes this Compose project's named volumes before rebuilding. This deletes the local PostgreSQL database and stored state for Redis Insight and optional observability services. It cannot be undone. Use it only when you intend to recreate local service data, such as after an incompatible database image upgrade. Ordinary start and stop keep the volumes. Do not delete another clone's data.

## Run without Docker

Use this only when compatible local PostgreSQL and Redis services already run:

```powershell
$env:ConnectionStrings__DefaultConnection = "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres"
$env:Redis__Configuration = "localhost:6379"
$env:Database__RunMigrationsAtStartup = "true"
dotnet run --project .\GrumPlates\GrumPlates.csproj -- --urls https://localhost:7186
```

If the HTTPS port is busy, choose another URL with `--urls` and set `E2E_BASE_URL` to the same URL for browser tests. React's Vite proxy and API setup are described in [Frontend/React](Frontend/React.md).

## Tailwind

Use the client lockfile for repeatable installs:

```powershell
Set-Location .\GrumPlates.Client
npm ci
npm run css:build
```

During active CSS work, use `npm run css:watch`. Generated output is `GrumPlates/wwwroot/tailwind.css`; commit it when Razor classes or `GrumPlates.Client/Styles` change.

## Migrations

Create and apply a local schema migration with:

```powershell
dotnet tool restore
dotnet ef migrations add <MigrationName> --project GrumPlates --startup-project GrumPlates --output-dir Infrastructure\Persistence\Migrations
dotnet ef database update --project GrumPlates --startup-project GrumPlates
```

Production uses the release workflow's verified migration bundle; follow the relevant [deployment guide](../Deployment/README.md). Do not import another system's data from application startup.

## Tests

Integration tests need Docker. See [Test](Test.md) for the normal run and full local gate; browser tests have a separate [opt-in guide](Testing/Browser.md).
