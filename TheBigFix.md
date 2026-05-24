# The Big Fix

## Goal

Make this repository feel like a coherent .NET 10 Blazor template app:

- The home page stays Movies, but visibly reports the render mode in a way that is technically correct.
- Blazor Auto must actually hydrate in local Docker and normal local runs.
- The app shell should follow the current .NET 10 Blazor Web App template patterns.
- Identity must move from Razor Pages Identity UI to the .NET 10 Blazor component Identity UI.
- Browser tests must prove render modes, Movies navigation, and Identity flows really work.
- Old .NET 9 migration leftovers and generated artifacts should not confuse future work.
- Custom Identity showcase/demo code stays removed.

## Execution Status

- [x] Phase 0: inspect current repo and fresh .NET 10 Individual Accounts + Auto template.
- [x] Phase 1: home page render-mode diagnostic.
- [x] Phase 2: app shell alignment with .NET 10 template.
- [x] Phase 3: replace internal asset package pin with official MSBuild property.
- [x] Phase 4: routing and navigation hardening.
- [x] Phase 5: modernize prerendered state usage.
- [x] Phase 6: migrate to Blazor component Identity.
- [x] Phase 7: add Playwright E2E tests.
- [x] Phase 8: clean generated .NET 9 artifacts.
- [x] Phase 9: full verification.

## Execution Results

- Home now renders Movies first, with a render-mode badge that separates configured mode (`Interactive Auto`), runtime assigned mode, current renderer, and interactivity.
- Component Identity has replaced the scaffolded Razor Pages Identity UI while preserving cookie-based register/login/logout/manage flows.
- Identity/login implementation files now live under feature slices:
  - server component Identity: `BlazorAutoApp/Features/Login/Account`
  - client login redirect helper: `BlazorAutoApp.Client/Features/Login/Components`
- Playwright E2E tests were added under `BlazorAutoApp.Test/E2E` and are gated behind `RUN_E2E=1`.
- Playwright covers render-mode hydration, Movies create/view/back/edit-cancel navigation, and Identity register/logout/login/profile.
- Browser E2E tests capture a screenshot under `TestResults/Playwright` only when a test fails.
- Generated `bin`/`obj` outputs were deleted after resolved-path verification and rebuilt cleanly.
- Historical EF migrations were intentionally left intact because they are database history, even when they mention removed features.

## Double Checked Status

- [x] Phase 0 double checked: reference template assumptions are recorded, and repo-specific deviations are intentional.
- [x] Phase 1 double checked: render-mode badge distinguishes configured Auto, runtime assigned mode, current renderer, and interactivity.
- [x] Phase 2 double checked: app shell has `ResourcePreloader`, shared route/head render mode, `ReconnectModal`, and `blazor.web.js` through static web assets.
- [x] Phase 3 double checked: internal ASP.NET asset package pin is gone; `<RequiresAspNetWebAssets>true</RequiresAspNetWebAssets>` is used.
- [x] Phase 4 double checked: router uses `NotFoundPage`, auth redirects route through the Login feature, and normal links work before hydration.
- [x] Phase 5 double checked: Movies prerender state uses `[PersistentState]` where it reduces manual state plumbing.
- [x] Phase 6 double checked: component Identity is server-side/static SSR, moved into the Login feature slice, and old Razor Pages Identity is removed.
- [x] Phase 7 double checked: Playwright E2E tests cover render modes, Movies, and Identity; failure screenshots are scoped to failing runs only.
- [x] Phase 8 double checked: stale `bin`/`obj` net9 outputs were removed and historical migrations were left intact deliberately.
- [x] Phase 9 double checked: build, unit/integration tests, package checks, npm checks, Docker, health endpoints, static web assets, and E2E all pass after cleanup.

## Official .NET 10 Position

Sources checked:

