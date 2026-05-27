# Improve Book Covers

## Goal

Status: done

Clean the book cover catalog down to a smaller, stronger set and improve the remaining weak designs until the design demo page and the live bookcase both look deliberate.

The current catalog has **61 active designs**. This plan removes **33 designs**, keeps **28 active designs**, and carefully improves **18 of the remaining designs**.

This is a design-quality cleanup, not a feature change. The result should feel like a curated template app, not a large pile of mixed-quality SVG experiments.

## Scope

Status: done

Files expected to change:

- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverDesignCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverArtwork.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverPageTabs.razor`, only if removed designs still have tab-specific branches
- `BlazorAutoApp/wwwroot/tailwind.css`, only if Tailwind regeneration changes it
- this plan file, to mark completed phases and record screenshot/test evidence

Files that should usually not change:

- book CRUD, auth, data access, migrations, deployment, local Docker scripts, and Playwright test code
- book modal view/edit/add flow
- database schema
- seeded book data

## Current Catalog Facts

Status: done

Confirmed from `BookCoverDesignCatalog.cs`:

- current active designs: `61`
- requested removals found in catalog: `33`
- requested improvement targets found in catalog: `18`
- final target active designs after removals: `28`
- removal list has no missing labels
- improvement list has no missing labels

Stable survivors that should remain unless screenshots reveal incidental damage:

1. Cloth Hardback
2. Decorative Hardcover
3. Field Notebook
4. Aurora Field Guide
5. Prism Atlas
6. Beacon Logbook
7. Quilt Reader
8. Calendar Folio
9. Bauhaus Reader
10. Seismograph Log

Designs to improve:

1. Droplet Monograph
2. Arbor Press
3. Transit Map Folio
4. Origami Edition
5. Woven Archive
6. Music Score
7. Herbarium Slip
8. Compass Fieldbook
9. Wave Notebook
10. Monoline City
11. Signal Flag Manual
12. Blueprint Register
13. Laboratory Log
14. Atlas Pinboard
15. Alpine Trail Guide
16. Bookmark Folio
17. Embroidery Sampler
18. Solar Dial Folio

Execution result:

- Final active catalog count is `28`.
- Removed design count is `33`.
- Improved design count is `18`.
- Stable survivor count is `10`.
- The final catalog order matches the target order in this plan.

## Removal List

Status: done

Completely remove these designs from the active app:

1. Technical Manual
2. Sunprint Notebook
3. Circuit Garden
4. Marble Index
5. Glasshouse Register
6. Cipher Codex
7. Topographic Survey
8. Cartographer Fold
9. Nautical Chart
10. Stamp Ledger
11. Mineral Plate
12. Archive Ribbon
13. Lantern Journal
14. Observatory Notebook
15. Type Foundry
16. Stage Playbook
17. Mosaic Codex
18. Ink Wash Journal
19. Railway Timetable
20. Patent Notebook
21. Vineyard Register
22. Geode Almanac
23. Copperplate Ledger
24. Kinetic Diagram
25. Film Slate Journal
26. Punchcard Manual
27. Weather Station Register
28. Stained Glass Reader
29. Currency Ledger
30. Newspaper Archive
31. Checkout Card
32. Microfiche Index
33. Waveform Notes

Removal means:

- remove their `BookCoverDesignCatalog.All` entries
- remove their `BookCoverDesignKind` enum members
- remove their `BookCoverArtwork.razor` branches
- remove any special page-tab branches in `BookCoverPageTabs.razor`
- confirm they no longer appear on `/books/design-demos`
- confirm their old direct demo routes no longer resolve as active design pages
- confirm `rg` finds no stale references except historical plan/test-result files if those are intentionally retained

Do not delete historical plan files or screenshot evidence unless explicitly requested. They are not active app surface.

## Target Final Catalog Order

Status: done

Keep the final catalog ordered and readable. A good target order after removals is:

1. Cloth Hardback
2. Decorative Hardcover
3. Field Notebook
4. Aurora Field Guide
5. Prism Atlas
6. Droplet Monograph
7. Arbor Press
8. Transit Map Folio
9. Origami Edition
10. Beacon Logbook
11. Woven Archive
12. Music Score
13. Herbarium Slip
14. Quilt Reader
15. Compass Fieldbook
16. Wave Notebook
17. Monoline City
18. Signal Flag Manual
19. Blueprint Register
20. Laboratory Log
21. Calendar Folio
22. Atlas Pinboard
23. Bauhaus Reader
24. Seismograph Log
25. Alpine Trail Guide
26. Bookmark Folio
27. Embroidery Sampler
28. Solar Dial Folio

The deterministic live bookcase may redistribute book designs because the catalog size changes from 61 to 28. That is acceptable.

## Design Quality Bar

Status: done

Every remaining design should satisfy these rules:

- title plate stays readable on desktop and mobile
- artwork does not collide with the title plate
- cover-face artwork does not crowd the right page gutter
- the page block still aligns behind the cover during hover/open motion
- artwork remains simple inline SVG, no external images, filters, masks, or runtime-generated geometry
- each design has a recognizable visual idea from a distance
- no design depends on tiny details that disappear on mobile
- designs should be different from one another in structure, not just color
- no noisy bottom-line filler unless it supports the concept
- avoid text labels inside the SVG artwork beyond the real book title

## Phase 1: Baseline Screenshots

Status: done

Before editing, capture a baseline so regressions are obvious:

- `TestResults/ImproveBookCovers/Baseline/overview-full-desktop.png`
- `TestResults/ImproveBookCovers/Baseline/overview-full-mobile.png`
- `TestResults/ImproveBookCovers/Baseline/books-desktop.png`
- `TestResults/ImproveBookCovers/Baseline/books-mobile.png`

Also capture forced-open detail screenshots for all 18 improvement targets:

- `droplet-monograph-open-desktop.png`
- `arbor-press-open-desktop.png`
- `transit-map-folio-open-desktop.png`
- `origami-edition-open-desktop.png`
- `woven-archive-open-desktop.png`
- `music-score-open-desktop.png`
- `herbarium-slip-open-desktop.png`
- `compass-fieldbook-open-desktop.png`
- `wave-notebook-open-desktop.png`
- `monoline-city-open-desktop.png`
- `signal-flag-manual-open-desktop.png`
- `blueprint-register-open-desktop.png`
- `laboratory-log-open-desktop.png`
- `atlas-pinboard-open-desktop.png`
- `alpine-trail-guide-open-desktop.png`
- `bookmark-folio-open-desktop.png`
- `embroidery-sampler-open-desktop.png`
- `solar-dial-folio-open-desktop.png`

## Phase 2: Remove Unwanted Designs

Status: done

Remove all 33 unwanted designs in one mechanical pass:

- delete catalog entries
- delete enum members
- delete artwork branches
- delete page-tab branches if present
- rebuild the project to catch switch/reference errors
- run `rg` for every removed enum/id/label in active source files

Acceptance:

- `BookCoverDesignCatalog.All.Count` is `28`
- `/books/design-demos` shows exactly 28 cards
- removed designs are absent from the design demo navigation list
- direct demo URLs for removed IDs no longer render those designs
- `dotnet build .\BlazorAutoApp.sln --no-restore` passes

## Phase 3: Improve Droplet Monograph

Status: done

Requested change:

- the drop should be in the bottom
- remove other curvy lines
- focus on the drop

Implementation direction:

- move the visual emphasis below the title plate
- use one clean drop shape as the main bottom motif
- optionally add a small highlight line inside the drop
- remove upper/lower wave-like or decorative curves
- keep the top quiet so it does not compete with the title

Acceptance:

- the cover reads as a droplet design immediately
- no unrelated curvy line filler remains
- the bottom drop does not collide with the cover edge or page shadow

## Phase 4: Improve Arbor Press

Status: done

Requested change:

- the tree should be more clearly visible
- current lines are off
- remove the bottom lines

Implementation direction:

- replace loose branch strokes with a clearer trunk-and-canopy structure
- keep branches balanced around a central trunk
- use simple leaf marks or clustered strokes only if they remain readable
- remove bottom decorative lines
- avoid tiny branch noise near the page gutter

Acceptance:

- the tree form is readable at mobile size
- bottom area is clean
- branch lines are centered and not visually slipping right

## Phase 5: Improve Transit Map Folio

Status: done

Requested change:

- remove lines that look like water
- add more lines that clearly look like transit

Implementation direction:

- replace soft wave lines with straight and angled route segments
- use several connected route paths with round station nodes
- make paths cross or transfer in a controlled transit-map way
- keep routes away from the title plate
- do not add station-name text

Acceptance:

- the design reads as transit, not water
- route nodes are visible
- routes look intentionally connected rather than random lines

## Phase 6: Improve Origami Edition

Status: done

Requested change:

- should look more like origami
- should not look like Prism Atlas

Implementation direction:

- use folded-paper geometry with clear crease lines
- build a simple folded emblem from overlapping triangular paper facets
- keep the fold shape asymmetrical enough to differ from Prism Atlas
- use light paper-like strokes, not jewel/prism facets
- avoid duplicating Prism Atlas' angular layout language

Acceptance:

- it reads as folded paper
- it no longer visually competes with or duplicates Prism Atlas
- crease lines are visible but not noisy

## Phase 7: Improve Woven Archive

Status: done

Requested change:

- carefully improve and iterate until nice

Implementation direction:

- make the weave structure clearer with alternating over-under bands
- keep line weights consistent
- use a small woven panel above or below the title plate rather than background clutter
- avoid letting weave strokes touch the page gutter
- make it distinct from Quilt Reader

Acceptance:

- it reads as woven material, not random crosshatching
- the design is distinct from Quilt Reader
- the cover still feels calm and readable

## Phase 8: Improve Music Score

Status: done

Requested change:

- make nodes visible

Implementation direction:

- make noteheads larger and clearer
- keep staff lines simple and aligned
- use a few strong notes rather than many tiny marks
- avoid placing notes behind the title plate
- preserve the music-score concept without making it busy

Acceptance:

- note nodes are visible on mobile
- staff lines do not visually merge with page lines
- design reads as music without requiring inspection

## Phase 9: Improve Herbarium Slip

Status: done

Requested change:

- make them look like leaves

Implementation direction:

- replace ambiguous marks with simple leaf silhouettes or outlined leaves
- add one or two central vein lines if useful
- use leaf clusters above and below the title plate
- keep shapes organic but clean
- avoid tiny botanical clutter

Acceptance:

- the cover clearly reads as leaves
- leaves stay inside the safe cover face area
- title remains visually dominant

## Phase 10: Improve Compass Fieldbook

Status: done

Requested change:

- move compass slightly up
- make it tilt a bit to the right so it is not straight vertical

Implementation direction:

- translate compass motif upward by a small, controlled amount
- rotate the compass needle or full compass motif slightly clockwise
- preserve symmetry enough that it still reads as a compass
- avoid overlap with the title plate

Acceptance:

- compass sits higher and has a slight right tilt
- no accidental crooked/misaligned look
- lower cover area stays clean

## Phase 11: Improve Wave Notebook

Status: done

Requested change:

- make it look like clean waves
- no dots

Implementation direction:

- remove all dot marks
- use two or three clean wave strokes
- keep waves smooth and evenly spaced
- avoid page-gutter crowding
- make the design calmer than the old noisy version

Acceptance:

- no dots remain
- waves read clearly on mobile
- waves do not look like transit routes or arbitrary curves

## Phase 12: Improve Monoline City

Status: done

Requested change:

- buildings should look more connected
- remove the orange roof

Implementation direction:

- remove the orange roof/accent shape
- connect buildings with a continuous baseline or shared monoline contour
- use a few window marks, not dense grids
- keep the skyline balanced around the title plate
- avoid making the buildings too tiny

Acceptance:

- skyline reads as one connected city mark
- no orange roof remains
- design remains legible at mobile size

## Phase 13: Improve Signal Flag Manual

Status: done

Requested change:

- clean up
- make it cleanly flags
- remove weird horizontal lines

Implementation direction:

- remove decorative horizontal line filler
- use simple flag shapes on short poles or a clean signal string
- keep flags few and readable
- vary flag fill shapes enough to read as flags
- do not add text or tiny labels

Acceptance:

- it clearly reads as flags
- horizontal filler lines are gone
- the design is clean and centered

## Phase 14: Improve Blueprint Register

Status: done

Requested change:

- make it look much more like a blueprint

Implementation direction:

- strengthen blueprint identity with fine cyan construction lines
- add simple plan-like rectangles, dimension ticks, and measurement leaders
- keep geometry clean and orthogonal
- avoid overfilling the cover
- use one recognizable plan detail above or below title plate

Acceptance:

- it reads as blueprint at first glance
- lines are visible without becoming noise
- title plate stays protected

## Phase 15: Improve Laboratory Log

Status: done

Requested change:

- make the flask clearly fully visible and nice

Implementation direction:

- redraw the flask as a complete outline with neck, shoulders, body, and visible fluid line
- position it so the title plate does not cut it into an unrecognizable shape
- optionally place the flask above the title plate with small bubbles away from the gutter
- keep the lower area clean if the flask is above

Acceptance:

- flask is fully visible
- shape is recognizable on mobile
- it does not collide with the title plate

## Phase 16: Improve Atlas Pinboard

Status: done

Requested change:

- pins should be connected to something
- route should be clean

Implementation direction:

- use two or three clear pins
- connect pins with a clean route polyline
- make the route intentional and simple
- remove loose marks that are not connected to the route
- keep route outside the title plate area

Acceptance:

- every pin participates in the route
- route reads cleanly
- no disconnected decorative map noise remains

## Phase 17: Improve Alpine Trail Guide

Status: done

Requested change:

- mountain looks nice
- bottom lines are ugly and noisy

Implementation direction:

- preserve the mountain/ridge idea
- remove noisy bottom line groups
- use a small trail path or sparse route dots only if it strengthens the concept
- keep bottom area clean and intentional

Acceptance:

- mountain remains the main identity
- bottom is no longer noisy
- mobile screenshot still reads as a trail guide

## Phase 18: Improve Bookmark Folio

Status: done

Requested change:

- make it more clean

Implementation direction:

- simplify bookmark shapes
- use one or two clear ribbon/bookmark tabs
- reduce competing small folds and points
- keep bookmark geometry vertically aligned and away from the title plate

Acceptance:

- design reads as bookmarks/folio without clutter
- title plate feels intentionally framed
- no small decorative leftovers distract

## Phase 19: Improve Embroidery Sampler

Status: done

Requested change:

- remove curvy lines
- make it look more like stitching

Implementation direction:

- remove all curved thread lines
- use rows of cross-stitches, running stitches, or dashed stitch marks
- keep stitch marks large enough for mobile
- place stitch bands above and below the title plate
- avoid making it look like generic dots

Acceptance:

- no curvy lines remain
- it clearly reads as stitching
- stitch marks are visible and aligned

## Phase 20: Improve Solar Dial Folio

Status: done

Requested change:

- remove bottom lines
- focus on solar dial

Implementation direction:

- remove lower decorative arcs/lines
- strengthen the solar dial at the top with clearer radial ticks and a single shadow/needle mark
- keep the dial centered and balanced
- avoid bottom filler

Acceptance:

- solar dial is the clear focus
- bottom lines are gone
- design feels calmer and stronger

## Redesign Result Summary

Status: done

Implemented changes:

- **Droplet Monograph**: moved the droplet to the lower cover, removed unrelated curves, and kept the mark inside the cover edge after Pass02.
- **Arbor Press**: replaced loose branch marks with a clearer tree, centered leaves, and no bottom filler.
- **Transit Map Folio**: replaced water-like curves with connected transit routes and visible station nodes.
- **Origami Edition**: changed the visual language toward folded-paper crease geometry so it no longer reads like Prism Atlas.
- **Woven Archive**: rebuilt the woven motif as broad over-under bands above and below the title plate.
- **Music Score**: enlarged noteheads and kept the staff lines readable.
- **Herbarium Slip**: redrew the motifs as readable leaves with stems.
- **Compass Fieldbook**: moved the compass upward and tilted it slightly clockwise.
- **Wave Notebook**: removed dots and kept clean wave strokes only.
- **Monoline City**: removed the orange roof and connected the skyline into one monoline structure.
- **Signal Flag Manual**: removed horizontal filler and simplified the artwork to clean signal flags.
- **Blueprint Register**: strengthened the blueprint read with plan rectangles, measured rules, and construction marks.
- **Laboratory Log**: redrew the flask so it is fully visible above the title plate after Pass02.
- **Atlas Pinboard**: connected pins with clean route lines.
- **Alpine Trail Guide**: preserved the mountain motif and replaced noisy bottom lines with sparse route dots.
- **Bookmark Folio**: simplified the bookmark tabs and reduced lower clutter.
- **Embroidery Sampler**: removed curvy lines and used aligned cross-stitch rows.
- **Solar Dial Folio**: removed bottom lines and made the solar dial the single visual focus.

## Phase 21: First Full Visual Pass

Status: done

After removals and redesigns, capture:

- `TestResults/ImproveBookCovers/Pass01/overview-full-desktop.png`
- `TestResults/ImproveBookCovers/Pass01/overview-full-mobile.png`
- `TestResults/ImproveBookCovers/Pass01/books-desktop.png`
- `TestResults/ImproveBookCovers/Pass01/books-mobile.png`
- forced-open detail screenshots for all 28 remaining active designs

Inspection requirements:

- inspect the full design overview first
- inspect all 18 improved detail pages
- inspect at least the stable survivors that are adjacent to changed/removed designs in catalog order
- inspect live `/books` desktop and mobile because the deterministic distribution changed

If anything looks off, do not proceed directly to tests. Patch the artwork and capture `Pass02`.

## Phase 22: Iteration Passes

Status: done

Iterate until all cover issues are acceptable.

Minimum expected passes:

- `Pass01`: first implementation review
- `Pass02`: cleanup after visual defects
- `Pass03`: final no-code confirmation pass

Each pass should include:

- full demo overview desktop
- full demo overview mobile
- live `/books` desktop
- live `/books` mobile

Only mark this phase done when:

- all 28 cards are present
- all removed cards are absent
- title plates are readable
- improved designs match their requested directions
- page blocks still align during forced-open/hover states
- mobile does not crop important design information

Execution result:

- `Baseline` captured the pre-change overview, live shelf, and all 18 target detail pages.
- `Pass01` captured the full 28-design overview, live desktop/mobile shelf, and forced-open detail screenshots for every remaining active design.
- Pass01 inspection found two issues: Droplet Monograph sat too low into the shadow, and Laboratory Log hid too much of the flask behind the title plate.
- `Pass02` fixed and rechecked Droplet Monograph and Laboratory Log, plus the full overview and live shelf.
- `Pass03` was captured as the final no-code confirmation pass:
  - `TestResults/ImproveBookCovers/Pass03/overview-full-desktop.png`
  - `TestResults/ImproveBookCovers/Pass03/overview-full-mobile.png`
  - `TestResults/ImproveBookCovers/Pass03/books-desktop.png`
  - `TestResults/ImproveBookCovers/Pass03/books-mobile.png`

## Phase 23: Deterministic Selection Check

Status: done

Run a deterministic distribution check against the live selection algorithm:

- parse `BookCoverDesignCatalog.All`
- compute the same stable title seed and mixed design seed as `BookSideView`
- sample at least 5,000 synthetic titles
- confirm all 28 remaining designs are reachable
- confirm no removed design IDs appear

Acceptance:

- total design count is `28`
- reached design count is `28`
- missing list is empty
- removed ID list is empty

Execution result:

- Sampled 5,000 synthetic titles against the same stable title seed and `MixDesignSeed` algorithm used by `BookSideView`.
- Total design count: `28`.
- Reached design count: `28`.
- Missing list: empty.
- Removed ID list: empty.

## Phase 24: Source Reference Cleanup

Status: done

Run active-source searches for removed designs:

- enum names
- labels
- route IDs
- old notes that could appear in UI

Search scope should include:

- `BlazorAutoApp.Client/Features/Books`
- `BlazorAutoApp.Test`
- active CSS/source files

Historical plan files and old screenshots may still contain removed names. That is acceptable, but active app code should not.

Execution result:

- Active-source search across `BlazorAutoApp.Client/Features/Books` and `BlazorAutoApp.Test` found no removed enum names, labels, or route IDs.
- All 33 removed design detail URLs returned `Book Design Missing`.

## Phase 25: Test Gate

Status: done

Run after final screenshots pass:

- `npm run css:build` from `BlazorAutoApp.Client`
- `dotnet build .\BlazorAutoApp.sln --no-restore`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed VisualSnapshot E2E
- headed RenderMode E2E
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query

Acceptance:

- build passes with 0 warnings and 0 errors
- non-E2E suite passes
- headed E2E checks pass against local app
- formatting verification passes
- whitespace check passes
- E2E cleanup query returns 0 generated rows

Execution result:

- `npm run css:build` passed.
- `dotnet build .\BlazorAutoApp.sln --no-restore` passed with 0 warnings and 0 errors.
- `dotnet test .\BlazorAutoApp.sln --no-build` passed: 64 passed, 5 E2E skipped by guard.
- Headed VisualSnapshot E2E and RenderMode E2E passed: 2 passed.
- Headed Books E2E desktop passed: 2 passed.
- Headed Books E2E mobile `390 x 844` passed: 2 passed.
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal --no-restore` passed.
- `git diff --check` passed.
- E2E cleanup query returned 0 generated rows.

## Phase 26: Plan Closeout

Status: done

Update this file with:

- final design count
- removed design confirmation
- improved design summary
- screenshot directories inspected
- deterministic selection result
- exact test results
- local app URL used for review

Do not mark the plan complete until all phases above are either done or explicitly deferred with a reason.

Execution result:

- Final design count: `28`.
- Removed designs: all 33 requested designs are gone from the active catalog, enum, artwork branches, and routeable demo pages.
- Improved designs: all 18 requested designs were adjusted and visually inspected.
- Final screenshot evidence is under `TestResults/ImproveBookCovers/Pass03`.
- Local app URL used for final review: `http://127.0.0.1:5099`.

## Non-Goals

Status: done

- Do not add bitmap images.
- Do not add new dependencies.
- Do not change authentication, authorization, or user seeding.
- Do not change book CRUD behavior.
- Do not change migrations or schema.
- Do not touch deployment.
- Do not introduce a generic shared UI folder outside the Books slice.
- Do not replace the deterministic live design selection with static assignment.
- Do not delete historical test result folders unless explicitly requested.
