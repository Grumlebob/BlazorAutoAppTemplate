# Nice Books SVG

## Goal

Make the Books home SVGs look much more like real side-view books.

The current side-view direction is closer, but the next version should be more convincing:

- Books should be taller.
- Books should clearly show page blocks on the right side.
- Books should have only three polished variants.
- Hover/focus should make the book open a tiny bit, like it is about to open.
- The hover effect must not distort or move the title enough to harm readability.
- The title must sit in a protected middle panel for all variants.
- The SVG should not display authors or a footer strip on the book face.
- The Blazor implementation should use Tailwind utility classes directly instead of adding custom book-specific CSS to `app.css`.

## Non-Goals

- Do not touch `Deployment/**`.
- Do not add raster images or external assets.
- Do not add upload/image functionality.
- Do not change auth behavior.
- Do not change the Books model.
- Do not remove render-mode diagnostics.
- Do not add new bookcase-specific CSS classes to `BlazorAutoApp/wwwroot/app.css` unless Tailwind cannot express the behavior.

## Current Target Files

- `BlazorAutoApp.Client/Features/Books/BookSideView.razor`
- `BlazorAutoApp.Client/Features/Books/Pages/Index.razor`
- `BlazorAutoApp/wwwroot/app.css` should be reduced or left alone for this feature; prefer Tailwind utility classes in Razor.
- `BlazorAutoApp/Features/Books/Seed/BookSeedExtensions.cs`
- `BlazorAutoApp.Test/E2E/*` only if selectors or visual expectations need updates.

## Design Requirements

### Visual Principle

The books should be simple, clean, and clearly book-like. Avoid over-decorating them into busy poster cards. The strongest visual signals should be a substantial front cover face, a visible page block on the right edge, a small amount of book thickness, one clean central title panel, and a small left hinge detail.

The bookcase should intentionally show fewer books at once. It is acceptable, and preferred, that desktop shows roughly 5-7 books at a time and mobile shows roughly 2-3 books at a time. Larger books are better here because the title must be readable and the book shape must be convincing.

### Target Dimensions

Use a larger and taller book than the current component.

Recommended SVG coordinate system:

```text
viewBox="0 0 210 160"
```

Recommended rendered dimensions:

```razor
class="h-[10.65rem] w-[14rem]"
```

Responsive mobile dimensions:

```razor
class="h-[8.95rem] w-[11.75rem] sm:h-[10.65rem] sm:w-[14rem]"
```

Recommended bookcase sizing:

```razor
bookcase viewport: class="overflow-x-hidden hover:overflow-x-auto focus:overflow-x-auto focus-within:overflow-x-auto px-2 pt-6 sm:pt-6"
bookcase track: class="flex w-max gap-[0.85rem] sm:gap-[1.1rem]"
bookcase shelf: class="h-[1.35rem] sm:h-[1.65rem]"
```

The bookcase must remain clipped inside its viewport. On hover or focus, the viewport should pause the animation and allow manual horizontal scrolling. No page-level horizontal scrollbar is acceptable.

### Book Shape

- Use a taller, wider viewBox, recommended around `0 0 210 160`.
- Keep a broad front cover face.
- Add a visible right-side page block on every variant.
- Add page lines on the right block, not only underneath.
- Add slight perspective so the right page block reads as thickness.
- Keep the book sitting on the shelf without looking like a flat card.

Use these approximate geometry zones in the `210 x 160` coordinate system:

- Cast shadow: `x=18 y=142 width=170 height=12`.
- Page block on the right: starts around `x=152`, width `36-42`, height `98-112`.
- Front cover: starts around `x=18`, width `142-150`, height `110-120`.
- Left hinge detail: starts around `x=18`, width `14-20`.
- Protected title panel: around `x=50 y=52 width=96 height=54`.
- Do not render a visible author strip or footer strip on the book face.

Every variant must share this same core silhouette so the shelf feels intentional and consistent.

Right page block requirements:

- Present in all variants.
- Clearly visible to the right of the cover.
- Use light paper colors such as `#fff7ed`, `#fefce8`, `#e7e5e4`, or `#d6d3d1`.
- Include 4-7 short horizontal page lines on the right block.
- Include a darker right edge or page shadow.
- Stay behind the cover group so the opening effect can reveal it slightly.

Avoid long vertical title spines, rotated title text, decoration crossing the title panel, page lines under the title panel, and tiny text that only works on desktop.

### Title Area

Every variant must reserve a clean middle title panel:

- Draw variant decoration first.
- Draw the title panel after decoration so nothing crosses over it.
- Put the title panel inside the cover group so it moves with the cover during hover.
- The title panel should be centered, high contrast, and wide enough for 1-3 lines.
- No decorative lines, page marks, or shine effects should run across the title text.
- Long titles should be deterministically split and trimmed.

Recommended title layout:

```text
panel x=50 y=52 width=96 height=54 rx=8
title center x=98
title start y = 74 - ((lineCount - 1) * 6)
max line length: 12 chars
max lines: 3
```

For one-word template titles, keep them on one line. For long titles, prefer two or three neat lines over tiny text.

