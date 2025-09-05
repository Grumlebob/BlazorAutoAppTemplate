# Blazor Auto App Template

Production‑ready Blazor (Auto render) template with vertical slices, EF Core + PostgreSQL, Serilog logging with Seq, Minimal APIs, Docker Compose, and CI via GitHub Actions. It prerenders on the server, hydrates to WASM, and avoids double‑fetches using PersistentComponentState.

![Build Status](./.github/workflows/BuildAndTest.yml/badge.svg)

## Why This Template
- Auto render mode across pages (SSR → WASM) without duplicate UI code.
- Vertical slices: each feature owns its model + requests/responses + endpoints.
- One shared Core interface per feature; host‑specific implementations for server (EF) and client (HTTP).
- Observability out of the box with Serilog and Seq.
- First‑class local dev using Docker Compose (web + Postgres + Seq) and EF Core migrations.
- CI ready: build and test on PRs, Dependabot and optional auto‑merge.

## Tech Stack
- Blazor Web App (.NET 9) with `InteractiveAuto` render mode and PersistentComponentState.
- EF Core 9 + Npgsql (PostgreSQL).
- Minimal APIs for feature endpoints.
- Serilog (Console + Seq sink), enrichment with environment and context.
- Docker Compose for app, database, and logging.
- GitHub Actions: build/test workflow + Dependabot auto‑merge.

## Repository Layout
- `BlazorAutoApp.Core/Features/*` — Vertical slices (contracts + DTOs). Example: `Features/Movies` with `Movie`, request/response DTOs, and `IMoviesApi`.
- `BlazorAutoApp` — Server host (SSR/prerender):
  - EF Core `AppDbContext` (PostgreSQL), migrations under `Data/Migrations`.
  - Serilog configuration via `appsettings.json` and `appsettings.Docker.json`.
  - Minimal API endpoints per feature (see `Features/Movies/Endpoints.cs`).
  - Registers `IMoviesApi` → `MoviesServerService` for prerender.
- `BlazorAutoApp.Client` — Client host (WASM after hydration):
  - Registers `IMoviesApi` → `MoviesClientService` (uses `HttpClient` to call server `/api/*`).
  - Pages use PersistentComponentState to rehydrate data fetched during SSR.
- `.github/workflows` — CI pipelines for .NET build/test and Dependabot auto‑merge.
- `docker-compose.yml` — Orchestration for web + postgres + seq.
- `overview.md` — Deeper architecture walkthrough.
- `HowToRun.md` — Docker‑first run instructions.

## Architecture Overview
Blazor Auto render is enabled in `BlazorAutoApp/Components/App.razor` via:
- `<HeadOutlet @rendermode="InteractiveAuto" />` and `<Routes @rendermode="InteractiveAuto" />`.

Vertical slice pattern:
- Core defines the contracts: `IMoviesApi`, request/response DTOs, and the `Movie` entity.
- Server implements `IMoviesApi` with EF Core (`MoviesServerService`) and exposes Minimal API routes.
- Client implements `IMoviesApi` with `HttpClient` (`MoviesClientService`).
- Pages only depend on `IMoviesApi`, so the same UI works both during prerender and after hydration.

SSR persistent state pattern:
- During SSR, pages fetch via server `IMoviesApi` and persist results using `PersistentComponentState.PersistAsJson(key, data)`.
- On first interactive render, pages call `TryTakeFromJson(key, out data)` to avoid a second HTTP request.
- Applied in `Client/Pages/Movies` for list, details, and edit flows.

Minimal APIs (example behavior):
- GET list → `200` with `GetMoviesResponse`.
- GET by id → `200` with `GetMovieResponse` or `404` if not found.
- POST create → `201 Created` with location header.
- PUT update → `204 No Content` (or `404`/`400` on errors).
- DELETE → `204 No Content` (or `404`).

## Logging and Observability
- Serilog is wired via `Program.cs` with configuration from `appsettings*.json`.
- Default sinks: Console; Docker environment adds Seq sink at `http://seq:5341`.
- Enrichment: environment name, machine, log context, and common HTTP properties via `UseSerilogRequestLogging`.
- Seq UI is exposed at `http://localhost:8081` when using Docker Compose.

## Data and Migrations (EF Core + PostgreSQL)
- Connection string key: `DefaultConnection` (local default: `Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres`).
- Migrations live in `BlazorAutoApp/Data/Migrations`.
- Apply on startup: `db.Database.Migrate()` runs at boot.
- CLI examples:
  - Add: `dotnet ef migrations add <Name> --project BlazorAutoApp --startup-project BlazorAutoApp --output-dir Data\Migrations`
  - Update DB: `dotnet ef database update --project BlazorAutoApp --startup-project BlazorAutoApp`
- Provider: `Npgsql.EntityFrameworkCore.PostgreSQL`.

## Running the App
Local (no Docker):
1) Ensure PostgreSQL is available (defaults to localhost:5432, db `app`, user `postgres`, pwd `postgres`).
2) From repo root: `dotnet run --project BlazorAutoApp`.
3) Open: `https://localhost:7190` or the port shown in logs.

Docker Compose (recommended full stack):
1) Export HTTPS dev cert: `pwsh -File ./docker/create-dev-cert.ps1`.
2) `docker compose up --build`.
3) URLs:
   - App: `http://localhost:8080` and `https://localhost:8443`
   - Seq: `http://localhost:8081`
   - Postgres: `localhost:5432`

More details in `HowToRun.md`.

## GitHub Actions
- `.github/workflows/BuildAndTest.yml` runs on pushes and PRs to `main`:
  - Setup .NET 9 (prerelease allowed), restore, build, test.
- `.github/workflows/auto-merge-dependabot.yml` can auto‑approve and merge Dependabot PRs.
- `.github/dependabot.yml` tracks GitHub Actions, Docker, and NuGet updates (daily).

## Testing and Conventions
- `BlazorAutoApp.Test` uses xUnit.
- Architecture tests enforce:
  - Every public Core interface ending with `Api` has both a server and a client implementation.
  - Implementation naming: `*ServerService` and `*ClientService`.
  - For each Core `*Request` in a feature, a corresponding `FeatureName/<Request>Tests` exists under tests with at least one `[Fact]` or `[Theory]`.
- Run tests: `dotnet test`.

## Configuration Notes
- `ASPNETCORE_ENVIRONMENT=Docker` activates `appsettings.Docker.json` (ports 8080/8443, Seq sink, container DB host).
- If Seq isn’t reachable in Docker, the server adds a safe default `http://seq:5341` sink at startup.
- Override connection string with env var: `ConnectionStrings__DefaultConnection`.

## Extending the Template
- Add a new feature slice in Core under `Features/<Feature>` with entity and request/response.
- Implement `I<Feature>Api` in server (EF‑backed) and client (HttpClient‑backed).
- Add Minimal API endpoints that delegate to your Core API interface.
- Build pages that inject the Core API interface and use persistent state where SSR data should survive hydration.

For a deeper conceptual walkthrough, see `overview.md`.

