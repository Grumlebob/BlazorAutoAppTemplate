# Book Shelf Renderer Cleanup

## Goal

Status: Completed

Make the bookcase rendering simpler, more honest, and cheaper without making the SVG code ugly.

The shelf should render the books it actually has. If there are five author books, only those five books should exist in the DOM and the user should scroll to the end. It should not repeat them just to create an artificial infinite loop.

Also clean up the book cover renderer internals:

- Replace manual `MarkupString` title generation with normal Razor SVG markup.
- Compute the `BookSideView` render model once per parameter update instead of through several computed properties.

Result: The shelf now renders finite book lists without duplicate copies, and the renderer cleanup was completed without converting SVG artwork into hard-to-read strings.

## Non-Goals

Status: Completed

- Do not redesign the book covers.
- Do not remove the hover/opening animation.
- Do not add JavaScript virtualization.
- Do not convert the SVG artwork into giant hard-to-read strings.
- Do not remove Interactive Auto or change app render mode behavior.
- Do not touch deployment, database, Redis, Cloudflare, or identity.

Result: These areas were not changed.

## Phase 1 - Finite Shelf Rendering

Status: Completed

Current problem:

- `BookcaseShelfItems.Build` repeats books up to `DefaultAutoScrollMinItems`.
- `BookcaseShelf` renders two passes when `AutoScroll` is enabled.
- With five author books, this creates many repeated book SVGs and makes the shelf look infinite even though the content is finite.

Desired behavior:

- Render each book once.
- Keep horizontal scrolling.
- Keep the shelf visually polished when it has few books.
- Stop at the end of the actual book list.
- Remove duplicate-pass animation behavior from normal shelves.

Implementation notes:

- Simplify `BookcaseShelfItems.Build` so it no longer pads or repeats books.
- Remove `DefaultAutoScrollMinItems` if it becomes unused.
- Remove `ShelfPassCount` if finite rendering makes it unnecessary.
- Replace the infinite `animate-bookcase-scroll` track behavior with a normal horizontal scrolling shelf.
- Keep the hidden scrollbar and hover/focus scroll behavior that already works.
- Keep `content-visibility:auto` on book frames.

Acceptance:

- The Authors Bookcase renders exactly five books when the catalog has five books.
- No hidden duplicate copies exist for those five books.
- The shelf scrolls horizontally and stops at the end.
- The user bookcase still renders exactly the user books, with no repeats.
- Mobile and desktop layouts remain readable.

Result:

- `BookcaseShelfItems.Build` now caps only when requested and never pads or repeats books.
- `BookcaseShelf` renders a single finite pass.
- The old duplicate-pass animation classes were removed from the component.
- The generated Tailwind CSS no longer contains `animate-bookcase-scroll` or `bookcase-scroll`.
- `AutoScroll` was renamed to `LimitItems` because the component no longer autoscrolls.
- Local SSR homepage output changed from roughly `144 KB`, `29` SVGs, `28` defs, and `28` author book nodes to roughly `39 KB`, `6` SVGs, `5` defs, and `5` author book nodes.

## Phase 2 - Clean SVG Title Rendering

Status: Completed

Current problem:

- `BookCoverRenderer` builds SVG `<text>` and `<tspan>` markup as a string.
- It manually HTML-encodes text and returns a `MarkupString`.
- This works, but it is less idiomatic Razor and makes the renderer easier to accidentally break.

Desired behavior:

- Render SVG text with normal Razor markup.
- Keep title line wrapping exactly as it is today.
- Keep title positioning, font size, font weight, and fill color.
- Keep encoded/safe output through Razor's normal rendering.

Implementation notes:

- Replace `TitleTextMarkup` and `BuildTitleTextMarkup`.
- Use a `<text>` element with a `for` loop over `TitleLines`.
- Use `dy` only after the first line.
- Preserve `x`, `y`, `text-anchor`, `font-family`, `font-size`, `font-weight`, `fill`, and `letter-spacing`.

Acceptance:

- Book titles display identically before and after the change.
- Long and multiline titles still stay inside the title plate.
- No `MarkupString` remains in `BookCoverRenderer`.

