# Nice Edit And Add Mode

## Goal

Make clicking a book open a polished, lightweight, SVG-based book-page view.

This is a replacement plan, not an additive UI polish pass. The old book details card and old create/edit layouts should disappear as user-facing experiences. Existing routes may stay, but they must render the new book page/view/editor surfaces.

The same visual language should apply to:

- Static books in **The Authors Bookcase**.
- User-owned books in **Your Bookcase**.

The author bookcase remains static and non-editable. User-owned books get a small pencil edit affordance from the details view. Adding a book should feel like editing an empty book, using the same editor surface as editing an existing book.

## Design Demo For Approval

- [x] Review `Plans/NiceEditAndAddMode.PageDemo.svg`.
- [x] Decide whether the page shape, title block, `Go to site` action, and pencil edit icon are approved before implementation.

The demo intentionally shows both modes:

- Static author page: no edit control.
- User page: same SVG page with a small pencil icon in the upper-right corner.

## Original State

- `BookSideView.razor` renders the shelf book SVGs.
- `BookcaseShelf.razor` can link books when `BookcaseBook.Href` is set.
- User shelf books already link to `/books/{id}`.
- Author shelf books are currently static non-links.
- `Pages/Details.razor` is a plain HTML card.
- `Pages/Create.razor` and `Pages/Edit.razor` are separate form experiences instead of one coherent book editor.
- User edit is only available through the saved-books table row.

This works functionally, but it makes the click-through experience feel weaker than the shelf experience.

## Replacement Contract

- Do not keep the old book details card as an alternate view.
- Do not keep separate old-style create and edit screens as alternate editor experiences.
- `Details.razor` should render the new read-only `BookPageView`.
- `Create.razor` should render the same editor as edit, initialized with an empty book model.
- `Edit.razor` should render the same editor as create, initialized from the loaded user-owned book.
- The route pages should be thin wrappers for authorization, loading, not-found/error states, and submit handlers.
- Shared visual markup belongs in reusable Books-slice components, not duplicated across `Create.razor`, `Edit.razor`, and `Details.razor`.
- Existing API ownership, persistence, validation rules, and routes can remain, but the visible user flow should only expose the new book page/view/editor surfaces.
- The saved-books table can remain as a management list if useful, but its view/edit actions must route into the new surfaces.

## Target Structure

```text
BlazorAutoApp.Client/Features/Books/
  AuthorBookcase/
    AuthorBookcase.razor
    AuthorBookcaseCatalog.cs
    AuthorBookDetails.razor
    AuthorBookPage.cs

  BookPage/
    BookPageView.razor
    BookPageEditor.razor
    BookPageEditorModel.cs (only if it keeps form state clean)
    BookPageTextLayout.cs

  Pages/
    Details.razor
    Create.razor
    Edit.razor

  Shared/
    BookcaseBook.cs
    BookcaseShelf.razor
    BookSideView.razor

  UserBookcase/
    UserBookcase.razor
    UserBookcaseTable.razor
    UserBookcaseLoginPrompt.razor
    UserBookcaseBookMapper.cs
```

Notes:

- Keep the page SVG inside the Books slice, not a global shared component.
- Keep editor reuse inside the Books slice. Prefer one `BookPageEditor` used by both create and edit over two mostly duplicated forms.
- Add helper files only when they remove real duplication or keep a component from becoming difficult to maintain.
- Keep author details static and local to `AuthorBookcase`.
- Keep user details backed by the existing authenticated API.
- Do not touch deployment.
- Do not change persistence or API ownership rules.

## Phase 1 - Approve SVG Direction

- [x] Status: Completed
- [x] Review the demo SVG in `Plans/NiceEditAndAddMode.PageDemo.svg`.
- [x] Confirm dimensions and page style.
- [x] Confirm the edit pencil placement for user-owned books.
- [x] Confirm author books should use the same page view without edit affordance.

Proposed dimensions:

