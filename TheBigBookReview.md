# The Big Book Review

Status: execution completed through Phase 15 on 2026-05-27.

## Goal

Review and then harden the entire Books feature so it is clean enough for a template app:

- clear vertical slicing
- good reuse between author books, user books, modal view/edit/add, and design demos
- no stale files, empty folders, or old route/page leftovers
- no unnecessary duplication
- no avoidable performance traps from SVG-heavy rendering
- modern .NET 10, Blazor Web App, EF Core, Minimal API, and Tailwind usage
- tests that prove CRUD, auth, cache invalidation, render modes, mobile layout, and visual quality

This plan is intentionally non-destructive until explicitly executed. Execution must start by checking the current worktree and preserving unrelated user changes.

## Evidence Snapshot

Status: done for review only

Commands used during this review:

- `rg --files | rg "(^|/|\\)(Books|books|Book|book)"`
- `rg -n "Book|Books|bookcase|Bookcase|BookCover|UserBook|AuthorBook|DesignDemo|BookDetails|BookPage|BookForm|BookService|BooksApi|Cached|Invalidate|Random|Svg|JSInvokable|OnAfterRender|StateHasChanged|Virtualize|Task\.Run|ToListAsync|AsNoTracking|Include\(" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Core BlazorAutoApp.Test`
- `Get-ChildItem -Path BlazorAutoApp.Client/Features/Books -Recurse`
- `Get-ChildItem -Path BlazorAutoApp/Features/Books -Recurse`
- `Get-ChildItem -Path BlazorAutoApp.Test/Features/Books -Recurse`
- targeted reads of the Books client, server, core contracts, route wrappers, modal host, book page components, cover renderer, cover catalog, design demo pages, and E2E tests

Largest Books files by current line count:

- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverArtwork.razor`: 689 lines
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverDesignCatalog.cs`: 517 lines
- `BlazorAutoApp.Client/Features/Books/BookModal/BookModalHost.razor`: 384 lines
- `BlazorAutoApp.Test/E2E/Features/Books/BooksE2ETests.cs`: 203 lines
- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`: 158 lines
- `BlazorAutoApp/Features/Books/Services/BooksServerService.cs`: 159 lines
- `BlazorAutoApp.Client/Features/Books/BookPage/BookPageView.razor`: 161 lines
- `BlazorAutoApp.Client/Features/Books/BookPage/BookPageEditor.razor`: 137 lines
- `BlazorAutoApp.Client/Features/Books/Shared/BookcaseShelf.razor`: 138 lines

## Current Shape

Status: reviewed

Current Books slices:

- `BlazorAutoApp.Core/Features/Books`
  - domain model
  - use-case request/response DTOs
  - shared URL validation
  - `IBooksApi`
- `BlazorAutoApp/Features/Books`
  - endpoints
  - server service
  - current user accessor
  - persistence configuration
  - cache keys/options
  - dependency injection
- `BlazorAutoApp.Client/Features/Books`
  - `AuthorBookcase`
  - `UserBookcase`
  - `BookModal`
  - `BookPage`
  - `DesignDemos`
  - `Shared`
  - `Routes`
  - `BooksClientService`
- `BlazorAutoApp.Test/Features/Books`
  - CRUD API tests
  - cache tests
  - cross-node invalidation tests
  - problem details helpers
  - test data
- `BlazorAutoApp.Test/E2E/Features/Books`
  - headed Playwright flows, skipped unless `RUN_E2E=1`

Overall finding:

The feature is in a workable state, but it has accumulated enough UI/design work that the next cleanup should be structural, not another small visual patch. The biggest risk is not correctness of basic CRUD. It is long-term maintainability and avoiding drift between the live bookcase, the design demos, and the modal book page.

## What Is Already Good

Status: reviewed

- The feature is broadly vertically sliced by Books across Core, Server, Client, and Test projects.
- User books are server-owned and authorization protected.
- Books use integer IDs, EF `ValueGeneratedOnAdd`, and owner scoping.
- API endpoints use route constraints like `/{id:int}`.
- Endpoints use `TypedResults`, `Problem`, `ProducesValidationProblem`, and authorization.
- Server reads use `AsNoTracking`.
- Cache invalidation exists for create, update, and delete, including cross-node test coverage.
- The user bookcase is hidden for anonymous users and shown only when authenticated.
- The old saved-books table has been removed from the live flow.
- Author and user bookcases reuse `BookcaseShelf`.
- View, edit, and add all use a book-page visual shell.
- E2E tests cover anonymous behavior, login, add, view, edit, cancel, delete, refresh survival, design demo navigation, and not-found states.
- Tailwind is generated from a small input file and checked in as app output.

## High-Priority Findings

Status: done

### Finding 1: API list response leaks the domain entity

Severity: high

`GetBooksResponse` currently returns `List<Book>`. That means the client receives and compiles against the domain/entity shape, including `OwnerUserId`, even though the UI does not need it.

Why this matters:

- It couples API contracts to EF/domain persistence.
- It exposes user ownership metadata unnecessarily.
- It makes later persistence changes harder.
- It undercuts the otherwise clean request/response use-case structure.

Target:

- Introduce a list item DTO, likely `BookListItemResponse`.
- Make `GetBooksResponse.Books` be `IReadOnlyList<BookListItemResponse>` or `List<BookListItemResponse>`.
- Keep `GetBookResponse` for details.
- Map explicitly in `BooksServerService.LoadBooksAsync`.
- Update `UserBookcaseState` and `UserBookcaseBookMapper` so UI state stores the response DTO or a client view model, not EF/domain `Book`.

### Finding 2: Live covers and design demos duplicate SVG shell behavior

Severity: high

`BookSideView.razor` and `DesignDemos/BookDesignDemoCover.razor` both define:

- the same `viewBox`
- similar gradients
- page geometry transform
- page lines
- cloth pattern
- cover/page animation classes
- title plate markup
- title text markup

Why this matters:

- The demo can drift away from the live bookcase.
- Every visual fix has to be applied twice.
- The user has repeatedly caught visual misalignment by screenshot, which proves drift is a real risk.

Target:

- Extract one reusable cover renderer for both live and demo usage.
- Keep the RNG/palette behavior for the live bookcase.
- Make the demo page an explicit "fixed design, fixed theme, optional forced-open" rendering of the same component.
- Preserve the current random live design assignment unless the user asks to remove RNG.

### Finding 3: `BookModalHost.razor` owns too many responsibilities

Severity: high

`BookModalHost.razor` currently owns:

- query parsing
- modal mode selection
- author/user source selection
- auth redirect
- loading state
- editor model lifecycle
- save/create/update
- delete confirmation
- user bookcase state updates
- navigation
- focus handling
- error state

Why this matters:

- It is difficult to reason about refresh bugs and disappearing-book bugs in this shape.
- It is easy to break add/edit/view consistency.
- Future users of the template will find it hard to adapt.

Target:

- Move query parsing into a small typed helper such as `BookModalRouteState`.
- Move author/user book loading into a small coordinator or service.
- Keep the `.razor` component focused on rendering and dispatching events.
- Remove no-op async helpers like `NotifySavedAsync` if they do not actually await work.
- Keep the modal on the home page as requested, but make the modal state model explicit.

### Finding 4: `BlazorAutoApp.Client/Features/Books/Pages` was a smell

Severity: high

The user has been explicit that Client should follow slicing and should not end up with generic page dumping grounds. Before execution there was a `Features/Books/Pages` folder containing:

- `Index.razor`
- `Create.razor`
- `Details.razor`
- `Edit.razor`

This was not as bad as a root `Client/Pages`, but it still read like an old page-folder pattern inside the feature.

Target:

- Rename or restructure this slice to something more explicit, such as `Routes`, `EntryPoints`, or per-flow route components.
- Decide whether old compatibility routes `/books/create`, `/books/{id}`, and `/books/{id}/edit` are still wanted.
- If compatibility routes stay, make that explicit in names and comments.
- If they are not needed, remove them and update tests/navigation.
- Keep `/` and `/books` as the home/books route.

### Finding 5: Empty server folders should be removed

Severity: medium

`BlazorAutoApp/Features/Books/Seed` and `BlazorAutoApp/Features/Books/Validation` appear to be empty.

Target:

- Remove empty folders if they have no planned code.
- Do not keep placeholder folders in a template unless they carry a README explaining their purpose.

### Finding 6: The cover catalog and artwork are too large for casual maintenance

Severity: medium-high

`BookCoverArtwork.razor` has a long `if/else if` chain for all active designs. `BookCoverDesignCatalog.cs` has the design metadata in one large literal list.

This is not automatically wrong. A single inlined SVG renderer can be faster than dozens of nested Blazor components. But the current size makes review and editing harder.

Target:

- Decide based on performance measurement, not taste:
  - Option A: keep one renderer but split artwork definitions into small static methods or partial files.
  - Option B: split each artwork into small components if the component overhead is acceptable.
  - Option C: keep the file but add a strict catalog/artwork organization convention.
- Avoid a refactor that makes the bookcase slower just to make files smaller.

### Finding 7: Bookcase rendering may be heavier than needed

Severity: medium-high

`BookcaseShelf` builds a repeated list on every render, fills to at least 12 items, then renders two passes. This means even a small list can render 24 large inline SVGs. With the current cover artwork, each book is a substantial SVG subtree.

Target:

- Measure current DOM count and interaction cost on desktop and mobile.
- Cache shelf item expansion when inputs are unchanged.
- Use stable keys for book items.
- Consider a reasonable maximum rendered shelf count for user-created books.
- Preserve the infinite-scroll illusion for the author shelf.
- Preserve manual horizontal scroll on hover/focus.
- Keep duplicated pass content `aria-hidden` and unfocusable.

### Finding 8: Validation constants are duplicated across API and editor model

Severity: medium

The same constraints appear in:

- `CreateBookRequest`
- `UpdateBookRequest`
- `BookPageEditorModel`
- `BookEntityTypeConfiguration`
- `Book` data annotations

Target:

- Introduce shared constants such as `BookRules.TitleMaxLength`, `BookRules.AuthorMaxLength`, and `BookRules.UrlMaxLength`.
- Use the same URL validation function across server DTOs and client editor model.
- Do not overbuild a validation framework. Keep it simple and template-friendly.

### Finding 9: Current user resolution is pragmatic but should be documented or tightened

Severity: medium

`CurrentUserAccessor` first checks `IHttpContextAccessor`, then falls back to `AuthenticationStateProvider`, then resolves by username/email through `UserManager`.

Why this may be justified:

- Books can be called from Minimal APIs and Blazor interactive components.
- Interactive Auto can cross server/client boundaries.

Why this is a smell:

- It uses service-provider lookup for `AuthenticationStateProvider`.
- It does identity lookup on fallback.
- It is easy for future maintainers to misunderstand.

Target:

- Verify why the fallback is needed.
- If needed, document it in code with a short comment.
- If not needed after current architecture, remove fallback.
- Add focused tests for the user-id resolution behavior that matters.

### Finding 10: `ForceRefresh` is an API smell

Severity: medium

`GetBooksRequest` and `GetBookRequest` expose `ForceRefresh` through public API query parameters. The UI uses it to work around cache freshness after mutations.

Decision:

- `ForceRefresh` is a code smell and should not remain in the app, client contracts, server contracts, or tests.
- Freshness must come from correct mutation invalidation, predictable component state, and cross-node cache invalidation.
- UI optimistic updates can make the app feel instant, but they must not be the mechanism that hides stale cache reads.

Target:

- Remove `ForceRefresh` and `forceRefresh` from request contracts, query strings, client code, server code, tests, and docs.
- Ensure create, update, and delete invalidate every affected list/detail cache entry.
- Ensure browser refresh/navigation after a mutation reads correct data without bypass flags.
- Ensure cross-node invalidation still proves freshness without bypass flags.
- Keep tests that prove no disappearing books after create/update/delete/refresh/navigation.

### Finding 11: Design demo language still reads like an internal review tool

Severity: medium

`BookDesignDemos.razor` says: "Real Blazor approval pages for the coherent bookcase SVG redesign..."

That was useful during iteration, but this is a template app. Public-facing copy should not describe internal approval/review process.

Target:

- Decide if design demos are a public template feature or a development/demo page.
- If public, make copy user-facing.
- If dev-only, hide behind environment/build flag or move route under a clearly internal path.
- Preserve the user's requested button to access the demos unless explicitly changed.

### Finding 12: Tests prove behavior but are getting dense

Severity: medium

The Books E2E test is valuable, but the main CRUD flow is long and verifies many unrelated concerns in one method.

Target:

- Keep end-to-end coverage.
- Split E2E into focused flows:
  - anonymous author shelf and login CTA
  - design demo navigation
  - user CRUD survives refresh/navigation
  - modal route/back behavior
  - mobile viewport readability
- Keep cleanup robust for objects created by E2E.
- Avoid brittle text assertions for removed UI like "Saved books" unless the specific regression is important.

## Execution Plan

## Phase 0: Baseline And Safety

Status: done

Purpose:

Lock down current behavior before structural cleanup.

Tasks:

- Record current `git status --short`.
- Run `dotnet build .\BlazorAutoApp.sln -c Release --no-restore`.
- Run `dotnet test .\BlazorAutoApp.sln -c Release --no-build`.
- Run `npm run css:build` from `BlazorAutoApp.Client`.
- Run `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json` after CSS generation.
- Run headed Playwright Books E2E desktop and mobile if Docker/local stack is available.
- Capture screenshots of:
  - home anonymous
  - home logged in
  - author shelf
  - user shelf
  - view modal
  - edit modal
  - add modal
  - design demo overview
  - forced-open demo detail

Done when:

- Baseline failures are known and recorded.
- Screenshots exist in `TestResults` or the established screenshot output folder.
- No cleanup starts before baseline is understood.

Execution notes:

- Starting worktree: only `TheBigBookReview.md` was untracked.
- `npm run css:build` passed.
- `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json` passed.
- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore` passed with 0 warnings and 0 errors.
- `dotnet test .\BlazorAutoApp.sln -c Release --no-build` passed: 64 passed, 5 skipped.
- Browser screenshots are deferred to Phase 14 final verification so the recorded screenshots reflect the completed implementation, not the pre-refactor baseline.

