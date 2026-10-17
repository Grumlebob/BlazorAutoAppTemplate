# CarbonCalculator implementation checkpoints

Status: planned work only, 2026-10-17. Use [the delivery plan](../../CarbonCalculatorDelivery.md) for the full packet order and gates, [FeatureSpecification.md](FeatureSpecification.md) for behavior and [Acceptance.md](Acceptance.md) for proof obligations. The owner approved the latest design; no packet requires another mockup selection.

This file splits the product work into reviewable changes. A numbered checkpoint can be a small PR, but its parent packet is complete only when the whole visible slice works. Do not create one broad backend phase followed by one broad frontend phase. Every public operation includes validation, generated contract, UI state/error handling and evidence in its slice.

## 1. Decisions before dependent work

### D01 — Capture the approved design

1. Record the owner's approval of the current direct-navigation mockup in the downstream progress ledger.
2. Preserve a compact screenshot/contact-sheet reference and component/token brief in the product repository when rights and paths are safe. Ignored temporary controller assets are not a runtime dependency.
3. Recreate Dashboard, its compact estimate/list header, direct Material/Transport/Documents links, one delivery workspace and secondary About from the approved brief.
4. Treat unimplemented controls in the preview as illustrative. Do not copy the prototype's duplicated function overrides, inline event handlers or local emissions formulas into React.
5. Mark D01 complete after the implementation brief is retained. Responsive/accessibility acceptance still occurs against real implementation; another color/layout approval is not a prerequisite.

### D02 — Selected accounts, ownership and lifetime

Selected on 2026-10-17: verified email/password accounts and server-saved private PostgreSQL projects across devices. Read [AccountsAndOwnership.md](AccountsAndOwnership.md) before dependent work; it replaces IndexedDB/anonymous-token storage and SQLite. Reuse the completed template account foundation; no auth redesign or another owner decision. Keep separate product identities, users, sessions and keys. Public launch level remains open; planning is not deployment authorization.

## 2. Foundation packets P01–P08 and P08B

| Checkpoint | Concrete output | Failure that must stop promotion |
| --- | --- | --- |
| P01 baseline | Full upstream SHA containing account review `45aa44308340285e54568a5a2262bcf0a6deec17` with exact-main successful CI, current guide/workflow inventory and destination-state evidence | Empty-repo import assumed without checking remote |
| P02 seed | Own private origin, safe app/image identity, Actions held until eligible runner, retained upstream provenance | A tool still defaults to template/Books or destination contains unknown work |
| P03 capacity | CarbonCalculator-specific eligible runner on the existing node, separate registration/service state, green product main | Existing template runner removed/rebound; inherited runner labels target another app |
| P04 React-only | Blazor dependency removal and replacement audits, retained browser test tooling, React-only build/image | Razor/WASM build path still accepted or shared assets deleted first |
| P05 single node | Shared audit/check relocation, caller inventory and removed target rejection | LocalSingleNode imports a deleted Cloud/LocalCluster helper |
| P06 rename | Explicit project/path/manifest/namespace map, Linux build and generated-contract drift check | Source/run/image/migration identity differs between publication and CD |
| P07 product docs | Current README/Requirements/Test/Operations and attribution; obsolete fork language removed | Required audit rules silently deleted with a guide |
| P08 SPA shell | Known routes, section navigation semantics, safe reserved-path/404 behavior, strict CSP and acceptance-profile binding | API/asset errors return HTML, private paths are prerendered or Books acceptance remains final |
| P08B accounts, after P08 | Enabled inherited React accounts and PostgreSQL owner-scoped thin project entry; local TLS SMTP and two-user/antiforgery/revocation proof | Accounts disabled, shared app identity/key ring, foreign IDs accepted, or template tests substituted for product ownership proof |