- Desktop SVG frame: `min(100%, 560px)` wide and about `720px` tall.
- Mobile SVG frame: full available content width. On a 390px viewport with normal page padding it renders around `358px x 460px`.
- ViewBox: `0 0 560 720`.
- Shape: single portrait page, not a wide two-panel spread. The ratio is intentionally close to a hardback page so it reads as a book on desktop while still fitting above the fold on common phones.
- Outer book body: roughly `486px x 652px` inside the viewBox, with a quiet left spine around `26px` wide after the rounded edge and only barely visible right-edge page lines. The spine shape must follow the full bottom curve of the book so the lower-left corner is not exposed as pale paper. Do not use a dark right-side strip.
- Primary content panel: roughly `344px x 252px`, centered from `108,132` to `452,384`.
- Title safe area: about `292px` wide. At the intended mobile size this still leaves roughly `186px` of rendered width, so long titles must be wrapped into 2-3 clean lines instead of shrinking into unreadable text.
- Site action safe area: about `166px` wide with a short icon lane on the left, anchored near the bottom of the page rather than inside the title panel. The visible label should be `Go to site`; the full URL belongs in the link target/accessibility text, not as crowded visible SVG text.
- Edit affordance: about `50px x 50px` in the SVG, rendering around `32px x 32px` on a 390px mobile viewport. Use a light outline-only control, not a dark filled button. The icon should read clearly as a pencil pointing down-left, with a colored body, eraser, ferrule, wood tip, and point.
- No raster images, no external fonts, no network-loaded assets.

## Phase 2 - Shared Book Page SVG Component

- [x] Status: Completed
- [x] Add `BookPage/BookPageView.razor`.
- [x] Render a stylized open book/page entirely in inline SVG.
- [x] Display title, author, and a compact `Go to site` action inside the SVG when a URL exists.
- [x] Render a small pencil icon only when `EditHref` is present.
- [x] Keep the pencil icon accessible as a normal link around/over the SVG.
- [x] Add deterministic text wrapping so long titles, authors, and site states do not escape the safe text area.
- [x] Add `BookPageTextLayout.cs` only if wrapping logic gets too large for the component.

Acceptance:

- [x] Title fits on desktop and mobile.
- [x] Author line fits and falls back to `Unknown author`.
- [x] URL is represented by a `Go to site` action if present.
- [x] Missing URL displays a quiet `No site` state.
- [x] SVG is responsive and does not cause horizontal page scroll.
- [x] The component has no API calls and no author/user ownership logic.

## Phase 3 - Author Book Details

- [x] Status: Completed
- [x] Extend the author catalog from title-only entries to structured entries:
  - slug
  - title
  - author
  - optional URL
- [x] Keep the fixed template titles:
  - `Ship`
  - `TraceBack`
  - `ImprovedDb`
  - `KinoJoin`
- [x] Add static author details route, for example `/books/author/{slug}`.
- [x] Link author shelf books to the static author route.
- [x] Render `BookPageView` without `EditHref`.
- [x] Keep author books completely outside the database.
- [x] Return the normal not-found experience for unknown author slugs.

Acceptance:

- [x] Author shelf books are clickable.
- [x] Author detail pages render the SVG page view.
- [x] Author detail pages do not show a pencil icon.
- [x] Author pages do not call `/api/books`.
- [x] Author pages work when the database has zero books.

## Phase 4 - User Book Details

- [x] Status: Completed
- [x] Replace the plain card in `Pages/Details.razor` with `BookPageView`.
- [x] Keep `[Authorize]`.
- [x] Keep loading/error/not-found behavior.
- [x] Pass `EditHref=$"/books/{Id}/edit"` so user-owned books show the pencil icon.
- [x] Keep direct URL access scoped through the existing server API.
- [x] Keep the Back link available below the SVG page view.

Acceptance:

- [x] Clicking a user shelf book opens the SVG page view.
- [x] User book details show title, author, and a `Go to site` action when a URL exists.
- [x] User book details show a small pencil icon.
- [x] Pencil navigates to `/books/{id}/edit`.
- [x] User A still cannot view user B's book by URL.

## Phase 5 - Add And Edit Visual Polish

