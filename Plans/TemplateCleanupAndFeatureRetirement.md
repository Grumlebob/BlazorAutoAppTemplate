# Template cleanup and feature retirement

## Status and purpose

Status: **in progress**. Repository reconnaissance, planning audits, execution review, baseline validation and complete source inventory are complete. The owner resolved the feature-retirement decisions recorded in section 10 on 2026-10-12. No preference question blocks execution.

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
| Operator tooling | Preserve local running, Lighthouse, public browser checks, observability and optional source audits. Retire the standalone synthetic-traffic simulator; keep application telemetry and dashboards. |
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
| C-04 | `FrontendComposition.React.cs` accepts `configuration` but does not use it; `FrontendComposition.BlazorAuto.cs` needs the same argument. The Blazor static-files hook is intentionally empty. | P07 verified the project compiles exactly one profile implementation while common `Program.cs` calls the shared methods. Blazor consumes `configuration` for Identity registration; retain the matching React signature. Retain the empty Blazor static-files hook: `MapStaticAssets` serves that profile's assets, and the hook pairs with React's custom static-root middleware. Profile tests and sequential publish-switch checks pass. |
| C-05 | `BookSideView.ForcedOpen` is implemented, but shelf callers do not set it. Demos pass `ForcedOpen` through `BookDesignDemoCover` to `BookCoverRenderer`. | Remove the unused outer option in P04; remove the renderer's demo-only forced-state option and branches in P13 after deleting its demo consumer. Preserve normal hover/focus motion. |
| C-06 | Root `grumlebet_gb_clean_smooth_v2.svg` was 144,015 bytes, outside both frontend asset roots. Tracked reference search found no consumer; the Web SDK content inventory and explicit publish items did not include it. Git history traces it to logo commit `6e745ffd`. | Removed as an abandoned root artifact in P09; the historical commit retains the artwork. |
| C-07 | `/books/design-demos` and `/books/design-demos/{DesignId}` have route components, navigation links, HEAD mappings, simulation scenarios and browser/render-mode tests. | Owner approved retirement. Remove the complete feature and its consumers atomically in P13; preserve normal bookcase artwork. |
| C-08 | `Routes/Create.razor`, `Details.razor`, `Edit.razor` redirect old URLs into the modal query flow. Two E2E journeys still use `/books/99999999` to show a missing-book state. | Owner directs removal of all three redirect shims. Keep missing-book coverage through the canonical `/books?bookId=99999999&bookMode=view` route; add no legacy compatibility or absence checks. |
| C-09 | README describes `Books:SeedLocalDefaults`; source reads `AuthorBooks:SeedAtStartup` with a default of `true` in `AuthorBookSeedExtensions`. | Confirmed documentation drift. Correct docs to actual behavior; changing seed defaults is a separate product change. Packet P10. |
| C-10 | React's `isbot` has no app import, but `FrontendProfiles.md` documents its React Router type-generation/prerender tooling role. Confirmed in the installed `@react-router/dev@8.4.0`: it declares `isbot` and its typegen checks for the direct manifest entry, printing an instruction to add it when absent. | Retain exact `5.2.2`; it is a documented framework tooling dependency, not dead app code. Packet P08. |
| C-11 | Quick `S1144` flags `Login.InputModel.Passkey` and nested `AppOpenTelemetryOptions` setters. Those models are form/configuration-bound. | False-positive risk. Preserve setters and prove binding behavior; do not remove them to reduce warnings. Packets P03/P12. |
| C-12 | Quick flags empty assembly markers, `BooksEndpointLogCategory` and the explicit `public partial class Program` declaration. | Retain assembly marker types used by architecture tests and the typed logger category used by endpoint logging. Remove only the explicit `Program` declaration: ASP0027 says it is unnecessary on the current ASP.NET Core target; verify the SDK-generated public `Program` remains usable by all `WebApplicationFactory<Program>` tests. Packet P03. |
| C-13 | Cancellation catches in `AuthorBookcaseState`, `UserBookcaseState` and `BookModalHost`; nested conditions/static candidates in `BookPageView`. | Review lifecycle semantics first. Removing a catch can change navigation or disposal behavior. Packet P11. |
| C-14 | Qlty settings duplication at `cloud_settings.py:154–168` and `deploy_settings.py:150–164`; matching validator entry-point setup. Existing backlog Q-007. | Candidate for narrow shared validation functions, with target-specific contracts preserved. Packet P18. |
| C-15 | `audit_deployment.py` leads Qlty's complexity ranking. The collision preflight, release validators and simulator options also rank highly. | P16 retires the simulator; no parser refactor remains. Complexity is not proof of dead deployment checks. Split only where equivalent rejection behavior can be demonstrated. Packets P18–P20. |
| C-16 | `RedisConfigurationTests.Production_AllowsMissingRedis_WhenFallbackIsExplicitlyAllowed` only accessed `factory.Services`. Existing Q-006 requests actual fallback assertions. | P15 now exercises in-memory cache reads/writes and confirms Redis connection/health-check registrations are absent. No registration change was justified. |
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
| Identity and compatibility packets still offered rejected alternatives. | P12 retains full Identity. Owner later directed removal of all three legacy Books redirects in P14; no legacy-route checks are added. |
| Simulation use and Caddy ownership verification needed disposition. | The owner now directs full retirement of the rarely used standalone simulator; P16/P17 remove its implementation and active guidance. P20 preserves the Caddy package checksum policy; replacing its verification mechanism remains a separate Q-002 project, not a cleanup blocker. |
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
| D | P12–P14 | Retain full Identity; retire design demos and legacy Books redirects. |
| E | P15–P17 | Cache/hosting cleanup and complete simulator retirement with focused checks. |
| F | P18–P21 | Deployment helpers, audit structure and CI/tooling. Keep shared-validator and audit changes separate. |
| G | P22–P24 | Documentation closure, re-audit and integrated verification. |

