# Requirements

Canonical rules for apps built from this template. Detailed commands live in the guides linked from [README.md](../README.md).

## Rendering

- Product routes must work in SSR/prerender and after WebAssembly hydration through `InteractiveAuto`.
- Do not force `InteractiveServer` on product routes to hide Auto, SSR or WebAssembly bugs. Any server-only exception needs a clear comment and focused tests.
- Interactive controls rendered during prerender stay disabled until the component is interactive (`disabled="@(!RendererInfo.IsInteractive)"`). `PreHydrationControlsE2ETests` protects this.
- Keep prerender payloads bounded. Use `PersistentComponentState` only for bounded public data, never for large response graphs.
- Components use shared Core contracts or feature state, not raw `HttpClient`.

## UI

- Prefer Tailwind utilities and existing UI patterns. Rebuild and commit `BlazorAutoApp/wwwroot/tailwind.css` when Tailwind output changes.
- Component CSS is fine when it is cleaner or faster than a long utility string. Do not add another CSS framework without a plan.

## Performance and caching

- Public pages must be fast: useful SSR content, no N+1 queries, bounded API payloads, stable layouts, and cache behaviour that works across app nodes.
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
