# Portfolio delivery phases

Parent: [PortfolioStudioImplementation.md](../../PortfolioStudioImplementation.md). Architecture/slices: [Architecture.md](Architecture.md). State: [Progress.md](Progress.md). Content: [PageBriefs.md](PageBriefs.md) and [ProjectInventory.md](ProjectInventory.md). Node work: [NodeHandoff.md](NodeHandoff.md).

Use [ExecutionDecisions.md](ExecutionDecisions.md) for resolved defaults and the proposed command/model contract, [ImplementationCheckpoints.md](ImplementationCheckpoints.md) for ordered substeps inside these packets, and [VisualProduction.md](VisualProduction.md) for concrete figure production. The packet IDs below remain the only work inventory.

## Execution rules

Each packet is a small unit that another agent can resume. A phase may require several PRs; combine tightly coupled code, contract, audit, test and documentation changes. Do not combine all cleanup and product work in one PR. Start a packet only when its listed inputs exist. Record actual file names after inspecting the chosen baseline; paths below describe the intended destination, not files already created.

The owner prefers vertical slice architecture and delivery. P0–P3 establish the independent product; VS1 then combines P4, P5 and first-story P7.1/P7.3 into one complete ImprovedDb reading journey. Begin API and UI against that story together, include direct readable HTML/hosting/acceptance before declaring VS1 complete, then repeat P6 per story. Phase IDs group tasks; [Architecture.md](Architecture.md) sets the product completion boundaries.

