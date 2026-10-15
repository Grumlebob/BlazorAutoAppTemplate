# CarbonCalculator implementation checkpoints

Status: planned work only, 2026-10-15. Use [the delivery plan](../../CarbonCalculatorDelivery.md) for the full packet order and gates, [FeatureSpecification.md](FeatureSpecification.md) for behavior and [Acceptance.md](Acceptance.md) for proof obligations. The owner approved the latest design; no packet requires another mockup selection.

This file splits the product work into reviewable changes. A numbered checkpoint can be a small PR, but its parent packet is complete only when the whole visible slice works. Do not create one broad backend phase followed by one broad frontend phase. Every public operation includes validation, generated contract, UI state/error handling and evidence in its slice.

## 1. Decisions before dependent work

### D01 — Capture the approved design

1. Record the owner's approval of the current direct-navigation mockup in the downstream progress ledger.
2. Preserve a compact screenshot/contact-sheet reference and component/token brief in the product repository when rights and paths are safe. Ignored temporary controller assets are not a runtime dependency.
3. Recreate Dashboard, its compact estimate/list header, direct Material/Transport/Documents links, one delivery workspace and secondary About from the approved brief.
4. Treat unimplemented controls in the preview as illustrative. Do not copy the prototype's duplicated function overrides, inline event handlers or local emissions formulas into React.
5. Mark D01 complete after the implementation brief is retained. Responsive/accessibility acceptance still occurs against real implementation; another color/layout approval is not a prerequisite.

### D02 — Resolve saved-project ownership/lifetime

1. Follow the owner's authentication investigation in [ReactAuthenticationFoundation.md](../../ReactAuthenticationFoundation.md). The current recommendation is a reusable Identity/cookie/React foundation and authenticated server-owned projects. Device-local storage in FeatureSpecification.md is an unselected alternative. Record the chosen credential/ownership policy before implementing either.
2. Record the answer and storage/lifetime statement in Requirements and Privacy before P08A or P12A. The old tab-only design is superseded as a recommendation, not silently promoted to production.
3. If device-local is approved, use IndexedDB and the local/server split below. If cross-device is chosen, prepare a focused account/ownership/migration packet, update the schema/access rules and revise authentication cleanup before implementing dependent storage. Do not ship anonymous server CRUD as a shortcut.
4. Keep foundation import, profile cleanup, source QA, pure domain work and provider adapters progressing while the answer is pending.

## 2. Foundation packets P01–P08

| Checkpoint | Concrete output | Failure that must stop promotion |
| --- | --- | --- |
| P01 baseline | Full upstream SHA with exact-main successful CI, current guide/workflow inventory and destination-state evidence | Empty-repo import assumed without checking remote |
| P02 seed | Own private origin, safe app/image identity, Actions held until eligible runner, retained upstream provenance | A tool still defaults to template/Books or destination contains unknown work |
| P03 capacity | CarbonCalculator-specific eligible runner on the existing node, separate registration/service state, green product main | Existing template runner removed/rebound; inherited runner labels target another app |
| P04 React-only | Blazor dependency removal and replacement audits, retained browser test tooling, React-only build/image | Razor/WASM build path still accepted or shared assets deleted first |
| P05 single node | Shared audit/check relocation, caller inventory and removed target rejection | LocalSingleNode imports a deleted Cloud/LocalCluster helper |
| P06 rename | Explicit project/path/manifest/namespace map, Linux build and generated-contract drift check | Source/run/image/migration identity differs between publication and CD |
| P07 product docs | Current README/Requirements/Test/Operations and attribution; obsolete fork language removed | Required audit rules silently deleted with a guide |
| P08 SPA shell | Known routes, section navigation semantics, safe reserved-path/404 behavior, strict CSP and acceptance-profile binding | API/asset errors return HTML, private paths are prerendered or Books acceptance remains final |