Do not combine all waves into one large PR. A packet with no justified changes needs only an evidence-backed retention entry, not an empty PR. Do not make extraction/refactoring a condition of completion when duplication is clearer than a generic abstraction.

Known required outcomes are C-01/C-02 cleanup, C-03 helper simplification when still unconsumed, C-09 documentation correction, complete C-07/C-17/C-18 demo retirement, Q-006 fallback assertions, full simulator retirement in P16/P17 and P18's shared pure validators. Q-001/Q-008 are superseded by removing their only product surface. If an outcome is already integrated upstream, verify it and record the commit instead of repeating it. Inventory/refactor packets may conclude retention, but cannot be used to skip these outcomes silently.

### 4.4 Dependency order and bounded substeps

The executable order is P00, P01, P02, P03, P04, P05, P06, P07, P08, P09, P10, P11, P12, P13, P14, P15, P16, P17, P18, P19, P20, P21, P22, P23, P24. This order satisfies the named dependencies. Do not make a later closure packet a prerequisite for an earlier change. P13 owns demo-specific style cleanup. P16 owns simulator code/config/CI removal and reduced test counts; P17 owns active documentation and backlog cleanup. Every packet owns its own test-count/audit-rule updates.

For P02, produce separate inventory sections for host/Core, Blazor/Razor, React, simulation, deployment/scripts, CI/quality tooling, assets/configuration and tests/docs. For P11, separate load/disposal review from save/delete review. For P17, separate active guide cleanup, generic observability guidance, and historical-plan/backlog disposition. For P20, extract one existing rule family at a time and run its positive/negative fixtures before the next family. A substep may be committed locally, but do not push/merge an intermediate state that breaks consumers or the gate. The atomic P13 substeps are specified in its packet.

## 5. Ordered implementation packets

### P00 — Apply the resolved scope contract

Dependencies: none. Inputs: sections 1, 2 and 10; current requirements and active plans.

1. Verify the support matrix in section 1 against the latest repository without changing its accepted policy.
2. Apply the recorded owner decisions: retire design demos and all three legacy Books redirects; retain full Identity. Do not ask for confirmation again.
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

**P13.1 — Freeze retained behavior.** Retire the Blazor `/books/design-demos` routes without preserving them as a supported contract or adding route-absence assertions; template clones commonly remove optional features. React continues its existing account-free SPA contract: unknown HTML navigation can receive its HTTP 200 shell and client not-found UI; non-HTML/unsafe navigation keeps its existing rejection. Do not add a global React 404 rule for this cleanup.

**P13.2 — Remove route/UI consumers.** Delete these four files under `BlazorAutoApp.Client/Features/Books/DesignDemos/`: `BookDesignDemos.razor`, `BookDesignDemoDetails.razor`, `BookDesignDemoCover.razor`, `BookDesignDemoCatalog.cs`. Remove desktop/mobile links and their selectors from `Features/AppShell/Layout/NavMenu.razor`. Remove the demo namespace import from the actual owning `_Imports.razor` file(s), checking both Client root and `Features/Books/_Imports.razor`. Remove the two demo `MapHead` entries in `BlazorAutoApp/Infrastructure/Hosting/HeadRequestExtensions.cs`.

**P13.3 — Remove dependent operator traffic.** In `BlazorAutoApp.Simulation/Scenarios/ScenarioCatalog.cs`, remove the `design-demos` and `design-demo-detail` scenarios. In `Scenarios/Scenario.cs`, remove the now-unused `ScenarioContext.NextDesignId()` and its duplicated design-ID list. Keep remaining weights and RPS/write safety budgets; normal weighted selection already handles a smaller catalog. Preserve historical report reading and document that new runs no longer emit the two scenario names. Add a focused catalog regression asserting no generated successful page scenario targets the retired prefix; update test counts immediately.

