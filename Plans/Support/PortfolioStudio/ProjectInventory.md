# Portfolio project inventory and story briefs

Reviewed: 2026-10-12.
Parent plan: [Portfolio Studio delivery master plan](../../PortfolioStudioImplementation.md).

Use [PageBriefs.md](PageBriefs.md) for editorial headlines and illustration treatments, [DeliveryPhases.md](DeliveryPhases.md) for executable packets, and [Progress.md](Progress.md) for current publication evidence. This inventory remains the factual source register and stable section-ID reference; proposed copy is not proof of implemented behavior.

This inventory covers the six owner projects named in the template's author-book seed and six additions: MiniTwit, BestBets, Geospatial research, Grumlebob, JobHunt and Template. The owner's 2026-10-12 request supersedes the earlier Template exclusion; cover demonstrations remain outside the catalog. This is a content preparation specification, not publication/runtime evidence. Unlost's recovered working files were separately imported into the owner's new repository; no source application was started or tested by this refinement.

## 1. Catalog and readiness

| Proposed order | Portfolio slug | Display name | Evidence available | Next content task |
| --- | --- | --- | --- | --- |
| 10 | `improveddb` | ImprovedDb | Owner motivation; prior source/public-interface review; genuine captures | Recheck factual copy, select media and prepare six sections |
| 20 | `geckobot` | GeckoBot | Private GeckoBot selected; Python structure reviewed; earlier demo deleted with private backup | Prepare source-backed fictional booking figures; omit unverified historical-use claims |
| 30 | `traceback` | TraceBack | Owner description and local README/concept/boundary/demo documentation | Prepare a prototype case study and capture a synthetic-data workflow |
| 40 | `kinojoin` | KinoJoin | Local UI, domain, import and calendar source | Prepare a cinema-planning case study and capture an example event |
| 50 | `ship-inspections` | Ship Inspections | Owner-confirmed repository; local inspection/upload source and feature docs | Prepare a vessel-part/image-upload story and capture a synthetic inspection |
| 60 | `unlost` | Unlost | Recovered Java/JavaFX source; confirmed Project map report and genuine figures | Pin imported source and reconcile it with dated report/media |
| 70 | `minitwit` | MiniTwit | Owner-supplied repository; local report, system description and operational documentation | Prepare a microblogging/DevOps story with dated architecture and workflow figures |
| 80 | `bestbets` | BestBets | Architecture report/prototypes; owner-selected school Exam PDF and BestBets deck located | Review preferred PDF/deck and reconcile their versions with repository evidence |
| 90 | `geospatial-research` | Geospatial research | Owner-supplied ExamGDS repository; local notebook and New York crime report | Prepare a research story with attributed maps, methods and limitations |
| 100 | `grumlebob` | Grumlebob | Owner-approved free-offer automation, passive income, approximately DKK 500,000 profit in one year and capacity explanation | Attribute claims to owner; prepare permitted generic illustrations |
| 110 | `jobhunt` | JobHunt | Owner's administrative/personal-work boundary; private repository and local workflow documentation | Prepare a restrained story with fictional examples; reconcile writing scope before publication |
| 120 | `template` | Template | Owner's tooling/choice list and BlazorAutoAppTemplate repository | Review pinned tooling, two frontend choices and three deployment choices |

Ordering is an editorial proposal; the manifest owns it. All twelve entries belong in the content backlog and local review catalog. Public visibility follows content readiness. Do not fill an incomplete entry with invented product features or publish a broken card destination.

The Books seed inventory is `BlazorAutoApp/Features/Books/AuthorBookcase/Seed/AuthorBookSeeder.cs`. Its six entries are TraceBack, Ship Inspections, ImprovedDb, KinoJoin, Unlost and GeckoBot. Their seed URLs are null. These book records are sample data, not a project-content API, and cannot establish public websites, repository URLs, dates or feature descriptions. The owner's subsequent project list extends the portfolio beyond that seed without requiring changes to the template. The owner supplied source repositories for KinoJoin, Ship Inspections, MiniTwit, BestBets and Geospatial research and confirmed the Unlost project-material folder. `ship-inspections` is a proposed portfolio slug, not a change to the template's `ship` seed key.

### Comparison with the Books implementation

The inspected Books implementation has two catalogs with different purposes:

| Source | Entries | Relationship to this portfolio |
| --- | --- | --- |
| `BlazorAutoApp/Features/Books/AuthorBookcase/Seed/AuthorBookSeeder.cs` | Six owner project titles | All six are included above |
| `BlazorAutoApp.Test/Features/Books/Seed/AuthorBookSeedTests.cs` | Expects exactly `geckobot`, `improveddb`, `kinojoin`, `ship`, `traceback`, `unlost` | Confirms the intended seed inventory; the test was read, not run |
| `BlazorAutoApp.Client/Features/Books/Shared/BookCoverDesignCatalog.cs` | Ten visual cover definitions and demonstration titles | Cover experiments are not additional verified owner projects |
| `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemoCatalog.cs` | Derives its entries directly from the cover catalog | Adds navigation around the same ten cover demos, not another content catalog |
| `README.md`, Current Behavior | Mentions four older local seed titles plus classics | Does not establish additional projects; its `SeedLocalDefaults` description was not found in the inspected current C# implementation |

Full cover-demo comparison:

| Cover ID | Cover style | Demonstration title | Content decision |
| --- | --- | --- | --- |
| `cloth-hardback` | Cloth Hardback | The Great Gatsby | Book/demo title; no portfolio project inferred |
| `decorative-hardcover` | Decorative Hardcover | Trace Back | The already-included TraceBack project, shown as a cover demo |
| `field-notebook` | Field Notebook | Designing Reliable Systems | Demo title; no verified project under this name |
| `prism-atlas` | Prism Atlas | Vector Room | Demo title; no verified project under this name |
| `droplet-monograph` | Droplet Monograph | Clear Signal | Demo title; no verified project under this name |
| `transit-map-folio` | Transit Map Folio | Line Atlas | Demo title; no verified project under this name |
| `compass-fieldbook` | Compass Fieldbook | True North | Demo title; no verified project under this name |
| `atlas-pinboard` | Atlas Pinboard | Pinned Atlas | Demo title; no verified project under this name |
| `seismograph-log` | Seismograph Log | Pulse Trace | Demo title; no verified project under this name |
| `alpine-trail-guide` | Alpine Trail Guide | Trail Guide | Demo title; no verified project under this name |