- ASP.NET Core Blazor render modes, .NET 10: https://learn.microsoft.com/aspnet/core/blazor/components/render-modes?view=aspnetcore-10.0
- What's new in ASP.NET Core in .NET 10: https://learn.microsoft.com/aspnet/core/release-notes/aspnetcore-10.0?view=aspnetcore-10.0
- Migrate from ASP.NET Core in .NET 9 to .NET 10: https://learn.microsoft.com/aspnet/core/migration/90-to-100?view=aspnetcore-10.0
- .NET 10 breaking changes: https://learn.microsoft.com/dotnet/core/compatibility/10
- ASP.NET Core 10 breaking changes: https://learn.microsoft.com/aspnet/core/breaking-changes/10/overview?view=aspnetcore-10.0
- ASP.NET Core Identity overview, .NET 10: https://learn.microsoft.com/aspnet/core/security/authentication/identity?view=aspnetcore-10.0
- ASP.NET Core Blazor authentication and authorization, .NET 10: https://learn.microsoft.com/aspnet/core/blazor/security/?view=aspnetcore-10.0
- Playwright .NET test runners: https://playwright.dev/dotnet/docs/test-runners

Key points from the docs:

- App-wide interactivity is assigned at `Routes`, not directly on the root `App` component.
- `HeadOutlet` should use the same render mode as `Routes`.
- For Interactive Auto, the first interactive render is server-side, then WebAssembly is used on later visits after the bundle is downloaded and cached.
- `RendererInfo.Name` alone is not enough for UI diagnostics because prerendering reports `Static` before hydration.
- The official runtime diagnostics are `RendererInfo.Name`, `RendererInfo.IsInteractive`, and `AssignedRenderMode`.
- In .NET 10, `blazor.web.js` and `blazor.server.js` are static web assets. They should be referenced through `@Assets["_framework/blazor.web.js"]`.
- If Docker restore runs before Razor files are copied, the SDK may not infer that framework web assets are required. The official fix is `<RequiresAspNetWebAssets>true</RequiresAspNetWebAssets>`, not a permanent direct dependency on `Microsoft.AspNetCore.App.Internal.Assets`.
- The .NET 10 Blazor Web App template sets `<BlazorDisableThrowNavigationException>true</BlazorDisableThrowNavigationException>`.
- The .NET 10 Blazor Web App template includes `ResourcePreloader` and a `ReconnectModal`.
- The .NET 10 router has `NotFoundPage`; the old `<NotFound>` render fragment is not the recommended path.
- The .NET 10 Blazor Web App Individual Accounts template includes Identity Razor components under `Components/Account` in the server project. This repo keeps the same component Identity pattern but places it under `Features/Login/Account` to match the feature-slice rule.
- For Interactive WebAssembly or Interactive Auto, authentication requests are handled by the server and Identity components render statically on the server.
- The Identity components themselves do not support interactivity.
- Interactive Auto auth state is flowed from server to client with authentication state serialization/deserialization.
- Playwright .NET provides an xUnit v3 integration through `Microsoft.Playwright.Xunit.v3`, which matches the existing test project's xUnit v3 direction.

## Initial Findings Before Execution

Already good at planning time:

- All source projects target `net10.0`.
- `Routes` and `HeadOutlet` are both configured with `InteractiveAuto`.
- `BlazorAutoApp.Client/Routes.razor`, layout, and nav are in the client project, which matches global Auto guidance.
- `BlazorAutoApp.Client/Pages` does not exist as a source folder.
- `/_framework/blazor.web.js` now returns `200` in the currently running Docker stack.
- `dotnet package list --outdated`, `--deprecated`, and `--vulnerable --include-transitive` found no current NuGet problems.
- `npm outdated` for the client produced no outdated output.

Problems or cleanup targets identified at planning time:

- The home page currently has no render-mode visibility.
- The previous `rendermode: Static` text was misleading because it showed prerender state without assigned mode or interactivity.
- The web project currently has an explicit `Microsoft.AspNetCore.App.Internal.Assets` package reference. It works, but it is less template-like than `<RequiresAspNetWebAssets>true</RequiresAspNetWebAssets>`.
- `App.razor` is missing the .NET 10 template's `ResourcePreloader`.
- The app has no custom `ReconnectModal`, so it falls back to framework behavior.
- The app does not set `BlazorDisableThrowNavigationException`.
- `Routes.razor` has no `NotFoundPage`.
- `NavMenu.razor` still uses `@onclick` navigation for Account/Login where normal anchors would work better and survive prerender.
- There are no browser-level tests. Current tests can prove API and architecture behavior, but not hydration, render-mode transitions, or real Identity cookie flows.
- Generated `bin` and `obj` folders still contain old `net9.0` outputs.
- EF migrations contain old Inspection names. This is historical migration state, not active source. Do not rewrite migrations unless we explicitly decide to squash/reset the database history.
- Identity is currently Razor Pages under `Areas/Identity`, not the newer Blazor component Identity layout used by the latest template. This must be migrated.

