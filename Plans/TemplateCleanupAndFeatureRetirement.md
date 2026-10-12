# Template cleanup and feature retirement

## Status and purpose

Status: **in progress**. Repository reconnaissance, planning audits, execution review, baseline validation and complete source inventory are complete. The owner resolved all three feature decisions on 2026-10-12. Section 10 records those decisions and accepted technical defaults. No preference question blocks execution.

Create a smaller, easier-to-maintain template by removing proven unused code, unused parameters, obsolete configuration and abandoned assets; simplifying unnecessary branches; and retiring explicitly selected old features as complete vertical changes. Preserve the supported template capabilities unless a recorded owner decision changes them.

This document is an execution runbook for an agent with no previous conversation context. Execute one packet at a time, record evidence, and stop a packet when its proof or checks fail. Do not treat a search result, analyzer warning, low coverage, or lack of recent traffic as permission to delete a feature.

The active goal [TemplateCleanupAndFeatureRetirementGoal.md](TemplateCleanupAndFeatureRetirementGoal.md) authorizes the ordinary repository implementation, required tests, PRs and normal merges described here. It does not authorize changing a live host, provisioning a node or dispatching a deployment. Follow the repository rules throughout execution.

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
| C-05 | `BookSideView.ForcedOpen` is implemented, but shelf callers do not set it. Demos pass `ForcedOpen` through `BookDesignDemoCover` to `BookCoverRenderer`. | Remove the unused outer option in P04; remove the renderer's demo-only forced-state option and branches in P13 after deleting its demo consumer. Preserve normal hover/focus motion. |
| C-06 | Root `grumlebet_gb_clean_smooth_v2.svg` is 144,015 bytes. Tracked text search found no filename reference; Git history records a logo commit. It is outside both frontend asset roots. | Likely abandoned source artifact. Check build inputs, documentation and planning references before removal; if still a deliberate design reference, retain and describe it. Packet P09. |
| C-07 | `/books/design-demos` and `/books/design-demos/{DesignId}` have route components, navigation links, HEAD mappings, simulation scenarios and browser/render-mode tests. | Owner approved retirement. Remove the complete feature and its consumers atomically in P13; preserve normal bookcase artwork. |
| C-08 | `Routes/Create.razor`, `Details.razor`, `Edit.razor` redirect old URLs into the modal query flow. `BooksE2ETests` still visits `/books/99999999`. | Owner accepted retaining the redirects. Verify their mappings in P14; do not delete the compatibility routes. |
| C-09 | README describes `Books:SeedLocalDefaults`; source reads `AuthorBooks:SeedAtStartup` with a default of `true` in `AuthorBookSeedExtensions`. | Confirmed documentation drift. Correct docs to actual behavior; changing seed defaults is a separate product change. Packet P10. |
| C-10 | React's `isbot` has no app import, but `FrontendProfiles.md` documents its React Router type-generation/prerender tooling role. | Retain unless framework-tool execution proves it unnecessary. App-import search alone is insufficient. Packet P08. |
| C-11 | Quick `S1144` flags `Login.InputModel.Passkey` and nested `AppOpenTelemetryOptions` setters. Those models are form/configuration-bound. | False-positive risk. Preserve setters and prove binding behavior; do not remove them to reduce warnings. Packets P03/P12. |
| C-12 | Quick flags empty assembly markers, `BooksEndpointLogCategory` and the explicit `public partial class Program` declaration. | Retain assembly marker types used by architecture tests and the typed logger category used by endpoint logging. Remove only the explicit `Program` declaration: ASP0027 says it is unnecessary on the current ASP.NET Core target; verify the SDK-generated public `Program` remains usable by all `WebApplicationFactory<Program>` tests. Packet P03. |
| C-13 | Cancellation catches in `AuthorBookcaseState`, `UserBookcaseState` and `BookModalHost`; nested conditions/static candidates in `BookPageView`. | Review lifecycle semantics first. Removing a catch can change navigation or disposal behavior. Packet P11. |
| C-14 | Qlty settings duplication at `cloud_settings.py:154–168` and `deploy_settings.py:150–164`; matching validator entry-point setup. Existing backlog Q-007. | Candidate for narrow shared validation functions, with target-specific contracts preserved. Packet P18. |
| C-15 | `audit_deployment.py` leads Qlty's complexity ranking. The collision preflight, release validators and simulation options also rank highly. | Complexity is not proof of dead checks. Split only where equivalent rejection behavior can be demonstrated. Packets P17–P20. |
| C-16 | `RedisConfigurationTests.Production_AllowsMissingRedis_WhenFallbackIsExplicitlyAllowed` only accesses `factory.Services`. Existing Q-006 requests actual fallback assertions. | Improve the existing meaningful test before touching Redis registration. Packet P15. |
| C-17 | `ScenarioCatalog.BuildReadOnly()` targets the two demo routes; `ScenarioContext.NextDesignId()` duplicates ten client design identifiers. | P13 must remove both scenarios and the now-unused selector/identifier list in the retirement PR. Otherwise simulation reports unexpected 404s after retirement. |
| C-18 | `BookCoverDesignDefinition` mixes rendering geometry with `DemoTitle*`, demo colors and descriptive metadata. Its normal renderer reads `Kind` and `Plate`; geometry tests also use `Id` and `Label`. | In P13 remove only demo-owned fields and their ten constructor argument sets after rechecking consumers. Preserve `Kind`, `Id`, `Label`, `Plate`, catalog ordering and artwork. |

### 2.4 Execution review and resolved failure modes