Keep the full removal inventories and local/PR/main gates in the main plan. Do not rename code that P04/P05 will delete. P03 uses the already approved extra registration on the existing node, never a bootstrap of the controller PC.

## 3. P08A — Project and delivery persistence through the approved shell

Prerequisites: P08, D01 and D02. No routing key is required. This packet introduces an actual useful editable record, with calculation explicitly input-needed until its handler lands.

1. Add feature-owned UI state modules under `app/features/site-receipts`: project context, delivery edit buffer, validation model and local-store adapter. Use route composition only for navigation. Do not put the complete application in a global mutable object.
2. Define/version IndexedDB stores for projects, deliveries, attachment blobs/metadata and saved snapshots. Keep browser schema migration separate from EF server migration. Add atomic upgrade/rollback-safe failure behavior; do not erase a database on an unsupported version.
3. Implement create/select/rename project with name and optional unresolved site. An empty installation is empty; sample project loading is explicit and separately labelled.
4. Implement Add delivery with one generated stable ID, empty quantity/supplier/origin/reference and optional received date. Add Material/Transport/Documents section routes and preserve raw edit strings while switching.
5. Save incomplete records atomically without calculation. Return to the original Dashboard context and show success only after the transaction commits. Add specific retry/export behavior for write/quota failure.
6. Implement open/edit/update for the same ID with local revision checks. Notify other tabs of changes and offer reload/save-as-new on conflict. Do not overwrite an unsaved buffer.
7. Implement leave handling: Save, Discard, Stay when dirty; section switches are safe without a prompt. The browser-close warning is best effort, not the sole protection.
8. Implement delivery and project deletion with named/count-aware confirmation and owned attachment reference cleanup. Delete only the current owner's records; keep exported copies outside app control.
9. Add bounded local search/filter/order/paging and direct Dashboard links to each delivery section. No provider calls occur during search, section switching, save or project selection.
10. Exercise refresh/browser restart, two projects, partial save, edit without duplication, two-tab conflict, failed writes, unknown deep link and cancelled/completed deletion. Use fresh storage profiles for deterministic evidence.

Exit: the real React app can save/reopen a project and an incomplete delivery, navigate directly to its useful sections and preserve data under D02. It must not show a fabricated estimate yet.

## 4. P09–P10 — First real route slice

1. Intake source JSON and manifest into staging; schema-validate IDs/refs/units without promoting numeric approval strings.
2. Implement `GetCapabilities` with configured/not-checked/last-outcome distinctions. Health checks do not consume provider calls.
3. Implement `SearchPlaces` end to end with typed Pelias adapter, cancellation, safe errors, generated types and selectable candidate UI. Test ambiguity, no matches and selected-text invalidation.
4. Implement `FindRoadRoute` through the shared routing feature with HGV restrictions, ferry avoidance, provider response validation and bounded cache/budget. No invented alternate route parameter.
5. Build one Route Explorer that is embedded under delivery Transport and reachable as a contextual standalone route. Require explicit submitted queries, not mount/focus refetch.
6. Finish map/card/table synchronization and a no-tiles fallback. Propagate source time/precision per road leg and preserve evidence through a saved route envelope.
7. Add schema-safe failure UI for missing/wrong key, 429, timeout, malformed response, unsupported place and cancel/superseded query. An unavailable route does not prevent saving the delivery.
8. Capture a bounded real request from new locations with a server key when available. Re-enter Aarhus instead of Copenhagen and prove changed geometry/source data. Keep fixture results distinct.

Exit: an arbitrary supported user-selected route works in the actual app/API with a real HGV response or a real provider error. A generated client, mock server or fixture alone does not complete VS1.

## 5. P11 — First source-backed material and freight calculation

