# Two New Showcase Book Designs

## Goal

Make the bookcase feel more like a polished template product by doing three things:

1. Clean up **Cloth Hardback** by removing the horizontal decorative line pairs at the top and bottom of the cover face.
2. Add **two completely new, high-quality SVG book cover designs** that are clearly different from the existing four:
   - Cloth Hardback
   - Technical Manual
   - Decorative Hardcover / Celestial Archive
   - Field Notebook
3. Increase the live bookcase books to **1.75x their current rendered size** so the artwork reads clearly and feels intentionally showcased.
4. Add a long-running extension phase with **ten more distinctive, performance-conscious SVG cover designs**.

The new designs must work in both places:

- the design approval pages under `/books/design-demos`,
- the live infinite bookcase on `/books`, with the existing deterministic RNG color behavior preserved.

The bar is not "two more variants". The bar is: a person seeing the demo page should feel the app has custom illustration quality and a real visual system.

The extension bar is higher: the larger set should still feel coherent, fast, and intentionally art-directed rather than becoming a pile of decorative branches.

The second extension bar is the same: add **15 more distinctive SVG designs** without slowing the template down or diluting the visual system. A fourth extension now brings the final catalog to **61 active designs**.

## Current Code Shape

Status: done

Relevant files:

- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverDesignCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverArtwork.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookCoverPageTabs.razor`
- `BlazorAutoApp.Client/Features/Books/Shared/BookSideView.razor`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCatalog.cs`
- `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCover.razor`

Current design count is four. `BookDesignDemoCatalog` projects from `BookCoverDesignCatalog.All`, so adding catalog entries should automatically add the demo cards and routes.

Important existing rule:

- `BookSideView` must keep its deterministic `StableSeed` palette selection. Do not force a single static live palette for special designs.

## Cloth Hardback Cleanup

Status: done

Remove the top and bottom horizontal line pairs from the Cloth Hardback branch in `BookCoverArtwork.razor`.

Current lines to remove:

- `M42 38h74`
- `M42 178h74`
- `M46 49h66`
- `M46 167h66`

Keep:

- the cloth weave texture in `BookSideView` and `BookDesignDemoCover`,
- the existing cover shape,
- the title plate,
- the page block and hover/open behavior.

Acceptance:

- Cloth Hardback becomes calmer and more fabric-like,
- no empty-looking imbalance is introduced above or below the title plate,
- title remains readable on mobile and desktop.

## New Design 1: Aurora Field Guide

Status: done

Concept:

A premium field-guide style cover with soft aurora ribbons and contour-map energy. It should feel organic and luminous, not technical and not celestial. This gives the set a graceful, natural visual direction.

Visual language:

- flowing layered ribbon paths,
- thin contour strokes that curve around the title plate,
- a few small glints or map pins,
- no square frame,
- no page tabs unless screenshots show the book needs more edge detail,
- title plate remains clean and protected.

Reference demo color direction:

- deep forest / night teal base,
- soft mint and icy blue accent strokes,
- warm pale title plate.

Implementation:

- Add `BookCoverDesignKind.AuroraFieldGuide`.
- Add catalog entry with id `aurora-field-guide`.
- Add a new `BookCoverArtwork` branch.
- Use paths that stay mostly within x `24` to x `116`.
- Keep major ribbons outside the title safe zone.

Demo title:

- `River`
- `Index`

Why it is different:

- Cloth Hardback is quiet texture.
- Technical Manual is ruled and utilitarian.
- Decorative Hardcover is celestial/foil.
- Field Notebook is note-taking/ruling.
- Aurora Field Guide is organic, flowing, and atmospheric without using bitmap assets.

## New Design 2: Prism Atlas Hardcover

Status: done

Concept:

A crisp, high-end geometric atlas cover using layered prism facets and tiny registration marks. It should feel modern, precise, and editorial, but not like the Technical Manual.

Visual language:

- asymmetric polygon facets,
- thin inlay seams,
- small corner registration ticks,
- one subtle diagonal light sweep,
- no square border,
- no dense grid,
- no constellation motifs.

Reference demo color direction:

- deep blue or graphite base,
- coral / cyan / pale brass accents,
- pale title plate with a sharper modern stroke.

Implementation:

- Add `BookCoverDesignKind.PrismAtlas`.
- Add catalog entry with id `prism-atlas`.
- Add a new `BookCoverArtwork` branch.
- Keep facets outside the central title plate.
- Ensure polygons do not crowd the right page gutter.

Demo title:

- `Vector`
- `Room`

Why it is different:

- It gives the set one sharp, architectural visual direction.
- It avoids looking like the existing Technical Manual because it uses broad facets, not ruled lines.
- It avoids looking like Decorative Hardcover because it has no orbits, stars, or foil constellation language.

## Catalog And Routing

Status: done

Update `BookCoverDesignCatalog.All` to contain six designs in this order:

1. Cloth Hardback
2. Technical Manual
3. Decorative Hardcover
4. Field Notebook
5. Aurora Field Guide
6. Prism Atlas

Reasons for this order:

- keep existing four stable,
- add the two new designs after the known set,
- avoid renumbering the existing demo cards more than necessary.

Expected new routes:

- `/books/design-demos/aurora-field-guide`
- `/books/design-demos/aurora-field-guide?open=true`
- `/books/design-demos/prism-atlas`
- `/books/design-demos/prism-atlas?open=true`

No database, deployment, auth, or CRUD changes.

## Long Running Extension: Ten Additional Cover Designs

Status: done

Add ten more active designs after the six-design baseline is stable. These should be pure SVG, distinctive from each other, and cheap enough for a fast template app. The implementation must still preserve deterministic live RNG palette behavior; no design may rely on a single hardcoded live color scheme to be readable.

Target final count:

1. Cloth Hardback
2. Technical Manual
3. Decorative Hardcover
4. Field Notebook
5. Aurora Field Guide
6. Prism Atlas
7. Droplet Monograph
8. Arbor Press
9. Transit Map Folio
10. Sunprint Notebook
11. Origami Edition
12. Circuit Garden
13. Marble Index
14. Beacon Logbook
15. Woven Archive
16. Glasshouse Register

Catalog rules:

- Keep the current six in their existing order.
- Append the ten new designs in the order listed above.
- Add one `BookCoverDesignKind` enum member per design.
- Add one `BookCoverDesignCatalog.All` entry per design.
- Ensure `BookDesignDemoCatalog` continues to project from the shared catalog without a second list.
- Expected new route pattern: `/books/design-demos/{design-id}` and `/books/design-demos/{design-id}?open=true`.

### SVG Performance Budget

Status: done

Each new design must stay lightweight:

- Use only inline SVG primitives and paths.
- Prefer `path`, `line`, `polyline`, `circle`, `ellipse`, and simple `rect`.
- Avoid bitmap images, external assets, `foreignObject`, heavy filters, large masks, animated gradients, and complex clip-path stacks.
- Keep each design branch roughly under 18 visible SVG elements where practical.
- Reuse shared cover/page/title geometry from the existing components.
- Do not add JavaScript for cover artwork.
- Do not add per-book runtime random shape generation; design selection and palette selection remain deterministic from the existing seed.
- Keep title safe zone untouched: center plate remains the readable surface and artwork must route around it.

Screenshot acceptance for performance:

- `/books` should still hydrate quickly and remain scrollable with the enlarged books.
- Hover/open animation should not stutter on desktop.
- Mobile screenshots should not show layout shifts or clipped titles.
- Generated Tailwind CSS should not balloon from many arbitrary classes; prefer SVG attributes for artwork-specific values.

### Design 3: Droplet Monograph

Status: done

Inspiration from the user: a drop of water shape.

Concept:

A restrained cover built around one large clean water-drop silhouette above the title plate, with a smaller echo droplet below it. It should feel calm, editorial, and premium.

