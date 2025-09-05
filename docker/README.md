Docker Local Development
========================

This setup runs the app and PostgreSQL via docker-compose with HTTPS support.

Prerequisites
-------------
- Docker Desktop running
- .NET SDK installed (for exporting the dev certificate)

Steps
-----
1) Export a dev HTTPS certificate into the mounted folder:
   - PowerShell: `pwsh -File ./docker/create-dev-cert.ps1`

2) Start the stack:
   - `docker compose up --build`

3) App URLs:
   - HTTP:  http://localhost:8080
   - HTTPS: https://localhost:8443 (uses the exported dev cert)
- Seq
   - UI: http://localhost:8081 (view logs)

Notes
-----
- Connection string inside containers uses service name `postgres` and matches `appsettings.Docker.json`.
- Kestrel endpoints are configured via `BlazorAutoApp/appsettings.Docker.json`.
- If you prefer to avoid HTTPS in containers, remove the volume mount and the 8443 port mapping, and override `ASPNETCORE_ENVIRONMENT` to `Development`. The app keeps `UseHttpsRedirection()` for non-container/dev scenarios.