1. Independently check timber source fields, unit/density/indicators/revision/rights and fit; stage unresolved fields.
2. Implement immutable quantity/conversion value types and explicit unknown states. Test source-based conversion and nonfinite/locale ambiguity rejection.
3. Add match candidate search/selection with exact/proxy/metadata-only/transport-only decisions, generated contract and actual Material UI. Persist consent against exact source/input revision.
4. Add pure load-allocation policy and route restriction normalization. Preserve separate material volume and cargo/packaging volume.
5. Implement `CreateEstimate` for the reviewed EPD production indicators and route-based cargo-tkm method. Bind server-issued route data to the submitted routing fingerprint; never accept client distance/factor numbers as official.
6. Return calculation nodes, source refs, exact decimals, method/module/indicator, evidence dimensions and coverage. Add the shared estimate panel with contextual Calculate estimate/Update estimate states; keep Save delivery independent and do not create a review page. Route updates remain explicit Search routes operations.
7. Support independent production-only, transport-only and per-unit outputs. Save partial records; do not require an EPD or actual quantity for standalone route exploration.
8. Add explicit offline sample loading using fixture data and local schematic, with per-leg/sample labels in UI and export. The real app stays live by default.
9. Prove actual C# engine/API/React outputs for the supplied timber/freight goldens, changed quantity, changed source consent and stale/racing responses. The source bundle's helper functions are reference data checks only.

Exit: a real delivery can produce separated, source-backed production and indicative freight with inspectable arithmetic, while missing inputs remain explicit.

## 6. P11A — Standard-material method without a routing dependency

1. Retain official source edition/hash and review notes for the method registry. Separate material-line calculations from any future project additions. Record eligibility and received/incorporated quantity basis.
2. Define stable category IDs and explicit mappings from material taxonomy. Mark ambiguous compound products unmapped; do not select the lowest factor or derive from EPD title alone.
3. Implement `AssessStandardTransport` as a pure decimal policy called through `CreateEstimate`. Reject unsupported category/unit/quantity-basis claims with typed reasons.
4. Add standard-versus-route basis selection to Transport. Exploring routes does not change the active basis until an explicit selection. Missing dispatch or provider configuration does not block a valid standard line.
5. Return normalized kg, exact factor/category/source revision, material-line result and scope nodes. Preserve supplier/dispatch facts even if unused by the method.
6. Prove timber 148 and brick 45 goldens under their reviewed method/basis. Also prove received-basis qualification, missing quantity, unmapped category, changed source edition, no EPD and no key.
7. Keep eligibility/current-result status distinct from formal regulatory compliance. No site A4/A5 pass/fail is produced by these line totals.

Exit: independent source-backed standard material lines work end to end. Live routing/ferry commitments remain separate mandatory scope.

## 7. P11B — Dashboard totals, edit invalidation and source inspection

Start pure fingerprint/aggregation rules alongside P11/P11A. Complete P12's persistent runtime/key ring before shipping signed aggregation. Packet labels group work; the concrete dependency order is P11/P11A, P12, P11B, P12A, P12B. Do not introduce a P11B/P12 completion cycle.

1. Define separate fingerprints for routing inputs, numeric calculation inputs and report context. Add the dependency table from FeatureSpecification.md as named domain/UI rules.
2. Mark edited results stale immediately; keep the prior snapshot immutable. Ignore a late response if its fingerprint/edit revision no longer matches. Preserve source history without counting old results as current.
3. Sign immutable snapshot envelopes with the app's persisted signing key ring; do not include access tokens in signatures/exports. Verification checks schema/key revision and normalized content. Unknown keys require explicit recalculation rather than trusting client totals.
4. Implement `AggregateProjectTransport` as server-owned pure aggregation. Validate signed/authorized inputs, stable record identity, quantity basis, method-group compatibility and non-overlap. Reject duplicate record/snapshot contributions and bounded-body violations.
5. Render headline/breakdown/coverage from that response. Keep standard and WTW/method revisions separate; no estimate means no estimate. Search/paging does not alter the project-wide total.
6. Put excluded/input-needed/stale counts into the estimate's compact coverage and existing list filters. Do not recreate To review as a second list/card.
7. Generate contextual Calculation and source drawers from the actual nodes, with safe links, provenance, exact substitutions and count/exclude reasons. About receives the general explanations.
8. Implement stable duplicate-warning behavior for new receipt records, with Open existing and intentional Save separate. Shared invoice references remain valid.
9. Exercise amount/material/site/dispatch/factor/route edits, blank quantity save, two-tab updates, filtered Dashboard, mixed methods, rounding, zero versus missing and history preserving old report outputs.

