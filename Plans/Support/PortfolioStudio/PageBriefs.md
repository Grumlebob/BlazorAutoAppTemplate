# Portfolio page and illustration briefs

Parent: [master plan](../../PortfolioStudioImplementation.md). Technical packets: [DeliveryPhases.md](DeliveryPhases.md). Facts, exact section IDs and source limitations: [ProjectInventory.md](ProjectInventory.md).

This document supplies editorial suggestions and concrete production tasks. Suggested headlines are draft copy. Publish factual claims only after checking the source register. Preserve the selected Studio layout: one home grid, one continuous page per project, desktop section rail, mobile section menu and both themes. Do not introduce separate About/Writing pages or chapter routes.

## 1. Home — `/`

**Heading:** Selected work.

**Suggested supporting copy:** A collection of software, research and practical tools I've worked on. Each project tells the story behind the idea, the decisions and what I learned.

Review this copy with the owner's actual contributions before publishing. Keep it to two or three quiet lines. The grid follows directly; no large biography panel, technology logo wall or animated hero is needed.

- Header: `Jacob Grum` linked home; accessible theme button on the right.
- Cards: 16:10 starting cover ratio, project name, one clear sentence and optionally one or two meaningful descriptors. Adjust crop per asset; preserve technical figure legibility inside stories.
- Order: ImprovedDb, GeckoBot, TraceBack, KinoJoin, Ship Inspections, Unlost, MiniTwit, BestBets, Geospatial research, Grumlebob, JobHunt. Hide drafts while preserving the relative order of published entries.
- Layout: two columns on comfortable desktop widths, one on mobile. Odd final entries retain the normal card width. Support different catalog sizes without filler cards or pagination.
- Footer: a small verified GitHub link and any owner-supplied contact action. Do not infer an email address, current job title or availability for work.
- First-load media: load only current card variants; do not fetch every story's screenshots or prose. Preserve intrinsic image dimensions and a quiet background before load.

Initial launch can contain four fully reviewed stories. A larger backlog stays in authoring/progress records, not as public empty destinations.

## 2. Shared project-page treatment

Show project name as H1, a concise editorial standfirst, a readable cover and verified actions. Optional context/role/status text belongs near the introduction only when established. Use clear headings rather than a row of technology badges.

Each main section should answer a question, show evidence and explain a decision. A useful working target is 80–180 words per ordinary section, with longer technical sections where warranted. Do not pad a project to a common word count or section count. Alternate prose and useful figures naturally; no image after every paragraph by rule.

Every figure needs a purpose, provenance, caption, alt decision and readable mobile treatment. Use one cover and roughly three to six useful supporting figures for a substantial story. A shorter authentic story needs fewer. Technical graphs and screenshots retain their content; reserve cropping for decorative covers.

Label media accurately:

| Kind | Use | Caption expectation |
| --- | --- | --- |
| Actual interface capture | Demonstrate a verified UI | Capture date/revision and what the screen shows |
| Synthetic example capture | Demonstrate a real feature safely | State that names/data are fictional examples |
| Redrawn architecture/workflow | Explain verified source behavior | State it is a explanatory diagram and cite source revision |
| Illustrative cover | Set tone while evidence is pending | Do not present it as the actual product interface |
| Historical report/notebook figure | Explain a dated project/research result | Date, dataset/source attribution and reuse basis |

Use SVG or static diagrams for architecture/workflows and genuine exports for research plots. Generate bitmap illustration only when it helps the story; never fabricate a screenshot, measured graph or product result. Avoid external hotlinks, animated backgrounds and decorative mock browser frames that make technical evidence smaller.

Suggested related links are below. Resolve them against published slugs; omit any unavailable destination.

## 3. ImprovedDb — `/projects/improveddb`

**Card:** Movie and series discovery, familiar faces, and the data behind the ratings.

**Standfirst suggestion:** A personal movie and series project built around a familiar question: where have we seen that actor before?

Use the exact owner motivation from the master plan. Preserve its six section IDs/headings. Interesting detail headings may appear below those H2s:

- Why I built this: begin with the living-room question, then identify the product goal.
- Familiar faces: **Recognising an actor through their work.** Explain popular, high-rated and recent credits using one readable cast/title capture.
- Ratings & scoring: **Making different scores comparable.** Show one sourced normalization/missing-value example. Keep the deeper rating note here with a stable anchor.
- Data collection: **From source data to a browsable catalog.** Redraw only the actual source/import/publication path.
- Statistics: **Questions the catalog can answer.** Select one or two genuine graphs and explain axes, period and the question each answers.
- Machine learning: **Exploring historical award signals.** Show genuine interface/model evidence and explain its retrospective scope and limitations.

**Cover:** genuine title/browse view with a recognisable interface composition. **Supporting figures:** cast credits, score comparison, import/publication diagram, real statistics graph, historical-model interface. Keep 781/8/model/vote-count claims out of evergreen copy until reverified.

**Reader takeaway:** a personal question led to useful browsing and a carefully explained data pipeline. **Links:** verified live ImprovedDb; public source only if confirmed. **Related:** KinoJoin, TraceBack.

Publication blockers: current source/revision, conflicting award cutoff copy, dated rating/model counts, chosen media and actual contribution/context wording.

## 4. GeckoBot — `/projects/geckobot`

**Card:** Automating repetitive email work.

**Standfirst suggestion:** A tool for recurring email tasks, with the actual workflow explained through one concrete example.

Private `Grumlebob/GeckoBot`, renamed from mail, is the selected sole active source: it explicitly names GeckoBot and separates Outlook booking flow, parser and Tkinter UI modules. The owner requested deletion of MailDemo; its distinct examples and complete Git history are retained only in a private backup. Review GeckoBot's requirements and actual historical use before publishing; source structure has been inspected, but runtime behavior has not.

- The repetitive work: establish the real task and why it was repetitive.
- The workflow: describe trigger, inputs, transformations and output from source evidence.
- Control and review: show only controls/failure handling that actually exist.
- Implementation: explain one verified integration or architecture decision.
- Outcomes and lessons: use demonstrated outcomes or owner reflection; no invented time savings.

**Cover:** a fictional booking/email example using the actual UI if safely captured, or a clearly illustrative workflow graphic. **Supporting figures:** new/change/cancel meeting flow, fictional booking email and source-backed parser/Outlook boundary diagram. Do not inspect real employee, customer, inbox or calendar data for captures. Keep private source links out of public actions.

**Reader takeaway:** automation of a specific recurring task. **Related:** Grumlebob, JobHunt.

Publication blockers: intended source version, requirements/actual use, sending/review boundary, contribution/status and fictional media. Do not describe AI, bulk outreach or autonomous sending without evidence. Capturing media must never send real mail or modify a real calendar.

## 5. TraceBack — `/projects/traceback`

**Card:** Preserve simulation inputs, scripts, outputs and run context so experiments can be inspected and recreated later.

**Standfirst suggestion:** Making the context around a simulation run explicit, so a saved experiment is easier to understand later.

Keep the inventory's six section IDs. Suggested narrative emphasis:

- Keeping the context of an experiment: **The files alone do not tell the whole story.** Establish the research-prototype context without inventing qualifications/employment.
- Making the pipeline explicit: explain Project, Pipeline, SoloExperiment and input/box/output blocks through one synthetic example.
- Connecting data and code: compare local/Git/remote references without showing real institution paths.
- Saving a run's evidence: show a short manifest and metadata/payload division.
- Revisiting a saved run: follow the same example into history/recreated selections.
- Reproducibility boundaries: **A reference and a snapshot preserve different things.** Explain mutable sources and external environment responsibilities.

**Cover:** synthetic project/pipeline overview from the actual prototype. **Supporting figures:** pipeline diagram, safe data locations, sanitized manifest, history/recreate capture, reference-versus-snapshot comparison.

**Reader takeaway:** traceability and saved context have explicit limits. **Related:** ImprovedDb, Geospatial research. Tutorial/source buttons require a confirmed accessible publication URL.

Publication blockers: fresh synthetic capture, reviewed source revision, owner role and public link choice. Never claim full pipeline execution or guaranteed identical scientific results.

