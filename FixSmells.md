# Fix Smells

Status: done.

## Goal

Remove the remaining concrete smells found after the Books refactor without changing the product direction or deployment ownership.

This plan focuses on real implementation risks:

- no hidden cache bypasses or duplicate Redis clients
- no stale async modal state
- no render hot paths that quietly scale badly
- no empty contracts or fake abstractions
- no stale Movies documentation after the Books migration
- no old approval artifacts that confuse a template user

The app should still be a .NET 10 Blazor Web App template with Books on the home page, Identity authentication, render-mode diagnostics, local Docker, visible E2E tests, and LocalCluster deployment.

## Non-Goals

- Do not remove LocalCluster deployment.
- Do not redesign the book covers or book page UI in this plan.
- Do not remove Identity, passkeys, local seeded users, or render-mode diagnostics.
- Do not add architecture guardrails that make the template hard to fork.
- Do not squash migrations or reset deployment data in this plan.
- Do not remove public design demos unless a phase explicitly proves they are stale artifacts rather than current app surface.
- Do not make Playwright headless by default.

## Baseline Evidence

Status: done.

Execution notes:

- Confirmed the worktree before the smell fixes and kept unrelated files intact.
- Confirmed there were no remaining `ForceRefresh` references before continuing.
- Ran a release build during execution; it passed cleanly with 0 warnings and 0 errors.

Before edits, run:

```powershell
rg -n "ForceRefresh|forceRefresh" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Core BlazorAutoApp.Test -S
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
git diff --check
```

Expected baseline:

- No app/test `ForceRefresh` references.
- Build and tests pass before changing behavior.
- Current dirty worktree is understood and unrelated user changes are preserved.

## Phase 1: Reuse One Redis Connection For Distributed Cache

Status: done.

Execution notes:

- `AddStackExchangeRedisCache` now reuses the registered `IConnectionMultiplexer`.
- Data Protection, Redis health checks, pub/sub, and distributed cache all resolve through the same Redis registration path.
- Added an integration test covering Redis-backed distributed cache access through the shared multiplexer registration.

Finding:

`AppCachingExtensions` creates one `IConnectionMultiplexer`, registers it, then configures `AddStackExchangeRedisCache` from the connection string. That can create a second Redis connection. Health checks and Data Protection use the registered multiplexer, while `HybridCache` distributed storage may use a different connection.

Risk:

- Redis health can be green while distributed cache has a separate degraded connection.
- Local Docker E2E can show intermittent Redis timeout noise under browser/test load.
- Multiple app nodes waste Redis connections.

Files:

- `BlazorAutoApp/Infrastructure/Hosting/AppCachingExtensions.cs`
- `BlazorAutoApp/Infrastructure/Hosting/RedisHealthCheck.cs`
- `BlazorAutoApp.Test/Infrastructure/Hosting/RedisConfigurationTests.cs`
- cache integration tests under `BlazorAutoApp.Test/Features/Books/Caching`

Tasks:

- Configure `AddStackExchangeRedisCache` to reuse the existing `IConnectionMultiplexer`.
- Keep Data Protection on the same multiplexer.
- Keep `RedisHealthCheck` on the same multiplexer.
- Add or update a test that proves the registered distributed cache uses the existing multiplexer when Redis is configured.
- Confirm local/test fallback still uses distributed memory cache when Redis is intentionally missing and allowed.
- Confirm production still fails fast when Redis is missing and fallback is not allowed.

Acceptance:

