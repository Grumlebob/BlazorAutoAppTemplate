# Fix Coherent Design

Status: completed. The Blazor approval demos, coherent production bookcase artwork, home-hosted modal flow, unified view/edit/add surface, data refresh, tests, and plan cleanup have all been implemented and verified.

## Current Findings

- `BookPageView` keeps the approved `560 x 720` SVG page shape.
- The old landscape `BookSideView` was replaced with the coherent portrait shelf artwork.
- The bookcase URL marker was removed.
- View, edit, and create now open as query-backed home-page modals.
- The editor title uses a mobile-readable two-line title field.
- The old static `Plans/*.html` demo was removed. The current demos are real Blazor approval pages under `Features/Books/DesignDemos`.
- Forced-open page alignment was repaired and visually inspected: the visible page block, lower cover curve, and shadow now read as one physical book.

## Non-Goals

- Do not touch deployment in this plan.
- Do not change database schema, migration strategy, API ownership, Redis invalidation, or authentication fundamentals.
- Do not add uploads or image functionality.
- Do not redesign the NiceEdit page visual language. Keep the existing page/book detail style, only adapt it for modal use, create/edit reuse, and mobile readability.
- Do not introduce component CSS files for the app UI. App styling should remain Tailwind utilities plus SVG attributes.

## Target Experience

- The home page remains the base experience at `/` and `/books`.
- Clicking a book opens a transparent-background popup over the home page.
- The popup background is invisible: no dark dimming layer, no blur, no card behind the book page.
- View mode has a clear `Close` action.
- Edit and add modes use the same book-page interface and have a primary `Close and save` action.
- Edit and add modes may also have a secondary `Close` action for discard, but the primary save action must be named `Close and save`.
- Add Book should open the same interface as editing an empty book.
- User books can show the pencil/edit affordance. Author books stay static and never expose edit mode.
- The bookcase SVGs and the modal page should share the same `7:9` visual family so the transition feels coherent.
- Bookcase books should show title only. No author text and no URL arrow on the bookcase.
- Manual horizontal scrolling must still work when hovering or focusing the infinite bookcase, with the scrollbar hidden.

## Route and State Strategy

- Use the home page as the modal host with query-backed modal state.
- Proposed query shape:
  - Author view: `/books?bookSource=author&bookId=ship&bookMode=view`
  - User view: `/books?bookSource=user&bookId=123&bookMode=view`
  - User edit: `/books?bookSource=user&bookId=123&bookMode=edit`
  - User create: `/books?bookSource=user&bookMode=create`
- Opening a book should be a normal link so browser back closes the popup by returning to the previous URL.
- Closing the popup should navigate back to `/books` or `/` without modal query parameters.
- Old create/edit/details page surfaces should be removed as user-facing UI. If temporary compatibility shims are kept, they must immediately navigate to the home modal and render no standalone page.

## Phase 1: Approval Demo Redesign

Done: [x]
Tested: [x]
Approval: [x]
Rework completed after rendered inspection: [x]

Tasks:

- Replace the old `210 x 160` demo concepts with a real Blazor `Features/Books/DesignDemos` subslice.
- Update `Plans/MoreBooksDesignDemos.md` to describe the new dimensions and approval scope.
- Use a shared motion-canvas coordinate system, currently `216 x 247`, with a large `7:9` book core matching the NiceEdit proportion and extra right-side inspection space.
- Render demo books at roughly:
  - Mobile preview: `8.75rem x 11.25rem`
  - Desktop preview: `10.5rem x 13.5rem`
- Keep the approved design directions close to what exists:
  - Cloth Hardback
  - Modern Paperback
  - Technical Manual
  - Decorative Hardcover
  - Library Ledger
  - Field Notebook
- Remove the URL marker from every demo.
- Keep title-only panels, no author text.
- Include real test titles in the demo, including `The Great Gatsby`, `Ship`, `TraceBack`, `ImprovedDb`, `KinoJoin`, and one deliberately long title.
- Ensure every design reserves a clean title area with no ornament crossing through the text.
- Keep page-edge hints subtle and aligned with the NiceEdit page direction.
- Do not add a visual footer strip to the books.

Rendered inspection findings from the first draft:

- Desktop screenshot captured at `1440 x 1200`: `TestResults/DesignReview/MoreBooksDesktop.png`.
- Mobile screenshot captured at `390 x 1200`: `TestResults/DesignReview/MoreBooksMobile.png`.
- The stage padding exists, but the SVG artwork itself does not have enough internal right-side motion gutter.
- On mobile, the book plus stage padding is too wide, so the right page area visually ends at the preview border.
- The page strip is too close to the cover edge and is partly buried by the cover, making it hard to read as pages.
- The hover effect moves the right-side page marks without enough continuous visible page surface, so the page lines can appear detached.
- The temporary bottom page-stack idea was wrong and must not be used.

Rework verification artifacts:

- Final normal desktop screenshot: `TestResults/DesignReview/MoreBooksDesktopV8.png`.
- Final forced-open desktop screenshot: `TestResults/DesignReview/MoreBooksDesktopOpenV8.png`.
- Final normal mobile screenshot: `TestResults/DesignReview/MoreBooksMobileV8.png`.
- Final forced-open mobile screenshot: `TestResults/DesignReview/MoreBooksMobileOpenV8.png`.
- Final validation passed:
  - `dotnet build .\BlazorAutoApp.sln`
  - `dotnet test .\BlazorAutoApp.sln --no-build`
  - `dotnet format --verify-no-changes --verbosity minimal --no-restore`
  - `git diff --check`

Phase 1A: self-inspected page-gutter repair:

- Keep the core book shape close to the approved portrait size, but distinguish the book core from the SVG motion canvas.
- Expand the SVG viewBox or add an internal artwork group so every demo has a real right-side gutter for page visibility and hover motion.
- Target at least `18-24` SVG units of visible right-side empty canvas after the page edge at rest.
- Target at least `10-16` SVG units of visible right-side empty canvas after the page edge in forced-hover state.
- Move the page block slightly left and make its page lines begin near the hinge, so the line starts are hidden under or directly connected to the cover edge instead of floating with a gap.
- Keep the page lines long enough to visibly run from the hinge area to the outer page edge.
- Reduce mobile rendered width or stage padding enough that a `390px` viewport shows the entire book, the page edge, and the motion gutter without horizontal clipping.
- Keep desktop rendered size large, but do not let size override readability of the page edge.
- Remove the dark cloth-hardback spine strip permanently.
- Make the cloth-hardback title plate larger by extending it upward, downward, and leftward, but keep it inside the cover and clear of ornaments.
- Do not add bottom page-stack shapes unless they are part of a coherent full-volume redesign.

Phase 1B: standalone approval pages:

Done: [x]
Tested: [x]

- Add a real standalone approval page for each book design, not only the compact overview card.
- Each standalone page must be reachable by a direct URL from the Blazor overview route.
- Each standalone page must show one design large enough for careful inspection on desktop.
- Each standalone page must remain usable on mobile.
- Each standalone page must support normal and forced-open inspection states.
- The standalone design must match the overview design geometry, including restrained page motion, squared page-left edge, no dark right-side line, and right-side gutter.
- The overview page remains the design index, while the standalone page is the detailed review surface.
- Implemented as:
  - `/books/design-demos`
  - `/books/design-demos/{designId}`
  - `/books/design-demos/{designId}?open=true`
- The Blazor subslice files are:
  - `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCatalog.cs`
  - `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCover.razor`
  - `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemos.razor`
  - `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoDetails.razor`
- Static `Plans/MoreBooksDesignDemos.html` and `Plans/MoreBooksDesignDemoPage.html` were removed so the repo has one current demo path.
- Standalone validation passed:
  - `dotnet build .\BlazorAutoApp.sln`
  - `dotnet test .\BlazorAutoApp.sln --no-build`
  - `dotnet format --verify-no-changes --verbosity minimal --no-restore`
  - `git diff --check`

Phase 1C: open-state page alignment repair:

Done: [x]
Tested: [x]
Visually inspected: [x]

