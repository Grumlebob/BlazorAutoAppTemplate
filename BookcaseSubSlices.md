# Bookcase Sub-Slices

## Assessment

The Books feature is sliced at the feature level, but the new bookcase split is not yet as neat as it should be.

Current shape:

- `BlazorAutoApp.Client/Features/Books/AuthorBookcase.cs` is a flat static helper.
- `BookcaseShelf.razor`, `BookcaseBook.cs`, and `BookSideView.razor` are flat shared UI primitives.
- `Pages/Index.razor` still owns too much:
  - authentication state handling
  - anonymous login CTA
  - user book loading
  - user book mapping
  - user book deletion
  - user saved-books table markup
  - composition of both bookcases

This works, but it is not the clean subsliced shape implied by the product model. **The Authors Bookcase** and **Your Bookcase** are now different concepts with different ownership, data source, permissions, and UI behavior. They should be explicit subslices inside `Features/Books`.

## Goal

Refactor the Books client slice so the page is a thin composition shell and the two bookcases are explicit subslices:

- `AuthorBookcase`: static, hardlocked template bookcase.
- `UserBookcase`: authenticated, user-owned, editable bookcase.

Do this without changing routes, API behavior, cache behavior, persistence, deployment, or the visible user workflow.

## Proposed Target Structure

```text
BlazorAutoApp.Client/Features/Books/
  Pages/
    Index.razor
    Create.razor
    Details.razor
    Edit.razor

  AuthorBookcase/
    AuthorBookcase.razor
    AuthorBookcaseCatalog.cs

  UserBookcase/
    UserBookcase.razor
    UserBookcaseTable.razor
    UserBookcaseLoginPrompt.razor
    UserBookcaseBookMapper.cs

  Shared/
    BookcaseBook.cs
    BookcaseShelf.razor
    BookSideView.razor

  BooksClientService.cs
  _Imports.razor
```

Notes:

- Keep route pages in `Features/Books/Pages` because this repo already uses `Pages` within feature slices, and there is no root-level `Client/Pages` folder.
- Keep `BookSideView` and `BookcaseShelf` shared only within the Books feature. Do not promote them to app-wide shared UI.
- Keep server-side API, cache, persistence, and domain files where they are. The requested split is a client subslice cleanup, not a data model refactor.
- Prefer `AuthorBookcase`/`UserBookcase` spelling consistently. Treat `Bookcase` as one word in file and type names.

## Phase 1 - Establish Shared Bookcase UI Boundary

- [x] Status: Done
- [x] Move `BookcaseBook.cs` to `BlazorAutoApp.Client/Features/Books/Shared/BookcaseBook.cs`.
- [x] Move `BookcaseShelf.razor` to `BlazorAutoApp.Client/Features/Books/Shared/BookcaseShelf.razor`.
- [x] Move `BookSideView.razor` to `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`.
- [x] Update namespaces/usings so Razor discovery stays clean.
- [x] Keep these components free of author-specific or user-specific behavior.

Acceptance:

- [x] `BookcaseShelf` only knows how to render a shelf from `BookcaseBook` items.
- [x] `BookSideView` only knows visual book rendering.
- [x] No auth, API, user ownership, or static catalog logic is placed in `Shared`.

## Phase 2 - Create AuthorBookcase Subslice

- [x] Status: Done
- [x] Create `BlazorAutoApp.Client/Features/Books/AuthorBookcase/AuthorBookcaseCatalog.cs`.
- [x] Move the current hardcoded author/template book list from `AuthorBookcase.cs` into `AuthorBookcaseCatalog`.
- [x] Create `AuthorBookcase.razor`.
- [x] Make `AuthorBookcase.razor` render the fixed shelf using `BookcaseShelf`.
- [x] Keep author books non-editable and non-database-backed.
- [x] Delete the old flat `AuthorBookcase.cs` after references move.

Acceptance:

- [x] `Index.razor` can render the author shelf with a single `<AuthorBookcase />`.
- [x] Author book titles remain unchanged, including `Ship`, `TraceBack`, `ImprovedDb`, and `KinoJoin`.
- [x] Author bookcase has no dependency on `IBooksApi`, auth state, delete flow, or user persistence.

## Phase 3 - Create UserBookcase Subslice

- [x] Status: Done
- [x] Create `BlazorAutoApp.Client/Features/Books/UserBookcase/UserBookcase.razor`.
- [x] Move authenticated user loading state from `Index.razor` into `UserBookcase.razor`.
- [x] Inject `IBooksApi` and `IJSRuntime` inside `UserBookcase.razor`, because that component owns the user-owned book workflow.
- [x] Keep `[PersistentState]` for user books in `UserBookcase.razor`, not the page shell.
- [x] Create `UserBookcaseBookMapper.cs` for converting `Book` rows into `BookcaseBook` links if this keeps the component cleaner.
- [x] Create `UserBookcaseTable.razor` for the saved-books table and row actions.
- [x] Keep delete confirmation and refresh logic owned by the user bookcase subslice.

