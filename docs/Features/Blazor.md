# Blazor feature client

Use this page for `.razor` UI in `GrumPlates.Client`. Choose the profile first in [FrontendProfiles](../FrontendProfiles.md). React has a separate implementation path in [Frontend/React](../Frontend/React.md). Product rendering and accessibility rules live in [Requirements](../Requirements.md).

## Client service and route

Put UI and state under `GrumPlates.Client/Features/{Feature}`. When server data is needed, implement the shared Core API contract using relative API paths. Register client implementations and state in [client Program.cs](../../GrumPlates.Client/Program.cs). Register server contracts in the feature's `DependencyInjection.cs` and Blazor state in [FrontendComposition.BlazorAuto.cs](../../GrumPlates/Frontend/FrontendComposition.BlazorAuto.cs), which is excluded from React builds. Components inject the contract or feature state, not `HttpClient` directly. UI-only behavior needs no API implementation.

Put routable components under `GrumPlates.Client/Features/{Feature}/Routes`. Keep markup focused; move reusable UI and nontrivial loading, error, and navigation state into feature components or state classes. Add navigation only when users need it. Model loading, empty, error, unauthorized, and not-found states when reachable. Mark protected routes with `[Authorize]`; use `AuthorizeView` for protected UI fragments. Enforce data access on the server. Add stable `data-testid` hooks only when browser tests cannot select workflow controls reliably. Keep route, state, and feature tests next to their feature.

[BooksClientService](../../GrumPlates.Client/Features/Books/BooksClientService.cs) is the API implementation example. [AuthorBookcaseState](../../GrumPlates.Client/Features/Books/AuthorBookcase/AuthorBookcaseState.cs), [UserBookcaseState](../../GrumPlates.Client/Features/Books/UserBookcase/UserBookcaseState.cs), and [BookModalRouteState](../../GrumPlates.Client/Features/Books/BookModal/BookModalRouteState.cs) show different state shapes; do not copy Books-specific behavior as a universal rule.

## Prerender and interactivity

Interactive Auto prerenders on the server, then usually starts server interactivity on the first visit while downloading WebAssembly. Later visits can run in WebAssembly; an existing server component does not switch runtime when the download finishes. The server contract implementation serves prerender and server interactivity; the client implementation serves WebAssembly. Keep both implementations consistent. See [Microsoft's render-mode guidance](https://learn.microsoft.com/en-us/aspnet/core/blazor/components/render-modes?view=aspnetcore-10.0#interactive-auto).

Use `PersistentComponentState` only for bounded public data that prevents a duplicate fetch after prerender. Do not persist user-specific response data into the page. Disable controls until `RendererInfo.IsInteractive` is true; do not wait specifically for WebAssembly. Make authentication-dependent UI resilient to the transition from prerender to interactivity.

For important workflows, test prerender controls, an initial uncached visit and a later WebAssembly visit; check the actual renderer. State examples include [UserBookcaseStateTests](../../GrumPlates.Test/Features/Books/Client/UserBookcaseStateTests.cs) and [BookModalRouteStateTests](../../GrumPlates.Test/Features/Books/Client/BookModalRouteStateTests.cs); browser examples are [RenderModeE2ETests](../../GrumPlates.Test/E2E/AppShell/RenderModeE2ETests.cs) and [PreHydrationControlsE2ETests](../../GrumPlates.Test/E2E/AppShell/PreHydrationControlsE2ETests.cs).

## Styling and verification

Reuse nearby Tailwind styles. When Razor classes or `GrumPlates.Client/Styles` change, rebuild and commit `GrumPlates/wwwroot/tailwind.css`. Use the lockfile from `GrumPlates.Client`:

```powershell
Set-Location .\GrumPlates.Client
npm ci
npm run css:build
```

See [local development](../HowToRunLocally.md#tailwind), [infrastructure tests](../Testing/Infrastructure.md), [browser tests](../Testing/Browser.md), and the [local gate](../Test.md#local-gate). The Razor output is separate from the React app and its generated `build/client` directory.