## 6. KinoJoin — `/projects/kinojoin`

**Card:** Plan a cinema outing, share possible showtimes, and collect the group's preferences.

**Standfirst suggestion:** From a list of showtimes to a shared cinema plan.

Use one fictional event across the six inventory sections. This creates a coherent story instead of disconnected screenshots:

- Choosing a cinema trip together: explain the documented coordination problem; obtain personal motivation separately.
- Finding the right showtimes: **Narrowing the choices.** Show cinema/film/genre/date filters.
- Creating and sharing an event: show event details, selected options and deadline.
- Collecting preferences: **Seeing which options work for the group.** Explain selections/results without assuming a voting algorithm.
- From a choice to a plan: distinguish host confirmation, external booking link and calendar handoff.
- Data model and design decisions: show imports and event/participant/showtime relationships.

**Cover:** genuine event-creation UI with fictional data. **Supporting figures:** filters, share/event screen, preference/results screen, calendar panel, small domain/data-flow diagram.

**Reader takeaway:** the design follows coordination through to a concrete plan. **Links:** supplied public source; live-site action only after verification. **Related:** ImprovedDb, JobHunt.

Publication blockers: owner role, actual captures, reviewed revision and calendar compatibility claims. No ticket purchase/payment or automatic consensus claim.

## 7. Ship Inspections — `/projects/ship-inspections`

**Card:** Record vessel-part observations and attach inspection images through a resumable upload workflow.

**Standfirst suggestion:** An inspection workflow organized around vessel parts and the images attached to them.

Use a fictional vessel and clearly permitted photographs. Keep the inventory's six sections:

- An inspection organized by vessel part: introduce the sample/prototype scope.
- Navigating the vessel: **Keeping each observation in context.** Show views, segments and completion state.
- Recording observations: connect notes/condition fields to the selected part.
- Reliable image uploads: **Resuming from the known offset.** Explain actual TUS chunks/HEAD/PATCH/pause behavior.
- From upload to usable images: show metadata, validation and thumbnail/original flow.
- Tradeoffs and next steps: state local sample status and unresolved limits/AI work honestly.

**Cover:** genuine segmented-vessel overview. **Supporting figures:** selected-part form, upload progress/pause/resume states, sourced TUS flow and thumbnail/gallery view.

**Reader takeaway:** interface context and upload mechanics work together. **Links:** supplied public source. **Related:** TraceBack, MiniTwit.

Publication blockers: actual runtime/media evidence, source/document upload-limit agreement, photo permission and role. A visible AI-score field proves no inference pipeline; a session resume proves no browser-reload recovery.

## 8. Unlost — `/projects/unlost`

**Card:** A Java map application exploring address search, route planning and A* pathfinding.

**Standfirst suggestion:** Building a map of Denmark, then finding a useful route through it.

Use existing genuine report artifacts. Preserve inventory IDs; do not make recovering the Java source a prerequisite.

- Building a map application: establish the 2022 team-project context and verified personal role.
- From map data to the screen: show genuine map UI/OSM structure.
- Finding addresses and places: explain actual search and POI behavior through available figures.
- Exploring routes with Dijkstra and A*: **Exploring less of the graph.** Show genuine path/search diagrams and car/bike/walk options where supported.
- Spatial data and performance: explain Kd-tree operations and documented large-map tradeoffs; no invented benchmark.
- Lessons from the project: explain documented teamwork/code/heuristic lessons; do not claim optimality the report does not support.

**Cover:** genuine Unlost map view. **Supporting figures:** menu/search, route plan, A* explored nodes/path, Kd-tree or OSM graph figure. Redraw tiny labels only with a source note; do not invent a new measured result.

**Reader takeaway:** data structures and algorithms become a usable map interface. **Related:** Geospatial research, BestBets.

Publication blockers: media selection/reuse, attribution and individual role. Exclude the other team's archive entirely. A source-code button is optional when no public source exists.

## 9. MiniTwit — `/projects/minitwit`

**Card:** A microblogging application exploring software evolution, deployment and observability.

