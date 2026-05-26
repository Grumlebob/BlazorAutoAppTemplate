# More Books

## Goal

Expand the bookcase so books have meaningfully different, polished SVG designs instead of mostly random color changes.

The current shelf is working, so this plan should preserve the core behavior:

- Home remains Books-first.
- Books still render from deterministic SVG, not raster assets.
- The infinite shelf still auto-scrolls.
- Hover/focus still pauses the shelf, allows manual horizontal scrolling, hides scrollbars, and opens each book slightly.
- The SVG still shows only title text, no visible author text and no footer strip.
- Title text remains protected inside the middle title panel.
- Deployment is not touched.

## Investigation Findings

### Current Component Shape

Active file:

- `BlazorAutoApp.Client/Features/Books/BookSideView.razor`

Current implementation:

- Uses `viewBox="0 0 210 160"`.
- Uses fixed rendered dimensions:
  - mobile: `h-[8.95rem] w-[11.75rem]`
  - desktop: `sm:h-[10.65rem] sm:w-[14rem]`
- Uses deterministic selection:
  - `Variant => StableSeed % 3`
  - `Colors => Palette[StableSeed % Palette.Length]`
- Uses one shared `BookPalette` record.
- Uses one shared `TitlePanel()` fragment.
- Uses one shared `UrlMarker()` fragment.
- Keeps title max line length at `12`.
- Keeps authors out of the SVG.
- Has no visible footer strip.

Current designs:

1. Rounded hardback.
2. Rounded paperback with top/bottom bands.
3. Technical manual with squared detail and page tabs.

Practical issue:

- The first two designs are visually close because both share nearly the same rounded cover silhouette.
- Most of the visible variation currently comes from palette changes, not structure.
- Adding more variants directly to the existing `if/else` block will make `BookSideView.razor` harder to maintain quickly.

### Current Bookcase Behavior

Active file:

- `BlazorAutoApp.Client/Features/Books/Pages/Index.razor`

Current behavior:

- Bookcase viewport is horizontally clipped normally.
- Hover/focus exposes horizontal scrolling.
- Scrollbar is hidden with Tailwind arbitrary utilities:
  - `[scrollbar-width:none]`
  - `[-ms-overflow-style:none]`
  - `[&::-webkit-scrollbar]:hidden`
- Animation pauses on hover/focus via named group utilities.
- Book item hover/focus applies subtle lift/drop shadow.

Constraint:

- Any new SVG utility classes used in Razor must be included in generated `tailwind.css`.
- The CI check fails if generated CSS changes are not committed.
- The previous CI failure came from `BookSideView.razor` not being tracked, so any new component/helper file must be tracked before CI.

### Current Quality Constraints

Keep:

- `viewBox="0 0 210 160"`.
- Shared book size.
- Shared hover/open mechanics.
- Shared title panel geometry unless a design explicitly needs a carefully reviewed alternate panel.
- Page blocks should sit slightly tucked behind the cover; avoid letting pages protrude too far right.
- Deterministic SSR/hydration output.
- No runtime randomization.
- No external assets.
- No custom book-specific CSS in `app.css`.
- No page-level horizontal scrollbar.
- No author/footer text inside SVG.

Avoid:

- Overly decorative posters.
- Rotated title text.
- Decorative lines crossing title text.
- Designs where the right page block disappears.
- Small text that only works on desktop.
- A giant `if/else` block that becomes unpleasant to maintain.
- One-off arbitrary class strings that are easy to lose from Tailwind generation.

## Design Direction

The shelf should have **six high-quality book designs**.

Six is enough to make the bookcase feel varied without turning the component into a pile of one-off drawings. Palette variation can still multiply the visual range, but design selection should be structural.

Every design must include:

- A front cover group.
- A right page block group.
- A protected title panel.
- A left hinge/spine detail.
- Optional URL marker outside the title panel.
- No visible author/footer strip.

## Proposed Designs

### 1. Cloth Hardback

Purpose:

- Keep the current quiet clothbound design, but polish it as the baseline.

Visual traits:

- Rounded cover.
- Subtle hinge strip.
- Restrained horizontal rule lines above and below title panel.
- Cream or light panel.
- Right page block with even page lines.

Implementation notes:

- This can evolve from current `Variant == 0`.
- Use it as the simplest silhouette.

### 2. Modern Paperback

Purpose:

- Keep a clean paperback but make it structurally distinct from cloth hardback.

Visual traits:

- Rounded cover, but with a lighter, flatter paperback feel.
- Large top color band or diagonal color block, never crossing title panel.
- Thinner hinge.
- Slight lower cover color block.
- Page block can be wider and slightly brighter.

Implementation notes:

- This can evolve from current `Variant == 1`.
- Needs stronger shape/detail differences from Cloth Hardback.