Visual language:

- one large teardrop outline or filled translucent droplet,
- one inner highlight curve,
- two or three small ripple arcs away from the title plate,
- no rain clutter,
- no dense pattern.

Demo title:

- `Clear`
- `Signal`

Implementation notes:

- Keep the main droplet between x `46` and x `102`, y `30` and y `70`.
- Bottom ripple must stay below y `156`.
- Use opacity sparingly so random palettes do not turn muddy.
- The droplet should still read on warm, blue, green, and red seeded palettes.

### Design 4: Arbor Press

Status: done

Inspiration from the user: a tree shape.

Concept:

A simplified tree mark with a trunk that forks into a canopy made from clean branch lines. This should feel like a publisher imprint or archival botanical press, not a children-style tree.

Visual language:

- centered small trunk above the title plate,
- branching linework that spreads horizontally without touching the plate,
- two or three leaf dots,
- subtle root lines below the plate.

Demo title:

- `Root`
- `Notes`

Implementation notes:

- Do not make a full scenic tree. Keep it logo-like.
- Canopy should live mostly between y `32` and y `68`.
- Roots below plate should be shallow, y `158` to y `178`.
- Avoid many tiny leaves; they will become visual noise at shelf size.

### Design 5: Transit Map Folio

Status: done

Concept:

A clean urban transit-map inspired cover with colored route lines and station dots. It should be modern and spatial, distinct from Technical Manual because it uses flowing routes rather than ruled reference lines.

Visual language:

- two or three route polylines,
- small station circles,
- one route crossing above the title plate and one below,
- no dense grid.

Demo title:

- `Line`
- `Atlas`

Implementation notes:

- Use rounded stroke caps and joins.
- Keep all routes outside the title plate.
- Make station dots large enough to read at shelf size.

### Design 6: Sunprint Notebook

Status: done

Concept:

A cyanotype/sunprint-inspired cover with a simple sun disk and botanical silhouette fragments. It should be bright and photographic in feeling while remaining pure vector.

Visual language:

- one pale sun circle,
- two or three negative-space leaf silhouettes,
- a few short light rays,
- quiet lower echo detail.

Demo title:

- `Blue`
- `Print`

Implementation notes:

- Avoid looking like Decorative Hardcover; no stars, orbits, or celestial arcs.
- Keep the sun behind or above linework, not behind the title text.
- Use simple leaf shapes, not many small stems.

### Design 7: Origami Edition

Status: done

Concept:

A folded-paper cover using angular fold facets and crease lines. It should feel tactile and modern, different from Prism Atlas by being softer and paper-based rather than glass/geometric atlas.

Visual language:

- folded corner motif,
- two or three crease lines,
- asymmetric paper facets above and below plate,
- subtle diagonal rhythm.

Demo title:

- `Fold`
- `Map`

Implementation notes:

- Avoid large facets that collide with the page block.
- Keep folds light and low-contrast enough to act like paper, but visible enough on the demo page.

### Design 8: Circuit Garden

Status: done

Concept:

A hybrid circuit-board and organic sprout design. This gives the set a technology/nature crossover without turning into another Technical Manual.

Visual language:

- two circuit traces with rounded corners,
- small node circles,
- one simple sprout/leaf mark,
- traces route around title plate like paths.

Demo title:

- `Green`
- `Stack`

Implementation notes:

- Keep traces sparse. Too many right angles will make it feel cheap.
- Avoid black-heavy strokes.
- Make node circles visually balanced on both random dark and bright covers.

### Design 9: Marble Index

Status: done

Concept:

A refined marble/endpaper cover with a few sweeping vein strokes. It should feel like old book endpapers, but cleaner and more modern than an ornate antique texture.

Visual language:

- three to five long organic vein paths,
- one accent vein in a warmer color,
- very low-density texture,
- no repeated noise pattern.

Demo title:

- `Stone`
- `Index`

Implementation notes:

- Keep veins behind no text and outside plate.
- Avoid too many curves; this must stay crisp at shelf size.
- The design should work even when the base palette is not white or gray.

### Design 10: Beacon Logbook

Status: done

Concept:

A lighthouse/beacon signal abstraction. It should communicate a guide/logbook without drawing a literal full scene.

Visual language:

- one small beacon tower shape or vertical mark,
- two signal arcs,
- one horizon line below the plate,
- a few restrained light ticks.

Demo title:

- `North`
- `Light`

Implementation notes:

- Do not create a landscape illustration.
- Keep the beacon mark compact and centered above the title plate.
- Signal arcs must not resemble Decorative Hardcover orbits.

### Design 11: Woven Archive

Status: done

Concept:

A woven textile-inspired cover with interlaced bands. It gives the set a material direction distinct from Cloth Hardback's fine weave.

Visual language:

- three broad woven bands,
- simple over/under breaks,
- one vertical and two diagonal strokes,
- title plate remains calm and untouched.

Demo title:

- `Thread`
- `Archive`

Implementation notes:

- This is not a dense weave texture. It should be a bold cover emblem.
- Use only a handful of rectangles/paths.
- Check carefully at mobile size so bands do not look like accidental stripes.

### Design 12: Glasshouse Register

Status: done

Concept:

A greenhouse/glasshouse line-art cover with a roof silhouette and pane divisions. It should feel architectural, airy, and different from Prism Atlas.

Visual language:

- simple greenhouse roof outline,
- two or three pane lines,
- one small plant silhouette,
- lower pane echo below title plate.

Demo title:

- `Glass`
- `House`

Implementation notes:

- Keep lines thin but not fragile.
- Avoid a full building scene.
- Ensure pane lines do not look like a square border around the whole cover.

## Extension Implementation Phases

Status: done

### Extension Phase 1: Catalog Skeleton

Status: done

- Add enum members for all ten designs.
- Add catalog entries with final ids, labels, demo titles, notes, palette defaults, cover/page colors, and plate settings.
- Confirm the design overview automatically shows sixteen cards.
- Confirm all ten new detail routes resolve.

### Extension Phase 2: First Five Designs

Status: done

Implement and screenshot:

- Droplet Monograph
- Arbor Press
- Transit Map Folio
- Sunprint Notebook
- Origami Edition

Capture:

- `TestResults/TwoNewShowcaseBookDesigns/ExtensionPass01/overview-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/ExtensionPass01/overview-mobile.png`
- one forced-open detail screenshot for each implemented design.
- `/books` desktop and mobile screenshots with live RNG distribution.

### Extension Phase 3: Second Five Designs

Status: done

Implement and screenshot:

- Circuit Garden
- Marble Index
- Beacon Logbook
- Woven Archive
- Glasshouse Register

Capture:

- `TestResults/TwoNewShowcaseBookDesigns/ExtensionPass02/overview-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/ExtensionPass02/overview-mobile.png`
- one forced-open detail screenshot for each implemented design.
- `/books` desktop and mobile screenshots with live RNG distribution.

### Extension Phase 4: Distribution And Repetition Review

Status: done

With sixteen designs, deterministic distribution needs a deliberate check.

Check:

- author seeded books show a varied subset, not just a clustered group,
- user-created titles distribute across the new set reasonably,
- the same title always gets the same design and palette,
- no design disappears from the demo catalog,
- no design relies on one specific palette to work.

If the current seed mixer clusters too much after sixteen designs, replace it with a tiny deterministic hash mixer in `BookSideView` and verify no app state or database behavior depends on design kind.

### Extension Phase 5: Visual Polish Loop

Status: done

Run at least three extension visual passes:

1. First implementation pass.
2. Cleanup pass after screenshot inspection.
3. Final no-code verification pass if the second pass is good enough, otherwise one final targeted polish pass.

Inspect for:

- title plate readability,
- mobile card readability,
- live shelf hover/open alignment,
- page block alignment,
- ornament collisions with the right page gutter,
- visual sameness across all sixteen designs,
- designs that look too expensive or too detailed for the template.

### Extension Phase 6: Full Test Gate

Status: done

Run after the ten-design extension:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed visual snapshot E2E
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query

Do not mark the extension done until the screenshots have been inspected and the app remains running locally for review.

## Live RNG Verification

Status: done

The live bookcase should continue to use deterministic RNG cover colors. The new designs must not depend on a single fixed color to work.

Check:

- `/books` desktop,
- `/books` mobile,
- at least two visible live examples of the new designs if seeded titles distribute that way,
- forced-open demo pages for both new designs.

If the seeded author books do not naturally show both new designs, temporarily inspect by changing title/seed locally or adding a temporary screenshot-only helper, then remove the helper before final verification.

Acceptance:

- the new artwork remains readable across the existing live palettes,
- no design hardcodes a static live palette in `BookSideView`,
- title plates remain readable,
- no cover face collides with page lines.

## Live Book Size

Status: done

Increase the rendered book size in the live bookcase to **1.75x** the current size.

Implementation notes:

- The likely source is `BookSideView.razor`, where the SVG currently controls rendered size with Tailwind height/width classes.
- Scale the live shelf books without changing the SVG `viewBox`.
- Keep the demo pages readable but do not blindly enlarge every demo if those pages already have their own review sizing.
- Check the horizontal shelf, hover/open animation, page block, shadows, and mobile layout after the size change.

Acceptance:

- live shelf books are approximately 1.75x larger than the current rendered size,
- the shelf remains horizontally scrollable where needed,
- no text or UI overlaps on mobile,
- the bookcase still feels like an infinite shelf rather than a cramped grid,
- the title plate text remains readable at the larger size,
- hover/open animation still looks aligned.

## Iteration Loop

Status: done

This is a visual task, so do not stop after first compile.

### Pass 01

Status: done

Implement first versions and capture:

- `TestResults/TwoNewShowcaseBookDesigns/Pass01/overview-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/Pass01/overview-mobile.png`
- `TestResults/TwoNewShowcaseBookDesigns/Pass01/aurora-open-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/Pass01/prism-open-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/Pass01/books-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/Pass01/books-mobile.png`

Review:

- Are the two new designs clearly new?
- Are they more impressive than filler variants?
- Does the Cloth Hardback cleanup look intentional?
- Are the live shelf books actually 1.75x larger and still usable?
- Does the overview page feel balanced with six cards?

### Pass 02

Status: done

Adjust based on Pass01.

Expected likely refinements:

- simplify Aurora if it gets too wispy at shelf size,
- increase Prism contrast if facets disappear on random colors,
- adjust shelf spacing, shelf band height, or bookcase overflow behavior if 1.75x sizing causes crowding,
- move any ornament away from the title plate,
- adjust demo title y/font if multiline text feels cramped,
- remove any detail that reads like accidental clutter.

Capture into:

- `TestResults/TwoNewShowcaseBookDesigns/Pass02`

### Pass 03

Status: done

Final polish pass.

This can be a no-code verification pass only if Pass02 already looks excellent. Otherwise, make a final targeted SVG adjustment and recapture:

- `TestResults/TwoNewShowcaseBookDesigns/Pass03`

Do not mark the plan complete until Pass03 has been manually inspected.

## Acceptance Criteria

Status: done

Final outcome must satisfy:

- Cloth Hardback has no top/bottom horizontal decorative line pairs.
- The app has six active cover designs.
- Live bookcase books render at approximately 1.75x their previous size.
- The two new designs have their own visual identities.
- The new designs are pure SVG.
- The design demo overview looks good on desktop and mobile.
- The live bookcase keeps deterministic RNG cover colors.
- The enlarged live bookcase remains scrollable and readable on desktop and mobile.
- The live bookcase does not look repetitive or broken with six variants.
- The forced-open state is clean for every new design.
- No title is obscured by artwork.
- No artwork visually merges with the right page block.
- No deployment/database/auth/CRUD changes.