**Standfirst suggestion:** A small social application used to learn how a system changes, ships and is observed.

Keep five inventory sections. Explain product behavior briefly, then focus on the dated engineering work:

- A small social application: real timeline and spring 2025 team context.
- Evolving the system: **From Flask to a .NET system.** Redraw actual client/API/storage boundaries.
- Building and delivering changes: connect source checks, image build and deployment to one verified workflow.
- Seeing what the system is doing: choose one useful logged/metric question and explain a genuine operational figure.
- Scaling decisions and lessons: separate design choices, observed failures and any measured result.

**Cover:** genuine timeline with fictional accounts if recaptured. **Supporting figures:** architecture, concise evolution timeline, sanitized delivery diagram, dated Seq/metrics figure.

**Reader takeaway:** delivery and observability are part of the software design. **Links:** supplied public source; old deployment addresses are not live-site evidence. **Related:** BestBets, Ship Inspections.

Publication blockers: personal contribution, figure selection/revision, dates and workflow/report agreement. No unsupported throughput/uptime claims.

## 10. BestBets — `/projects/bestbets`

**Card:** Architecture research for a fictitious platform facing large data volumes and major sports-event traffic spikes.

**Standfirst suggestion:** Designing for uneven demand, with requirements and tradeoffs made visible.

Use the five inventory sections:

Prioritize the owner's school-material `Exam.pdf` and `BestBets.pptx`; their private locations are in the source overview. These newly supplied files are located but unreviewed. Reconcile them with the repository's report/prototypes before selecting claims or figures.

- The fictitious scenario: state that this is a design study of odds aggregation.
- Turning constraints into requirements: **When demand concentrates around one event.** Present one clear quality-attribute scenario.
- Architectural views: show a readable responsibility/module view before a detailed deployment view.
- Handling sports-event bursts: explain the sourced broker/actor/data-flow decisions and bottlenecks.
- Evaluating the decisions: **Targets, experiments and open questions.** Separate report requirements from actual prototype evidence.

**Cover:** restrained concept architecture diagram labelled design study. **Supporting figures:** one quality-attribute scenario, module/component view, burst/event flow and sourced decision/experiment comparison.

**Reader takeaway:** architectural reasoning connects a workload to concrete choices and limits. **Links:** supplied Architecture repository. **Related:** MiniTwit, TraceBack.

Publication blockers: preferred PDF/deck review, source-version agreement, selected figures, role and results/targets distinction. No claim of production betting, payments or demonstrated large-scale traffic.

## 11. Geospatial research — `/projects/geospatial-research`

**Card:** Exploring spatial relationships between New York City crime and nearby amenities.

**Standfirst suggestion:** Looking at spatial patterns in New York City, and the limits of what those patterns explain.

Optional subtitle: **New York crime and amenities**. Preserve the five inventory sections:

- The research question: explain place, period and study question.
- Collecting and aligning the data: **Making different geographic records comparable.** Show crime/OSM/neighborhood inputs and documented matching issues.
- Mapping the patterns: give maps dates, legends, units and denominators.
- Spatial analysis: explain what each selected method asks before presenting the genuine result.
- Findings and limitations: discuss association, population/boundaries/confounding and data limitations.

**Cover:** genuine study-area map. **Supporting figures:** data-source/matching diagram, one informative choropleth, point-pattern plot and selected actual spatial-analysis figure. Use static exports and adjacent text interpretation.

**Reader takeaway:** the analysis is only as interpretable as its data and assumptions. **Links:** supplied ExamGDS source. **Related:** Unlost, TraceBack.

Publication blockers: reviewed source/result period, dataset/map attribution, contribution and selected figures. Do not run notebooks just to decorate the page; reproduction is a separate claim requiring evidence. No causal or current neighborhood-safety claims.

## 12. Grumlebob — `/projects/grumlebob`

**Card suggestion:** Personal tools for automation, analysis, bookkeeping and billing.

**Standfirst suggestion:** A collection of tools built around recurring tasks and useful questions.

