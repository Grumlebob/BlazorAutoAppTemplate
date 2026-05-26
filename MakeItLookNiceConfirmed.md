# Make It Look Nice Confirmed

## Goal

Fix the open-book SVG state so the visible page block and cover align cleanly at the bottom. The result should look like one physical book opening slightly, not a cover floating above a separate paper slab.

This plan covers the live bookcase SVG and the Blazor design-demo SVG. It intentionally does not change CRUD, routing, modal book-page layout, seeded books, or deployment.

## Before Screenshots

Captured current rendered output before the fix:

- `TestResults/MakeItLookNiceConfirmed/Before/cloth-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/Before/modern-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/Before/technical-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/Before/ledger-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/Before/field-open-mobile.png`
- `TestResults/MakeItLookNiceConfirmed/Before/home-mobile.png`

## Current Finding

Status: done

The open state moves the cover left/up and rotates it slightly, while the page block only moves right. That leaves the paper bottom visually lower than the cover bottom in the forced-open and hover states.

The relevant behavior is duplicated in:

- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCover.razor`

## Fix Strategy

Status: done

Move the page block upward in the same open state that moves it right.

Design target:

- keep the existing cover/title/plate dimensions,
- keep the restrained right-side page gutter,
- keep the slight open-book motion,
- add a small upward page motion only while open/hover/focused,
- apply identical geometry to the production SVG and demo SVG.

Initial value: `-translate-y-[2px]` on the page group while open.

## Visual Confirmation

Status: done

After the fix, capture and inspect:

- `TestResults/MakeItLookNiceConfirmed/After/cloth-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/After/modern-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/After/technical-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/After/ledger-open-desktop.png`
- `TestResults/MakeItLookNiceConfirmed/After/field-open-mobile.png`
- `TestResults/MakeItLookNiceConfirmed/After/home-mobile.png`

Confirmed after inspection:

- the page block bottom now aligns with the lifted cover in forced-open state,
- the paper gutter still remains visible,
- the technical/manual tabs remain attached to the paper block,
- the mobile standalone demo remains readable and balanced.

Acceptance criteria:

- no visible beige paper slab hangs below the cover bottom,
- bottom-right corner reads as one book,
- page lines stay attached to the paper block,
- technical/manual tabs still sit on the pages,
- normal mobile shelf still looks clean,
- title readability is unchanged.

## Verification

Status: done

Run:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`

The app should remain available locally for manual review after the fix.