P08B runs before P08A. Preserve Identity/React endpoints, antiforgery, key store and encrypted mail outbox during Blazor cleanup. Add thin Projects owner FK/revision/index and real create/list/read/empty UI; P08A completes CRUD and child data. Prove account flows with real Identity cookies/isolated PostgreSQL/TLS SMTP, forged-owner/nested-ID denial, admin without bypass, session changes, owner-bound drafts and stale-response cancellation. Record account export/deletion hooks now and extend them with every later entity. P18 prepares production mail; controlled real-inbox verification at P19/P20 gates public launch, not local implementation.

Keep the full removal inventories and local/PR/main gates in the main plan. Do not rename code that P04/P05 will delete. P03 uses the already approved extra registration on the existing node, never a bootstrap of the controller PC.

## 3. P08A — Project and delivery persistence through the approved shell

Prerequisites: P08B, D01 and selected D02. No routing key is required. This packet introduces an actual useful editable record, with calculation explicitly input-needed until its handler lands.

1. Add feature-owned UI state modules under `app/features/site-receipts`: project context, delivery edit buffer, validation model and generated owner-scoped API/query adapter. Use route composition only for navigation. Do not put the complete application in a global mutable object.
2. Extend PostgreSQL project/delivery schema with FKs, owner-constrained handlers, revision tokens and transactional idempotency. Keep saved records distinct from memory edit buffers; migrations never erase existing data on unsupported versions.

3. Implement create/select/rename project with name and optional unresolved site. An empty installation is empty; sample project loading is explicit and separately labelled.
4. Implement Add delivery with one generated stable ID, empty quantity/supplier/origin/reference and optional received date. Add Material/Transport/Documents section routes and preserve raw edit strings while switching.
5. Save incomplete records atomically without calculation. Return to the original Dashboard context and show success only after the transaction commits. Add specific retry/export behavior for network/storage/quota failure.
6. Implement open/edit/update for the same ID with atomic server revision checks. Notify other tabs of changes and handle independent device updates and offer reload/save-as-new on conflict. Do not overwrite an unsaved buffer.
7. Implement leave handling: Save, Discard, Stay when dirty; section switches are safe without a prompt. The browser-close warning is best effort, not the sole protection.
8. Implement delivery and project deletion with named/count-aware confirmation and owned attachment access removal and durable byte cleanup. Delete only the current owner's records; keep exported copies outside app control.
9. Add bounded owner/project-scoped server search/filter/order/paging and direct Dashboard links to each delivery section. No provider calls occur during search, section switching, save or project selection.
10. Exercise refresh/browser restart, two projects, partial save, edit without duplication, two-tab conflict, failed writes, unknown deep link and cancelled/completed deletion. Use two isolated signed-in users/devices for deterministic ownership, conflict and revocation evidence. Extend account/project deletion/export in this packet.

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

Start pure fingerprint/aggregation rules alongside P11/P11A. Complete P12's saved snapshot support before shipping aggregation; PostgreSQL already exists from P08B/P08A. Packet labels group work; the concrete dependency order is P11/P11A, P12, P11B, P12A, P12B. Do not introduce a P11B/P12 completion cycle.

1. Define separate fingerprints for routing inputs, numeric calculation inputs and report context. Add the dependency table from FeatureSpecification.md as named domain/UI rules.
2. Mark edited results stale immediately; keep the prior snapshot immutable. Ignore a late response if its fingerprint/edit revision no longer matches. Preserve source history without counting old results as current.
3. Load snapshots from the authorized project instead of verifying signed browser contribution envelopes. Validate ownership, record identity/revision, input fingerprint and immutable payload hash; imported claims remain historical until recalculation. No new signing key ring.
4. Implement server-owned aggregation over current selected saved assessments, compatible quantity/method groups and non-overlapping movement identities. Reject foreign/duplicate record refs, stale revisions and bounds violations. Extend account export/deletion to new aggregate metadata if any is retained.