**P13.4 — Remove orphaned demo metadata.** Recheck every property consumer of `BookCoverDesignDefinition`. Remove `DemoTitleLines`, `DemoTitleY`, `DemoTitleDy`, `DemoTitleFontSize`, `DemoTitleFill`, `Note`, `CoverColors`, `PageColors` and `LineStroke` when their only consumers were demos. Remove their named arguments from all ten catalog entries. Delete `BookCoverDesignColors` if it then has no consumers. Preserve `Kind`, `Id`, `Label`, `Plate`, all ten artwork designs, enum values, plate data and catalog order; order affects deterministic design selection. Do not change normal `BookCoverTheme` values.

**P13.5 — Remove orphaned rendering knobs.** After deleting the demo wrapper and P04's outer option, remove `BookCoverRenderer.ForcedOpen` and collapse `PagesClass`/`CoverClass` to their current false-branch strings. Preserve hover, keyboard focus, focus-within and reduced-motion classes exactly. `TitleDy` is only customized by demos at the inspected source: if still true, replace its unused configurable parameter with the existing `1.2em` default in the renderer. Do not remove title layout inputs used by normal books.

**P13.6 — Preserve meaningful test journeys.** In `RenderModeHtmlTests`, replace the two demo rows in `StaticAndAccountPages_DoNotLoadInteractiveBlazorRuntime` with `/Account/Register` and `/Account/ForgotPassword`, retaining `/Account/Login`. Replace the demo row in `PublicPages_DoNotReferenceRemovedScopedCssBundle` with `/books`, retaining `/`. This preserves five positive theory cases for supported pages. Do not add route-absence or navigation-absence tests for retired demos. In `BooksE2ETests.Books_CanCreateViewEditCancelAndNavigateBack`, replace the anonymous demo detour with a retained `/Account/Login` round trip. In `SeededUser_BookcaseCrudSurvivesRefreshAndNavigation`, use authenticated `/Account/Manage` and return through existing home/interactivity helpers. Preserve all CRUD, refresh, missing-book and navigation assertions; do not delete these complete tests.

**P13.7 — Reconcile styles/docs/counts.** Remove only CSS rendered solely by the retired UI, regenerate `BlazorAutoApp/wwwroot/tailwind.css`, and remove the deleted namespace/type references. Replace the demo path in `docs/Test.md`'s Lighthouse example with `/books`; review other current docs/commands for active demo instructions. Preserve historical execution evidence in old plans, adding a superseded note only where needed. Apply section 4.2's same-PR count updates: the retained theory rows and existing E2E methods preserve their counts, the four new retired-route cases apply only to Blazor, and any new simulation test normally applies to both profiles. Measure final totals rather than hard-coding a guessed delta.

**P13.8 — Verify and integrate the complete retirement.** Search tracked production/current test/docs paths for `BookDesignDemo`, `NextDesignId`, `DemoTitle`, `design-demo-link`, `design-demo-menu-link` and the retired URL prefix. Current source and user-facing docs should have no retired route consumers; historical plans and the retirement record may describe the removed feature. Run geometry/shelf, affected render, both profile and targeted Books browser checks, plus the full local gate. Verify retained book navigation and React's unchanged SPA contract. Review normal shelf screenshots at narrow/wide widths before merging.

Verification and exit: routes, links, HEAD aliases, demo traffic, imports, metadata and forced-open-only branches are all removed in one green exact-head PR, followed by green exact-main CI. Normal art, hover/focus motion, account flows and canonical Books modal routes remain functional.

### P14 — Remove legacy Books redirect shims

Dependencies: P00/P11/P13. Inputs: `Routes/Create.razor`, `Details.razor`, `Edit.razor`, canonical modal route state and existing Books E2E journeys.

1. Confirm the three Razor components have no callers beyond their route declarations. Search production code, tests and current docs for old paths and component references; keep canonical `/books` modal routes, author routes, APIs and current links.
2. Delete `Routes/Create.razor`, `Details.razor` and `Edit.razor`. Do not add redirect, legacy-access or legacy-route-absence checks. Preserve no old-URL behavior for template clones.
3. Change the two existing E2E journeys that visit `/books/99999999` to use `/books?bookId=99999999&bookMode=view`. Keep their missing-book assertions and visual snapshot; this covers supported canonical flow without testing retired paths.
4. Run focused Books state tests and existing Books/visual Playwright journeys when local prerequisites are available. Run the full local gate, inspect the complete diff and route references, then open a code PR. Keep strict test counts unchanged; require green exact-head `build-test-push` before merge and green exact-main CI after merge.

Verification and exit: all three shims are deleted; current source, tests and docs contain no old Books route consumers. Canonical create/view/edit and missing-book behavior remain covered. No legacy compatibility or route-absence check exists. Exact-head and exact-main code gates pass.

### P15 — Clean cache and hosting internals behind stronger assertions

Dependencies: P06/P07/P11. Inputs: hosting/cache invalidation modules, Books cache options/services, Redis tests and Q-006.

