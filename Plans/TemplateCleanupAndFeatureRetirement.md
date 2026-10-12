# Template cleanup and feature retirement

## Status and purpose

Status: **planned; implementation has not started**. Repository reconnaissance and the planning audits below are complete. Feature retirement decisions remain open in section 10. Those decisions block only their own packets, not the behavior-preserving cleanup.

Create a smaller, easier-to-maintain template by removing proven unused code, unused parameters, obsolete configuration and abandoned assets; simplifying unnecessary branches; and retiring explicitly selected old features as complete vertical changes. Preserve the supported template capabilities unless a recorded owner decision changes them.

This document is an execution runbook for an agent with no previous conversation context. Execute one packet at a time, record evidence, and stop a packet when its proof or checks fail. Do not treat a search result, analyzer warning, low coverage, or lack of recent traffic as permission to delete a feature.

The present request authorizes research and creation of this plan. It does not authorize executing the cleanup, changing a live host, provisioning a node, or dispatching a deployment. A later instruction to execute this plan authorizes its ordinary repository changes, subject to unresolved feature decisions and the repository rules.

## 1. Sources of truth and boundaries

Read these files before execution:

- [AGENTS.md](../AGENTS.md): PR, local gate, exact-head/exact-main verification, shared-host safeguards and explicit-path staging.
- [Requirements.md](../docs/Requirements.md): rendering, API security, caching and runtime requirements.
- [Test.md](../docs/Test.md): complete local gate and focused commands.
- [FrontendProfiles.md](../docs/FrontendProfiles.md): supported profile composition, routes, assets and public/private API boundary.
- [QualityTools.md](../docs/Quality/QualityTools.md) and [SonarQubeAnalysis.md](../docs/Quality/SonarQubeAnalysis.md): existing optional audits and their limits.
- [CodeQualityImprovements.md](CodeQualityImprovements.md): previously reviewed Q-001 through Q-008. Reuse their evidence; do not create conflicting implementations or silently broaden their scope.
- [Deployment/README.md](../Deployment/README.md) and [Deployment/Common/README.md](../Deployment/Common/README.md): deployment targets and release contracts.

The default supported surface is:

| Surface | Default contract for this cleanup |
| --- | --- |
| BlazorAuto | Preserve SSR, `InteractiveAuto`, WebAssembly hydration, reconnect behavior, public author books, authenticated user books and account flows. |
| React | Preserve the account-free public SPA, direct navigation, API contracts, security headers and denial of protected APIs. |
| Shared backend | Preserve PostgreSQL, Identity storage, Redis requirements, Data Protection, rate limiting, health checks and public/private response behavior. |
| Deployment | Preserve LocalSingleNode, LocalCluster and Cloud, digest-pinned releases, migration provenance, scoped maintenance and backups. An unused target in the owner's current installation is still a supported template target. |
| Operator tooling | Preserve local running, Lighthouse, public browser checks, simulation, optional source audits and their documented command interfaces. |
| Downstream work | Preserve Portfolio planning and active React delivery records. The Portfolio plan is for another product; its database-free final runtime does not authorize removing this template's database or Identity. |

Do not upgrade packages, rename the solution, redesign the bookcase, replace frameworks, squash EF migrations, rewrite Git history, or add a new mandatory analyzer as part of this cleanup. A genuine defect discovered during cleanup needs a separately described behavioral fix and appropriate tests.

## 2. Research completed before implementation

### 2.1 Source checkpoint

Research date: **2026-10-12**. Inspected commit: **`de90f08d962d4789f4e55e19ddd15aed780b0882`**. `origin/main` was fetched and matched that commit. The checkout was clean when the audits started; the selected profile was `BlazorAuto`. These are historical observations, not a requirement to execute against this old commit.

There were **862 tracked files**. The largest areas were `Deployment` (363), the host (127), tests (74), scripts (60), the Blazor client (53), React (43), simulation (35), retained plans (32), and Core (21). Counts include configuration and documentation. File count is an inventory measure, not a cleanup target.

Completed grunt work:

1. Read the working rules, requirements, testing guide, profile composition and existing quality backlog.
2. Inventoried tracked files, central package references, lexical type references and Razor parameters that are not read in their declaring file.
3. Ran the existing native Qlty audit against clean tracked source.
4. Ran the existing Quick C# analyzer audit sequentially for both profiles. Both analyzer builds succeeded; the wrapper restored the normal selected-profile NuGet graph afterward.
5. Inspected concrete candidate callers, book routes, HEAD mappings, configuration binding, seeding behavior and duplicated deployment validators.

Private, ignored evidence in the original research checkout:

- `Plans.local/TemplateCleanup/static-inventory.json`.
- `TestResults/QualityTools/20261012-102050-2b7d60ba/summary.json`, `metrics.txt` and `qlty.sarif`.
- `artifacts/quality/quick/quick-20261012T102056Z-de90f08d962d-21ddc461/`, with summaries and SARIF for each profile.

These reports are conveniences, not prerequisites for another clone. Reproduce the relevant reports with the commands in section 8 when missing. Keep raw reports ignored; record portable, reviewed findings here or in PR descriptions. Do not copy private paths, tokens, secrets or entire scan output into tracked documents.

### 2.2 Audit observations and limits

Qlty **0.653.0** completed in **5.14 seconds**. It reported **125 locations** and **five duplication groups**. The group pairs included deployment settings, their validator entry points, two audit sections, simulation duration/integer parsing, and update/delete endpoint handling. These are review prompts, not 125 defects or five required extractions.

Quick **SonarAnalyzer.CSharp 10.35.0.4138** succeeded for both profiles. Production findings were **86 for BlazorAuto** and **79 for React**, with **90 test findings per profile**. Do not add the counts: much source is shared. This was an analyzer build, not a test run, a trusted Full SonarQube baseline, a browser acceptance run, or deployment verification. A React solution build can still analyze the client project; profile-specific report presence does not prove that code ships in the React host.

No central NuGet `PackageVersion` lacked a corresponding `PackageReference`. The lexical scan found no standalone production type that was proven dead. Its one-occurrence type names were mostly extension classes or the design-time EF factory, which have indirect callers. There is no justification for bulk package or class deletion.

### 2.3 Initial candidate register

