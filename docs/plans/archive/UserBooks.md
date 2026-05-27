# User Books

## Goal

Split the current Books experience into two clearly different bookcases:

- A hardlocked, template-owned bookcase named **The Authors Bookcase**.
- An authenticated user's own editable bookcase below it.

Anonymous users should see the author bookcase and a prompt below it:

> Create your own bookcase by logging in.

Authenticated users should see two bookcases:

1. **The Authors Bookcase**: fixed template content, not user-editable.
2. **Your Bookcase**: only the signed-in user's books.

The editing table and all create/edit/delete actions must operate only on the signed-in user's own books.

## Current State

The app currently has one global Books data set:

- `BlazorAutoApp.Client/Features/Books/Pages/Index.razor` renders one bookcase from `BooksState`.
- `BlazorAutoApp/Features/Books/Services/BooksServerService.cs` lists every row in `Books`.
- `BlazorAutoApp/Features/Books/Seed/BookSeedExtensions.cs` writes local default books into the database.
- `Book` has no ownership field.
- `BooksCacheKeys` has global list/item cache keys.
- Create/update/delete require authentication, but list/details are public and not user-scoped.

That shape conflicts with the requested behavior because hardlocked author books and user-owned books are currently the same database concept.

## Core Decisions

- The author bookcase must be static template content, not database content.
- The author bookcase must not be editable, deletable, or affected by user CRUD.
- User books must be private to the authenticated user.
- The server must derive ownership from the authenticated principal. The client must never send an owner id.
- API reads for user books should require authentication.
- Details/edit/delete for a book owned by another user should return not found, not forbidden, to avoid leaking ids.
- Cache keys and invalidation must include the user id so one user's books cannot appear in another user's cache.
- Local default book seeding into `Books` should be removed or disabled because author books no longer live in the database.

## Phase 1 - Model Ownership

- [x] Status: Done
- [x] Add `OwnerUserId` to `Book`.
- [x] Add a relationship from `Book` to `ApplicationUser`.
- [x] Add an index on `OwnerUserId`.
- [x] Consider an index on `(OwnerUserId, Title)` only if useful for list sorting/search later.
- [x] Keep owner id out of public DTOs unless a test-only assertion needs database verification.
- [x] Add an EF migration for user-owned books.

Migration policy:

- [x] Remove known local seed/default books from `Books` during migration, because they move to static author bookcase content.
- [x] Decide whether to delete all existing unowned `Books` rows or leave `OwnerUserId` nullable for one migration.
- [x] Preferred template outcome: `OwnerUserId` is required after migration, and all persisted books are user-owned.

Validation:

- [x] `dotnet ef migrations add UserOwnedBooks ...`
- [x] `dotnet build BlazorAutoApp.sln`
- [x] Migration bundle still builds later, but deployment files are not part of this plan unless separately requested.

## Phase 2 - Server User Scope

- [x] Status: Done
- [x] Add a small current-user helper in the server project, likely in the Books or Login-adjacent infrastructure slice.
- [x] Resolve the current user id from `ClaimTypes.NameIdentifier`.
- [x] Make `BooksServerService` require an authenticated user for list/detail/create/update/delete.
- [x] On create, set `Book.OwnerUserId` from the current authenticated user.
- [x] On list, filter by `OwnerUserId`.
- [x] On details, update, and delete, query by both `Id` and `OwnerUserId`.
- [x] Return `null`/`false` for not-owned books so endpoints keep returning 404.
- [x] Keep URL normalization unchanged.

Endpoint changes:

- [x] Add `.RequireAuthorization()` to `GET /api/books`.
- [x] Add `.RequireAuthorization()` to `GET /api/books/{id}`.
- [x] Keep create/update/delete authorized.
- [x] Keep typed results and ProblemDetails behavior.

Validation:

- [x] Anonymous list/details return `401`.
- [x] Authenticated user A cannot read/update/delete user B's books.
- [x] User A list never includes user B's books.