- Treated the open-state geometry as not approved until the repaired screenshots passed inspection.
- Repair the SVG so the page block, cover edge, and bottom shadow read as one coherent book at rest, hover, focus, and forced-open state.
- The page block must align with the book's lower edge in every design. It must not leave a blank bottom gap between the cover and pages.
- The page lines must stay visually attached to the book volume in all formats; no line may appear to float, shoot out, or stop before it reaches the covered hinge area.
- The page surface should sit behind the cover with a believable squared-left hidden edge and a consistent right-side curve. Avoid a dark right edge.
- The cover opening motion must be smaller if needed so the pages do not separate from the cover or shadow.
- The bottom shadow must support the combined book volume, not only the cover. Adjust shadow width/position after page alignment is fixed.
- Confirm every variant, not just Cloth Hardback:
  - Cloth Hardback
  - Modern Paperback
  - Technical Manual
  - Decorative Hardcover
  - Library Ledger
  - Field Notebook
- Confirm every viewport and state:
  - overview desktop normal
  - overview desktop hover/focus or forced-open equivalent
  - overview mobile normal
  - overview mobile hover/focus or forced-open equivalent
  - standalone desktop normal
  - standalone desktop forced-open
  - standalone mobile normal
  - standalone mobile forced-open
- Always inspect rendered screenshots before marking this phase done. A passing build, CSS generation, or E2E run is not enough.
- Save the final inspection screenshots under `TestResults/DesignReview/` and reference them here when done.

Final inspection artifacts:

- `TestResults/DesignReview/CoherentDemoOverviewDesktop.png`
- `TestResults/DesignReview/CoherentDemoOverviewMobile.png`
- `TestResults/DesignReview/CoherentDemoClothOpenDesktop.png`
- `TestResults/DesignReview/CoherentDemoClothOpenMobile.png`
- `TestResults/DesignReview/CoherentBooksHomeDesktop.png`
- `TestResults/DesignReview/CoherentBooksHomeMobile.png`
- `BlazorAutoApp.Test/TestResults/Playwright/Snapshots/390x844-home.png`
- `BlazorAutoApp.Test/TestResults/Playwright/Snapshots/390x844-books-details.png`
- `BlazorAutoApp.Test/TestResults/Playwright/Snapshots/390x844-books-edit.png`

Phase 1A screenshot gate:

- Capture a normal desktop screenshot of `/books/design-demos`.
- Capture a normal mobile screenshot at `390px` width.
- Capture a forced-hover desktop screenshot where all `.pages` and `.cover` transforms are applied.
- Capture a forced-hover mobile screenshot at `390px` width.
- Inspect screenshots before returning the design to the user.
- Acceptance for this repair is visual, not just code-based:
  - The right-side page edge must have clear breathing room from the preview border.
  - Page lines must look connected to the book volume at rest and in forced-hover.
  - No page lines may appear to shoot out detached from the cover.
  - The page block, bottom cover curve, and shadow must align so the open state looks like one physical book.
  - There must be no blank lower gap where pages should continue under the cover.
  - The book must be fully visible on mobile.
  - The cloth hardback must not have a dark spine strip.
  - The cloth title plate must be visibly larger and more usable.

Phase testing gate:

- Open `/books/design-demos` manually at desktop width.
- Open the same demo at a mobile-like width near `390 x 844`.
- Confirm all six variants have coherent rounded corners, aligned panels, no text overlap, no URL marker, and a believable relation to the NiceEdit page.
- Run:

```powershell
dotnet build .\BlazorAutoApp.sln
dotnet test .\BlazorAutoApp.sln --no-build
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --check
```

Approval checkpoint:

- Completed. Implementation proceeded after demo approval and the follow-up request to execute the full plan.

## Phase 2: Shared Artwork Geometry and Title Layout

Done: [x]
Tested: [x]

Tasks:

- Introduce a shared book artwork layout helper inside the Books slice, not a generic cross-app utility.
- Use the same geometry rules for author and user bookcase books.
- Replace ad hoc title wrapping with a deterministic helper that:
  - Handles short titles cleanly.
  - Splits `The Great Gatsby` into readable lines when needed.
  - Trims or wraps long single words without overflowing the protected title panel.
  - Limits shelf title lines to a fixed maximum so layout cannot shift.
- Keep SVG text accessible through `<title>` and useful link labels.
- Keep app styling in Tailwind utilities and SVG attributes.