1. Improve the existing Redis fallback test to assert the intended fallback registrations/behavior, alongside required-Redis startup failure. Prefer strengthening an existing test over adding duplicate tests.
2. Inventory cache interfaces, messages and options against both publishers/subscribers and cross-node tests. Remove only unused implementations or settings with complete evidence.
3. Preserve schema-versioned keys, app/environment channel isolation, local TTL fallback, publish/apply timeout behavior and post-write invalidation even when caller cancellation occurs.
4. Preserve shared Redis connection reuse, Data Protection persistence, health checks, forwarded-header trust and fail-open request observability.

Verification and exit: Redis configuration/reuse, invalidation, Books caching/cross-node, forwarding, rate-limiting and observability tests pass. No runtime infrastructure requirement is weakened by cleanup.

### P16 — Retire the standalone synthetic-traffic simulator

Dependencies: P02/P15. Inputs: `BlazorAutoApp.Simulation`, simulator tests and project references, runner/report scripts, CI and quality configuration.

1. Confirm simulator has no runtime dependency from the app, client, Core or deployment. Identify every tracked entry point and consumer before deletion. Keep PostgreSQL/Redis, app telemetry, dashboards, alert rules, Lighthouse, public browser checks and ordinary E2E coverage.
2. Delete the complete `BlazorAutoApp.Simulation` project and its tests, including the test that only asserts the simulator is not deployed. Do not replace deleted tests with route/project absence checks. Remove solution and test-project references.
3. Delete `RunSimulation.ps1`, `RunSimulation.cmd`, `RunSimulationMatrix.ps1`, `AnalyzeSimulationReports.ps1`, the simulator README and `docs/SimulationGuide.md`. Remove the CI wrapper-help step, `.dockerignore` exclusion and Sonar coverage exclusion. Keep `Microsoft.Playwright` package references still used by E2E tests.
4. Inspect `Directory.Packages.props`, lockfiles, Docker inputs and workflow call sites for simulator-only dependencies. Remove only dependencies proven unused by the remaining tree; do not change shared Playwright or app dependencies.
5. Update every strict .NET test-count consumer in this PR: `docs/Test.md`, `Scripts/CI/validate-frontend-profiles.sh`, `Scripts/Quality/Invoke-SonarAnalysis.ps1`, `Scripts/Quality/sonar_report.py` and its count fixtures. Derive exact profile totals from the full test run; preserve 13 expected opt-in skips and profile-specific exclusions.
6. Run focused solution restore/build/test after removing project references, then the full local gate. Keep `dotnet build` and `dotnet test` sequential. Check that removal does not alter deployment manifests or app image contents unexpectedly.

Verification and exit: solution contains no simulator project; all remaining code/configuration builds cleanly; exact profile counts match executed tests; full local gate and exact-head/exact-main checks pass. No live synthetic traffic or deployment is needed. Complete P17's docs/backlog cleanup in the same feature-retirement PR so merged code has no broken simulator guidance.

### P17 — Remove simulator guidance and close superseded findings

Dependencies: P16. Inputs: README and active docs, `Plans/CodeQualityImprovements.md`, historical simulation plan.

1. Remove simulator commands and claims from README and local-running guides. Remove simulator paths from fork/migration prompts, feature-development guidance and frontend-profile descriptions.
2. Remove the simulator-only Synthetic Traffic section from `docs/ObservabilityGuide.md`. Keep OpenTelemetry setup, metric names, dashboards, alerts, and query guidance. Explain that normal app requests produce telemetry; do not add a replacement traffic generator.
3. Mark Q-001 and Q-008 superseded because P16 removed their only target. Mark simulator-only analyzer observations as historical. Preserve `Plans/ImprovedSimulation.md` as a completed historical record; do not rewrite its old execution log.
4. Search active source, workflows and current docs for runnable simulator paths, flags, project names and artifacts. Exclude preserved historical plan records from stale-reference cleanup. Add no test whose purpose is to prove removed simulator or routes stay absent.

Verification and exit: active documentation has no broken simulator commands or promises; application observability guidance remains accurate. Include this packet in P16's mixed code/docs PR, run the full code gate on the combined diff, and verify exact-head and exact-main CI. No separate docs-only PR is needed because the docs describe the same removed feature.

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

