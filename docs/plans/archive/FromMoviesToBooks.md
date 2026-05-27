# From Movies To Books

## Goal

Convert the template app from a Movies sample domain to a Books sample domain.

The finished app should feel intentionally book-focused:

- Home page is Books-first.
- A book has `Title`, `Author`, and `Rating`.
- The home page keeps the render-mode diagnostics visible because this is a Blazor template.
- The primary visual should be an infinite horizontally scrolling bookcase.
- Books should render as inline SVG book spines, not bitmap images.
- Hovering or focusing a book should slightly tip it, like a book being pulled from a shelf.
- Old Movies routes, API paths, visible text, test names, and code concepts should not remain in the active app.

## Explicit Non-Goals

- Do not touch `Deployment/**` in this plan.
- Do not rename the old `ship` deployment naming in this plan.
- Do not modify LocalCluster Ansible, deployment compose files, deployment scripts, or deployment docs in this plan.
- Do not add upload/image/media functionality.
- Do not add external image assets for books; the bookcase should be SVG/CSS.
- Do not keep `/movies` or `/api/movies` compatibility routes unless a later decision explicitly asks for legacy support.

## Current Inventory

Active Movies surfaces found outside deployment:

- `BlazorAutoApp.Core/Features/Movies`
  - `Movie` domain type.
  - `IMoviesApi`.
  - Create, update, get, list, delete request/response DTOs.
- `BlazorAutoApp/Features/Movies`
  - Minimal API endpoints under `/api/movies`.
  - `MoviesServerService`.
  - cache keys/options under `Movies`.
  - EF entity configuration for `Movie`.
- `BlazorAutoApp.Client/Features/Movies`
  - home/list page at `/` and `/movies`.
  - create, edit, details pages.
  - `MoviesClientService`.
  - test ids and user-facing text using movie terminology.
- `BlazorAutoApp/Infrastructure/Persistence`
  - `DbSet<Movie> Movies`.
  - model configuration registration.
  - migrations/model snapshot currently contain a `Movies` table with `Director`.
- App composition/config
  - `Program.cs` registers/maps Movies.
  - `BlazorAutoApp.Client/Program.cs` registers `IMoviesApi`.
  - `appsettings.json` and `appsettings.Docker.json` contain `Cache:Movies`.
- App shell
  - nav branding uses `M` and `Movies`.
- Tests
  - integration tests under `BlazorAutoApp.Test/Features/Movies`.
  - Playwright E2E under `BlazorAutoApp.Test/E2E/Features/Movies`.
  - architecture/rate-limit/endpoint tests reference `/api/movies`.
- Docs
  - `README.md`, `overview.md`, `TemplateCustomization.md`, and historical docs/plans reference Movies.

Historical plans under `docs/plans` may mention Movies as old history. They can be updated only if they are meant to describe current state. Do not churn old status/history text unless it would confuse template users.

## Naming Decisions

Use these names consistently:

- Domain entity: `Book`.
- Table: `Books`.
- Key property: `Id`.
- Fields: `Title`, `Author`, `Rating`.
- Core namespace: `BlazorAutoApp.Core.Features.Books`.
- Server namespace: `BlazorAutoApp.Features.Books`.
- Client namespace: `BlazorAutoApp.Client.Features.Books`.
- Contract: `IBooksApi`.
- Server implementation: `BooksServerService`.
- Client implementation: `BooksClientService`.
- Cache options: `BooksCacheOptions`.
- Cache keys: `BooksCacheKeys`.
- Configuration section: `Cache:Books`.
- API group: `/api/books`.
- UI routes:
  - `/` and `/books` for the bookcase home/list page.
  - `/books/create` for create.
  - `/books/{id:int}` for details.
  - `/books/{id:int}/edit` for edit.

No active code should use `Movie`, `Movies`, `Director`, `/movies`, `/api/movies`, `movie-*` test ids, or `Cache:Movies` after execution.

## Data And Migration Strategy

Recommended default for this template: produce a clean Books schema in the active EF model and migrations.

Because this repository is still being shaped as a template and the requested end state is not Movies-based, the cleanest final state is:

- `Books` table in the current model.
- `Author` column instead of `Director`.
- no active app migration snapshot references to `Movie`.
- local Docker database reset after the migration change.

Execution needs one deliberate decision before changing migrations:

- If there is no data to preserve, replace the current template initial migration with a fresh Books initial schema and reset local Docker volumes with `.\RunLocal.ps1 -ResetDatabase`.
- If preserving data matters, add a normal migration that renames `Movies` to `Books` and `Director` to `Author`, then accept that old migration history may still contain `Movies` references.

For this template, prefer the first option unless the user says to preserve data.

Deployment is not part of this plan, but migration changes can affect the old deployment flow later. The follow-up section covers that.

## Bookcase UI Design

The home page should stop feeling like a plain CRUD table and become a useful bookcase.

Recommended structure:

- Keep the page in the `Books` vertical slice.
- Keep `RenderModeBadge` visible near the top.
- Provide a clear `Add Book` action.
- Show an infinite horizontal shelf/bookcase as the first major visual.
- Render each book with an inline SVG component, for example `BookSpine.razor`.
- Use no external book cover images.
- Keep CRUD actions accessible from each book.

Book SVG details:

- Use a stable `viewBox`, for example `0 0 72 132`.
- Draw a vertical spine rectangle with subtle bevel/edge shapes.
- Derive a small varied color palette from book id/title so the shelf is not one-note.
- Render the title text on the spine using SVG `<text>`.
- Keep titles readable by truncating or splitting into short lines.
- Include `aria-label` on the anchor/button wrapping each SVG.
- Use a `<title>` element inside the SVG for assistive technology.

Infinite scrolling behavior:

- Use CSS animation on a repeated inline flex track.
- Duplicate the current book collection enough times to make a seamless loop.
- Pause the track on hover/focus so users can select a book.
- Respect `prefers-reduced-motion: reduce` by disabling the animation.
- Avoid JS timers for scrolling unless CSS cannot meet the behavior.
- Avoid layout shifts when books are added/removed.

Hover/focus behavior:

- Each book should slightly rotate and translate upward on hover/focus.
- Use `transform-origin: bottom center`.
- Keep the movement small enough to avoid overlap or clipping.
- Include `:focus-visible` styling for keyboard users.

Empty state:

- If no books exist, the page should still look intentional.
- Show an empty shelf with a small set of non-persisted placeholder SVG spines or an empty shelf rail.
- Keep the copy short, for example `No books saved yet.`
- Provide `Add Book` near the empty state.

Details/forms:

- Create/edit forms should use `Author`, not `Director`.
- Details page should show `Author: ...`.
- Validation messages and problem titles should say `Book`.

## Execution Plan

### Phase 1 - Safety Baseline

- [x] Status: Done
- [x] Confirm working tree status before edits.
- [x] Confirm no deployment files will be edited.
- [x] Run a baseline build if the repo is already expected to compile.
- [x] Keep a focused list of files renamed/changed.

Validation:

- [x] `dotnet build BlazorAutoApp.sln`

### Phase 2 - Rename Core Domain And Contracts

- [x] Status: Done
- [x] Rename `BlazorAutoApp.Core/Features/Movies` to `Books`.
- [x] Rename `Movie` to `Book`.
- [x] Rename `Director` to `Author`.
- [x] Rename request/response DTOs:
  - `CreateMovieRequest` to `CreateBookRequest`.
  - `CreateMovieResponse` to `CreateBookResponse`.
  - `GetMovieRequest` to `GetBookRequest`.
  - `GetMovieResponse` to `GetBookResponse`.
  - `GetMoviesRequest` to `GetBooksRequest`.
  - `GetMoviesResponse` to `GetBooksResponse`.
  - `UpdateMovieRequest` to `UpdateBookRequest`.
  - `DeleteMovieRequest` to `DeleteBookRequest`.
- [x] Rename `IMoviesApi` to `IBooksApi`.
- [x] Update namespaces and usings.
- [x] Keep validation equivalent:
  - title required, max 200.
  - author optional, max 200.
  - rating range 0-10.

Validation:

- [x] `dotnet build BlazorAutoApp.Core/BlazorAutoApp.Core.csproj`

### Phase 3 - Rename Server Feature Slice

- [x] Status: Done
- [x] Rename `BlazorAutoApp/Features/Movies` to `Books`.
- [x] Rename endpoint extension to `MapBookEndpoints`.
- [x] Change API group from `/api/movies` to `/api/books`.
- [x] Change endpoint names/tags to Books:
  - `ListBooks`
  - `GetBook`
  - `CreateBook`
  - `UpdateBook`
  - `DeleteBook`