Exit: Dashboard and delivery calculations agree, use no independent JavaScript emissions engine, and never show a stale/mixed total as current.

## 8. P12 — Server runtime and immutable reports

1. Introduce EF SQLite migrations for provider caches, route envelopes, global budgets, snapshots/capability hashes, signing-key metadata and short-lived evidence metadata. Approved catalogs remain versioned files.
2. Add capability issue/read/delete with independent random tokens, hash-only server storage, safe comparisons, expiry and generic inaccessible responses. No global report list.
3. Implement report snapshot/signature serialization and no-network read/print/JSON export. Preserve source and method revisions; rerun creates a new ID and explicit comparison.
4. Copy the safe signed immutable snapshot into the local project on explicit save/export. Server capability remains tab-local; a local copy does not keep the server object alive.
5. Remove Books/PostgreSQL/Redis sample infrastructure. Remove or replace inherited authentication only after D02 is resolved. Update health/Compose/secrets/migrations/tooling/CI/audit together.
6. Build/verify a real SQLite migration bundle and Linux native dependencies. Persist runtime data, key ring and app document paths under owned volumes with non-root write permissions.
7. Implement retention as an app-scoped bounded job; deny expired objects on read even if deletion lags. Document deletion/backups separately.
8. Exercise expiry/wrong capability, restart, concurrent writes, migration from previous schema, source updates after old reports and no provider calls during read/print/export.

Exit: reproducible private reports and persistent runtime work without template sample dependencies. VS2/C2 still require P12A/P12B and all applicable product behavior.

## 9. P12A — Documents as a complete vertical feature

1. Resolve D02 and store selected local files under atomic record/blob ownership. Set count/size/project caps and handle denied persistence/browser quota without losing existing data.
2. Add attach/list/remove with file picker, optional accessible drop area, safe filename/type/size and duplicate-byte warning. File selection does not parse or populate business fields.
3. Implement explicit short-lived server evidence-container creation and bounded upload under independent receipt capabilities. Add idempotency for container/upload retries; reused keys with different payload fail.
4. Stream into owned temporary storage while enforcing limits. Validate signature/type/hash and bounded images before promotion; ensure failed validation/abort leaves no accessible partial file.
5. Commit SQLite metadata and final bytes through a documented recoverable promotion protocol. On restart reconcile scoped staged/unreferenced files rather than guessing successful upload from file existence.
6. Add authorized retrieval/deletion with safe headers/no caching and consistent inaccessible responses. PDF download is required; inline preview requires a proven sandbox. Local originals remain downloadable after server expiry.
7. Link attachment ID/page to user-entered evidence only through explicit selection. Preserve source/evidence distinction; no OCR or dispatch verification runs.
8. Add metadata/hash snapshots to reports; removing/expiring bytes preserves immutable historical metadata and displays original-unavailable state.
9. Add bounded cleanup, per-client/global storage controls, capacity health, staging/orphan retention and server deletion retry state. Set initial numeric limits from FeatureSpecification.md and confirm host capacity before launch.
10. Extend backup/restore to SQLite, key ring and finalized server files consistently. Local browser originals need user-owned downloads/backups and are not covered by the node backup.
11. Exercise spoofed MIME/type, traversal, malformed/oversized images, wrong owner, expiry, interrupted upload, two retries, quota, restart promotion/reconciliation and no capability/document content in logs.
12. Exercise browser attach/download or preview/remove, duplicate handling, save/reopen and report metadata. Prove no entered quantity/dispatch field changes merely because a file was attached.

