# Side View Bookcase Redesign

## Goal

Redesign the public Books home visual so the SVGs are no longer narrow bookbacks/spines.

The bookcase should show larger side-view books with enough face area for titles to be displayed neatly. The result should still feel like an infinite scrolling bookcase, but each book should read more like a stylized book object than a thin spine.

Requested changes:

- Replace bookback/spine-style SVGs with side-view book SVGs.
- Make each book larger.
- Give the title enough room to render neatly.
- Keep three deterministic visual variants.
- Add fixed seeded books titled:
  - `Ship`
  - `TraceBack`
  - `ImprovedDb`
  - `KinoJoin`

## Non-Goals

- Do not touch `Deployment/**`.
- Do not change Books back into Movies or any other domain.
- Do not add upload, image, cover-art, or media functionality.
- Do not use raster assets; the book visuals remain inline SVG.
- Do not remove render-mode diagnostics from the home page.
- Do not make management controls visible to anonymous users.

## Current Findings

- `BookSpine.razor` is the current SVG component and still models a vertical spine/bookback.
- CSS uses `book-spine-*` class names.
- The home page uses `data-testid="book-spine"`.
- The seeded local defaults currently contain ten common books.
- The current title layout is constrained by a narrow `72 x 132` SVG viewBox.

## Design Direction

Replace the visual metaphor:

- Current: narrow upright book spine.
- Target: larger side-view book object with a broad readable face.

Recommended SVG shape:

- Use a wider viewBox, for example `0 0 164 124` or similar.
- Draw a front-facing cover panel with subtle perspective.
- Add a visible page block edge, bottom page lines, cover bevel, and cast shadow.
- Keep a small spine/hinge strip only as a book detail, not as the main reading surface.
- Put the title on the wide face area, not vertically on a narrow spine.
- Allow 2-4 title lines with a larger font.
- Keep author as a smaller subtitle or footer strip.
- Use optional URL presence as a small marker, not as dominant content.

Three deterministic variants:

- Hardback side view:
  - thick cover board.
  - cloth hinge strip.
  - page block visible on right/bottom.
  - centered title label.
- Paperback angled side view:
  - softer cover.
  - diagonal perspective side edge.
  - bright title band.
  - lighter page texture.
- Technical/manual book side view:
  - cleaner geometric cover.
  - small corner tabs or index marks.
  - clear title panel.
  - subtle grid or ruled page marks.

Selection rules:

- Derive variant from stable seed, for example `StableSeed % 3`.
- Do not call random APIs during render.
- Keep server prerender and hydrated client output identical.

## Naming Cleanup

Avoid stale bookback/spine terminology after the redesign.

Recommended rename:

- `BookSpine.razor` -> `BookShelfBook.razor` or `BookSideView.razor`.
- CSS:
  - `book-spine-svg` -> `book-side-svg`
  - `book-spine-link` -> `book-side-link`
  - `book-spine-placeholder` -> `book-side-placeholder`
  - `book-spine-title` -> `book-side-title`
  - `book-spine-author` -> `book-side-author`
- Test IDs:
  - `book-spine` -> `bookcase-book`

Keep old names only if changing test IDs causes unnecessary churn, but prefer the cleanup because the user explicitly dislikes the bookback concept.

## Seed Strategy

Update local seed defaults inside `BlazorAutoApp/Features/Books/Seed/BookSeedExtensions.cs`.

Add the four fixed books as deterministic local defaults:

- `Ship`
- `TraceBack`
- `ImprovedDb`
- `KinoJoin`

Recommended placement:

- Put these four first so they are visible early in the scrolling shelf.
- Keep the existing common books after them unless the user later wants only the fixed template books.
- Use neutral/template authors, for example:
  - `Template`
  - `Diagnostics`
  - `Data`
  - `Cinema`
- Keep `Url = null` unless a stable internal route is intentionally assigned later.

Seed requirements:

- Idempotent by title and author.
- No duplicates after restart.
- Still gated to local Development/Docker seed config.
- Tests must not depend on seed rows.

## Execution Plan

### Phase 1 - Baseline And Scope Guard

- [ ] Status: Pending
- [ ] Capture current `git status`.
- [ ] Confirm deployment paths are untouched before edits.
- [ ] Build the solution before making visual changes.
- [ ] Review current `BookSpine.razor`, `Index.razor`, app CSS, and seed extension.

Validation:

- [ ] `dotnet build BlazorAutoApp.sln`
- [ ] `git status --short -- Deployment .github docker-compose.yml Dockerfile`

### Phase 2 - Rename The Book Visual Concept

- [ ] Status: Pending
- [ ] Rename the SVG component away from spine/bookback naming.
- [ ] Update the Books home page to use the renamed component.
- [ ] Update CSS class names to side-view naming.
- [ ] Update E2E selectors if `data-testid` changes.
- [ ] Search for stale `spine` terminology in active code and remove it where it refers to the old visual.

Validation:

- [ ] `rg -n "book-spine|BookSpine|spine|bookback|bookback" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Test --glob '!**/bin/**' --glob '!**/obj/**'`
- [ ] Remaining hits reviewed.

### Phase 3 - Redesign The SVG Books

- [ ] Status: Pending
- [ ] Replace narrow spine SVG with larger side-view SVG.
- [ ] Use a wider stable viewBox.
- [ ] Add three side-view variants.
- [ ] Add cover face, page block, edge shading, cover bevels, and cast shadows.
- [ ] Move title text onto the wide book face.
- [ ] Improve title splitting so titles can use 2-4 neat lines.
- [ ] Keep author text readable but secondary.
- [ ] Keep optional URL marker subtle.
- [ ] Keep all visuals inline SVG.

Validation:

- [ ] Build compiles with Razor SVG syntax.
- [ ] Titles like `Pride and Prejudice`, `TraceBack`, `ImprovedDb`, and `To Kill a Mockingbird` fit cleanly.

### Phase 4 - Enlarge And Rebalance The Bookcase Layout

- [ ] Status: Pending
- [ ] Increase rendered SVG dimensions.
- [ ] Increase bookcase viewport height/padding to match larger books.
- [ ] Adjust shelf height and shadow.
- [ ] Adjust horizontal gaps so the larger books do not crowd each other.
- [ ] Keep infinite scrolling smooth and seamless.
- [ ] Keep hover/focus tip/pull behavior, adjusted for the wider books.
- [ ] Keep reduced-motion behavior.
- [ ] Verify no mobile overlap with render-mode badge or next content.

Validation:

- [ ] Desktop screenshot review.
- [ ] Mobile screenshot review.
- [ ] Confirm no horizontal page overflow.

### Phase 5 - Update Local Seed Defaults

- [ ] Status: Pending
- [ ] Add fixed local seeds:
  - `Ship`
  - `TraceBack`
  - `ImprovedDb`
  - `KinoJoin`
- [ ] Put fixed seeds first in the seed list.
- [ ] Preserve idempotency.
- [ ] Decide whether to keep or reduce existing common books; recommended default is keep them after the fixed titles.
- [ ] Reset local Docker DB to verify fresh seed output.
- [ ] Restart app and verify seed count is stable.

Validation:

- [ ] Fresh `/api/books` includes all four fixed titles.
- [ ] Restarting local app does not duplicate seed rows.

### Phase 6 - Tests And Documentation

- [ ] Status: Pending
- [ ] Update E2E tests if test IDs changed.
- [ ] Update visual snapshot expectations by regenerating headed screenshots.
- [ ] Update README/overview only if they mention SVG spine details.
- [ ] Update plan statuses.

Validation:

- [ ] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- [ ] visible desktop E2E
- [ ] visible mobile E2E

### Phase 7 - Full Verification

- [ ] Status: Pending
- [ ] Build solution.
- [ ] Run full test project.
- [ ] Run formatting verification.
- [ ] Run local Docker with reset.
- [ ] Smoke-check public anonymous home.
- [ ] Smoke-check seeded book titles.
- [ ] Smoke-check `/books` and `/api/books`.
- [ ] Confirm `/movies` and `/api/movies` still return `404`.
- [ ] Confirm deployment files remain untouched.

Validation:

- [ ] `dotnet build BlazorAutoApp.sln`
- [ ] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- [ ] `dotnet format BlazorAutoApp.sln --verify-no-changes`
- [ ] `git diff --check`
- [ ] `.\RunLocal.ps1 -ResetDatabase -NoBrowser`
- [ ] visible desktop E2E
- [ ] visible mobile E2E

## Acceptance Criteria

- [ ] The SVG books no longer look like bookbacks/spines.
- [ ] Books are visibly larger.
- [ ] Titles have enough space and render neatly.
- [ ] Three deterministic side-view variants exist.
- [ ] The infinite bookcase still works.
- [ ] Anonymous users still do not see `Add Book` or `Saved books`.
- [ ] Logged-in users can still manage books.
- [ ] Local seed includes `Ship`, `TraceBack`, `ImprovedDb`, and `KinoJoin`.
- [ ] Local seed remains idempotent.
- [ ] Tests pass.
- [ ] Visible E2E passes on desktop and mobile.
- [ ] Deployment files remain untouched.

## Risks And Mitigations

- Larger books can cause horizontal or vertical overflow on mobile.
  - Mitigation: use fixed responsive dimensions, inspect mobile screenshots, and keep bookcase clipped to its viewport.
- Wider title text can still overflow on long titles.
  - Mitigation: implement deterministic line splitting and maximum line length per variant.
- Renaming test IDs can break E2E unnecessarily.
  - Mitigation: update E2E in the same phase and keep selectors semantic.
- Seed changes can duplicate rows.
  - Mitigation: keep title+author idempotency and verify after container restart.

## Follow-Up Findings

- Deployment/`ship` naming remains intentionally out of scope.
- If the four fixed books are meant to replace common public-domain books rather than supplement them, make a small follow-up decision before execution.