- [x] Rename `MoviesServerService` to `BooksServerService`.
- [x] Rename cache types/options/keys to Books.
- [x] Change cache keys from `movies:*` to `books:*`.
- [x] Change logs and problem details from Movie to Book.
- [x] Register `AddBooksFeature` in `Program.cs`.
- [x] Map book endpoints in `Program.cs`.

Validation:

- [x] `dotnet build BlazorAutoApp/BlazorAutoApp.csproj`

### Phase 4 - Persistence And Migrations

- [x] Status: Done
- [x] Change `AppDbContext` from `DbSet<Movie> Movies` to `DbSet<Book> Books`.
- [x] Rename `MovieEntityTypeConfiguration` to `BookEntityTypeConfiguration`.
- [x] Configure `Author` max length 200.
- [x] Update EF model snapshot/migration according to the chosen migration strategy.
- [x] If using clean template migration:
  - [x] replace current initial migration with a clean Books initial schema.
  - [x] verify no active migration/model snapshot references `Movie`, `Movies`, or `Director`.
  - [x] reset local Docker DB before local app verification.
- [x] Preserving migration path: Not used for this template reset.
  - [x] No rename-based preserving migration was added because the accepted strategy was a fresh Books initial schema.

Validation:

- [x] `dotnet ef migrations list --project BlazorAutoApp --startup-project BlazorAutoApp`
- [x] `dotnet build BlazorAutoApp.sln`
- [x] local Docker reset if clean initial migration was chosen:
  - `.\RunLocal.ps1 -ResetDatabase -NoBrowser`

### Phase 5 - Client Feature Slice And Routes

- [x] Status: Done
- [x] Rename `BlazorAutoApp.Client/Features/Movies` to `Books`.
- [x] Rename `MoviesClientService` to `BooksClientService`.
- [x] Update client DI registration to `IBooksApi`.
- [x] Change HTTP calls to `/api/books`.
- [x] Change routes:
  - `/` and `/books`.
  - `/books/create`.
  - `/books/{id:int}`.
  - `/books/{id:int}/edit`.
- [x] Remove `/movies` page route.
- [x] Update all user-facing labels to Books/Book/Author.
- [x] Update all test ids to `book-*`.
- [x] Update navigation brand from `M Movies` to a book-focused identity, for example `B Books`.

Validation:

- [x] `dotnet build BlazorAutoApp.sln`

### Phase 6 - Build The Infinite SVG Bookcase Home Page

- [x] Status: Done
- [x] Replace the current table-first list with a bookcase-first home page.
- [x] Add an inline SVG book component in the Books slice.
- [x] Add a shelf/track component or local markup for repeated book spines.
- [x] Keep CRUD affordances:
  - view/select a book.
  - create a book.
  - edit/delete available without hiding core functionality.
- [x] Keep `RenderModeBadge` visible and readable.
- [x] Keep the layout responsive on mobile and desktop.
- [x] Add CSS for:
  - infinite horizontal scroll.
  - pause on hover/focus.
  - tipped-book hover/focus transform.
  - reduced-motion behavior.
  - stable book dimensions.
- [x] Ensure the UI does not use decorative image assets.
- [x] Ensure the Add Book button remains readable after the earlier global link styling fix.

Validation:

- [x] Run local app with Docker.
- [x] Manually inspect `https://localhost:7186`.
- [x] Confirm home page looks like an infinite bookcase.
- [x] Confirm hover/focus tips individual books.
- [x] Confirm render-mode badge remains visible.
- [x] Confirm create, view, edit, delete still work.

### Phase 7 - Tests

- [x] Status: Done
- [x] Rename test folders/namespaces from Movies to Books.
- [x] Update integration tests to use `/api/books`.
- [x] Update test data generator to `BookDataGenerator`.
- [x] Update endpoint surface tests.
- [x] Update rate limiting tests from `/api/movies` to `/api/books`.
- [x] Update cache tests to Books.
- [x] Update cross-node cache invalidation tests to Books.
- [x] Update E2E flow to Books routes and `book-*` test ids.
- [x] Do not add a dedicated visual hover assertion unless explicitly requested.
- [x] Keep visible Playwright behavior as the preferred E2E mode.

Validation:

- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- [x] visible E2E with:
  - `RUN_E2E=1`
  - `E2E_BASE_URL=https://localhost:7186`
  - no `E2E_HEADLESS=1`

### Phase 8 - Documentation

