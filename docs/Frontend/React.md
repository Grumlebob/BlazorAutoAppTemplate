# React frontend

This page covers local React development and public feature changes. React is public-only: add no account UI or authenticated client API. Read [FrontendProfiles](../FrontendProfiles.md) only when changing the persisted profile, static hosting, or release pairing. The package manifest and lockfile are the version authorities: [package.json](../../BlazorAutoApp.React/package.json), [package-lock.json](../../BlazorAutoApp.React/package-lock.json).

## Install and develop

Use the pinned Node and npm versions in the package manifest. From `BlazorAutoApp.React/`:

```powershell
npm ci
npm run api:check
npm run typecheck
npm run lint
npm test
npm run build
```

For live development, start compatible PostgreSQL and Redis services as described in [local setup](../HowToRunLocally.md#run-without-docker). In separate terminals, run `npm run dev:api` and `npm run dev` from `BlazorAutoApp.React`. Open `https://localhost:5173`. Vite proxies `/api` to the C# host. If the API uses another HTTPS origin, set `REACT_API_ORIGIN` in both terminals. The dev scripts require a trusted ASP.NET Core HTTPS certificate; if needed, trust it with `dotnet dev-certs https --trust`. They do not build or change the production static root.

## Change a typed public feature

The React client uses the existing C# API. Keep public API contracts in Core/server and generated request/response types in the React package. It has no login, cookie, auth, or CSRF bootstrap; public requests omit credentials and protected APIs must continue to deny anonymous access.

UI-only changes stay in React and need no new API contract or generation. Run the package checks above and the repository local gate.

When a C# endpoint contract changes:

1. Run `npm run api:check` to find drift.
2. Review the OpenAPI metadata and update generated files deliberately with `npm run api:generate`.
3. Commit the backend contract, `api/openapi.json`, and `app/api/generated/schema.d.ts` together.
4. Implement the route/component using the typed API client and existing query keys. Pass the query abort signal to the transport and preserve explicit loading, empty, and safe error states.
5. Add focused component tests. Run the package checks above, then the repository [local gate](../Test.md#local-gate).

Generation uses a metadata-only server host; it needs the .NET SDK and package toolchain, but not a running database, Redis service, or built React bundle. Do not hand-edit generated declarations or maintain duplicate wire DTOs.

## Runtime behavior

Use the generated API client in [app/api/client.ts](../../BlazorAutoApp.React/app/api/client.ts), safe error parsing in [errors.ts](../../BlazorAutoApp.React/app/api/errors.ts), and shared query defaults in [query-client.ts](../../BlazorAutoApp.React/app/api/query-client.ts). The shared query client keeps results fresh for 60 seconds, removes unused entries after five minutes, and refetches on focus or reconnect. It retries once for network failures and 502/503/504, never for 4xx responses. Errors expose safe ProblemDetails, field errors, a Retry-After value capped at 60 seconds, and available correlation IDs; malformed or unexpected success bodies become invalid-response errors. Keep public links limited to safe HTTP or HTTPS URLs.

Routes live under `BlazorAutoApp.React/app/routes`; feature components live under `app/features`. Extend the generated contract rather than duplicating API types. Browser acceptance is in [Testing/Browser](../Testing/Browser.md).