1. Review jobs, inputs, artifacts, environment settings and helper scripts against all workflow/manual/operator callers. Optional or manually dispatched tooling is not dead solely because it rarely runs. Remove the four-case `RetiredBookDesignDemoRouteTests` and the desktop/mobile E2E assertions that only require retired demo links to stay absent; do not replace them with other absence checks.
2. Remove genuinely superseded paths with their documentation/tests. Preserve exact release SHA/run/attempt provenance, separate PR validation/main publishing and frontend image smoke.
3. Audit the same-PR count updates already required by section 4.2. Search actual expectations in the profile gate, CI, `Invoke-SonarAnalysis.ps1`, `sonar_report.py`, `validate_vitest_results.py`, relevant fixtures and `docs/Test.md`. Compare discovered cases, profile traits and TRX results after the four retired-route cases are removed. Update every current count consumer from measured TRX results in this PR; preserve honest historical baseline measurements. P16 owns the reduced totals from simulator test removal; do not defer those updates to P21.
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
| Simulation | Retired by P16. No simulator contract, absence or wrapper-help tests remain. |
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
| Owner decisions | Complete | 2026-10-12: remove design demos and all three legacy Books redirect shims; retain Identity as part of the template. Do not add legacy compatibility or route-absence checks. |
| Worktree cleanup | Initial pass complete; final recheck pending | 2026-10-12: removed 13 stale checkouts from this repository; the 10 deleted local branches matched merged PRs #135, #154, #159, #162, #164, #167, #171, #172, #185 and integrated PR #153. Preserved the dirty React P3 worktree and the unmerged `coord/node-inventory-handoff` branch/ref. Current list has this cleanup checkout and P3 only; repeat at P24. Removed Kilo CLI/settings/processes and Kilo-owned worktrees. Deletion of remaining user-local Kilo application data and VS Code extension folders was blocked by command policy; record for manual cleanup without retrying through another route. |
| P00 | Complete | At `origin/main` `fdd36a2e`, changes since the research source `de90f08d` are the plan and goal Markdown only. Rechecked the supported BlazorAuto/React profiles, account-free React/full retained Identity requirement, security/cache/test constraints and open PR state; no scope choice reopened. Preserved the active modified P3 handoff worktree. |
| P01 | Complete | Baseline source `fdd36a2e0691fd0e25186a8e8b8912ebcf5cadfa`; selected profile BlazorAuto. Full gate passed: BlazorAuto 211 passed/13 expected skips, React 203 passed/13 expected skips, lifecycle 3 passed/0 skipped, profile Python 32/32, React tests 31/31 plus API/typecheck/lint/build, format, common/cloud/observability/deployment/rendered-template, yamllint, ShellCheck and actionlint. Gate ran in WSL Ubuntu 24.04 native storage after old root-owned ignored DrvFs build outputs blocked the initial mounted-checkout attempt; final selected-profile Windows restore/build passed. |
| P02 | Complete | Inventory source `fdd36a2e0691fd0e25186a8e8b8912ebcf5cadfa`, 864 tracked paths. All paths classified by subsystem/kind; routes, redirects, HEAD/API routes, packages, configuration aliases, scripts/workflows, authored CSS/JS, DTOs and EF declarations indexed. Candidate register C-01–C-18 has explicit dispositions and owning packets. Ignored detail: `Plans.local/TemplateCleanup/Run-20261012/`. |
| P03 | Complete | [PR #189](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/189), exact head `21748b7ffd40812bf79d917f22ab2441d9f98a73`, passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38242840319/job/114789434599). Squash-integrated as `4ba9056a4f73cdc27e7b407a375649b4c5fcdce2`; exact-main [CI run](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38243672357) passed. Quick 10.35.0.4138 at `01dbeae5`: retained `Input.Passkey` and `AppOpenTelemetryOptions` setters because form/configuration binding consumes them; retained assembly markers, `ApplicationUser`, `BooksEndpointLogCategory` and the intentionally empty Blazor static-file hook. Removed only the explicit `Program` declaration flagged by ASP0027; `WebApplicationFactory<Program>` tests compile and run against the SDK-generated type. Code commit `326ec373`; full local gate passed (211/13 BlazorAuto, 203/13 React; 32 Python tests; format, common/cloud/observability/deployment audits, rendered templates, yamllint, ShellCheck and actionlint). No test count changed. Quick evidence is under ignored `Plans.local/TemplateCleanup/Run-20261012/quick/`. |
| P04 | Complete | [PR #190](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/190), exact head `46b4ecc016fbc3ba986d4f5b053954addc27586b`, passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38245770354/job/114799113045). Squash-integrated as `5988c14361cb57f71598f4db81c785cf2a30e5fd`; exact-main [CI run](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38246594118) passed. Removed the unread `BookSideView.Url` input and shelf assignments, plus the never-set outer `BookSideView.ForcedOpen` input/forwarding. Kept `BookcaseBook.Url`, API/detail URL flow, `BookPageView` site link and demo-only `BookCoverRenderer.ForcedOpen`. Mobile author-shelf and CRUD/details/site-link journeys passed. Full local gate passed: 211/13 BlazorAuto, 203/13 React, 32 Python tests, format, release/cloud/observability/deployment audits, rendered templates, YAML, ShellCheck and actionlint. No test-count or Tailwind class changes. |
| P05 | Complete | [PR #191](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/191), exact head `21a5f0fb1c1ebabe0f6e52aa7f3938f71c42b062`, passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38248405963/job/114808449624). Squash-integrated as `5dba345e70a1090d577d34ce05d1d78c81099e56`; exact-main [CI run](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38249332928) passed. Input was `origin/main` `5988c14361cb57f71598f4db81c785cf2a30e5fd`; code commit `fc17fcac2818c9a21aa3978df5776dd6b454beea`. Replaced the identical `DeleteControlX` branches with constant `372` and made stateless `PencilIcon` static. Kept state-dependent close-control positions and all geometry/markup behavior. Full local gate passed: 211/13 BlazorAuto, 203/13 React, 32 Python tests, restore, format, all release/cloud/observability/deployment audits, rendered templates, YAML, ShellCheck and actionlint. Desktop 1280×900 and narrow 768×1024 CRUD journeys passed; visual snapshot journeys passed at 1280×900 and 390×844, and the generated details/edit images were reviewed. At 390px, the existing full CRUD test stops at its unrelated desktop-only demo-menu precondition; the app correctly hides that link. No Razor class or Tailwind output changes. |
| P06 | Complete | [PR #193](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/193), exact head `d805ab4a84f04c82ee94336e74c1e72c2ba40d1e`, passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38250743960/job/114816074986). Squash-integrated as `796e89704c18903ffe8c52f63b6c02baa381daa3`; exact-main [CI run](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38251622748) passed. Input `origin/main` was `16a8a26708f9c06bc7bb06ff7bf559b9918a429d`; code commit `726c6afa8b670642ac1e06d5b195ac49fbbc0f25`. All five `WithAuthorizationResponses` callers ignore the helper's return and end the endpoint chain there. Changed its return type to `void`; preserved the 401/403 metadata and authorization requirement. Full local gate passed: 211/13 BlazorAuto, 203/13 React, 32 Python tests, restore, format, release/cloud/observability/deployment audits, rendered templates, YAML, ShellCheck and actionlint. `EndpointSurfaceTests` and `OpenApiMetadataTests` passed; React `api:check` passed with generated OpenAPI and TypeScript unchanged. No test-count, CSS or schema changes. |
| P07 | Complete | [Documentation-only PR #195](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/195) used `[skip ci]`; integrated as `bc23d8fc816dcb5273dd228859180a29814d8662`, then fetched and verified on `origin/main`. Input `origin/main` was `d88250b787475abaa7b616fcdd5953a70ec7fa1f`. Kept the paired `FrontendComposition` signatures and empty Blazor static-files hook after confirming project conditions select one implementation and `Program.cs` uses a shared contract. Reviewed bound app-name, database, forwarding, rate-limit, Data Protection and cache-invalidation settings against consumers/tests; no unused bound option remains. Kept React's `{*path:nonfile}` catch-all parameter because ASP.NET routing uses its name/policy to select fallback requests. Focused tests passed: 16/16 Blazor composition/hosting/asset/render-mode; 35/35 React composition/hosting/response/HEAD with the documented Blazor-profile exclusion. Both profile builds passed with zero warnings. Sequentially published React then BlazorAuto to one disposable directory: React retained `wwwroot/index.html` without Blazor runtime assets; switching back restored `_framework` and removed the React index. No source, test, CSS or schema change. |
| P08 | Complete | [Documentation-only PR #197](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/197) records the audit on input `origin/main` `9a9c3a93d2d38f252453ca0f0c4b49b352250b5f`, branch `cleanup/template-p08-20261012`. No package or code removal was justified: all 36 central NuGet versions have matching references; React imports, route modules and exports are consumed by application routes, tests or framework conventions; generated OpenAPI and React Router types remain generated contracts. `isbot` is directly required by React Router Dev typegen. Both npm lockfiles installed cleanly; React API check, strict typecheck, lint, all 31 tests and static prerender build passed. Client npm tree matched its manifest; axe-core resolved, Tailwind CLI started, Lighthouse reported 13.5.0. npm warned that local install policy blocked the optional `@parcel/watcher` build script; this did not block the Tailwind CLI. Sequential React and BlazorAuto solution restores/builds passed with zero warnings, then the default BlazorAuto NuGet graph was restored. Tracked manifests, lockfiles and generated contracts are unchanged. No additional scanner was introduced. |
| P09 | Complete | [PR #198](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/198) records input `origin/main` `5333edc72b065d673226c7a2e82eacfeb0681b4c`, branch `cleanup/template-p09-20261012`. Removed the unreferenced root SVG after confirming no source/build consumer. Removed unused `.account-button-secondary`, `.account-code-grid`, `.account-form`, `.account-subtle` and `.field-validation-error` rules; repository-wide search found no markup, dynamic string, test, or documented consumer. Preserved Blazor's generated `validation-message`, valid/invalid and error-boundary classes; bookcase scrolling/hover/focus/reduced-motion behavior; reconnect styles; and demo-only classes pending P13. Tailwind output was unchanged because no Razor class or Client/Styles input changed. Full local gate passed: 32 Python tests; format; BlazorAuto 211 passed/13 expected skips and React 203/13, zero warnings; common/cloud/observability/deployment audits; rendered templates, YAML, ShellCheck and actionlint. Focused `VisualSnapshotE2ETests` passed 1/1; reviewed home, login and account-manage captures. For that run, the repo app used temporary PostgreSQL host port 5434 because the configured 5433 was occupied; E2E cleanup used the matching local connection, and the test-prefix account/book counts returned to zero. Stopped the repo stack through `RunLocal.ps1 -StopStack`, preserving volumes. Squash-integrated as `3bf93d688fc1b17ab8903908f321efa8fd7b31d0`; fetched `origin/main` matched, and exact-main [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38257451863) passed on that SHA. |
| P10 | Complete | Corrected README seeding documentation to `AuthorBooks:SeedAtStartup`, default `true`, and the actual public catalog. Distinguished public author-book seeding from Development/local-Docker login-account seeding; verified React skips account seeding and deployment Compose disables it. Removed duplicate `FromLogContext` and `WithEnvironmentName` entries from base/Docker Serilog config while preserving the programmatic context, environment, activity trace/span and application enrichers plus configured machine name. Audited appsettings keys, code readers, `.env.example`, and local/deployment producers; found no additional dead setting. Full local gate passed: 32 Python tests; format; BlazorAuto 211/13 and React 203/13 with zero build warnings; common/cloud/observability/deployment checks, rendered templates, YAML, ShellCheck and actionlint. Merged [PR #199](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/199) as `7880416ccb5526c51b0d8f954db9ce6a833b406e`; exact-main [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38260347107) passed on that SHA. |
| P11 | Complete | [PR #200](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/200) head `ea5136f50498079495b9cabf024bbddc85642ea0` passed exact-head [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38263220156). Removed unused `CurrentUserId`, made the user-only `Books` collection private, and removed the unused `userId` parameter from `ApplyLoadResult`; retained version guards that reject stale user/author loads and writes. Added three focused state tests and expanded existing book E2E flows for modal Escape, save retry, delete cancel, and failed-delete recovery. Failed delete now keeps the loaded book visible and announces the operation error. Updated frontend-profile and Sonar expected counts, plus the deployment audit's matching guard. Focused state tests passed 3/3; `BooksE2ETests` passed 3/3 with database test data cleaned up. Tailwind rebuilt with no generated diff. Full local gate passed: 32 CI Python tests (4 skipped), formatting, BlazorAuto 214/13 and React 206/13 with zero build warnings, 25 Sonar-report tests, common/cloud/observability/deployment checks, rendered templates, YAML, ShellCheck and actionlint. Merged as `e876615f0a989cc17fc08457bcc64fd0e78e23f4`; exact-main [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38264180374) passed. |
| P12 | Complete | [Documentation-only PR #201](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/201) used `[skip ci]`, merged as `b5b1d838ffb7cda282348cf3d76afa6e6817ee2a`, then fetched and verified on `origin/main`; `git diff --check` passed, and the docs-only exception required no CI wait. Retained full Identity after reviewing account routes and helpers. Registration/login/logout, email confirmation/reset, external login, passkeys, 2FA/recovery, account management and personal-data flows remain routed and wired to Identity services/endpoints. Identity registration/login/profile/passkey/password-reset E2E passed 1/1; auth-denial, principal-accessor and local-account-seed tests passed 10/10. Test account cleanup count returned zero. No Identity code removal was justified; no real OAuth credentials, email provider or passkey hardware was needed. |
| P13 | Complete | [PR #202](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/202), exact head `5b5fb4bb08d84c4db6fc4bb38cebd31847832ad9`, passed exact-head [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38270220064). Squash-integrated as `7f388b673439bc0ea83c812e79a21f377cf3dd40`; exact-main [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38271194124) passed on that SHA. Removed the four design-demo pages, nav links/imports/HEAD aliases, both simulation scenarios and `NextDesignId`; removed demo-only cover metadata/types and forced-open/title-offset inputs while preserving the ten ordered designs, IDs, labels, plates and normal hover/focus/reduced-motion behavior. Updated E2E detours, retained positive render cases, added desktop/mobile nav absence assertions, Blazor-only GET/HEAD 404 coverage and a simulation catalog regression, refreshed current test-count consumers/docs, and rebuilt Tailwind. Focused route/geometry/scenario tests passed 10/10; Sonar report tests 25/25; Python discovery passed for Scripts/CI (58), LocalSingleNode (141), Common (82) and LocalCluster (23), plus every `test-*.sh` fixture in those deployment test folders. Format, both profile builds/tests (BlazorAuto 219 passed/13 expected skips; React 207/13, zero build warnings), release/cloud/observability/deployment audits, rendered templates/YAML, ShellCheck and actionlint passed. Books E2E passed 3/3; visual snapshot journey passed at 390x843 and 1281x900 (1/1 each), and normal shelf art was reviewed at both widths. E2E cleanup returned test users/books to zero. The repo stack used PostgreSQL port 5434 because an external container owns 5433; it was stopped with `RunLocal.ps1 -StopStack -SkipDockerCleanup`, preserving volumes. Tailwind output changed and is included. |
| P14 | Complete | Input `origin/main` `7f388b673439bc0ea83c812e79a21f377cf3dd40`; branch `cleanup/template-p14-20261012`. Owner clarified that clones remove legacy features: deleted `Routes/Create.razor`, `Details.razor` and `Edit.razor`; added no legacy compatibility or route-absence checks. Updated both existing missing-book E2E visits to canonical `/books?bookId=99999999&bookMode=view`. Current Books modal coverage and strict counts stay unchanged. Restore, format and full local gate passed: BlazorAuto 219/13 expected skips, React 207/13, 32 Python tests (4 skipped), settings/observability/deployment/rendered-template/YAML/ShellCheck/actionlint checks passed. Existing Books and visual snapshot browser journeys passed 2/2. Existing screenshots were restored after preserving new captures in ignored `Plans.local`; local stack stopped with `-SkipDockerCleanup`, preserving volumes. [PR #203](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/203) exact head `39ece6157149e7a424dac43fa9a3922d3c42426d` passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38274220094), merged as `c5a0b9a0486e04aec3792e10efb85566eca1a156`. The exact-main [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38275861583) passed on `6cd82940ccc3161aea5e8da5f97325f100887cf9`. |
| P15 | Complete | Input `origin/main` `c5a0b9a0486e04aec3792e10efb85566eca1a156`; branch `cleanup/template-p15-20261012`; merged latest `origin/main` `6cd82940ccc3161aea5e8da5f97325f100887cf9` as `efd6e94d`. Strengthened the existing Redis fallback test: in-memory `IDistributedCache` reads/writes succeed, while `IConnectionMultiplexer` and the `redis` health check are absent; the production-required-Redis failure test remains. Inventory confirmed cache keys/options, invalidation interfaces, both publishers, subscriber, no-op fallback, and cross-node tests all have consumers, so no cache implementation or setting was removed. Focused tests passed 2/2; full local gate passed on the P15 change before merging latest main, with BlazorAuto 219/13 expected skips, React 207/13, 32 Python tests and all settings, observability, deployment, render, lint and actionlint checks. [PR #205](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/205) exact head `c33aea3ae856d550b35074801d189adecea6fbe8` passed [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38277026193), squash-merged as `eca338b334bb7069487debec840664a710ff5553`; exact-main [build-test-push](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38278455688) passed on that SHA. |
| P16–P21 | Pending | Retire simulator, then execute bounded deployment and tooling packets with focused checks. |
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
| D-01: design demos | Retire both public demo routes, menus, HEAD aliases, traffic scenarios and demo-only scaffolding. Keep every normal cover design and bookcase interaction. Add no route-absence or navigation-absence tests for this retired feature; React's existing SPA fallback remains unchanged. |
| D-02: legacy URLs | Delete all three legacy Books redirect components. Template clones commonly remove old features, so preserve no compatibility promise. Keep current `/books` query-modal routes and their behavior; add no legacy URL or route-absence checks. |
| D-03: Identity | Retain the complete template account surface, including passkeys, external/Google login, 2FA, recovery, confirmation/reset and personal-data management. Retain its storage, dependencies and binding setters. |
| D-04: template capabilities | Retain both frontend profiles, all three deployment targets, PostgreSQL/Redis/Data Protection, observability and existing quality tools. Remove the rarely used standalone simulator; keep app telemetry, dashboards and alerts. |
| D-05: warning-driven abstractions | Retain separate typed endpoint handlers, frontend hook symmetry, assembly markers and discovery/configuration contracts. Simplify actual redundancies; do not invent generic wrappers, dummy reads or analyzer suppressions. |
| D-06: orphaned root artwork | Delete the unused root logo artifact if fresh consumer checks still show no required role. Retain only on concrete contrary evidence; Git history preserves the removed artifact. No cosmetic question is needed. |
| D-07: simulator retirement | Delete the simulator implementation, tests, wrappers, active guide, CI hook and active references as complete vertical retirement. Do not retain optional CLI compatibility or simulator-absence tests. Q-001/Q-008 become superseded; no simulator TLS or parser work remains. |
| D-08: quality backlog boundaries | Complete overlapping Q-006 and Q-007 work. Q-004 supplies focused tests before changed modal behavior. Broad unchanged Identity coverage Q-003 and replacement of Caddy's verification mechanism Q-002 remain separate work, explicitly outside this cleanup's completion criteria. Structural collision review may proceed while preserving the current verification policy. |
| D-09: history and testing | Preserve active/historical plans, EF migrations and strict gates. Change test-count consumers in the same PR as their test changes. Use local/disposable fixtures; no live deployment is needed. |

There are **no open preference questions or established human-only blockers**. If fresh evidence disproves a source detail, correct the detail and follow the accepted policy. For a new unproven breaking removal, retain the current external behavior and record why. Escalate only a proven external hard stop after safe alternatives and independent work are exhausted; do not stop because routine implementation judgment is needed.