Phase testing gate:

```powershell
Push-Location .\BlazorAutoApp.Client
npm run css:build
Pop-Location
dotnet build .\BlazorAutoApp.sln
dotnet test .\BlazorAutoApp.sln --no-build
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

## Phase 3: Coherent Bookcase SVG Implementation

Done: [x]
Tested: [x]

Tasks:

- Replace the old landscape `BookSideView` with the approved portrait `7:9` shelf artwork.
- Consider renaming `BookSideView` to a more accurate slice-local name such as `BookCoverView`, unless the rename creates unnecessary churn.
- Use the approved six variants and deterministic variant/color selection.
- Remove `UrlMarker` entirely from the shelf artwork.
- Preserve the hidden-scrollbar manual scroll behavior.
- Preserve infinite auto-scroll pause on hover, focus, and focus-within.
- Ensure author and user bookcases use the same component, dimensions, hover behavior, title layout, and variant rules.
- Keep the current locked author bookcase concept: `The Authors Bookcase`.

Phase testing gate:

```powershell
Push-Location .\BlazorAutoApp.Client
npm run css:build
Pop-Location
dotnet build .\BlazorAutoApp.sln
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

Manual checks:

- On desktop, the bookcase should show fewer, larger portrait books than a tiny list of covers.
- On mobile, titles must remain readable and not overflow the book panel.
- Hover/focus should still pause auto-scroll and allow manual horizontal scrolling.
- No top-right URL arrow should appear on any shelf book.

## Phase 4: Home-Hosted Transparent Modal

Done: [x]
Tested: [x]

Tasks:

- Add a Books slice modal host on the home page.
- Render view, edit, and create modes as a popup over the existing home page.
- Use a transparent fixed overlay. The background should remain visually unchanged.
- Provide accessible dialog semantics:
  - `role="dialog"`
  - `aria-modal="true"`
  - meaningful accessible name
  - Escape closes the popup
  - focus moves into the popup and returns to the triggering control when possible
- Use query-backed links for open state so browser back closes the popup.
- Close should remove the query parameters and return to the home bookcase without a full-page detail surface.
- Add Book should become a home-modal link instead of `/books/create`.
- Book links should become home-modal links instead of full detail-page navigation.

Phase testing gate:

```powershell
Push-Location .\BlazorAutoApp.Client
npm run css:build
Pop-Location
dotnet build .\BlazorAutoApp.sln
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

Manual checks:

- Click author book, see modal, click `Close`, return to same home bookcase context.
- Click user book, see modal, click browser Back, modal closes.
- Click outside behavior should be intentional and not interfere with manual bookcase scrolling.
- The modal must not render a visible dimmer or background panel.

## Phase 5: Unified View, Edit, and Add Surface

Done: [x]
Tested: [x]

Tasks:

- Extract the reusable NiceEdit page shell so view, edit, and add share one visual system.
- Keep `BookPageView` visually consistent with the existing approved page style.
- Rework `BookPageEditor` so edit and add look like the view page, not a separate form card.
- Add mode should be the editor with an empty book model.
- Use `Close and save` as the primary edit/add action text.
- Keep validation visible but visually integrated into the page surface.
- Make mobile title sizing robust:
  - no overlap inside the page title panel
  - no text touching panel edges
  - readable at `390 x 844`
  - long titles degrade by wrapping/trimming, not by overflowing
- Keep the `Go to site` action at the bottom of the page view.
- Keep the pencil edit affordance only for user-owned books in view mode.

Phase testing gate:

```powershell
Push-Location .\BlazorAutoApp.Client
npm run css:build
Pop-Location
dotnet build .\BlazorAutoApp.sln
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

Manual checks:

- Add Book opens the same page-like modal with empty fields.
- Editing a user book opens the same page-like modal with populated fields.
- `Close and save` saves, closes the popup, and refreshes the user bookcase.
- Closing without saving does not mutate the book.
- Author books do not show edit controls.

## Phase 6: Data Flow and Authorization

Done: [x]
Tested: [x]

Tasks:

