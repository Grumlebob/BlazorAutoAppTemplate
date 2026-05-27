# Make Book Covers Clean

## Goal

Refactor and clean the book cover designs so the approval demos and the live bookcase use the same corrected artwork. This is not a one-coordinate patch. The current cover faces have several alignment problems and the demo set includes a design that should be removed.

Required user-facing changes:

- Remove **Modern Paperback** entirely.
- Remove **Library Ledger** entirely after follow-up design review.
- Keep the remaining covers coherent and polished.
- Give **Technical Manual** different colored page tabs.
- Give **Field Notebook** four tabs.
- Remove the square cover-face borders from **Technical Manual** and **Decorative Hardcover**.
- Remove the right vertical face line from **Technical Manual**.
- Remove the straight orange face lines from **Decorative Hardcover**.
- Move cover-face line work left where it crowds the right page gutter.
- Fix off-center and misaligned face details on Decorative Hardcover, Technical Manual, and Field Notebook.
- Verify every change with screenshots and iterate until acceptable.

## Before Screenshots

Status: done

Captured current rendered output before the refactor:

- `TestResults/MakeBookCoversClean/Before/overview-desktop.png`
- `TestResults/MakeBookCoversClean/Before/overview-mobile.png`
- `TestResults/MakeBookCoversClean/Before/cloth-open-desktop.png`
- `TestResults/MakeBookCoversClean/Before/technical-open-desktop.png`
- `TestResults/MakeBookCoversClean/Before/decorative-open-desktop.png`
- `TestResults/MakeBookCoversClean/Before/ledger-open-desktop.png`
- `TestResults/MakeBookCoversClean/Before/field-open-desktop.png`

Observed issues from those screenshots:

- **Modern Paperback** is still present as card `02`, despite no longer being wanted.
- **Library Ledger** has right-side blue/corner line work too close to the page gutter; the face art visually leans right and competes with the pages.
- **Decorative Hardcover** has gold/orange ornament lines that do not read centered; the right diamond/line cluster feels pushed toward the page gutter.
- **Technical Manual** right-side vertical detail and inner lines are too close to the book's right edge; page tabs are mostly the same teal/green family and need more deliberate color variety.
- **Field Notebook** currently has only two tabs; face lines run too far right and the left dots/lines do not feel balanced against the title plate.
- Several cover-face drawings use local coordinates all the way to x `120-126`, while the cover's visible right edge is around x `136`; this leaves too little breathing room before the page gutter.

## Current Code Shape

Status: done

Relevant files:

- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCover.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`
- `BlazorAutoApp.Client/Features/Books/AuthorBookcase/AuthorBookcaseCatalog.cs`
- `BlazorAutoApp/wwwroot/tailwind.css`

Current duplication:

- `BookDesignDemoCover.razor` has one copy of the cover artwork switch.
- `BookSideView.razor` has another copy of the production cover artwork switch.
- The demo catalog and production component separately encode design count and design names.

This duplication is the main reason visual fixes risk drifting between approval demos and the real shelf.

## Refactor Direction

Status: done

Create a single source of truth for book cover designs inside the Books slice.

Preferred shape:

- Add a shared cover design model under `Features/Books/Shared`, for example:
  - `BookCoverDesignDefinition.cs`
  - `BookCoverDesignCatalog.cs`
  - `BookCoverArtwork.cs` if a small static helper is cleaner
- Store the approved design list there.
- Have `BookDesignDemoCatalog` project from that shared list instead of maintaining independent design records.
- Have `BookSideView` select from the same shared list for production.
- Keep rendering in Razor components where it is easier to inspect SVG, but avoid independent duplicated coordinate sets.

Do not create a generic UI folder. Keep everything inside `Features/Books`.

Implemented with a shared Books-slice catalog and shared SVG subcomponents:

- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverDesignCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverArtwork.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverPageTabs.razor`

The demo catalog and live `BookSideView` now use the same definitions and artwork.

## Remove Modern Paperback

Status: done

Remove Modern Paperback from:

- `BookDesignDemoCatalog.All`
- `BookDesignArtwork`
- production `BookCoverDesign`
- production design selection modulo
- cover artwork switch branches
- any notes, navigation order, screenshots, tests, or references

Expected final demo set:

1. Cloth Hardback
2. Technical Manual
3. Decorative Hardcover
4. Field Notebook

If production book design assignment uses modulo selection, update it to the new count. It is acceptable that seeded/live sample books redistribute across the remaining designs.

Confirmed in code and screenshots:

- demo overview now contains four cards,
- the removed route is no longer in the active Books slice catalog,
- production selection uses `BookCoverDesignCatalog.All.Count`.

## Shared Geometry Rules

Status: done

Introduce clear coordinate rules and apply them to every cover face:

- Cover outer edge remains around x `136`.
- Page gutter remains visible to the right.
- Face art should normally stay within x `22` to x `116`.
- Title plate may end around x `120-122`, but decorative line work should not visually press into the page gutter.
- Right-side cover-face details should stop around x `112-116` unless they are deliberately part of the cover edge.
- Page tabs belong to the page block, not the cover face.
- Normal and forced-open states must preserve the corrected spacing.

Acceptance criteria:

- no cover-face line appears to overlap, kiss, or visually merge with page lines,
- title plate remains centered inside the cover, not centered relative to the pages,
- page tabs stay visually attached to the page block,
- bottom shadows and page block alignment stay intact from the previous fix.

Applied through the shared artwork component so the demo pages and live shelf use the same corrected geometry.