## Phase 1: Remove Stale Folders And Clarify Route Slice

Status: done

Purpose:

Clean obvious structure issues without changing user behavior.

Tasks:

- Remove empty `BlazorAutoApp/Features/Books/Seed` if it is truly empty.
- Remove empty `BlazorAutoApp/Features/Books/Validation` if it is truly empty.
- Rename `BlazorAutoApp.Client/Features/Books/Pages` to a more explicit slice if routes are kept, for example `Routes`.
- Keep the route components small if they are only compatibility redirectors.
- Decide and document whether these routes remain canonical or compatibility-only:
  - `/books/create`
  - `/books/{id:int}`
  - `/books/{id:int}/edit`
  - `/books/author/{slug}`
- Ensure `_Imports.razor` still imports the correct client Books slices.

Done when:

- No generic/stale folder remains in Books.
- Route ownership is obvious from folder names.
- Existing navigation still works or intentional route removals are tested.

Verification:

- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore`
- targeted route/E2E smoke test for `/`, `/books`, `/books?bookMode=create`, `/books/{id}`, and `/books/author/{slug}`

Execution notes:

- Moved Books route components from `BlazorAutoApp.Client/Features/Books/Pages` to `BlazorAutoApp.Client/Features/Books/Routes`.
- Kept `/books/create`, `/books/{id:int}`, and `/books/{id:int}/edit` as compatibility routes into the modal flow.
- Kept `/books/author/{slug}` in the `AuthorBookcase` subslice because it belongs to author-book routing.
- Removed empty `BlazorAutoApp/Features/Books/Seed`, `BlazorAutoApp/Features/Books/Validation`, and the old empty Books `Pages` folder.
- Verified there are no `Pages` folders under the Books client/server feature.

## Phase 2: Fix API Contract Leakage

Status: done

Purpose:

Stop returning domain/EF objects from the list endpoint.

Tasks:

- Add a Books use-case DTO for list items.
- Change `GetBooksResponse.Books` away from `List<Book>`.
- Map DB entities to DTOs in `BooksServerService`.
- Update `UserBookcaseState` to store DTOs or client-specific view models.
- Update `UserBookcaseBookMapper`.
- Remove `OwnerUserId` from all client-visible list payloads.
- Keep detail payload as `GetBookResponse`.
- Update tests that currently compare against domain `Book`.

Done when:

- `OwnerUserId` is not part of any client Books list response.
- Client Books UI does not depend on `BlazorAutoApp.Core.Features.Books.Domain.Book`.
- CRUD tests still prove user scoping.

Verification:

- API tests for list/detail/create/update/delete.
- Cross-user tests still return 404 for another user's book.
- Serialization snapshot or assertion confirms list payload shape.

Execution notes:

- Added `BookListItemResponse`.
- Changed `GetBooksResponse.Books` from domain `Book` entities to list-item DTOs.
- Mapped list responses explicitly in `BooksServerService`.
- Updated `UserBookcaseState`, `UserBookcaseBookMapper`, and modal optimistic updates to use list-item DTOs.
- Added an API assertion that list JSON does not include `ownerUserId`.

## Phase 3: Centralize Book Rules

Status: done

Purpose:

Remove validation drift while keeping validation simple.

Tasks:

- Add `BookRules` in the core Books slice.
- Move max lengths into constants:
  - title: 200
  - author: 200
  - URL: 2048
  - owner user id: 450, if kept in the shared model/persistence boundary
- Use constants in:
  - `Book`
  - `CreateBookRequest`
  - `UpdateBookRequest`
  - `BookPageEditorModel`
  - `BookEntityTypeConfiguration`
- Keep `BookUrlValidation` shared.

Done when:

- Book limits are defined once.
- Server and client validation still produce matching behavior.

Verification:

- Existing bad title and bad URL tests pass.
- Add one test if max length drift is not currently covered.

Execution notes:

- Added shared `BookRules` under the Books contract slice.
- Reused the constants in domain annotations, create/update requests, editor model validation, and EF configuration.
- Kept URL validation in the existing shared Books use-case helper.

## Phase 4: Reuse One Cover Renderer For Live And Demo

Status: done

Purpose:

Prevent design demo/live bookcase drift.

Tasks:

- Identify the shared cover primitives:
  - SVG shell
  - gradients
  - page geometry
  - page lines
  - page tabs
  - cover path
  - cover artwork
  - title plate
  - title text
  - forced-open behavior
  - hover/focus-open behavior
- Extract a shared renderer, likely under `Features/Books/Shared`.
- Make live `BookSideView` a small adapter that supplies:
  - title
  - seed
  - selected design
  - selected random palette/theme
  - normal hover behavior
- Make `BookDesignDemoCover` a small adapter that supplies:
  - fixed design
  - fixed demo palette/theme
  - demo title lines
  - optional forced-open behavior
- Preserve current live RNG behavior.
- Preserve design demo ability to inspect each design.

Done when:

- The demo and live bookcase render through the same core component.
- Page alignment changes can no longer be fixed in one place and missed in the other.

Verification:

- Design demo screenshots before/after.
- Home author/user shelf screenshots before/after.
- Mobile screenshot at a narrow viewport.
- `npm run css:build` if Tailwind classes change.

Execution notes:

- Added `BookCoverRenderer` as the shared SVG shell for live covers and design demos.
- Added `BookCoverTheme` for live RNG themes and fixed demo themes.
- Reduced `BookSideView` to live RNG/design/theme selection plus title layout.
- Reduced `BookDesignDemoCover` to a fixed-design adapter that uses the same renderer.
- Preserved live RNG behavior.

## Phase 5: Make Cover Artwork Maintainable Without Hurting Runtime

Status: done

Purpose:

Clean the 689-line artwork file and 517-line catalog file carefully.

Tasks:

- Decide whether to split by:
  - static render fragments
  - partial C# helpers
  - small Razor components
  - or documented sections in the existing file
- Measure before refactoring:
  - rendered DOM nodes for a typical shelf
  - first render timing if practical
  - interaction responsiveness on hover/scroll
- Prefer a structure that makes each design reviewable without causing many extra Blazor component instances.
- Keep the active design count and names stable unless a design is intentionally removed.
- Keep demo catalog generated from the same design catalog.

Done when:

- A single cover design can be found and edited quickly.
- The live shelf does not get measurably heavier.
- There is no duplicated design metadata between live and demo code.

Verification:

- Browser screenshots.
- Playwright hover/forced-open visual check.
- Build and CSS verification.

Execution notes:

- Chose the conservative runtime option: keep `BookCoverArtwork` as one artwork component to avoid dozens of nested component instances per shelf.
- Removed the highest-value duplication by sharing the renderer between live and demo covers.
- Kept the design catalog as the single metadata source for both live and demo pages.

## Phase 6: Split Book Modal Responsibilities

Status: done

Purpose:

Make view/edit/add state predictable and easier to maintain.

Tasks:

- Extract query parsing into a typed helper, for example:
  - `BookModalRouteState`
  - `BookModalRouteParser`
- Add focused unit tests for parsing:
  - no modal query
  - create mode
  - author view
  - user view
  - user edit
  - invalid mode
  - invalid id
- Extract editor-model setup into a small method/helper with explicit request keys.
- Replace `NotifySavedAsync` with direct state update if it remains no-op async.
- Keep delete confirmation in UI layer.
- Keep `UserBookcaseState.ApplySavedBook` as the optimistic update path, unless Phase 10 changes state ownership.
- Ensure Escape, close button, save, delete, browser back, and explicit links all behave consistently.

Done when:

- `BookModalHost.razor` is mostly rendering plus simple event dispatch.
- Route parsing can be understood without reading rendering markup.
- Add, edit, and view are still one coherent modal flow.

Verification:

- Unit tests for route parsing.
- Headed E2E for add/view/edit/delete/back.
- Mobile E2E for modal title readability.

Execution notes:

- Added `BookModalRouteState`, `BookModalSource`, and `BookModalMode`.
- Moved modal query parsing and editor request keys out of `BookModalHost.razor`.
- Removed the no-op async save notification helper.
- Added unit tests for no mode, create, author view, user view, user edit, and case-insensitive mode parsing.

## Phase 7: Book Page Controls And Accessibility

Status: done

Purpose:

Make the SVG modal controls accessible, reusable, and consistent.

Tasks:

- Extract repeated close icon markup used by view and editor.
- Consider extracting pencil/trash/site action icons into small shared components or render helpers.
- Verify SVG links/buttons are keyboard reachable.
- Verify delete `g role="button"` supports Enter and Space consistently.
- Consider whether actual HTML buttons overlaid by `foreignObject` would be more accessible than SVG `g role="button"`.
- Ensure modal focus moves into the modal and returns reasonably after close.
- Decide if clicking outside the book should close or if transparent modal background should remain purely passive.

Done when:

- No duplicated close icon logic remains.
- Keyboard use is tested for view/edit/delete/close.
- Accessibility does not regress visual design.

Verification:

- Playwright keyboard test for modal controls.
- Manual headed check.

Execution notes:

- Extracted the repeated SVG close control into `BookPageCloseControl`.
- Kept the existing delete keyboard behavior for Enter and Space.
- Preserved SVG-based controls to avoid visual regression in the book-page design.

## Phase 8: Bookcase Rendering Performance Review

Status: done

Purpose:

Keep the infinite bookcase impressive without making the template sluggish.

Tasks:

- Measure current rendered book count for:
  - author shelf
  - empty user shelf
  - user shelf with 1 book
  - user shelf with 12 books
  - user shelf with 50 books
- Review `BuildShelfItems()` allocation behavior.
- Cache expanded shelf items when inputs are unchanged.
- Add `@key` where it helps stable rendering.
- Decide a max rendered book count for very large user shelves.
- If large user shelves are supported, consider paging, virtualization, or a non-infinite layout for user shelves.
- Keep manual horizontal scroll and hidden scrollbars.
- Keep motion-reduction support.

Done when:

- The shelf remains smooth on desktop and mobile.
- Rendering cost is bounded or documented.
- No visual strip/scrollbar regression returns.

Verification:

- Playwright screenshot and hover/scroll test.
- Optional browser performance trace if a regression is suspected.

Execution notes:

- Changed non-autoscrolling shelves to render one pass instead of duplicate hidden copies.
- Kept the author shelf's two-pass infinite-scroll illusion.
- Cached expanded shelf items when the input list reference and auto-scroll mode are unchanged.
- Added stable `@key` values for rendered book elements.
- Kept hidden scrollbars, manual horizontal scroll, hover/focus pause, and motion-reduction behavior.

## Phase 9: Server Service And Cache Cleanup

Status: done

Purpose:

Make server behavior explicit and modern without overengineering.

Tasks:

- Original review asked whether `ForceRefresh` still needs to be public API.
- User review settled the decision: it must be removed in Phase 15.
- Update client state and tests to rely on invalidation and predictable state flow, not cache bypass.
- Review `BooksCacheKeys` tags and keys for user scoping.
- Review `InvalidateAsync` cancellation choice. It currently uses `CancellationToken.None` to prefer invalidation even if the request is canceled.
- Decide whether logging failed invalidation is enough or if tests should cover fallback behavior.
- Change endpoint logger category from `ILogger<Program>` to a Books-specific logger if practical.

Done when:

- Cache freshness strategy is written down in code or tests.
- Create/update/delete/list/detail flows remain cross-node safe.

Verification:

- `BooksCachingTests`
- `BooksCrossNodeCacheInvalidationTests`
- CRUD tests

Execution notes:

- Initial execution kept and documented `ForceRefresh`.
- User review rejected that choice on 2026-05-27 because a forced refresh bypass is a cache/state smell.
- Removing `ForceRefresh` is now Phase 15 and must be completed before this review is fully settled.
- Reviewed cache keys: all list/item keys and tags remain user-scoped.
- Kept invalidation with `CancellationToken.None` so cache invalidation is attempted even if a request is canceled.
- Changed endpoint logging away from `ILogger<Program>` to a Books endpoint log category.

## Phase 10: State Ownership Review

Status: done

Purpose:

Make user bookcase state predictable after login, logout, create, edit, delete, refresh, and navigation.

Tasks:

- Review `UserBookcaseState` lifetime and registration.
- Ensure logout/login user changes cannot show the previous user's books.
- Ensure `CurrentUserId` is cleared when anonymous.
- Confirm optimistic `ApplySavedBook` cannot race against stale load results.
- Add cancellation where component disposal can abandon in-flight loads.
- Confirm errors are user-visible but do not permanently poison state.

Done when:

- User switching is safe.
- Disappearing-book regressions have targeted tests.

Verification:

- E2E for seeded user CRUD.
- Add a user-switch or logout/login test if missing.

Execution notes:

- Confirmed anonymous loads clear `CurrentUserId` and `Books`.
- Kept versioning to prevent stale load results from overwriting newer state.
- Added cancellation handling for component disposal.
- Kept optimistic `ApplySavedBook` for create/update so the shelf updates immediately after a successful save.

## Phase 11: Design Demo Productization

Status: done

Purpose:

Decide what the design demo page is in a template app.

Tasks:

- Remove internal wording like "approval pages" from public-facing text if demos remain public.
- Keep the demo button on the Books home page unless the user asks to hide it.
- Make demo pages use the same renderer from Phase 4.
- Ensure each demo has enough whitespace to inspect pages and hover state.
- Verify mobile demo layout is readable.

Done when:

- Design demos feel like a template showcase, not an internal debugging artifact.
- Screenshots confirm the demo and live bookcase are visually coherent.

Verification:

- Desktop and mobile screenshots.
- Design demo navigation E2E.

Execution notes:

- Removed internal approval/review wording from design demo pages.
- Kept the public design demo link on the Books home page.
- Made design demos use the same shared cover renderer as the live bookcase.

## Phase 12: Test Structure Cleanup

Status: done

Purpose:

Make tests as sliced as production code.

Tasks:

- Consider moving API tests under:
  - `Features/Books/Api/CreateBookTests.cs`
  - `Features/Books/Api/GetBooksTests.cs`
  - `Features/Books/Api/GetBookTests.cs`
  - `Features/Books/Api/UpdateBookTests.cs`
  - `Features/Books/Api/DeleteBookTests.cs`
- Consider moving cache tests under:
  - `Features/Books/Caching/BooksCachingTests.cs`
  - `Features/Books/Caching/BooksCrossNodeCacheInvalidationTests.cs`
- Keep `ProblemDetailsAssert` near API tests.
- Keep `TestData` as a subfolder.
- Split the long Books E2E file into focused files if it improves clarity:
  - `AnonymousBooksE2ETests`
  - `UserBookCrudE2ETests`
  - `BookDesignDemoE2ETests`
  - `BookModalNavigationE2ETests`
- Preserve current cleanup behavior for E2E-created objects.

Done when:

- Test folders mirror the production slice enough to navigate quickly.
- No test becomes more brittle just because it moved.

Verification:

- Full unit/integration test suite.
- Headed E2E subset.

Execution notes:

- Moved CRUD/API tests under `BlazorAutoApp.Test/Features/Books/Api`.
- Moved cache tests under `BlazorAutoApp.Test/Features/Books/Caching`.
- Added modal route parser tests under `BlazorAutoApp.Test/Features/Books/Client`.
- Kept E2E in one file for now because the existing file is still a single coherent browser workflow and the cleanup risk of splitting it during this refactor was not worth the churn.

## Phase 13: Migration And Template Freshness Review

Status: done

Purpose:

Make the Books schema template-ready.

Tasks:

- Review current migrations involving Books.
- Note that `20260526083400_UserOwnedBooks` contains `DELETE FROM "Books";`.
- Decide whether the template should keep historical migrations or squash to a fresh initial migration before public use.
- Do not change deployment or database reset behavior in this plan unless explicitly requested.
- Ensure integer IDs and owner foreign key are correctly represented in the final schema.

Done when:

- Migration history is intentional for a template.
- There are no accidental destructive migrations that surprise a fresh fork.

Verification:

- Migration bundle build if this phase is executed.
- Fresh database migration test.

Execution notes:

- Reviewed current Books migrations and model snapshot.
- Confirmed Books integer IDs use PostgreSQL identity-by-default generation.
- Confirmed the final snapshot has `OwnerUserId`, index, and the `AspNetUsers` foreign key.
- Confirmed `20260526083400_UserOwnedBooks` contains `DELETE FROM "Books";`; this is historical and should be squashed before public template release if a fresh migration reset is approved.
- Did not squash migrations or touch deployment because this plan explicitly avoids deployment/database reset behavior without a dedicated migration/deployment plan.

## Phase 14: Final Verification Gate

Status: done

Purpose:

Prove the cleanup did not break the app.

Required commands:

- `npm run css:build` from `BlazorAutoApp.Client`
- `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json`
- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore`
- `dotnet test .\BlazorAutoApp.sln -c Release --no-build`
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore`
- `git diff --check`

Required browser verification:

- Start local stack or app using the established local script.
- Verify anonymous home:
  - author shelf visible
  - login CTA visible
  - add book hidden
  - design demo link visible
- Verify authenticated home:
  - author shelf visible
  - user shelf visible
  - add book visible
  - user CRUD works
- Verify modal:
  - view book
  - edit book
  - add book
  - delete book
  - close
  - browser back
  - refresh survival
- Verify mobile:
  - shelf books readable
  - modal title readable
  - edit/add fields usable
  - no SVG clipping
- Verify design demos:
  - overview
  - detail
  - forced open
  - hover open

Done when:

- All command verification passes.
- Browser verification passes.
- Screenshots are saved for any design-sensitive pages changed.

Execution notes:

- `npm run css:build` passed.
- `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json` passed.
- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore` passed with 0 warnings and 0 errors.
- `dotnet test .\BlazorAutoApp.sln -c Release --no-build` passed: 71 passed, 5 skipped.
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore` passed.
- `git diff --check` passed.
- Docker app stack rebuilt and started successfully.
- Health check passed at `https://localhost:7186/health/ready`.
- Headed desktop Playwright passed for:
  - `Books_CanCreateViewEditCancelAndNavigateBack`
  - `SeededUser_BookcaseCrudSurvivesRefreshAndNavigation`
  - `HomePage_ReportsAssignedAutoAndHydratedRenderer`