Result: `BookCoverRenderer` now renders the title plate text with normal Razor SVG `<text>` and `<tspan>` markup. Manual `MarkupString` title generation and manual HTML encoding were removed from this component.

## Phase 3 - Compute BookSideView Render Model Once

Status: Completed

Current problem:

- `BookSideView` computes `Design`, `Theme`, `TitleLines`, `TitleY`, and `TitleFontSize` through separate computed properties.
- Razor can call these repeatedly during rendering.
- The work is small, but the component is rendered many times on shelves and demos.

Desired behavior:

- Compute the cover inputs once when parameters change.
- Pass stable, simple values into `BookCoverRenderer`.
- Keep deterministic design and theme selection.

Implementation notes:

- Add a small private render model record or fields inside `BookSideView`.
- Populate it in `OnParametersSet`.
- Keep the current stable seed logic.
- Keep title-based design selection so the same title remains visually stable.
- Avoid introducing a shared abstraction unless it removes real duplication.

Acceptance:

- Existing books keep stable designs and colors across refreshes.
- Author and user shelves behave the same way.
- The code is easier to read than the current collection of computed properties.

Result: `BookSideView` now computes a private render model in `OnParametersSet` and passes stable values into `BookCoverRenderer`.

## Phase 4 - Tests

Status: Completed

Unit/component-level checks:

- Update `BookcaseShelfItemsTests` so finite shelves do not repeat books.
- Add or update coverage for the exact visible item count behavior.
- Add a small deterministic `BookSideView`-adjacent test only if existing test structure supports it cleanly.

End-to-end checks:

- Run the visible Playwright book flow locally.
- Confirm the homepage bookcase is scrollable on desktop and mobile.
- Confirm clicking author books and user books still opens the modal correctly.
- Confirm create, edit, delete still update the user bookcase without refresh workarounds.

Performance checks:

- Compare local SSR output before/after if practical:
  - total HTML bytes
  - number of `<svg>` elements
  - number of `<defs>` blocks
  - number of duplicate title nodes
- Re-run local Lighthouse spot checks if the implementation changes generated CSS or layout behavior.

Result:

- `BookcaseShelfItemsTests` now asserts finite shelf behavior and verifies that small booksets are not padded.
- Full test suite passed: `76` passed, `5` skipped, `0` failed.
- Visible Playwright E2E passed against `https://127.0.0.1:7186`.
- Local Lighthouse spot check reports:
  - `/` mobile: Performance `65`, Accessibility `100`, Best Practices `100`, SEO `100`.
  - `/books/design-demos` mobile: Performance `66`, Accessibility `100`, Best Practices `100`, SEO `100`.
  - Reports: `TestResults/Lighthouse/local-bookshelf-renderer-cleanup-20260528-105057`.

## Phase 5 - Validation

Status: Completed

Run after implementation:

```powershell
npm --prefix .\BlazorAutoApp.Client run css:build
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
git diff --check
.\RunLocal.ps1 -NoBrowser
```

If UI behavior changes, also run visible E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
$env:E2E_HEADLESS='0'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter FullyQualifiedName~E2E
```

Result:

- `npm --prefix .\BlazorAutoApp.Client run css:build` passed.
- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore` passed.
- `dotnet test .\BlazorAutoApp.sln -c Release --no-build` passed.
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore` passed.
- `git diff --check` passed.
- `docker compose up -d --build web` rebuilt and recreated the web container.
- `.\RunLocal.ps1 -NoBrowser -NoBuild -TimeoutSeconds 30` passed after the explicit rebuild.
- Local app is running at `https://localhost:7186`.

## Done Criteria

Status: Completed

- No repeated book DOM is generated for normal shelves.
- A five-book author shelf renders five books and scrolls to the end.
- `BookCoverRenderer` no longer uses manual `MarkupString` title generation.
- `BookSideView` computes cover inputs once per parameter update.
- Tests and local validation pass.
- The result is simpler code, not a clever optimization layer.

Result: Done.