The second review followed each packet as an executor with no conversation memory and searched the consumers of the accepted retirement. It found these practical gaps:

| Problem in the initial plan | Resolution now required |
| --- | --- |
| Demo retirement omitted simulation and Razor imports. | P13 names both scenarios, `NextDesignId`, both imports files and the exact four demo files. Remove them in the same PR as the routes. |
| Existing Books E2E journeys use demos as navigation detours. | P13 replaces those detours with retained account-page navigation; preserve CRUD and navigation coverage rather than deleting the whole tests. |
| Positive static-render tests would request deleted routes. | Replace the three demo theory rows with retained static account routes, preserving the assertions and documenting any actual discovered-count delta. |
| Removing pages alone leaves demo-only rendering options and catalog data. | P13 removes proven orphaned fields/types/options after the pages, then rebuilds CSS and checks normal artwork. |
| P21 updated strict test counts only after earlier PRs could already fail. | Section 4.2 requires every test-changing PR to update all count consumers immediately. P21 performs the final consistency audit. |
| A blanket retired-route 404 would contradict React's SPA fallback. | Blazor GET/HEAD return 404 for retired demo routes. React keeps its documented HTML-shell fallback and client not-found behavior; do not redesign SPA HTTP statuses. |
| Identity and compatibility packets still offered rejected alternatives. | P12 and P14 now verify retention only. Full Identity and all three compatibility redirects stay. |
| Simulation TLS and Caddy ownership verification left design choices unresolved. | P16 defines the accepted explicit local TLS exception. P20 preserves the Caddy package checksum policy; replacing its verification mechanism remains a separate Q-002 project, not a cleanup blocker. |
| Large audit/parser cleanup could become a generic rewrite. | Use the substeps and bounded extraction rules below. Preserve intentional endpoint duplication and frontend hook symmetry by default. |
| A broad inventory could become endless or rubber-stamped. | Classify all tracked areas, inspect each candidate's consumers and assign dispositions. Required known changes cannot be dismissed as no-op without proof they already landed upstream. |

Further read-only preflight on 2026-10-12 confirmed the local Linux Docker engine responds, .NET 10.0.303, Node 24.21.0, npm 12.2.0 and Python 3.13.7 are available, and PowerShell 7/Bash/Git/GitHub CLI resolve. No PR was open at that checkpoint. This is tool availability, not a completed local gate or proof that every optional Linux lint package is installed. Do not persist machine-specific executable paths or assume the same tools exist in another clone.

## 3. Rules for proving a removal

Before deleting or narrowing any symbol, file, configuration key or dependency, record:

1. Its declaration and intended responsibility.
2. Direct callers in production, tests, scripts and documentation, using tracked files rather than ignored backup copies.
3. Indirect consumers: Razor routes/attributes, DI registrations, reflection, configuration/form binding, serialization, EF discovery, assembly markers, static asset manifests, CSS-generated classes, workflow dispatch, CLI entry points and framework tools.
4. Which frontend profiles and deployment targets can reach it.
5. Whether it is externally observable: URL, JSON field, environment variable, CLI argument, exit code, dashboard series, deployment setting or database shape.
6. The resulting behavior and a focused verification that distinguishes the old risk from the new behavior.

Use `git grep` or `rg` restricted to tracked source areas. A filename can be generated, a class can be reached through its extension methods, and a setting may come only from environment variables. Zero text matches is a candidate, not a proof.

Use these dispositions in the execution ledger: **remove**, **simplify**, **retain with reason**, or **separate defect outside this cleanup**. Every reviewed candidate gets one. Resolve an unproven new breaking removal by retaining the external contract and recording the missing proof, not by creating another preference question. A packet is complete when its disposition is justified and verified, even if retaining the code is the correct result. A required known outcome can be retained only when fresh evidence disproves the original premise or proves it already landed; include that evidence.

Never remove migrations or the model snapshot because they have no normal callers. Never remove `CancellationToken`, route/form/query parameters, serialized fields or configuration setters merely because a lexical analyzer misses their consumers. Never make private APIs public or remove Redis/security checks to simplify a profile.

## 4. Execution and handoff protocol

### 4.1 Start and resume

1. Fetch `origin/main`, read this plan and the current working rules, and inspect `git status` before edits.
2. Preserve unrelated dirty work. Use a clean, separate worktree when necessary; do not stash, reset or overwrite another person's files. Observe applicable worktree task-binding rules.
3. Check active PRs and retained React/Portfolio/quality plan status before claiming files. Coordinate overlapping work by rebasing or deferring the overlapping packet, not by overwriting it.
4. Create a cleanup branch from current `origin/main`. Record its input SHA and claimed paths in section 9.
5. Choose the earliest uncompleted packet whose dependencies are satisfied. Section 10 already supplies the decisions; do not ask the same preference questions again.
6. Read the packet's named files completely before changing them. Revalidate research candidates against the current source.

### 4.2 One packet's completion cycle

For each packet: establish the before behavior, make the smallest coherent change, update directly affected tests/docs/generated outputs, run focused checks, review the full diff, then run the required local gate before pushing. Stage explicit paths. Create a PR with the concrete behavior and validation results.

Code/configuration PRs require green `build-test-push` on the **exact PR head** before merging. After merge, fetch the integrated commit and require green **exact-main CI** for that commit before marking the code packet complete. Do not substitute another commit's green run. Record the merge commit, check URLs and dispositions in section 9 or the linked PR description.