Titles to manually inspect:
  - `Ship`
  - `TraceBack`
  - `ImprovedDb`
  - `KinoJoin`
  - `The Great Gatsby`
  - `Pride and Prejudice`
  - `To Kill a Mockingbird`

### Three Variants

Keep exactly three variants:

1. Hardback
   - Overall feel: quiet clothbound book.
   - Front cover: rounded rectangle, approximately `x=18 y=24 width=146 height=114 rx=10`.
   - Right pages: visible behind the cover, approximately `x=152 y=34 width=38 height=96`.
   - Page lines: 5-6 short horizontal lines on the right block.
   - Left hinge: narrow darker strip, approximately `x=20 y=30 width=18 height=102 rx=7`.
   - Cover details: 2-3 restrained horizontal bands above or below the title panel only.
   - Title panel: quiet cream/gold plaque, centered and uninterrupted.
   - Palette: deep cover color, light paper, cream title panel, subtle gold linework.

2. Paperback
   - Overall feel: clean modern paperback.
   - Front cover: rounded rectangle sharing the same core silhouette as the other variants, approximately `x=18 y=24 width=148 height=114 rx=10`.
   - Right pages: rounded page block, approximately `x=150 y=34 width=46 height=102 rx=9`.
   - Page lines: 5-7 short horizontal lines on the right page block.
   - Cover details: one bold color band at top or bottom, never through the title panel.
   - Title panel: simple light rectangle centered on the cover face.
   - Palette: brighter cover color, muted page block, simple accent band.

3. Technical Manual
   - Overall feel: precise template/manual book.
   - Front cover: geometric rectangle, approximately `x=18 y=22 width=148 height=116 rx=6`.
   - Right pages: squared page block, approximately `x=154 y=31 width=36 height=104`.
   - Page lines: 4-6 thin ruled lines on the page block.
   - Index tabs: 2-3 small tabs on the right edge of the page block.
   - Cover details: thin rule lines and small corner marks outside the title panel.
   - Title panel: crisp white or pale panel, centered and uninterrupted.
   - Palette: strong cover color, white/cream panel, subtle grid details.

Variant selection must remain deterministic:

- `StableSeed % 3`.
- No runtime randomness.
- SSR and hydrated output must match.

### Hover/Open Interaction

Hover/focus should make the book look like it opens a tiny bit:

- Use two SVG groups:
  - `.book-side-pages`: the right page block and page lines.
  - `.book-side-cover`: the front cover, hinge, title panel, and cover decorations.
- Apply the main motion through CSS on `.book-side-link:hover .book-side-cover`.
- The cover should rotate/translate by a tiny amount only.
- Use `transform-box: fill-box` and `transform-origin: 12% 52%` or equivalent SVG-safe CSS.
- The title panel must move with the cover, not separately.
- The page block can shift right by only `2-3px`.
- The cover should visually open no more than `3-5px`.
- The shelf item may lift slightly, but should not rotate enough to make text feel slanted.
- Focus-visible should use the same open effect plus a clear outline.
- Respect `prefers-reduced-motion: reduce`.

Recommended CSS direction:

```razor
<a class="group block flex-none transition-transform duration-200 hover:-translate-y-1 focus-visible:-translate-y-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600">
    <svg class="h-[8.95rem] w-[11.75rem] sm:h-[10.65rem] sm:w-[14rem]">
        <g class="transition-transform duration-200 group-hover:translate-x-[3px] group-focus-visible:translate-x-[3px] motion-reduce:transform-none">
            <!-- pages -->
        </g>
        <g class="origin-left transition-transform duration-200 group-hover:-translate-x-0.5 group-hover:-translate-y-px group-hover:-rotate-[0.8deg] group-focus-visible:-translate-x-0.5 group-focus-visible:-translate-y-px group-focus-visible:-rotate-[0.8deg] motion-reduce:transform-none">
            <!-- cover, title panel, cover decoration -->
        </g>
    </svg>
</a>
```

If the cover transform makes title text even slightly messy in screenshots, reduce the cover motion until it is clean. If needed, fall back to page-block shift plus a tiny whole-item lift only.

Tailwind constraint:

- Use Tailwind utilities and arbitrary values in Razor markup for sizing, spacing, transitions, transforms, focus rings, and reduced-motion behavior.
- Do not introduce custom selectors such as `.book-side-cover` in `app.css`; if a semantic class is needed for readability, keep Tailwind utilities alongside it and avoid relying on separate CSS.
- Tailwind group hover should drive the open effect.

## Implementation Plan

### Phase 1 - Baseline

- [x] Status: Completed
- [x] Confirm current working tree status.
- [x] Confirm deployment paths are untouched.
- [x] Run `dotnet build BlazorAutoApp.sln`.
- [x] Inspect current generated home screenshots if available.

Validation:

- [x] `git status --short -- Deployment .github docker-compose.yml Dockerfile`
- [x] `dotnet build BlazorAutoApp.sln`

### Phase 2 - Rebuild `BookSideView`

