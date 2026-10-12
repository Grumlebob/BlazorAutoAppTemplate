# Portfolio implementation checkpoints

Read [DeliveryPhases.md](DeliveryPhases.md) for packet scope and [ExecutionDecisions.md](ExecutionDecisions.md) for concrete defaults. These checkpoints subdivide the existing packets; they do not create new phases or independent completion ledgers. Record the last completed checkpoint and the next one in [Progress.md](Progress.md). Commands proposed in the decisions document must first be implemented; commands in inherited runbooks must be verified against the selected baseline.

## 1. Session algorithm

1. Read current ledger/claims, applicable rules, the active packet and its decision/visual brief. Inspect status, remotes and main CI. Preserve dirty files and active worktrees.
2. Name the smallest visitor/operator outcome and the files needed for it. Record the base SHA and claim. If an input is missing, classify it as a true prerequisite or omit/fallback using the recorded decision; do independent work while awaiting a genuine external input.
3. Write a short before/after behavior inventory in the PR draft. Implement one cohesive checkpoint, with contract/gate replacements in the same change when behavior changes. Avoid half-removing a service registration or release artifact consumer.
4. Review the actual output and run the applicable local gate before push. Record exact commands/results and unavailable checks. Do not run application checks for a Markdown-only handoff.
5. Integrate through a small PR, exact final-head `build-test-push`, normal merge and successful exact-main CI. If rebased/updated, recheck the new final head. A completed watcher is not necessarily a completed workflow.
6. Record merge evidence in the ledger or linked PR description, output revision and precise next checkpoint. Describe partial work as partial until the whole slice passes. Never create a ledger-only commit just to record that same commit's future merge SHA.

Use only the master's [three recommended fresh-chat checkpoints](../../PortfolioStudioImplementation.md#recommended-fresh-chat-checkpoints). They are optional context resets after verified boundaries; prepare Progress's filled handoff and keep full-plan scope. Do not end a chat merely because one packet or PR finished.

## 2. Platform checkpoints — VS0

| Packet | Perform in order | Reviewable output / next checkpoint |
| --- | --- | --- |
| P0.1 | Read both upstream React plans; fetch main/open PRs; create a capability table for UI/contracts/dev/static host/release/native setup; classify remaining SR dependencies; select merged-green SHA and lockfile versions. | Baseline record with true blockers and independent work; next P0.2. Do not use “React finished” as an unverified shortcut. |
| P0.2 | Recheck destination refs/visibility/rules; disable Actions for empty import; clone pinned history with correct remotes; seed Portfolio app/image/React/single-node settings; run seed gate; initial push only if empty; copy plans/private intent; inventory runner/environment/secrets before enabling Actions. | Independent checkout and safe workflow routing. If CI capacity is absent, next P8.1/P8.2 prerequisite; otherwise P0.3/P1.1. |
| P0.3 | Select approved Studio references; record source licenses; copy only portable reference captures/assets; inventory private sources and transfer privately. | Design/source handover that another machine can use; next P1.1. |
| P1.1 | Inventory old identifiers and create rename map; rename solution/projects/namespaces/references; update Docker/CI/tooling paths; regenerate contracts; classify remaining old names. | Linux-case-correct Portfolio solution and paths; next P1.2. |
| P1.2 | Align package/image/profile/resource identity; inspect every workflow/runtime caller; recheck no inherited app/package write; run renamed gate and image smoke. | Own release identity throughout; next P2.1. |
| P2.1 | Map client/UI/profile dependencies; move genuinely shared contracts; delete Blazor build/runtime branches; replace profile/hosting/asset assertions and CSS rules. | One React frontend and no built Blazor payload; next P2.2. |
| P2.2 | Trace account UI/backend consumers; remove unreachable services/routes where coherent; record temporary storage consumers for P4/P7; update Requirements/AGENTS/local dev. | Public UI with accurate transitional graph and denied removed routes; next P3.1. |
| P3.1 | Make keep/move/delete dependency table; relocate shared audit/render/smoke code; update imports, fixtures, workflow and local gate; run relocated checks before deletion. | Canonical retained check paths verified; next P3.2. |
| P3.2 | Delete unsupported target directories/workflows; enforce single target; retarget docs/AGENTS and all callers; classify historical matches; run full retained gate. | LocalSingleNode-only product without broken shared operations; next VS1/P4.1. |

P0/P8 capacity-first does not authorize public exposure. Resolve the seed/CI dependency using the inherited state machine, not a new manually installed runner or a secret copied from the template.

