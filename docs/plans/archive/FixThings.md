# Fix Things

Status: completed.

## Context

- The modal close control currently floats above the popup instead of belonging to the book surface.
- The user asked for the close button at the top right of the book; when a user book can be edited, close should sit beside the edit pencil.
- The home page should also expose a button/link to the Blazor design demo page.
- Creating a book can leave `Your Bookcase` showing the empty state, and refreshes can appear to lose recently saved books.

## Non-Goals

- Do not touch deployment.
- Do not change the database schema or migrations.
- Do not remove the author bookcase/user bookcase split.
- Do not add uploads, images, or non-SVG assets.

## Phase 1: Modal Controls Belong To The Book

Done: [x]
Tested: [x]

- Remove the separate top-level modal close row from `BookModalHost`.
- Add a close affordance inside `BookPageView` at the book's top right.
- If a user book has an edit pencil, place close next to that edit pencil.
- Add the same top-right close affordance to `BookPageEditor`.
- Keep `Close and save` as the editor's primary bottom action.
- Remove the duplicate bottom discard close action from the editor.
- Preserve keyboard Escape closing.

## Phase 2: Design Demo Navigation

Done: [x]
Tested: [x]

- Add a clear home-page button/link to `/books/design-demos`.
- Keep it near the existing template/runtime controls, not inside a shelf.
- Add a stable test id so E2E can verify it.

## Phase 3: User Bookcase Consistency

Done: [x]
Tested: [x]

- Add an explicit force-refresh option to list/detail book queries.
- Keep default API caching behavior for ordinary API calls and existing cache tests.
- Make the interactive user bookcase load with force refresh so page reloads do not show stale cached empty lists.
- After create/update, update the visible user bookcase from the saved book data immediately.
- Keep a server/API reconciliation load after save, but do not allow stale cache data to wipe the just-saved book.
- Ensure delete still refreshes the visible shelf and table.

## Phase 4: Tests

Done: [x]
Tested: [x]

- Update Books E2E for the new close-control placement.
- Cover the design demo button.
- Add or update server/API tests for force-refresh behavior.
- Run build, normal tests, CSS generation, headed E2E desktop, headed E2E mobile, formatting, and diff checks.

Verification completed:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- Headed E2E desktop: `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"`
- Headed E2E mobile at `390 x 844`: `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --no-build --filter "Category=E2E"`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`

Visual inspection artifacts:

- `BlazorAutoApp.Test/TestResults/Playwright/Snapshots/390x844-home.png`
- `BlazorAutoApp.Test/TestResults/Playwright/Snapshots/390x844-books-details.png`
- `BlazorAutoApp.Test/TestResults/Playwright/Snapshots/390x844-books-edit.png`

## Acceptance Criteria

- Close is visually part of the book page/editor, at the top right.
- In view mode with edit available, close sits beside the pencil.
- Add Book saves and immediately shows the saved book in `Your Bookcase`.
- A browser refresh still shows saved user books.
- The Design demos button opens `/books/design-demos`.
- All relevant automated tests pass.
