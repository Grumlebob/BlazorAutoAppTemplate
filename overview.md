# Overview

This solution is a .NET 10 Blazor Web App template built around Interactive Auto render mode. The home page is the Movies feature. It prerenders on the server, hydrates in the browser, and keeps the UI code shared by depending on feature contracts from the Core project.

## Architecture

- `BlazorAutoApp.Core/Features/Movies`
  - `Movie` domain type.
  - Request/response DTOs for list, details, create, update, and delete.
  - `IMoviesApi`, the shared interface used by pages.
- `BlazorAutoApp`
  - Server host, EF Core owner, Minimal API owner, startup composition, Identity account components, and SSR/prerender runtime.
  - `MoviesServerService` implements `IMoviesApi` directly over EF Core.
  - `/api/movies` exposes the Movies API for the hydrated client.
- `BlazorAutoApp.Client`
  - WASM client and UI slices.
  - `MoviesClientService` implements `IMoviesApi` with `HttpClient`.
- `BlazorAutoApp.Test`
  - xUnit integration and architecture tests.
  - Headed Playwright E2E tests for render mode, Movies, and Identity.

## Interactive Auto Flow

1. The browser requests `/`.
2. The server prerenders the Movies page using server DI.
3. The page resolves `IMoviesApi` to `MoviesServerService` and reads from EF Core.
4. The page persists the read model into `PersistentComponentState`.
5. Blazor hydrates in the browser.
6. The client resolves `IMoviesApi` to `MoviesClientService`.
7. The page reads the persisted state to avoid an immediate duplicate fetch.
8. Later interactions call `/api/movies` over HTTP.

The home page includes render-mode diagnostics because this repository is a template app. Users should be able to see whether they are looking at prerendered, server-interactive, or WebAssembly-interactive behavior.

## Movies Feature

Routes:

- `/` and `/movies`: Movies list and home page.
- `/movies/create`: create a movie.
- `/movies/{id:int}`: details.
- `/movies/{id:int}/edit`: edit.

API endpoints:

- `GET /api/movies`
- `GET /api/movies/{id:int}`
- `POST /api/movies`
- `PUT /api/movies/{id:int}`
- `DELETE /api/movies/{id:int}`

Validation lives on Core request DTOs, so server and client use the same rules.

## Identity

Identity is real authentication/account management, not a showcase feature. Account components live under `BlazorAutoApp/Features/Login/Account`.

Canonical routes:

- `/Account/Login`
- `/Account/Register`
- `/Account/Manage`

Old package-style compatibility routes are intentionally not part of this template.

The client has a small login route helper under `BlazorAutoApp.Client/Features/Login/Components` because redirects need to participate in client routing. The server account implementation remains in the login feature on the server.

## Persistence And Caching

- PostgreSQL is used through EF Core and `AppDbContext`.
- The current template migration history starts with one clean initial migration.
- Redis backs HybridCache and Data Protection keys.
- `App:Name` scopes Data Protection keys and authenticator issuer names for forks.
- If Redis is not configured, local/dev fallback keys are written under `/app/Storage` or `BlazorAutoApp/Storage`; this is runtime key storage, not upload storage.
- Movies cache keys:
  - List: `movies:list`
  - Item: `movies:item:{id}`
- Writes invalidate the list key and the touched item key.

Startup migrations run when `Database:RunMigrationsAtStartup` is true. Development defaults to true; Docker sets it explicitly for local use.

## Rate Limiting

Rate limiting is configured in `BlazorAutoApp/Security/AppRateLimiting.cs` and uses ASP.NET Core's built-in rate limiter middleware.

Default limits:

- Global app limit: `600` requests per minute per user/IP.
- Movies API limit: `60` requests per minute per user/IP.
- Account POST endpoint limit: `120` requests per five minutes per user/IP.

Rejected requests return `429` with a `Retry-After` header and a problem response body.

Forwarded headers are configured through `ForwardedHeaders`. The template clears ASP.NET Core's default trusted proxy lists and trusts only configured proxies/networks. LocalCluster sets the Caddy node IP as a trusted proxy for app servers.

Configuration section:

```json
"RateLimiting": {
  "Global": { "PermitLimit": 600, "WindowSeconds": 60, "QueueLimit": 0 },
  "Api": { "PermitLimit": 60, "WindowSeconds": 60, "QueueLimit": 0 },
  "Authentication": { "PermitLimit": 120, "WindowSeconds": 300, "QueueLimit": 0 }
}
```

## Tailwind

Tailwind source:

```text
BlazorAutoApp.Client/Styles/input.css
```

Generated output:

```text
BlazorAutoApp/wwwroot/tailwind.css
```

Commands:

```powershell
cd BlazorAutoApp.Client
npm install
npm run css:build
```

## Migrations

Add a migration:

```powershell
dotnet ef migrations add <MigrationName> --project BlazorAutoApp --startup-project BlazorAutoApp --output-dir Data\Migrations
```

Apply migrations:

```powershell
dotnet ef database update --project BlazorAutoApp --startup-project BlazorAutoApp
```

Bundle migrations for deployment verification:

```powershell
dotnet ef migrations bundle --project BlazorAutoApp\BlazorAutoApp.csproj --startup-project BlazorAutoApp\BlazorAutoApp.csproj --configuration Release --self-contained --runtime linux-x64 --output artifacts\migrations\verify-migrate
```
