# Fix Pages

## Goal

Move the visible page block on the bookcase SVGs slightly left so the books still read as closed books with a small right-side paper gutter, without changing the approved cover shapes, title plates, title layout, or modal book-page design.

The fix must be coherent across:

- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCover.razor`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCatalog.cs`
- generated Tailwind output, only if class usage changes

## Current Finding

The production bookcase and design-demo SVGs both use a `216 x 247` viewBox and render the book inside `translate(7 10) scale(1.04)`.

The cover generally ends around SVG x `136`, while the page block extends to about x `160` or `161`. That leaves roughly `24-25` SVG units of visible page gutter before hover, which is a bit too much for the current larger book size.

The page block is not one isolated coordinate. It includes:

- the page fill path,
- the horizontal page-line path,
- optional tab rectangles for technical/manual variants,
- the page gradient coordinate range,
- the hover/forced-open `translate-x-px` motion.

Changing only the fill path would leave page lines or tabs visually disconnected, so all page geometry needs to move together.

## Design Target

Use a small left shift: start with `-3` SVG units.

Expected visual result:

- the right-side paper gutter still exists, but is quieter,
- page lines remain fully inside the page block,
- technical/manual and field-notebook tabs stay attached to the page block,
- the hover-open effect still works, but the open state no longer exaggerates the page protrusion,
- the title plate and cover art do not move.

If `-3` is visibly too much after inspection, adjust to `-2`. Do not exceed `-4`, because the page block must remain legible as pages.

## Implementation Plan

### 1. Normalize the Page Offset

Status: done

Add an explicit page geometry offset in the production component.

Preferred shape:

- keep the existing animated page group as the outer group,
- wrap page fill, page lines, and page tabs in one inner SVG group,
- apply `transform="translate(-3 0)"` to that inner group.

This keeps the current Tailwind hover class simple and avoids manually editing every line endpoint in `BookSideView.razor`.

### 2. Apply the Same Offset to Design Demos

Status: done

Apply the same inner page-group offset in `BookDesignDemoCover.razor`.

The design demos are the approval source for the production bookcase, so they must show the same page protrusion as the live shelf. Do not leave the demo with older geometry.

### 3. Align Page Gradients

Status: done

Move the page gradient x coordinates left by the same amount in both production and demo components.

Current production gradient:

- `x1="108" x2="161"`

Current demo gradient:

- `x1="120" x2="161"`

After the geometry shift, inspect whether these should become approximately:

- production: `x1="105" x2="158"`
- demo: `x1="117" x2="158"`

The exact values should be chosen visually so the gutter still has a paper edge and does not turn flat.

### 4. Review Hover and Forced-Open State

Status: done

Keep the current `translate-x-px` page hover movement initially. After visual inspection, reduce or remove it only if the open state still looks like pages are sticking out too far.

Acceptance criteria:

- normal state has a restrained right-side page gutter,
- hover/focus state still suggests the book is opening slightly,
- page lines do not detach from the book edge,
- no dark or hard outer page line appears.

### 5. Visual Inspection

Status: done

Run the app locally and inspect:

- `/books`
- `/books/design-demos`
- `/books/design-demos/cloth-hardback?open=true`
- `/books/design-demos/modern-paperback?open=true`
- `/books/design-demos/technical-manual?open=true`
- `/books/design-demos/decorative-hardcover?open=true`
- `/books/design-demos/library-ledger?open=true`
- `/books/design-demos/field-notebook?open=true`

Inspect desktop and mobile widths. The bookcase shelves and standalone design pages must agree visually.

### 6. Automated Checks

Status: done

Run:

- `npm run css:build` from `BlazorAutoApp.Client`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed Books E2E against the local app
- mobile Books E2E with the `390 x 844` viewport
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`

If Tailwind output changes, keep the generated `BlazorAutoApp/wwwroot/tailwind.css` in sync.

## Acceptance Criteria

- The visible page gutter is slightly narrower in all six bookcase designs.
- Production bookcase SVGs and design-demo SVGs use the same page offset.
- No title, author, URL, modal page, or CRUD behavior changes.
- Hover/focus still gives a subtle open-book impression.
- Desktop and mobile visual checks pass.
- Build, tests, formatting, and generated CSS verification pass.
