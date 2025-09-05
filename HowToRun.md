How To Run
==========

This repo uses Docker Compose to orchestrate the app, PostgreSQL, and Seq for logs.

Docker Compose
--------------
Prereqs
- Docker Desktop running
- .NET SDK (to export HTTPS dev cert)

Steps
1) Export HTTPS dev cert: `pwsh -File ./docker/create-dev-cert.ps1`
2) Launch: `docker compose up --build`

URLs
- App (HTTP): http://localhost:8080
- App (HTTPS): https://localhost:8443
- Seq UI: http://localhost:8081
- Seq ingestion: http://localhost:5341
- Postgres: localhost:5432 (db=app, user=postgres, pwd=postgres)

Notes
- App reads `appsettings.Docker.json` in `ASPNETCORE_ENVIRONMENT=Docker` (set by compose).
- Serilog sinks: Console + Seq (to `http://seq:5341` inside the compose network).

Troubleshooting
---------------
- If Docker build failed with a test project path error, ensure the app Dockerfile restores/builds only `BlazorAutoApp.csproj` (already set up).
- If HTTPS fails in containers, re-export the dev cert with `docker/create-dev-cert.ps1` and keep the volume mount (`./docker/https:/https:ro`).
 - If Seq shows no events:
   - Verify the app container logs show Serilog writing to Seq.
   - Confirm `appsettings.Docker.json` includes the Seq sink with `serverUrl: http://seq:5341`.
   - Ensure the `seq` service is healthy in `docker compose ps` and reachable from the app container.
