# Nice Book Designs

## Goal

Fix the book cover alignment coherently across every active book design. `problem.png` and Prism Atlas are only the clearest example: all designs should use one shared cover geometry contract so title plates, title text, artwork, cover face, and visible page/back thickness are visually centered and consistent.

The title center must be identical for every design. Do not move title centers around to make individual designs look right. Move and rebalance the geometric/artwork layer around the fixed shared title center instead. The live main book design used by `BookSideView` and the shelf must be fixed and kept performant, not only the large demo pages.

## Execution Results

Status: implemented on 2026-05-28.

- [x] Added a shared `BookCoverGeometry` contract with one `TitleCenterX`.
- [x] Moved common cover path, page path, and page-line path into shared geometry.
- [x] Changed `BookCoverRenderer` to use the shared shell geometry.
- [x] Changed every catalog entry to derive its plate from `BookCoverGeometry.CenteredPlate(...)`.
- [x] Removed per-design `CoverPath` and `PagePath` from `BookCoverDesignDefinition`.
- [x] Added geometry regression tests covering all active designs.
- [x] Shifted the shared title center slightly left to keep every cover aligned from the same X coordinate.
- [x] Removed Bookmark Folio, Embroidery Sampler, Signal Flag Manual, and Woven Archive from the active designs.
- [x] Removed Origami Edition, Herbarium Slip, Quilt Reader, Wave Notebook, Blueprint Register, Laboratory Log, Calendar Folio, and Bauhaus Reader from the active designs.
- [x] Removed Aurora Field Guide, Music Score, and Solar Dial Folio from the active designs.
- [x] Removed Arbor Press, Beacon Logbook, and Cityline from the active designs.
- [x] Reduced and shifted the Droplet Monograph drop so it is clear below the shared title plate.
- [x] Moved Field Notebook dots slightly left.
- [x] Captured and manually reviewed browser screenshots for all active design detail pages in normal state.
- [x] Captured and manually reviewed browser screenshots for all active design detail pages in forced-open state.
- [x] Captured and reviewed the design demo overview at small card scale.
- [x] Checked `/books`, `/health/ready`, and `/api/author-books`; all return HTTP 200 against the local Docker-backed app.
- [x] Reviewed `BookSideView` as the live shelf adapter; it continues to use the same shared renderer and does not add new measurement, JavaScript, randomness, or per-render path parsing.
- [x] Rechecked rendered browser screenshots for the active designs in normal state and forced-open state. The measured rendered title-plate center stays within 1.5 px of the rendered cover center.
- [x] Confirmed removed design labels are absent from the rendered design demo overview.

Verification:

- [x] `dotnet build BlazorAutoApp.sln`
- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj --filter FullyQualifiedName~BookCoverGeometryTests`
- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj --filter "FullyQualifiedName~BlazorAutoApp.Test.Features.Books.Client"`
- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj --filter "Category=E2E"`
- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj` with `RUN_E2E=1`
- [x] `dotnet format BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`

Visual artifacts:

- Normal contact sheet: `BlazorAutoApp.Test/TestResults/Playwright/BookDesignReview/contact-normal.png`
- Forced-open contact sheet: `BlazorAutoApp.Test/TestResults/Playwright/BookDesignReview/contact-open.png`
- Prism Atlas detail screenshot: `BlazorAutoApp.Test/TestResults/Playwright/BookDesignReview/prism-atlas-normal.png`
- `/books` environment-blocker screenshot: `BlazorAutoApp.Test/TestResults/Playwright/BookDesignReview/books-route-no-db.png`

## Problem

The current renderer is shared, but the geometry is still too ad hoc:

- `BookCoverRenderer.razor` draws the SVG shell, page/back block, cover group, title plate, and title text.
- `BookCoverDesignCatalog.cs` repeats per-design `CoverPath`, `PagePath`, and full `Plate` coordinates.
- `BookCoverArtwork.razor` draws each design with independent coordinates.
- `BookDesignDemoCover.razor` and `BookSideView.razor` both use the shared renderer, so bad geometry affects both demo pages and the live shelf.

The coherent fix is not to move Prism Atlas by a few pixels. The fix is to define the book's visual coordinate system once, make the renderer own the common cover/page/title geometry, and make every design conform to that system.

## Non-Goals

- Do not add raster assets.
- Do not change book data, auth, API, caching, or persistence behavior.
- Do not redesign the whole bookcase.
- Do not remove the hover/forced-open behavior.
- Do not touch `Deployment/**`.
- Do not archive or delete `problem.png` unless the user asks.

## Target Files

- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverRenderer.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverDesignCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverArtwork.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverPageTabs.razor`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCover.razor`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoDetails.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`
- `BlazorAutoApp.Test/**` for geometry/unit tests and any existing visual/E2E coverage that should be expanded.

## Active Design Scope

The fix applies to every current design:

- Cloth Hardback
- Decorative Hardcover
- Field Notebook
- Prism Atlas
- Droplet Monograph
- Transit Map Folio
- Compass Fieldbook
- Atlas Pinboard
- Seismograph Log
- Alpine Trail Guide

## Coherent Fix

### Shared Geometry Contract

Define one canonical coordinate contract for the book cover renderer:

- one cover face path,
- one page/back block path,
- one page-line layout,
- one visual cover center,
- one protected title-zone center used by every design,
- one shadow position,
- one set of safe artwork zones above and below the title plate.

The catalog should not repeat full horizontal placement for every design. If designs need different title plate sizes, they can specify dimensions and style, but the renderer should derive:

- `Plate.X` from shared center and plate width,
- `Plate.TextX` from shared center,
- inner plate X/width from the outer plate,
- page/back placement from the shared book geometry.

If keeping the existing `BookCoverTitlePlate` record is less churn, add a helper/factory such as `CenteredPlate(...)` and make every catalog entry use it. The important outcome is that all designs are mechanically centered from the same source of truth.

Required title-center rule:

- there is exactly one shared title center X value,
- every design's outer plate center equals that value,
- every design's inner plate center equals that value,
- every design's text anchor equals that value,
- no design may override title center X.

### Artwork Contract

Each artwork branch should draw inside named design zones:

- top zone above the title plate,
- bottom zone below the title plate,
- optional edge/accent zone,
- no decoration crossing the protected title plate.

Design-specific artwork may be intentionally asymmetric, but the composition must still balance around the shared cover center. Do not compensate for bad shell geometry with arbitrary per-design transforms.

For geometric designs, the geometry itself must be moved/fixed. Designs such as Prism Atlas, Transit Map Folio, Atlas Pinboard, and Seismograph Log should have their lines, facets, marks, and accent systems centered or visually balanced around the fixed title center. The title center is not the variable.

### Open-State Contract

The cover opening motion should preserve the same center in the closed state and move as one coherent book object in hover/focus/forced-open states:

- page/back block remains behind the cover,
- cover and title plate move together,
- text remains readable,
- the open offset is visibly intentional and small.

### Performance Contract

The main shelf path must stay lightweight:

- `BookSideView.razor` should remain a small adapter over shared renderer data.
- Avoid per-render SVG path parsing, DOM measurement, JavaScript layout work, or runtime randomness.
- Prefer static/shared geometry constants and simple record data over recomputing derived coordinates per book.
- Keep the inline SVG node count controlled; do not solve alignment by duplicating invisible helper shapes per design.
- Design demos can expose review states, but the live shelf must use the same fixed geometry without extra demo-only overhead.
- SSR and hydrated output must remain deterministic.

## Implementation Plan

### Phase 1 - Baseline Every Design

- [ ] Open `problem.png` and use it as the visible failure example, not as the only target.
- [ ] Confirm the design demo routes render from `BookDesignDemoCatalog.All`.
- [ ] Capture or inspect normal and forced-open states for all 28 designs.
- [ ] Record the current repeated geometry patterns:
  - cover paths,
  - page paths,
  - plate x/width/text center,
  - artwork bounds where obvious.
- [ ] Identify one target visual center for the front cover face and title zone.

Validation:

- [ ] There is a before-state reference for every active design.
- [ ] The plan executor can say which geometry is shared and which is design-specific.

### Phase 2 - Centralize Cover Geometry

- [ ] Add a shared geometry source for cover/page/title placement.
- [ ] Define one shared title center X constant.
- [ ] Move common cover face and page/back paths out of per-design entries if practical.
- [ ] Move page-line coordinates into the shared renderer or geometry helper.
- [ ] Make the renderer derive plate outer X, inner X, and text X from the shared title center.
- [ ] Keep per-design differences limited to palette, title plate size/style, and artwork kind.
- [ ] Remove or neutralize duplicated horizontal placement values that allow designs to drift.
- [ ] Ensure no design can specify a custom title center.

Validation:

- [ ] Every design has the exact same mechanical title center.
- [ ] Plate outer rect, inner rect, and text anchor share that center.
- [ ] Page/back thickness is consistent across every design.

### Phase 3 - Normalize The Catalog

- [ ] Update every `BookCoverDesignCatalog.All` entry to use the shared geometry/factory.
- [ ] Preserve each design's label, id, demo title, note, palette, and title plate styling.
- [ ] Keep legitimate plate height/width differences only where they improve title readability.
- [ ] Remove repeated hand-authored `CoverPath` and `PagePath` values if the new model supports it.
- [ ] If the old record shape must remain, make all entries use identical centered values derived from the helper.
- [ ] Remove per-design title-center data from the catalog API if practical.

Validation:

- [ ] All 28 catalog entries compile.
- [ ] No catalog entry hardcodes a different title center.
- [ ] No catalog entry uses a one-off shell path unless it has a written reason in code or plan notes.

### Phase 4 - Rebalance Artwork For All Designs

- [ ] Review every `BookCoverArtwork.razor` branch against the shared title zone.
- [ ] Move decorations out of the protected title plate area.
- [ ] Center symmetrical artwork around the shared cover center.
- [ ] For intentionally asymmetric artwork, balance visual weight on both sides of the shared center.
- [ ] Move/fix geometric artwork coordinates instead of moving title plates.
- [ ] Keep the design identities intact; this is alignment and composition cleanup, not a full redesign.
- [ ] Check page tabs in `BookCoverPageTabs.razor` so they align with the shared page/back block.

Validation:

- [ ] No artwork branch makes the title plate look shifted.
- [ ] Geometric designs are visually balanced around the fixed center.
- [ ] No decoration crosses or crowds title text.
- [ ] Page tabs still attach to the visible page/back edge.

### Phase 5 - Add Geometry Tests

- [ ] Add focused tests for all active `BookCoverDesignCatalog.All` entries.
- [ ] Assert every design uses the exact same computed title center.
- [ ] Assert plate outer center, inner center, and text center match.
- [ ] Assert no catalog entry can supply a custom title center.
- [ ] Assert plate bounds stay inside the front cover safe area.
- [ ] Assert demo ids remain unique and design count stays intentional.
- [ ] If helper/factory methods are added, test them directly.

Validation:

- [ ] A future hand-authored off-center plate fails a test.
- [ ] Tests cover every active design, not a sampled subset.
- [ ] A future per-design title-center override fails a test or is impossible by model shape.

### Phase 6 - Visual Verification For Every Design

- [ ] Add or run a visual review path that iterates through all design demo routes.
- [ ] Check each design in normal state.
- [ ] Check each design in forced-open state with `?open=true`.
- [ ] Check the demo overview grid.
- [ ] Check the live `/books` shelf with multiple titles so shared renderer use is covered outside demos.
- [ ] Check live shelf hover/focus on enough books to confirm the main book design is fixed, not just demo scale.
- [ ] Confirm no page-level horizontal overflow was introduced.

Validation:

- [ ] Every design has balanced left/right visual spacing in normal state.
- [ ] Every forced-open state still reads as an intentional book opening.
- [ ] The live shelf matches the demo behavior.
- [ ] The live shelf remains smooth and does not gain avoidable DOM/layout overhead.

### Phase 7 - Main Shelf Performance Review

- [ ] Review `BookSideView.razor` for unnecessary per-render allocation or recomputation after the geometry change.
- [ ] Keep design selection deterministic and cheap.
- [ ] Keep shared geometry values static or otherwise reused.
- [ ] Avoid adding browser measurement or JavaScript to decide alignment.
- [ ] Confirm the main shelf still renders with the existing repeated book count without sluggish hover/focus behavior.

Validation:

- [ ] Main shelf uses the shared fixed geometry.
- [ ] No demo-only alignment code is required for the live shelf.
- [ ] No new runtime randomness or layout measurement exists.

### Phase 8 - Automated Gates

- [ ] Run `dotnet build BlazorAutoApp.sln`.
- [ ] Run focused geometry tests.
- [ ] Run `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj` if the shared rendering/catalog contract changed broadly.
- [ ] Run `dotnet format BlazorAutoApp.sln --verify-no-changes`.
- [ ] Run `git diff --check`.

Validation:

- [ ] Build passes.
- [ ] Relevant tests pass.
- [ ] Formatting check passes.
- [ ] Whitespace diff check passes.

## Acceptance Criteria

- [ ] All active designs use a shared cover/page/title geometry contract.
- [ ] All active designs use the exact same title center.
- [ ] All title plates are centered by construction, not by per-design hand tuning.
- [ ] All title text anchors align with the shared title center.
- [ ] Geometric artwork is moved/fixed around the shared center instead of moving title centers.
- [ ] All artwork respects the protected title zone.
- [ ] Page/back thickness is consistent and still visible.
- [ ] Normal state and forced-open state are both visually balanced for every design.
- [ ] Design demos and live shelf use the same fixed renderer behavior.
- [ ] The main `BookSideView`/shelf path remains performant and deterministic.
- [ ] Geometry tests prevent future per-design drift.
- [ ] No unrelated app behavior changes.
- [ ] Deployment files remain untouched.

## Notes For Execution

- Do not fix this by moving Prism Atlas alone.
- Do not make title centers vary by design.
- Do not hide the issue by cropping the demo wrapper or moving the whole SVG stage.
- Prefer a small model/helper change that makes bad alignment impossible.
- Fix geometric compositions by moving their artwork coordinates to match the shared center.
- If visual perception and raw path math disagree, adjust the shared geometry once and keep every design derived from it.