5. Render headline/breakdown/coverage from that response. Keep standard and WTW/method revisions separate; no estimate means no estimate. Search/paging does not alter the project-wide total.
6. Put excluded/input-needed/stale counts into the estimate's compact coverage and existing list filters. Do not recreate To review as a second list/card.
7. Generate contextual Calculation and source drawers from the actual nodes, with safe links, provenance, exact substitutions and count/exclude reasons. About receives the general explanations.
8. Implement stable duplicate-warning behavior for new receipt records, with Open existing and intentional Save separate. Shared invoice references remain valid.
9. Exercise amount/material/site/dispatch/factor/route edits, blank quantity save, two-tab updates, filtered Dashboard, mixed methods, rounding, zero versus missing and history preserving old report outputs.

Exit: Dashboard and delivery calculations agree, use no independent JavaScript emissions engine, and never show a stale/mixed total as current.

## 8. P12 — Server runtime and immutable reports

1. Extend PostgreSQL migrations for owned immutable reports, route/cache/budget data and temporary expiry. Reuse account/Identity/key/outbox runtime and release migration tooling; catalogs remain versioned files.
2. Authorize report create/read/delete/export through current session and owner graph; antiforgery protects writes. No anonymous capability API. Validate nested IDs and selected result fingerprint/revision.
3. Serialize exact immutable snapshot bytes; read/print/JSON export make no network/provider call. Explicit recalculation creates a new ID/comparison.
4. Persist saved reports until explicit deletion; unattached standalone results expire by default. Browser keeps parsed private data only in owner-scoped memory; explicit user downloads are separate.
5. Remove Books sample endpoints/UI/data with reviewed schema cleanup while retaining PostgreSQL, supported Redis, account storage, protected wrapping inputs and real migration/release tooling.
6. Add snapshot linkage to project/account export/deletion; reject imported owner/approval claims and cross-project result rebinding. Avoid replaying provider/mutation work on uncertain commits.
7. Implement bounded temporary expiry and durable deletion reconciliation. Deny expired/deleted/inaccessible objects even when physical cleanup lags; disclose backup retention.
8. Exercise two-user/antiforgery/revocation denial, restart, concurrency, previous-schema migration, exact-byte exports and unchanged old reports after catalog updates. No extra local-signature trust mechanism.

Exit: reproducible private reports and persistent runtime work without template sample dependencies. VS2/C2 still require P12A/P12B and all applicable product behavior.

## 9. P12A — Documents as a complete vertical feature

1. Require an explicitly saved owned incomplete delivery before upload. Use AccountsAndOwnership.md §4 limits; no browser persistence or anonymous receipt container.
2. Add file picker/optional accessible drop area, progress/failure/retry, duplicate-byte warning within this delivery, download-or-safe-preview and remove. Selecting a file never extracts business values.
3. Use session/antiforgery and full nested owner graph checks on upload/list/read/remove. Scope idempotency receipts and byte reservations to user/project/operation; differing replay payload conflicts.
4. Stream to owned staging with byte/type/hash/pixel bounds. Reject active/spoofed types, traversal and malformed images; abort leaves no accessible partial file.
5. Promote finalized bytes/PostgreSQL metadata through a documented recoverable protocol. Reconcile staged/unreferenced files on restart; filesystem presence alone is not upload success.
6. Finalized originals persist across logout/restart/another signed-in device. Safe download headers/no-store are required; PDF inline preview needs proven isolation.
7. Link document/page to a user-entered fact only through explicit selection. No automatic OCR, dispatch confirmation or source approval.
8. Snapshot safe attachment metadata/hash; removal makes original unavailable without rewriting retained numerical reports. Raw bytes/tokens stay out of JSON.
9. Enforce concurrent per-user/project/global caps and bounded staging expiry. Remove access immediately on delete, commit independent deletion jobs and retry scoped cleanup after crashes.
10. Extend account/project export/deletion and consistent PostgreSQL/files/key recovery. Stop late uploads/saves from recreating deleted data; do not delete another owner's bytes.
11. Exercise foreign/nested IDs, revoked sessions, antiforgery, type/MIME/traversal/pixel/size/count/storage limits, abort/retry/promotion/cleanup and no private-content logs.
12. Exercise real browser attach/download/remove, explicit initial save, cross-device reopen and account/project deletion. Verify quantities/dispatch stay unchanged.