### 3. Technical Manual

Purpose:

- Preserve the template/manual flavor.

Visual traits:

- Squarer cover radius.
- Thin outer frame.
- Corner marks or small grid details.
- Right-side page tabs.
- Crisp title panel.

Implementation notes:

- This can evolve from current `Variant == 2`.

### 4. Decorative Hardcover

Purpose:

- Add a decorative hardcover style that is clearly different from the simple hardback without using a dust jacket treatment.

Visual traits:

- Geometric corner marks.
- Restrained ornamental lines above and below the title panel.
- No heavy left-side block.
- Right page block remains visible.
- Title panel remains the stable central anchor.

Geometry idea:

- Cover base: `rect x=18 y=24 width=148 height=114 rx=10`.
- Outer border: `rect x=27 y=32 width=130 height=98 rx=6`.
- Corner diamonds or L-shaped marks outside the title panel.
- Top and bottom decorative rules outside the title panel.
- Keep title panel at `x=50 y=52 width=96 height=54`.

### 5. Library Ledger

Purpose:

- Add a heavier reference-book style with a different personality.

Visual traits:

- Strong border frame.
- Corner protectors or reinforced corners.
- Double-line cover border.
- No heavy dark left-side block.
- Title panel must be carefully centered; do not let the formal plate drift up or right.
- Page block slightly aged.
- Title panel looks like a formal plate.

Geometry idea:

- Cover base: `rect x=18 y=23 width=148 height=115 rx=8`.
- Outer border: `rect x=27 y=32 width=128 height=96 rx=5`.
- Corner marks: four small L-shaped paths outside title panel.
- Title panel remains clear.

### 6. Field Notebook

Purpose:

- Add a notebook/sketchbook-inspired design without making it look like a spiral notebook from the front.

Visual traits:

- Rounded cover.
- Soft left binding detail.
- Small page tabs or side markers on the page block.
- Minimal cover markings.
- Horizontal cover rules should extend close enough to the right edge to feel intentional.
- Title panel can be slightly smaller or more label-like but still readable.

Geometry idea:

- Cover base: `rect x=18 y=24 width=146 height=114 rx=12`.
- Hinge: slim left strip.
- Page block has fewer, cleaner page lines.
- Title panel stays centered and clear.

## Architecture Plan

### Problem With Current Shape

The current component mixes:

- variant selection,
- page block drawing,
- cover drawing,
- title drawing,
- URL marker drawing,
- palette definitions,
- title splitting,
- hover classes,
- and SVG geometry

in a single `.razor` file.

That is still acceptable for three variants, but six variants will become hard to review if added as one longer `if/else` chain.

### Recommended Implementation Shape

Keep one public component:

- `BookSideView.razor`

Add one small internal enum in the component:

```csharp
private enum BookDesign
{
    ClothHardback,
    ModernPaperback,
    TechnicalManual,
    DecorativeHardcover,
    LibraryLedger,
    FieldNotebook
}
```

Use a constant:

```csharp
private const int DesignCount = 6;
private BookDesign Design => (BookDesign)((StableTitleSeed + (uint)StableSeed) % DesignCount);
```

Keep palette independent:

```csharp
private BookPalette Colors => Palette[StableSeed % Palette.Length];
```

Split rendering into focused fragments:

- `RenderPageBlock(BookDesign design)`
- `RenderCover(BookDesign design)`
- `TitlePanel()`
- `UrlMarker()`

This keeps title and URL behavior shared while allowing each design to have a different page block and cover.

Avoid adding many new files unless the component gets genuinely too large. A single Razor component with named render fragments is still the simplest shape for this feature.

## Detailed Implementation Plan

### Phase 1 - Baseline And Guardrails

- [x] Status: Completed
- [x] Confirm current working tree status.
- [x] Confirm `BookSideView.razor` is tracked.
- [x] Confirm deployment paths are untouched.
- [x] Run `npm run css:build`.
- [x] Run the generated CSS verification command.
- [x] Run `dotnet build BlazorAutoApp.sln`.

Validation:

- [x] `git status --short`
- [x] `git ls-files -- BlazorAutoApp.Client/Features/Books/BookSideView.razor`
- [x] `git status --short -- Deployment .github docker-compose.yml Dockerfile`
- [x] `npm run css:build`
- [x] `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json`
- [x] `dotnet build BlazorAutoApp.sln`

### Phase 2 - Refactor For More Designs

- [x] Status: Completed
- [x] Add `BookDesign` enum with six designs.
- [x] Replace `Variant => StableSeed % 3` with deterministic title-and-seed based `Design` selection.
- [x] Keep palette selection independent from design selection.
- [x] Extract shared page/cover group class strings into constants if it improves readability.
- [x] Extract page block drawing into a `RenderPageBlock(BookDesign design)` fragment.
- [x] Extract cover drawing into a `RenderCover(BookDesign design)` fragment.
- [x] Keep `TitlePanel()` shared.
- [x] Keep `UrlMarker()` shared.
- [x] Keep title splitting unchanged unless visual inspection shows a problem.