## Phase 3 - User-Scoped Cache

- [x] Status: Done
- [x] Replace global list key `books:list` with user-scoped list keys, for example `books:user:{userId}:list`.
- [x] Replace item keys with user-scoped item keys, for example `books:user:{userId}:item:{bookId}`.
- [x] Replace global list tags with user-scoped list tags.
- [x] Keep a broad `books` tag only if still useful for operational full flush.
- [x] Update `BooksCacheKeys.ForChangedBook` to accept `userId` and `bookId`.
- [x] Ensure create/update/delete invalidate only the current user's list and changed item.
- [x] Update cross-node invalidation tests for per-user keys.

Validation:

- [x] Cache test proves user A and user B list caches are isolated.
- [x] Delete invalidation only removes the current user's affected item/list.
- [x] Cross-node invalidation still works for create/update/delete.

## Phase 4 - Hardlocked Author Bookcase

- [x] Status: Done
- [x] Move the fixed author/template books out of the database seed path.
- [x] Create a static author book list inside the Books feature slice.
- [x] Keep the current fixed titles:
  - `Ship`
  - `TraceBack`
  - `ImprovedDb`
  - `KinoJoin`
- [x] Keep the popular/common books already used for the public shelf unless design review says otherwise.
- [x] Render the author bookcase from this static list every time.
- [x] The author bookcase should not show edit/delete/view table actions.
- [x] Author bookcase books should either be non-links or link only to safe external URLs if URLs are added later.
- [x] Remove or disable `SeedLocalBooksAsync` so local defaults do not pollute user-owned books.
- [x] Remove `Books:SeedLocalDefaults` settings if no longer needed.

Validation:

- [x] Anonymous home always shows **The Authors Bookcase**.
- [x] Authenticated home always shows **The Authors Bookcase**.
- [x] Creating/deleting user books does not change **The Authors Bookcase**.
- [x] Database can be empty and the author bookcase still renders.

## Phase 5 - Homepage Layout

- [x] Status: Done
- [x] Keep the home route as Books.
- [x] Keep render mode diagnostics visible.
- [x] Rename the first shelf heading to **The Authors Bookcase**.
- [x] Render the author shelf first.
- [x] Below the author shelf, show anonymous CTA text:
  - `Create your own bookcase by logging in.`
- [x] Add login/register actions near that CTA if they fit the existing UI style.
- [x] When authenticated, replace the CTA with **Your Bookcase**.
- [x] Put the Add Book button in the user's bookcase section, not above the author shelf.
- [x] Render a second infinite bookcase from only the authenticated user's books.
- [x] If the user has no books, show an empty user-bookcase state without affecting the author shelf.
- [x] Keep hidden scrollbar/manual scrolling behavior for both shelves.
- [x] Avoid duplicating the shelf markup by extracting a local reusable component if the duplication gets large.

Recommended component shape:

- [x] Keep `BookSideView.razor`.
- [x] Add a small `BookcaseShelf.razor` inside `BlazorAutoApp.Client/Features/Books`.
- [x] Pass shelf title, items, link behavior, empty state, and test ids into `BookcaseShelf`.
- [x] Keep all components under the Books slice, not in a generic Client `Pages` folder.

Validation:

- [x] Anonymous desktop/mobile screenshots show one author shelf plus CTA.
- [x] Authenticated desktop/mobile screenshots show author shelf, user shelf, Add Book, and user's table.
- [x] Text does not overlap and shelves do not create page-level horizontal scrolling.

## Phase 6 - User Book Pages

- [x] Status: Done
- [x] Add `[Authorize]` to user book details if details are only for user-owned books.
- [x] Keep create/edit authorized.
- [x] Ensure details for a not-owned book shows the existing not-found behavior.
- [x] Ensure edit for a not-owned book shows not found and cannot save.
- [x] Ensure delete for a not-owned book returns 404.
- [x] After create/update/delete, navigate back to `/books` and refresh only the user's state.
- [x] Keep author bookcase independent from details/edit pages.

