# Portfolio progress and resume ledger

Read [master plan](../../PortfolioStudioImplementation.md), [architecture/slices](Architecture.md), [phases](DeliveryPhases.md), [execution decisions](ExecutionDecisions.md), [implementation checkpoints](ImplementationCheckpoints.md), [page briefs](PageBriefs.md), [visual production](VisualProduction.md), [source inventory](ProjectInventory.md) and [node handoff](NodeHandoff.md). The later goal prompt is [PortfolioStudioDeliveryGoal.md](../../PortfolioStudioDeliveryGoal.md).

## Current checkpoint

Last updated: 2026-10-11. Planning prepared; no Portfolio code, node bootstrap or deployment executed by this task.

- Destination: [Grumlebob/Portfolio](https://github.com/Grumlebob/Portfolio). It existed and was empty when inspected; recheck before import.
- Source: [Grumlebob/BlazorAutoAppTemplate](https://github.com/Grumlebob/BlazorAutoAppTemplate).
- Latest readiness inspection: upstream main `310dca9610419523c9f07412ed8ea6c0cb665ef4`; successful [CI run 38153407171](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38153407171). This is a planning checkpoint, not the final seed selection. Portfolio advertised no Git refs at this review.
- Another agent owns the [React delivery goal](../../ReactFrontendDeliveryGoal.md) and active [SR1–SR6 plan](../../ReactFrontendSingleRepository.md). P0–P7 implementation/controller SSH and retired-repository cleanup are complete; public React delivery is unfinished. Prefer completed reusable delivery; P0 classifies actual merged capabilities/dependencies. Preserve that agent's work and existing deployment.
- Product decisions: Portfolio naming, React frontend/C# backend, Books/Blazor removal, LocalSingleNode-only deployment and intended public URL `https://portfolio.jacobgrum.com/`.
- Owner architecture preference: vertical slices organized around use cases. After P0–P3, VS1 completes ImprovedDb's content/C# API/React home-reader/prerender/hosting/acceptance together; later stories repeat that journey.
- Supplied local checkout/node details: ignored `Plans.local/Portfolio/OperatorIntent.md`. Transfer privately to the downstream checkout. GitHub authentication on the fresh native node is reported, not independently verified.
- Recommended next implementation task: **P0.1** after a delivery instruction. While reusable upstream dependencies are unfinished, independently prepare source/prose/media using VisualProduction. No Portfolio implementation has started.
- Public launch authorization: not recorded for execution. This request prepares plans; do not dispatch a deployment from it.

After P0 import, this ledger in **Portfolio** is authoritative. Retain a link from the template plan to downstream execution evidence. Do not maintain two competing live ledgers or import the React agent's progress as Portfolio progress.

## Vertical slice ledger

These rows record visitor/operator completion across the existing packets. Keep the phase ledger as the detailed work inventory; a phase's partial backend/frontend work does not verify a product slice.

| Slice | Status | Owned packets / exact next action | End-to-end evidence |
| --- | --- | --- | --- |
| VS0 Independent product | Ready | P0–P3; start P0.1; early P8 only for actual access/CI prerequisites | Pending |
| VS1 Read ImprovedDb | Pending | P4/P5, initial P6.1 review and first-story P7.1/P7.3/applicable P7.4 | Pending content/API/home/story/direct HTML/theme/mobile/image acceptance |
| VS2 One additional story | Pending | Repeat one eligible P6 packet; catalog review P6.12 | Pending per-story export/API/routes/media/metadata and checks |
| VS3 Runtime alignment | Pending | P7.2 final file-only runtime and matching release/operations changes | Pending |
| VS4 Public launch | Pending | P7.4, remaining P8 and P9 | Pending native/LAN/release/public acceptance |
| VS5 Update/recover | Pending | P10 and remaining P6 stories | Pending recovery/authoring/full catalog disposition |

## Phase ledger

Statuses: `pending`, `ready`, `in progress`, `blocked`, `merged`, `verified`, `owner-deferred`. `merged` records code integration; a phase becomes `verified` only when its exit evidence is satisfied. A queued CI run is not green evidence.

| Phase | Status | PR / final head / merge / main CI | Evidence or exact next action |
| --- | --- | --- | --- |
| P0 Baseline/import | Ready to begin | — | Verify retained React foundation/dependencies, remote state and selected SHA; no import executed |
| P1 Portfolio naming | Pending | — | Build rename inventory after import; establish CI capacity if absent |
| P2 React-only cleanup | Pending | — | Remove Blazor/profile branches with replacement checks |
| P3 Single-node cleanup | Pending | — | Move shared audit/smoke dependencies before target deletion |
| P4 Portfolio content/API | Pending | — | Build VS1's first-story bundle/contracts alongside its API/UI; remove Books |
| P5 Studio home/reader | Pending | — | Complete VS1 home/ImprovedDb in both themes with first-story P7 hosting/acceptance |
| P6 Eleven stories | Pending | — | Each reviewed story updates export/API/card/detail/prerender/media and checks together |
| P7 Rendering/release | Pending | — | P7.1/P7.3 start in VS1; extend each story; then runtime/final release gates |
| P8 Native node/SSH | Pending | — | Use native runbook; bring CI bootstrap forward if required |
| P9 Public launch | Pending | — | Record authorization/release; complete LocalSingleNode public setup |
| P10 Recovery/handover | Pending | — | Update/recovery evidence and all-story disposition |

## Current packet record

Copy this record for each active packet. Keep finished packet records or link their PR descriptions. Record enough for an agent with no earlier chat to continue.

```text
Packet ID and title:
Last completed checkpoint / exact next checkpoint:
Vertical slice ID, visitor/operator outcome and owned packet IDs:
Status:
Owner/session and start date:
Repository and base main SHA:
Branch/worktree:
Claimed files:
Inputs/dependencies verified:
Output implemented:
Content/backend/frontend/hosting/check changes, or why a boundary is unaffected:
Checks: exact commands, environment, result, report/run links:
Unverified or unavailable checks:
PR URL and exact final head SHA:
Merge SHA and successful main CI URL:
Content/release revision if applicable:
Blocker and actor needed, if any:
Private handoff note location, if relevant (no values/secrets):
Exact next action:
```

Do not leave `next action: continue implementation`. Name a command from the implemented runbook or a small task/file set, such as “P3.1: inventory CI references to the old audit path and record the keep/move/delete table.” Preserve somebody else's active claim; do not infer abandonment from elapsed time alone.

## Fresh-chat handoff

Use the master's [C1–C3 recommendations](../../PortfolioStudioImplementation.md#recommended-fresh-chat-checkpoints). No checkpoint is ready yet. Fill this record when its verified boundary is reached; preserve earlier handoffs or link their PR descriptions. Commit stable handoff facts through the normal documentation process. Final merge/main evidence can be saved in the linked PR description without creating another evidence-only commit. Keep private facts in ignored notes and provide their location only.

```text
Checkpoint: C1 / C2 / C3; pending / ready / transferred:
Verified slice/phase exits and public evidence links:
Authoritative repository and handoff document revision:
Verified base/main SHA, PR/head/merge and exact-main CI:
Current content/release revision, image digest and workflow IDs if relevant:
Next packet / substep / concrete first action:
Relevant implementation paths and verified commands:
Applicable decisions and remaining blockers/catalog:
Open PRs/runs, active claims, dirty work and their owners:
Private note location and whether the receiving agent can access it:
Owner authorization scope and still-required operator action:
Claim transfer: previous owner stopped editing / receiving owner and time:
```

Give the owner one short continuation prompt, filling every bracket from this record. Omit inapplicable fields explicitly; never invent a value. The existing detailed packet/release records hold the supporting evidence.

```text
Continue the complete Portfolio delivery plan in [authoritative repository]. Read AGENTS.md, Plans/PortfolioStudioImplementation.md, its indexed companions and Progress's latest packet/release records. Fresh-chat checkpoint [C1/C2/C3] is verified at [main SHA; evidence links], with handoff [document revision/PR]. Start [packet/substep] by [concrete action], using [actual paths/verified runbook commands]. Apply the recorded decisions and preserve vertical slice completion; this is continuation of the full P0-P10 goal.

Recheck status/remotes/claims, current main CI and [open PR/run IDs or none] before claiming work. Claim transfer is [state/owner]; preserve [dirty work/other claims or none]. Release/content identity is [values or not applicable]. Outstanding stories/blockers are [IDs and next actions]. Read private notes at [location]; request the smallest missing private input if unavailable. Live operations are authorized only within [recorded scope or not yet authorized]. Do not borrow upstream React authorization, restart completed setup or redispatch a recorded run. Save exact evidence and the next checkpoint; complete only after full-plan public/recovery/catalog handover acceptance.
```

## Project readiness ledger

Each cell requires real evidence. Source preparation from the existing inventory is not publication approval or runtime verification.

| Packet / project | Source review | Prose | Media/provenance | Role/status | Publication | PR / revision / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| P6.1 ImprovedDb | Prior review; recheck | Outline | Existing captures; select | Motivation known; role pending | Pending | Recheck ratings/ML/cutoff copy |
| P6.2 KinoJoin | Prior source review | Outline | Synthetic capture pending | Pending | Pending | Capture event journey; verify role |
| P6.3 TraceBack | Prior docs review | Outline | Synthetic capture pending | Prototype; role pending | Pending | Verify public source/tutorial choice |
| P6.4 Unlost | Report/artifacts reviewed | Outline | Genuine figures; select | Team context; role pending | Pending | Review attribution/figure reuse |
| P6.5 Ship Inspections | Prior source/docs review | Outline | Synthetic capture pending | Sample; role pending | Pending | Reconcile upload behavior/limits |
| P6.6 MiniTwit | Prior report/docs review | Outline | Historical figures; select | Team context; role pending | Pending | Align source/report and dated claims |
| P6.7 BestBets | Preferred Exam/deck text reviewed; final design reconciled | Outline | Original figure visual/reuse review pending | Team design study; individual role optional | Pending | Produce sourced broker/actor/target/tradeoff figures |
| P6.8 Geospatial research | Notebook/report structure | Outline | Genuine maps/plots; select | Team context; role pending | Pending | Dates, attribution and limitations |
| P6.9 GeckoBot | Private GeckoBot selected; trees/AST structure reviewed | Brief | Fictional captures pending | Historical use/status pending | Draft | Prepare source-backed fictional figures; omit unverified use claims; private demo backup retained |
| P6.10 Grumlebob | Owner explanation; restricted folder located | Domain-neutral brief | Approved generic figures pending | Pending | Draft | Obtain approved public explanation; source inspection optional |
| P6.11 JobHunt | General private docs reviewed | Copy boundary resolved | Flow concept; fictional captures pending | Personal review; assisted drafting accurately described | Draft | Produce permitted figures; omit unverified account creation |

Launch set: not yet approved/published. Recommended: ImprovedDb, KinoJoin, TraceBack, Unlost when ready. Initial launch does not close unfinished story packets.

Owner source update on 2026-10-11: `Grumlebob/GeckoBot` remains the sole active private source, with rename identity/history/privacy preserved; deleted MailDemo's complete history remains privately backed up. BestBets' preferred Exam/deck text now supplies final-design/prototype-limit evidence; selected figures still need visual/reuse review. Grumlebob uses only approved public explanation; restricted source inspection is unnecessary. Exact locations, backup evidence and publication boundaries remain in ignored `Plans.local/Portfolio/ProjectSources.md`.

Execution enhancement: D01–D12 resolve routine dependency/compiler/media/runtime/copy choices, ImplementationCheckpoints subdivides all technical packets and repeatable story slices, and VisualProduction specifies eleven project figure sets. Unknown personal roles/counts may be omitted; permission, Grumlebob public explanation and native/human authorization remain genuine scoped inputs. This is planning evidence, not completed product work. Planning PR/head/merge/main evidence belongs in this enhancement's PR description.

## Decision and blocker records

Apply D01–D12 in ExecutionDecisions. Record implementation-specific choices such as seed SHA, relocated gate paths, actual command evidence, file-only service removals, configured origin, launch set and owner-approved deferrals. Do not reopen settled defaults merely because an older outline used “choose.”

```text
Decision ID/date:
Affected packet:
Decision and reason:
Evidence/source or applicable owner instruction:
Follow-up impact:
```

```text
Blocker ID/date:
Affected packet and what was attempted:
Smallest missing input/action:
Actor: controller agent / node agent / operator / upstream delivery:
Independent work that can proceed:
One-step handoff issued and private note location:
Response/evidence received:
Exact resume action:
```

A node/operator handoff can pause its dependent packet while independent content work remains available. If a live autonomous goal exists, follow the goal tool's status rules; this ledger alone does not authorize changing goal status. Never mark a required blocked packet complete to advance the plan.

## Release and operator handoff record

Store public/sanitized evidence here. Keep node address/login, host/runner labels, provider resource IDs, secrets and runtime paths in the private note.

```text
Operator authorization and scope:
Main release SHA / build run / image digest:
Frontend and acceptance profiles:
Content revision and published slugs:
Native identity/collision/capacity gate result:
Bootstrap/setup actor and last completed step:
Controller pairing status: prepared / authorized / verified:
LAN acceptance result and report reference:
CD run ID/URL and outcome:
Public HTTPS/browser acceptance result:
Doctor/backup result for services actually retained:
Previous compatible release / recovery evidence:
Remaining operator action or limitation:
```

## Resume prompt for another agent

```text
Continue Portfolio using Plans/PortfolioStudioImplementation.md and all companions, especially Progress, ExecutionDecisions, ImplementationCheckpoints and VisualProduction. This is an independent product in Grumlebob/Portfolio from a verified merged template baseline. Another agent owns unfinished upstream React SR1–SR6 delivery; preserve its worktrees and existing Blazor deployment. Retired-repository cleanup is complete; do not recreate it. Prefer completed reusable delivery and inspect actual capability dependencies before import.

Use Architecture.md's vertical slice boundaries. After platform prerequisites, finish one real ImprovedDb journey through content, C# APIs, React home/reader, prerender/hosting and acceptance before expanding the catalog. P4/P5 and first-story P7 work are one VS1 outcome. Repeat later P6 stories end to end; do not mark an API-only or UI-only checkpoint a verified product slice.

If resuming a planned fresh-chat checkpoint, use its filled handoff above. Recommend only C1–C3 after their verified exits; no reset per PR/story and no automatic goal pause or completion. Recheck live evidence and record claim transfer before editing.

Inspect actual repository/remotes/main CI, task ownership and dirty files. Read the ignored Plans.local/Portfolio/OperatorIntent.md if present; never commit its local paths/node facts/secrets. If still in the template, complete P0 and move implementation to the intended Portfolio checkout. After import, use the downstream ledger as authority.

Choose the first eligible unfinished packet, record a claim and complete its specific output/checks. Required end state: Portfolio naming, React frontend/C# backend, no Books or Blazor product, LocalSingleNode only, approved Studio home/continuous illustrated project stories and public Portfolio acceptance. Use small PRs, applicable local gates, exact-head build-test-push, normal merges and green main evidence. Update Progress with precise next action.

For native-only or operator-only steps, use NodeHandoff.md and return one simple verified action or node-agent prompt. Do not bootstrap this Windows controller, run sudo yourself, invent commands, silently rename a node or borrow another delivery's deployment authorization. Preserve provider/SSH ownership state. Do not claim completion from plans, mockups or queued workflows.
```