Line numbers below refer to the research checkpoint. Find symbols again after rebasing.

| ID | Evidence and location | Classification and intended disposition |
| --- | --- | --- |
| C-01 | `BookSideView.razor:19` declares `Url` without reading it. `BookcaseShelf.razor:50,58` pass `book.Url`. | Proven unused component input. Remove the input and both attribute assignments. Preserve book URLs in models and the details/site-link flow. Packet P04. |
| C-02 | `BookPageView.razor:152`: `DeleteControlX` returns `372` on both sides of a condition. | Proven redundant branch. Replace it with the same constant result, preserving SVG placement. Packet P05. |
| C-03 | `BooksEndpoints.cs:209`: `WithAuthorizationResponses` returns a builder ignored by its current callers (`S3241`). | Narrow helper candidate. Inspect every call before changing its return type; preserve all endpoint metadata and authorization. Packet P06. |
| C-04 | `FrontendComposition.React.cs` accepts `configuration` but does not use it; `FrontendComposition.BlazorAuto.cs` needs the same argument. The Blazor static-files hook is intentionally empty. | Shared compile-time composition contract, not automatic dead code. Keep paired signatures unless a complete, simpler replacement is demonstrated. Packet P07. |
| C-05 | `BookSideView.ForcedOpen` is implemented, but inspected shelf callers do not set it. Demos pass `ForcedOpen` directly through `BookDesignDemoCover` to `BookCoverRenderer`. | Unused option candidate, not an unused implementation. Search all consumers before removing only the outer option. Packet P04. |
| C-06 | Root `grumlebet_gb_clean_smooth_v2.svg` is 144,015 bytes. Tracked text search found no filename reference; Git history records a logo commit. It is outside both frontend asset roots. | Likely abandoned source artifact. Check build inputs, documentation and planning references before removal; if still a deliberate design reference, retain and describe it. Packet P09. |
| C-07 | `/books/design-demos` and `/books/design-demos/{DesignId}` have live route components, navigation links and HEAD mappings. | Active feature, not dead code. Owner decision required to retire it. Keep shared cover rendering and designs. Packet P13. |
| C-08 | `Routes/Create.razor`, `Details.razor`, `Edit.razor` redirect old URLs into the modal query flow. `BooksE2ETests` still visits `/books/99999999`. | Live compatibility behavior. Decide retention or retirement before removal. Packet P14. |
| C-09 | README describes `Books:SeedLocalDefaults`; source reads `AuthorBooks:SeedAtStartup` with a default of `true` in `AuthorBookSeedExtensions`. | Confirmed documentation drift. Correct docs to actual behavior; changing seed defaults is a separate product change. Packet P10. |
| C-10 | React's `isbot` has no app import, but `FrontendProfiles.md` documents its React Router type-generation/prerender tooling role. | Retain unless framework-tool execution proves it unnecessary. App-import search alone is insufficient. Packet P08. |
| C-11 | Quick `S1144` flags `Login.InputModel.Passkey` and nested `AppOpenTelemetryOptions` setters. Those models are form/configuration-bound. | False-positive risk. Preserve setters and prove binding behavior; do not remove them to reduce warnings. Packets P03/P12. |
| C-12 | Quick flags empty assembly markers, `BooksEndpointLogCategory` and public partial `Program`. | Indirectly used identities: architecture/assembly discovery, typed logging and `WebApplicationFactory<Program>`. Retain unless all consumers are deliberately replaced. Packet P03. |
| C-13 | Cancellation catches in `AuthorBookcaseState`, `UserBookcaseState` and `BookModalHost`; nested conditions/static candidates in `BookPageView`. | Review lifecycle semantics first. Removing a catch can change navigation or disposal behavior. Packet P11. |
| C-14 | Qlty settings duplication at `cloud_settings.py:154–168` and `deploy_settings.py:150–164`; matching validator entry-point setup. Existing backlog Q-007. | Candidate for narrow shared validation functions, with target-specific contracts preserved. Packet P18. |
| C-15 | `audit_deployment.py` leads Qlty's complexity ranking. The collision preflight, release validators and simulation options also rank highly. | Complexity is not proof of dead checks. Split only where equivalent rejection behavior can be demonstrated. Packets P17–P20. |
| C-16 | `RedisConfigurationTests.Production_AllowsMissingRedis_WhenFallbackIsExplicitlyAllowed` only accesses `factory.Services`. Existing Q-006 requests actual fallback assertions. | Improve the existing meaningful test before touching Redis registration. Packet P15. |

## 3. Rules for proving a removal

Before deleting or narrowing any symbol, file, configuration key or dependency, record:

1. Its declaration and intended responsibility.
2. Direct callers in production, tests, scripts and documentation, using tracked files rather than ignored backup copies.
3. Indirect consumers: Razor routes/attributes, DI registrations, reflection, configuration/form binding, serialization, EF discovery, assembly markers, static asset manifests, CSS-generated classes, workflow dispatch, CLI entry points and framework tools.
4. Which frontend profiles and deployment targets can reach it.
5. Whether it is externally observable: URL, JSON field, environment variable, CLI argument, exit code, dashboard series, deployment setting or database shape.
6. The resulting behavior and a focused verification that distinguishes the old risk from the new behavior.

Use `git grep` or `rg` restricted to tracked source areas. A filename can be generated, a class can be reached through its extension methods, and a setting may come only from environment variables. Zero text matches is a candidate, not a proof.

Use these dispositions in the execution ledger: **remove**, **simplify**, **retain with reason**, **needs owner decision**, or **separate defect**. Every reviewed candidate gets one. A packet is complete when its disposition is justified and verified, even if retaining the code is the correct result.

Never remove migrations or the model snapshot because they have no normal callers. Never remove `CancellationToken`, route/form/query parameters, serialized fields or configuration setters merely because a lexical analyzer misses their consumers. Never make private APIs public or remove Redis/security checks to simplify a profile.

## 4. Execution and handoff protocol

### 4.1 Start and resume