- One Redis multiplexer is registered for Redis-backed cache, health checks, pub/sub, and Data Protection.
- Existing Redis configuration tests still pass.
- Cross-node cache invalidation tests still pass.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~RedisConfigurationTests|FullyQualifiedName~BooksCrossNodeCacheInvalidationTests|FullyQualifiedName~BooksCachingTests"
```

## Phase 2: Make Book Modal Async State Race-Safe

Status: done.

Execution notes:

- Added per-load cancellation to the modal host.
- Version-guarded async modal state writes after awaited authentication and API calls.
- Replaced silent load failure handling with logger-backed warnings and a safe user message.

Finding:

`BookModalHost` has a load version, but several state writes happen before all async work is proven current. Its broad catch also overwrites modal state without logging. Detail/edit loads do not use per-load cancellation tokens.

Risk:

- A slow detail request can write stale state after navigation to another modal.
- A failed old request can replace a newer modal with "Book details could not be loaded."
- User-visible modal bugs will be hard to diagnose because failures are swallowed.

Files:

- `BlazorAutoApp.Client/Features/Books/BookModal/BookModalHost.razor`
- `BlazorAutoApp.Client/Features/Books/BookModal/BookModalRouteState.cs`
- `BlazorAutoApp.Client/Features/Books/UserBookcase/UserBookcaseState.cs`
- `BlazorAutoApp.Test/E2E/Features/Books/BooksE2ETests.cs`
- client parser/state tests under `BlazorAutoApp.Test/Features/Books/Client`

Tasks:

- Add a per-load `CancellationTokenSource` to `BookModalHost`.
- Cancel the prior modal load when the location changes or the component is disposed.
- Pass the token into `Books.GetByIdAsync`.
- Guard every async state write with the current load version.
- Avoid a broad silent catch. Log unexpected failures through an injected logger.
- Preserve static author-book modal behavior without unnecessary async work.
- Preserve login redirect behavior for create/edit.
- Add focused tests where possible for route-state parsing and stale modal state rules. If component-level unit testing is not practical, strengthen E2E around fast open/back/edit transitions.

Acceptance:

- Stale modal loads cannot mutate `_error`, `_viewModel`, `_editorModel`, or `_loading`.
- Disposing the modal host cancels outstanding work.
- Unexpected load errors are logged and still show a safe user message.
- Desktop and mobile Books E2E still pass.

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
```

## Phase 3: Remove Empty Books Request Plumbing

Status: done.

Execution notes:

- Removed the empty `GetBooksRequest` contract.
- Simplified `IBooksApi.GetAsync`, the client implementation, the server implementation, and the list endpoint to use only an optional cancellation token.
- Confirmed no `GetBooksRequest` references remain.

Finding:

`GetBooksRequest` is empty after removing `ForceRefresh`. It remains in endpoint and API contracts only as leftover plumbing.

Risk:

- New contributors may assume there is hidden behavior.
- The public contract is noisier than the use case requires.
- The old bypass shape can creep back in through the empty DTO.

Files:

- `BlazorAutoApp.Core/Features/Books/UseCases/GetBooks/GetBooksRequest.cs`
- `BlazorAutoApp.Core/Features/Books/Contracts/IBooksApi.cs`
- `BlazorAutoApp.Client/Features/Books/BooksClientService.cs`
- `BlazorAutoApp/Features/Books/Endpoints/BooksEndpoints.cs`
- `BlazorAutoApp/Features/Books/Services/BooksServerService.cs`
- Books API/cache/client tests

Tasks:

- Remove `GetBooksRequest` if no paging/filtering/search is being added now.
- Change `IBooksApi.GetAsync` to `GetAsync(CancellationToken cancellationToken = default)`.
- Update client and server implementations.
- Update endpoint list handler to remove `[AsParameters] GetBooksRequest`.
- Update tests and architecture checks that expect request classes.
- If architecture tests require every use case to have a request DTO, adjust the rule to allow parameterless read use cases instead of keeping an empty DTO.

Acceptance:

- No empty public request DTO remains for list books.
- Books list API behavior is unchanged.
- Architecture tests remain fork-friendly and do not require fake DTOs.

Verification:

```powershell
rg -n "GetBooksRequest" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Core BlazorAutoApp.Test -S
dotnet test .\BlazorAutoApp.sln -c Release --no-build
```

## Phase 4: Cache User Bookcase Mapping Instead Of Rebuilding It Per Render

Status: done.

Execution notes:

- `UserBookcaseState` now owns the mapped `ShelfBooks` list.
- Create, update, delete, and reload paths update DTO state and shelf state together.
- `UserBookcase.razor` now passes the stable mapped list to `BookcaseShelf`.

Finding:

`UserBookcase.razor` calls `UserBookcaseBookMapper.ToBookcaseBooks(UserBooks.Books)` during render. The mapper always allocates a new list, so `BookcaseShelf` reference-based cache misses on every render.