If a packet adds, removes or replaces tests, update strict expectations **in that same PR before running its full gate**. Count discovered cases, including each theory row, not just test methods. At the inspected source, the count consumers include `Scripts/CI/validate-frontend-profiles.sh`, `.github/workflows/ci.yml`, `Scripts/Quality/Invoke-SonarAnalysis.ps1`, `Scripts/Quality/sonar_report.py`, `Scripts/Quality/validate_vitest_results.py`, their relevant fixtures/tests and `docs/Test.md`. Inspect profile traits: a Blazor-only theory delta must not lower the React expected count. Explain old/new passed/skipped totals. Preserve the 13 opt-in skips unless an approved test change genuinely affects them. Existing historical baseline examples need not be rewritten as current measurements. P21 verifies this work; it is not the first opportunity to do it.

Ordinary Markdown-only PRs use the repository documentation exception: complete diff review, `git diff --check`, `[skip ci]` in the documentation commit and squash title, a PR, then fetched integrated-content verification on `origin/main`. Do not wait for CI or run builds for a purely documentation change. A PR that deletes an SVG or HTML file is not documentation-only, even if the file is unused.

Do not dispatch CD to establish completion of a repository cleanup. Live acceptance can be a separate, explicitly authorized follow-up if necessary. Preserve deploy locks, volumes, backups, scoped ownership checks and release provenance.

### 4.3 PR size and order

Suggested waves:

| Wave | Packets | Purpose |
| --- | --- | --- |
| A | P00–P03 | Establish scope, baseline and removal proof. |
| B | P04–P07 | Small, behavior-preserving client/server cleanup. Prefer separate client and backend PRs. |
| C | P08–P11 | Dependencies, assets, configuration/docs and lifecycle review. Split non-Markdown work from independent docs. |
| D | P12–P14 | Verify full Identity and legacy redirects; retire design demos as one complete feature PR. |
| E | P15–P17 | Cache/hosting and simulation cleanup with focused risk tests. |
| F | P18–P21 | Deployment helpers, audit structure and CI/tooling. Keep shared-validator and audit changes separate. |
| G | P22–P24 | Documentation closure, re-audit and integrated verification. |

Do not combine all waves into one large PR. A packet with no justified changes needs only an evidence-backed retention entry, not an empty PR. Do not make extraction/refactoring a condition of completion when duplication is clearer than a generic abstraction.

Known required outcomes are C-01/C-02 cleanup, C-03 helper simplification when still unconsumed, C-09 documentation correction, complete C-07/C-17/C-18 demo retirement, Q-006 fallback assertions, P16's defined TLS policy and P18's shared pure validators. If an outcome is already integrated upstream, verify it and record the commit instead of repeating it. Inventory/refactor packets may conclude retention, but cannot be used to skip these outcomes silently.

### 4.4 Dependency order and bounded substeps

The executable order is P00, P01, P02, P03, P04, P05, P06, P07, P08, P09, P10, P11, P12, P13, P14, P15, P16, P17, P18, P19, P20, P21, P22, P23, P24. This order satisfies the named dependencies. Do not make a later closure packet a prerequisite for an earlier change. In particular, P13 owns demo-specific style cleanup, P16 may update parser plumbing before P17 decomposes it, and every packet owns its own test-count/audit-rule updates.

For P02, produce separate inventory sections for host/Core, Blazor/Razor, React, simulation, deployment/scripts, CI/quality tooling, assets/configuration and tests/docs. For P11, separate load/disposal review from save/delete review. For P17, separate CLI input mapping, pure parsing, safety validation and report-consumer review. For P20, extract one existing rule family at a time and run its positive/negative fixtures before the next family. A substep may be committed locally, but do not push/merge an intermediate state that breaks consumers or the gate. The atomic P13 substeps are specified in its packet.

## 5. Ordered implementation packets

### P00 — Apply the resolved scope contract

Dependencies: none. Inputs: sections 1, 2 and 10; current requirements and active plans.

1. Verify the support matrix in section 1 against the latest repository without changing its accepted policy.
2. Apply the recorded owner decisions: retire design demos, retain all three legacy redirects, and retain full Identity. Do not ask for confirmation again.
3. Apply section 10's technical defaults. If source contradicts a research detail, correct that detail and continue within the same accepted scope. Keep an unproven new breaking removal rather than inventing a preference blocker.
4. Identify shared files owned by active React delivery or Portfolio planning. Avoid importing downstream product removals into the template.

Verification and exit: accepted decisions are reflected in the inventory; no preference question remains. Required cleanup outcomes and retained capabilities are explicit.

### P01 — Capture a trustworthy execution baseline

Dependencies: P00. Inputs: `docs/Test.md`, `.github/workflows/ci.yml`, profile gate and current package/configuration files.

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

Verification and exit: every source area is classified. Unproven candidates are retained with reasons, not left indefinitely pending. The inventory does not label ignored `Plans.local`, `node_modules`, test output or build artifacts as tracked dead code.

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
3. Search all `BookSideView` usages for `ForcedOpen`. Remove the unused outer option and its forwarding attribute when the current callers still leave it unset. Keep `BookCoverRenderer.ForcedOpen` until P13 removes its remaining demo consumer in the complete retirement PR.
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
2. Retain the separate update/delete typed handlers and their clear operation-specific outcome blocks. Do not introduce a generic endpoint wrapper to satisfy Qlty. Remove an independently proven redundant local/helper if one exists.
3. Preserve route/body ID mismatch rejection, ownership filtering, 401/403/404/429 behavior, validation payloads, `private, no-store`, telemetry and cancellation propagation.
4. Do not merge public author-book contracts with authenticated user-book contracts or rename serialized fields as cleanup.