1. Fetch `origin/main`, read this plan and the current working rules, and inspect `git status` before edits.
2. Preserve unrelated dirty work. Use a clean, separate worktree when necessary; do not stash, reset or overwrite another person's files. Observe applicable worktree task-binding rules.
3. Check active PRs and retained React/Portfolio/quality plan status before claiming files. Coordinate overlapping work by rebasing or deferring the overlapping packet, not by overwriting it.
4. Create a cleanup branch from current `origin/main`. Record its input SHA and claimed paths in section 9.
5. Choose the earliest uncompleted packet whose dependencies and decisions are satisfied. Do not execute decision-dependent retirements by guessing an answer.
6. Read the packet's named files completely before changing them. Revalidate research candidates against the current source.

### 4.2 One packet's completion cycle

For each packet: establish the before behavior, make the smallest coherent change, update directly affected tests/docs/generated outputs, run focused checks, review the full diff, then run the required local gate before pushing. Stage explicit paths. Create a PR with the concrete behavior and validation results.

Code/configuration PRs require green `build-test-push` on the **exact PR head** before merging. After merge, fetch the integrated commit and require green **exact-main CI** for that commit before marking the code packet complete. Do not substitute another commit's green run. Record the merge commit, check URLs and dispositions in section 9 or the linked PR description.

Ordinary Markdown-only PRs use the repository documentation exception: complete diff review, `git diff --check`, `[skip ci]` in the documentation commit and squash title, a PR, then fetched integrated-content verification on `origin/main`. Do not wait for CI or run builds for a purely documentation change. A PR that deletes an SVG or HTML file is not documentation-only, even if the file is unused.

Do not dispatch CD to establish completion of a repository cleanup. Live acceptance can be a separate, explicitly authorized follow-up if necessary. Preserve deploy locks, volumes, backups, scoped ownership checks and release provenance.

### 4.3 PR size and order

Suggested waves:

| Wave | Packets | Purpose |
| --- | --- | --- |
| A | P00–P03 | Establish scope, baseline and removal proof. |
| B | P04–P07 | Small, behavior-preserving client/server cleanup. Prefer separate client and backend PRs. |
| C | P08–P11 | Dependencies, assets, configuration/docs and lifecycle review. Split non-Markdown work from independent docs. |
| D | P12–P14 | Selected feature retirements, each in its own PR after its decision. Skip retirements explicitly rejected by the owner. |
| E | P15–P17 | Cache/hosting and simulation cleanup with focused risk tests. |
| F | P18–P21 | Deployment helpers, audit structure and CI/tooling. Keep shared-validator and audit changes separate. |
| G | P22–P24 | Documentation closure, re-audit and integrated verification. |

Do not combine all waves into one large PR. A packet with no justified changes needs only an evidence-backed retention entry, not an empty PR. Do not make extraction/refactoring a condition of completion when duplication is clearer than a generic abstraction.

## 5. Ordered implementation packets

### P00 — Resolve the scope contract

Dependencies: none. Inputs: sections 1, 2 and 10; current requirements and active plans.

1. Confirm the default support matrix in section 1 against the latest repository.
2. Record owner answers for design demos, compatibility URLs and optional Identity features. Use a separate decision entry for each feature.
3. Mark unapproved retirements blocked; continue behavior-preserving packets.
4. Identify shared files owned by active React delivery or Portfolio planning. Avoid importing downstream product removals into the template.

Verification and exit: every potentially breaking removal has a recorded decision, and all other behavior remains covered by the default contract. Do not mark an unanswered decision as approval.

### P01 — Capture a trustworthy execution baseline

Dependencies: P00 for scope; unanswered retirement questions do not block this packet. Inputs: `docs/Test.md`, `.github/workflows/ci.yml`, profile gate and current package/configuration files.

1. Record current `origin/main`, selected profile, clean/dirty status and available local tools without printing secrets.
2. Run the existing complete local gate from `docs/Test.md` and React package checks. Keep restore/build/test sequential across profiles in this checkout.
3. Save TRX, React test results and relevant logs in ignored result directories. Record actual counts and failures. At the research checkpoint the expected ordinary counts were BlazorAuto **211 passed/13 opt-in skips**, React **203 passed/13 opt-in skips**, lifecycle **3 passed/0 skips**, React unit tests **31 passed/0 skips**.
4. If current `main` fails, distinguish a pre-existing failure from a cleanup regression. Resolve or explicitly isolate the cause before using that area as a deletion baseline. Do not lower counts or introduce skips to obtain green results.

Verification and exit: baseline status is known for both profiles and the deployment/script gate. The planning Quick audit is not a substitute. Document unavailable environment checks according to `docs/Test.md`; still run all checks that can run.

### P02 — Build the complete disposition inventory

Dependencies: P01. Inputs: tracked files, current routes, DI composition, project files, workflow/script entry points and section 2 candidates.

1. Enumerate `git ls-files`; classify every tracked production source/configuration/asset path by owning subsystem. Classify tests and documentation by the behavior they protect or describe. Batch only independent searches.
2. Create an ignored detailed inventory and a portable summary linked from the PR. For each candidate include declaration, callers, indirect consumers, profile/target reachability, external contract, risk, disposition and packet.
3. Inventory routes from Razor `@page`, React route configuration, endpoint mappings and HEAD mappings. Include redirects, catch-all navigation and reserved paths.
4. Inventory direct NuGet/npm packages and framework tooling; configuration keys and environment aliases; script/workflow entry points; CSS selectors and JS modules; public DTO fields and EF entities.
5. Refresh Qlty and Quick analyzer reports only if the source changed materially since the recorded research. Deduplicate shared findings and review test findings separately.

Verification and exit: every source area is classified. Unproven candidates remain retained or explicitly pending. The inventory does not label ignored `Plans.local`, `node_modules`, test output or build artifacts as tracked dead code.

### P03 — Remove proven C# leftovers and reject false positives

Dependencies: P02. Inputs: Quick SARIF, host/Core/client/simulation C# files and architecture tests.

1. Review unused usings, private fields, private methods, locals and unreachable branches one file at a time. Follow partial classes and Razor-generated consumers.
2. Preserve configuration/form-bound models, assembly markers, typed logging category classes, `Program`, the design-time EF factory and extension classes unless a complete replacement is required for another approved change.
3. Inspect all `S1144` locations before accepting them. Confirm that `AppOpenTelemetryOptions` is loaded by configuration binding and `Login.InputModel` is populated by form binding. Record these retention reasons.
4. Apply narrow fixes only. Do not run broad automatic analyzer fixes or suppress rules/exclude production files to reduce the report.