## Plan

### Phase 1: Home Page Render-Mode Diagnostic

Add a small, intentional template diagnostic component instead of a raw debug paragraph.

Implementation:

- Create `BlazorAutoApp.Client/Features/TemplateDiagnostics/Components/RenderModeBadge.razor`.
- Use the official properties:
  - `AssignedRenderMode`
  - `RendererInfo.Name`
  - `RendererInfo.IsInteractive`
- Display all three facts compactly:
  - Assigned: `Interactive Auto`
  - Current: `Static prerender`, `Server`, or `WebAssembly`
  - Interactive: `yes` or `no`
- When `RendererInfo.Name == "Static"` and `AssignedRenderMode` is interactive, label it as prerendering, not as the final mode.
- Add the badge to the Movies home page near the heading.
- Keep this under a sliced feature folder, not `Client/Pages`.

Acceptance:

- Home page visibly shows the render-mode status.
- It never implies that `Static` prerendering means the page is permanently static.
- After hydration, the status updates to an interactive renderer.

### Phase 2: Align App Shell With .NET 10 Template

Make the app shell match the current .NET 10 template where appropriate.

Implementation:

- Add `<ResourcePreloader />` after `<base href="/" />` in `BlazorAutoApp/Components/App.razor`.
- Keep `<HeadOutlet @rendermode="InteractiveAuto" />`.
- Keep `<Routes @rendermode="InteractiveAuto" />`.
- Keep the Blazor script as `<script src="@Assets["_framework/blazor.web.js"]"></script>`.
- Add a local `ReconnectModal` component and include it after `Routes`.
- Add `<BlazorDisableThrowNavigationException>true</BlazorDisableThrowNavigationException>` to the web and client project files.

Acceptance:

- App shell matches the .NET 10 Auto template shape.
- Reconnection UI is controlled by app code instead of relying only on framework fallback.
- Navigation exception behavior matches .NET 10 template expectations.

### Phase 3: Replace Internal Asset Package Pin With Official MSBuild Property

The current explicit package reference fixes Docker, but the official .NET 10 way is to make the web asset requirement explicit.

Implementation:

- Remove the direct package reference:
  - `Microsoft.AspNetCore.App.Internal.Assets`
- Add this to `BlazorAutoApp/BlazorAutoApp.csproj`:

```xml
<RequiresAspNetWebAssets>true</RequiresAspNetWebAssets>
```

- Keep `COPY global.json ./` in `BlazorAutoApp/Dockerfile` so the Docker restore layer uses the pinned SDK.
- Rebuild Docker with a clean restore path at least once.

Acceptance:

- Linux Docker publish includes:
  - `/app/wwwroot/_framework/blazor.web.js`
  - `/app/wwwroot/_framework/blazor.server.js`
  - `/app/wwwroot/_framework/blazor.webassembly.js`
- `https://localhost:7186/_framework/blazor.web.js` returns `200`.
- No direct reference remains to `Microsoft.AspNetCore.App.Internal.Assets`.

### Phase 4: Routing and Navigation Hardening

Basic navigation should not depend on hydration unless it is genuinely an interactive action.

Implementation:

- Convert Account/Login buttons in `NavMenu.razor` to anchors:
  - `/Identity/Account/Manage`
  - `/Identity/Account/Login`
- Keep the mobile menu toggle as interactive UI.
- Add a sliced `NotFound` page, for example:
  - `BlazorAutoApp.Client/Features/AppShell/Pages/NotFound.razor`
- Set `NotFoundPage` on the router.
- Consider `app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true)` if browser-address 404 handling needs a consistent page.

Acceptance:

- Movies View/Edit/Add/Back/Cancel work before and after hydration.
- Account/Login navigation works as normal links.
- Unknown Blazor routes render the .NET 10 `NotFoundPage`.

### Phase 5: Modernize Prerendered State Usage

The Movies pages use manual `PersistentComponentState`. .NET 10 has a cleaner declarative model.

Implementation:

- Replace simple page state persistence with `[PersistentState]` where it reduces code.
- Keep manual persistence only where dynamic keys or custom timing are truly needed.
- Consider `[StreamRendering]` for pages that fetch data during prerender, especially the Movies list and details pages.
- Verify the app does not double-fetch unnecessarily when hydrating.