Showcase bar:

- Decorative Hardcover remains strong.
- Aurora Field Guide adds a soft organic premium direction.
- Prism Atlas adds a crisp geometric premium direction.
- The full six-design set feels like intentional template artwork, not random decorations.

## Tests And Verification

Status: done

Run after final visual pass:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed visual snapshot E2E
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query

Keep the app running locally at the end for review.

Execution result:

- Implemented 16 active cover designs total: the original four, Aurora Field Guide, Prism Atlas, and the ten-design extension.
- Added the ten extension routes through the shared catalog: `/books/design-demos/droplet-monograph`, `/books/design-demos/arbor-press`, `/books/design-demos/transit-map-folio`, `/books/design-demos/sunprint-notebook`, `/books/design-demos/origami-edition`, `/books/design-demos/circuit-garden`, `/books/design-demos/marble-index`, `/books/design-demos/beacon-logbook`, `/books/design-demos/woven-archive`, and `/books/design-demos/glasshouse-register`.
- Captured and inspected baseline screenshots in `TestResults/TwoNewShowcaseBookDesigns/Pass01`, `Pass02`, and `Pass03`.
- Captured and inspected extension screenshots in `TestResults/TwoNewShowcaseBookDesigns/ExtensionPass01`, `ExtensionPass02`, and `ExtensionPass03`.
- Confirmed author shelf distribution uses a varied subset of the 16 designs and a 64-title sample reaches every design.
- Confirmed the earlier Books E2E failure was caused by local rate-limit exhaustion during repeated headed browser runs, not a CRUD regression; rerunning against a locally started app with relaxed rate-limit settings passed.
- Deleted one stale generated E2E book row left by the earlier failed run and verified the generated E2E book query returns no rows.
- Final verification passed: `npm run css:build`, `dotnet build .\BlazorAutoApp.sln --no-restore`, `dotnet test .\BlazorAutoApp.sln --no-build`, headed VisualSnapshot E2E, headed RenderMode E2E, headed Books E2E desktop, headed Books E2E mobile `390 x 844`, `dotnet format --verify-no-changes --verbosity minimal --no-restore`, and `git diff --check`.

## Second Extension: Fifteen Additional Cover Designs

Status: done

Add 15 more active SVG designs, bringing the catalog from 16 to 31 total designs.

Target additions:

17. Cipher Codex
18. Topographic Survey
19. Music Score
20. Cartographer Fold
21. Herbarium Slip
22. Nautical Chart
23. Stamp Ledger
24. Quilt Reader
25. Compass Fieldbook
26. Wave Notebook
27. Monoline City
28. Mineral Plate
29. Archive Ribbon
30. Signal Flag Manual
31. Lantern Journal

Rules:

- Keep the first 16 designs stable and append the 15 new entries after `Glasshouse Register`.
- Keep all new designs pure inline SVG.
- Reuse `BookCoverDesignCatalog`, `BookCoverArtwork`, and the existing demo projection.
- Keep each design lightweight: no external assets, filters, masks, scripts, or per-book runtime shape generation.
- Keep title plates readable and untouched.
- Preserve deterministic live RNG design and palette selection.

Implementation result:

- Added all 15 `BookCoverDesignKind` members.
- Added all 15 catalog entries after `Glasshouse Register`.
- Added pure inline SVG artwork branches for all 15 designs.
- Confirmed the design demo catalog now exposes 31 designs through the shared projection.
- Confirmed the new detail route pattern works for each new design: `/books/design-demos/{design-id}` and `/books/design-demos/{design-id}?open=true`.
- Confirmed deterministic live design distribution still works; a 256-title sample reached all 31 designs.

### Second Extension Visual Passes

Status: done

Capture and inspect:

- `TestResults/TwoNewShowcaseBookDesigns/SecondExtensionPass01/overview-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/SecondExtensionPass01/overview-mobile.png`
- one forced-open detail screenshot for each of the 15 new designs,
- `/books` desktop and mobile screenshots.

If Pass01 needs polish, capture `SecondExtensionPass02`; otherwise capture it as a no-code confirmation pass. Capture `SecondExtensionPass03` as the final confirmation pass.

Execution result:

- Captured and inspected the full first pass in `TestResults/TwoNewShowcaseBookDesigns/SecondExtensionPass01`.
- Captured and inspected no-code confirmation screenshots in `TestResults/TwoNewShowcaseBookDesigns/SecondExtensionPass02`.
- Captured final live confirmation screenshots in `TestResults/TwoNewShowcaseBookDesigns/SecondExtensionPass03`.
- Inspected forced-open detail screenshots for all 15 added designs.
- Inspected `/books` desktop and mobile screenshots after the extension.
- Confirmed title plates remain readable, page blocks stay aligned, and mobile shelf rendering remains usable.

### Second Extension Test Gate

Status: done

Run after the final visual pass:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln --no-restore`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed VisualSnapshot E2E
- headed RenderMode E2E
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query

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
- Local app is running on `http://127.0.0.1:5099` for review.

## Third Extension: Fifteen Additional Cover Designs

Status: done

Add 15 more active SVG designs, bringing the catalog from 31 to 46 total designs.

Target additions:

32. Observatory Notebook
33. Blueprint Register
34. Type Foundry
35. Stage Playbook
36. Mosaic Codex
37. Ink Wash Journal
38. Laboratory Log
39. Railway Timetable
40. Patent Notebook
41. Vineyard Register
42. Geode Almanac
43. Calendar Folio
44. Atlas Pinboard
45. Copperplate Ledger
46. Kinetic Diagram

Rules:

- Keep the first 31 designs stable and append the 15 new entries after `Lantern Journal`.
- Keep all new designs pure inline SVG.
- Reuse `BookCoverDesignCatalog`, `BookCoverArtwork`, and the existing demo projection.
- Keep each design lightweight: no external assets, filters, masks, scripts, or per-book runtime shape generation.
- Keep title plates readable and untouched.
- Preserve deterministic live RNG design and palette selection.

Implementation result:

- Added all 15 `BookCoverDesignKind` members.
- Added all 15 catalog entries after `Lantern Journal`.
- Added pure inline SVG artwork branches for all 15 designs.
- Confirmed the design demo catalog now exposes 46 designs through the shared projection.
- Confirmed the new detail route pattern works for each new design: `/books/design-demos/{design-id}` and `/books/design-demos/{design-id}?open=true`.
- Confirmed deterministic live design distribution still works; a 512-title sample reached all 46 designs.

### Third Extension Visual Passes

Status: done

Capture and inspect:

- `TestResults/TwoNewShowcaseBookDesigns/ThirdExtensionPass01/overview-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/ThirdExtensionPass01/overview-mobile.png`
- one forced-open detail screenshot for each of the 15 new designs,
- `/books` desktop and mobile screenshots.

If Pass01 needs polish, capture `ThirdExtensionPass02`; otherwise capture it as a no-code confirmation pass. Capture `ThirdExtensionPass03` as the final confirmation pass.

Execution result:

- Captured and inspected the first pass in `TestResults/TwoNewShowcaseBookDesigns/ThirdExtensionPass01`.
- Captured one forced-open detail screenshot for each of the 15 added designs.
- Captured full-page desktop and mobile overview screenshots so the lower rows of the 46-design catalog were checked.
- Captured no-code confirmation screenshots in `TestResults/TwoNewShowcaseBookDesigns/ThirdExtensionPass02`.
- Captured final confirmation screenshots in `TestResults/TwoNewShowcaseBookDesigns/ThirdExtensionPass03`.
- Inspected `/books` desktop and mobile screenshots after the extension.
- Confirmed title plates remain readable, page blocks stay aligned, and mobile shelf rendering remains usable.