Verification and exit: compile both profiles, run applicable architecture/composition tests and the focused affected behavior. Every warning considered has a disposition; no required binding or discovery surface is removed.

### P04 — Remove unused Razor inputs and unnecessary options

Dependencies: P03. Inputs: `BookSideView.razor`, `BookcaseShelf.razor`, cover components and all component callers.

1. Reconfirm that `BookSideView.Url` is not read by markup, code, a partial file or a derived component.
2. Remove only that `[Parameter]` property and both `Url="@book.Url"` assignments in `BookcaseShelf`. Preserve `BookcaseBook.Url`, API URL fields, URL validation and links in book details.
3. Search all `BookSideView` usages for `ForcedOpen`. If no supported consumer sets it and no extension contract requires it, remove the unused outer option and its forwarding attribute. Preserve `BookCoverRenderer.ForcedOpen` and demo consumers if demos are retained.
4. Review other component inputs, injected services and callbacks using the same proof. Do not remove values used by binding, events, accessibility text, prerender state or routing.
5. Rebuild Tailwind after Razor changes as required by `AGENTS.md`; commit generated CSS if it changes.

Verification and exit: both profiles build; geometry/shelf tests pass; the Blazor shelf still opens the right book and site links still work in details. Use existing relevant browser journeys, not new tests that merely assert a property was deleted.

### P05 — Simplify book view branches without changing geometry

Dependencies: P04. Inputs: `BookPageView.razor`, layout/geometry helpers and existing Books browser tests.

1. Replace `DeleteControlX`'s identical `372` branches with the same constant result.
2. Inspect adjacent nested expressions and static-helper suggestions. Preserve all close/edit/delete/site control positions for each supported state.
3. Preserve HTML encoding in SVG text markup, keyboard event handling, accessibility names, renderer interactivity guards and title/author truncation.
4. Avoid merging `BookPageTextLayout` and `BookCoverTextLayout` merely because both wrap text; they have different visual constraints.

Verification and exit: geometry tests and targeted Books browser states pass at narrow and wide widths. Compare the existing visual artifacts for view-only, editable and deletable books. Generate only the screenshots needed to verify this change.

### P06 — Clean endpoint helpers while preserving contracts

Dependencies: P03. Inputs: both Books endpoint files, Core request/response types, metadata tests and feature API tests.

1. Inspect every `WithAuthorizationResponses` caller. If its return is always ignored, change the private helper to `void` with the same three builder calls. Otherwise retain the fluent return and record the consumer.
2. Review duplicated update/delete outcome code. Extract only if the result is shorter and preserves typed results, operation names and independent endpoint metadata; leaving clear duplication is acceptable.
3. Preserve route/body ID mismatch rejection, ownership filtering, 401/403/404/429 behavior, validation payloads, `private, no-store`, telemetry and cancellation propagation.
4. Do not merge public author-book contracts with authenticated user-book contracts or rename serialized fields as cleanup.

Verification and exit: feature API tests, `EndpointSurfaceTests`, `OpenApiMetadataTests`, caching tests and React `api:check` pass. Any intentional schema change must regenerate and review both schema outputs; otherwise generated API files remain unchanged.

### P07 — Review frontend composition and unused hook arguments

Dependencies: P06. Inputs: both `FrontendComposition` implementations, `Program.cs`, host project conditions and hosting tests.

1. Document the shared method signatures compiled under each profile. The React configuration argument and Blazor empty static-files hook are currently deliberate symmetry.
2. Retain that symmetry unless an alternative actually reduces total code and conditional complexity. Do not remove an argument in one implementation and leave the shared call broken.
3. Review unused hosting options against all configuration sources and tests. Keep catch-all route values used by framework route selection even when no handler reads their name.
4. Preserve profile-specific authentication/UI registration, middleware ordering, error handling, GET/HEAD behavior, response headers and publish-output cleanup.

Verification and exit: composition, React hosting, response behavior, HEAD, app-asset and render-mode tests pass. Publish both profiles sequentially to one disposable directory and verify that each switch clears the other profile's assets, as described in `docs/Test.md`.

### P08 — Audit dependencies and React source

Dependencies: P02/P07. Inputs: all project files, central versions, both npm manifests/lockfiles, React config and scripts.

1. Match every direct package to runtime code, configuration-loaded features, tests or build tooling. Central NuGet references were complete at research time; rerun the check rather than assuming unused versions exist.
2. Inspect React imports/exports and route modules; generated OpenAPI declarations and React Router route types are generated contracts, not deletion candidates.
3. Keep `isbot` until type generation and static build can be demonstrated without it; its tooling use is documented. Keep accessibility/Lighthouse development dependencies used by scripts and E2E instrumentation.
4. Remove one proven unused direct dependency at a time. Update the corresponding lockfile with the pinned toolchain. Do not hand-edit resolved lockfile trees or upgrade unrelated packages.
5. Keep TypeScript's existing `noUnusedLocals`/`noUnusedParameters`; run normal lint and strict typecheck. Do not add another dependency scanner unless the existing tools leave a concrete gap.

Verification and exit: lockfile installs, API check, typecheck, lint, all React tests and build pass; Blazor Tailwind/Lighthouse/axe tooling still resolves. Both .NET profile restores/builds succeed with the normal graph restored afterward.

### P09 — Remove abandoned assets and stale styles

Dependencies: P02/P04/P08. Inputs: root SVG, frontend asset roots, `app.css`, `input.css`, JS modules and asset tests. Leave demo-only styles until P13 decides the demo policy; remove those styles within that retirement packet.

1. Confirm whether the root logo SVG is a required source/design reference by checking tracked plans, history and build inputs. Delete it only if classified abandoned; otherwise place its purpose in the inventory. Do not copy arbitrary private artwork into the repository.
2. Build a selector-to-consumer inventory. Include dynamic class strings, account pages, reconnect UI, SVG hover/focus states, reduced motion and generated CSS input.
3. Remove proven unused rules in small groups. Remove collocated JS only when every importer and supported route has gone.
4. Regenerate `tailwind.css` through the Client package; never edit generated output directly. Keep the favicon and framework/module asset paths unless consumers are deliberately changed.