Acceptance:

- [x] User book loading/error/empty states are inside `UserBookcase`.
- [x] The saved-books table is not embedded in `Index.razor`.
- [x] Add/view/edit/delete still operate only on the authenticated user's books.
- [x] User bookcase still refreshes after delete.

## Phase 4 - Create Anonymous UserBookcase Prompt

- [x] Status: Done
- [x] Create `UserBookcaseLoginPrompt.razor` under `UserBookcase`.
- [x] Move the anonymous CTA text and login/register buttons out of `Index.razor`.
- [x] Keep exact visible text:
  - `Create your own bookcase by logging in.`
- [x] Keep existing `data-testid="bookcase-login-cta"` unless tests are intentionally updated.

Acceptance:

- [x] Anonymous users still see the author bookcase and CTA.
- [x] Anonymous users still do not see Add Book or the saved-books table.
- [x] The anonymous prompt is clearly part of the user-bookcase subslice, because it invites creation of the user's own bookcase.

## Phase 5 - Thin The Home Page

- [x] Status: Done
- [x] Reduce `Pages/Index.razor` to route-level composition:
  - page routes
  - page title
  - heading
  - render-mode badge
  - auth-state gate
  - `<AuthorBookcase />`
  - `<UserBookcase />` or `<UserBookcaseLoginPrompt />`
- [x] Keep route URLs unchanged:
  - `/`
  - `/books`
- [x] Keep render-mode diagnostics visible.
- [x] Avoid moving create/edit/details pages unless a later plan tackles CRUD page subslicing.

Acceptance:

- [x] `Index.razor` no longer contains user-book API calls.
- [x] `Index.razor` no longer contains delete logic.
- [x] `Index.razor` no longer contains saved-books table markup.
- [x] `Index.razor` reads as page composition, not feature behavior.

## Phase 6 - Imports And Namespace Hygiene

- [x] Status: Done
- [x] Update `Features/Books/_Imports.razor` with only the namespaces needed by child components.
- [x] Avoid broad imports that hide ownership boundaries.
- [x] Ensure the new folders do not require awkward fully qualified names.
- [x] Keep names internal where possible for C# helper types.

Acceptance:

- [x] Components compile without noisy duplicated `@using` blocks.
- [x] Helper classes are not accidentally public API unless Razor requires it.
- [x] The new folder structure is easy to navigate from Rider.

## Phase 7 - Test And Selector Review

- [x] Status: Done
- [x] Keep existing `data-testid` selectors stable unless there is a clear reason to change them.
- [x] Run Books E2E tests to ensure the component split did not break visible behavior.
- [x] Run non-E2E tests to ensure route/API assumptions remain intact.
- [x] Regenerate Tailwind CSS if moving markup changes generated classes.

Validation:

- [x] `npm run css:build`
- [x] `dotnet build .\BlazorAutoApp.sln`
- [x] `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category!=E2E"`
- [x] Headed E2E desktop for Books flow.
- [x] Headed E2E mobile `390x844` for Books flow.
- [x] `dotnet format .\BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`

## Explicit Non-Goals

- Do not touch deployment.
- Do not change API routes.
- Do not change EF migrations.
- Do not change cache invalidation strategy.
- Do not change the current SVG book designs.
- Do not introduce a generic app-wide `Shared` component library.
- Do not rename Books to another domain.

## Final Acceptance Criteria

- [x] `AuthorBookcase` is a real client subslice under `Features/Books/AuthorBookcase`.
- [x] `UserBookcase` is a real client subslice under `Features/Books/UserBookcase`.
- [x] Shared shelf primitives live under `Features/Books/Shared`.
- [x] `Index.razor` is thin and only composes the page.
- [x] Existing behavior remains unchanged for anonymous and authenticated users.
- [x] Tests and headed E2E pass.

## Execution Verification

- [x] `npm run css:build`
- [x] `dotnet build .\BlazorAutoApp.sln`
- [x] `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category!=E2E"` passed with 63 tests.
- [x] Docker app stack rebuilt with `docker compose up -d --build web`.
- [x] `https://localhost:7186/health/ready` returned `Healthy`.
- [x] Headed desktop E2E passed with 4 tests.
- [x] Headed mobile E2E at `390x844` passed with 4 tests.
- [x] `dotnet format .\BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`
- [x] Local database cleanup check showed `0` E2E books, `0` E2E users, and `0` persisted books after the E2E run.