- Headed mobile Playwright passed for both Books E2E tests at `390x844`.
- Visual snapshot E2E passed and refreshed screenshots under `BlazorAutoApp.Test/TestResults/Playwright/Snapshots`.
- For browser E2E, `E2E_BASE_URL` was set to `https://127.0.0.1:7186` because Docker publishes the app on IPv4 loopback.

## Phase 15: Remove `ForceRefresh` And Fix Freshness Properly

Status: done

Purpose:

Remove the forced-refresh escape hatch. The app should stay correct because the write path invalidates the right cache entries and the client state observes those writes predictably, not because the UI asks the server to skip cache behavior.

Tasks:

- Remove `ForceRefresh` from `GetBooksRequest` and `GetBookRequest`.
- Remove `forceRefresh` query construction and call-site arguments from `BooksClientService`.
- Remove force-refresh branches from `BooksServerService`; cache behavior should have one normal read path.
- Remove all UI calls that currently set `ForceRefresh = true`, including user bookcase loading and modal loading.
- Review `UserBookcaseState.ApplySavedBook`, reload, delete, and user-switch behavior so optimistic state remains a convenience, not a substitute for cache correctness.
- Confirm create invalidates all affected user list cache entries and any affected detail cache entries.
- Confirm update invalidates the user list cache entry and the edited detail cache entry.
- Confirm delete invalidates the user list cache entry and the deleted detail cache entry.
- Confirm author book reads are not accidentally tied to user-book invalidation.
- Confirm cross-node Redis pub/sub invalidation covers create, update, and delete without any bypass flag.
- Remove or rewrite tests that depend on `ForceRefresh`; replace them with invalidation-first tests.
- Add or update tests that prove create/update/delete remain visible after browser refresh, back/forward navigation, and modal reopen.
- Search docs and comments for `ForceRefresh` or `forceRefresh` and remove stale guidance.

