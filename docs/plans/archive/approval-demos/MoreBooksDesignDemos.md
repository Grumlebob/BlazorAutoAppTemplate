# More Books Design Demos

Approval-only demos for the coherent bookcase redesign. The current demos are real Blazor pages in the Books `DesignDemos` subslice.

Current approval status: approved and implemented. The forced-open page alignment was repaired and visually checked before the production bookcase was replaced.

Open:

- `/books/design-demos`
- `/books/design-demos/cloth-hardback`
- `/books/design-demos/modern-paperback`
- `/books/design-demos/technical-manual`
- `/books/design-demos/decorative-hardcover`
- `/books/design-demos/library-ledger`
- `/books/design-demos/field-notebook`

Notes:

- These demos are wired into the Blazor app as an approval/review subslice, not as static `Plans/*.html` files.
- They use a `216 x 247` SVG motion canvas with a large `7:9` book core and a visible right-side page gutter.
- They are still closed-book shelf designs, not the open page/detail view.
- They keep subtle right-side page hints on every design.
- The covers are intentionally narrower than the full page block, so the pages remain visible before hover.
- The page lines start near the hinge, so the hover-open effect does not leave blank gaps between the cover and the visible page marks.
- The page block extends to the lower book corner, and the page-line set includes lower lines so the bottom-right area still reads as paper.
- The hover-open page movement is intentionally restrained.
- The page block uses a squared left edge under the cover and no dark outer-edge rule.
- Add `?open=true` to a detail route to force the open inspection state.
- Each design has a standalone Blazor approval page linked from the overview.
- They keep the title in a protected middle panel.
- They do not show author text.
- They do not show a URL arrow or URL marker.
- They do not show a footer strip on the book.
- Hover or focus a demo book to preview the slight open effect: the cover tips left while the page block moves right.
- The open effect was visually inspected before approval. The pages, lower cover edge, and shadow align as one physical book in the overview and standalone demo surfaces.
- Resize the browser near `390 x 844` to review the mobile scale.

Inspection artifacts:

- `TestResults/DesignReview/CoherentDemoOverviewDesktop.png`
- `TestResults/DesignReview/CoherentDemoOverviewMobile.png`
- `TestResults/DesignReview/CoherentDemoClothOpenDesktop.png`
- `TestResults/DesignReview/CoherentDemoClothOpenMobile.png`
- `TestResults/DesignReview/CoherentBooksHomeDesktop.png`
- `TestResults/DesignReview/CoherentBooksHomeMobile.png`

Designs:

1. Cloth Hardback
2. Modern Paperback
3. Technical Manual
4. Decorative Hardcover
5. Library Ledger
6. Field Notebook