- [x] Status: Completed
- [x] Replace the current SVG geometry with a taller side-view book using `viewBox="0 0 210 160"`.
- [x] Create exactly three variants.
- [x] Add a right-side page block to every variant.
- [x] Add page-line details on right page blocks.
- [x] Keep the left hinge/spine as a small detail only.
- [x] Draw a protected title panel after all variant decoration.
- [x] Keep the protected title panel inside `.book-side-cover`.
- [x] Remove the visible author/footer strip from the SVG.
- [x] Keep optional URL marker subtle and outside the title panel.
- [x] Ensure `Ship`, `TraceBack`, `ImprovedDb`, and `KinoJoin` display cleanly.
- [x] Ensure `Pride and Prejudice` and `To Kill a Mockingbird` display cleanly.

Validation:

- [x] `dotnet build BlazorAutoApp.sln`
- [x] Razor/SVG compiles without parser issues.
- [x] Screenshot review confirms the right page block is visible for all three variants.

### Phase 3 - Hover Open Effect

- [x] Status: Completed
- [x] Add an SVG group around the front cover, title panel, hinge, and cover decoration.
- [x] Add an SVG group around the right page block and page lines.
- [x] Use Tailwind `group-hover:*`, `group-focus-visible:*`, and `motion-reduce:*` utilities for movement.
- [x] Apply subtle open transform on hover/focus: cover moves no more than `3-5px` visually.
- [x] Shift page block right by only `2-3px`.
- [x] Keep the title panel inside the moving cover group.
- [x] Keep motion small enough that text remains readable.
- [x] Add reduced-motion fallback.
- [x] If title readability is worse on hover, reduce motion until it is clean.

Validation:

- [x] Manual desktop screenshot review.
- [x] Manual mobile screenshot review.
- [x] Hover/focus does not cause title overlap, clipping, skewed-looking title text, or panel escape.

### Phase 4 - Layout Polish

- [x] Status: Completed
- [x] Set desktop book size around `14rem x 10.65rem` using Tailwind arbitrary sizing classes.
- [x] Set mobile book size around `11.75rem x 8.95rem` using Tailwind responsive utility classes.
- [x] Adjust bookcase viewport padding and shelf height.
- [x] Tune animation duration for fewer/larger books, likely `80-96s`.
- [x] Let hover/focus pause the animation and expose manual horizontal scrolling inside the bookcase viewport.
- [x] Ensure no horizontal page overflow.
- [x] Ensure the bookcase does not crowd render-mode diagnostics.
- [x] Ensure mobile still shows the bookcase cleanly.
- [x] Accept fewer visible books: approximately 5-7 desktop and 2-3 mobile.

Validation:

- [x] Desktop screenshot.
- [x] Mobile screenshot at `390x844`.

### Phase 5 - Seed Check

- [x] Status: Completed
- [x] Keep fixed seed titles:
  - `Ship`
  - `TraceBack`
  - `ImprovedDb`
  - `KinoJoin`
- [x] Verify they remain first in local seed order.
- [x] Verify idempotency after restart.

Validation:

- [x] `/api/books` includes all four fixed titles.
- [x] Seed count is unchanged after app restart.

### Phase 6 - Tests

- [x] Status: Completed
- [x] Run full test project.
- [x] Run visible desktop E2E.
- [x] Run visible mobile E2E.
- [x] Inspect generated home screenshots.
- [x] Confirm anonymous home still hides `Add Book` and `Saved books`.

Validation:

- [x] `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`
- [x] visible desktop E2E
- [x] visible mobile E2E

### Phase 7 - Final Verification

- [x] Status: Completed
- [x] Run formatting check.
- [x] Run whitespace diff check.
- [x] Smoke-check routes.
- [x] Confirm stale spine/bookback terms do not remain in active code.
- [x] Confirm deployment paths are untouched.

Validation:

- [x] `dotnet format BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`
- [x] `rg -n "book-spine|BookSpine|bookback|spine" BlazorAutoApp BlazorAutoApp.Client BlazorAutoApp.Test --glob '!**/bin/**' --glob '!**/obj/**'`
- [x] `/books` returns `200`
- [x] `/api/books` returns `200`
- [x] `/movies` returns `404`
- [x] `/api/movies` returns `404`

## Acceptance Criteria

- [x] Books look clearly like side-view books, not cards or spines.
- [x] Every variant has visible pages on the right.
- [x] Every variant has a clean middle title panel.
- [x] Title text does not get drawn over by decoration.
- [x] Visible SVG does not render authors or a footer strip.
- [x] Hover/focus opens the book a tiny bit.
- [x] Hover/focus allows manual scrolling of the infinite bookcase.
- [x] Hover/focus does not harm title readability.
- [x] Books are larger and more polished.
- [x] Exactly three variants exist.
- [x] Fixed seed titles remain present.
- [x] Tests pass.
- [x] Visible desktop and mobile E2E pass.
- [x] Deployment files remain untouched.

## Notes For Execution

- Prefer grouping cover elements in SVG so Tailwind group-hover utilities can animate the cover separately from the page block.
- Keep the title panel in the cover group, so it opens with the cover and remains aligned.
- If SVG transforms become inconsistent between browsers, fall back to a simpler full-item lift plus tiny internal page-shadow shift.
- The final call should include screenshot inspection, not only test output.
