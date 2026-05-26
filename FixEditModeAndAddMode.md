# Fix Edit Mode And Add Mode

## Goal

Make Add Book and Edit Book look like the current polished book view mode.

Today `BookPageView.razor` is the nice `560 x 720` SVG book page, while `BookPageEditor.razor` is a separate HTML card that only loosely resembles the same design. This should be corrected so view, edit, and add all feel like the same object.

The end state:

- viewing a book shows the current nice formatted SVG page,
- editing a book shows the same page shape, spine, page lines, control positions, and overall proportions,
- adding a book shows the same interface as editing an empty book,
- the modal remains on the home/books page with transparent background,
- the existing CRUD flow and test IDs keep working.

## Current Findings

Status: done

Relevant files:

- `BlazorAutoApp.Client/Features/Books/BookPage/BookPageView.razor`
- `BlazorAutoApp.Client/Features/Books/BookPage/BookPageEditor.razor`
- `BlazorAutoApp.Client/Features/Books/BookModal/BookModalHost.razor`
- `BlazorAutoApp.Client/Features/Books/BookPage/BookPageEditorModel.cs`
- `BlazorAutoApp.Client/Features/Books/BookPage/BookPageTextLayout.cs`
- `BlazorAutoApp.Test/E2E/Features/Books/BooksE2ETests.cs`
- `BlazorAutoApp.Test/E2E/VisualRegression/VisualSnapshotE2ETests.cs`

Current mismatch:

- `BookPageView` renders a full SVG book page with paper gradient, spine, page lines, close/edit/delete controls, title panel, author, and site action.
- `BookPageView` currently includes `<rect width="560" height="720" fill="#f8fafc"></rect>`, which creates a grey rectangular backing around the book. That backing should be transparent in the final shared chrome.
- `BookPageEditor` renders an HTML section/card with a different max width, rounded box, different spacing, different close button, and form controls outside the SVG language.
- Add mode and edit mode already share `BookPageEditor`, so fixing that component is the main path.

## Design Direction

Status: done

Use one shared book-page chrome for view/edit/add.

Preferred implementation:

- Extract the common SVG page shell from `BookPageView.razor` into a reusable component, for example `BookPageFrame.razor`.
- Keep the exact current `560 x 720` viewBox, paper/spine gradients, page shadow, side page hints, page lines, and control coordinate system.
- Remove the grey full-SVG background rectangle or make it transparent so the modal background remains invisible around the book page.
- Let the chrome accept small render fragments for:
  - top-right controls,
  - main title/content panel,
  - lower action area.
- Refactor `BookPageView` to render through the shared chrome without changing its visual result.
- Refactor `BookPageEditor` to render through the same chrome and place form fields inside SVG `foreignObject` regions so inputs can remain accessible HTML controls while the visual container remains the same book page.

If `foreignObject` causes unacceptable layout or browser behavior during Playwright checks, use an SVG background with absolutely positioned HTML controls on top, but keep exact dimensions and coordinates matched to the current view mode. Do not return to the current separate HTML card look.

## Editor Layout

Status: done

The editor should match view mode closely:

- same outer width as view mode: `w-[min(calc(100vw-2rem),35rem)]`,
- same page shape and paper/spine details,
- no grey rectangular SVG backing outside the page silhouette,
- same top-right close button location and icon styling,
- same title card location around `x=108 y=132 width=344 height=252`,
- same lower action area around the current “Go to site” button position.

Fields:

- Title goes in the title card as the main, large field.
- Author goes below title in the same card, visually where view mode displays author.
- URL goes in the lower action area, styled as a compact site field rather than a large form row.
- Save action sits in the lower action area and reads `Close and save`.

Add mode:

- uses the same editor surface,
- starts with empty fields,
- still has `data-testid="book-title"`, `book-author`, `book-url`, `book-save`, and `book-back`.

Edit mode:

- uses the same editor surface,
- preloads existing book values,
- close without save returns to `/books`,
- save updates and returns to `/books`.

## Validation And Error Display

Status: done

Keep validation behavior, but make errors fit the book-page design.

Required behavior:

- required title validation remains active,
- URL validation remains active,
- `_saveError` still appears when saving fails,
- validation messages do not overlap the title, author, URL, or buttons on mobile.

Implementation guidance:

- Place summary/error text in a small panel below the main card or above the lower action area inside the page.
- Keep error text concise and visually subordinate.
- Avoid adding instructional text that explains the UI.

## Reuse And File Shape

Status: done

Keep the Books slice clean.

Expected shape:

- `BookPageView.razor` becomes a thin consumer of shared page chrome.
- `BookPageEditor.razor` becomes a thin consumer of the same shared page chrome.
- shared SVG shell/control helpers live under `Features/Books/BookPage`.
- no new generic `Pages` folder or cross-feature UI bucket.
- no duplicated SVG page shell in view and editor after the refactor.

Possible new files:

- `BookPageFrame.razor`
- `BookPageControlIcons.razor` or a small static helper if it genuinely removes duplication

Only add helper files if the result is simpler than leaving small local render fragments.

## Visual Confirmation

Status: done

Capture screenshots before and after.

Before:

- `TestResults/FixEditModeAndAddMode/Before/view-desktop.png`
- `TestResults/FixEditModeAndAddMode/Before/add-desktop.png`
- `TestResults/FixEditModeAndAddMode/Before/edit-desktop.png`
- `TestResults/FixEditModeAndAddMode/Before/add-mobile.png`
- `TestResults/FixEditModeAndAddMode/Before/edit-mobile.png`

After:

- `TestResults/FixEditModeAndAddMode/After/view-desktop.png`
- `TestResults/FixEditModeAndAddMode/After/add-desktop.png`
- `TestResults/FixEditModeAndAddMode/After/edit-desktop.png`
- `TestResults/FixEditModeAndAddMode/After/add-mobile.png`
- `TestResults/FixEditModeAndAddMode/After/edit-mobile.png`

Acceptance criteria:

- Add/edit visibly look like the same book page as view mode.
- The area around the page silhouette is transparent, not grey.
- The title card, close button, spine, page lines, and lower action area align with view mode.
- Mobile text remains readable and no controls overlap.
- The save button is obvious but does not look like an unrelated dashboard button.
- The URL field does not force a long URL to overflow the book.

## E2E Updates

Status: done

Keep existing Books E2E behavior passing.

Tests should continue to verify:

- anonymous users cannot add books,
- logged-in users can add books,
- created books appear in `Your Bookcase`,
- refresh preserves created books,
- user book view opens,
- edit mode preloads values,
- cancel/close from edit returns to the bookcase,
- save updates the book,
- delete works from view mode,
- the saved-books table remains absent.

Add focused assertions if useful:

- `book-page-editor` is visible in add/edit,
- `book-page-editor` uses the same main page dimensions as `book-page-view`,
- mobile add/edit screenshots capture without overlap.

## Verification

Status: done

Run:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- visual screenshot capture for add/edit/view
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query for temporary books

## Non-Goals

- Do not change deployment.
- Do not change database schema.
- Do not change bookcase SVG designs.
- Do not restore the saved-books table.
- Do not change authentication or authorization.
- Do not introduce a new generic UI framework for one editor.
