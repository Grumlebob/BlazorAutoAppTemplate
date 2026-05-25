# Books Auth And Shelf Refresh

## Goal

Refine the Books template so anonymous users see a polished public bookcase, while authenticated users can manage saved books.

Requested changes:

- Hide `Add Book` unless the user is logged in.
- Hide the `Saved books` management list unless the user is logged in.
- Replace `Rating` with an optional `Url` on the Book model.
- Make the SVG book spines more detailed and visually stronger.
- Add three SVG spine variants and choose between them deterministically/randomly per book.
- Seed local development with recognizable common books.

## Implementation Summary

- Books now use `Title`, optional `Author`, and optional absolute HTTP/HTTPS `Url`.
- Anonymous users see the render-mode badge and public SVG bookcase only.
- Authenticated users see `Add Book`, `Saved books`, edit, and delete.
- Create, update, and delete API endpoints require authorization; read endpoints remain public.
- The bookcase uses three deterministic inline SVG spine variants.
- Development and Docker local runs seed ten common books after startup migrations.
- Deployment files were intentionally left untouched.

## Non-Goals

- Do not touch `Deployment/**` in this plan.
- Do not rename old deployment/`ship` assets in this plan.
- Do not add book cover images or upload/media functionality.
- Do not add per-user ownership unless explicitly requested later.
- Do not add legacy `Rating` compatibility fields after the schema is changed.
- Do not restore `/movies` or `/api/movies`.

## Initial Findings

- `Rating` exists in the active domain, DTOs, EF migration/snapshot, API service, client forms, details page, bookcase page, SVG component, tests, and docs.
- `Add Book` is currently visible to anonymous users on the home page.
- `Saved books` is currently visible to anonymous users on the home page.
- Create, edit, and delete APIs are currently reachable through `/api/books` without endpoint-level authorization.
- Books are globally stored, not tied to an individual user.
- There is no app-level local seed path for default books.
- Current `BookSpine.razor` has one visual shape and displays rating text.

## Product Decisions

Use this behavior unless changed before execution:

- Anonymous home page:
  - Show the title, subtitle, render-mode badge, and public SVG bookcase.
  - Do not show `Add Book`.
  - Do not show `Saved books`.
  - If no database books exist yet, show seeded/placeholder public books in the shelf.
- Authenticated home page:
  - Show `Add Book`.
  - Show `Saved books` management list.
  - Allow view, edit, and delete actions.
- Book storage:
  - Keep Books as a global template sample domain for now.
  - Do not introduce `UserId`, ownership filtering, or per-account saved libraries in this pass.
- API security:
  - Keep list/details reads public so the public bookcase can render.
  - Require authorization for create, update, and delete endpoints.
  - Protect create/edit pages with `[Authorize]`.
  - Details can remain public unless later requested otherwise.
- URL:
  - Add nullable `Url` to Book.
  - Validate as an absolute HTTP/HTTPS URL when supplied.
  - Use a practical max length, recommended `2048`.
  - Display it as an external link with `target="_blank"` and `rel="noopener noreferrer"`.

## Data And Migration Strategy

Recommended for this template: refresh the current clean initial schema again.

Because this app has already been intentionally reset as a template and there is no real data to preserve right now:

- Replace the `Rating` column with nullable `Url` in the active initial migration and EF model snapshot.
- Reset local Docker database after migration changes with:

```powershell
.\RunLocal.ps1 -ResetDatabase -NoBrowser
```

Do not add a preserving migration unless the requirement changes to keep existing book rows.

## Local Seed Strategy

Add local seed infrastructure under the server app, preferably in the Books vertical slice:

- Suggested path: `BlazorAutoApp/Features/Books/Seed/BookSeedData.cs`.
- Suggested extension: `SeedLocalBooksAsync`.
- Call after migrations complete.
- Only run for local/development by config, not unconditionally in production.
- Add an app setting such as:

```json
"Books": {
  "SeedLocalDefaults": true
}
```

Seed behavior:

- Idempotent by title and author.
- Do not duplicate rows if the app starts multiple times.
- Keep seed data small, recognizable, and neutral.
- Suggested seed books:
  - `Pride and Prejudice` by Jane Austen
  - `1984` by George Orwell
  - `The Hobbit` by J.R.R. Tolkien
  - `To Kill a Mockingbird` by Harper Lee
  - `The Great Gatsby` by F. Scott Fitzgerald
  - `Moby-Dick` by Herman Melville
  - `Jane Eyre` by Charlotte Bronte
  - `Frankenstein` by Mary Shelley
  - `The Odyssey` by Homer
  - `Don Quixote` by Miguel de Cervantes

Use optional URLs only when stable and low-risk. It is acceptable to seed `Url = null` for all default books.

## SVG Bookcase Design