Verification and exit: generated CSS is current; asset tests and relevant browser states pass. Validate account, reconnect, modal and reduced-motion states touched by the change. The root SVG deletion requires the full code gate, not the Markdown exception.

### P10 — Reconcile configuration and documentation

Dependencies: P02/P07. Inputs: README, all appsettings examples, `.env.example`, option types, Compose/Ansible templates and seed extensions.

1. Map each setting to its binder or direct read, defaults, environment override and deployment producer. Keep secrets out of output and use synthetic example values.
2. Correct README's obsolete `Books:SeedLocalDefaults` claim to `AuthorBooks:SeedAtStartup` and the source's actual default behavior. Verify both local and deployment seeding paths before wording the replacement.
3. Distinguish public author-book seeding from development-only account seeding. Preserve React public seeds and its disabled account-seed path.
4. Remove a stale documented option when no current reader exists. If a key has external deployments/forks as consumers, record a migration/deprecation decision before changing its name or default.
5. Compare logging configuration with programmatic Serilog setup and audit requirements. Simplify only actual duplication; retain environment enrichment and trace/span correlation.

Verification and exit: options/seeding/observability tests and rendered configuration validators pass for non-Markdown changes. Pure documentation corrections use the docs-only workflow. Documentation matches actual defaults without silently changing them.

### P11 — Review client state and asynchronous cancellation

Dependencies: P04/P05; read existing Q-004 before changing modal behavior. Inputs: both bookcase state classes, modal host/route state and client services.

1. Trace load, cancellation, navigation, stale-response handling, subscription and disposal paths.
2. Explain each empty cancellation catch. Retain intentional canceled-operation handling with a concise purpose comment when useful; do not convert expected cancellation into user-visible errors.
3. Remove redundant state only after identifying all writers, readers and lifecycle transitions. Preserve bounded public prerender state and never persist user-specific response graphs into public payloads.
4. Before a risky modal refactor, add focused behavior coverage for an obsolete response arriving after navigation, close/reopen and cancellation. Cover failed save/delete and ensure a delete targets the selected owned book. Reuse Q-004's design.

Verification and exit: existing route-state tests and focused lifecycle coverage pass; relevant real-browser modal journeys pass under SSR/hydration and interactive navigation. No duplicate requests, stale modal content or disposal errors are introduced.

### P12 — Apply the selected Identity feature policy

Dependencies: recorded Identity decision in P00; P11; Q-003 for retained account-management coverage. Inputs: account pages/shared components/endpoint helpers, registration, Google configuration, Core/private APIs and Identity E2E.

1. Enumerate all account routes and helper endpoints, including passkeys, Google/external login, 2FA, recovery, email confirmation/reset and personal-data export/deletion. Record which remain supported.
2. If the full template Identity surface is retained, remove only proven scaffolding leftovers and stale text. Missing provider credentials, a no-op email sender or low coverage do not prove the associated pages dead.
3. If features are retired, remove each selected feature's pages, menu/login links, endpoint mappings, model helpers, JS, configuration examples, direct packages and tests coherently. Recheck retained features' dependencies before deleting shared token providers or sender services.
4. Preserve login/register/logout, ownership enforcement, antiforgery, cookie challenges, security-stamp revalidation and retained data management. Preserve Identity tables and existing migrations even for React.
5. Ensure removed routes reject requests without a misleading UI or still-active POST endpoint. Define whether they return 404 or another explicitly agreed response before implementation.

Verification and exit: retained Identity browser journeys and API-denial tests pass; removed routes and helper endpoints have appropriate negative coverage. Use framework-supported virtual authenticators or fakes where possible. Real hardware, email accounts and OAuth credentials are not assumed manual prerequisites for repository cleanup.

### P13 — Retain or retire public design demos

Dependencies: recorded demo decision in P00; P09. Inputs: `Features/Books/DesignDemos`, nav menu, HEAD mappings, styles, docs and browser selectors.

1. If retained, record that the routes are live review tooling; trim only proven unused code within them.
2. If retired, delete the two route components and demo-only catalog/cover wrapper after checking their consumers. Remove desktop/mobile menu links and both HEAD mappings from `HeadRequestExtensions`.
3. Preserve `BookCoverDesignCatalog`, `BookCoverRenderer`, `BookCoverArtwork`, `BookCoverPageTabs`, geometry, themes and designs used by normal shelves. Retiring the review pages must not remove normal book artwork.
4. Remove only demo-specific styles, tests and documentation. Rebuild Tailwind. Replace checks that required the pages with checks for their agreed retired response where that contract matters.

Verification and exit: no live navigation or HEAD route advertises a retired page; normal bookcase designs still render; asset/geometry tests and relevant browser checks pass. Direct requests to both retired route patterns behave as agreed.

### P14 — Retain or retire old Books URLs

Dependencies: recorded compatibility decision in P00; P11. Inputs: `Routes/Create.razor`, `Details.razor`, `Edit.razor`, modal URLs, `BooksE2ETests` and route docs.

1. If retained, keep the small authorized redirect components and verify their query mapping. Their only purpose is compatibility, which is still a purpose.
2. If retired, decide the response for `/books/create`, `/books/{id:int}` and `/books/{id:int}/edit` before deleting the components. If the decision is 404, delete all three, remove old links and verify unknown paths reach the normal not-found handling.
3. Update the invalid-book test that currently visits `/books/99999999` to exercise the canonical modal URL when testing missing book behavior. Keep a separate legacy-route assertion if retirement behavior is a contract.
4. Preserve `/`, `/books`, `/books/author/{seedKey}` and `bookId`/`bookMode` modal query semantics. Private REST routes remain unchanged.

Verification and exit: route-state and Books E2E tests cover direct navigation, back/forward, unauthorized access and missing IDs. Legacy requests follow the recorded policy instead of accidentally invoking SPA/Blazor fallbacks.

### P15 — Clean cache and hosting internals behind stronger assertions

Dependencies: P06/P07/P11. Inputs: hosting/cache invalidation modules, Books cache options/services, Redis tests and Q-006.

