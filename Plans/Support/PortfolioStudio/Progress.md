# Portfolio progress and resume ledger

Read [master plan](../../PortfolioStudioImplementation.md), [phases](DeliveryPhases.md), [page briefs](PageBriefs.md), [source inventory](ProjectInventory.md) and [node handoff](NodeHandoff.md) before implementation.

## Current checkpoint

Last updated: 2026-10-11. Planning prepared; no Portfolio code, node bootstrap or deployment executed by this task.

- Destination: [Grumlebob/Portfolio](https://github.com/Grumlebob/Portfolio). It existed and was empty when inspected; recheck before import.
- Source: [Grumlebob/BlazorAutoAppTemplate](https://github.com/Grumlebob/BlazorAutoAppTemplate).
- Inspected upstream main: `99c319fc38b3b443cd7115093a5c614c1f9de7e3`; successful [CI run 38146167014](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38146167014). This is a planning checkpoint, not the final seed selection.
- Another agent owns the unfinished [React delivery goal](../../ReactFrontendDeliveryGoal.md). Fetch/read its current evidence; preserve its work.
- Product decisions: Portfolio naming, React frontend/C# backend, Books/Blazor removal, LocalSingleNode-only deployment and intended public URL `https://portfolio.jacobgrum.com/`.
- Supplied local checkout/node details: ignored `Plans.local/Portfolio/OperatorIntent.md`. Transfer privately to the downstream checkout. GitHub authentication on the fresh native node is reported, not independently verified.
- Recommended next task: **P0.1**. Inspect the live upstream dependency gate, then decide the seed baseline. No project source needs to be changed for that inspection.
- Public launch authorization: not recorded for execution. This request prepares plans; do not dispatch a deployment from it.

After P0 import, this ledger in **Portfolio** is authoritative. Retain a link from the template plan to downstream execution evidence. Do not maintain two competing live ledgers or import the React agent's progress as Portfolio progress.

## Phase ledger

Statuses: `pending`, `ready`, `in progress`, `blocked`, `merged`, `verified`, `owner-deferred`. `merged` records code integration; a phase becomes `verified` only when its exit evidence is satisfied. A queued CI run is not green evidence.

| Phase | Status | PR / final head / merge / main CI | Evidence or exact next action |
| --- | --- | --- | --- |
| P0 Baseline/import | Pending | — | Verify upstream completion/dependencies, remote state and selected SHA |
| P1 Portfolio naming | Pending | — | Build rename inventory after import; establish CI capacity if absent |
| P2 React-only cleanup | Pending | — | Remove Blazor/profile branches with replacement checks |
| P3 Single-node cleanup | Pending | — | Move shared audit/smoke dependencies before target deletion |
| P4 Portfolio content/API | Pending | — | Implement public bundle/contracts and remove Books |
| P5 Studio home/reader | Pending | — | Implement/review home and ImprovedDb in both themes |
| P6 Eleven stories | Pending | — | Prepare sources/media; publish only reviewed destinations |
| P7 Rendering/release | Pending | — | Exact prerender hosting, Portfolio acceptance and runtime decision |
| P8 Native node/SSH | Pending | — | Use native runbook; bring CI bootstrap forward if required |
| P9 Public launch | Pending | — | Record authorization/release; complete LocalSingleNode public setup |
| P10 Recovery/handover | Pending | — | Update/recovery evidence and all-story disposition |

## Current packet record

Copy this record for each active packet. Keep finished packet records or link their PR descriptions. Record enough for an agent with no earlier chat to continue.

```text
Packet ID and title:
Status:
Owner/session and start date:
Repository and base main SHA:
Branch/worktree:
Claimed files:
Inputs/dependencies verified:
Output implemented:
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
| P6.7 BestBets | Prior report review; preferred Exam/deck located | Outline | Preferred deck/figures need review | Design study; role pending | Pending | Review owner-selected materials and reconcile versions |
| P6.8 Geospatial research | Notebook/report structure | Outline | Genuine maps/plots; select | Team context; role pending | Pending | Dates, attribution and limitations |
| P6.9 GeckoBot | Private mail/MailDemo trees/declarations reviewed | Brief | Fictional captures pending | Version/status pending | Draft | Review requirements and confirm intended version |
| P6.10 Grumlebob | Owner explanation; restricted folder located | Domain-neutral brief | Approved generic figures pending | Pending | Draft | Obtain approved public explanation; source inspection optional |
| P6.11 JobHunt | General private docs reviewed | Outline | Flow concept; fictional captures pending | Boundary alignment pending | Draft | Resolve manual-writing/account-creation copy |

Launch set: not yet approved/published. Recommended: ImprovedDb, KinoJoin, TraceBack, Unlost when ready. Initial launch does not close unfinished story packets.

Owner source update on 2026-10-11: GeckoBot's private mail/MailDemo repositories are recorded, with mail recommended from read-only tree/Python-declaration comparison. BestBets' preferred Exam PDF and presentation are located but unreviewed. Grumlebob's restricted background folder is located; use the owner's approved explanation, exclude private context/artifacts/results, and do not require source inspection. Exact local locations and the explicit private publication boundary are in ignored `Plans.local/Portfolio/ProjectSources.md`.

## Decision and blocker records

Record a decision when a future agent would otherwise have to infer it. Examples: seed SHA, audit relocation paths, retained DB/Redis, canonical URL setting, final acceptance-profile name, published launch set and owner-approved deferrals.

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
Continue Portfolio using Plans/PortfolioStudioImplementation.md. Read all linked companions, especially Progress.md, before editing. This is an independent product in Grumlebob/Portfolio, cloned from a verified merged BlazorAutoAppTemplate baseline. Another agent owns upstream React delivery; preserve its plan/worktrees/demo.

Inspect actual repository/remotes/main CI, task ownership and dirty files. Read the ignored Plans.local/Portfolio/OperatorIntent.md if present; never commit its local paths/node facts/secrets. If still in the template, complete P0 and move implementation to the intended Portfolio checkout. After import, use the downstream ledger as authority.

Choose the first eligible unfinished packet, record a claim and complete its specific output/checks. Required end state: Portfolio naming, React frontend/C# backend, no Books or Blazor product, LocalSingleNode only, approved Studio home/continuous illustrated project stories and public Portfolio acceptance. Use small PRs, applicable local gates, exact-head build-test-push, normal merges and green main evidence. Update Progress with precise next action.

For native-only or operator-only steps, use NodeHandoff.md and return one simple verified action or node-agent prompt. Do not bootstrap this Windows controller, run sudo yourself, invent commands, silently rename a node or borrow another delivery's deployment authorization. Preserve provider/SSH ownership state. Do not claim completion from plans, mockups or queued workflows.
```