This explains the larger visible demo catalog. The reviewed source establishes six named owner projects and ten cover designs, with TraceBack appearing in both. Six owner additions, including Template requested on 2026-10-12, bring the backlog to twelve projects independently of the cover designs. Do not add invented case studies for the cover titles. Recompare these files with the verified upstream baseline at execution time.

### Source register for continued improvement

| Source ID | Project | Source and origin | What it supports | What remains to establish |
| --- | --- | --- | --- | --- |
| `SRC-IMPROVEDDB-WEB` | ImprovedDb | Owner-supplied [ImprovedDb site](https://improveddb.jacobgrum.com/) and its browse, title/cast, statistics and ML pages | Public workflow and original screenshot references | Recheck pages, facts and capture dates before publication |
| `SRC-IMPROVEDDB-CODE` | ImprovedDb | Owner-supplied local repository; README, architecture/import/statistics/ML docs and rating policy from the earlier investigation | Engineering explanation and dated model/rating details | Record the specific reviewed revision when preparing final content |
| `SRC-KINOJOIN` | KinoJoin | Owner-supplied [Grumlebob/KinoJoin](https://github.com/Grumlebob/KinoJoin), plus the local checkout/file list in section 4 | Cinema planning, sharing, participant choices and calendar source | Screenshot capture, owner contribution and exact public/local revision alignment |
| `SRC-SHIP` | Ship Inspections | Owner-supplied [Grumlebob/BlazorTusReliableUpload](https://github.com/Grumlebob/BlazorTusReliableUpload), plus the local checkout/file list in section 7 | Vessel-part forms, image handling and TUS implementation | Screenshot capture, public/local revision alignment and behavior claims requiring execution |
| `SRC-TRACEBACK` | TraceBack | Owner description; local `README.md`, `Docs/CoreConcepts.md`, `Docs/ReproducibilityBoundaries.md` and `Docs/Demos.md` | Research-prototype purpose, concepts, saved context and limitations | Media capture, individual contribution and an approved public source/tutorial URL |
| `SRC-UNLOST` | Unlost | Owner-confirmed Dropbox **Project map** report/figures and recovered [Grumlebob/Unlost](https://github.com/Grumlebob/Unlost) source | Historical map/pathfinding account; Java/JavaFX/FXML, Gradle, JUnit and JaCoCo configuration | Pin import revision, reconcile source/report, review media attribution and contribution; runtime remains unverified |
| `SRC-GECKOBOT` | GeckoBot | Selected private [GeckoBot](https://github.com/Grumlebob/GeckoBot), renamed from mail; reviewed file trees/Python AST structure; earlier demo deleted with complete private Git backup | Outlook/COM booking-email flow, parser/UI separation and configuration functions; no execution evidence | Review requirements/actual use and prepare fictional media; omit private source/backup buttons |
| `SRC-MINITWIT` | MiniTwit | Owner-supplied [Grumlebob/The-Pentuple-MiniTwit](https://github.com/Grumlebob/The-Pentuple-MiniTwit); local report chapters and `MiniTwitSolution/Documentation/` | Microblogging purpose, historical .NET migration, architecture and documented DevOps work | Capture selected media, confirm individual contribution and align the reviewed local/public revisions |
| `SRC-BESTBETS` | BestBets | Owner-selected school `Exam.pdf` and `BestBets.pptx` (locations private), plus [Grumlebob/Architecture](https://github.com/Grumlebob/Architecture), report/diagrams/prototypes | Preferred text reviewed; broker/final actor design and prototype limits reconciled | Visually select permitted figures; preserve targets/results and team attribution |
| `SRC-GEOSPATIAL` | Geospatial research | Owner-supplied [Grumlebob/ExamGDS](https://github.com/Grumlebob/ExamGDS); local `exam.ipynb` and `New_York_Crime.pdf` | New York crime/amenity research question, documented spatial methods and data-preparation issues | Verify dataset windows/licenses, select legible figures and review conclusions and contribution |
| `SRC-GRUMLEBOB` | Grumlebob | Owner statements on 2026-10-12; restricted folder recorded privately, contents unreviewed | Free online offer automation for passive income; approximately DKK 500,000 profit in one year; membership capacity due to concern about being caught | Attribute to owner, avoid invented year/member count/guarantees; protect remaining restricted context and prepare generic media |
| `SRC-JOBHUNT` | JobHunt | Owner-supplied [Grumlebob/JobHunt](https://github.com/Grumlebob/JobHunt); authenticated repository metadata confirms private visibility; local `README.md`, `AGENTS.md` and `jobhunt/applications/` procedures | Administrative workflow, document organization, Notion tracking, browser-assisted preparation and user-only final submission policy | Use D10: acknowledge drafting assistance/personal review, omit unverified account creation, select fictional media |
| `SRC-TEMPLATE` | Template | Owner's 2026-10-12 list and [BlazorAutoAppTemplate](https://github.com/Grumlebob/BlazorAutoAppTemplate) | Lighthouse, SonarQube, Qlty, Trivy, ZAP, sitespeed.io, scc; Blazor/React; Cloud/LocalCluster/LocalSingleNode | Pin source evidence for tooling/choices; configuration alone establishes no passing score or deployment |

Keep these source IDs in private editorial fact notes so later copy changes can be traced to evidence. Public copy includes only useful source links and permitted provenance, not this preparation table or private machine paths. The owner explicitly excluded `hojelseMaps.zip`; it is not an Unlost source. Record exact local locations in ignored preparation notes when needed, rather than introducing machine-specific paths into tracked plans.

## 2. Common story brief

Every project preparation task should produce:

1. A one-sentence card summary explaining the problem or purpose in ordinary language.
2. A short opening introducing the project and its actual status, with the owner's contribution/context when supplied.
3. Three to six meaningful main sections. The content determines their number; avoid padding every project to six sections.
4. At least one useful cover and, when available, two to four supporting figures with captions and accessible descriptions. Use illustrative art openly when genuine screenshots are unavailable.
5. A concise engineering explanation tied to a visible feature, supported by source evidence.
6. Honest tradeoffs or limitations and only documented outcomes. Numbers need a source and context.
7. Verified outbound links, or no outbound action when the project is not publicly accessible.
8. A private editorial evidence record: source repository/commit, relevant files, review date, fact checks and media permission/provenance. Private paths and internal references are excluded from the public bundle.
9. Source-supported `technologyIds` referencing the common registry. The compiler supplies the shared **Techs** section; the published references also feed the deduplicated Technologies page.

The project status (for example prototype or archived) is separate from editorial publication status (draft, review-ready or published). A historical project may have a polished public story; a currently running app may still have an unpublished draft. Do not derive employment, project dates or personal ownership scope from file timestamps or repository existence.

## 3. ImprovedDb

### Story position

Explain a personal question that led to a browsable movie/series product, then show the engineering supporting it. The supplied motivation and six approved sections remain in the parent plan.

Proposed card copy: **Movie and series discovery, familiar faces, and the data behind the ratings.** This is editorial draft copy based on the reviewed product.

### Content preparation checklist

- Preserve the owner's motivation before introducing technical details.
- Use an actual title/cast view to show finding an actor's most popular, highest-rated and recent credits. Explain what the reader sees in the caption.
- Explain ratings through a sourced example and the handling of missing signals. Keep the detailed rating note within this section.
- Illustrate the collection/publication path using current source evidence. Do not imply live provider calls occur on every page request.
- Select one or two readable statistics graphs and explain their question, not just their implementation.
- Explain historical ML exploration and its limitations. Recheck counts and date ranges before publishing.
- Include a verified live-site action to `https://improveddb.jacobgrum.com/`. Add a source-code link only when a public URL and publication intent are established.

### Media brief

Cover: genuine browsing/title interface. Supporting assets: familiar-faces capture, rating comparison, data-flow diagram, a real generated graph and ML interface. Preserve screenshot capture dates. Technical images must remain readable on mobile; use enlargement instead of forcing all labels into a tiny crop.

## 4. KinoJoin

### Verified source findings

The owner supplied [Grumlebob/KinoJoin](https://github.com/Grumlebob/KinoJoin). Its public repository is accessible. The local source was reviewed at commit `abf8a978d180399d63bbabac9df5bcff6dc48c37`; Git reported a clean working tree at review time. This establishes the inspected source state, not successful execution or current public availability. Check local/public revision alignment before using permanent source links in the final story.

- `Presentation/Presentation.Client/Pages/JoinCreate.razor` presents cinema-event creation: cinema/movie/genre/date filtering, showtime selection, event title/description/deadline, and a create-and-share flow.
- `Presentation/Presentation.Client/Pages/JoinFill.razor` presents a shared event, participant showtime selections, results navigation and host sharing controls.
- `Domain/KinoJoinModels.cs` models events, showtimes, participant selections and a chosen showtime.
- `Presentation/Presentation.Client/Pages/Components/Specialised/Filling/JoinEventResults.razor` contains results, host confirmation, a booking link and calendar actions.
- `Application/Modules/CalendarService.cs` constructs a calendar file and a Google Calendar URL. Mention export as a feature; do not claim timezone correctness or calendar-client compatibility without verification.
- `Infrastructure/ExternalServices/KinoAPI/FetchNewestKinoDkDataService.cs` imports cinema/showtime-related data from Kino.dk into the application's model.
- The inspected project files use C#/.NET 8, Blazor WebAssembly-related UI packages and EF Core/Npgsql; the README describes Tailwind and Auth0. These are historical source observations, not a recommendation to adopt those exact dependency versions in the portfolio.

Proposed card copy: **Plan a cinema outing, share possible showtimes, and collect the group's preferences.**

### Proposed sections

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `the-coordination-problem` | Choosing a cinema trip together | Explain the coordination problem; obtain the owner's actual motivation and contribution | Opening product cover; no invented personal anecdote |
| `finding-showtimes` | Finding the right showtimes | Show how cinema, movie, genre and date filters narrow the available options | Actual creation/filter view with example data |
| `creating-and-sharing` | Creating and sharing an event | Explain the event details, selected options, deadline and shared link | Creation/share flow; replace real participant links with examples |
| `collecting-preferences` | Collecting preferences | Explain participant selections and the results view without claiming a particular voting algorithm | Example response screen and results matrix |
| `choosing-and-following-through` | From a choice to a plan | Host confirmation, booking handoff and calendar actions | Chosen-showtime/calendar panel |
| `data-and-design` | Data model and design decisions | Explain external showtime imports and the event/participant/selection relationships; include current limitations | Simple domain/data-flow diagram |

### Publication boundaries

Do not describe KinoJoin as a booking provider, ticket-payment system, automatic consensus engine or deployed service without evidence. The source contains a link to an external booking flow; that is not ticket purchase handled by KinoJoin. Personal motivation, dates, collaborators and exact contribution need owner input. Original Danish UI labels may appear in screenshots with English explanatory captions.

Do not publish participant names/emails, real shared event IDs or configuration/setup credentials. A screenshot session should use synthetic event details. The historical README's deployment/authentication instructions are not the portfolio's operating instructions and must not be copied into the story.

## 5. TraceBack

### Verified source findings

The local source was reviewed at commit `5722d4f1633b7c47852f5de33f476f57b1fe2a61`; Git reported a clean working tree at review time. No runtime or test verification was performed for this planning task.

- `README.md` describes a final thesis research prototype for preserving and inspecting simulation-run context, initially motivated by wind-energy simulation work around the Balancing Tool Chain at DTU.
- `Docs/CoreConcepts.md` explains Project, Pipeline, SoloExperiment, input/box/output blocks, DataLocation and RunManifest.
- `Docs/ReproducibilityBoundaries.md` distinguishes mutable references from stronger snapshots and identifies external environments, schedulers, credentials and storage availability as user responsibilities.
- The documented integrations cover local files, Git/GitLab/GitHub references, SSH-style storage, OneDrive and MinIO-compatible object storage.
- PostgreSQL stores metadata/references while larger payloads remain in configured storage backends.
- `Docs/Demos.md` describes synthetic demonstration material and a create/select project, build pipeline, save run, inspect history and recreate selections journey.

The README establishes project context; it does not establish the owner's academic qualification, employment at DTU or individual contribution. Obtain those details before writing biography or role statements.

Proposed card copy: **Preserve simulation inputs, scripts, outputs and run context so experiments can be inspected and recreated later.**

### Proposed sections

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `the-reproducibility-problem` | Keeping the context of an experiment | Explain why scattered files, scripts and assumptions are difficult to reconstruct | Actual project/pipeline overview with synthetic names |
| `modelling-a-pipeline` | Making the pipeline explicit | Show experiments and their input, box and output blocks | Pipeline/experiment screenshot and annotated diagram |
| `connecting-data` | Connecting data and code | Explain DataLocation references across storage types | Safe example of local/Git/remote selections; no private paths |
| `saving-run-evidence` | Saving a run's evidence | Explain manifests, notes and snapshot choices, and the metadata/payload boundary | Save-run view and short sanitized manifest excerpt |
| `history-and-recreation` | Revisiting a saved run | Show history and reloading the saved selections/context | History and recreate views from the same example |
| `boundaries-and-lessons` | Reproducibility boundaries | Explain what remains mutable or external, and prototype limitations | Small comparison of mutable references versus snapshots |

### Publication boundaries

Use the term **research prototype** unless later evidence establishes another status. TraceBack supports traceability and recreation of saved context; it does not execute the entire simulation pipeline or guarantee identical scientific results. Distinguish snapshot creation from a reference that can change. Do not depict it as an HPC scheduler or regulatory certification system.

Prefer a local synthetic demo for screenshots. Avoid research datasets, institutional paths, usernames, tokens and remote hostnames. A tutorial/video link appears in the README, but confirm availability, relevance and publication permission before adding it to the portfolio. Capture UI stills first; video is optional and must not be required to understand the story.

## 6. GeckoBot

The sole active source is the selected private [GeckoBot](https://github.com/Grumlebob/GeckoBot) repository, renamed from mail on 2026-10-11 at the owner's request. Repository ID, default branch, head and private visibility were verified unchanged by the rename. Read-only tree/Python-AST review on the same date inspected it under the former name at `af54ad38f5a9ca3c0098ca663a4ea78fff58db79` and the earlier MailDemo at `fc9a44c6be1a1cd28d4a5a3a4341accd0a5f30be`. At the owner's request, MailDemo was deleted after preserving all five commits and its unique examples in a complete private Git mirror/bundle. Backup verification passed; authenticated lookup confirmed deletion and the retained repository remained accessible. Private recovery details are in the ignored source note. No app, inbox, calendar or automation was executed.

`GeckoBot` includes `GeckoBot.bat`, separate `geckoBot.py`, `mailParsers.py` and `ui.py`, a requirements document and guide. Its 14-commit/13-file baseline has declarations for Windows Outlook/COM integration, booking-email parsing, new/changed/cancelled meeting handling, folder movement, Tkinter UI, employee management, meeting-type settings and notifications. The five-file demo has distinct event-based/timezone examples; the retained repository is the more developed application structure, not an exact superset or a runtime-verified replacement. Source selection is resolved; confirm actual historical use, runtime claims and timezone compatibility before publication. The private source and backup are editorial references, not public source buttons. Do not use employee/customer/inbox/calendar records for media.

Proposed card copy: **Automating repetitive email work.** Do not label it an AI agent, outreach platform or autonomous sending service without source evidence.

Section brief, to refine after requirements and owner-version review:

| Stable ID | Heading | Information needed |
| --- | --- | --- |
| `the-repetitive-work` | The repetitive work | What emails/tasks are automated; what originally motivated the project |
| `the-workflow` | The workflow | Trigger, inputs, transformations, human actions and output |
| `control-and-review` | Control and review | Actual approval, preview, failure handling or limits, if implemented |
| `implementation` | Implementation | Verified integrations, architecture and one meaningful technical decision |
| `outcomes-and-lessons` | Outcomes and lessons | Demonstrated result or owner reflection; no unsourced time-saved number |

Media request: workflow cover, a genuine configuration or preview screen if one exists, and a sanitized before/after example. Use fictional addresses and message content. If there is no UI, use a diagram and a reviewed code/example artifact. Do not fabricate an application screenshot.

## 7. Ship Inspections

The owner identifies [Grumlebob/BlazorTusReliableUpload](https://github.com/Grumlebob/BlazorTusReliableUpload) as this project's repository. Keep **Ship Inspections** as the portfolio display name and `ship-inspections` as its proposed slug; explain the repository name through the upload feature only if useful to readers.

### Verified source findings

The local source was reviewed at commit `bde4b733c589c8d195a57c3d25ec14dd7ee02d9d`; Git reported a clean working tree at review time. No app startup, upload or runtime inspection was performed.

- `README.md` describes a local sample built from the application template, with .NET 10 Blazor Interactive Auto, EF Core/PostgreSQL, Redis and resumable uploads through `tusdotnet`. It explicitly excludes the template's CI/CD/deployment package; do not present it as an operational production service.
- `BlazorAutoApp.Client/Features/Inspections/InspectionFlow/Pages/Flow.razor` presents an inspection type, vessel name, several vessel views, selectable ship segments and completion states.
- `BlazorAutoApp.Client/Features/Inspections/InspectionFlow/Components/VesselPartForm.razor` combines attached images, notes and structured fouling/coating/hull-condition fields.
- `HullImages.md` describes upload progress, pause/resume, metadata, validation, thumbnail delivery and the temporary-to-final storage path.
- `BlazorAutoApp/wwwroot/js/tusUpload.js` keeps browser upload sessions, creates a TUS resource, synchronizes an offset with HEAD and sends chunks with PATCH. This is source evidence for session-level resumability, not proof of persistence across a browser reload.
- `BlazorAutoApp.Core/Features/Inspections/HullImages/Domain/HullImage.cs` stores file metadata and a vessel-part association. The UI displays `AiHullScore`, but the inspected model defaults it to zero and this review did not establish a working inference pipeline.

Proposed card copy: **Record vessel-part observations and attach inspection images through a resumable upload workflow.**

### Proposed sections

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `the-inspection-workflow` | An inspection organized by vessel part | Obtain the owner's motivation/context; introduce the actual workflow | Synthetic vessel inspection overview |
| `navigating-the-vessel` | Navigating the vessel | Explain view selection, ship segments and completion indicators | Actual segmented-vessel screen and detail crop |
| `recording-observations` | Recording observations | Show notes and structured condition fields tied to a part | Example part form with synthetic observations |
| `uploading-images` | Reliable image uploads | Explain progress, chunks, offsets and pause/resume in the inspected browser session | Upload state screenshots and a small TUS flow diagram |
| `storing-and-browsing` | From upload to usable images | Validation, persisted metadata, thumbnails and original-image access | Actual thumbnail/detail view; storage diagram |
| `tradeoffs-and-next-steps` | Tradeoffs and next steps | Local sample status, storage assumptions, source/documentation discrepancies and deferred AI work | Concise explanation; no fabricated analysis results |

### Publication boundaries

Obtain the owner's contribution and any client/collaborator attribution before stating professional context. Use fictional vessel names and permitted/synthetic photographs; remove identifying file names and metadata. Do not imply regulatory compliance, offline inspection support, generated reports, cloud storage, AI diagnosis or deployed reliability without evidence.

The feature document contains different upload-limit figures and mixes existing/future behavior. Reconcile details with current implementation before quoting a limit. A displayed AI score field is not proof of ML inference. A resumable session is not proof of recovery after closing/reloading the browser. Portfolio screenshots explain this system; the portfolio itself does not acquire an inspection form or upload API.

## 8. Unlost

The owner describes Unlost as a Java map application with A* and confirms **Project map** as the correct Dropbox folder for its school materials. The owner explicitly identifies `hojelseMaps.zip` as someone else's project; exclude it from Unlost's evidence, screenshots, architecture and code claims.

### Verified artifact findings

- The folder's `rapport.pdf` is a 109-page first-year Map of Denmark team-project report, dated 20 May 2022. It names Unlost and includes the owner's name. This supports a historical team-project context, not sole ownership of every component.
- The report describes OpenStreetMap input, map drawing, address search, points of interest, Kd-tree spatial operations, Dijkstra and A* routing.
- Its user guide describes car/bike/walk choices, suggested addresses, a textual route plan and overview values.
- Its conclusion discusses full-Denmark performance limitations and code-structure tradeoffs. The A* discussion acknowledges heuristic limitations and cases where its route differs from Dijkstra's.
- `rapport/user/menu.PNG` visibly identifies Unlost. `rapport/images/routeplan.PNG` shows an actual route-instruction view. Supporting artifacts include `rapport/images/astarwithexplored.png`, `rapport/images/astarpath.png`, `rapport/images/graph/osmgraphlive.png` and Kd-tree illustrations.
- On 2026-10-12 the owner located the Java source and supplied the new [Unlost repository](https://github.com/Grumlebob/Unlost) for its import. Recovered files include JavaFX 18, FXML views, Gradle 7.3.3, JUnit 5 and JaCoCo configuration. Preserve the existing local edits; pin the imported revision for later content review. Large regional OSM files/archives and generated caches are excluded from Git; the exact historical `small.osm` test fixture is retained. No build/test/runtime result is established by the import.

Proposed card copy: **A Java map application exploring address search, route planning and A* pathfinding.**

### Proposed sections

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `building-a-map-application` | Building a map application | Introduce the team project and the map/navigation problem; obtain the owner's specific contribution | Genuine Unlost UI cover from the confirmed materials |
| `from-map-data-to-screen` | From map data to the screen | Explain the report's OSM parsing, roads and drawing model | Map view and reviewed data/rendering diagram |
| `finding-addresses` | Finding addresses and places | Suggested addresses, search structures and points of interest | Actual address-menu and POI artifacts |
| `routing-with-astar` | Exploring routes with Dijkstra and A* | Describe the implemented approach as documented, its heuristic and limitations | Existing explored-edge/path images and route-plan screenshot |
| `spatial-data-and-performance` | Spatial data and performance | Kd-tree queries and tradeoffs with a larger map | Existing tree/range-query illustration; no invented benchmark |
| `lessons-from-the-project` | Lessons from the project | Historical teamwork, coupling/UI/performance lessons and what the owner would change | Concise sourced reflection after owner review |

### Publication boundaries

Use the report as a dated project account, not evidence of current runtime behavior. Do not claim optimal A* routes, national-scale smooth performance, current map accuracy, measured speedups or sole authorship. Explain the documented limitations plainly without repeating unverified mathematical claims from the report. Review map-data attribution and screenshot reuse before publication. Keep exact personal start/end addresses out of published examples.

Preserve a selection of genuine artifacts and their captions in the portable content package. Do not commit the entire school folder or another team's source archive. Use a static case study; rebuilding the Java map app or embedding an interactive map is outside the portfolio implementation.

## 9. MiniTwit

Use **MiniTwit** as the display name, regardless of the repository's longer name. Source: [Grumlebob/The-Pentuple-MiniTwit](https://github.com/Grumlebob/The-Pentuple-MiniTwit).

Proposed card copy: **A microblogging application exploring software evolution, deployment and observability.**

### Reviewed evidence

The local report's `report/chapters/00_introduction.tex` describes a spring 2025 team course project migrating a Python Flask MiniTwit to .NET. Users register, post messages and read a shared timeline. `01_System_perspective.tex` documents a Blazor WebAssembly client, .NET Minimal API, PostgreSQL, Docker Swarm and Serilog/Seq logging. The repository also contains CI/deployment workflows and documentation for testing, security, TLS and performance. These are historical source findings, not verification of a currently operating service or every operational claim in the report.

### Proposed sections

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `a-small-social-application` | A small social application | Introduce the timeline and course/team context; clarify personal contribution | Genuine timeline screenshot using example accounts |
| `evolving-the-system` | Evolving the system | Explain the documented Flask-to-.NET migration and client/API responsibilities | Redrawn architecture and one relevant code excerpt |
| `delivery-workflow` | Building and delivering changes | Review CI, tests and deployment workflow from the actual files | Sanitized workflow diagram or dated run capture |
| `observability` | Seeing what the system is doing | Connect logs and response/error/message metrics to operational questions | Selected Seq graph with its time range and explanation |
| `scaling-and-lessons` | Scaling decisions and lessons | Explain deployment/cache choices, failures and tradeoffs from reviewed evidence | Deployment diagram and a sourced reflection |

Prepare media from the client, report diagrams and operational docs. Treat `Performance.md` entries as a dated development log; do not invent throughput or uptime. Review current workflow/report agreement before final copy. Do not publish historical raw deployment addresses or expose a live-site button based on the README's old addresses. The public repository is the supplied outbound link.

## 10. BestBets

Source: [Grumlebob/Architecture](https://github.com/Grumlebob/Architecture). The owner describes designing architecture for fictitious scenarios with very large data volumes and bursts during events such as the World Cup.

The owner additionally prioritizes the school-material `Exam.pdf` and `BestBets.pptx`. On 2026-10-11, relevant Exam text and all twenty deck slides' text were reviewed read-only. The local Exam has 104 pages, including a separate individual Zeguu reconstruction appendix; that appendix is outside the BestBets story. Exact locations remain private. Source diagrams have not been visually inspected/selected by this enhancement; figure extraction/redrawing still needs that review and attribution. Do not assume Exam is identical to `Deliverables/BestBets.pdf`.

Proposed card copy: **Architecture research for a fictitious platform facing large data volumes and major sports-event traffic spikes.**

### Reviewed evidence

`Deliverables/BestBets.pdf` documents a spring 2025 team architecture project whose scenario is a betting-odds aggregation platform. Its structure covers architectural drivers, quality-attribute scenarios, module/component/deployment views, design decisions and evaluation. Reviewed passages consider event brokers, actor-based processing, uneven match popularity, ordering and failure bottlenecks. `Prototyping/` contains actor/remote-request experiment artifacts. Do not treat the report's target response measures as achieved benchmarks.

### Preferred Exam/deck reconciliation

- Exam p.16–18 defines separate performance scenarios. P.17's surge from 1,000 to 100,000 users in ten minutes, 95% page responses within two seconds and odds updates within three seconds are **design targets**, not achieved measurements. Preserve the scenario/units if quoted in a figure; do not combine response targets from different scenarios.
- Exam p.30–38/figures 20–23 explains the Trigger Order Broker, microkernel and bookmaker plugin actors. P.62's final evaluation explicitly narrows the earlier Global Odds Broker to a Trigger Order Broker that **does not notify the UI**. UI odds updates remain undecided. The final design uses a **load-balanced actor model**; do not publish the earlier global-broker/UI path as final architecture.
- Deck slides 14–18 describe actor-model versus load-balancer hypotheses and qualitative observations, followed by a proposed combination. Slide16 says retries were not simulated correctly, every simulated provider had the same logic, and local versus real network behavior limits validity. No numerical throughput/latency series was established by this text review.
- Exam p.60–62's aSQA 1–5 scores are team evaluations based on design/prototyping, not objective performance measurements. P.63 identifies unresolved DB topology and UI update design. Show architectural learning and limits instead of retroactively completing that fictitious system.
- Exam is later evidence for the selected combined design; the deck is evidence for how the team arrived there. Review actual diagrams before choosing public figures. Some deck fixture/infrastructure text identifies private background context; exclude such references from extracted/redrawn public media. The report identifies a three-person team including Jacob; it does not establish his individual contribution to each BestBets subsystem.

### Proposed sections

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `the-fictitious-scenario` | The fictitious scenario | Explain the intended product and high-volume, bursty workload | Existing concept illustration clearly labeled as a design concept |
| `quality-attributes` | Turning constraints into requirements | Show how performance, availability and changeability influence the design | One readable quality-attribute scenario with targets labeled as requirements |
| `architectural-views` | Architectural views | Explain responsibility boundaries, data movement and deployment alternatives | Selected module and component/deployment diagrams |
| `handling-event-bursts` | Handling sports-event bursts | Discuss concentrated demand, broker/actor choices and bottlenecks | Annotated event/data-flow diagram grounded in the report |
| `evaluation-and-tradeoffs` | Evaluating the decisions | Separate analysis, prototype experiments, measurements and unresolved risks | A reviewed experiment figure or decision comparison with conditions |

Use selected `Illustrations/BestBets.drawio`, report figures and prototype evidence after checking they agree. Label the project as an architecture/design study, not a production betting service. Confirm which work the owner contributed. Portfolio implementation does not build the proposed platform, execute benchmarks or implement betting/payment functions.

## 11. Geospatial research

Display name: **Geospatial research**. Suggested subtitle: **New York crime and amenities**. Source: [Grumlebob/ExamGDS](https://github.com/Grumlebob/ExamGDS).

Proposed card copy: **Exploring spatial relationships between New York City crime and nearby amenities.**

### Reviewed evidence

The local `exam.ipynb` contains data collection, neighborhood/population matching, amenity preparation, map visualization, correlation and spatial-analysis sections. Markdown notes describe difficulties matching neighborhood names. `New_York_Crime.pdf` is a 2025 team research report examining bars, restaurants and railway stations alongside crime records. It documents point-pattern analysis and spatial autocorrelation, including Ripley's K, Hopkins' statistic and LISA. This preparation read notebook structure and selected report text; it did not run the notebook or reproduce results.

### Proposed sections

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `the-research-question` | The research question | Introduce the crime/amenity relationship and study scope | Genuine study-area map as cover, with source attribution |
| `collecting-and-aligning-data` | Collecting and aligning the data | Explain crime, OSM amenities and neighborhood/population inputs; verify actual filters and periods | Data-source diagram and a neighborhood-matching example |
| `mapping-the-patterns` | Mapping the patterns | Explain point and choropleth views and their denominators | Legible selected maps with dates, legends and units |
| `spatial-analysis` | Spatial analysis | Explain the question answered by each selected clustering/autocorrelation method | One or two actual plots/maps with readable interpretation |
| `findings-and-limitations` | Findings and limitations | Describe reviewed observations alongside confounding, population and boundary limitations | A focused comparison figure plus sourced caveats |

Use static exports of genuine research figures; the portfolio does not need a GIS runtime or notebook execution. Preserve dataset/map attribution and review figure reuse. Verify methodological details and findings before publication. Describe association without claiming causation or presenting the analysis as current neighborhood-safety advice. Obtain the owner's contribution and choose a small number of informative figures rather than reproducing every notebook output.

## 12. Grumlebob

The owner names this project **Grumlebob** and previously described AHK/Python automation, analysis, bookkeeping and automated billing. A local background folder is now supplied and recorded privately; only its presence was checked. The owner's explanation is the primary editorial source, and inspecting or publishing that folder is not a prerequisite. No GitHub repository has been supplied; do not guess one from the account name.

On 2026-10-12 the owner approved these public facts: Grumlebob automates free online offers to generate money passively; approximately **DKK 500,000 profit in one year**; membership has reached capacity because of concern about being caught. Public prose attributes the profit and capacity explanation to the owner. The calendar year, exact member count, profit accounting and providers are unspecified; do not invent them or promise future returns. These statements supersede the earlier blanket exclusion only for this supplied scope.

Proposed card copy: **Automation of free online offers for passive income, supported by analysis, bookkeeping and billing tools.** Keep identifying accounts, providers, operational details, private data and background artifacts out of all public surfaces. Generic figures may explain the approved scope without showing restricted source material.

### Proposed sections

| Stable ID | Heading | Story and evidence to obtain | Media request |
| --- | --- | --- | --- |
| `automating-recurring-work` | Automating recurring work | Introduce the approved public scope of the tools and their purpose | Owner-approved generic cover or explanatory illustration |
| `automation` | Automation using AHK and Python | Explain an approved technical workflow from the owner's account without exposing restricted context | Newly prepared generic diagram; source excerpt only if specifically approved |
| `analysis` | Analysis | Explain approved methods and lessons without private datasets/results | Generic explanatory figure or fictional example, accurately labelled |
| `bookkeeping-and-billing` | Bookkeeping and automated billing | Show the real record-to-bill workflow and implemented controls | Synthetic records and an example bill with fictional details |
| `design-and-lessons` | Design and lessons | Explain verified boundaries, failure handling and maintenance decisions | Reviewed workflow diagram and owner reflection |
| `results-and-capacity` | Results and member capacity | Owner reports approximately DKK 500,000 profit in one year and membership at capacity because of concern about being caught | Plain attributed prose; no invented financial chart or member counts |

Keep one entry. Do not infer whether tools share code, integrations, ML/computer vision, autonomous sending, payment collection or outcomes beyond the expressly supplied owner statements. Use fictional billing/accounting examples only where they represent approved functionality. Restricted folder contents are not approved media. No automation, invoice or interaction is executed for this preparation.

## 13. JobHunt

Source supplied by the owner: [Grumlebob/JobHunt](https://github.com/Grumlebob/JobHunt). Authenticated repository metadata confirms it is private. Keep this URL in the editorial source register; omit a public repository button while visitors cannot access it. A portfolio case study can use reviewed, independently prepared figures without publishing the private repository or its application records.

### Story position and proposed public copy

Present a personal engineering project that reduces repetitive administration around a deliberate application. Keep the copy concrete, calm and personal. Describe actual tasks and boundaries without predicting how every recruiter will respond or making unsupported efficiency claims.

Proposed card copy: **Keeping job-application documents, details and tracking organized.**

Recommended headline: **Administrative help. Personal decisions.**

Proposed opening, to check against the selected version before publication:

> JobHunt organizes the practical work around an application: saving the posting, bringing together relevant documents and keeping the tracker up to date. It can assist preparation and drafting, while the applicant supplies personal motivation, reviews the application and performs final submission.

The owner's phrase **“Helps with the administrative work, keeps the personal work personal”** is the editorial guiding principle. Job selection, motivation and personal writing remain explicit human responsibilities in the requested direction. Explain assisted browser/model work through the administrative task it performs, without concealing assistance where it is relevant.

### Step-by-step application flow and graphic

Include the reviewed sequence immediately after the introduction. Figure title: **Application preparation and review**. Describe supported assistance and the owner's intended authorship boundary separately; omit unsupported account creation. The concept preview is a reference, not implementation evidence.

| Step | Visible label | Responsibility | Short explanation |
| --- | --- | --- | --- |
| 1 | Choose a role | Personal | The owner decides which opportunity is worth pursuing and supplies its posting link |
| 2 | Save the job details | Assisted | Capture the posting and verified facts, check for an existing record and preserve the source link |
| 3 | Prepare portal access | Assisted | Inspect required fields and use the appropriate saved login; required account creation remains subject to implementation review |
| 4 | Gather relevant documents | Assisted | Bring together the maintained CV and requested certificates/references from base documents |
| 5 | Write the personal application | Personal, intended boundary | The owner supplies personal motivation and reviews wording; current instructions can assist drafting |
| 6 | Update the tracker | Assisted | Keep the same application identity and verified details in Notion; describe tracking intent separately from submission |
| 7 | Prepare the form and attachments | Assisted | Fill supported factual fields and upload the selected, reviewed documents |
| 8 | Review and send | Personal | The owner checks the prepared form, documents and personal message, then performs final submission |

This is a simplified reading sequence, not a claim that every portal or integration follows a rigid execution order. Portal inspection starts early so document preparation uses actual requirements. Tracking can progress while another destination is blocked. Required user input pauses only the affected action. If a receipt is discussed afterward, show it as separate evidence following the owner's submission, not as a consequence of a tracker update.

Graphic direction: use Studio typography and whitespace. Desktop uses two rows of four numbered steps; mobile a vertical sequence. Every step includes its responsibility label, including possible drafting assistance. Keep all eight labels and explanations visible with an ordered-list text equivalent. Use neutral ink and one accent; no error-like red markers, robot imagery, employer logos or simulated outcomes. See VisualProduction for the final specification.

Implement with existing figure and prose blocks: a safe static diagram, a mobile variant only if needed, and a complete ordered-list explanation. No custom workflow block, widget schema, chart library or animation is required in v1. This supersedes the earlier special workflow-block suggestion and preserves the shared five-kind model.

A portable interactive preparation preview is retained as [JobHuntWorkflow.html](JobHuntWorkflow.html); open it in a browser to review the two lanes and selectable step explanations. It is a design reference, not application source, and contains only illustrative copy. Preserve an approved static reference and this step specification in the future design package before implementation. The preview represents the intended flow and does not claim to show a running JobHunt interface.

### Automation boundary for the story

Use a compact comparison within the story, with explicit Personal/Assisted labels and accurate drafting-assistance wording. Use neutral ink and the shared restrained accent; no red error-like markers or large colored panels. The comparison can be ordinary prose/list content without a new block schema.

| Task | Intended boundary | Evidence and wording constraint |
| --- | --- | --- |
| Finding and choosing a role worth pursuing | Personal/manual | The owner chooses a specific posting and initiates its workflow; do not describe random selection or bulk application |
| Signing in or creating a required application account | Administrative assistance | Existing browser-saved login/credential handling is documented. Account creation is owner-proposed scope; verify the implemented procedure before claiming it works universally. Describe credentials as handled through saved logins or the configured secret store, without an unverified security guarantee |
| Bringing together relevant documents | Administrative assistance | Use owner-maintained CV and base documents; select the actual files requested by the form. Document selection does not authorize inventing experience or rewriting personal facts |
| Saving posting and application details | Administrative assistance with review | Source-linked facts and structured records support consistency. Distinguish data models from AI assistance; information extraction still needs verification against the posting/form |
| Updating the application tracker | Administrative assistance | Notion synchronization is documented. Describe record consistency and readback; a tracker status is separate from employer receipt |
| Writing motivation and the personal application | Personal authorship/review; assistance possible | Current guides support assisted drafting; acknowledge it and distinguish the owner's intention from an enforced restriction |
| Filling repeated factual fields and uploading selected documents | Administrative assistance | Browser assistance prepares verified answers and relevant attachments for the chosen role. Review actual accepted files and form constraints; do not promise every portal is supported |
| Reviewing and sending the application | Personal/manual | Current project instructions explicitly reserve final employer Send and confirmation for the user |

### Reviewed evidence and alignment task

Read-only review covered the private repository's visibility and local general documentation, including `README.md`, `AGENTS.md`, and relevant passages in `WORKFLOW.md`, `DOCUMENTS.md` and `EMPLOYER.md`. No applicant facts, credentials, base documents, application packages or tracker contents were read for this story. No JobHunt command, browser flow, upload or external write was executed.

The documented workflow includes deliberate posting intake, duplicate checks, organized document packages, verified facts, Notion tracking, employer-form preparation and a final handoff. Python helpers and browser assistance have different responsibilities; do not portray a single autonomous service as doing everything. The project instructions require the user to submit and distinguish tracking intent, a prepared form and actual receipt evidence.

Resolved decision D10: acknowledge actual drafting assistance and personal motivation/review/final submission. The owner's stricter personal-writing direction is an intention, not enforced current behavior. This task does not modify JobHunt. Omit entirely-manual/never-AI-written, automatic account-creation and unverified credential guarantees; no source change is needed merely to make portfolio copy accurate.

### Proposed sections and media

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `why-i-built-jobhunt` | Why I built JobHunt | Explain the repeated administrative steps and the owner's desired personal boundary | Quiet document/tracker illustration or genuine synthetic example |
| `the-application-flow` | From a chosen role to a reviewed application | Walk through the eight reviewed steps and the handoff between personal work and administrative help | Numbered responsibility timeline; all steps visible in desktop/mobile layouts |
| `personal-and-administrative-work` | Personal and administrative work | Show the reviewed boundary comparison without defensive or impersonal copy | Compact text-labeled comparison within the prose |
| `keeping-information-organized` | Keeping information organized | Explain saving source facts, consistent records, document selection and tracker updates | A fictional posting and fictional Notion tracker example |
| `preparing-an-application` | Preparing an application | Explain selected-role login/form/upload help and final user review | A synthetic local form/handoff figure, clearly labeled as an example |
| `reliability-and-lessons` | Reliability and lessons | Explain duplicate handling, verified state and boundaries from source evidence | Small workflow diagram and owner reflection |

Prepare all public media using fictional employers, applicant details, documents and tracker records. Do not publish real application letters, personal CVs, references, employer correspondence, active application status, private workspace links, credentials or receipts. Choose simple workflow and record examples that communicate the engineering without exposing another application's data. Keep automation choices tied to the owner's real behavior. Do not claim hiring success, recruiter approval, time saved or autonomous mass submission without evidence. The portfolio contains a story, not a live application bot or access to the private tracker.

## 14. Template

Display name **Template**, slug `template`, packet **P6.13**. Public source: [BlazorAutoAppTemplate](https://github.com/Grumlebob/BlazorAutoAppTemplate). This addition replaces the earlier catalog exclusion and does not restore removed frontend/deployment targets inside Portfolio.

Proposed card copy: **A reusable application template with two frontend choices, three deployment choices and integrated quality tooling.**

| Stable ID | Heading | Story and evidence | Media request |
| --- | --- | --- | --- |
| `a-reusable-foundation` | A reusable foundation | Purpose, shared C# host and configurable product foundation | Sourced responsibility diagram |
| `frontend-choices` | Two frontend choices | Blazor and React profiles; pin actual capabilities at the reviewed revision | Two concise choices with shared host boundary |
| `deployment-choices` | Three deployment choices | Cloud, LocalCluster and LocalSingleNode; distinguish configuration from live delivery | Three-choice diagram without host identifiers |
| `quality-and-security` | Quality and security tooling | Lighthouse, SonarQube, Qlty, Trivy, ZAP, sitespeed.io and scc; describe each role from source evidence | Brief tool-to-purpose list; actual results only with dated run evidence |
| `tradeoffs-and-lessons` | Tradeoffs and lessons | Profile complexity, reusable checks and maintenance decisions supported by source | Reviewed explanatory diagram or prose |

Reference canonical technology IDs for the actual stack and all seven requested tools. Do not present deployment choice labels as invented technologies. Do not infer quality scores, scan clearance, certification or a deployed target from configured tools alone.

## 15. Preparation task matrix

| Project | Source/fact review | Draft sections | Genuine media | Role/context confirmed | Public links verified | Publish decision |
| --- | --- | --- | --- | --- | --- | --- |
| ImprovedDb | Prior review; recheck at content release | Outlined | Existing captures; select/update | Personal motivation supplied; role details pending | Live site known; recheck | Pending editorial review |
| KinoJoin | Source reviewed; runtime unverified | Outlined | Pending capture | Pending | Owner-supplied public repository; live app unknown | Pending editorial review |
| TraceBack | Docs reviewed; runtime unverified | Outlined | Pending synthetic capture | Research context documented; personal role pending | Pending | Pending editorial review |
| GeckoBot | Private GeckoBot selected/tree/AST reviewed; runtime unverified | Brief | Fictional captures pending | Historical use/status pending | Active source/backup private; omit public buttons | Draft pending source-aligned copy/permitted figures |
| Ship Inspections | Source/docs reviewed; runtime unverified | Outlined | Pending synthetic capture | Pending | Owner-supplied public repository; live app unknown | Pending editorial review |
| Unlost | Recovered Java source plus confirmed report/artifacts; runtime unverified | Outlined | Genuine figures available; select/review | Team context; individual contribution pending | Owner-supplied public repository | Pending source/report and editorial review |
| MiniTwit | Repository/report/docs reviewed; runtime unverified | Outlined | Report/source artifacts identified; capture/select | Team context documented; individual contribution pending | Owner-supplied public repository; live app unverified | Pending editorial review |
| BestBets | Preferred Exam/deck text reviewed and reconciled | Outlined | Preferred deck/figures pending review | Team context; individual role pending | Public repository supplied | Pending visual/rights/editorial review |
| Geospatial research | Notebook structure/report reviewed; results not reproduced | Outlined | Report/notebook figures identified; select/export | Team context documented; individual contribution pending | Owner-supplied public repository | Pending editorial review |
| Grumlebob | Free offers/passive income/profit/capacity supplied by owner | Public facts scoped; draft copy | Generic examples pending | Owner-reported outcomes; no member count/year inferred | None approved | Draft pending figures/editorial review |
| JobHunt | Private repository/general docs reviewed; runtime unverified | Eight-step flow and copy boundary resolved | Workflow preview prepared; fictional examples pending | Personal intent supplied; contribution/status wording pending | Private source supplied; omit inaccessible public action | Draft pending figures/editorial review |
| Template | Owner tooling/choices supplied; pin source evidence | Outlined | Choice/tool diagrams pending | Contribution/context to be sourced | Public template repository | Pending source/figure/editorial review |

For each row, use its P6 packet and ImplementationCheckpoints' repeated story sequence. Unknown individual-role/count/date claims can be omitted with neutral accurate context; permissions and approved public explanation remain prerequisites where needed. Readiness must not be inferred from the presence of a folder, a cover image or a seed row. Recheck facts and links at execution time because implementation is deliberately scheduled for later.