1. Improve the existing Redis fallback test to assert the intended fallback registrations/behavior, alongside required-Redis startup failure. Prefer strengthening an existing test over adding duplicate tests.
2. Inventory cache interfaces, messages and options against both publishers/subscribers and cross-node tests. Remove only unused implementations or settings with complete evidence.
3. Preserve schema-versioned keys, app/environment channel isolation, local TTL fallback, publish/apply timeout behavior and post-write invalidation even when caller cancellation occurs.
4. Preserve shared Redis connection reuse, Data Protection persistence, health checks, forwarded-header trust and fail-open request observability.

Verification and exit: Redis configuration/reuse, invalidation, Books caching/cross-node, forwarding, rate-limiting and observability tests pass. No runtime infrastructure requirement is weakened by cleanup.

### P16 — Consolidate simulation HTTP handling

Dependencies: P02/P15; read Q-001. Inputs: `Http/HttpClientFactory.cs`, `Running/ScenarioRunner.cs`, auth bootstrap, scenario client and browser sampling.

1. Trace both HTTP handler construction paths, cookie ownership, disposal, redirect behavior, target discovery and TLS policy.
2. Consolidate duplicate handler construction only while preserving existing target/auth behavior. Share a small factory, not a broad new transport abstraction.
3. Keep all deployed-target certificate validation and credential redaction. Do not silently broaden the localhost exception.
4. Q-001's switch from silent bypass to explicit local opt-in is a behavioral fix. If included, describe that change separately, choose the exact option/warning contract, update wrappers/help and add tests showing invalid TLS fails by default, opt-in is loopback-only, and both call paths honor it. Otherwise retain the current policy with the Q-001 follow-up recorded.
5. Preserve synthetic cleanup, cookie isolation, write authorization, timeout/cancellation and simulator exclusion from app publishing.

Verification and exit: simulation auth/contract tests and focused handler-policy tests pass. Run local read-only smoke and `-AuthCheck` on a disposable supported local target if available. Authenticated writes or remote traffic need their own existing explicit gates; neither is required merely to remove duplicated handler setup.

### P17 — Simplify simulation parsing and obsolete scenarios

Dependencies: P16; Q-008 if options parsing changes. Inputs: options/parser classes, scenario catalog, report models and PowerShell wrappers.

1. Map every CLI argument, profile/scenario identifier and report field to readers. Keep environment-only credentials and all write/deployed-target gates.
2. Review Qlty's duration/integer parser pair. Share only equivalent parsing mechanics; preserve separate accepted units, bounds and diagnostic messages.
3. Split option validation into narrow target/auth/write groups if that improves clarity. Preserve aggregated errors, help and exit codes.
4. Delete a scenario or report field only if no current profile, wrapper, report analyzer or documented invocation uses it. Preserve deterministic random selection; it is simulation, not cryptography.

Verification and exit: table-driven parser/auth tests, report/contract tests and wrapper help pass. Equivalent arguments produce equivalent options and errors. Simulation remains built/tested but excluded from published images.

### P18 — Share narrow deployment settings validators

Dependencies: P02/P10; existing Q-007. Inputs: LocalCluster `deploy_settings.py`, Cloud `cloud_settings.py`, their validator entry points and common release helpers.

1. Write representative accepted/rejected synthetic fixtures for shared rules: ports, DNS names, retention, paths and observability. Include each target's defaults and target-specific exceptions.
2. Extract only shared pure validation functions into `Deployment/Common`. Keep schemas/key sets, Cloud address rules and target-specific errors in their owners.
3. Compare old/new accepted settings, defaults and error conditions. Share entry-point setup only when import/execution paths remain reliable from arbitrary working directories.
4. Preserve local `machines.yml`/inventory-driven values and per-fork settings. Never replace target rules with values from this machine or installation.

Verification and exit: Common/Cloud/LocalCluster settings and script tests, template rendering, YAML lint and deployment audit pass. Include paired equivalence cases and target-specific rejection cases. No live host is touched.

### P19 — Review wrappers and abandoned deployment helpers

Dependencies: P18. Inputs: all tracked shell/Python/PowerShell entry points, docs, workflows and imports.

1. Record which wrappers forward to Common helpers and which add target-specific behavior. A thin wrapper can be a stable documented operator interface; retain it when useful.
2. Search workflow steps, docs, sibling scripts, tests, setup runbooks and generated template commands before deleting a helper.
3. Remove proven superseded files and their callers together. If an externally documented command changes, provide its replacement in the same PR rather than silently breaking operators.
4. Keep cleanup ownership validation, volume protection, lock protocol, target gates, native Linux bootstrap restrictions, backup/restore and release-identity verification.

Verification and exit: all affected script suites and ShellCheck pass; documented command help and fixture execution still work. Do not bootstrap, restart, prune or deploy a real node to test a wrapper cleanup.

### P20 — Make deployment audit and collision logic easier to review

Dependencies: P18/P19; read Q-002/Q-005 for collision work. Inputs: `audit_deployment.py`, LocalSingleNode collision modules, audit contract tests and synthetic deployment fixtures.

1. Inventory current audit rules by behavior. Identify duplicate mechanics separately from distinct safety assertions.
2. Split only coherent checks into functions/modules, with explicit inputs and descriptive errors. Preserve every existing rejection and target-specific path.
3. When behavior has intentionally changed in an earlier packet, replace the old audit rule with the new rule in that same behavioral change; never delete a failing check merely to pass.
4. Before touching collision/preflight detection, settle Q-002's packaged-Caddyfile verification basis. An MD5 package metadata check must not become an unconditional allow or a naive different-hash comparison against incompatible metadata.
5. Add meaningful negative fixtures for modified foreign Caddy config, port conflicts, invalid release settings and the safety contracts touched. Avoid tests that only mirror helper names or file layout.

Verification and exit: unchanged valid fixtures pass; altered unsafe fixtures still fail for the intended reason. Run deployment audit, collision tests, quality audit-contract tests and relevant template/script checks. Complexity metrics may improve, but behavioral parity is the acceptance condition.

### P21 — Remove obsolete CI/test/tooling paths without weakening gates

Dependencies: prior code packets integrated. Inputs: `.github`, profile/result validators, lifecycle fixtures, quality scripts and architecture guardrails.