- [x] Status: Done
- [x] Update `README.md` to describe Books as the sample domain.
- [x] Update `overview.md` with Books architecture, routes, API endpoints, cache keys, and render-mode flow.
- [x] Update `TemplateCustomization.md` from Movies sample domain to Books sample domain.
- [x] Update `TESTING.md` if test names/routes are listed.
- [x] Update `HowToRunLocally.md` only if migration reset instructions need to mention the fresh Books migration.
- [x] Do not edit deployment docs in this plan.

Validation:

- [x] `rg -n "\bMovie\b|\bMovies\b|\bmovie\b|\bmovies\b|\bDirector\b|\bdirector\b|/api/movies|/movies|Cache__Movies" --glob '!Deployment/**' --glob '!docs/plans/**' --glob '!FromMoviesToBooks.md' --glob '!**/bin/**' --glob '!**/obj/**' --glob '!**/node_modules/**'`
- [x] Review every remaining hit.

### Phase 9 - Full Verification

- [x] Status: Done
- [x] Build solution.
- [x] Run full test project.
- [x] Run formatting verification.
- [x] Run local Docker app.
- [x] If migration was cleaned/squashed, run with `-ResetDatabase`.
- [x] Open home page and exercise Books CRUD.
- [x] Run visible E2E.
- [x] Confirm Docker health is ready.
- [x] Confirm no active app routes or API endpoints still expose Movies.
- [x] Confirm deployment files were not changed.

Validation commands:

- [x] `dotnet build BlazorAutoApp.sln`
- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- [x] `dotnet format --verify-no-changes`
- [x] `.\RunLocal.ps1 -ResetDatabase -NoBrowser`
- [x] `$env:RUN_E2E='1'`
- [x] `$env:E2E_BASE_URL='https://localhost:7186'`
- [x] `Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue`
- [x] `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"`

## Acceptance Criteria

- [x] Home page is Books, not Movies.
- [x] Home page has an infinite scrolling SVG bookcase.
- [x] Hover/focus tips a book spine slightly.
- [x] Books can be created, viewed, edited, and deleted.
- [x] Book fields are `Title`, `Author`, and `Rating`.
- [x] Render-mode diagnostics remain visible on the home page.
- [x] `/books` works.
- [x] `/movies` does not exist unless explicitly added later.
- [x] `/api/books` works.
- [x] `/api/movies` does not exist unless explicitly added later.
- [x] Active code outside historical plans and this plan has no Movies naming.
- [x] Tests pass.
- [x] Visible E2E passes.
- [x] Deployment files remain untouched.

## Risks And Mitigations

- EF migration cleanup can break existing local volumes.
  - Mitigation: use `.\RunLocal.ps1 -ResetDatabase` for local Docker after a clean migration reset.
- Old deployment DBs may have `Movies` tables or old migration history.
  - Mitigation: do not deploy until the follow-up deployment cleanup plan is executed.
- Infinite scrolling can be distracting.
  - Mitigation: pause on hover/focus and respect reduced motion.
- SVG text can become unreadable on tiny spines.
  - Mitigation: use fixed dimensions, truncation, tooltips/labels, and details page links.
- Renaming the feature touches many files.
  - Mitigation: work by vertical slice, build after each phase, and run full tests before finishing.

## Follow-Up Plan To Create Later

Create a separate deployment-focused plan after this one, because deployment is intentionally out of scope here.

Suggested plan name:

```text
DeploymentShipToTemplateCleanup.md
```

Follow-up items:

- Rename old `ship` deployment naming to match the template/app naming.
- Review `Deployment/LocalCluster` for Books/API/migration assumptions.
- Review deployment DB migration strategy after the Movies-to-Books conversion.
- Decide whether deployed databases should be reset or migrated.
- Update deployment docs after the Books migration is stable.
- Verify CI/CD artifact names, migration bundle names, compose service names, GHCR image names, Ansible variables, and environment files.
- Run deployment audit scripts after the deployment rename.
- Confirm no deployment value was accidentally removed while renaming.
- Review whether LocalCluster should keep being part of the public template or be clearly marked as optional deployment infrastructure.

Other follow-up findings to review after execution:

- Re-scan active code for old sample-domain terms after the deployment plan.
- Consider extracting shared button/form styles so future sample-domain swaps do not repeat long Tailwind class strings.
- Consider adding a small design-system note for template UI primitives.
- Consider whether docs should include a short "rename Books to your domain" recipe for fork users.