Acceptance:

- Less boilerplate around prerender state.
- No visible loading regressions.
- No duplicate API calls beyond expected prerender/hydration behavior.

### Phase 6: Migrate to Blazor Component Identity

Identity must remain ASP.NET Core Identity underneath, but the UI should move to the .NET 10 Blazor component Identity pattern.

Implementation:

- Generate a clean temporary .NET 10 Blazor Web App with Individual Accounts and Interactive Auto to use as the reference implementation.
- Port the account component structure into the server project, following the template behavior while using the repo feature-slice layout:
  - `BlazorAutoApp/Features/Login/Account/Pages`
  - `BlazorAutoApp/Features/Login/Account/Pages/Manage`
  - `BlazorAutoApp/Features/Login/Account/Shared`
- Keep account components in the server project because they are static SSR/server-auth surfaces, not client-side feature pages.
- Preserve the repo's slicing rule: do not create `BlazorAutoApp.Client/Pages`.
- Adapt the generated Identity components to the existing `ApplicationUser` and `AppDbContext`.
- Keep PostgreSQL and the existing Identity schema.
- Configure Identity services using the .NET 10 component template pattern:
  - cookie authentication
  - Identity core/sign-in manager/token providers as needed
  - cascading authentication state
  - authentication state serialization for server-to-client auth state in Auto mode
  - authentication state deserialization in the WebAssembly client
- Replace old Razor Pages Identity UI:
  - remove `Microsoft.AspNetCore.Identity.UI` package reference
  - remove `Areas/Identity`
  - remove `Pages/Shared/_Layout.cshtml` and `_LoginPartial.cshtml` if they are only used by old Identity UI
  - remove `builder.Services.AddRazorPages()`
  - remove `app.MapRazorPages()`
- Add compatibility redirects from old `/Identity/Account/...` paths to the new component routes if useful during migration.
- Update nav links to component Identity routes, preferably:
  - `/account/login`
  - `/account/register`
  - `/account/manage`
  - `/account/logout`
- Use normal anchors for Identity navigation, not `@onclick` navigation.

Render-mode boundary:

- Account pages must use static SSR because they set and clear auth cookies.
- Add `PageRenderMode` logic to `App.razor` so account routes get `null` render mode and all normal app routes get `InteractiveAuto`.
- Apply the same boundary to `HeadOutlet`.
- Use the template helper pattern for detecting routes that accept interactivity, or a clear path-based equivalent if the generated template still does that in .NET 10.
- Do not place the render-mode badge on account pages unless it is hidden/test-only; public account pages should stay focused on auth.

Acceptance:

- Register creates a real Identity user.
- Login sets the auth cookie and updates app auth state.
- Logout clears the auth cookie.
- Account manage page requires authentication.
- Unauthenticated users are redirected to login for protected account/manage routes.
- Movies still run with `InteractiveAuto`.
- Account pages render static SSR and do not require WebAssembly hydration to work.
- No old Razor Pages Identity UI remains.

### Phase 7: Add Playwright E2E Tests

Add browser-level tests because unit/integration tests cannot prove hydration, Auto render-mode behavior, or cookie-based Identity flows.

Implementation:

- Add Playwright to `BlazorAutoApp.Test`:
  - `Microsoft.Playwright`
  - `Microsoft.Playwright.Xunit.v3`
- Add browser test folder:
  - `BlazorAutoApp.Test/E2E`
- Add a base URL configuration:
  - `E2E_BASE_URL` environment variable
  - default to `https://localhost:7186`
- Keep E2E tests in a separate xUnit collection/category/trait so they can run explicitly without slowing every unit test pass.
- Add a documented setup command to install browsers:

```powershell
pwsh .\BlazorAutoApp.Test\bin\Debug\net10.0\playwright.ps1 install chromium
```

- Decide whether the E2E fixture starts Docker Compose or requires the stack to be running first. Recommended:
  - verification script starts `docker compose up -d --build`
  - Playwright tests assert against `E2E_BASE_URL`
  - tests fail clearly if the app is unreachable

Render-mode tests:

- Add stable test IDs to the render-mode badge:
  - `data-testid="render-mode-badge"`
  - `data-testid="configured-render-mode"`
  - `data-testid="assigned-render-mode"`
  - `data-testid="current-renderer"`
  - `data-testid="is-interactive"`
