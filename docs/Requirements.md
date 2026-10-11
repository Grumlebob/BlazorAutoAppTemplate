# Requirements

Canonical rules for apps built from this template. Detailed commands live in the guides linked from [README.md](../README.md).

## Rendering

- In Blazor Auto, product routes must work in SSR/prerender and after WebAssembly hydration through `InteractiveAuto`.
- In Blazor Auto, do not force `InteractiveServer` on product routes to hide Auto, SSR or WebAssembly bugs. Any server-only exception needs a clear comment and focused tests.
- In Blazor Auto, interactive controls rendered during prerender stay disabled until the component is interactive (`disabled="@(!RendererInfo.IsInteractive)"`). `PreHydrationControlsE2ETests` protects this.
- In Blazor Auto, keep prerender payloads bounded. Use `PersistentComponentState` only for bounded public data, never for large response graphs.
- Blazor components use shared Core contracts or feature state, not raw `HttpClient`.
- React v1 is a client-rendered static SPA; it makes no SSR/prerender SEO claim. Its route, asset and fallback contract is defined in [FrontendProfiles.md](FrontendProfiles.md).

## UI

- In Blazor Auto, prefer Tailwind utilities and existing UI patterns. Rebuild and commit `BlazorAutoApp/wwwroot/tailwind.css` when Tailwind output changes.
- Blazor component CSS is fine when it is cleaner or faster than a long utility string. Do not add another CSS framework without a plan.

## Performance and caching

- Blazor Auto public pages must be fast: useful SSR content, no N+1 queries, bounded API payloads, stable layouts, and cache behaviour that works across app nodes.
- Put a schema version in cache keys (for example `books:v2:...`) so a deploy that changes a cached shape does not read old entries.
- User-specific API responses are sent with `Cache-Control: private, no-store`.

## Runtime

- Redis is required outside development and test. Observability must fail open for app requests.
- API requests answer 401/403, never a redirect to the HTML login page.

## Testing

- Test the risk: the solution gate for normal changes, focused tests for narrow changes, E2E for real browser and render-mode workflows, Lighthouse when first load or public layouts change materially.
- Integration tests use the shared Testcontainers fixtures; containers carry `localcluster.ci.*` labels and keep data on tmpfs.

## Security

- Never log or commit secrets, auth headers, cookies, raw request bodies, connection strings or vault contents.
- React v1 is account-free and reads public APIs without credentials or an auth/CSRF bootstrap. Keep protected APIs denied and profile-specific route/security headers documented in [FrontendProfiles.md](FrontendProfiles.md); skip local account seeding while retaining public author-book seeds and existing Identity storage.