1. Review jobs, inputs, artifacts, environment settings and helper scripts against all workflow/manual/operator callers. Optional or manually dispatched tooling is not dead solely because it rarely runs.
2. Remove genuinely superseded paths with their documentation/tests. Preserve exact release SHA/run/attempt provenance, separate PR validation/main publishing and frontend image smoke.
3. For intentionally added/removed tests, enumerate the actual test cases before changing strict count expectations. Update `validate-frontend-profiles.sh`, result-validator fixtures, React workflow count checks, `validate_vitest_results.py` if affected, Full Sonar count validation and `docs/Test.md` wherever those expectations live. Search for the old counts; explain the delta in the PR.
4. Preserve opt-in E2E/lifecycle semantics and investigate every extra skip. Keep normal build/test sequential in a checkout.
5. Update architecture tests only when their contract deliberately changes. Never remove a guardrail because cleanup violates it.

Verification and exit: workflow/result-validator tests, lifecycle checks, ShellCheck, actionlint, both profile gates and image/browser smoke pass. Exact-head and exact-main required checks remain authoritative.

### P22 — Reconcile operational docs and retained plans

Dependencies: all intended behavioral changes decided/integrated. Inputs: README, docs, deployment guides, existing plans and their support files.

1. Remove references to retired routes/options/commands and add current replacements where applicable. Align README's profile description with the supported reality.
2. Keep one canonical testing guide; repair links and old commands instead of copying another full gate into multiple guides.
3. Mark superseded plan instructions as historical and point to the active replacement. Preserve integrated commit evidence and active downstream plans. Do not delete Portfolio/React/quality plans simply because they are large or completed in part.
4. Archive only plans proven inactive, under a clearly linked tracked archive if useful. Update links, including support files and both paths of any rename. No archival PR is required if it adds churn without improving navigation.
5. Use ordinary prose in persisted documentation and PRs, regardless of compressed chat style.

Verification and exit: review the complete documentation diff and links, run `git diff --check`, use `[skip ci]` and the docs-only PR workflow where applicable. Verify integrated files on fetched `origin/main`.

### P23 — Re-audit and close every candidate

Dependencies: P22 and intended cleanup code integrated. Inputs: disposition inventory, Qlty/Quick reports and optionally the existing Full Sonar baseline.

1. Rerun Qlty and Quick against the final clean source. Use the same tool versions for meaningful comparison; record any version change.
2. Compare candidate dispositions, unused inputs, package references, route/config inventories and duplication groups. Do not compare summed cross-profile issue counts or claim LOC reduction equals quality.
3. Review new warnings and regressions. Retain justified framework/binding findings with reasons rather than suppressing them.
4. Use a Full audit only if refreshed coverage/server evidence will resolve a remaining question; it is optional and does not replace required CI. Do not perform new Trivy/ZAP/sitespeed runs merely to produce more reports for cleanup.
5. Update the existing Q backlog for completed overlapping items, preserving history and links. Leave separately scoped defects as explicit follow-up work.

Verification and exit: every candidate has a final disposition; no high-risk unresolved cleanup defect is hidden as deferred scope. Reports bind to recorded source SHAs. Claims describe actual changes and limits.

### P24 — Verify integrated completion and publish the handoff

Dependencies: all selected packets complete or explicitly retained/skipped; decision-dependent features resolved or explicitly excluded from the authorized execution scope.

1. Fetch `origin/main` and verify every cleanup merge is present. Record the final integrated code SHA and its green exact-main `build-test-push` run.
2. Confirm both profile gates, appropriate React checks, publish switching, deployment audits/script suites and affected browser journeys passed for the final code. Reuse trustworthy final checks rather than rerunning unchanged suites repeatedly.
3. Review the full baseline-to-final diff for unrelated changes, secret material, dropped safety rules, stale route links, uncommitted generated CSS/schema and test-count discrepancies.
4. Record retained features, deliberate retirements, total candidate dispositions, merge commits, checks and remaining separate defects. Do not report deployment validation or a live rollout unless actually authorized and performed.
5. Integrate the final Markdown completion record through the docs-only workflow. Its `[skip ci]` commit need not have a CI run; verify its content on `origin/main` and cite the green final code commit separately.

Verification and exit: the owner can resume from this ledger without reconstructing conversation history. Mark this cleanup complete only after integrated verification, not after a local build or PR creation.

## 6. Acceptance matrix

Use existing suites first. Add focused tests only for meaningful changed risk, not every deleted line.

| Changed area | Required focused evidence, in addition to the full gate |
| --- | --- |
| Razor parameters/geometry/styles | `BookCoverGeometryTests`, `BookcaseShelfItemsTests`, affected Books browser states, CSS regeneration and relevant visual comparison. |
| Client lifecycle/modal | `BookModalRouteStateTests`, focused stale-response/cancellation/delete coverage, affected SSR/hydration/navigation journeys. |
| Endpoints/contracts | Books API tests, `EndpointSurfaceTests`, `OpenApiMetadataTests`, public/private boundary tests and React `api:check`. |
| Composition/publish | `FrontendCompositionTests`, `ReactFrontendHostingTests`, `HostingResponseBehaviourTests`, `HeadRequestTests`, asset/render-mode tests, sequential publish-switch inspection. |
| Identity retirement | Retained login/account journeys, protected API denial, negative removed-route/helper-endpoint tests and form/passkey binding where retained. |
| Cache/hosting | Redis configuration/reuse, invalidation, cross-node Books caching, forwarding, rate limiting and observability tests. |
| React/dependencies | Lockfile install, API check, typecheck, lint, tests/build and public browser acceptance appropriate to route changes. |
| Simulation | Options/auth/contract/publish-exclusion tests, handler-policy tests when changed and wrapper help. Optional safe local smoke for transport changes. |
| Deployment/scripts/audit | Relevant Common/Cloud/LocalCluster/LocalSingleNode script suites, valid/invalid fixtures, rendering, audit, ShellCheck, YAML lint and actionlint. |
| CI/test inventory | Exact count validators, deliberate count delta, lifecycle cleanup and profile/image/browser CI. |
| Ordinary Markdown only | Complete diff/link review, `git diff --check`, docs-only PR and integrated-content verification. |

## 7. Manual blockers and external actions