The owner's explanation is the primary source. A restricted local folder is recorded privately; its contents are not approved publication material and need not be inspected. Obtain the approved public description before publishing. Keep one entry with distinct sections unless the owner chooses otherwise:

- Automating recurring work: explain whether these are one system or separate tools.
- Automation using AHK and Python: explain approved technical decisions and controls through a generic diagram.
- Analysis: explain approved methods/lessons using an accurately labelled generic or fictional example.
- Bookkeeping and automated billing: follow fictional records to a reviewed example bill; describe only implemented controls.
- Design and lessons: explain verified failure/maintenance boundaries and owner reflections.

**Cover:** an approved generic workflow illustration. **Supporting figures:** a newly prepared technical diagram and fictional bookkeeping/billing example where supported by the approved explanation. Source excerpts or actual artifacts require specific publication approval.

**Reader takeaway:** practical scripts solve specific recurring tasks. **Related:** GeckoBot, JobHunt.

Publication blockers: approved public explanation, role/status and permitted figures. Exclude private domain context, sensitive workflows/data/results and identifying source artifacts from prose, images, filenames, alt text, captions, social previews and links. Do not invent another real use case to replace excluded context. Do not infer a repository, integrations, payment collection, ML or outcomes. Media preparation must not execute real automation or send invoices.

## 13. JobHunt — `/projects/jobhunt`

**Card:** Keeping job-application documents, details and tracking organized.

**Standfirst suggestion:** Administrative help. Personal applications.

Use the owner's principle: **Helps with the administrative work, keeps the personal work personal.** The inventory records a conflict between intended manual writing and current assisted drafting instructions. Resolve that conflict before publishing the manual-writing opening as implemented fact.

Keep six sections: why, eight-step flow, personal/administrative boundary, organized information, application preparation and reliability/lessons. The flow figure is the distinctive centerpiece:

1. Choose a role — personal.
2. Save the job details — assisted.
3. Prepare portal access — assisted; verify actual account-creation scope.
4. Gather relevant documents — assisted.
5. Write the personal application — personal in the owner's intended direction; factual alignment required.
6. Update the tracker — assisted.
7. Prepare the form and attachments — assisted.
8. Review and send — personal.

Show all eight steps in a readable horizontal/wrapped desktop composition and vertical mobile sequence. Use explicit `Personal`/`Assisted` text labels; color is secondary. The main explanation remains visible. Optional details can expand, but no carousel hides steps. Include a text equivalent and meaningful focus order if controls are used.

**Cover:** quiet document/tracker illustration or synthetic actual example. **Supporting figures:** eight-step responsibility timeline, fictional posting/tracker, fictional local form/attachment handoff, source-backed duplicate/state flow. The existing [workflow preview](JobHuntWorkflow.html) is a concept reference; adapt it to the validated story and shared components.

**Reader takeaway:** reliable administration supports a deliberate application and visible personal decisions. **Related:** Grumlebob, GeckoBot. Omit a source button for the inaccessible private repository.

Publication blockers: writing/account-creation alignment, fictional examples, reviewed role/status. Never read/publish private applicant documents, credentials or employer submissions merely to populate this case study. A tracker state is not proof of employer receipt.

## 14. Per-story publication checklist

- [ ] Reviewed source revision/date and factual notes are recorded privately/editorially.
- [ ] Headline/summary explains the actual project without invented impact or biography.
- [ ] Owner role, collaborators, prototype/historical status and any dates are accurate.
- [ ] All main sections are complete and match stable metadata IDs.
- [ ] Cover/supporting figures are licensed/permitted, readable, captioned and correctly identified as actual/example/illustrative.
- [ ] Private names, paths, records, credentials and identifying media metadata are excluded.
- [ ] Outbound links are accessible and appropriate; private source buttons are omitted.
- [ ] Internal/related links target published content only.
- [ ] Light/dark, mobile/desktop, keyboard, text zoom and image enlargement are reviewed.
- [ ] Public export/API/HTML/social metadata/sitemap include the story and exclude drafts.
- [ ] PR/merge/main CI evidence and publication decision are recorded in Progress.

Do not check a box from the existence of this brief. The checklist describes future execution evidence.
