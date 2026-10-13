# Blazor feature client

Use this page for `.razor` UI in `BlazorAutoApp.Client`. Choose the profile first in [FrontendProfiles](../FrontendProfiles.md). React has a separate implementation path in [Frontend/React](../Frontend/React.md). Product rendering and accessibility rules live in [Requirements](../Requirements.md).

## Client service and route

Put the client implementation under `BlazorAutoApp.Client/Features/{Feature}`. It implements the shared Core API contract and calls relative API paths. Register it in the client composition. Components inject the contract or a feature state class, not `HttpClient` directly.

Put routable components under `BlazorAutoApp.Client/Features/{Feature}/Routes`. Keep markup focused; move reusable UI and nontrivial loading, error, and navigation state into feature components or state classes. Add a navigation entry only when users need it. Model loading, empty, error, unauthorized, and not-found states when the feature can reach them. Use `AuthorizeView` or `[Authorize]` for protected routes, while keeping data ownership checks on the server. Add stable `data-testid` hooks only for workflow controls that browser tests cannot select reliably. Keep route, state, and feature tests next to their feature.

[BooksClientService](../../BlazorAutoApp.Client/Features/Books/BooksClientService.cs) is the API implementation example. [AuthorBookcaseState](../../BlazorAutoApp.Client/Features/Books/AuthorBookcase/AuthorBookcaseState.cs), [UserBookcaseState](../../BlazorAutoApp.Client/Features/Books/UserBookcase/UserBookcaseState.cs), and [BookModalRouteState](../../BlazorAutoApp.Client/Features/Books/BookModal/BookModalRouteState.cs) show different state shapes; do not copy Books-specific behavior as a universal rule.

## Prerender and interactivity

Interactive Auto renders on the server before the WebAssembly client hydrates. The server implementation of the shared contract serves prerender; the client implementation serves later interactive calls. Keep both implementations consistent.

Use `PersistentComponentState` only for bounded public data that prevents a duplicate post-hydration fetch. Do not persist user-specific response data into the page. Disable controls that cannot work until hydration completes, and make authentication-dependent UI resilient to state changes during hydration.

For important workflows, cover rendering and pre-hydration behavior with browser tests. The current state tests include [UserBookcaseStateTests](../../BlazorAutoApp.Test/Features/Books/Client/UserBookcaseStateTests.cs) and [BookModalRouteStateTests](../../BlazorAutoApp.Test/Features/Books/Client/BookModalRouteStateTests.cs); browser examples live under [RenderModeE2ETests](../../BlazorAutoApp.Test/E2E/AppShell/RenderModeE2ETests.cs) and [PreHydrationControlsE2ETests](../../BlazorAutoApp.Test/E2E/AppShell/PreHydrationControlsE2ETests.cs).

## Styling and verification

Reuse nearby Tailwind styles. When Razor classes or `BlazorAutoApp.Client/Styles` change, rebuild and commit `BlazorAutoApp/wwwroot/tailwind.css`. Use the lockfile from `BlazorAutoApp.Client`:

```powershell
Set-Location .\BlazorAutoApp.Client
npm ci
npm run css:build
```

See [local development](../HowToRunLocally.md#tailwind), [infrastructure tests](../Testing/Infrastructure.md), [browser tests](../Testing/Browser.md), and the [local gate](../Test.md#local-gate). The Razor output is separate from the React app and its generated `build/client` directory.