- Assert homepage exposes configured mode as `Interactive Auto`.
- Assert assigned mode is an interactive mode selected by the runtime.
- Assert the badge eventually reports `Interactive: yes`.
- Assert the current renderer eventually becomes `Server` or `WebAssembly`, not permanently `Static prerender`.
- Do not require WebAssembly on first load because Interactive Auto can legitimately start on Server.
- Optionally run a second navigation/reload after assets are cached and allow `WebAssembly` as the expected preferred renderer.

Movies E2E tests:

- Navigate from home to a movie details page through `View`.
- Click `Back` and assert the browser returns to the Movies list.
- Navigate Add -> Cancel.
- Navigate Edit -> Cancel.
- Assert no console errors for missing Blazor boot assets.

Identity E2E tests:

- Navigate to Register.
- Register a unique test user.
- Assert authenticated UI state is visible.
- Navigate to Account Manage.
- Logout.
- Login again with the same user.
- Confirm account/manage is protected when logged out.
- Confirm Identity pages work without requiring the current renderer to become interactive.

Acceptance:

- E2E tests prove real browser navigation and hydration.
- E2E tests prove component Identity login/register/logout works with cookies.
- E2E tests cover render-mode diagnostics as a first-class requirement.
- Playwright screenshots are captured on failure without creating artifacts for successful runs.

### Phase 8: Generated Artifact Cleanup

Remove old generated outputs from the .NET 9 era.

Implementation:

- Delete `bin` and `obj` folders under repo projects after verifying resolved paths stay inside the repo.
- Rebuild from clean state.
- Do not edit historical EF migrations just because they mention removed features.

Acceptance:

- No `bin/**/net9.0` or `obj/**/net9.0` directories remain.
- Fresh build recreates only `net10.0` outputs.

### Phase 9: Verification

Run this as the final verification sequence:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
dotnet package list --project .\BlazorAutoApp.sln --outdated
dotnet package list --project .\BlazorAutoApp.sln --deprecated
dotnet package list --project .\BlazorAutoApp.sln --vulnerable --include-transitive
npm outdated --prefix .\BlazorAutoApp.Client
npm audit --prefix .\BlazorAutoApp.Client
docker compose build --no-cache web
docker compose up -d
curl.exe -k -s -o NUL -w "%{http_code}" https://localhost:7186/health/ready
curl.exe -k -s -o NUL -w "%{http_code}" https://localhost:7186/_framework/blazor.web.js
pwsh .\BlazorAutoApp.Test\bin\Debug\net10.0\playwright.ps1 install chromium
$env:E2E_BASE_URL = "https://localhost:7186"
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
```

Manual/browser checks:

- Load `https://localhost:7186/`.
- Confirm the homepage shows assigned render mode and current renderer.
- Confirm the current renderer changes after hydration.
- Navigate View -> Back.
- Navigate Add -> Cancel.
- Navigate Edit -> Cancel.
- Register, logout, login, and open Account Manage.
- Open a missing route and confirm the custom Not Found page.

## Risks

- Interactive Auto can legitimately report `Server` on the first interactive visit and `WebAssembly` on later visits. The badge must explain the current renderer, not promise that every visit is WebAssembly immediately.
- Moving Identity from Razor Pages to Blazor components is a real migration, not a rename. The plan must keep auth cookies, redirects, antiforgery, and protected manage pages working.
- Component Identity pages must stay static SSR. Accidentally making them interactive can break cookie-setting flows.
- Playwright requires a real browser-accessible server. `WebApplicationFactory` alone is not enough because browser automation cannot use in-memory `TestServer`.
- Deleting generated artifacts is safe only after path verification and should not touch source, migrations, storage, or Docker volumes.
- Historical migrations with removed feature names are normal. Rewriting them is a database-history decision, not a cleanup task.

## Done Criteria

- `TheBigFix.md` is implemented or explicitly superseded.
- Home page render diagnostics are visible, accurate, and not misleading during prerender.
- Blazor component Identity replaces Razor Pages Identity UI.
- Register, login, logout, and account manage work in a real browser.
- Docker and local app runs both serve the Blazor boot script through static web assets.
- The app shell includes the relevant .NET 10 template pieces.
- Basic navigation works before hydration.
- No stale `net9.0` generated outputs remain.
- Build, test, package audit, npm audit, Docker build, health check, boot-script check, and Playwright E2E pass.