Validation:

- [x] `dotnet build BlazorAutoApp.sln`
- [x] `npm run css:build`
- [x] Generated CSS check passes.

### Phase 3 - Implement Six Book Designs

- [x] Status: Completed
- [x] Implement Cloth Hardback.
- [x] Implement Modern Paperback.
- [x] Implement Technical Manual.
- [x] Implement Decorative Hardcover.
- [x] Implement Library Ledger.
- [x] Implement Field Notebook.
- [x] Ensure every design has visible right pages.
- [x] Ensure every design has visible page lines on the right page block.
- [x] Ensure no design draws decoration over the title panel.
- [x] Ensure no design includes visible author text or footer strip.
- [x] Ensure URL marker does not overlap title or decorative elements.
- [x] Keep all designs inside the same `210 x 160` coordinate system.

Validation:

- [x] Screenshot review confirms approved designs render across seeded books.
- [x] `Ship`, `TraceBack`, `ImprovedDb`, `KinoJoin`, `The Great Gatsby`, `Pride and Prejudice`, and `To Kill a Mockingbird` remain readable.

### Phase 4 - Palette And Distribution Review

- [x] Status: Completed
- [x] Review existing palette against the six designs.
- [x] Keep palette count independent from design count.
- [x] Avoid a one-note palette family.
- [x] Avoid combinations where panel/ink contrast is weak.
- [x] Add or tune palettes only if needed for contrast and variety.
- [x] Keep generated SVG deterministic for SSR/hydration.

Validation:

- [x] Visual review checks seeded books across desktop and mobile.
- [x] No title panel has low contrast.
- [x] No design relies only on color to feel different.

### Phase 5 - Bookcase Interaction Regression

- [x] Status: Completed
- [x] Confirm infinite auto-scroll still runs.
- [x] Confirm hover pauses the animation.
- [x] Confirm hover allows manual horizontal scrolling.
- [x] Confirm focus allows manual horizontal scrolling.
- [x] Confirm scrollbars remain visually hidden.
- [x] Confirm no page-level horizontal scrollbar appears.
- [x] Confirm hover/open effect still reveals page blocks subtly.

Validation:

- [x] Manual browser check.
- [x] Desktop screenshot review.
- [x] Mobile screenshot review at `390x844`.

### Phase 6 - Tests And Generated Assets

- [x] Status: Completed
- [x] Run non-E2E tests.
- [x] Run visible desktop E2E.
- [x] Run visible mobile E2E.
- [x] Inspect Playwright screenshots.
- [x] Regenerate Tailwind CSS and verify it is committed.
- [x] Run formatting and whitespace checks.

Validation:

- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj --filter "Category!=E2E"`
- [x] `RUN_E2E=1 E2E_HEADLESS=0 dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj --filter "Category=E2E"`
- [x] visible mobile E2E with `E2E_VIEWPORT_WIDTH=390` and `E2E_VIEWPORT_HEIGHT=844`
- [x] `npm run css:build`
- [x] `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json`
- [x] `dotnet format BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`

### Phase 7 - Local Run For Review

- [x] Status: Completed
- [x] Rebuild and run the local Docker app.
- [x] Wait for readiness.
- [x] Provide the local URL for visual review.

Validation:

- [x] `docker compose up -d --build web`
- [x] `https://localhost:7186/health/ready` returns `200`
- [x] User can inspect `https://localhost:7186`

## Acceptance Criteria

- [x] The shelf has six structural book designs.
- [x] Designs differ by geometry and details, not just color.
- [x] Books still look like one coherent design family.
- [x] Every design shows a right-side page block.
- [x] Every design keeps the title in a protected central panel.
- [x] No visible author text appears in the SVG.
- [x] No visible footer strip appears in the SVG.
- [x] Long titles remain readable and do not cross safe zones.
- [x] URL marker remains subtle and outside the title panel.
- [x] Hover/focus still opens books slightly.
- [x] Hover/focus still allows manual hidden-scrollbar shelf scrolling.
- [x] Tailwind generated CSS verification passes.
- [x] Build passes.
- [x] Tests pass.
- [x] Visible desktop and mobile E2E pass.
- [x] Deployment files remain untouched.

## Notes For Execution

- Prefer improving the component structure before adding all variants.
- Keep the title panel as the invariant anchor of the design system.
- Do not add author/footer strip back into the SVG.
- Do not rely on color alone for variation.
- Do not add custom app CSS for the book designs.
- Keep all new SVG/Tailwind classes in tracked Razor files before running CI.