## Design-Specific Fixes

Status: done

### Cloth Hardback

Keep it mostly as the stable baseline.

Check:

- title plate remains centered,
- top/bottom lines do not move too far right,
- cloth pattern does not obscure text.

### Technical Manual

Fixes:

- Move the right vertical teal line left from the current crowded x `121` area.
- Reduce or recenter the frame width if needed so it does not lean toward the pages.
- Move short left-side manual lines into a cleaner grid.
- Use different tab colors, not only teal/green variants.

Proposed tab palette:

- cyan or teal,
- amber,
- rose or coral,
- lime or blue.

Keep tabs restrained and on the page block.

### Decorative Hardcover

Fixes:

- Recenter gold/orange top and bottom horizontal lines.
- Move the right diamond clusters left enough that the orange ornaments do not crowd the page gutter.
- Make top and bottom ornament groups symmetric.
- Keep curved ornamental strokes balanced around the title plate.

Acceptance:

- the face reads as intentionally centered,
- right ornaments no longer feel “off” or clipped toward the page side.

### Library Ledger

Follow-up status: removed from the active design set.

Previous fixes:

- Move the blue/cyan corner marks and right-side vertical ticks left.
- Pull ledger border/detail lines left or narrow the inner ledger frame.
- Keep the title plate centered and the ledger details outside the title safe zone.
- Avoid line clusters that visually overlap the page lines on the right.

Acceptance:

- right-side ledger details have clear cover-colored space before the page gutter,
- blue details do not look like page-line artifacts.

Current acceptance:

- Library Ledger no longer appears in the demo list or production design catalog.

### Field Notebook

Fixes:

- Add four page tabs.
- Use a deliberate tab palette with four distinct colors.
- Move cover-face horizontal lines left or shorten them.
- Balance left dot markers against the title plate and right edge.
- Keep notebook styling quiet, not busy.

Acceptance:

- four tabs are visible and evenly spaced on the page block,
- face lines do not run into the page side,
- title remains readable.

Implemented and visually checked in `TestResults/MakeBookCoversClean/Pass01`.

## Screenshot Iteration Loop

Status: done

For each implementation pass:

1. Build CSS and app output.
2. Run the local app.
3. Capture screenshots into a numbered folder:
   - `TestResults/MakeBookCoversClean/Pass01`
   - `TestResults/MakeBookCoversClean/Pass02`
   - continue if needed.
4. Inspect these pages:
   - `/books/design-demos`
   - `/books/design-demos/cloth-hardback?open=true`
   - `/books/design-demos/technical-manual?open=true`
   - `/books/design-demos/decorative-hardcover?open=true`
   - `/books/design-demos/library-ledger?open=true`
   - `/books/design-demos/field-notebook?open=true`
   - `/books`
5. Inspect desktop and mobile overview screenshots.
6. If any design still looks off-center, crowded, or visibly sloppy, adjust and repeat.

Do not mark this phase done until screenshots have been personally inspected.

Pass01 was inspected and accepted:

- `TestResults/MakeBookCoversClean/Pass01/overview-desktop.png`
- `TestResults/MakeBookCoversClean/Pass01/overview-mobile.png`
- `TestResults/MakeBookCoversClean/Pass01/cloth-open-desktop.png`
- `TestResults/MakeBookCoversClean/Pass01/technical-open-desktop.png`
- `TestResults/MakeBookCoversClean/Pass01/decorative-open-desktop.png`
- `TestResults/MakeBookCoversClean/Pass01/ledger-open-desktop.png`
- `TestResults/MakeBookCoversClean/Pass01/field-open-desktop.png`

Follow-up pass was inspected and accepted:

- `TestResults/MakeBookCoversClean/UserRequestedCoverCleanup/overview-desktop.png`
- `TestResults/MakeBookCoversClean/UserRequestedCoverCleanup/overview-mobile.png`
- `TestResults/MakeBookCoversClean/UserRequestedCoverCleanup/technical-open-desktop.png`
- `TestResults/MakeBookCoversClean/UserRequestedCoverCleanup/decorative-open-desktop.png`

## Live Bookcase Verification

Status: done

The design demos are not enough. The live shelf must also be checked because the bookcase uses production seeded/randomized covers.

Check:

- `/books` anonymous desktop,
- `/books` anonymous mobile,
- logged-in `/books` with user bookcase,
- hover/forced-open visual behavior if possible.

Acceptance:

- no production book uses Modern Paperback,
- the remaining designs match the approval demos,
- author and user bookcases use the same corrected design set,
- title multiline layout still fits the title plates.

Checked in:

- `TestResults/MakeBookCoversClean/Pass01/books-desktop.png`
- `TestResults/MakeBookCoversClean/Pass01/books-mobile.png`
- `TestResults/MakeBookCoversClean/UserRequestedCoverCleanup/books-desktop.png`
- `TestResults/MakeBookCoversClean/UserRequestedCoverCleanup/books-mobile.png`

## Tests And Validation

Status: done

Run:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- visual snapshot E2E if affected by routes/screenshots
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query

If generated CSS changes, keep `BlazorAutoApp/wwwroot/tailwind.css` committed with the source changes.

Completed:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- headed visual snapshot E2E
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query returned `0 rows`

## Non-Goals

- Do not change deployment.
- Do not change database schema.
- Do not change the book page view/edit/add modal.
- Do not restore the saved-books table.
- Do not change authentication.
- Do not introduce bitmap images; these covers remain SVG.
