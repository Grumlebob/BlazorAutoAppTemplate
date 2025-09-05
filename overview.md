# Overview

This solution enables Auto render mode across pages without duplicating UI code by abstracting data access behind a shared Core interface and using host-specific implementations for prerender (server) and post-hydration (client/WASM).

## Architecture

- Core contracts and models (vertical slice):
  - `BlazorAutoApp.Core/Features/Movies`
    - `Movie` entity
    - Request/Response DTOs: GetMovies, GetMovie, CreateMovie, UpdateMovie, DeleteMovie
    - `IMoviesApi` interface: unified Movies operations

- Server (SSR/prerender):
  - EF Core with PostgreSQL via `AppDbContext`
  - `MoviesServerService` implements `IMoviesApi` using EF Core (no HTTP)
  - Minimal API endpoints call `IMoviesApi`
  - DI in `Program.cs`: `AddScoped<IMoviesApi, MoviesServerService>()`

- Client (WASM after hydration):
  - `MoviesClientService` implements `IMoviesApi` using `HttpClient` against `/api/movies`
  - DI in Client `Program.cs`: `AddScoped<IMoviesApi, MoviesClientService>()`

- UI (Client project):
  - Pages inject `IMoviesApi` and are agnostic to hosting model
  - Auto render mode already enabled in Server `App.razor`:
    - `<HeadOutlet @rendermode="InteractiveAuto" />`
    - `<Routes @rendermode="InteractiveAuto" />`

## SSR Persistent State Pattern

Goal: Avoid double fetching during prerender → hydrate. Use `PersistentComponentState` to serialize server-fetched data into the HTML payload and read it on the client side on first render.

Pattern applied to:
- List page: `BlazorAutoApp.Client/Pages/Movies/Index.razor`
  - On initialize: try `AppState.TryTakeFromJson<GetMoviesResponse>(key, out var cached)`; if present, use it.
  - If not present, fetch via `IMoviesApi` and register persist: `AppState.RegisterOnPersisting(() => AppState.PersistAsJson(key, response))`.

- Edit page: `BlazorAutoApp.Client/Pages/Movies/Edit.razor`
  - Same approach keyed by movie id, storing a `GetMovieResponse` snapshot.

- Details page: `BlazorAutoApp.Client/Pages/Movies/Details.razor`
  - Route: `/movies/{Id:int}`
  - Uses the same SSR state pattern with a per-id cache key to avoid re-fetching on hydrate.

When to use:
- Use this pattern on read-only or read-first pages (lists, details, edit forms that preload). Don’t persist for pure input forms (create) where prerender lacks meaningful data.

## Validation

- DTO annotations in Core ensure consistent rules on both server and client:
  - `CreateMovieRequest`, `UpdateMovieRequest` use `[Required]`, `[StringLength(200)]`, `[Range(0,10)]`.
- Forms (`Create.razor`, `Edit.razor`) include `DataAnnotationsValidator` + `ValidationMessage` components for field-level messages.
- Visual hints are styled in `BlazorAutoApp/wwwroot/app.css` using Blazor’s `valid/invalid` classes emitted by Input components (red for invalid, green for valid).
- The Details page is read-only, so validation is not applicable there.

## Endpoints (Minimal API)

- Use request/response DTOs from Core.
- Return types:
  - GET collection: 200 with `GetMoviesResponse`
  - GET by id: 200 with `GetMovieResponse`, 404 if not found
  - POST: 201 Created with `CreateMovieResponse` and Location header
  - PUT: 204 No Content (400 if route/body id mismatch, 404 if not found)
  - DELETE: 204 No Content (404 if not found)

## Adding a New Page with SSR State

1) Inject `PersistentComponentState` and `IMoviesApi`.
2) Choose a unique cache key (include route params if needed).
3) On initialize, try `TryTakeFromJson<T>(key, out var cached)` and use it if present.
4) If not present, fetch via `IMoviesApi` and register persist:
   - `AppState.RegisterOnPersisting(() => AppState.PersistAsJson(key, data))`.

This ensures SSR provides data to the client on first interactive render without a second HTTP call.

Example implementations in this repo:
- List: `Client/Pages/Movies/Index.razor` (caches `GetMoviesResponse`)
- Details: `Client/Pages/Movies/Details.razor` (caches `GetMovieResponse` per id)
- Edit: `Client/Pages/Movies/Edit.razor` (preloads and caches `GetMovieResponse` per id)

## Notes / Tips

- Server and client each register a different `IMoviesApi` implementation. Pages stay the same across modes.
- Keep request/response DTOs in Core to prevent duplication across tiers.
- Use 204 for mutation endpoints to simplify client handling; the client services return `bool` for success.

## Migrations

- Provider: PostgreSQL via `Npgsql.EntityFrameworkCore.PostgreSQL`.
- Connection string: `DefaultConnection` in `BlazorAutoApp/appsettings.json`.
- Migrations folder: `BlazorAutoApp/Data/Migrations`.
- Add migration:
  - `dotnet ef migrations add <Name> --project BlazorAutoApp --startup-project BlazorAutoApp --output-dir Data\Migrations`
- Apply to database:
  - `dotnet ef database update --project BlazorAutoApp --startup-project BlazorAutoApp`
- Runtime apply: `Program.cs` calls `db.Database.Migrate()` on startup.
- Current migrations:
  - `InitialCreate` (Movies table) — applied.
  - `AddReleaseYearToMovie` (nullable `ReleaseYear` column) — applied.
- EF CLI: updated to `9.0.8` to match runtime.

## Architecture Tests

- Project: `BlazorAutoApp.Test` (xUnit).
- Rule: For each public Core interface ending with `Api`, there must be both a server and a client implementation.
- Test: `ArchitectureTests.ForEachCoreApiInterface_HasServerAndClientImplementation()` reflects over assemblies to enforce the rule.
- Run: `dotnet test` at the solution root.

## Lifecycle (Auto Render)

1) Request arrives to server
   - Router renders page with `InteractiveAuto`.
   - Components resolve `IMoviesApi` → `MoviesServerService` (server DI).
   - Data loads via EF Core (no HTTP).

2) Persist SSR data (optional but used here)
   - Page stores results with `PersistentComponentState.PersistAsJson(key, data)` inside `RegisterOnPersisting`.
   - Server emits HTML + a JSON payload for each key.

3) Hydration in browser
   - Blazor bootstraps; components re-initialize.
   - DI resolves `IMoviesApi` → `MoviesClientService` (client DI).
   - Pages call `TryTakeFromJson(key, out data)` to read cached SSR data and avoid an immediate HTTP request.

4) Interactivity / further actions
   - Any subsequent data changes use `MoviesClientService` over HTTP to the server APIs.

## Short Diagram

```
Browser ── HTTP ─▶ Server (SSR)
   │                 │
   │                 ├─ Resolve IMoviesApi → MoviesServerService
   │                 ├─ Load data via EF (DbContext)
   │                 ├─ Persist SSR state (PersistentComponentState)
   │                 ▼
   ◀──────────── HTML + JSON (SSR state) ─────────────
   │
   ├─ Hydration (InteractiveAuto)
   ├─ Resolve IMoviesApi → MoviesClientService (HttpClient)
   ├─ TryTakeFromJson(state) to avoid re-fetch
   └─ Interactive operations → call /api/movies via HTTP
```

# Tailwind

go to BlazorAutoApp\BlazorAutoApp
run:
npx @tailwindcss/cli -i ./Styles/input.css -o ./wwwroot/tailwind.css --watch