Improve `BookSpine.razor` without adding external assets.

Three variants:

- Classic clothbound spine:
  - raised bands.
  - inset label plaque.
  - subtle paper edge.
  - vertical highlight.
- Modern paperback spine:
  - bold color blocks.
  - author strip.
  - small publisher mark.
  - diagonal accent or horizontal bands.
- Antique hardback spine:
  - darker base.
  - gold linework.
  - ornament corners.
  - title cartouche.

Selection:

- Add a `Variant` or derive it from `Seed % 3`.
- Keep deterministic output so server prerender and hydrated client match.
- Keep text truncation deterministic.
- Do not use random values during render.

Accessibility and layout:

- Keep stable dimensions and viewBox.
- Include `<title>` or external `aria-label`.
- Ensure text remains within spine bounds on mobile.
- Continue hover/focus tipping behavior.
- Respect reduced motion.
- Pause the infinite bookcase on hover/focus.
- Do not let tipped books overlap surrounding UI.

## Execution Plan

### Phase 1 - Baseline And Scope Guard

- [x] Status: Done
- [x] Capture working tree status.
- [x] Confirm `Deployment/**` remains untouched.
- [x] Run baseline build.
- [x] Run current test suite if the repo is expected to be green.

Validation:

- [x] `dotnet build BlazorAutoApp.sln`
- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`

### Phase 2 - Replace Rating With Optional Url

- [x] Status: Done
- [x] Update `Book` domain:
  - remove `Rating`.
  - add `string? Url`.
- [x] Update create/update DTOs:
  - remove `Rating`.
  - add nullable `Url`.
  - add URL validation.
  - add max length validation.
- [x] Update create/get response DTOs to expose `Url`.
- [x] Update `IBooksApi` consumers and implementations.
- [x] Update `BooksServerService` create/update/projection logic.
- [x] Update tests and test data generator.

Validation:

- [x] `rg -n "\bRating\b|book-rating|rating" BlazorAutoApp BlazorAutoApp.Core BlazorAutoApp.Client BlazorAutoApp.Test`
- [x] Remaining hits reviewed and removed unless historical docs/plans.

### Phase 3 - Persistence And Migration Refresh

- [x] Status: Done
- [x] Update `BookEntityTypeConfiguration`:
  - configure `Url` as optional.
  - max length `2048`.
- [x] Update initial migration to create nullable `Url` instead of required `Rating`.
- [x] Update `AppDbContextModelSnapshot`.
- [x] Verify no active EF artifacts contain `Rating`.

Validation:

- [x] `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`
- [x] `dotnet build BlazorAutoApp.sln`

### Phase 4 - Auth-Aware Home UI

- [x] Status: Done
- [x] Wrap `Add Book` in `AuthorizeView`.
- [x] Render `Saved books` only in the authorized state.
- [x] Keep public bookcase visible for anonymous users.
- [x] Ensure anonymous users see a polished public state, not an empty admin page.
- [x] Remove rating text from the list and replace with URL display if present.
- [x] Keep render-mode badge visible for all users.
- [x] Confirm mobile layout remains clean.

Validation:

- [x] Anonymous home page has no `Add Book`.
- [x] Anonymous home page has no `Saved books`.
- [x] Authenticated home page has `Add Book`.
- [x] Authenticated home page has `Saved books`.

### Phase 5 - Protect Management Flow

- [x] Status: Done
- [x] Add `[Authorize]` to create/edit pages.
- [x] Keep details public unless requirements change.
- [x] Require authorization for POST, PUT, DELETE `/api/books`.
- [x] Keep GET `/api/books` and GET `/api/books/{id}` public.
- [x] Update endpoint tests for `401`/redirect behavior as appropriate.
- [x] Update E2E Books flow to log in before creating/editing/deleting.

Validation:

- [x] Anonymous POST `/api/books` is rejected.
- [x] Anonymous PUT `/api/books/{id}` is rejected.
- [x] Anonymous DELETE `/api/books/{id}` is rejected.
- [x] Authenticated Books CRUD still works.

### Phase 6 - Richer Three-Variant SVG Book Spines

- [x] Status: Done
- [x] Redesign `BookSpine.razor` with three deterministic variants.
- [x] Remove rating display from the SVG.
- [x] Use title, author, and optional URL presence as visual metadata.
- [x] Add richer details:
  - spine bevels.
  - labels.
  - bands.
  - ornaments.
  - paper-edge highlights.
- [x] Keep all drawing inline SVG.
- [x] Keep color palette varied and not one-note.
- [x] Keep hover/focus tipped-book behavior.
- [x] Verify text does not overflow spines.

Validation:

- [x] Desktop screenshot review.
- [x] Mobile screenshot review.
- [x] Reduced-motion behavior remains supported.

### Phase 7 - Local Default Book Seeding

- [x] Status: Done
- [x] Add seed data inside the Books vertical slice.
- [x] Add config-driven local seed toggle.
- [x] Seed after migrations.
- [x] Make seed idempotent.
- [x] Keep seed disabled or explicitly opt-in outside local/development.
- [x] Reset local Docker DB after schema/seed change.

Validation:

- [x] Fresh local run shows default books in the bookcase.
- [x] Restarting local app does not duplicate seeded books.

### Phase 8 - Forms, Details, And Client Service

- [x] Status: Done
- [x] Replace rating fields in create/edit pages with optional URL input.
- [x] Update details page to show URL when present.
- [x] Update validation messages.
- [x] Update test IDs from `book-rating` to `book-url`.
- [x] Ensure create/edit submit behavior remains unchanged.
- [x] Ensure cancel/back behavior remains correct.

Validation:

- [x] Create book with no URL works.
- [x] Create book with valid URL works.
- [x] Invalid URL shows validation error.
- [x] Details page external link is correct when URL exists.

### Phase 9 - Tests And Visual E2E

- [x] Status: Done
- [x] Update integration tests for URL model.
- [x] Update caching tests for URL changes and invalidation.
- [x] Update cross-node invalidation tests.
- [x] Update architecture tests if endpoint auth metadata is asserted.
- [x] Update Playwright Books tests to authenticate before management actions.
- [x] Add checks that anonymous home hides management UI.
- [x] Keep E2E visible by default when manually run.
- [x] Do not add headless-only E2E checks.

Validation:

- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- [x] visible E2E desktop with `RUN_E2E=1`
- [x] visible E2E mobile with `RUN_E2E=1`, `E2E_VIEWPORT_WIDTH=390`, `E2E_VIEWPORT_HEIGHT=844`

### Phase 10 - Documentation

- [x] Status: Done
- [x] Update `README.md`:
  - Books have title, author, optional URL.
  - management actions require login.
  - local seed defaults.
- [x] Update `overview.md` architecture and API behavior.
- [x] Update `TemplateCustomization.md`.
- [x] Update `BlazorAutoApp.Test/TESTING.md` if E2E flow changes.
- [x] Update this plan with completed statuses.

Validation:

- [x] `rg -n "\bRating\b|book-rating|rating" --glob '!docs/plans/**' --glob '!**/bin/**' --glob '!**/obj/**'`
- [x] Remaining hits reviewed.

### Phase 11 - Full Verification

- [x] Status: Done
- [x] Build solution.
- [x] Run full tests.
- [x] Run formatting verification.
- [x] Run local Docker stack with reset.
- [x] Check anonymous home page.
- [x] Check authenticated CRUD flow.
- [x] Check desktop and mobile screenshots.
- [x] Check `/books` and `/api/books`.
- [x] Check `/movies` and `/api/movies` are still gone.
- [x] Confirm `Deployment/**` unchanged.

Validation:

- [x] `dotnet build BlazorAutoApp.sln`
- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- [x] `dotnet format BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`
- [x] `.\RunLocal.ps1 -ResetDatabase -NoBrowser`
- [x] visible desktop E2E
- [x] visible mobile E2E

## Acceptance Criteria

- [x] Anonymous users cannot see `Add Book`.
- [x] Anonymous users cannot see `Saved books`.
- [x] Logged-in users can see `Add Book`.
- [x] Logged-in users can see `Saved books`.
- [x] Book model has `Title`, `Author`, and optional `Url`.
- [x] No active app code uses `Rating`.
- [x] SVG bookcase has three deterministic visual spine variants.
- [x] Home page looks polished with local default books.
- [x] Local seed is idempotent.
- [x] Create/update/delete book endpoints require authentication.
- [x] Read endpoints remain public.
- [x] Tests pass.
- [x] Visible E2E passes desktop and mobile.
- [x] Deployment files remain untouched.

## Risks And Mitigations

- Auth gating only in UI would leave write APIs open.
  - Mitigation: require auth on mutation endpoints as well.
- Deterministic SVG variants could mismatch during hydration if random values are used.
  - Mitigation: derive variants from stable seed values only.
- Local seed could leak into production.
  - Mitigation: make seeding environment/config gated.
- Reset migration can break existing local data.
  - Mitigation: this template currently has no real data; run local DB reset and document it.
- Optional URL validation can reject useful but non-HTTP values.
  - Mitigation: accept only absolute HTTP/HTTPS URLs for predictable browser behavior.

## Follow-Up Findings

- Deployment still has old `ship` naming and should be handled in the separate deployment cleanup plan.
- If Books should become a per-user library later, add `OwnerUserId`, ownership filters, and per-user authorization tests.
- Consider a small reusable auth-aware CRUD page pattern after this settles.

