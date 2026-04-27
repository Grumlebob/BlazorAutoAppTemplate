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
- App (HTTPS): https://localhost:7186
- Seq UI: http://localhost:8081
- Seq ingestion: http://localhost:5341
- Postgres: localhost:5432 (db=app, user=postgres, pwd=postgres)
- Redis: localhost:6379
- Redis UI: http://localhost:5540 - Go to Add Redis Database and write redis://redis:6379

Notes
- App reads `appsettings.Docker.json` in `ASPNETCORE_ENVIRONMENT=Docker` (set by compose).
- Serilog sinks: Console + Seq (to `http://seq:5341` inside the compose network).
- Caching: HybridCache is enabled; Redis is required in Docker. TTLs can be tuned via `Cache:Movies:*`.
- Identity uses the same application DbContext (`AppDbContext`) and works without Google OAuth setup.

Identity quick verification
--------------------------
After startup:
1) Open `/` and find the `IdentityShowcase` card.
2) As anonymous user, you should see `Guest view`.
3) Click `Login` or `Register` and complete sign-in.
4) Return to `/` and click `Refresh` in IdentityShowcase.
5) You should now see authenticated user details loaded from the secured endpoint.

Relevant endpoints:
- Public showcase: `/api/identity-showcase/public`
- Authorized showcase: `/api/identity-showcase/secure`
- Login: `/Identity/Account/Login`
- Register: `/Identity/Account/Register`

Optional Google login
---------------------
Google login is optional and only activates when both values are configured:
- `Authentication__Google__ClientId`
- `Authentication__Google__ClientSecret`

See `Plans/GoogleLoginGuideThatNeedsFinishing.md` for the full Google setup checklist.

Redis specifics (Docker Compose)
- No local install needed: compose runs a `redis` service exposed on `6379`.
- The server is configured to use `redis:6379` inside the compose network via `appsettings.Docker.json` (`Redis:Configuration`).
- `web` depends on `redis` becoming healthy, so startup waits until Redis responds to `PING`.
- If you change Redis host/port, either update `appsettings.Docker.json` or set env var `Redis__Configuration` on the `web` service.

Troubleshooting
---------------
- If Docker build failed with a test project path error, ensure the app Dockerfile restores/builds only `BlazorAutoApp.csproj` (already set up).
- If HTTPS fails in containers, re-export the dev cert with `docker/create-dev-cert.ps1` and keep the volume mount (`./docker/https:/https:ro`).
- If Seq shows no events:
  - Verify the app container logs show Serilog writing to Seq.
  - Confirm `appsettings.Docker.json` includes the Seq sink with `serverUrl: http://seq:5341`.
  - Ensure the `seq` service is healthy in `docker compose ps` and reachable from the app container.
- If Redis issues occur:
  - Check `redis` health with `docker compose ps` and container logs.
  - Ensure port `6379` isn’t blocked by other processes on your host.
  - Confirm the `web` container sees `Redis:Configuration=redis:6379` (Docker env or appsettings).