- [x] Status: Completed
- [x] Replace the old create/edit form layouts with one shared `BookPageEditor`.
- [x] Keep the editor as a regular HTML form for accessibility and validation.
- [x] Make create behave like editing an empty book:
  - title starts empty
  - author starts empty
  - URL starts empty
  - submit creates a new user-owned book
- [x] Make edit behave like the same editor with loaded values:
  - title starts from the existing book
  - author starts from the existing book
  - URL starts from the existing book
  - submit updates the existing user-owned book
- [x] Keep `Create.razor` and `Edit.razor` as thin route/load/save wrappers around `BookPageEditor`.
- [x] Do not put form inputs inside raw SVG unless there is a strong reason; HTML inputs are better for validation, accessibility, and mobile keyboards.
- [x] Use a simple page-like panel around fields so add/edit are the editor version of the SVG details page, not a separate app style.
- [x] Keep Save and Cancel controls stable.
- [x] Keep current `data-testid` values for E2E.
- [x] Remove duplicated create/edit markup after extracting the shared editor.

Acceptance:

- [x] Create page still saves a user-owned book.
- [x] Edit page still updates a user-owned book.
- [x] Create and edit use the same component for the visible editor surface.
- [x] No old-style create/edit UI remains reachable.
- [x] Validation messages remain readable.
- [x] Mobile layout does not overlap or create horizontal scroll.

## Phase 6 - Navigation And Shelf Behavior

- [x] Status: Completed
- [x] Update `AuthorBookcaseCatalog` to map static entries to `BookcaseBook` links.
- [x] Keep `UserBookcaseBookMapper` mapping user rows to `/books/{id}`.
- [x] Confirm author and user shelf books have the same hover/motion behavior.
- [x] Keep author books non-editable even though they are clickable.
- [x] Keep user table actions if they still help power users.
- [x] Ensure all view/edit links route to the new detail/editor surfaces.

Acceptance:

- [x] Author shelf click opens static details.
- [x] User shelf click opens user details.
- [x] The saved-books table, if kept, supports view/edit/delete through the new surfaces.
- [x] No edit route exists for author books.

## Phase 7 - Tests

- [x] Status: Completed
- [x] Update Books E2E:
  - author shelf book can be clicked
  - author details has no pencil
  - user shelf book can be clicked
  - user details has pencil
  - pencil opens edit
  - create then return still shows the user bookcase item
  - create page renders the same editor surface as edit with empty values
  - edit page renders the same editor surface as create with loaded values
  - old detail card/form layouts are not present in the rendered flow
- [x] Update visual snapshots for:
  - author details SVG page
  - user details SVG page
  - create page
  - edit page
- [x] Keep existing ownership and not-found integration tests unchanged unless routes require additions.
- [x] Add focused test coverage for author slug not found if the static route has server/route logic worth checking.

Validation:

- [x] `npm run css:build`
- [x] `dotnet build .\BlazorAutoApp.sln`
- [x] `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category!=E2E"`
- [x] Headed Books E2E desktop.
- [x] Headed Books E2E mobile `390x844`.
- [x] `dotnet format .\BlazorAutoApp.sln --verify-no-changes`
- [x] `git diff --check`

## Explicit Non-Goals

- Do not make author books editable.
- Do not move author books into the database.
- Do not add image uploads or external image dependencies.
- Do not change deployment.
- Do not change book ownership/cache invalidation behavior.
- Do not replace accessible HTML form inputs with SVG-only inputs.
- Do not keep parallel old and new book view/edit/add flows.

## Final Acceptance Criteria

- [x] Every visible book in both bookcases is clickable.
- [x] Static author book clicks open a static SVG book-page view.
- [x] User book clicks open an authenticated SVG book-page view.
- [x] User book details show a small pencil edit icon.
- [x] Author book details do not show edit controls.
- [x] Title, author, and `Go to site` are displayed in the SVG page view.
- [x] Create/edit use one shared editor surface.
- [x] Add book is the same interface as editing an empty book.
- [x] No old book view/edit/add UI remains as a reachable alternate path.
- [x] Create/edit remain usable, accessible, and visually coherent.
- [x] E2E passes for desktop and mobile.