The master defines [three recommended fresh-chat checkpoints](../../PortfolioStudioImplementation.md#recommended-fresh-chat-checkpoints), C1–C3. Prepare the filled Progress handoff at those verified boundaries; continue in the current chat if the owner prefers. Phase and packet boundaries alone do not require new chats.

For each packet:

1. Read its dependencies and the current progress ledger. Inspect clean status and ownership. Claim the packet and affected files.
2. Create a task branch/worktree from verified Portfolio `origin/main`. Keep the template checkout and other agents' worktrees untouched.
3. Implement the listed output and its required checks. Preserve useful checks when replacing old behavior.
4. Run the applicable documented local gate before pushing. Builds/tests run sequentially. Never call an unavailable check passed.
5. Stage explicit paths, open a PR, verify `build-test-push` on its exact final head, merge normally and verify green main CI.
6. Record evidence, merge SHA and the precise next packet in the ledger. Commit the handoff through the normal documentation process; merge evidence may instead live in the linked PR description to avoid endless ledger-only commits.

Markdown-only packets require Markdown review and `git diff --check`; inherited protection/CI still applies. Initial seed of an empty repository has no branch against which to open a PR. Use the documented initial import, then route retained changes through PRs. If Portfolio is no longer empty, seed work is a normal reconciled PR.

## Dependency map and milestones

| Phase | Depends on | Result |
| --- | --- | --- |
| P0 | Planning and upstream inspection | Verified template baseline and independent Portfolio checkout |
| P1 | P0; CI capacity when needed | Complete Portfolio naming and React selection |
| P2 | P1 | React-only frontend/C# host; Blazor UI/profile removed |
| P3 | P2 | LocalSingleNode-only deployment with preserved shared gates |
| P4 | P2; merge after P3; co-developed with P5 | VS1's first-story content/export/API and Books-domain replacement |
| P5 | Incremental P4 contracts; co-developed with P4 | VS1's Studio home, Technologies page and ImprovedDb reader with Techs |
| P6 | VS1 verified; source preparation may begin earlier | Repeatable full story slices and reviewed launch set |
| P7 | P7.1/P7.3 begin within VS1; final P7.4 requires reviewed launch set | Per-slice prerender/acceptance, runtime alignment and final release readiness |
| P8 | P0 identity; latest P3/P7 for installation/deploy | Native node, runner, LAN readiness and controller SSH |
| P9 | P7, P8 and recorded launch authorization | Cloudflare publication and public acceptance |
| P10 | P9; remaining P6 packets | Recovery, authoring handover and final backlog disposition |

Source/media preparation in P6 can happen before P5. P8's access/runner-capacity work may be brought forward immediately after P0 when needed for CI. This is an ordering exception for infrastructure prerequisites, not permission to deploy incomplete product changes.

## P0 — Verify React delivery and seed Portfolio

### P0.1 — Select the upstream baseline

Inputs: current upstream React goal/profile plan, live upstream main and main CI.

- Fetch upstream and inspect the other agent's progress, open PRs and unresolved handoffs.
- Verify merged React Router/Vite/Tailwind foundation, generated API contracts, local HTTPS development, static C# serving, image/release profile labels, CI checks, LocalSingleNode setup and controller/public runbooks.
- Record upstream SHA, CI run URL, dependency/lockfile versions and any still-required open fixes in the ledger.
- Verify retained P0–P7 foundation and live SR1–SR6 delivery. The retired repository cleanup is complete, but public React delivery remains unfinished. Prefer completed reusable delivery; classify missing merged release/setup capabilities as dependencies and remaining demo observation as independent only with evidence. Do not recreate the retired repository or claim cancelled method equals completed delivery.
- Pin that SHA. Recheck once more before import if another upstream fix lands. Do not repeatedly chase main without a concrete needed fix.

Exit: one reproducible merged baseline with successful main CI; unresolved dependencies classified as blocking or independent. Planning checkpoint SHAs are evidence of inspection, not a mandatory baseline.

### P0.2 — Import into the supplied destination

Inputs: P0.1, current remote Portfolio state and private operator intent.

- Destination is `Grumlebob/Portfolio`; use the requested sibling checkout named `Portfolio`.
- Verify repository permissions, contents, visibility, Actions settings and branch protection. Do not create a differently named repository.
- For an empty destination, disable Actions before copying workflows. Clone template history at the selected commit and configure `origin` to Portfolio, `upstream` to the template. Before its first push, make a small seed configuration commit: select React, set app slug/internal identity to `portfolio`, set the Common image to `ghcr.io/grumlebob/portfolio`, align required temporary multi-target identity reads, and select only LocalSingleNode. Keep original project paths until P1. Record the pristine upstream SHA and this seed delta separately.
- Run the inherited applicable local gate for that seed configuration, then push the initial `main` once. This initial import has no downstream PR base; all subsequent changes use PRs. Do not include ignored files or unrelated dirty work. Never enable publishing or bootstrap using the inherited template app/image identity: this owner also owns the template package, so an owner-only fork check is insufficient.
- Record original upstream SHA and repository URL in a downstream origin record. Preserve history/license/attribution. This is an independent product clone, not a requirement to create a GitHub fork relationship.
- Copy this master plan and all companions into Portfolio. Privately copy the operator intent and useful source-location notes. The downstream copy becomes the execution authority.
- Verify the configured React seed locally before destructive cleanup. Keep upstream frontend/target support intact. Initial bootstrap may use the original project/target code, but its app/image/runner identity is already Portfolio.
- Inventory inherited workflow triggers/secrets first. Enable Actions only after runner routing, required checks and identity are safe. Provision CI capacity through P8.1–P8.2 if necessary.

Exit: own clean checkout/remotes, baseline provenance, downstream plans, no accidental workflow dispatch, and a viable route to PR CI. Any preexisting Portfolio changes are preserved.

### P0.3 — Preserve design/source handover

- Copy selected Studio reference screenshots into `docs/design/studio/` in Portfolio: home/project, mobile/desktop, both themes.
- Recover reference assets from the local approved mockup if available. If unavailable, use the master design contract and report the missing visual package; never silently select a different style.
- Preserve image licenses/provenance and a concise design decision record. Exclude abandoned mockups, review controls, server logs and embedded prototype application code.
- Translate local source locations into a private source map. Keep the public source register and factual limitations portable.

Exit: a future agent can implement the selected Studio layout from the downstream repository and private source note.

## P1 — Rename the product completely

### P1.1 — Inventory and rename projects

Inputs: P0 baseline; functioning CI capacity or documented P8 bootstrap path.

Use a rename map before editing. Required destinations are:

| Existing identity | Portfolio identity |
| --- | --- |
| Solution | `Portfolio.sln` |
| C# web host | `Portfolio/Portfolio.csproj`, assembly/root namespace `Portfolio` |
| Shared contracts/core | `Portfolio.Core` |
| Tests | `Portfolio.Test` |
| React package | `Portfolio.React`; package name `portfolio-react` |
| Temporary simulation/client projects still needed by the baseline | Rename consistently, then remove through P2/P4 if unused |
| Display product | `Portfolio`; site branding remains `Jacob Grum` |
| Internal app identity/deployment slug | `portfolio` |
| Container image | `ghcr.io/grumlebob/portfolio` |

Update solution entries, project references, namespaces, assembly/resource names, root namespaces, `InternalsVisibleTo`, reflection assertions, EF tooling, Docker build contexts/stages, Compose, launch profiles, IDE configuration, scripts, CI working directories, coverage/browser report paths, generated-schema tooling, package scripts, `.gitignore`, docs and product settings. Preserve source URLs/case-study names and upstream attribution; do not globally replace historical evidence.

Regenerate generated API artifacts through their real command. Do not hand-edit generated declarations. Confirm renamed paths work on Linux, including case-sensitive imports and asset paths.

### P1.2 — Align release/deployment identity

- Update common release settings, migration-bundle identity if retained, image labels, repository links and selected frontend profile.
- Configure app/data/backup/runner resource names consistently from `portfolio`. Native facts, ports and secrets remain private/detected; collision checks select actual available values.
- Keep Data Protection and cache isolation coherent while their services remain. Do not reuse another app's keys/data/volumes.
- Search for the old template name; classify every remainder as historical attribution, project evidence or a bug. Operational commands must use Portfolio paths.

Exit evidence: renamed solution format/build/tests, React install/typecheck/build, publish/image smoke, current contract checks, working local commands and no active dependency on old project paths. Update test result expectations from actual discovery; explain every removed/changed test rather than decrementing counts blindly.

## P2 — Remove Blazor and inactive account UI

### P2.1 — Remove the frontend/profile branches

- Inventory Razor pages/components, `.Client` project, WebAssembly/Razor packages, `_framework`/`_content` assets, Blazor boot scripts, CSS build, hydration/render-mode code and profile-switch branches.
- Keep a single React frontend. Remove the Blazor client/UI projects and dependencies from solution, host, Docker, npm scripts, local launch, CI and image stages.
- Simplify profile configuration to React-only while retaining the frontend/acceptance manifest interface used by deployment. Unsupported `BlazorAuto` selection fails clearly; it must not activate leftover components.
- Move any genuinely shared contracts/helpers out of the deleted client before deletion. Move test-only axe/browser assets to the React/test dependency path.
- Remove obsolete Razor/Tailwind output rules and tests. Replace hosting tests with React/Portfolio reserved routes, assets, errors and security assertions.

### P2.2 — Remove unused account frontend services

- Remove account/register/login components, UI session bootstrap, mail/social-login/passkey/recovery services used only by removed account flows.
- Inventory backend Identity/storage dependencies before removing them. Complete domain/storage cleanup in P4/P7; keep the temporary service graph buildable between packets.
- Preserve HTTPS/security headers, request limits, diagnostics and safe routing. A deleted route must not fall through to a public HTML document.
- Rewrite frontend/product requirements and `AGENTS.md` so future agents are not told to regenerate deleted Blazor CSS or validate an unsupported profile.

Exit evidence: final React publish contains no WASM, Blazor component assemblies or framework boot assets; no Razor/Blazor product code is built; local development, production publish and tests use React/C#; obsolete profile checks are replaced with useful assertions.

## P3 — Remove Cloud and LocalCluster deployment targets

Follow the inherited [single-node-only clone guide](../../../Deployment/LocalSingleNode/SingleNodeOnlyClone.md) before removing its upstream references from downstream documentation.

### P3.1 — Inventory and move shared dependencies first

Search workflows, scripts, tests, docs, settings and build files for `Deployment/Cloud`, `Deployment/LocalCluster`, target selectors and cluster-specific environment/runner inputs. Create a file-by-file keep/move/delete table in the PR.

Current known traps to inspect against the actual baseline:

- CI audit/render entry points, Python audit library and script tests under LocalCluster.
- Docker smoke scripts, cleanup traps, Compose helpers and common image-name reads from cluster settings.
- Common release provenance, migration artifacts, runner prerequisites and deployment locks.
- Shared Caddy/Cloudflare/backup roles used by LocalSingleNode.
- Local gates, deployment chooser/fork guide, `AGENTS.md`, optional observability and acceptance scripts.

Move reusable checks/helpers into `Deployment/Common` or LocalSingleNode with updated imports/tests/callers. Choose and record canonical downstream audit/render/smoke commands, for example `Deployment/Common/Scripts/audit-deployment.sh`; these are proposed destinations until implemented. Test the relocated entry points before deleting the old directories.

### P3.2 — Delete unsupported targets and close references

- Remove Cloud and LocalCluster directories and their target-specific workflows, provisioning, inventory examples, maintenance tasks and obsolete docs.
- Keep LocalSingleNode, required Common roles/helpers, Cloudflare tunnel publication and shared lock tooling. Cloudflare is the single-node public connector, not the removed Cloud deployment target.
- Support only `DEPLOY_TARGETS=localsinglenode`. Unknown/removed targets fail clearly; no fallback to cluster settings.
- Update workflow filters, local gate, audits, script tests, smoke checks, fork/deployment instructions and repository rules together.
- Replace old audit rules with the new supported behavior. Preserve checks for ownership, host identity, secrets, release provenance, locks, backups and public acceptance.
- Remove stale target references in active plans/runbooks; clearly marked historical source context may remain. Copying an old template plan does not make its commands valid downstream.

Exit evidence: neither removed directory exists; no active workflow/script imports it; required CI and local gates execute from retained paths; one-node setup/public/update/backup/restore commands remain documented and tested. No live deployment is changed by this cleanup.

**C1:** once all VS0 exits and required early access/CI prerequisites are verified, recommend a fresh chat for VS1 using the saved handoff.

## P4 — Implement portfolio content and replace Books

### P4.1 — Canonical authoring model and exporter

Inputs: P2; master sections 4–5; source register.

- Create `Content/Portfolio/site.json`, per-project metadata/Markdown/media and a draft starter. Begin with ImprovedDb's actual story; other catalog entries remain draft metadata until their slice is prepared.
- Implement ContentTool/C# validation/export and DTOs for site, summary/detail, sections, blocks, assets, technology registry/catalog and published manifest. Validate source-supported `technologyIds`, synthesize Techs and derive the categorized overview from published projects only. Use ExecutionDecisions' Markdig, safe HTML, media-plan and CLI defaults.
- Produce deterministic public-only normalized output and a content revision. No DB/Redis/network/credentials are required for export.
- Validate unsafe HTML/links/SVG, path containment/case, missing media, duplicate IDs, internal links to drafts, dimensions, supported block kinds and payload budgets.
- Keep provenance/review notes out of public DTOs. Draft content and media cannot ship merely because they live near published files.

Exit: deterministic export, invalid fixtures rejected, first-story content supported, unpublished projects/media excluded, and a documented real export command. This packet is partial VS1 work until the corresponding API/UI/prerender journey is verified.

### P4.2 — Public API and generated client

- Add `/api/portfolio/site`, `/api/portfolio/projects`, `/api/portfolio/projects/{slug}` and `/api/portfolio/technologies` with public read-only contracts, bounded payloads, ETags and 404 Problem Details. TechnologyCatalog shares the immutable content revision.
- Generate/check OpenAPI and TypeScript through inherited tooling; replace Books query keys/transport/hooks with Portfolio ones.
- Use the same exported bundle for runtime reads and later prerender. Include its schema/revision in compatibility checks.
- Retain loading/empty/offline/throttled/server-error UX and cancellation; permanent 404s do not retry.

Exit: accurate generated types/status metadata, lightweight collection, correct detail/errors and one shared query client.

### P4.3 — Delete sample-domain dependencies

- Remove Books endpoints/contracts/entities/seeding/covers/pages/bookcase/account APIs and sample-only auth/services after checking references.
- Remove or replace Books-specific tests, simulator workloads, dashboard metrics, caches and docs. Retain generic useful infrastructure with new Portfolio assertions.
- Remove login/account configuration, unnecessary secrets and dependency registrations. If an existing schema/service still requires Identity for technical reasons, document the temporary boundary and finish it in P7.2; it is not a portfolio feature.
- Define former Books/account/auth routes as 404, including direct and non-HTML requests. Never expose former private data through frontend fallback.
- Preserve historical Books comparison/source evidence in this planning inventory; it does not belong in the product catalog.
- Do not replay/drop production data. The new app has its own storage identity; any migration reset requires proof that only disposable, app-owned data exists.

Exit: no Books UX/API/simulator in the product; generated schema and runtime dependencies describe Portfolio. Existing security checks are replaced with deletion/denial checks.

## P5 — Build the approved Studio experience

### P5.1 — Home and visual system

- Implement header (`Jacob Grum`, Technologies link and theme switch), `Selected work.`, supporting copy and image-led project grid. Implement `/technologies` as a brief categorized, deduplicated overview with stable anchors and published project links.
- Implement shared tokens/fonts, focus/skip link, one/two-column responsive layout, odd final-card behavior and system/user theme precedence before first paint.
- Read catalog metadata, do not encode project-name conditionals. Cards are real links without nested interactive elements.
- Preserve useful empty/error states and image aspect ratios. Add verified footer links only when available; omit unverified contact details.

### P5.2 — ImprovedDb continuous reader

- Publish a reviewed ImprovedDb bundle using the owner's motivation and six approved sections.
- Implement project intro/cover/actions, reusable prose/figures/gallery/code/quotes and stable section IDs.
- Add desktop sticky rail and mobile disclosure derived from the same sections. Use native anchors, deterministic active tracking, focus/fragment offsets and Back/Forward restoration.
- Implement accessible image enlargement where needed. Theme changes preserve position and never invert source screenshots.

### P5.3 — Visual checkpoint

Review real home/Technologies/ImprovedDb at the required viewport sizes in both themes. Compare with portable Studio references. Verify keyboard navigation, deep fragment reload, final short section, long figure/code sections and 200% text zoom. Record screenshots and actual findings. Correct drift before duplicating content across projects.

Exit: one complete real story, approved layout faithfully implemented and components suitable for different section counts. Finish first-story P7.1/P7.3 hosting/prerender/image acceptance before marking VS1 verified. This checkpoint is review evidence, not a requirement to stop for another style choice.

**C2:** recommend a fresh chat for story production only after the whole VS1 journey, including its first-story P7 work, is verified. P5.3 alone does not trigger this handoff.

## P6 — Prepare the twelve distinct project stories

Use the detailed [page briefs](PageBriefs.md). Each story is a resumable vertical content slice; keep a per-project source/media/publication row in Progress. Its exit includes actual export/API/catalog/detail/prerender/metadata/media and applicable checks together, not merely a Markdown draft. Introduce needed contract/renderer behavior in that same story slice. P6.1's initial publication requirements are part of VS1.

| Packet | Story | Required output |
| --- | --- | --- |
| P6.1 | ImprovedDb | Final sourced ratings/data/statistics/ML explanation, selected real captures, six-section story |
| P6.2 | KinoJoin | Synthetic cinema-event journey, preference/result capture and domain/calendar diagram |
| P6.3 | TraceBack | Research-prototype workflow, synthetic run context and references/snapshots boundary figure |
| P6.4 | Unlost | Recovered Java source reconciled with historical map/search/pathfinding report and genuine figures; no runtime claim from import alone |
| P6.5 | Ship Inspections | Synthetic vessel/part/image journey, real upload states and sourced TUS flow |
| P6.6 | MiniTwit | Historical evolution/DevOps narrative with architecture, delivery and useful operational figure |
| P6.7 | BestBets | Owner-selected Exam PDF/deck reviewed against repository evidence; architecture views and targets-versus-results figure |
| P6.8 | Geospatial research | Attributed genuine maps/plots, data/methods and findings with limitations |
| P6.9 | GeckoBot | Selected private GeckoBot source/requirements and historical-use review; fictional Outlook booking/email examples and accurate UI/parser story; deleted demo retained only in private backup |
| P6.10 | Grumlebob | Free online offers/passive income; owner-reported DKK 500,000 profit in one year and member capacity due to concern about being caught; generic figures, private details excluded |
| P6.11 | JobHunt | Eight-step responsibility figure, factual writing boundary and fictional administrative examples |
| P6.13 | Template | Lighthouse, SonarQube, Qlty, Trivy, ZAP, sitespeed.io, scc; Blazor/React and Cloud/LocalCluster/LocalSingleNode choices, supported by pinned source |
| P6.12 | Catalog review | Stable order, twelve story dispositions, Techs/Technologies consistency, no dangling public cards/links, launch set recorded |

P6.12 retains its existing ID. P6.13 adds Template; final catalog review follows every story's recorded disposition.

For every story, confirm source revision, technology references, individual role, status/context, safe media rights, meaningful caption/alt text, valid outbound links and accurate limitations. Update Techs and Technologies together. A header suggestion is editorial copy, never a source for a factual claim. Related links point only to published stories.

For Grumlebob, the owner's 2026-10-12 public facts are the primary source; attribute profit/capacity statements and protect remaining restricted context. Restricted code inspection is not an exit gate. Do not fabricate another use case. For GeckoBot, private source access does not authorize publishing real employee/customer/email/calendar data or a private repository button.

Recommended first launch set: ImprovedDb, KinoJoin, TraceBack, Unlost. Do not publish incomplete cards to meet a count. Continue later packets independently. Owner-approved deferrals must be recorded before full-plan completion.

## P7 — Public rendering and operational readiness

### P7.1 — Prerender and exact C# hosting

Begin this packet within VS1 for home, Technologies and ImprovedDb, then extend known routes/generated output in each P6 story slice. It is not deferred until all stories are written.

- Use the pinned Router version's supported prerendering with `ssr:false`, explicit published routes and snapshot loaders. Verify version-specific APIs rather than upgrading to match current examples.
- Build content first, then contracts/frontend, then package the exact bundle and generated HTML/navigation data in the C# image. Production has no Node process.
- Serve correct documents/data for home and known slugs. Reject missing assets/data, unknown/draft routes and reserved paths with real statuses; do not return a generic shell everywhere.
- Generate unique title/description/canonical/social metadata, preview images, sitemap and robots behavior from the same content/settings. Preview environments are unindexed.
- Verify useful project prose/anchors/images without JavaScript, hydration compatibility and no redundant API fetch.
- Record cache/asset retention rules and behavior of an already-open page across releases.

### P7.2 — Complete the file-only runtime

Final default: file-only public content, without PostgreSQL/Redis/Identity/migrations. Keep transitional dependencies until their real consumers are removed; finish this packet before final P7.4 readiness.

Produce a consumer inventory for DB, Redis, Identity, migration, Data Protection, SMTP/social-auth and simulator services. Remove unused services in cohesive PRs covering startup, Compose, health, workflows, release artifacts, backup/doctor/recovery, audits and tests. Explicitly support a file-only release without migration artifacts; never create a dummy empty migration bundle to satisfy an old consumer. Recover content/UI/media from reviewed Git and immutable release evidence, and retain protected app/provider configuration through its owned operations. Do not claim a database backup protects file-only content. Any newly demonstrated product requirement to retain a service needs a documented revision to D06 and matching operations; inherited checks alone are not justification.

### P7.3 — Replace sample acceptance with Portfolio acceptance

Introduce the first-story profile/assertions within VS1. Expand the manifest-driven acceptance with later published slices and complete final launch checks in P7.4.

- Introduce the selected `PortfolioPublicV1` acceptance profile; preserve `FrontendProfile=React`.
- Update resolver, build/image labels, release manifest, Docker smoke, setup-state machine, deployment workflow and controller acceptance together.
- Check site metadata, ordered summaries, a known real project and sections, matching content revision, direct/deep/fragment URLs, missing/draft routes, assets/data, former sample/account denial and security/cache headers.
- Keep GET/HEAD acceptance read-only. Do not create accounts or use synthetic Books data to make the check pass.
- Replace inherited hard-coded sample test counts with reviewed actual suite expectations. Test discovery/failures/skips must remain enforced.

### P7.4 — Release-readiness evidence

Run current downstream local gate, applicable React/content/script checks, production image smoke, browser/accessibility/visual checks and documented loading measurements. Reproduce from a fresh checkout. Merge PRs with exact-head required CI; verify main publishing and release SHA/digest/manifest/content revision. Prepare authoring and operations commands with actual paths/options.

Exit: deployable immutable Portfolio release with supported operations and no live dependency on Blazor, Books, Cloud or LocalCluster.

**C3:** when this final readiness exit, VS3 and reviewed launch set are verified, recommend a fresh chat for remaining P8, public launch and recovery/full handover. Save release/authorization/remaining-catalog evidence first. Early P8 prerequisite work is not a separate reset.

## P8 — Establish the native node and controller access

Follow [NodeHandoff.md](NodeHandoff.md). Do not invent a second bootstrap process.

### P8.1 — Native identity and initial checkout

Verify actual Linux Mint/native hostname/address from the private intent. The owner's old/new node labels refer to the intended fresh PC until native evidence establishes its actual identity. If identity differs, return a simple clarification before any privileged mutation; never silently rename or configure another node.

Use the seeded Portfolio repository, authenticated `gh`, and the existing setup-status entry point. Copy the applicable operator instruction into the private setup record. Initial cloning and node-only probes happen there; the Windows controller is never the node.

### P8.2 — Bootstrap and CI capacity

Follow returned actor steps in `AgentSetup.md`. The operator performs authentication and the single returned root command; the agent never runs sudo. Use the documented combined node/CI-runner bootstrap when CI is absent, then resume deferred customization PRs. This prerequisite may happen before P1–P7 finish. If the state machine requires a temporary LAN baseline deployment, describe its sample status and obtain applicable operator authorization; no public launch is implied.

Verify one app-scoped runner, registration scope/labels, Docker/local gate capacity and safe workflow permissions before enabling the inherited Actions. Existing upstream demo runner-reuse authorization does not apply to this fresh Portfolio node.

### P8.3 — LAN readiness and SSH pairing

Complete the persistent controller handoff through the existing `controller-ssh.py` prepare/authorize/configure commands. Verify pinned identity and passwordless native probe; keep private key/address/login out of tracked records. Prefer SSH for later authorized controller work.

Before app deployment, check app-owned resource collisions, capacity, Docker access, locks, current doctor/backup status and immutable Portfolio release. A new app has no rollback predecessor; record that honestly and use reinstall/recovery guidance until its first compatible previous release exists.

Exit: correct native node, runner/privilege setup, verified controller alias, LAN Portfolio acceptance for the selected release and independent main-PC confirmation.

## P9 — Publish portfolio.jacobgrum.com through LocalSingleNode

### P9.1 — Public configuration

Inputs: P7 release, P8 node/LAN evidence, explicit Portfolio launch authorization and protected Cloudflare authentication.

- Follow retained `PublicSetup.md`; controller handles owned DNS/tunnel configuration and protected credentials.
- Verify target zone/hostname, app-owned tunnel and free loopback origin port. Preserve conflicting/foreign resources; report an actual blocker.
- Keep ownership IDs/state protected/private. Configure repository public variables and encrypted connector token using the existing script.
- Cloudflare publication does not require the removed Cloud deployment target or a LocalCluster.

### P9.2 — Deploy once and accept publicly

- Verify green Portfolio main release, SHA/digest/profile/content manifest and target identity.
- Dispatch only `CD - Deploy LocalSingleNode`. Record its run ID immediately and resume watching that same run if interrupted.
- Verify connector/systemd/Caddy/health, independent LAN and public HTTP acceptance, normal TLS validation and actual browser interactions.
- Public pages must identify Jacob Grum and the reviewed projects; no Books shell, Blazor assets, account UI, authentication wall or Cloudflare challenge interfering with normal visitors.
- Exercise direct story and fragment visits, unknown routes, themes, mobile reading, section navigation, assets/navigation data and release revision.

Exit: valid public HTTPS on the intended product URL; immutable release and actual browser/HTTP evidence recorded. DNS/tunnel creation alone is incomplete.

## P10 — Recovery, continuation and final handover

### P10.1 — Scoped update/recovery

Verify persistence across one scoped app restart. Retain runner/connector/health checks. Prove recovery for the services actually retained. After a second compatible release exists, demonstrate rollback using a recorded previous SHA/digest with matching content/assets; do not destroy data or remove locks. Record first-release limitations until this evidence exists.

### P10.2 — Repeatable authoring and full backlog

Write fresh-clone/local-run/content-add/build/release/update/backup/restore instructions using implemented commands. Complete remaining P6 stories or obtain explicit owner deferrals. Recheck all public links, captions, factual dates and contribution statements. Record launch set separately from the twelve-project disposition.

### P10.3 — Close the delivery

Verify every required packet's merge/main evidence, public release/URL and operations evidence. Update the downstream ledger and link it from the retained template plan. Remove obsolete temporary coordination files only after preserving required evidence and checking ownership. Keep private SSH trust/keys, provider ownership state, public setup runbooks and unresolved content inputs.

Completion requires merged green changes, public acceptance and honest disposition of the full catalog. A local screenshot, queued workflow or partially configured node does not complete a packet.