### Third Extension Test Gate

Status: done

Run after the final visual pass:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln --no-restore`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed VisualSnapshot E2E
- headed RenderMode E2E
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query

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
- Local app is running on `http://127.0.0.1:5099` for review.

## Fourth Extension: Fifteen More Distinct Cover Designs

Status: done

Add 15 more active SVG designs, bringing the catalog from 46 to 61 total designs. This batch must be more visually distinct than just small variations of the existing set.

Target additions:

47. Bauhaus Reader
48. Film Slate Journal
49. Punchcard Manual
50. Seismograph Log
51. Weather Station Register
52. Alpine Trail Guide
53. Bookmark Folio
54. Stained Glass Reader
55. Currency Ledger
56. Newspaper Archive
57. Checkout Card
58. Embroidery Sampler
59. Waveform Notes
60. Microfiche Index
61. Solar Dial Folio

Rules:

- Keep the first 46 designs stable and append the 15 new entries after `Kinetic Diagram`.
- Keep all new designs pure inline SVG.
- Reuse `BookCoverDesignCatalog`, `BookCoverArtwork`, and the existing demo projection.
- Make the 15 additions noticeably distinct in visual grammar, not merely recolored copies.
- Keep each design lightweight: no external assets, filters, masks, scripts, or per-book runtime shape generation.
- Keep title plates readable and untouched.
- Preserve deterministic live RNG design and palette selection.

Execution result:

- Added all 15 catalog entries and enum values after `Kinetic Diagram`, preserving the first 46 designs.
- Added one pure inline SVG branch per design in `BookCoverArtwork.razor`.
- Kept the live shelf deterministic: the same title/id seed always lands on the same design, while the catalog now has 61 active choices.
- Ran a 5,000-title deterministic distribution check against the same title-seed and mix algorithm; all 61 designs were reached with no missing entries.

### Fourth Extension Visual Passes

Status: done

Capture and inspect:

- `TestResults/TwoNewShowcaseBookDesigns/FourthExtensionPass01/overview-full-desktop.png`
- `TestResults/TwoNewShowcaseBookDesigns/FourthExtensionPass01/overview-full-mobile.png`
- one forced-open detail screenshot for each of the 15 new designs,
- `/books` desktop and mobile screenshots.

If Pass01 needs polish, capture `FourthExtensionPass02`; otherwise capture it as a no-code confirmation pass. Capture `FourthExtensionPass03` as the final confirmation pass.

Execution result:

- Captured and inspected `FourthExtensionPass01` with full desktop/mobile overview, live `/books` desktop/mobile, and forced-open detail pages for each new design.
- Captured no-code confirmation passes `FourthExtensionPass02` and `FourthExtensionPass03`.
- Final inspected screenshots are in `TestResults/TwoNewShowcaseBookDesigns/FourthExtensionPass03`.
- Confirmed the mobile and desktop shelves keep readable title plates, aligned page blocks, and distinct cover silhouettes/details.

### Fourth Extension Test Gate

Status: done

Run after the final visual pass:

- `npm run css:build`
- `dotnet build .\BlazorAutoApp.sln --no-restore`
- `dotnet test .\BlazorAutoApp.sln --no-build`
- headed VisualSnapshot E2E
- headed RenderMode E2E
- headed Books E2E desktop
- headed Books E2E mobile `390 x 844`
- `dotnet format --verify-no-changes --verbosity minimal --no-restore`
- `git diff --check`
- E2E cleanup DB query

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
- Local app is running on `http://127.0.0.1:5099` for review.

## Non-Goals

Status: done

- Do not add bitmap images.
- Do not change the book modal view/edit/add flow.
- Do not touch database schema or migrations.
- Do not touch deployment.
- Do not touch authentication.
- Do not reintroduce Library Ledger or Modern Paperback.
- Do not create generic shared UI folders outside `Features/Books`.