Done when:

- `rg -n "ForceRefresh|forceRefresh" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Core BlazorAutoApp.Test` returns no app/test references.
- Books CRUD works without disappearing books after create, update, delete, refresh, navigation, and modal reopen.
- Cache tests prove invalidation rather than cache bypass.
- Cross-node invalidation tests still pass.

Verification:

- `rg -n "ForceRefresh|forceRefresh" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Core BlazorAutoApp.Test -S`
- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore`
- `dotnet test .\BlazorAutoApp.sln -c Release --no-build`
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore`
- `git diff --check`
- `docker compose up -d --build web`
- `Invoke-WebRequest -Uri https://127.0.0.1:7186/health/ready -SkipCertificateCheck`
- Headed desktop Books E2E against `https://127.0.0.1:7186`
- Headed mobile Books E2E at `390x844` against `https://127.0.0.1:7186`

Execution notes:

- Removed `ForceRefresh` from the Books request DTOs.
- Removed `forceRefresh` query-string construction from the client API service.
- Removed force-refresh branches from the server service; list and detail reads now use one normal cached path.
- Removed UI call-site bypasses from the user bookcase load and book modal detail load.
- Reworked cache tests so they assert normal reads stay cached until create/update/delete invalidates the affected list/item entries.
- Renamed the create integration assertion to `Create_Valid_IsReturnedByNormalListForSameUser`.
- Updated the older bookcase-fix plan so it no longer documents the removed bypass as current guidance.
- One combined mobile E2E run hit a transient Docker/Redis timeout and failed before the editor opened. Both mobile tests then passed individually, and the combined mobile Books E2E run passed on rerun.