Risk:

- Unnecessary allocations and repeated shelf-item rebuilding.
- The shelf cache looks stronger than it is for user books.
- Larger personal shelves will render more expensively than needed.

Files:

- `BlazorAutoApp.Client/Features/Books/UserBookcase/UserBookcase.razor`
- `BlazorAutoApp.Client/Features/Books/UserBookcase/UserBookcaseState.cs`
- `BlazorAutoApp.Client/Features/Books/UserBookcase/UserBookcaseBookMapper.cs`
- `BlazorAutoApp.Client/Features/Books/Shared/BookcaseShelf.razor`

Tasks:

- Move mapped `IReadOnlyList<BookcaseBook>` ownership into `UserBookcaseState`, or cache it by source reference/version in the mapper.
- Ensure create/update/delete update both API DTO state and shelf view state consistently.
- Keep `BookcaseShelf` as a reusable display component, not a state owner.
- Consider simplifying `BookcaseShelf` caching after the user state owns stable mapped references.

Acceptance:

- User book mapped list remains reference-stable between unrelated renders.
- Create, update, delete, reload, logout/login, and anonymous state all update the mapped shelf correctly.
- Books E2E still proves no disappearing books.

Verification:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BooksE2ETests|FullyQualifiedName~BooksCachingTests|FullyQualifiedName~BookModalRouteStateTests"
```

## Phase 5: Put A Clear Bound On Bookcase SVG Rendering Cost

Status: done.

Execution notes:

- Added configurable min/max bounds for auto-scrolling shelves.
- Auto-scroll now caps the unique books before repeating items for the visual loop.
- User shelves remain a single non-auto-scrolling pass.

Finding:

The author bookcase uses an infinite-scroll illusion by rendering repeated passes of complex inline SVG books. It is acceptable at the current catalog size, but the code gives future template users no visible limit or guidance.

Risk:

- Adding many author books can balloon DOM size.
- Inline SVG gradients, filters, title markup, and artwork paths multiply quickly.
- Performance regressions may appear first on mobile.

Files:

- `BlazorAutoApp.Client/Features/Books/Shared/BookcaseShelf.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverRenderer.razor`
- `BlazorAutoApp.Client/Features/Books/AuthorBookcase/AuthorBookcaseCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/*`

Tasks:

- Count rendered SVG book instances for author and user shelves.
- Add a documented maximum for auto-scroll shelf items, or compute a bounded display set before repeating.
- Ensure duplicate/repeated copies remain `aria-hidden` and non-focusable.
- Keep manual horizontal scrolling and hidden scrollbar behavior.
- Keep motion-reduction behavior.
- Avoid premature virtualization unless a real large-shelf case requires it.
- Add a lightweight test or source-level assertion for the auto-scroll bound if practical.

Acceptance:

- Author shelf cannot accidentally render unbounded SVG copies.
- User shelf remains one pass and does not auto-scroll.
- Desktop and mobile visual behavior remains the same for current catalog size.

Verification:

```powershell
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
dotnet test .\BlazorAutoApp.sln -c Release --no-build
```

## Phase 6: Replace Browser Confirm With In-App Delete Confirmation

Status: done.

Execution notes:

- Removed browser `confirm` from the Books modal.
- Added an in-app confirmation state with explicit confirm and cancel actions.
- Updated Books E2E tests to use the app confirmation controls.

Finding:

Book delete uses `window.confirm`. It works, but it is visually and behaviorally inconsistent with the custom SVG book modal.

Risk:

- Browser confirm cannot be styled or tested as part of the app UI.
- It is a placeholder-feeling interaction in an otherwise custom flow.
- It depends on JS interop for an operation that can be represented in Blazor state.

Files:

- `BlazorAutoApp.Client/Features/Books/BookModal/BookModalHost.razor`
- `BlazorAutoApp.Client/Features/Books/BookPage/BookPageView.razor`
- `BlazorAutoApp.Test/E2E/Features/Books/BooksE2ETests.cs`

Tasks:

- Add a small in-app confirmation state inside the book modal.
- Keep the first click as "delete" and require an explicit confirm click before API delete.
- Provide cancel/back behavior that returns to view mode without losing the modal.
- Remove `IJSRuntime` injection from `BookModalHost` if no longer needed.
- Update E2E tests to click the in-app confirmation instead of accepting a browser dialog.

Acceptance:

- Delete confirmation is visible, keyboard reachable, and styled with the book modal.
- No browser `confirm` is used for Books.
- E2E cleanup still works if a test fails midway.

Verification:

```powershell
rg -n "confirm\\(" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Test -S
dotnet test .\BlazorAutoApp.sln -c Release --no-build
```

## Phase 7: Revisit `CurrentUserAccessor` And Remove The Fallback If Possible

Status: done.

Execution notes:

- Removed service-provider lookup from `CurrentUserAccessor`.
- The fallback dependency is now explicit through injected authentication state providers.
- Kept the fallback because Interactive Auto component calls still need a non-HTTP-context path.

Finding:

`CurrentUserAccessor` falls back from `HttpContext.User` to `AuthenticationStateProvider`, then resolves by username/email through Identity. This was added to make Interactive Auto component calls work, but it is still a workaround shape.

Risk:

- It hides claim/identity configuration problems.
- It does service-provider lookup from a domain-ish service.
- It performs an extra Identity lookup when claims are incomplete.

Files:

- `BlazorAutoApp/Features/Books/Services/CurrentUserAccessor.cs`
- Identity registration/configuration under `BlazorAutoApp/Features/Login/Account`
- `BlazorAutoApp.Client/Features/Books/UserBookcase/UserBookcaseState.cs`
- API and E2E auth tests

Tasks:

- Verify exactly which component/API paths still lack `ClaimTypes.NameIdentifier`.
- If possible, fix Identity claim propagation so `NameIdentifier` is always present.
- Remove the `AuthenticationStateProvider` fallback if HTTP/API-only user resolution is sufficient after the current architecture.
- If the fallback is still required, make it explicit with smaller dependencies and focused tests.
- Add tests that prove seeded local users and newly registered users resolve the same owner id across API and interactive flows.

Acceptance:

- User id resolution is explicit and tested.
- No fallback exists unless a test proves why it is necessary.
- No user can read or mutate another user's books.

Verification:

```powershell
dotnet test .\BlazorAutoApp.sln -c Release --no-build --filter "FullyQualifiedName~Books|FullyQualifiedName~Identity"
```

## Phase 8: Clean Stale Deployment Docs After Movies-To-Books Migration

Status: done.

Execution notes:

- Updated LocalCluster deployment docs from Movies cache invalidation to Books cache invalidation.
- Replaced the stale `Cache__Movies__DisableLocalCache` setting with `Cache__Books__DisableLocalCache`.

Finding:

`Deployment/LocalCluster/HowToDeployLocalCluster.md` still describes movie cache invalidation and `Cache__Movies__DisableLocalCache`, while the code now uses Books.

Risk:

- Deployment users will configure the wrong setting.
- It undermines trust in the template documentation.

Files:

- `Deployment/LocalCluster/HowToDeployLocalCluster.md`
- `README.md`
- `HowToRunLocally.md`
- `TESTING.md`
- `BlazorAutoApp.Test/TESTING.md`
- `TemplateCustomization.md`
- `docs/plans/*` only if they are meant to remain current docs

Tasks:

- Replace current deployment docs references from Movies to Books.
- Replace `Cache__Movies__DisableLocalCache` with `Cache__Books__DisableLocalCache`.
- Search current docs for stale Movies references.
- Leave historical plan documents alone only if they are clearly archival. If they are visible root docs, either update them or move them under `docs/plans`.

Acceptance:

- Current user-facing docs describe Books, not Movies.
- LocalCluster cache invalidation docs match current `BooksCacheOptions`.
- Historical plans are either intentionally archival or no longer mixed with current docs.

Verification:

```powershell
rg -n "Movies|movies|Cache__Movies|Cache:Movies" README.md HowToRunLocally.md TESTING.md BlazorAutoApp.Test/TESTING.md TemplateCustomization.md Deployment -S
```

## Phase 9: Template Artifact Cleanup

Status: done.

Execution notes:

- Moved historical root plans into `docs/plans/archive`.
- Moved old approval demo artifacts into `docs/plans/archive/approval-demos`.
- Kept current docs and the active `FixSmells.md` plan in the root.

Finding:

The repo root contains many implementation plans and approval artifacts. Some are useful history, but a template user should not have to mentally separate current docs from old build notes.

Examples:

- `FixCoherentDesign.md`
- `FixEditModeAndAddMode.md`
- `FixPages.md`
- `FixThings.md`
- `ImproveBookCovers.md`
- `MakeItLookNiceConfirmed.md`
- `MoreBooks.md`
- `NiceBooksSvg.md`
- `ReallyGetBooksInOrderFullReviewAndFix.md`
- `TheBigBookReview.md`
- `Worthy.md`
- `Plans/NiceEditAndAddMode.PageDemo.svg`

Risk:

- Template consumers see unfinished implementation history as product documentation.
- Old plans can contain stale instructions that conflict with current behavior.

Tasks:

- Classify root `.md` files into:
  - current docs
  - active plan
  - archival plan
  - stale artifact to remove
- Move archival plans to `docs/plans/archive` or a similarly clear location.
- Remove obsolete approval-only SVG demos only if the real Blazor design demo page replaces them.
- Update README docs index if files move.
- Preserve deployment docs and current run/testing docs.

Acceptance:

- Root directory contains only current docs, app files, and intentionally active plans.
- Historical plans are clearly archival and not mistaken for instructions.
- No current docs link to removed files.

Verification:

```powershell
rg -n "NiceEditAndAddMode.PageDemo|FixCoherentDesign|ReallyGetBooksInOrderFullReviewAndFix|Worthy.md" README.md HowToRunLocally.md TESTING.md TemplateCustomization.md docs Deployment --glob '!docs/plans/archive/**' -S
git status --short
```

## Phase 10: Final Verification Gate

Status: done.

Execution notes:

- Restore completed with all projects up to date.
- Release build passed with 0 warnings and 0 errors.
- Full non-E2E-default test run passed: 72 passed, 5 skipped.
- `dotnet format --verify-no-changes`, Tailwind generated CSS verification, and `git diff --check` passed.
- Docker rebuilt the web image and the app reported ready at `https://127.0.0.1:7186/health/ready`.
- Visible desktop Books E2E passed: 2 passed, 0 skipped.
- Visible mobile Books E2E passed: 2 passed, 0 skipped.
- The old `Plans` directory is empty and no longer tracked, but Windows reported it is currently held open by another process when removal was attempted.

Run this after all phases:

```powershell
rg -n "ForceRefresh|forceRefresh" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Core BlazorAutoApp.Test -S
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
docker compose up -d --build web
Invoke-WebRequest -Uri https://127.0.0.1:7186/health/ready -SkipCertificateCheck
```

Run visible desktop Books E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.E2E.Features.Books.BooksE2ETests"
```

Run visible mobile Books E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BlazorAutoApp.Test.E2E.Features.Books.BooksE2ETests"
```

Manual checks:

- Add a book.
- Refresh.
- Open view modal.
- Edit and save.
- Refresh.
- Delete with in-app confirmation.
- Refresh.
- Logout/login as seeded user.
- Confirm no disappearing books.
- Confirm design demos still open.

## Recommended Execution Order

Status: done.

1. Phase 1 Redis connection reuse.
2. Phase 2 modal async race-safety.
3. Phase 3 empty request cleanup.
4. Phase 4 user bookcase mapping cache.
5. Phase 5 bookcase SVG render bound.
6. Phase 6 in-app delete confirmation.
7. Phase 7 current-user accessor review.
8. Phase 8 stale deployment docs.
9. Phase 9 template artifact cleanup.
10. Phase 10 final verification.

## Done Criteria

Status: done.

- No known workaround remains for Books cache freshness.
- No duplicate Redis connection path remains for cache/data-protection/health/pub-sub.
- Modal async loads are cancellation-aware and version-guarded.
- User bookcase render path avoids unnecessary mapped-list allocations.
- Books list request contract is either meaningful or removed.
- Current docs say Books, not Movies.
- Root template docs are clean enough for a fork.
- Full build/test/format/CSS/Docker/E2E verification passes.