Verification and exit: feature API tests, `EndpointSurfaceTests`, `OpenApiMetadataTests`, caching tests and React `api:check` pass. Any intentional schema change must regenerate and review both schema outputs; otherwise generated API files remain unchanged.

### P07 — Review frontend composition and unused hook arguments

Dependencies: P06. Inputs: both `FrontendComposition` implementations, `Program.cs`, host project conditions and hosting tests.

1. Document the shared method signatures compiled under each profile. The React configuration argument and Blazor empty static-files hook are currently deliberate symmetry.
2. Retain the paired signatures and the intentionally empty Blazor static-files hook. Do not add conditional calls or dummy configuration reads to eliminate a warning.
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

Dependencies: P02/P04/P08. Inputs: root SVG, frontend asset roots, `app.css`, `input.css`, JS modules and asset tests. Leave demo-only styles until P13 removes their live consumers; remove those styles within that retirement packet.

1. Recheck the root logo SVG against tracked plans, history and build inputs. The accepted default is to delete this unused root artifact when no required current consumer exists; Git history preserves the old artwork. If new source proves a deliberate reference, retain it with the exact consumer in the inventory rather than asking a cosmetic preference question.
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

### P12 — Preserve and verify full Identity

Dependencies: P00/P11. Inputs: account pages/shared components/endpoint helpers, registration, Google configuration, Core/private APIs and Identity E2E. Q-003 is background coverage evidence, not a prerequisite to finish unchanged account pages.

1. Inventory account routes/helpers, including passkeys, Google/external login, 2FA, recovery, email confirmation/reset and personal-data export/deletion. Mark all retained.
2. Remove only proven scaffolding leftovers and stale text. Missing provider credentials, a no-op email sender or low coverage do not prove associated pages dead. Preserve form/configuration setters and browser JS.
3. Preserve login/register/logout, ownership enforcement, antiforgery, API cookie challenges, security-stamp revalidation, data management, token providers, Identity tables and migrations, including in the React backend.
4. Run the existing Identity journey and focused affected tests. Add binding/security regression coverage only if a cleanup actually changes those paths; broad Q-003 account coverage remains separately scoped.

Verification and exit: retained routes, services and required dependencies remain present; existing account/API-denial behavior passes. Use existing fakes or virtual authenticators for a changed path. No real OAuth account, email provider or passkey hardware is required just to retain the scaffold.

### P13 — Retire public design demos as one complete feature

Dependencies: P00/P09/P12. Inputs: the exact paths below, normal cover consumers, `RenderModeHtmlTests`, `BooksE2ETests`, `HeadRequestTests`, simulation contracts and strict test-count consumers. Complete substeps P13.1–P13.8 before pushing this feature PR.

**P13.1 — Freeze the before/after contract.** Blazor `/books/design-demos` and `/books/design-demos/cloth-hardback`, with or without `?open=true`, return 404 for GET and HEAD after retirement; HEAD has no body. Links and successful simulation traffic to them disappear. React continues its existing account-free SPA contract: unknown HTML navigation can receive its HTTP 200 shell and client not-found UI; non-HTML/unsafe navigation keeps its existing rejection. Do not add a global React 404 rule for this cleanup.

**P13.2 — Remove route/UI consumers.** Delete these four files under `BlazorAutoApp.Client/Features/Books/DesignDemos/`: `BookDesignDemos.razor`, `BookDesignDemoDetails.razor`, `BookDesignDemoCover.razor`, `BookDesignDemoCatalog.cs`. Remove desktop/mobile links and their selectors from `Features/AppShell/Layout/NavMenu.razor`. Remove the demo namespace import from the actual owning `_Imports.razor` file(s), checking both Client root and `Features/Books/_Imports.razor`. Remove the two demo `MapHead` entries in `BlazorAutoApp/Infrastructure/Hosting/HeadRequestExtensions.cs`.

**P13.3 — Remove dependent operator traffic.** In `BlazorAutoApp.Simulation/Scenarios/ScenarioCatalog.cs`, remove the `design-demos` and `design-demo-detail` scenarios. In `Scenarios/Scenario.cs`, remove the now-unused `ScenarioContext.NextDesignId()` and its duplicated design-ID list. Keep remaining weights and RPS/write safety budgets; normal weighted selection already handles a smaller catalog. Preserve historical report reading and document that new runs no longer emit the two scenario names. Add a focused catalog regression asserting no generated successful page scenario targets the retired prefix; update test counts immediately.

**P13.4 — Remove orphaned demo metadata.** Recheck every property consumer of `BookCoverDesignDefinition`. Remove `DemoTitleLines`, `DemoTitleY`, `DemoTitleDy`, `DemoTitleFontSize`, `DemoTitleFill`, `Note`, `CoverColors`, `PageColors` and `LineStroke` when their only consumers were demos. Remove their named arguments from all ten catalog entries. Delete `BookCoverDesignColors` if it then has no consumers. Preserve `Kind`, `Id`, `Label`, `Plate`, all ten artwork designs, enum values, plate data and catalog order; order affects deterministic design selection. Do not change normal `BookCoverTheme` values.

**P13.5 — Remove orphaned rendering knobs.** After deleting the demo wrapper and P04's outer option, remove `BookCoverRenderer.ForcedOpen` and collapse `PagesClass`/`CoverClass` to their current false-branch strings. Preserve hover, keyboard focus, focus-within and reduced-motion classes exactly. `TitleDy` is only customized by demos at the inspected source: if still true, replace its unused configurable parameter with the existing `1.2em` default in the renderer. Do not remove title layout inputs used by normal books.