- Keep author book details resolved from the static author catalog.
- Keep user book view/edit/create resolved through the existing Books API.
- Ensure create/edit modal paths require authentication.
- If an unauthenticated user navigates directly to a create/edit modal query, route through login with a return URL or show the existing login prompt without exposing edit UI.
- After create/edit/delete, refresh the user bookcase state without requiring a manual full page reload.
- Ensure E2E-created books are cleaned up through the existing cleanup support.

Phase testing gate:

```powershell
Push-Location .\BlazorAutoApp.Client
npm run css:build
Pop-Location
dotnet build .\BlazorAutoApp.sln
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

Manual checks:

- Logged-out users see the author bookcase and login prompt, not add/edit controls.
- Logged-in users see author bookcase plus their own bookcase.
- User-created books appear in the user's bookcase immediately after save.
- Cleanup leaves no E2E books behind.

## Phase 7: Playwright Coverage and Visual Confidence

Done: [x]
Tested: [x]

Tasks:

- Update Books E2E tests to cover:
  - Author book opens in home modal.
  - User book opens in home modal.
  - Browser Back closes the modal.
  - `Close` closes view mode.
  - Add Book opens empty page-like modal.
  - `Close and save` creates a book and closes the modal.
  - Pencil opens edit mode for user books only.
  - `Close and save` updates a book and closes the modal.
  - Mobile `390 x 844` viewport has no title overflow or obvious overlap.
  - No URL marker appears on shelf books.
  - Manual scrolling works while auto-scroll is paused.
- Keep E2E headed by default.
- Keep test-created data cleanup explicit and reliable.
- Add visual snapshot coverage for at least:
  - Home bookcase desktop.
  - Home bookcase mobile.
  - View modal mobile.
  - Edit/add modal mobile.

Phase testing gate:

```powershell
Push-Location .\BlazorAutoApp.Client
npm run css:build
Pop-Location
dotnet build .\BlazorAutoApp.sln
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

## Phase 8: Cleanup and Documentation

Done: [x]
Tested: [x]

Tasks:

- Remove stale full-page view/edit/create surfaces if no compatibility shim is needed.
- Remove stale demo notes that describe the old `210 x 160` shape.
- Ensure files stay within the Books vertical slice:
  - `AuthorBookcase`
  - `UserBookcase`
  - `Shared` or a better slice-local artwork folder
  - `BookPage` or a renamed page-shell sub-slice
  - `BookModal` for modal orchestration
- Keep route/page responsibilities minimal and avoid spreading login or book-specific code into unrelated folders.
- Update `TESTING.md` only if any command or E2E setup changes.
- Mark this plan with done/tested statuses as each phase completes.

Final testing gate:

```powershell
Push-Location .\BlazorAutoApp.Client
npm run css:build
Pop-Location
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_WIDTH -ErrorAction SilentlyContinue
Remove-Item Env:\E2E_VIEWPORT_HEIGHT -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
$env:E2E_VIEWPORT_WIDTH='390'
$env:E2E_VIEWPORT_HEIGHT='844'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
dotnet format --verify-no-changes --verbosity minimal --no-restore
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
```

Final verification completed:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- Headed E2E desktop: `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"`
- Headed E2E mobile at `390 x 844`: `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`

## Acceptance Criteria

- `/books/design-demos` shows the approved coherent `7:9` bookcase designs before app implementation.
- The open-state book geometry has been inspected and approved across all six designs, with pages aligned to the cover in desktop and mobile.
- The home bookcase and the modal page feel like the same product language.
- View/edit/add are popup experiences on the home page, not standalone full-page UI.
- Add and edit share the same page-like interface, with `Close and save`.
- Mobile E2E verifies the bookcase and modal are readable at `390 x 844`.
- The bookcase has no URL arrow marker.
- The scrollbar remains hidden while manual horizontal scrolling still works.
- Author books are static. User books support view/edit/create.
- E2E-created user books are cleaned up.
- CSS generation, formatting, build, unit/integration tests, and headed E2E pass after every phase.

## Follow-Up Outside This Plan

- Deployment naming still includes old `ship` terminology and should be handled in a separate deployment-focused plan.
- After this plan lands, review whether any old `/books/create`, `/books/{id}`, or `/books/{id}/edit` compatibility shims should be removed entirely before template release.
