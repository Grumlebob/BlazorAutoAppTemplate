# Portfolio Studio delivery master plan

Status: planning prepared; Studio design approved; Portfolio implementation not started.
Last reviewed: 2026-10-11.

This is a multi-day delivery plan for an independent **Portfolio** product. Different agents should complete small, recorded packets without reconstructing earlier decisions. The destination is [Grumlebob/Portfolio](https://github.com/Grumlebob/Portfolio), seeded from [Grumlebob/BlazorAutoAppTemplate](https://github.com/Grumlebob/BlazorAutoAppTemplate). The intended public product URL is **https://portfolio.jacobgrum.com/**, delivered through **LocalSingleNode and its Cloudflare Tunnel extension**. Configure this URL through product/deployment settings; do not embed it in components or scripts.

| Read this document | Purpose |
| --- | --- |
| This master plan | Product scope, approved Studio design, content/API architecture and final acceptance |
| [DeliveryPhases.md](Support/PortfolioStudio/DeliveryPhases.md) | Ordered phases, small executable packets, dependency gates, checks and removal inventories |
| [Progress.md](Support/PortfolioStudio/Progress.md) | Current task, packet ledger, blockers, decision records and resume prompt |
| [PageBriefs.md](Support/PortfolioStudio/PageBriefs.md) | Home copy, eleven project story treatments, illustration briefs and publication checklist |
| [ProjectInventory.md](Support/PortfolioStudio/ProjectInventory.md) | Existing source evidence, detailed section IDs, provenance and factual limitations |
| [NodeHandoff.md](Support/PortfolioStudio/NodeHandoff.md) | Controller/node responsibilities, first bootstrap, SSH pairing, public launch and simple operator handoffs |

Machine-specific intent lives in ignored `Plans.local/Portfolio/OperatorIntent.md`. It records the supplied local checkout locations, fresh Linux Mint node, reserved address and node-name clarification. Copy it privately to the future Portfolio checkout. Tracked plans remain portable. The main PC is a development/controller machine; it must never be bootstrapped as the deployment node.

## 1. Purpose and relationship to the React delivery

Build Jacob Grum's public portfolio from the approved Studio mockup. Home presents projects. Each project opens a continuous, illustrated story with navigation between its sections.

This is a downstream product plan. [ReactFrontendProfile.md](ReactFrontendProfile.md) and [ReactFrontendDeliveryGoal.md](ReactFrontendDeliveryGoal.md) deliver the reusable public React foundation and its reference deployment. Another agent owns that delivery. Do not add portfolio requirements to its current packets, modify its worktrees, or treat its public demo as the portfolio deployment.

The present request expands the plan; it does not execute the product migration, bootstrap a node or dispatch a deployment. A future instruction to execute this plan authorizes its ordinary repository work. Before live bootstrap or deployment, record the operator's applicable instruction and the exact target/release in the progress ledger. Do not borrow the other React agent's deployment authorization.

Planning checkpoint: upstream `main` was `99c319fc38b3b443cd7115093a5c614c1f9de7e3`, with successful [main CI run 38146167014](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38146167014). The Portfolio repository existed with no default branch/content, and the requested local Portfolio checkout did not exist. These facts were inspected on 2026-10-11; recheck them at execution. The React goal still records unfinished node/public acceptance. Expect it to finish soon, but never treat that expectation as evidence. Planning, source briefs and private operator preparation can proceed immediately; select the actual baseline through P0.

### Recommended decisions

| Area | Decision | Reason |
| --- | --- | --- |
| UI | React + TypeScript + Vite, using the delivered template's pinned versions | Reuse its build, development, error handling and deployment integration |
| Routes | React Router Framework Mode | Route modules, layouts, navigation, route types and a path to static prerendering |
| Rendering | Begin in SPA mode; prerender public pages before production launch | Validate the design early, then deliver readable HTML and metadata on direct requests |
| API state | TanStack Query and the template's shared QueryClient | API caching, cancellation, retries and request states without another server-state store |
| Styling | Tailwind CSS with a small local component set and shared theme tokens | Preserve Studio consistently without imposing a large component library |
| Backend | ASP.NET Core, serving frontend assets and same-origin APIs | Retain validation, public content contracts and hosting in C# |
| Contracts | ASP.NET OpenAPI + openapi-typescript + openapi-fetch | Reuse generated types and transport rather than maintaining duplicate DTOs |
| Content authoring | Markdown prose, typed JSON metadata and local media in Git | Simple reviewable project stories; no admin interface needed initially |
| Publishing | One validated content bundle, built and released with the app | API responses and prerendered pages describe the same release |
| Product identity | `Portfolio`, `Portfolio.sln`, `Portfolio.React`, `Portfolio.Core`, `Portfolio.Test`; lowercase deployment slug `portfolio` | Remove operational reliance on the template name |
| Deployment | LocalSingleNode only, with retained `Deployment/Common` support | One native Linux node and app-owned Cloudflare publication |
| Sample removal | Replace Books and remove Blazor UI/profile support, accounts and unused sample-domain code | Deliver a public portfolio with one frontend and one product domain |
| Backing services | Retain inherited PostgreSQL/Redis initially; decide removal through an explicit later packet | Avoid coupling frontend removal to a speculative operations rewrite |

Use the template's existing Router/Vite integration; do not create a second Vite application alongside it. Tailwind's official [Vite integration](https://tailwindcss.com/docs/installation/using-vite) fits this setup. Inherit compatible versions from the delivered lockfile and review upgrades separately.

ASP.NET Core remains the runtime authority. Git is the authoring source for editorial content. A small C# content validation/export path produces the published bundle used by both the backend and the frontend build. This avoids an independent TypeScript copy of the projects. Adding a portfolio content database or CMS is unnecessary for v1.

## 2. Dependency gate and repository ownership

Before implementation:

1. Read the master plan, companions, applicable repository rules, `docs/Test.md`, `docs/FrontendProfiles.md`, fork guide and LocalSingleNode runbooks. Inspect Git status, task ownership, worktrees and live PR/check evidence.
2. Recheck the other agent's React delivery. Select a merged commit with green main CI containing the required React foundation, typed contracts, development commands, C# production hosting and reusable deployment tooling. Record what remains unfinished. Missing required infrastructure blocks seeding; unrelated demo acceptance may be waived only by recording why Portfolio does not depend on it. Do not copy unmerged work or alter the other agent's plan/worktrees.
3. Reinspect the supplied Portfolio repository before seeding. If it is still empty, disable inherited Actions during initial import and use a plain clone/import of the verified template commit with retained history. Apply the small Portfolio app/image/React seed configuration and inherited local gate described in P0.2 before the initial push or native bootstrap. Preserve pristine upstream provenance separately; point `origin` at Portfolio and `upstream` at the template. If it now contains work, preserve it and reconcile through a branch/PR. Never force-push or replace it.
4. Create the sibling Portfolio checkout from the private intent note. Record independent app/image/release identity and `React` selection. Use the inherited bootstrap path for runner capacity if no runner can execute PR checks; do not get stuck waiting for CI on an unbootstrapped fresh node.
5. Rename projects and namespaces deliberately, remove Blazor and unused targets through separate verified packets, then replace the Books domain. All product changes occur in Portfolio. Keep the template multi-profile/multi-target and its existing demo untouched.
6. Make the Portfolio copy of this plan and its progress ledger authoritative after import. Link the template planning record to the downstream execution record once the first downstream PR is merged. Consume future upstream fixes selectively through review; do not blindly merge template changes over Portfolio removals.

Planning and content preparation can proceed before the upstream gate. Product implementation begins once its dependencies are merged. Upstream fixes discovered later belong in separate template PRs and must be consumed through a verified merge.

Blazor, Books, Cloud and LocalCluster removal are required phases of this plan. Keep PostgreSQL/Redis and their backup/doctor requirements until P7 explicitly retains or removes each service. Retain `Deployment/Common`, Cloudflare support, release provenance, locks, Caddy and LocalSingleNode acceptance. Some currently shared CI/audit/smoke helpers live under LocalCluster; move and retarget them before deleting that folder. Removing a target is complete only when runtime, CI, tests, scripts, runbooks and `AGENTS.md` agree.

## 3. Approved Studio design contract

This section supersedes earlier mockup directions and the initial investigation's larger page inventory.

### Home and header

- `/` is the Work project grid. There is no separate landing page before it.
- The header has **Jacob Grum** on the left, linking to `/`.
- The right side has a light/dark mode button. It does not display a Work navigation label.
- Writing and About are absent as separate pages and navigation destinations.
- Retain the approved home heading, **Selected work.**, and concise supporting copy. Final supporting copy is editorial content, not hard-coded component text.
- Show image-led project cards in two columns at comfortable desktop widths and one column on narrow screens. Preserve the quiet, open layout, restrained typography and whitespace.
- The planned catalog includes eleven actual projects: ImprovedDb, GeckoBot, TraceBack, KinoJoin, Ship Inspections, Unlost, MiniTwit, BestBets, Geospatial research, Grumlebob and JobHunt. Use the companion inventory's proposed order and a project manifest, rather than conditional markup for each project. Public visibility depends on reviewed content readiness. The application template supplies the technical foundation and is excluded from the showcased catalog, as requested by the owner.
- Cards use real links with meaningful titles. Keep tags and metadata sparse. No dense dashboard panels, prominent technology badge walls or new category controls are required.
- The eleven-project backlog occupies six desktop rows when all stories are published, with one card on the final row. Smaller launch sets can also end with a single card. Do not add a fictitious card or stretch the last project to fill space. The same layout must support one, four, seven, ten, eleven and twelve entries without changing its markup or adding pagination/filtering for this small catalog.

### Project reading layout

- Each project has a title, short introduction, suitable cover image and verified external links when available.
- The project story is one continuous page. Every main section appears in document order and remains visible while scrolling.
- At desktop width, place a sticky section navigation on the left beside the reading column. It must not become an overview grid above the story that delays reading.
- Navigation links jump to section headings. The active section follows the reader's scroll position.
- On mobile, replace the sidebar with an expandable section menu displaying the current section. All content remains in the same page.
- Header branding and a clear return link lead to home. Browser Back restores the previous home position where practical.
- Images, paragraphs, subheadings, lists, quotes, explanations, code and links share one reusable content layout. Projects can have different section counts and content lengths.
- Any ImprovedDb rating note remains associated with that project. For v1, incorporate it beneath Ratings & scoring with a stable subheading anchor; do not recreate a global Writing index or separate chapter-page flow.

### Visual baseline

Use the approved mockup as the visual reference. These values are starting tokens, subject to contrast and responsive review:

| Token | Light | Dark |
| --- | --- | --- |
| Page background | `#ffffff` | `#171918` |
| Panel/image backdrop | `#f0f2f3` | `#282c2e` |
| Primary text | `#202527` | `#f0f4f5` |
| Muted text | `#697074` | `#b0b9bf` |
| Dividers | `#e0e5e7` | `#3a4346` |

Headings use Manrope; body text uses DM Sans, with local fallback fonts. Self-host licensed font files and include their license notices. Avoid a production dependency on third-party font requests. Preserve restrained borders and square/open card surfaces.

The mockup's desktop section rail is approximately 165 px with a 40 px gap. Treat these as reference proportions, not fixed requirements at every viewport. Keep prose around 65–75 characters per line; allow images and diagrams to use more width. Verify headings, navigation and images at 320, 390, 768, 1024 and 1440 CSS pixels, plus 200% text zoom.

### Portable design handover

The approved gallery currently lives in ignored `Plans.local/PortfolioMockups/`. It is useful for local review but cannot be a future implementer's only reference.

Before layout implementation, preserve a small portable reference package in the portfolio repository, for example `docs/design/studio/`: home and project screenshots at desktop/mobile sizes in both themes, this decision record, and reusable source images with provenance. Capture the selected Studio surface without the gallery review controls. Do not commit server scripts/logs, browser state, abandoned alternatives or the large base64-embedded prototype as application source.

## 4. Project content and evidence

### ImprovedDb

Use the supplied motivation as the opening section:

> I love movies and series. While we were watching something, my significant other would often wonder where we had seen one of the actors before. I wanted the answer right there on the page for the movie or series we were watching. You can quickly explore an actor's most popular, highest-rated, and latest work, and spot the title you recognise them from.

Keep this section sequence:

| Stable section ID | Heading | Content and media |
| --- | --- | --- |
| `why-i-built-this` | Why I built this | Personal motivation and the problem being solved |
| `familiar-faces` | Familiar faces | Browsing, actor credits and recognising other work; actual browse/cast images |
| `ratings-and-scoring` | Ratings & scoring | Comparable provider scores, handling missing values and the combined rating; rating note as deeper explanation |
| `data-collection` | Data collection | How source data becomes the catalog; a sourced explanation and simple diagram |
| `statistics` | Statistics | Generated graphs, useful questions and the publication pipeline; real graph imagery |
| `machine-learning` | Machine learning | Historical award exploration, model families and limitations; actual interface imagery |

The live source is [ImprovedDb](https://improveddb.jacobgrum.com/). Verify facts against its current repository/docs and public interface during content preparation. Existing source captures show browsing, cast, graphs, statistics and machine learning. Preserve captions, capture date and provenance; screenshots are local portfolio assets rather than hotlinked live dependencies.

Research notes describe seven possible rating signals, valid-value normalization/averaging, a minimum of two signals and 10,000 IMDb votes for combined ranking, a 781-definition graph catalog, and eight accepted historical models. These are dated research findings, not evergreen counts. Recheck before publication, avoid unsupported performance claims, and explain ML outputs as retrospective contender signals rather than calibrated winning probabilities. Resolve or omit the previously observed conflicting award-data cutoff copy.

### Other project examples

- **GeckoBot:** the owner supplied the private `Grumlebob/mail` and `Grumlebob/MailDemo` repositories. Begin with `mail`, which explicitly names GeckoBot and separates Outlook booking flow, parser and Tkinter UI modules; retain MailDemo as related demo evidence until the intended version is confirmed. Prepare fictional booking/email examples. No runtime behavior has been verified, and private source URLs are not public actions.
- **TraceBack:** describe the documented research prototype, explicit experiment/pipeline structure, data locations, saved run manifests, snapshots and recreation of saved context. Capture a synthetic workflow and preserve its reproducibility boundaries. Do not claim full pipeline execution or guaranteed identical results.
- **KinoJoin:** use the owner-supplied [KinoJoin repository](https://github.com/Grumlebob/KinoJoin). Its inspected source supports cinema/showtime filtering, creating and sharing an event, participant preferences, results, host confirmation and calendar actions. Prepare a project-specific story, not a copy of ImprovedDb's headings.
- **Ship Inspections:** use the owner-supplied [BlazorTusReliableUpload repository](https://github.com/Grumlebob/BlazorTusReliableUpload). Its inspected source contains vessel-part navigation, condition forms, attached images and resumable upload handling. Present the local/sample status accurately; do not infer production operation, compliance or working AI inference from the UI.
- **Unlost:** the owner confirms the Dropbox **Project map** folder as the source for this historical Java map project. Use its `rapport.pdf` and genuine UI/algorithm images for OSM rendering, address search, spatial structures, Dijkstra/A* routing and project lessons. The Java application source was not located; at the owner's instruction, continue with these artifacts. `hojelseMaps.zip` belongs to someone else and is excluded.
- **MiniTwit:** use the owner-supplied [The-Pentuple-MiniTwit repository](https://github.com/Grumlebob/The-Pentuple-MiniTwit), displaying the name **MiniTwit**. Reviewed report/docs support a historical microblogging project, migration to .NET, client/API separation and DevOps work. Prepare timeline, architecture and observability figures; do not assume old deployment addresses still host the app.
- **BestBets:** prioritize the owner's school-material `Exam.pdf` and `BestBets.pptx`, with private locations recorded in the source note. Reconcile those materials with the [Architecture repository](https://github.com/Grumlebob/Architecture), existing report, diagrams and prototypes. Explain architecture for the fictitious high-data-volume scenario and sports-event bursts such as the World Cup. Separate quality-attribute targets, design decisions and actual prototype evidence. The newly supplied PDF/deck have been located, not content-reviewed.
- **Geospatial research:** use the owner-supplied [ExamGDS repository](https://github.com/Grumlebob/ExamGDS) for the New York crime/amenities research story. Reviewed notebook structure/report support data preparation, maps and spatial-analysis sections. Select genuine figures with data attribution, explain limitations and avoid causal conclusions from association.
- **Grumlebob:** use the owner's explanation as the primary editorial source. A restricted local background folder is now recorded privately; inspecting or publishing its contents is not required. Prepare an accurate, domain-neutral story about approved automation, analysis, bookkeeping and billing. Exclude private domain context, identifying artifacts, sensitive workflows and results from prose, figures, links and metadata. Do not invent a different real use case to replace excluded context. Obtain the approved public explanation before publishing.
- **JobHunt:** use the owner-supplied private source repository recorded in the companion inventory. Frame the story around keeping job-application documents, details and tracking organized. The owner's desired boundary keeps role selection and personal writing manual, while administrative assistance handles records, relevant documents, Notion and form/upload preparation. Current source procedures also allow assisted letter drafting; resolve that difference before claiming writing is entirely manual. Preserve the documented user-only final submission. Use fictional media and omit an inaccessible public source action.

The [companion inventory](Support/PortfolioStudio/ProjectInventory.md) provides proposed summaries, stable section IDs, media requests, evidence and limitations for all eleven projects. It also compares the six public author-book project titles with the ten book-cover demos. The portfolio's eleven entries comprise those six owner projects plus five explicitly supplied additions; the cover demo names do not establish more owner projects.

Do not infer employers, clients, dates, project roles, frameworks, public repository links, usage numbers or outcomes. Use facts established by the provided sources and distinguish team-project context from individual contribution. Keep unsupported case-study material as local drafts. Before public launch, each visible card needs reviewed copy and a meaningful destination; omit incomplete projects rather than publishing placeholder stories. All eleven candidates remain in the preparation backlog even if the launch set is smaller.

### Content preparation and review sequence

1. Recheck ImprovedDb and prepare its complete six-section story as the first implementation slice.
2. Prepare KinoJoin and TraceBack next. Their different workflows exercise shared components, code/examples, screenshots and diagrams without repeating the same story structure.
3. Prepare Ship Inspections from its actual forms/upload source and capture a fictional inspection. Prepare Unlost from its confirmed historical report and existing screenshots; source recovery is not required.
4. Prepare MiniTwit from the reviewed application/report/docs and BestBets first from the owner-selected Exam PDF and presentation, reconciled with report/prototype evidence. Keep historical operation, hypothetical requirements and measured evidence distinct.
5. Prepare Geospatial research from its notebook/report, with a few legible attributed maps and plots, method explanations and limitations.
6. Review GeckoBot's supplied sources/requirements and confirm the intended version. Obtain Grumlebob's approved public explanation and permitted generic figures; restricted source inspection is optional. These remaining content inputs do not block the other stories.
7. Prepare JobHunt's administrative-work story and compact personal/assisted-task comparison using fictional examples. Reconcile its writing boundary and verify account-creation/credential claims before final public wording. Do not modify its private workflow as part of portfolio planning.
8. Review each project's role/context, facts, media and links independently. An incomplete project stays a draft while ready projects proceed.

For each story, record fact notes using the companion register's source IDs. Each numerical claim, historical date, implementation statement or outcome needs an evidence reference. Proposed personal motivation and lessons require owner review. Keep an explicit list of open questions instead of silently converting them into public copy.

## 5. Content architecture and API contract

### Authoring and publishing

Recommended source layout in the downstream repository:

```text
Content/Portfolio/
  site.json
  projects/
    improveddb/
      project.json
      sections/
        why-i-built-this.md
        familiar-faces.md
        ratings-and-scoring.md
        data-collection.md
        statistics.md
        machine-learning.md
      media/
    geckobot/
    traceback/
    kinojoin/
    ship-inspections/
    unlost/
    minitwit/
    bestbets/
    geospatial-research/
    grumlebob/
    jobhunt/
```

`project.json` holds typed metadata and ordered section descriptors. Each descriptor supplies an explicit stable ID, heading, Markdown file and optional structured media blocks. Writing prose should not require editing JSX. Avoid arbitrary executable MDX, raw React components in content, and a general page-builder schema.

The C# content path validates the source and produces a deterministic, public-only bundle. Use a maintained Markdown parser with raw HTML disabled and an allowlisted rendering policy. Normalize content into the agreed public DTOs once; use the same compiled representation for API responses and prerendering. Decide the specific parser/library during the first content slice and record the choice, rather than maintaining two independent Markdown implementations.

V1 renderers support prose, headings, links, lists, quotes, images with captions, code and simple galleries where the story needs them. Serve diagrams as reviewed image/SVG assets with accessible text equivalents. Do not load an interactive chart or diagram runtime to display a static figure.

The validator rejects duplicate slugs/section IDs, missing files, unsafe paths or link schemes, unsupported block kinds, invalid metadata, missing image dimensions/alt decisions, and published links to draft content. Drafts must be excluded from the API, prerender snapshot, sitemap and public media output. Generate only public assets; do not copy the entire authoring directory into `wwwroot`.

### Authoring contract details

Keep `publication` separate from an optional factual project status such as prototype or archived. New content defaults to draft. Previewing a draft locally must not turn it into a production API route; a production export always excludes drafts and private preparation records.

Use explicit string values for supported block kinds, with a corresponding C# model and OpenAPI discriminator. Begin with `prose`, `figure`, `gallery`, `code` and `quote`; introduce another kind only when reviewed content requires it. A `prose` source can contain ordinary Markdown lists, links and subheadings. A main section's H2 and ID come from metadata; prose headings begin below that level. This keeps the visible story and sidebar synchronized.

Example authoring shape, illustrating a draft KinoJoin section rather than files already created:

```json
{
  "schemaVersion": 1,
  "slug": "kinojoin",
  "title": "KinoJoin",
  "publication": "draft",
  "displayOrder": 40,
  "summary": "Plan a cinema outing, share possible showtimes, and collect the group's preferences.",
  "cover": {
    "asset": "media/kinojoin-cover.webp",
    "alt": "Example cinema-event planning screen"
  },
  "links": [
    { "label": "Source code", "url": "https://github.com/Grumlebob/KinoJoin" }
  ],
  "sections": [
    {
      "id": "finding-showtimes",
      "title": "Finding the right showtimes",
      "blocks": [
        { "kind": "prose", "source": "sections/finding-showtimes.md" },
        {
          "kind": "figure",
          "asset": "media/showtime-filters.webp",
          "alt": "Example cinema, film, genre and date filters",
          "caption": "An example of narrowing the available showtimes."
        }
      ]
    }
  ]
}
```

The exporter resolves image dimensions/variants and content revision; authors do not invent those fields. The final model may use the delivered template's naming conventions, but retain these responsibilities. The public DTO contains rendered/normalized blocks and public asset URLs, not `source` file paths, publication-review notes or internal authoring paths.

Validation includes case-sensitive path checks so Windows authoring produces a valid Linux build; relative path containment; unique IDs; at least one section for a published story; supported URL schemes; escaped code; image existence/format checks; and bounded content. Raw HTML, scripts, event handlers and unsafe SVG/link content must not pass through to the reader. Validate internal links after excluding drafts so a published page cannot point at an unpublished destination.

An update to a published slug or section ID needs a deliberate compatibility decision. Prefer keeping identifiers stable. If a slug changes, record an explicit old-to-new redirect; do not derive redirects from guessed titles. Moving a section keeps its ID, while removed anchors need an editorial decision and checked incoming links.

### Minimum public model

- `SiteContent`: name, home heading/summary and verified global links.
- `ProjectSummary`: stable slug, title, summary, cover, optional sparse tags and display order.
- `ProjectDetail`: summary metadata, verified external links, ordered sections and optional editorial dates only when known.
- `ProjectSection`: stable ID, title and ordered supported content blocks. The sidebar derives from this list.
- `ImageAsset`: public URL, intrinsic width/height, responsive variants, alt text or explicit decorative status, optional caption and provenance.
- `PublishedContentManifest`: schema version, deterministic content revision, published slugs and generated asset references.

The catalog response stays lightweight: cover metadata, title, summary, sparse tags and order. Full prose belongs to the detail response. Initially keep collection and detail payloads below 100 KiB and 250 KiB of uncompressed JSON respectively, excluding separate image files. Treat these as review budgets, measure them against actual stories and document any justified exception. No inline base64 screenshots or fetching every project story to render home.

Suggested read endpoints are `GET /api/portfolio/site`, `GET /api/portfolio/projects`, and `GET /api/portfolio/projects/{slug}`. Final endpoint/module names should follow the delivered template conventions. Return summaries from the collection endpoint, not every full story. Missing/unpublished projects return 404 Problem Details; no HTML fallback on API paths. No anonymous content-writing endpoint is required.

Define DTOs and validation in C#, expose accurate OpenAPI metadata, and use the inherited schema/type generation and drift checks. [openapi-fetch](https://openapi-ts.dev/openapi-fetch/) supplies the typed transport. During migration, preserve authorization and private cache rules for any endpoints still present. Final Portfolio removes account/bookcase APIs; former private routes must return 404 without an HTML fallback or leaked data.

### One release, one content revision

Build order:

1. Validate and compile public content/media with the C# export entry point, without a live database, Redis or production credentials.
2. Generate/check the API schema and TypeScript contracts using the template workflow.
3. Build React using the compiled public snapshot. Generate the page list from published slugs.
4. Package that exact content bundle, frontend output and required assets into the ASP.NET release.

Hash the compiled content into a revision and include it in the public manifest. API and HTML output must reference the same revision. A content edit ships through a reviewed rebuild/release; it is not a runtime filesystem edit on the deployment node. Rollback restores content, images and UI together. Keep generated artifacts reproducible and follow the downstream repository's established policy for which outputs are committed.

## 6. Frontend responsibilities and interactions

Use the delivered React structure, renamed to `Portfolio.React`. Keep route modules small; separate the portfolio feature, reusable visual components, generated API code and content renderers. Suggested components are `SiteHeader`, `ThemeToggle`, `ProjectGrid`, `ProjectCard`, `ProjectStory`, `SectionNavigation`, `ContentRenderer` and `ProjectImage`.

React Router owns URL matching, document metadata, route errors, route focus and navigation/scroll restoration. TanStack Query owns runtime API reads. React state owns the theme preference, expanded mobile menu and image dialog. Do not introduce Redux or put scroll position in Query.

### Route and component contract

| Surface/component | Input | Required behavior |
| --- | --- | --- |
| Home route `/` | Published site metadata and ordered project summaries | Selected-work heading, all ready cards, meaningful empty/error states |
| Project route `/projects/:slug` | One published project detail | Cover/introduction, continuous sections, navigation and outbound actions |
| `ProjectCard` | One summary | One clear accessible project link; descriptive image behavior; no nested interactive controls |
| `ProjectStory` | Ordered sections and blocks | One H1; metadata-driven H2s; shared reader layout; no project-name conditionals |
| `SectionNavigation` | Sections and current ID | Desktop sticky rail/mobile disclosure; real links; one active item |
| `ContentRenderer` | Validated block union | Exhaustive supported renderer selection; safe links/prose/code; captioned media |
| `ProjectImage` | Dimensions, variants and alt decision | Stable layout, appropriate loading priority and optional accessible enlargement |
| Not-found route | No matching published slug | Useful home link and HTTP 404 for direct production requests |

Home needs no separate `/work` page. If an actual published legacy Work URL exists, add an explicit redirect to `/`; do not introduce legacy URLs merely because the prototype used page-switching state. No About, Writing, login or admin routes belong to v1.

Optional related-project links at the end of a story derive from published slugs only and use plain links. They must not delay or replace the full section content. Do not add a carousel, ratings widget, map runtime or functioning email/upload tool to explain a project's existing feature.

### Runtime API state

- Use one shared QueryClient, the generated transport and centralized query options/keys. Include the content schema/revision where needed to isolate incompatible releases.
- Initial recommendation for ordinary public API content: `staleTime: 5 minutes`, `gcTime: 30 minutes`, no polling, no focus-triggered refetch of the story being read, and stale reconnect refetch. Pass cancellation signals to the transport.
- Retry transient failures at most twice with backoff. Do not retry 404 or other permanent client errors. Respect throttling responses and provide a manual retry action.
- Define loading, empty, missing, offline, throttled and server-error states. Preserve already readable content on background failure.
- HTTP caching and Query caching are separate: public responses can use ETags and short revalidation policies; private endpoints retain `private, no-store`. Fingerprinted assets use long immutable caching; HTML remains revalidatable.
- Do not persist API data to localStorage or add a service worker in v1. Only the theme preference needs local persistence.

These are portfolio-specific settings to confirm in the first slice, not replacements for the template's global defaults. Query considers data stale by default and can refetch on focus, mount and reconnect; choose the policy deliberately. See [Query defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults).

In the initial SPA slice, hooks use the generated API and optional `clientLoader` prefetching uses the same query options. In the prerendered release, editorial data can be rendered directly from the build snapshot. Do not add a Query request just to obtain data already present in static route output. When an existing API-backed hook is seeded, use the same key/DTO; revision-scoped static story entries can use `staleTime: Infinity` to prevent a later release replacing the narrative during reading. The ordinary API policy above still applies to unseeded/runtime reads. Keep real timestamps and content revisions; do not manufacture build-time data freshness to suppress hydration problems.

### Section links and scroll tracking

- Use real fragment links such as `/projects/improveddb#statistics`, not buttons with mockup-only state routing.
- Derive desktop and mobile navigation from the same ordered section metadata. Use explicit IDs so editing a heading does not break shared links.
- Use an IntersectionObserver with a documented heading-offset rule. Highlight the section whose heading has most recently passed the reading threshold; handle short sections and the end of the page deterministically.
- Passive scrolling updates `aria-current="location"` and visual highlighting without adding browser-history entries, moving focus or repeatedly announcing changes.
- Explicit section navigation updates the fragment and makes the target heading reachable by keyboard/focus. Apply `scroll-margin-top` for any fixed header and account for images/fonts settling on initial fragment visits.
- Preserve native links before hydration. Use reduced-motion preferences when enhancing scroll behavior. Route changes reset section observers cleanly; Back/Forward restores fragment and reading state.
- The mobile section menu closes after selection and returns focus appropriately. A long desktop sidebar scrolls within available height instead of clipping links.

For deterministic active tracking, choose the last section heading above a threshold just below the fixed header, select the first section before that point is crossed, and select the final section at the end of the document. Calculate offsets from the actual header rather than the mockup review toolbar. Observe layout changes without polling every frame; images already reserve their dimensions. Re-evaluate after route/content changes and clean up observers/listeners on unmount. Test a short final section and a long code/gallery section explicitly.

Passive scroll highlighting does not rewrite the fragment. The URL reflects an explicit destination, while active navigation reflects the current position. Back/Forward restoration must not be cancelled by an effect that repeatedly scrolls to an old fragment on every render.

### Theme and media

Default to system appearance until the user chooses light or dark; save that choice and apply it across routes. Follow system changes only when no explicit choice exists. Use accessible button labels/state and visible focus. Theme changes preserve reading position and never recolor or invert screenshots.

Apply the initial theme before first paint using a small CSP-compatible bootstrap with guarded storage access and a CSS system-preference fallback. The React initial render must be compatible with the build environment and hydration; do not read `window` or localStorage unguarded while rendering. React Router's [SPA documentation](https://reactrouter.com/how-to/spa) explains its build-time root rendering requirement.

Generate responsive image variants with fixed intrinsic dimensions; prefer modern formats with a fallback where useful. Load the visible cover promptly and lazy-load lower images. Cards may crop decorative covers; technical screenshots/graphs in stories retain legibility and offer enlargement when useful. An enlargement dialog needs Escape, focus containment, a close control and focus return.

Prepare roughly 640 px card, 1280 px reading and 1920 px enlargement variants when originals justify those sizes; do not upscale smaller sources. Keep originals out of the first-load path. Store captions and crop intent in content metadata. Strip unnecessary identifying metadata, preserve original-source attribution and do not invert screenshots in dark mode. Diagrams need an adjacent prose explanation; color alone cannot encode meaning.

Use the project inventory's shot lists to prepare real media. For Unlost, select already available artifacts and preserve their dated provenance. For GeckoBot, a clearly illustrative workflow graphic is acceptable for local review until actual product evidence exists. Fonts and above-the-fold assets need a small preload policy based on measurements, not preloading every asset.

## 7. Public rendering and hosting

SPA mode is the development milestone, not the intended final public reading experience. Before launch, set `ssr:false` with an explicit prerender list containing `/` and every published `/projects/{slug}`. React Router supports [prerendering without a runtime SSR server](https://reactrouter.com/how-to/pre-rendering). Node is a build dependency; production continues to run ASP.NET Core only.

Prerender loaders read the compiled public snapshot, not a live production API. They are a build-time adapter, not a second backend or an independent server-state store. For API-backed components, seed the same Query definitions from this snapshot and prevent a redundant hydration fetch. Keep runtime-only data out of static output. Match implementation details to the delivered Router version and verify generated HTML, navigation data and fallback artifacts rather than assuming their filenames.

ASP.NET hosting must serve the correct prerendered document and Router navigation-data file for each known route. Keep asset/API/health/reserved paths outside frontend fallback. Unknown projects, missing images/scripts and missing Router data return actual HTTP 404 responses. A client error screen displayed under HTTP 200 is insufficient. Drive known route validation from the published manifest and implement a real 404 document for unknown public routes. This requires a portfolio hosting change beyond the template's SPA fallback.

Each public page needs a unique title/description, configured canonical URL, social preview metadata and an appropriate preview image. Generate sitemap entries from published projects; configure the public base URL through validated product settings. Preview environments stay unindexed. Include JSON-LD only when accurate content supports it. Do not invent dates, credentials or professional affiliations.

JavaScript-disabled direct responses should contain the project title, prose, section links and images. Interactive enhancements such as active-section tracking, theme controls and image dialogs can hydrate afterward. Navigation data, HTML and APIs must remain compatible across a deployment; follow the inherited cache/asset retention policy and rehearse a page left open across an update.

## 8. Phases, progress and agent handoffs

[DeliveryPhases.md](Support/PortfolioStudio/DeliveryPhases.md) replaces the former S0–S6 packet list. Its P0–P10 phases explicitly include downstream import, full Portfolio naming, React-only cleanup, LocalSingleNode-only cleanup, product content, public rendering, operations and release acceptance. No previous S packet was implemented; do not interpret the new IDs as completed work.

Use [Progress.md](Support/PortfolioStudio/Progress.md) as the single execution ledger. Every packet records its owner/session, branch, exact PR head, local checks, PR, merge SHA, green main CI, changed files, blockers and exact next action. Complete means merged with green main, not merely written or tested locally. Mark verified work complete; keep unverified claims and unavailable checks explicit.

Start with one eligible packet per session. Read the latest ledger before editing. Reserve files before sharing a phase with another agent. Do not run build and test concurrently in one checkout. Different agents working over different days need no shared chat history: the resume prompt, packet contract and retained evidence must be sufficient.

Review the real Studio home and ImprovedDb story at P5 before filling the remaining stories. Preserve the approved design. Publication blockers on GeckoBot, Grumlebob or JobHunt do not block building the renderer or publishing other fully reviewed stories.

### Planned verification during implementation

The current task changes Markdown plans only. Review Markdown and run `git diff --check`; do not run application builds or tests for this planning change.

During implementation, use the actual downstream local gate from `docs/Test.md`, updating it in each removal/rename packet. Keep format, Release build, Release tests, deployment audit/render/script checks and applicable React checks. Before LocalCluster deletion, move its reusable gate entry points and replace obsolete rules with Portfolio rules. After rename, commands must use `Portfolio.sln`. Require `build-test-push` green on every PR's exact final head and successful main CI on its merge.

Required implementation evidence covers:

- Deterministic C# content validation/export; DTO/status contracts; drafts excluded from API, media, prerender and sitemap.
- Generated-contract drift; strict TypeScript/lint; content renderer and query behavior; no Books/account dependency in the final contract.
- Home, every published story, direct fragment links, desktop section tracking, mobile menu, theme persistence, accessible enlargement and Back/Forward.
- SPA failure/retry states; prerendered initial content; hydration without duplicate reads.
- GET/HEAD, exact documents/navigation data, canonical paths, real 404s, former sample/account routes and reserved-path protection.
- WCAG 2.2 AA review: contrast, semantic headings, skip link, focus, reflow, reduced motion, alt text and manual screen-reader spot checks.
- Both themes at 320, 390, 768, 1024 and 1440 CSS pixels and 200% text zoom. Use Chromium broadly and representative Firefox/WebKit smoke coverage.
- Measured production loading under documented mobile conditions. Initial targets are LCP at most 2.5 s and CLS at most 0.1; record actual JS/image transfers. Lab measurements do not establish real-user performance.
- Production image inspection: C# runtime, no Node/Blazor runtime payload, Portfolio image identity, matching content/release revision and scoped update/rollback.
- LocalSingleNode audit, native identity, runner capacity, LAN/public acceptance, connector health, backup/doctor and independent controller checks.

The final acceptance profile must be Portfolio-specific. The inherited `ReactPublicV1` profile checks sample Books data and is useful only before product replacement. Update the profile resolver, image labels, manifest, CI smoke, node setup and `Scripts/Test-DeployedSite.ps1` together. Do not leave production acceptance asking for Books or silently weaken it to an HTTP 200 check.

## 9. Content editing and final completion

Document how to add a project without editing the layout: create metadata/Markdown, add licensed reviewed media, validate, preview, publish through a PR and rebuild the immutable release. Include a small draft starter and instructions for stable IDs, safe blocks, dimensions, provenance, related links and public/draft separation. Once implemented, record real export/build/preview commands; do not invent executable commands in advance.

Known decisions are Portfolio identity, destination repository, React/C# architecture, LocalSingleNode target and intended public URL. Remaining input concerns actual node identity/privileged bootstrap, protected Cloudflare authentication, verified project contributions/media and the factual gaps in the inventory. Ask for each only when its dependent packet needs it. Use the node handoff's one-action format whenever the controller cannot proceed.

Release milestones:

1. **Repository foundation ready:** P0–P3 merged and green; Portfolio identity, React-only frontend and LocalSingleNode-only deployment are proven.
2. **Product ready:** P4–P7 merged and green; reviewed Studio pages, public HTML, final acceptance profile and documented operations work locally.
3. **Public launch:** P8–P9 pass on the intended native node with valid HTTPS, verified release/content identity and a recorded launch set.
4. **Full handover:** P10 records update/recovery evidence, complete authoring/runbooks and disposition of all eleven stories.

Recommend an initial launch of ImprovedDb, KinoJoin, TraceBack and Unlost, subject to their publication checklist. Expand to all eleven without filler cards. An initial four-story launch is a milestone, not completion of the eleven-story backlog. Mark the entire plan complete only when all required packets are merged and green, public acceptance passes, and each intended story is published or explicitly deferred by the owner with a reason. Do not count an agent's unilateral draft decision as owner-approved scope reduction.

Historical preparation on 2026-10-11 compared both sample Books catalogs, reviewed the source/report artifacts recorded in the inventory, and prepared the JobHunt workflow preview. It ran no source apps, notebooks or benchmarks and completed no Portfolio implementation, node setup or deployment. Keep that evidence separate from later runtime and publication results.