**P13.6 — Preserve meaningful test journeys.** In `RenderModeHtmlTests`, replace the two demo rows in `StaticAndAccountPages_DoNotLoadInteractiveBlazorRuntime` with `/Account/Register` and `/Account/ForgotPassword`, retaining `/Account/Login`. Replace the demo row in `PublicPages_DoNotReferenceRemovedScopedCssBundle` with `/books`, retaining `/`. This preserves five positive theory cases for supported pages. Add four Blazor-only GET/HEAD retired-route cases, reusing the host fixture and preserving React's profile exclusion. In `BooksE2ETests.Books_CanCreateViewEditCancelAndNavigateBack`, replace the anonymous demo detour with a retained `/Account/Login` round trip. In `SeededUser_BookcaseCrudSurvivesRefreshAndNavigation`, use authenticated `/Account/Manage` and return through existing home/interactivity helpers. Preserve all CRUD, refresh, missing-book and navigation assertions; do not delete these complete tests. Verify desktop/mobile nav has no demo links using the relevant existing browser journeys.

**P13.7 — Reconcile styles/docs/counts.** Remove only CSS rendered solely by the retired UI, regenerate `BlazorAutoApp/wwwroot/tailwind.css`, and remove the deleted namespace/type references. Replace the demo path in `docs/Test.md`'s Lighthouse example with `/books`; review other current docs/commands for active demo instructions. Preserve historical execution evidence in old plans, adding a superseded note only where needed. Apply section 4.2's same-PR count updates: the retained theory rows and existing E2E methods preserve their counts, the four new retired-route cases apply only to Blazor, and any new simulation test normally applies to both profiles. Measure final totals rather than hard-coding a guessed delta.

**P13.8 — Verify and integrate the complete retirement.** Search tracked production/current test/docs paths for `BookDesignDemo`, `NextDesignId`, `DemoTitle`, `design-demo-link`, `design-demo-menu-link` and the retired URL prefix. Remaining URL references are allowed only in negative tests, the current retirement record or historical evidence. Run geometry/shelf, affected render/HEAD, simulation, both profile and targeted Books browser checks, plus the full local gate. Verify Blazor GET/HEAD 404 responses and React's unchanged navigation contract. Review normal shelf screenshots at narrow/wide widths before merging.

Verification and exit: routes, links, HEAD aliases, demo traffic, imports, metadata and forced-open-only branches are all removed in one green exact-head PR, followed by green exact-main CI. Normal art, hover/focus motion, account flows and legacy redirects remain functional.

### P14 — Verify retained old Books URLs

Dependencies: P00/P11/P13. Inputs: `Routes/Create.razor`, `Details.razor`, `Edit.razor`, modal route state, `BooksE2ETests` and route docs.

1. Preserve all three authorized compatibility components and their `[Authorize]` attributes. Verify the mappings: `/books/create` to `/books?bookMode=create`; `/books/{id:int}` to `/books?bookId={id}&bookMode=view`; `/books/{id:int}/edit` to `/books?bookId={id}&bookMode=edit`, with invariant-culture IDs and history replacement.
2. Keep the existing invalid-book visit to `/books/99999999` because it now intentionally protects compatibility and missing-book behavior. Add canonical modal assertions only when needed; do not replace the compatibility test accidentally.
3. Verify direct authenticated navigation, unauthorized access, back/forward and the selected book ID. Preserve `/`, `/books`, author routes, public/private API separation and existing query semantics.

Verification and exit: redirects are retained and behavior-tested; no legacy component is classified dead merely because its only operation is redirecting.

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
4. Implement the accepted Q-001 policy as a separately described simulation change: default certificate validation on every HTTP/browser path; explicit CLI `--allow-insecure-localhost` and wrapper `-AllowInsecureLocalhost`; no implicit environment opt-in. Reject the flag unless the target is `local`, the base scheme is HTTPS and the host is exactly `localhost`, `127.0.0.1` or `::1`. The flag does not satisfy deployed/write gates. Emit one clear startup warning without credentials or cookies. Keep normal local HTTP and trusted HTTPS working without the flag.
5. Thread the policy through `SimulationOptions`, `AuthBootstrapOptions`, `ScenarioRunner` discovery, `HttpScenarioClient`, `AuthenticatedBooksClient`, `BrowserAuthBootstrap` and its authenticated HTTP probe. Share a small policy predicate and handler factory rather than duplicating localhost decisions. For handler certificate callbacks, test the actual request URI, including redirects; a loopback base URI must never disable certificate validation for a remote redirect. For Playwright, `IgnoreHTTPSErrors` is permitted only in the explicit local context; prevent off-origin requests/navigation while that context bypass is active so the option cannot bless a remote certificate. Default browser behavior remains unchanged. Update simulator help, wrapper help and local examples together.
6. Add meaningful policy/parser/handler/browser-option tests: default invalid TLS rejected; explicit loopback allowed; deployed/custom remote rejected; actual remote redirect never bypassed; cookies, cancellation and valid local traffic preserved. Prefer isolated loopback/fake-handler tests; do not ask for live provider credentials or disable validation globally to run smoke.
7. Preserve synthetic cleanup, cookie isolation, write authorization, timeout/cancellation and simulator exclusion from app publishing. Update strict test counts in this PR, not P21.

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

Execute the extraction in these bounded substeps, keeping one coherent validator PR:

- **P18.1:** Capture the two validators' existing outputs for shared valid/invalid inputs. Include blank optional values, boundary ports 1023/1024/65535/65536, non-digits, reused app/observability ports, accepted/rejected retention suffixes, malformed DNS and target-specific path examples. Compare error ordering and text as well as pass/fail.
- **P18.2:** Add a small pure module at `Deployment/Common/Scripts/Component/lib/settings_validation.py`. Begin with the identical observability port loop and retention syntax predicates. Pass key/value and existing port ownership state explicitly; do not import target settings, read files, access environment variables or initialize CLI state inside the shared module.
- **P18.3:** Call the shared functions from both owners at the original validation positions. Preserve their key lists, blank-value policy, seen-port mutation/order and target-specific messages. Port collisions must still include app ports and earlier observability ports, not just a new local set.
- **P18.4:** Extend to DNS/path primitives only where their accepted syntax is actually equivalent. Keep differing example/error strings in each owner. Leave Cloud network/address rules and schema key enforcement untouched. Retain duplicated CLI entry-point setup by default unless its extraction demonstrably removes more code than import plumbing adds.
- **P18.5:** Exercise both CLIs from the repository root and an unrelated temporary working directory using absolute source/fixture paths. Add isolated module/parity tests and run the settings, render and deployment gates. If an audit inspects an inline implementation, replace that assertion with the shared-call/new behavior contract in this same PR.

Verification and exit: Common/Cloud/LocalCluster settings and script tests, template rendering, YAML lint and deployment audit pass. Include paired equivalence cases and target-specific rejection cases. No live host is touched.

### P19 — Review wrappers and abandoned deployment helpers

Dependencies: P18. Inputs: all tracked shell/Python/PowerShell entry points, docs, workflows and imports.

1. Record which wrappers forward to Common helpers and which add target-specific behavior. A thin wrapper can be a stable documented operator interface; retain it when useful.
2. Search workflow steps, docs, sibling scripts, tests, setup runbooks and generated template commands before deleting a helper.
3. Remove proven superseded files and their callers together. If an externally documented command changes, provide its replacement in the same PR rather than silently breaking operators.
4. Keep cleanup ownership validation, volume protection, lock protocol, target gates, native Linux bootstrap restrictions, backup/restore and release-identity verification.

Verification and exit: all affected script suites and ShellCheck pass; documented command help and fixture execution still work. Do not bootstrap, restart, prune or deploy a real node to test a wrapper cleanup.

### P20 — Make deployment audit and collision logic easier to review

Dependencies: P18/P19. Inputs: `audit_deployment.py`, LocalSingleNode collision modules, audit contract tests and synthetic deployment fixtures. Read Q-002/Q-005 as context; replacing the packaged-Caddyfile verification mechanism is outside this cleanup and does not block structural review.

1. Inventory current audit rules by behavior. Identify duplicate mechanics separately from distinct safety assertions.
2. Split only coherent checks into functions/modules, with explicit inputs and descriptive errors. Preserve every existing rejection and target-specific path.
3. Verify that earlier packets already updated any audit contract they intentionally changed. Replace an obsolete rule with the new behavior check immediately when discovered, with negative evidence; never delete a failing check merely to pass. Future behavioral changes still own their audit update in their own PR.
4. Preserve the current packaged-Caddyfile comparison policy during decomposition. Its digest must remain compatible with dpkg's conffile metadata; do not replace MD5 with an incompatible SHA comparison, auto-download a package or alter host adoption. Q-002's stronger package-verification design remains explicitly separate. If preserving the predicate prevents a useful collision extraction, retain that predicate and close only the structural review with a reason. Do not claim Q-002 complete.
5. Add meaningful negative fixtures for modified foreign Caddy config, port conflicts, invalid release settings and the safety contracts touched. Avoid tests that only mirror helper names or file layout.

Verification and exit: unchanged valid fixtures pass; altered unsafe fixtures still fail for the intended reason. Run deployment audit, collision tests, quality audit-contract tests and relevant template/script checks. Complexity metrics may improve, but behavioral parity is the acceptance condition.

### P21 — Remove obsolete CI/test/tooling paths without weakening gates

Dependencies: prior code packets integrated. Inputs: `.github`, profile/result validators, lifecycle fixtures, quality scripts and architecture guardrails.

1. Review jobs, inputs, artifacts, environment settings and helper scripts against all workflow/manual/operator callers. Optional or manually dispatched tooling is not dead solely because it rarely runs.
2. Remove genuinely superseded paths with their documentation/tests. Preserve exact release SHA/run/attempt provenance, separate PR validation/main publishing and frontend image smoke.
3. Audit the same-PR count updates already required by section 4.2. Search actual expectations in the profile gate, CI, `Invoke-SonarAnalysis.ps1`, `sonar_report.py`, `validate_vitest_results.py`, relevant fixtures and `docs/Test.md`. Compare discovered cases, profile traits and TRX results. Repair inconsistent current expectations; preserve honest historical baseline measurements. This packet must not be the first count update after P13/P16 add tests.
4. Preserve opt-in E2E/lifecycle semantics and investigate every extra skip. Keep normal build/test sequential in a checkout.
5. Update architecture tests only when their contract deliberately changes. Never remove a guardrail because cleanup violates it.

Verification and exit: workflow/result-validator tests, lifecycle checks, ShellCheck, actionlint, both profile gates and image/browser smoke pass. Exact-head and exact-main required checks remain authoritative.

### P22 — Reconcile operational docs and retained plans

Dependencies: all intended code changes integrated. Inputs: README, docs, deployment guides, existing plans and their support files.

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

Dependencies: every packet complete with an evidence-backed disposition, all required known changes integrated, and retained features verified. No pending preference decision remains.