**No certain manual machine action is currently required to create this plan or start behavior-preserving repository cleanup.** GitHub authentication was available during research and the Quick/native audits ran successfully. No new credentials, paid tools, hardware or node bootstrap is part of the plan.

The unresolved product decisions in section 10 require the owner's judgment. They are not manual setup chores. Keep their packets pending while independent cleanup proceeds.

Do not invent blockers such as asking the owner to run commands the agent can safely run, delete build folders, configure a new analyzer, authenticate an optional provider, or provision a deployment host. If execution reveals a real access/environment failure, record the failed action and exact missing capability, try the supported safe alternative, and ask for only the remaining human-only step. None has been established by this research.

Repository cleanup does not require a live deployment. If the owner later requests one, the applicable explicit CD authorization remains necessary; it is outside this plan's current repository scope.

## 8. Reproducible preparation and verification commands

These commands are aids. Read `docs/Test.md` for the current authoritative full gate. Use the installed RTK wrapper where supported by the executing environment; unsupported scripts and PowerShell cmdlets can run normally.

Source inventory and reviewed searches:

```powershell
git status --short
git fetch origin main
git rev-parse HEAD origin/main
git ls-files
git grep -n -F 'BookSideView'
git grep -n -F 'WithAuthorizationResponses'
git grep -n -F 'grumlebet_gb_clean_smooth_v2'
git grep -n -F 'isbot' -- ':!BlazorAutoApp.React/package-lock.json'
rg -n '@page|MapHead|MapGet|MapPost|MapPut|MapDelete|MapMethods' BlazorAutoApp BlazorAutoApp.Client
```

Existing planning audits, run sequentially:

```powershell
python Scripts/Quality/run_quality_audit.py qlty --timeout-minutes 10
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Mode Quick -FrontendProfile Both
```

Quick accepts dirty source and labels it; Full `-Candidate` requires a clean committed checkout. The Qlty audit copies tracked files, so new source must be staged with explicit paths before a Qlty audit that depends on it. Quick's builds are not a test baseline. Never run a second build/test against the same checkout while the audit is building.

Standard local profile gate in a supported Bash environment, with Docker running:

```bash
bash Scripts/CI/validate-frontend-profiles.sh /tmp/template-cleanup-profile-results
```

The remaining local gate includes `git diff --check`, restore, format verification, Python/script validators, observability/deployment audits, rendered templates, YAML/ShellCheck/actionlint and affected script suites. Copy the full current list from `docs/Test.md`; the profile command alone is insufficient.

React package checks from the root:

```powershell
npm --prefix BlazorAutoApp.React ci
npm --prefix BlazorAutoApp.React run api:check
npm --prefix BlazorAutoApp.React run typecheck
npm --prefix BlazorAutoApp.React run lint
npm --prefix BlazorAutoApp.React test
npm --prefix BlazorAutoApp.React run build
```

When Razor classes or Client styles change:

```powershell
npm --prefix BlazorAutoApp.Client ci
npm --prefix BlazorAutoApp.Client run css:build
git diff -- BlazorAutoApp/wwwroot/tailwind.css
```

## 9. Execution ledger

Only preparation rows are complete. Add one row per packet/PR. Include enough detail to resume: exact input SHA, claimed paths, reviewed candidates, final disposition, local checks, exact-head PR checks, integrated SHA/main checks, and next action. Link detailed evidence from the row rather than pasting logs.

| Item | Status | Evidence / next action |
| --- | --- | --- |
| Repository reconnaissance | Complete | Clean source checkpoint `de90f08d962d4789f4e55e19ddd15aed780b0882`; tracked inventory and named candidates in section 2. |
| Qlty preparation | Complete | Qlty 0.653.0, completed; 125 locations/five duplication groups. Review, do not automatically fix. |
| Quick preparation | Complete | Both analyzer builds succeeded with analyzer 10.35.0.4138; normal selected-profile restore succeeded. No tests or deployment acceptance claimed. |
| Plan integration | Pending | Record documentation PR, integrated SHA and fetched-content verification here or in its PR description. |
| P00 | Pending | Record demo, compatibility and Identity decisions. |
| P01–P03 | Pending | Establish fresh baseline and complete disposition inventory. |
| P04–P11 | Pending | Execute small behavior-preserving cleanup PRs. |
| P12–P14 | Decision-dependent | Retire only selected features; record retention when declined. |
| P15–P21 | Pending | Execute bounded hosting/simulation/deployment/tooling packets with focused checks. |
| P22–P24 | Pending | Reconcile docs, close findings and verify integrated completion. |

Decision entry template:

```text
Decision ID / date:
Feature or external contract:
Owner instruction:
Keep/remove policy and exact resulting behavior:
Affected packets and files:
Verification needed:
```

Packet entry template:

```text
Packet / status:
Input origin/main SHA and branch:
Claimed paths and overlapping work checked:
Candidate IDs and removal/retention evidence:
Changes and behavior preserved or deliberately changed:
Focused checks and full local gate:
PR URL, exact head SHA and required check:
Integrated SHA and exact-main check (or docs-only content verification):
Remaining issue / next packet:
```

## 10. Important open decisions

1. **Design demos:** Should `/books/design-demos` and its detail pages remain a public template feature? Recommendation: retire the public review pages if they were only design exploration; retain the normal bookcase artwork and cover catalog. Until answered, keep the live pages.
2. **Old Books URLs:** Should `/books/create`, `/books/{id}` and `/books/{id}/edit` keep redirecting into the modal flow, or may they be retired to the normal 404 behavior? Recommendation: keep the small redirects unless breaking old links is acceptable. Until answered, preserve them.
3. **Identity breadth:** Should the template keep its full account-management scaffold, or become a narrower template with selected optional flows removed? Name any flows to retire, such as passkeys, Google/external login, 2FA or email confirmation/reset. Recommendation: preserve the current Identity surface during the first cleanup wave; make an explicitly selected reduction a separate PR. Until answered, remove only proven leftovers, not working account features.

No answer is needed to begin the proven dead-input, redundant-branch, configuration-documentation and inventory work after implementation is authorized. Both frontend profiles, all deployment targets, simulation and observability remain supported defaults rather than speculative retirement candidates.