Exit: supporting evidence behaves predictably across local save, explicit server copy, expiry, deletion and recovery. Future scanning is still unimplemented.

## 10. P12B — Portable project backup and restore

1. Define versioned `ProjectBackup` separately from `CalculationReport`; include editable record IDs/references, original user values, safe snapshots and an originals manifest. Never include capabilities, private server URLs or paths.
2. Add Project backup and Report JSON actions with truthful filenames/labels and scope. Clearly state that ordinary JSON excludes document bytes; provide separate original downloads.
3. Build an import validator with bounded bytes/depth/records/source refs and explicit supported versions. Reject unsafe URLs/text/unsupported schemas before permanent writes.
4. Show a preview: project name, record/material counts, numerical trust state, missing originals and duplicate-batch warning. Default to creating a new project and fresh record IDs.
5. Apply import in one local transaction or a recoverable staged operation. Existing project edits must survive a failed import. Never restore source approval flags or network-fetch external attachment URLs from imported data.
6. Preserve signed snapshots as historical evidence; verify them before any current aggregate use. Fresh local IDs and mapping changes can require recalculation/re-signing. Never edit a signed envelope to make a new identity appear verified.
7. Exercise same-browser reopen and new-browser restore with no original server objects, hostile/older/newer schema imports, duplicate imports and quota failures. Recalculation remains explicit and separate.

Exit: users can retain and restore their editable project/calculation evidence without pretending absent originals or expired server capabilities were backed up. An optional file-inclusive archive is deferred unless separately implemented and bounded.

## 11. P13–P14 — Material breadth and warehouse/load behavior

1. Run the same complete slice for each remaining source: official row/variant review, unit mapping, contract, UI selection, conversion/fit warnings and engine/API/browser evidence. Do not create a calculator per material.
2. Add broader taxonomy/synonyms as data and preserve metadata-only rows. WD100 volume/mass, Thermocell density range, RT247 neighboring variants and precast-versus-ready-mix remain explicit cases.
3. Complete per-unit/input-needed and load-split controls under Transport, including sources for assumed truck/usable cargo volume and manual-logistics stops for unsupported cargo.
4. Implement Add warehouse with confirmed selected location and unchanged-product statement. Persist two movement IDs, calculate them separately and remove the old direct contribution.
5. Distinguish via-point geometry from real warehouse receipt/dispatch, preserve failed/unknown movements and provide clear counted/excluded/unresolved ledger rows.
6. Implement removing/changing warehouse, route override per movement and source-preserving recalculation. Do not add an imaginary direct leg or duplicate A1–A3 per movement.
7. Prove all five source goldens, unknown conversions, 25/25/10 load allocation, correct gross restrictions, warehouse two-leg behavior and transformation/unclassified boundary blocks.

Exit: the same approved workspace handles real material breadth and the required two-movement case without fake upstream coverage.

## 12. P15–P16 — Directional ferry research and route inference

1. Create a direction checklist for departure entrance/arrival exit, official source, HGV status, reviewed point and snap evidence. Review both directions of each service separately.
2. Make a bounded real approach request with actual truck restrictions and validate continuous accessible geometry. Failed/unresolved directions stay unavailable; never toggle approval to satisfy a fixture test.
3. Persist ferry metadata revision, checked service/reference sailing information and per-leg source modes. Keep sea geometry visibly schematic.
4. Implement deterministic geographic prefilter, road-only/eligible ferry candidate construction, continuity/loop checks and deduplication with explicit exclusion reasons.
5. Implement pure ranking/tie/ambiguity/sensitivity policies and use those outputs in map/table/cards. Required named route constraints fail clearly if unavailable.
6. Add user selection/override, saved selection and coherent per-leg carbon/source output. Do not infer carrier probability, fare or exact schedule.
7. Prove fixture numeric/ranking/sensitivity goldens and separate new live directional approach evidence. A road-only success cannot complete the multimodal gate.