1. Fetch `origin/main` and verify every cleanup merge is present. Record the final integrated code SHA and its green exact-main `build-test-push` run.
2. Confirm both profile gates, appropriate React checks, publish switching, deployment audits/script suites and affected browser journeys passed for the final code. Reuse trustworthy final checks rather than rerunning unchanged suites repeatedly.
3. Review the full baseline-to-final diff for unrelated changes, secret material, dropped safety rules, stale route links, uncommitted generated CSS/schema and test-count discrepancies.
4. Record retained features, deliberate retirements, total candidate dispositions, merge commits, checks and remaining separate defects. Do not report deployment validation or a live rollout unless actually authorized and performed.
5. Integrate the final Markdown completion record through the docs-only workflow. Its `[skip ci]` commit need not have a CI run; verify its content on `origin/main` and cite the green final code commit separately.
6. Re-inventory registered worktrees. Remove clean stale checkouts only after verifying their work is merged or their committed refs are preserved; retain dirty or active checkouts. Remove generated untracked artifacts only after verifying their exact paths and contents. Prune stale worktree metadata, then record removed checkouts, preserved branches and the final inventory without machine-specific paths.

Verification and exit: the owner can resume from this ledger without reconstructing conversation history. Mark this cleanup complete only after integrated verification, not after a local build or PR creation.

## 6. Acceptance matrix

Use existing suites first. Add focused tests only for meaningful changed risk, not every deleted line.

Run Books/Identity/render-mode browser journeys against a disposable **BlazorAuto** app and React public journeys against a **React** app. Explicitly restore/build the matching profile before `--no-build` tests; the preceding two-profile gate ends with React binaries. Do not point the complete `Category=E2E` suite at React and then weaken failing account tests. Use the test guide's profile/category filters, opt-in variables and data cleanup. After sequential profile experiments, restore/build the tracked selected profile when its normal local workflow is needed. Keep local test targets distinct from live deployments.

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

The owner supplied the product decisions and accepted intelligent implementation recommendations. Section 10 closes them. Do not reopen those decisions, convert an intentionally retained feature into a blocker, or ask the owner to choose routine names, helper boundaries or test arrangements.

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

Preparation, resolved scope and baseline rows are complete. P02 is complete; P03 has passed its local gate and awaits exact-head CI and integrated verification. Complete each packet row only after the gate appropriate to its change type. Include enough detail to resume: exact input SHA, claimed paths, reviewed candidates, final disposition, local checks, exact-head PR checks, integrated SHA/main checks, and next action. Link detailed evidence from the row rather than pasting logs.