## Recommended Execution Order

Status: done through Phase 15.

Recommended order if the plan is executed:

1. Phase 0 baseline.
2. Phase 1 stale folders and route slice cleanup.
3. Phase 2 API contract leakage.
4. Phase 3 shared validation rules.
5. Phase 6 modal split, because it reduces risk before UI refactors.
6. Phase 4 shared cover renderer.
7. Phase 5 cover artwork maintainability.
8. Phase 8 rendering performance.
9. Phase 7 accessibility controls.
10. Phase 10 state ownership.
11. Phase 9 server/cache cleanup.
12. Phase 11 design demo productization.
13. Phase 12 test structure cleanup.
14. Phase 13 migration/template review, only if explicitly approved.
15. Phase 14 final verification.
16. Phase 15 force-refresh removal and cache freshness proof.

## Non-Goals For This Plan

Status: done

- Do not touch deployment unless a later deployment-specific plan asks for it.
- Do not remove authentication or Identity.
- Do not remove the author bookcase unless requested.
- Do not remove live RNG in the bookcase. The user explicitly prefers it.
- Do not remove the design demo link without approval.
- Do not introduce a large frontend framework or non-Blazor rendering system.
- Do not replace Tailwind with custom CSS.
- Do not add architecture guardrails that make the template hard to fork.

## Open Questions Before Execution

Status: resolved during execution

These are not blockers for the review plan, but they matter before destructive or route-visible changes:

1. `/books/create`, `/books/{id}`, and `/books/{id}/edit` stay as compatibility routes into the query-modal flow.
2. Design demos stay public as a template showcase page with public-facing copy.
3. The author bookcase keeps the infinite-scroll illusion; the user bookcase now renders one pass and remains suitable for modest personal shelves.
4. Migration history was reviewed but not squashed. Squashing should be handled in a dedicated migration/deployment plan.
5. `ForceRefresh` was removed in Phase 15 and is not acceptable as a permanent cache escape hatch.
