# Portfolio execution decisions and failure review

Parent: [master plan](../../PortfolioStudioImplementation.md). Ownership and completion: [Architecture.md](Architecture.md), [DeliveryPhases.md](DeliveryPhases.md), [Progress.md](Progress.md). Figure production: [VisualProduction.md](VisualProduction.md).

These are implementation defaults, approved as planning recommendations by the request to resolve routine decisions. They specify work to create in Portfolio; no command or component below is implemented by this planning change. A future agent may revise a default only with a concrete dependency or visitor benefit, a recorded decision, and corresponding contract/check updates. Source evidence and operator authorization cannot be invented to close a checklist.

## 1. Decisions that no longer need a design question

| ID / packet | Decision | Reason and boundary |
| --- | --- | --- |
| D01 / P0.1 | Prefer a completed, merged-green reusable React delivery baseline. The active upstream delivery is SR1–SR6 in `ReactFrontendSingleRepository.md`; it is not cancelled. | P0–P7 implementation and retired-repository cleanup are complete; public React delivery remains incomplete. Independently prepare content now. Before import, verify required foundation, release and native tooling on a selected SHA. If upstream public observation alone remains, record why it is independent; missing reusable release/setup code blocks its dependent packet. Do not copy an open PR or interfere with the other agent. |
| D02 / P4.1 | Use Markdig in C# with CommonMark prose, HTML disabled, and an explicit supported-node/link policy. | One parser/compiler, no MDX, client Markdown parser or arbitrary component expressions. Pin a compatible package at implementation time. See [Markdig's primary documentation](https://github.com/xoofx/markdig). Disabling HTML alone does not validate links. |
| D03 / P4.1 | Compile prose to safe HTML in C#; render it through one audited React `Prose` component. | Reject unsupported syntax and unsafe destinations during compilation; encode text/code and attributes. Only compiler output can reach `dangerouslySetInnerHTML`. No raw author HTML, runtime sanitization of arbitrary responses, Markdown images or embedded SVG/iframes. Figures are typed blocks. |
| D04 / P4.1 | Add one console project, `Portfolio.ContentTool`, referencing `Portfolio.Core`; put compilation/contracts in `Portfolio.Core/Content` and immutable bundle loading in the host. | Share the public representation without booting the web host, Identity or a DB to export. Avoid a plugin engine, generic repository, custom Markdown grammar or another DTO model. Compilation runs at build time; runtime reads packaged output once. |
| D05 / P4.1, P5.3 | Use pinned Sharp as a Node build dependency for raster variants; reviewed SVG remains an external image asset. | Node already exists for Vite. Add `scripts/portfolio-media.mjs`, use [Sharp output options](https://sharp.pixelplumbing.com/api-output/), and encode only allowlisted published assets. No image server or .NET image-library licensing dependency. No runtime Node. |
| D06 / P7.2 | Final Portfolio is file-only: remove PostgreSQL, Redis, Identity, migrations, account mail/provider/session services and unused Data Protection dependencies. | Public immutable editorial content needs none of them. Keep inherited services temporarily while earlier packets need them. VS3 must remove the complete dependency graph before final release readiness, including gates and operations. A newly demonstrated real requirement needs an explicit revised decision; inherited checks alone are not such a requirement. |
| D07 / P5, P7.1 | Published routes use offline prerender loaders; ordinary reading/navigation does not fetch the same story again through Query. | C# APIs remain the public read contract. Keep the generated client and one QueryClient for actual API consumers and their checks. No duplicated HTTP + loader + state-effect fetch. Use the pinned [Router prerender contract](https://reactrouter.com/how-to/pre-rendering); its dynamic routes need an explicit published-path list. |
| D08 / P6 | Prefer a strong static figure and prose explanation. Add no project-specific interactive demo in v1. | Navigation, theme, responsive figures and optional enlargement supply useful interaction. Do not rebuild maps, calendars, uploaders, mail or trackers inside the portfolio. Code-native diagrams and genuine plot exports keep content portable. |
| D09 / P6 | Omit unverified numerical outcomes, dates and personal contribution claims. Preserve known team/prototype/historical context. | A missing individual role does not force fabricated credit or block a neutral, accurately attributed project description. Review role wording if included. Source-backed descriptions can publish without a role badge. Missing reuse rights or prohibited context still block the affected asset/story. |
| D10 / P6.11 | JobHunt describes administrative assistance and personal review/final submission; acknowledge that instructions can assist drafting where the reviewed version supports it. | Do not promise that all writing is manual. Present personal authorship as the owner's intended boundary, distinguish it from implementation, and omit automatic account creation until verified. This resolves copy without changing the JobHunt application. |
| D11 / P6.10 | Grumlebob remains a generic, truthful tools story using the owner's approved explanation; restricted source inspection is unnecessary. | Existing title/card copy is a proposal, not approved public evidence. Prepare a neutral diagram and short proposed copy, then request one specific description/approval when this packet reaches publication. Never invent another business context or expose excluded context in any output. |
| D12 / P9, P10 | Launch four reviewed stories when possible; finish all eleven or record explicit owner deferrals. | No placeholder public cards, unilateral scope reduction, or declaring completion at first launch. Missing late-story evidence does not block ready stories. |

## 2. Concrete content/compiler contract

Implement these names during P4.1, then replace this proposed-command notice with actual help/output evidence in the downstream authoring guide. Run from the Portfolio repository root; Node/npm/.NET versions come from the pinned baseline.

```text
dotnet run --project Portfolio.ContentTool -- validate --source Content/Portfolio
dotnet run --project Portfolio.ContentTool -- plan-media --source Content/Portfolio --output artifacts/portfolio-media-plan.json
npm --prefix Portfolio.React run content:media
dotnet run --project Portfolio.ContentTool -- export --source Content/Portfolio --media artifacts/portfolio-media/manifest.json --output artifacts/portfolio-content
npm --prefix Portfolio.React run api:generate
npm --prefix Portfolio.React run build
```

`content:media` reads the fixed intermediate plan and writes only `artifacts/portfolio-media/`. The export publishes into a new staging directory under `artifacts/`, checks it, then swaps the app-owned output atomically. Never delete an arbitrary output directory from an unchecked CLI value. `validate` checks source structure without requiring generated variants; `export` additionally requires valid complete prepared media. Production/CI uses the same ordered pipeline with no network reads beyond dependency installation. Provide a convenience build script rather than relying on remembered manual order.

### Authoring and public output

Keep the master's `site.json`, project metadata, section Markdown and media layout. Author metadata has the existing `prose`, `figure`, `gallery`, `code`, `quote` block kinds. Start VS1 with prose/figure/code as needed; add gallery/quote support in the first story requiring them, without publishing unsupported blocks. Markdig prose supports paragraphs, emphasis, strong text, inline code, lists and ordinary links. H1/H2 belong to metadata; allow explicit H3 subheadings with validated stable IDs for deeper notes. Reject Markdown images, raw HTML, embedded widgets and unsupported extensions with a project/file/block diagnostic. Code blocks remain text with a bounded language label, never executable or interpreted HTML. Do not enable all advanced extensions by default.

Implement URL validation on parsed destinations, including decoded/obfuscated schemes. Outbound links are HTTPS; same-site links resolve to a published path/anchor; explicit verified site contact may use `mailto`. Reject protocol-relative URLs, `javascript`, `data`, absolute local paths and links to drafts. For MVP, reject raw HTML source even though disabled parsing would otherwise render it as text. The safe HTML renderer emits only the selected semantic tags and encoded attributes. Treat it as a security boundary with malformed/link/encoding fixtures; do not substitute a regex HTML sanitizer.

Use an explicit authoring convention for H3 anchors, for example `### Rating details {#rating-details}` with Markdig's generic-attributes extension enabled only for this controlled use. Accept only an `id` attribute on H3, validate it against the section/subheading namespace, and reject classes, styles or attributes on other nodes. Do not derive stable IDs from mutable heading titles. Figures/links to those anchors are checked after compilation.

SVG input is parsed with DTD/external entity resolution prohibited. Allow only required static drawing/text/group/definition/clip/gradient primitives and approved numeric/color/layout attributes. Reject scripts, event attributes, `foreignObject`, animation, embedded HTML, embedded raster payloads, external references, URL-bearing styles and unsupported elements. Internal clip/gradient references must resolve to local IDs. Do not execute SVG to inspect it or paste source SVG directly into React markup. An asset outside the policy must be faithfully re-exported/redrawn as a safe image, or omitted; stripping unknown markup silently is not validation.

Suggested exported layout:

```text
artifacts/portfolio-content/
  manifest.json              # schemaVersion, revision, published paths, asset hashes
  site.json                  # public SiteContent DTO
  catalog.json               # ordered lightweight ProjectSummary DTOs
  projects/<slug>.json       # public ProjectDetail DTO with normalized blocks
  media/<content-hash>.<ext>  # approved variants, fonts and previews as applicable
```

The exact DTOs are C# records with explicit OpenAPI discriminators for supported block kinds. Generated TypeScript must narrow on `kind`; use an exhaustive renderer and fail the build on unknown kinds. Do not handwrite parallel frontend interfaces or expose filesystem paths. `safeHtml` belongs only to compiled prose; asset provenance in public DTOs is limited to an intentional attribution/capture note, never private review records. Keep source registers and restricted inputs outside `wwwroot`, Vite `public`, package copy globs and public source maps.

Compute SHA-256 revision from canonical UTF-8 public JSON and sorted asset path/hash pairs, excluding the revision field itself. Normalize source newlines, serialize invariantly with stable ordering, and exclude timestamps, absolute paths, machine names and build IDs. Display order is numeric with slug as a deterministic tie-breaker; repeated orders warn, duplicate slugs/IDs fail. Changed image bytes change revision. Repeated builds on Windows/Linux produce the same content revision. Emit no draft entry, review text, unused original or private source location. Validate casing, root containment, symlink escape, output-path collisions and image bounds. Negative fixtures use distinctive draft/private sentinel strings and verify absence from the complete packaged public tree.

The media plan comes from C# published metadata. Sharp emits dimensions, variants and byte hashes; C# export verifies the plan/output correspondence, paths and hashes before accepting it. Prefer WebP plus original PNG/JPEG fallback where needed; no AVIF requirement for v1. Bound dimensions/pixel count before decoding. Never upscale. Portrait/technical material uses `contain`; covers may use an explicit focal crop. Defaults are 640/1280/1920 px widths limited by the source. Tiny diagrams stay vector or original size. Keep processing-library/version settings pinned and generated output ignored; commit approved source assets and provenance. Generated API declarations retain the baseline's commit/drift-check policy; compiled content, media variants and frontend build output are ignored/release artifacts, not manually edited tracked files.

Font production uses licensed self-hosted Manrope/DM Sans WOFF2 with Latin coverage appropriate to the published English text, normal variable weights only where supported, and included license files. Obtain originals from the official font source, record version/license and do not improvise font conversion or remove required notices. Use `font-display: swap` and measured selective preloads. Initial review budgets: a 640 px card variant about 160 KiB or less, 1280 px cover about 320 KiB, and a detailed reading figure about 500 KiB; preserve legible genuine plots and document justified exceptions. These are review targets, not reasons to damage labels. Home loads summaries and visible cover variants; lower cards/figures are lazy. Do not eagerly preload all eleven covers or enlargement originals.

## 3. API, route and release decisions

- APIs are the three master endpoints, read-only GET/HEAD, using one immutable loaded bundle. Include `schemaVersion` and `contentRevision` at the response envelope. Health/readiness verifies the current valid bundle; startup rejects missing/invalid assets/manifests. No runtime source watching or write endpoint.
- ETags derive from the representation/revision. Handle conditional GET/HEAD, 304 with no body, invalid slug and missing/draft detail 404 Problem Details. Apply short revalidation caching to public JSON/HTML, long immutable caching only to fingerprinted assets. Do not apply public cache headers to inherited private handlers during transition.
- Canonical routes are `/` and lowercase `/projects/<slug>` without a trailing slash. Redirect an otherwise known trailing-slash route with 308; unknown/case-variant paths return 404. Do not silently lowercase API slugs. Explicit published legacy redirects live in metadata, are loop/collision checked, and preserve relevant fragments in links.
- P7.1 inventories actual Router build output for `/` and one dynamic story before creating a hosting adapter. Map known documents and navigation-data requests from generated output; do not guess `.data` filenames, write a custom Router serialization format, or allow catch-all SPA fallback. GET/HEAD status and cache semantics agree. Missing asset/data/reserved/API paths keep genuine 404s; unknown public pages get a useful 404 document.
- HTML and Router data carry the same revision/schema as APIs. Keep the build-only snapshot reader out of browser bundles; client navigation uses generated Router data. Verify production has no unexpected framework manifest-discovery endpoint requiring Node. Pin route discovery behavior to a static complete route map if the selected version requires it.
- Keep current-document content stable during reading. On navigation-data revision/schema mismatch, perform one full document navigation to that destination; on a chunk-load failure after deployment, offer/perform a guarded single reload. Prevent reload loops and retain the target fragment. Retain previous fingerprinted assets if supported by inherited app-scoped deployment tooling; do not claim browser/CDN caches alone guarantee compatibility. P7 acceptance must exercise a tab opened before an update, navigation after it, and an unavailable-network retry.
- `PortfolioPublicV1` is the final acceptance-profile name, `React` is the frontend profile, and `ghcr.io/grumlebob/portfolio` is the image. Remove unused additional-profile publication from this React-only clone. Public origin is validated configuration; previews emit `noindex`, public release emits the published sitemap. No inaccurate JSON-LD is needed.

## 4. Adversarial execution review

| A less experienced executor might… | Consequence | Required correction / checkpoint |
| --- | --- | --- |
| Assume retired demo cancellation means React delivery is finished | Fork incomplete release/setup tooling | D01 and P0 capability matrix distinguish completed code, active SR packets and independent observation |
| Push template workflows before product identity is changed | Publish to the template's package or route jobs to its runner | P0 seed identity first; disabled Actions, explicit image/app/runner/environment inventory, no copied secrets |
| Wait for PR checks on a node with no runner | Circular bootstrap dependency | Early P8 runbook capacity path; human native step returned once, then resume customization PRs |
| Implement all API layers before any page | Large unseen integration failure | VS1 completes real ImprovedDb content/API/UI/direct HTML before expanding |
| Glob-copy content or import all project JSON into Vite | Ship drafts, private notes and every story on home | Compiler-published allowlist; negative package inspection; collection remains summaries only |
| Disable Markdown HTML and assume all links are safe | Script/encoded-scheme injection | Parsed destination policy, fixed HTML renderer and negative fixtures |
| Build a generic CMS, widget DSL or per-project JSX branches | Scope growth and hard maintenance | Five bounded block kinds, external static figures, one metadata reader |
| Guess Router data URLs or leave generic fallback | Broken client navigation or HTTP-200 missing pages | Inspect actual pinned output, exact route/data manifest, status matrix |
| Remove DB from Compose only | Startup, smoke, migration/release or recovery failure | P7.2 complete service consumer inventory and coherent capability/profile update |
| Carry old credentials or make empty migration bundles | Cross-app data risk and false provenance | Fresh app identity; no fake artifacts; file-only release contract explicitly omits migrations |
| Create decorative charts from convenient numbers | Misrepresent research/design as measured results | VisualProduction figure evidence and caption; omit unavailable results |
| Infer sole authorship from repository ownership | Incorrect portfolio credit | Neutral project description/team attribution; personal role only when verified |
| Treat first public homepage/four cards as completion | Missing stories, deep links and recovery | Full catalog dispositions plus direct/API/browser/operations evidence |
| Re-dispatch after a watcher stops or fix a host manually | Duplicate mutation or shared-service damage | Persist workflow ID; use runbooks/owned resources; resume that run |

## 5. Remaining external inputs and exact fallback

| Input | Default progress / smallest eventual handoff |
| --- | --- |
| Upstream SR work unfinished | Continue source/figure preparation; P0 inspects live merged capability matrix, waits only on its genuine dependency. No changes to upstream product behavior from this plan. |
| Individual roles/dates/outcomes | Omit unknown fields and unsupported counts; identify evidenced historical/team/prototype context. Ask one grouped contribution question only if personal credit is desired or source attribution cannot otherwise be accurate. |
| Actual screenshot unavailable | Use a clearly labeled sourced explanatory diagram; do not call it an actual interface. Choose fewer, stronger figures. Permission to reuse real artifacts must still be established. |
| BestBets evidence reconciliation | Preferred Exam/deck text review now identifies final broker/actor decisions and prototype limits; use the evidence note in ProjectInventory. Original diagram visual review remains part of figure production, not a new architecture choice. |
| Grumlebob public explanation | Prepare a short neutral proposal from existing owner statements; request that one concrete description before publication. Restricted context never supplies a fallback. Other stories proceed. |
| Native identity, root setup, credentials or launch authorization | Only return the one currently missing action from NodeHandoff. Include detected facts privately, never guessed target values. Do authorized independent repository/content work while waiting. |

Full-plan completion still requires public delivery and all story dispositions. Defaults reduce design questions; they do not manufacture approval, source access, permissions, tests or operational evidence.

## 6. Verification matrix to implement with the slices

| Boundary / packet | Required positive and negative evidence |
| --- | --- |
| Compiler / P4.1 | Valid first story; deterministic Windows/Linux revision; changed asset changes revision; duplicate slug/anchor, traversal/symlink/case mismatch, missing/oversized media, unsafe/encoded links, raw HTML/SVG and unknown block rejected; draft/private sentinels absent from complete packaged public output |
| API / P4.2 | Site/catalog/detail accurately generated; collection excludes body; real 404 Problem Details for unknown/draft slug; GET/HEAD/conditional 304 correct; no write routes; bounded payloads and consistent schema/revision; generated-contract drift fails |
| Reader / P5 | Continuous content, one H1 and stable section anchors; native links without JS; deterministic short/long/end sections; menu/focus/Back/Forward; both themes without hydration flash/error; blocked storage fallback; responsive image sizing and accessible enlargement |
| Hosting / P7.1 | Exact root/story GET200 and HEAD200/no body; known trailing slash308; unknown/draft route404; missing scripts/images/navigation data404; former Books/account/API paths404 without HTML fallback; reserved health/API/static separation; metadata/sitemap contain published routes only |
| Production browser / P7.3–P7.4 | Title/prose/section links/images readable without JS; hydrate without duplicate initial story request; navigate home/story/fragment and return; no unexpected Router discovery server request; open old tab then update/navigate/chunk failure with guarded recovery; offline preserves existing readable content |
| File-only operations / P7.2 | Startup/health/image with no DB/cache credentials; migration-free release accepted only for the declared file-only profile; mismatched source/digest/profile/hash still denied; doctor/backup/recovery/audits reflect actual services; no foreign volumes/services removed |
| Native/public / P8–P10 | True native identity and scoped access/capacity; exact running immutable release/revision; independent LAN/public normal TLS/browser/denial checks; owned connector healthy; authorized scoped restart, update and compatible rollback; all eleven story dispositions and handover evidence |

Use focused checks while implementing a checkpoint, then the full applicable documented local gate before push. Do not run every browser matrix after every prose keystroke or weaken required checks to save time. Packet completion records actual evidence, not this planned matrix.