| Item | Status | Evidence / next action |
| --- | --- | --- |
| Repository reconnaissance | Complete | Clean source checkpoint `de90f08d962d4789f4e55e19ddd15aed780b0882`; tracked inventory and named candidates in section 2. |
| Qlty preparation | Complete | Qlty 0.653.0, completed; 125 locations/five duplication groups. Review, do not automatically fix. |
| Quick preparation | Complete | Both analyzer builds succeeded with analyzer 10.35.0.4138; normal selected-profile restore succeeded. No tests or deployment acceptance claimed. |
| Initial plan integration | Complete | [PR #186](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/186), integrated `9bf5d49ba2e1af61c5fcd85708047943e029a074`; fetched plan matched the reviewed head. |
| Execution review and goal | Complete | [PR #188](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/188), squash-integrated as `01dbeae5441e1d9a50d4cb3387bffe356edc6d91`; fetched plan and goal content verified on `origin/main`. Goal prompt is 3,459 characters. |
| Owner decisions | Complete | 2026-10-12: remove design demos, take the recommendation to keep legacy redirects, retain Identity as part of the template. |
| Worktree cleanup | Initial pass complete; final recheck pending | 2026-10-12: removed 13 stale checkouts from this repository; the 10 deleted local branches matched merged PRs #135, #154, #159, #162, #164, #167, #171, #172, #185 and integrated PR #153. Preserved the dirty React P3 worktree and the unmerged `coord/node-inventory-handoff` branch/ref. Current list has this cleanup checkout and P3 only; repeat at P24. |
| P00 | Complete | At `origin/main` `fdd36a2e`, changes since the research source `de90f08d` are the plan and goal Markdown only. Rechecked the supported BlazorAuto/React profiles, account-free React/full retained Identity requirement, security/cache/test constraints and open PR state; no scope choice reopened. Preserved the active modified P3 handoff worktree. |
| P01 | Complete | Baseline source `fdd36a2e0691fd0e25186a8e8b8912ebcf5cadfa`; selected profile BlazorAuto. Full gate passed: BlazorAuto 211 passed/13 expected skips, React 203 passed/13 expected skips, lifecycle 3 passed/0 skipped, profile Python 32/32, React tests 31/31 plus API/typecheck/lint/build, format, common/cloud/observability/deployment/rendered-template, yamllint, ShellCheck and actionlint. Gate ran in WSL Ubuntu 24.04 native storage after old root-owned ignored DrvFs build outputs blocked the initial mounted-checkout attempt; final selected-profile Windows restore/build passed. |
| P02 | Complete | Inventory source `fdd36a2e0691fd0e25186a8e8b8912ebcf5cadfa`, 864 tracked paths. All paths classified by subsystem/kind; routes, redirects, HEAD/API routes, packages, configuration aliases, scripts/workflows, authored CSS/JS, DTOs and EF declarations indexed. Candidate register C-01–C-18 has explicit dispositions and owning packets. Ignored detail: `Plans.local/TemplateCleanup/Run-20261012/`. |
| P03 | Complete | [PR #189](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/189), exact head `21748b7ffd40812bf79d917f22ab2441d9f98a73`, passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38242840319/job/114789434599). Squash-integrated as `4ba9056a4f73cdc27e7b407a375649b4c5fcdce2`; exact-main [CI run](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38243672357) passed. Quick 10.35.0.4138 at `01dbeae5`: retained `Input.Passkey` and `AppOpenTelemetryOptions` setters because form/configuration binding consumes them; retained assembly markers, `ApplicationUser`, `BooksEndpointLogCategory` and the intentionally empty Blazor static-file hook. Removed only the explicit `Program` declaration flagged by ASP0027; `WebApplicationFactory<Program>` tests compile and run against the SDK-generated type. Code commit `326ec373`; full local gate passed (211/13 BlazorAuto, 203/13 React; 32 Python tests; format, common/cloud/observability/deployment audits, rendered templates, yamllint, ShellCheck and actionlint). No test count changed. Quick evidence is under ignored `Plans.local/TemplateCleanup/Run-20261012/quick/`. |
| P04 | Complete | [PR #190](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/190), exact head `46b4ecc016fbc3ba986d4f5b053954addc27586b`, passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38245770354/job/114799113045). Squash-integrated as `5988c14361cb57f71598f4db81c785cf2a30e5fd`; exact-main [CI run](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38246594118) passed. Removed the unread `BookSideView.Url` input and shelf assignments, plus the never-set outer `BookSideView.ForcedOpen` input/forwarding. Kept `BookcaseBook.Url`, API/detail URL flow, `BookPageView` site link and demo-only `BookCoverRenderer.ForcedOpen`. Mobile author-shelf and CRUD/details/site-link journeys passed. Full local gate passed: 211/13 BlazorAuto, 203/13 React, 32 Python tests, format, release/cloud/observability/deployment audits, rendered templates, YAML, ShellCheck and actionlint. No test-count or Tailwind class changes. |
| P05 | Local gate passed; PR pending | Input `origin/main` `5988c14361cb57f71598f4db81c785cf2a30e5fd`; branch `cleanup/template-p05-20261012`; code commit `fc17fcac2818c9a21aa3978df5776dd6b454beea`. Replaced the identical `DeleteControlX` branches with constant `372` and made stateless `PencilIcon` static. Kept state-dependent close-control positions and all geometry/markup behavior. Full local gate passed: 211/13 BlazorAuto, 203/13 React, 32 Python tests, restore, format, all release/cloud/observability/deployment audits, rendered templates, YAML, ShellCheck and actionlint. Desktop 1280×900 and narrow 768×1024 CRUD journeys passed; visual snapshot journeys passed at 1280×900 and 390×844, and the generated details/edit images were reviewed. At 390px, the existing full CRUD test stops at its unrelated desktop-only demo-menu precondition; the app correctly hides that link. No Razor class or Tailwind output changes. PR and exact-head verification pending. |
| P06–P11 | Pending | Execute small behavior-preserving cleanup PRs. |
| P12–P14 | Pending | Verify full Identity, atomically retire design demos, verify retained redirects. |
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

## 10. Resolved decisions and accepted defaults

The owner resolved the feature questions on **2026-10-12** and requested intelligent recommendations so the goal can run directly. Apply this contract without another preference round:

| Decision | Accepted policy and reason |
| --- | --- |
| D-01: design demos | Retire both public demo routes, menus, HEAD aliases, traffic scenarios and demo-only scaffolding. Keep every normal cover design and bookcase interaction. Blazor returns 404; React's existing SPA fallback is unchanged. |
| D-02: legacy URLs | Retain all three authorized Books redirect components and verify their exact mappings. Small compatibility shims still serve old links. |
| D-03: Identity | Retain the complete template account surface, including passkeys, external/Google login, 2FA, recovery, confirmation/reset and personal-data management. Retain its storage, dependencies and binding setters. |
| D-04: template capabilities | Retain both frontend profiles, all three deployment targets, PostgreSQL/Redis/Data Protection, simulation, observability and existing quality tools. Optional does not mean obsolete. |
| D-05: warning-driven abstractions | Retain separate typed endpoint handlers, frontend hook symmetry, assembly markers and discovery/configuration contracts. Simplify actual redundancies; do not invent generic wrappers, dummy reads or analyzer suppressions. |
| D-06: orphaned root artwork | Delete the unused root logo artifact if fresh consumer checks still show no required role. Retain only on concrete contrary evidence; Git history preserves the removed artifact. No cosmetic question is needed. |
| D-07: simulation TLS | Accept Q-001's explicit loopback-only opt-in, using the exact CLI/wrapper contract and HTTP/browser restrictions in P16. Prefer normal certificate validation; all other simulation gates remain required. |
| D-08: quality backlog boundaries | Complete overlapping Q-001, Q-006 and Q-007 work and Q-008 parser cleanup where justified. Q-004 supplies focused tests before changed modal behavior. Broad unchanged Identity coverage Q-003 and replacement of Caddy's verification mechanism Q-002 remain separate work, explicitly outside this cleanup's completion criteria. Structural collision review may proceed while preserving the current verification policy. |
| D-09: history and testing | Preserve active/historical plans, EF migrations and strict gates. Change test-count consumers in the same PR as their test changes. Use local/disposable fixtures; no live deployment is needed. |

There are **no open preference questions or established human-only blockers**. If fresh evidence disproves a source detail, correct the detail and follow the accepted policy. For a new unproven breaking removal, retain the current external behavior and record why. Escalate only a proven external hard stop after safe alternatives and independent work are exhausted; do not stop because routine implementation judgment is needed.
