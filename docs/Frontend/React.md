# React frontend

This page covers local React development and feature changes. React has public catalog routes and an optional cookie-based account experience; the server disables accounts by default and exposes capability before the client starts account requests. Public catalog calls stay credential-free. See the [Accounts runbook](../Accounts.md) for local Admin setup, mail configuration and recovery. Read [FrontendProfiles](../FrontendProfiles.md) when changing the persisted profile, static hosting, or release pairing. The package manifest and lockfile are the version authorities: [package.json](../../GrumPlates.React/package.json), [package-lock.json](../../GrumPlates.React/package-lock.json).

## Install and develop

Use the pinned Node and npm versions in the package manifest. From `GrumPlates.React/`:

```powershell
npm ci
npm run api:check
npm run typecheck
npm run lint
npm test
npm run build
```

For live development, start compatible PostgreSQL and Redis services as described in [local setup](../HowToRunLocally.md#run-without-docker). In separate terminals, run `npm run dev:api` and `npm run dev` from `GrumPlates.React`. Open `https://localhost:5173`. Vite proxies `/api` to the C# host. If the API uses another HTTPS origin, set `REACT_API_ORIGIN` in both terminals. The dev scripts require a trusted ASP.NET Core HTTPS certificate; if needed, trust it with `dotnet dev-certs https --trust`. They do not build or change the production static root.

## Change a typed public feature

The React client uses the existing C# API. Keep public API contracts in Core/server and generated request/response types in the React package. The neutral generated-client factory and result helper live in `app/api/api-client.ts` and `app/api/api-result.ts`. Each factory caller explicitly selects credentials. The public catalog client omits credentials. Accounts owns the private client's session decoration: it reads `/api/client-config`, then uses same-origin cookies, captured-owner checks, cancellation and the session's antiforgery token when the server reports accounts enabled. Private features use that decorated provider client. Protected APIs must continue to deny anonymous access.

UI-only changes stay in React and need no new API contract or generation. Run the package checks above and the repository local gate.

When a C# endpoint contract changes:

1. Run `npm run api:check` to find drift.
2. Review the OpenAPI metadata and update generated files deliberately with `npm run api:generate`.
3. Commit the backend contract, `api/openapi.json`, and `app/api/generated/schema.d.ts` together.
4. Implement the route/component using the typed API client and existing query keys. Pass the query abort signal to the transport and preserve explicit loading, empty, and safe error states.
5. Add focused component tests. Run the package checks above, then the repository [local gate](../Test.md#local-gate).

Generation uses a metadata-only server host; it needs the .NET SDK and package toolchain, but not a running database, Redis service, or built React bundle. Do not hand-edit generated declarations or maintain duplicate wire DTOs.

## Runtime behavior

Use the generated API client in [app/api/client.ts](../../GrumPlates.React/app/api/client.ts), safe error parsing in [errors.ts](../../GrumPlates.React/app/api/errors.ts), and shared query defaults in [query-client.ts](../../GrumPlates.React/app/api/query-client.ts). The shared query client keeps results fresh for 60 seconds, removes unused entries after five minutes, and refetches on focus or reconnect. It retries once for network failures and 502/503/504, never for 4xx responses. Errors expose safe ProblemDetails, field errors, a Retry-After value capped at 60 seconds, and available correlation IDs; malformed or unexpected success bodies become invalid-response errors. Keep public links limited to safe HTTP or HTTPS URLs.

Routes live under `GrumPlates.React/app/routes`; feature components live under `app/features`. Extend the generated contract rather than duplicating API types. Browser acceptance is in [Testing/Browser](../Testing/Browser.md).