Exit: both configured services and their eligible directions have actual evidence, route inference is reusable and every missing direction remains honestly recorded.

## 13. P17 — Reviewed second-provider intake

1. Inspect the actual official export/schema/license before implementing a mapping. Download only permitted bounded data and retain original hash/source/version.
2. Implement an offline operator command in `CarbonCalculator.DataTool`; the command validates/stages/promotes, it is not a public app upload endpoint.
3. Parse named columns/units/indicators with bounded archive expansion and safe paths. Unknown mappings remain rejected/metadata-only.
4. Produce explicit review summary and field citations. A second check is independent evidence, not an approval string copied from input.
5. Promote at least one suitable German dataset as generic or product EPD correctly, query/select it through the shared catalog and calculate compatible approved indicators through the existing handlers.
6. Prove re-import idempotency, duplicate/version rules, rollback and old-report immutability. Document a complete worked record/provider example.

Exit: second-provider expansion is real, source-reviewed and usable through the existing product; no screen-specific arithmetic or unsupported rights claim.

Proposed CLI surface, to implement and document before claiming these commands work:

```text
dotnet run --project CarbonCalculator.DataTool -- import-oekobaudat --file <official-export> --limit 50 --stage-dir <owned-staging-directory>
dotnet run --project CarbonCalculator.DataTool -- validate-catalog --file <normalized-catalog>
dotnet run --project CarbonCalculator.DataTool -- promote-reviewed --review-manifest <reviewed-manifest> --output <owned-catalog-output>
```

Staging output records original document/hash, parsed candidate rows, original/normalized notation, field citations, rejected reasons and rights/QA status. Promotion requires an explicit review manifest bound to input hashes; it cannot approve a changed source or a generic dataset as a product EPD. Source tools are operator/local tools, never unauthenticated web endpoints.

## 14. P18–P21 — Launch and recovery evidence

1. Resolve the owner launch-level decision. Road beta has a documented reduced publication gate; complete v1 still requires all mandatory rows in Acceptance.md. No default assumption of an early launch.
2. Complete deterministic feature/API/browser acceptance against the approved navigation, local/server storage contract, quantities, source matching, grouping, reports and uploads. Live provider checks remain separate and bounded.
3. Reconcile all 61 source IDs and added AC IDs; record test/artifact, exact SHA and actual status. No row is passed by its written requirement alone.
4. Evaluate the real UI with five genuine beginners; prepare neutral tasks and record original feedback. Four must distinguish making versus moving and estimated versus actual. Agents cannot impersonate participants.
5. Produce an exact-main release with immutable image/payload digest, source/run/profile/schema/method/catalog identities. Confirm storage/key-ring compatibility and no browser-exposed provider secret.
6. On the approved shared node, run only the product-owned deployment path for that immutable target. Record the dispatched run ID before watching and preserve other applications/resources.
7. Publish only the owned requested hostname/tunnel through retained scripts; reuse safe existing credentials. Verify external HTTPS/deep links/API/private caching and the exact release identity.
8. Prove normal update, compatible rollback/forward, app/connector restart and isolated SQLite/documents/key-ring restore. Restore must enforce original expiry/capability rules and signature verification.
9. Hand over real runbooks for provider budget, failed uploads, browser-local backup, server expiry, source updates, key rotation, doctor and release recovery. Distinguish recoverable node data from browser data the node does not hold.
10. Close finished PRs/worktrees/branches only after integrated-content verification, dependency/dirty/ignored review and evidence preservation. Do not remove a live preview or another task's checkout as cleanup.

Exit: the chosen launch level is publicly proven; complete-v1 status is reserved for the full source/feature/recovery contract. Remaining external inputs have concrete owner/action/state records.
