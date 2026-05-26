# Worthy

## Goal

Replace the current **Decorative Hardcover** with a showcase-quality SVG cover that feels like a premium template-app visual, not a small ornament tweak. The new design must be visually distinct from Cloth Hardback, Technical Manual, and Field Notebook, and it must work both in the design demo pages and in the live infinite bookcase.

This plan is intentionally visual and iterative. The target is a design that can be shown to someone evaluating the app and make the bookcase feel like a polished, custom-built Blazor experience.

## Current Assessment

Status: done

Current active design files:

- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverDesignCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverArtwork.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCover.razor`

Current Decorative Hardcover problems:

- It is still visually close to the previous decorative-book version, just simplified.
- The four diamonds plus curved lines do not create a memorable identity.
- It has no coherent theme beyond "purple with gold marks".
- It does not feel materially different enough from the other covers.
- It does not show off the SVG craftsmanship the template is capable of.

Important current constraints:

- The cover is rendered as inline SVG through shared Books-slice components.
- The demo page and live bookcase share `BookCoverArtwork`.
- The cover uses the same title plate system as the other books.
- The book viewBox is `0 0 216 247`.
- The cover drawing itself is inside a translated/scaled group.
- The cover face safe area should avoid crowding the right page gutter.

## New Design Direction

Status: pending

Replace Decorative Hardcover with a new concept:

**Celestial Archive Hardcover**

Design characteristics:

- deep ink-violet or midnight-indigo hardcover,
- warm foil accents, closer to antique brass than bright orange,
- fine constellation dots and connecting strokes,
- a large off-center orbital arc system that moves around the title plate without crossing it,
- tiny debossed star marks and short foil ticks,
- no square border,
- no straight top or bottom bars,
- no heavy frame,
- title plate remains clean, readable, and centered.

The purpose is to make the cover feel like a premium archival/science-fantasy hardcover while still being simple enough for a small SVG on mobile.

## Geometry

Status: pending

Keep the shared book dimensions and animation behavior.

Use these decorative-cover layout rules:

- cover outer path stays as currently defined for Decorative Hardcover,
- visible face artwork should mainly stay within x `24` to x `116`,
- no face detail should visually merge with page lines on the right,
- title plate remains at current approximate position unless screenshots show it needs a small adjustment,
- title safe zone is the plate plus at least `7px` of visual breathing room,
- major arcs should pass above, below, or around the title plate, never through title text,
- constellation dots should be small enough not to look like noise in the shelf size,
- the open-book hover state must not cause the arcs or dots to look clipped.

Expected visual hierarchy:

1. book silhouette and title plate,
2. graceful foil arc motif,
3. constellation dots and small ticks,
4. subtle cover depth.

## Implementation Plan

Status: pending

### Phase 1: First Premium Direction

Status: pending

Update only the Decorative Hardcover branch in `BookCoverArtwork.razor`.

Replace the current diamonds and curve strokes with a new SVG group:

- two or three partial orbital arcs using `path` commands,
- 8 to 12 small foil dots,
- 3 to 5 short accent ticks,
- one subtle secondary stroke color for depth,
- all paths clipped only by their own coordinates, not by a hard visible border.

Keep the branch small enough to read. If the SVG becomes hard to understand, split the branch into a private Razor fragment helper inside the same component or add a purpose-specific shared component under `Features/Books/Shared`.

### Phase 2: Catalog Tone

Status: pending

Update Decorative Hardcover metadata in `BookCoverDesignCatalog.cs`:

- keep `Id` as `decorative-hardcover` so existing route links remain stable,
- change the `Note` to describe the new premium archive direction,
- adjust `CoverColors` only if the new artwork needs a deeper base,
- adjust `Plate` colors only if the title plate looks too cold or too flat against the new cover.

Do not add a new route or extra variant unless the first implementation proves the old name is misleading. The current variant slot should evolve rather than expanding the design count.

### Phase 3: Screenshot Pass 01

Status: pending

Build and run the app locally, then capture:

- `TestResults/Worthy/Pass01/overview-desktop.png` from `/books/design-demos`
- `TestResults/Worthy/Pass01/overview-mobile.png` from `/books/design-demos`
- `TestResults/Worthy/Pass01/decorative-open-desktop.png` from `/books/design-demos/decorative-hardcover?open=true`
- `TestResults/Worthy/Pass01/books-desktop.png` from `/books`
- `TestResults/Worthy/Pass01/books-mobile.png` from `/books`

Inspect the screenshots manually.

Pass01 is acceptable only if:

- the design is clearly not the old diamond cover,
- the cover reads as premium at overview card size,
- the title remains more important than the ornament,
- no ornament touches the page gutter,
- the live bookcase still feels coherent with the other covers.

### Phase 4: Iteration Pass 02

Status: pending

Expect at least one adjustment pass.

Possible refinements:

- increase or reduce foil opacity,
- move arcs further from the title plate,
- simplify dots if the mobile overview gets noisy,
- add one subtle highlight if the cover feels flat,
- lower the title plate contrast if it feels pasted on,
- adjust `DemoTitleY` or title plate if `Trace Back` looks cramped.

Capture screenshots into:

- `TestResults/Worthy/Pass02`

Do not mark this done until Pass02 is visually better than Pass01.

### Phase 5: Iteration Pass 03

Status: pending

Do a final senior-quality polish pass after comparing Pass01 and Pass02.

Focus on:

- balance on the left and right sides of the cover face,
- readability at mobile card size,
- elegance in the forced-open state,
- not over-designing the book compared to the rest of the shelf.

Capture screenshots into:

- `TestResults/Worthy/Pass03`

If Pass02 already looks excellent, Pass03 can be a no-code verification pass with fresh screenshots. If Pass02 exposes a real issue, Pass03 must include a code adjustment.

## Acceptance Criteria

Status: pending

The final Decorative Hardcover must satisfy all of these:

- looks like a new design direction, not a cleaned-up version of the old one,
- works as a small book on the live shelf,
- works as a large forced-open demo,
- has no square border,
- has no straight orange bars,
- has no right-edge vertical line,
- has no ornament crossing the title text,
- has no visual collision with the page block,
- uses pure SVG and existing Razor/Tailwind patterns,
- stays inside `Features/Books`,
- keeps routes stable,
- does not touch deployment, database, authentication, or CRUD behavior.

Showcase bar:

- A person looking at `/books/design-demos` should immediately see that Decorative Hardcover is the premium visual variant.
- A person looking at `/books` should feel the shelf has custom illustration quality rather than repeated placeholder cards.

## Tests And Verification

Status: pending

Run after the final visual pass:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed visual snapshot E2E
- headed Books E2E desktop if the live shelf behavior is touched
- headed Books E2E mobile `390 x 844` if title sizing or shelf layout changes
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`

Keep the app running locally at the end so the final design can be reviewed in the browser.

## Non-Goals

Status: pending

- Do not add bitmap images.
- Do not add a new design demo framework.
- Do not reintroduce Library Ledger or Modern Paperback.
- Do not change book CRUD, edit mode, add mode, routing, identity, deployment, Docker, or migrations.
- Do not add generic shared UI folders outside the Books slice.