Exit: supporting evidence behaves predictably across server save, cross-device access, temporary staging expiry, deletion and recovery. Future scanning is still unimplemented.

## 10. P12B — Portable project backup and restore

1. Define versioned `ProjectBackup` separately from `CalculationReport`; include editable record IDs/references, original user values, historical snapshots and an originals manifest. Never include capabilities, private server URLs or paths.
2. Add Project backup and Report JSON actions with truthful filenames/labels and scope. Clearly state that ordinary JSON excludes document bytes; provide separate original downloads.
3. Build an import validator with bounded bytes/depth/records/source refs and explicit supported versions. Reject unsafe URLs/text/unsupported schemas before permanent writes.
4. Show a preview: project name, record/material counts, numerical trust state, missing originals and duplicate-batch warning. Default to creating a new project and fresh record IDs.
5. Apply import in one owner-scoped PostgreSQL transaction or a recoverable staged operation. Existing project edits must survive a failed import. Never restore source approval flags or network-fetch external attachment URLs from imported data.
6. Preserve imported snapshots as historical/unverified evidence; new owned IDs never inherit current numerical approval. Explicit server recalculation creates current results after validation. Ignore supplied owner IDs and do not rebind old report/attachment access.
7. Exercise signed-in reopen on another device and import after original project deletion, hostile/older/newer schema imports, duplicate imports and quota failures. Recalculation remains explicit and separate.

Exit: users can retain and restore their editable project/calculation evidence without pretending absent originals or private access to deleted originals was backed up. An optional file-inclusive archive is deferred unless separately implemented and bounded.

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
2. Complete deterministic feature/API/browser acceptance against the approved navigation and selected account-owned PostgreSQL storage contract, quantities, source matching, grouping, reports and uploads. Live provider checks remain separate and bounded.
3. Reconcile all 61 source IDs and added AC IDs; record test/artifact, exact SHA and actual status. No row is passed by its written requirement alone.
4. Evaluate the real UI with five genuine beginners; prepare neutral tasks and record original feedback. Four must distinguish making versus moving and estimated versus actual. Agents cannot impersonate participants.
5. Produce an exact-main release with immutable image/payload digest, source/run/profile/schema/method/catalog identities. Confirm storage/key-store/wrapping-key compatibility and no browser-exposed provider secret.
6. On the approved shared node, run only the product-owned deployment path for that immutable target. Record the dispatched run ID before watching and preserve other applications/resources.
7. Publish only the owned requested hostname/tunnel through retained scripts; reuse safe existing credentials. Verify external HTTPS/deep links/API/private caching and the exact release identity.
8. Prove normal update, compatible rollback/forward, app/connector restart and isolated PostgreSQL/documents/wrapping-key restore. Disable external mail/provider egress; verify owner denials, exact snapshots, deletion reconciliation and the disaster-restore reauthentication policy.
9. Hand over real runbooks for provider budget, failed uploads, account/project export and deletion, temporary expiry, source updates, key rotation, doctor and release recovery. Distinguish server-saved work from unsaved memory edits and downloaded user copies. P18 prepares and validates sender/mail configuration; P19/P20 proves authorized real inbox delivery, confirmation and recovery on the reachable HTTPS product before public launch.
10. Close finished PRs/worktrees/branches only after integrated-content verification, dependency/dirty/ignored review and evidence preservation. Do not remove a live preview or another task's checkout as cleanup.

Exit: the chosen launch level is publicly proven; complete-v1 status is reserved for the full source/feature/recovery contract. Remaining external inputs have concrete owner/action/state records.