**C1 fresh-chat recommendation:** after all VS0 exits and required early access/CI prerequisites are verified, save the handoff and recommend a new chat for VS1. First work: P4.1 plus initial P6.1. Do not carry the import/cleanup transcript forward.

## 3. First story checkpoints — VS1

Maintain one active VS1 outcome covering P4/P5/P6.1/P7.1/P7.3. Suggested cohesive PR boundaries follow; combine or split by actual dependency and review size. Do not treat them as separate completed product slices.

### A. Real story and compiler — P4.1 + initial P6.1

1. Locate the selected ImprovedDb revision/captures, keep the approved motivation, verify actual ratings/import behavior, and omit unresolved counts/cutoff statements. Use neutral contribution wording until personal role is evidenced.
2. Add site and ImprovedDb metadata with six stable editorial section IDs and source-supported technology IDs. Create the canonical registry; synthesize Techs and published-only TechnologyCatalog. Add draft starters separately. Select figures/provenance and only needed block kinds.
3. Create ContentTool and shared C# contracts/compilation. Implement validate/media-plan/media/export command contracts, diagnostics and published-only output. Wire build order before any Vite public copy.
4. Verify identical repeated exports, draft/private sentinel exclusion, unsafe prose/media/path rejection, image hashes and payload budgets. Record actual commands, model fields and content revision.

Checkpoint output: a reviewed first-story bundle that can feed both API and build, without DB/Redis/credentials. Next: B, not all twelve content records.

### B. Read API and home/reader together — P4.2 + P5.1/P5.2

1. Load the exported immutable bundle in the C# host. Add the four read features and status/ETag metadata; regenerate TypeScript through actual inherited tooling.
2. Replace the relevant Books consumers with home, Technologies and the story reader with generated Techs. Use the approved shell/tokens/fonts, native links, six editorial sections plus Techs, and the shared block renderer.
3. During the development increment, use generated transport/Query with cancellation and permanent-error policy. Add actual loading/empty/error behavior without delaying readable content after prerender.
4. Implement section/menu focus and tracking, theme bootstrap/persistence and figure sizing. Verify the journey at one narrow and one wide viewport early; save final visual evidence later.

Checkpoint output: home → ImprovedDb reading journey using the real DTOs; still partial VS1. Next: C/D.

### C. Sample removal — P4.3

1. Trace Books/account/simulator entities, endpoint registrations, seed/cache/auth consumers, generated contract and tests. Record each removal or necessary temporary service.
2. Remove the sample domain and endpoints, replace relevant tests/metrics with Portfolio assertions, regenerate schema and deny former paths. No blanket security-test deletion.
3. Keep temporary storage only while its real callers remain; do not reset existing data. Update dependencies/local run docs. Hand the inventory to VS3.

Checkpoint output: no sample product, safe removed routes and a buildable graph. Next: D; storage remains explicitly transitional until VS3.

### D. Direct HTML and acceptance — P7.1/P7.3 + P5.3

1. Wire offline loaders to the exact bundle and explicit published paths. Build `/`, `/technologies` and `/projects/improveddb`; inventory generated HTML/navigation data/asset layout and route discovery behavior.
2. Add exact C# routing and true 404 document/status policy, canonical redirects, reserved paths and revision compatibility. Remove generic shell fallback for unknown production requests.
3. Implement `PortfolioPublicV1` consistently in profile resolver, labels, manifests, setup/workflows, image smoke and deployed-site script. Check real story sections/assets and matching revision, not Books seeds.
4. Add title/description/canonical/social/sitemap/robots output. Verify useful HTML with JavaScript disabled and no duplicate initial API reads. Add approved responsive media/font handling.
5. Review both themes, specified viewport/zoom matrix, native fragment/Back behavior, short final section, image dialog focus, real route/asset/API errors and production image. Record the visual checkpoint and exact release identity.

Checkpoint output: complete VS1 only after merged-green code and the production journey pass. Next: eligible P6 story or required VS3 cleanup.

**C2 fresh-chat recommendation:** now save the actual compiler/build/hosting commands, shared renderer/model paths and verified visual/revision evidence. Recommend a new chat for repeatable story delivery; normally start P6.2. Do not trigger C2 after A, B or C alone.

## 4. Repeatable story checkpoints — P6.1–P6.13 / VS2

For P6.2–P6.11 and P6.13, use the respective inventory sections and [VisualProduction.md](VisualProduction.md). P6.1's initial review happens within VS1. Every story follows the same sequence:

1. **Source:** pin code/report revision and publication context. Separate code, report, media and owner explanation. Do not execute source software merely to establish facts.
2. **Copy:** write a short introduction, stable H2 sections, one grounded design explanation and limitations. Verify technology IDs against source; reserve `techs` for the generated section. Omit unverified role/count/date claims. Attribute Grumlebob's supplied profit/capacity statements to the owner.
3. **Figures:** produce cover and primary explanation, then only useful supporting evidence. Record rights/provenance/caption/alt/crop. Use synthetic fixtures or honest explanatory fallbacks; no private data.
4. **Integration:** publish only after review; compile/export; verify catalog/detail, Techs/Technologies entries and links, direct HTML, navigation data, social/sitemap and related links. Extend generic rendering only for a concrete story need.
5. **Checks:** content/privacy/links + relevant API/hosting/browser/image acceptance. A non-Markdown content/media change follows the applicable implementation gate, even if no C# file changed.
6. **Handoff:** record source/content revision, changed boundaries, PR/head/merge/main evidence and exact next story. If genuinely blocked, leave draft and choose an independent story.

P6.13 adds Template; P6.12 retains the catalog-review ID. Inspect full catalog/order, card/detail pairs, Techs and deduplicated Technologies, related links, figures and launch readiness. Record four-story launch separately from twelve dispositions. Every deferral needs owner instruction/reason.

## 5. Runtime, public launch and handover — VS3–VS5

| Packet | Perform in order | Exit / next checkpoint |
| --- | --- | --- |
| P7.2 | Complete service-consumer inventory from P2/P4; remove app DB/cache/Identity/migrations and unused key/mail/provider consumers; make migration artifacts explicitly optional for file-only profile; update Compose/startup/release/CI/audit/doctor/backup/recovery together; verify image starts with only app/Caddy/connector needs. | Final file-only runtime and honest operations, no empty fake migration bundle; next P7.4. |
| P7.4 | Reproduce fresh-checkout pipeline; run current gate/image/browser/accessibility/loading checks; inspect exported public tree; merge exact-head green; verify exact-main publication and digest/profile/content manifest; produce launch-ready evidence. | Immutable deployable release; next remaining P8. |
| P8.1 | Verify native machine privately, correct repository and operator current-node setup request; clone/sync safely; run retained setup status. | Correct native target, no Windows bootstrap; next returned actor step/P8.2. |
| P8.2 | Follow state machine; return its single human root command; verify runner scope/labels/capacity and Actions routing; resume deferred repo customization. | CI/native prerequisites established; next P8.3 or deferred cleanup. |
| P8.3 | Pair verified controller SSH; check owned collisions/locks/capacity/current release; perform only authorized LAN operation; independently verify final Portfolio acceptance. | Native/LAN readiness with exact evidence; next P9.1. |
| P9.1 | Prepare concrete release/public inputs; record applicable launch authorization; use protected Cloudflare runbook authentication; configure owned tunnel/DNS/connector and repo inputs. | Owned public configuration, no foreign overwrite; next P9.2. |
| P9.2 | Recheck exact release/target; dispatch LocalSingleNode once, save run ID; verify running digest/source/profile/revision, normal public HTTPS/browser/deep links/denials/themes and unrelated workloads. | Public launch milestone; next P10 and remaining stories. |
| P10.1 | Perform authorized scoped restart/recovery; create a second reviewed meaningful content release if needed for a compatible predecessor; rehearse update/open-tab behavior and scoped rollback/forward using real releases; verify doctor/owned connector. | Recovery evidence, honest first-release limitations until proven; next P10.2. |
| P10.2 | Complete remaining story slices or record owner deferrals; write actual fresh-clone/content/release/maintenance instructions; dry-review a new-project procedure and validate source/register completeness. | Full catalog disposition and executable handover; next P10.3. |
| P10.3 | Audit every required packet/slice evidence and public release; link downstream authority from template planning record through a docs PR; retain private trust/ownership records; remove only owned obsolete scratch after evidence is preserved. | Whole plan complete only with merged-green changes, public acceptance and recovery/full catalog evidence. |

Never manufacture a second release merely by changing an evidence timestamp. A legitimate small editorial improvement can provide the second compatible file-only release needed to rehearse rollback. Runtime content is rebuilt and released, never edited on the node.

**C3 fresh-chat recommendation:** after launch-set review, VS3 and final P7.4 are verified, save the exact release, remaining P8 step, native/private-note references, authorization scope and uncompleted stories. Recommend a new chat for remaining P8, P9 and P10. Keep launch/recovery together; an operator handoff is not another planned chat reset.