Validation:

- [x] User A can create/view/edit/delete their own book.
- [x] User A cannot view/edit/delete user B's book by URL.
- [x] Anonymous users are redirected for user-owned details/create/edit.

## Phase 7 - Tests

- [x] Status: Done
- [x] Update feature/integration tests for ownership.
- [x] Add list isolation test: user A sees only user A books.
- [x] Add details isolation test: user A gets 404 for user B book.
- [x] Add update isolation test: user A cannot update user B book.
- [x] Add delete isolation test: user A cannot delete user B book.
- [x] Update anonymous list/details tests to expect `401` if endpoints become authenticated.
- [x] Update cache tests for user-scoped keys.
- [x] Update cross-node cache invalidation tests for user-scoped invalidation.
- [x] Update E2E anonymous test:
  - sees **The Authors Bookcase**
  - sees CTA
  - does not see Add Book
  - does not see user table
- [x] Update E2E authenticated test:
  - sees **The Authors Bookcase**
  - sees **Your Bookcase**
  - Add Book creates into **Your Bookcase**
  - table only includes user's books
  - cleanup still removes E2E-created user books/users.
- [x] Update visual snapshots for the new layout.

Validation:

- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj --filter "Category!=E2E"`
- [x] headed E2E desktop
- [x] headed E2E mobile `390x844`
- [x] E2E cleanup leaves zero reserved E2E rows afterward.

## Phase 8 - Tailwind And Visual QA

- [x] Status: Done
- [x] Regenerate Tailwind CSS after markup changes.
- [x] Verify generated CSS is committed.
- [x] Review desktop screenshot.
- [x] Review mobile screenshot.
- [x] Verify both shelves animate and pause independently.
- [x] Verify manual horizontal scrolling works on hover/focus for both shelves.
- [x] Verify scrollbars remain hidden.
- [x] Verify no table/actions appear for the author shelf.

Validation:

- [x] `npm run css:build`
- [x] `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json`
- [x] `dotnet format BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`

## Acceptance Criteria

- [x] The first bookcase is always titled **The Authors Bookcase**.
- [x] The author bookcase is static and hardlocked.
- [x] The author bookcase does not use database rows.
- [x] Anonymous users see the author bookcase and `Create your own bookcase by logging in.`
- [x] Anonymous users do not see Add Book or the saved-books table.
- [x] Authenticated users see both the author bookcase and their own bookcase.
- [x] Add/edit/delete only affect the authenticated user's own bookcase.
- [x] The saved-books table lists only the authenticated user's own books.
- [x] User A cannot see or mutate user B's books through API or direct URL.
- [x] Cache keys and invalidation are user-scoped.
- [x] Local default book database seeding is removed or disabled.
- [x] Existing author SVG/book visuals remain high quality.
- [x] Headed E2E passes and cleans up after itself.

## Execution Verification

- [x] `npm run css:build`
- [x] `dotnet build .\BlazorAutoApp.sln`
- [x] `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category!=E2E"` passed with 63 tests.
- [x] `dotnet format .\BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`
- [x] Docker app stack rebuilt with `docker compose up -d --build web`.
- [x] `https://localhost:7186/health/ready` returned `Healthy`.
- [x] Headed desktop E2E passed with 4 tests.
- [x] Headed mobile E2E at `390x844` passed with 4 tests.
- [x] Local database cleanup check showed `0` E2E books, `0` E2E users, and `0` persisted books after the E2E run.

## Follow-Up Considerations

- Consider whether user books should ever be shareable by public URL. That is outside this plan.
- Consider whether author books should get curated external URLs. If so, keep them hardcoded and not user-editable.
- Consider whether account deletion should cascade user books. If `Book.OwnerUserId` has cascade delete, this is handled by EF/database.
- Consider whether the API route should be renamed from `/api/books` to `/api/user-books` later. This plan keeps existing routes to limit churn.
