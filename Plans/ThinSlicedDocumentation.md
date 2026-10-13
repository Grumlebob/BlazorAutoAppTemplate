# Thin, Sliced Template Documentation

Status: prepared; documentation restructuring has not started.
Baseline inspected: `e59d39c5263b5e227ff7124b7abacb0d263fe326` on `origin/main`, 2026-10-13.
Preceding cleanup: [PR #225](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/225) removed the project-specific migration prompt and unrelated project details.

## 1. Outcome and scope

Make the durable documentation easy for a new developer or a less capable AI to navigate without loading unrelated guides. Keep sufficient instructions to complete each task safely and correctly. Achieve this through task-sized slices, canonical ownership, source links and removal of redundant content.

Scope: root `README.md`, `AGENTS.md`, `CLAUDE.md`, ordinary Markdown under `docs/` and `Deployment/`, and the narrow audit changes described in D2. Preserve every supported frontend and deployment target.

Existing plans and historical plan records are outside the cleanup scope. This file records only this plan's current progress and links to PR evidence. Do not rewrite other plans, touch downstream product folders, implement application changes, alter deployment settings or operate live services.

This request prepares the plan. It does not authorize execution of its implementation packets or deployment workflows.

## 2. Executor instructions

1. Read `AGENTS.md`, this plan's status, the relevant packet, and its source files. Do not read every guide or historical plan first.
2. Fetch `origin`, inspect branch/worktree ownership and dirty files, and use an isolated task branch based on current `origin/main`. Preserve other work. The baseline SHA is evidence, not a required old branch base.
3. Execute D1 first. D2 precedes any D4/D7 movement that changes audited guide content. D3, D5 and D6 depend on D1 but can be separate sequential PRs. D8 follows all selected packets.
4. Each numbered step below is a checkpoint. Complete its action and verification before marking it done. Each packet is normally one PR; split D7 into one PR per target if necessary.
5. Record the active step and concrete next file/action in section 11. Keep inspection outputs and section disposition notes in ignored `Plans.local/`; commit only durable docs and the small progress record.
6. A renamed heading is a link change. Update inbound links in the same PR. A removed example needs a source reference or a reason that its information is redundant or irrelevant.
7. When source and docs disagree, document implemented behavior. Do not silently change source behavior to match prose. Repository working rules take precedence over an outdated guide's description of the verification process.
8. If a packet would modify non-Markdown files beyond D2's explicit scope, stop that expansion, record the dependency and prepare a separate code proposal. Do not smuggle code into a documentation PR.

## 3. Work already performed

The preparation inspected all 34 tracked durable Markdown files by path, size and headings. It checked their explicit relative Markdown destinations and 13 local heading anchors, inspected repeated command references, and read documentation consumers in deployment scripts and audits. It did not run application tests, deploy, contact nodes or alter documentation beyond the preceding cleanup.

The scoped corpus contains **46,576 whitespace-separated words**, including code blocks. This is a reproducible proxy for context size, not a tokenizer measurement. A standard initial read of `AGENTS.md`, `README.md` and `docs/Requirements.md` costs 2,340 words. Adding the entire feature guide costs 6,502; adding the frontend guide costs 5,166; adding the test guide costs 5,679.

| Existing entry | Words | Lines | Intended disposition |
| --- | ---: | ---: | --- |
| `README.md` | 1,323 | 159 | Short overview, one local start command, task links |
| `AGENTS.md` | 625 | 43 | Keep mandatory rules; link detailed commands |
| `CLAUDE.md` | 2 | 1 | Keep its `AGENTS.md` pointer |
| `docs/Requirements.md` | 392 | 38 | Keep canonical product constraints |
| `docs/HowToRunLocally.md` | 1,285 | 326 | Keep local operation; remove unrelated test/deployment details |
| `docs/HowToAddANewFeature.md` | 4,162 | 865 | Short workflow plus server and Blazor slices |
| `docs/HowToForkThisRepo.md` | 4,212 | 784 | Shared identity workflow; route cluster steps to their target |
| `docs/FrontendProfiles.md` | 2,826 | 154 | Profile contract plus focused React workflow |
| `docs/Test.md` | 3,339 | 435 | Canonical local gate plus browser/infrastructure slices |
| `docs/Quality/QualityTools.md` | 1,233 | 76 | Keep on-demand tool operation and report interpretation |
| `docs/Quality/SonarQubeAnalysis.md` | 1,772 | 168 | Audit usage plus separate maintenance slice |
| `docs/ObservabilityGuide.md` | 2,258 | 776 | Task entry with architecture and operations slices |
| `Deployment/README.md` | 451 | 38 | Target selection only, linked prerequisites |
| `Deployment/LocalCluster/HowToDeployLocalCluster.md` | 9,547 | 1,677 | Target entry plus setup, settings, existing-cluster and operations slices |
| `Deployment/Cloud/HowToDeployCloud.md` | 4,048 | 1,008 | Target entry plus setup and operations slices |
| `Deployment/LocalSingleNode/HowToDeployLocalSingleNode.md` | 2,475 | 166 | Short setup route plus focused operations slice |

Remaining files are target/component indexes, existing native setup/security guides and four short observability runbooks. Keep these unless their entire role becomes redundant after their parent is updated. Small file size alone is not a reason to merge or split a file.

### Verified defects and dependencies

- `docs/Quality/SonarQubeAnalysis.md` links to `../Test.md#lighthouse`; the existing heading is `## Lighthouse Performance`, whose anchor is `#lighthouse-performance`. No missing explicit relative file destinations were found.
- `Deployment/Cloud/README.md` says every node gets public IPv4. The main guide and `Deployment/Cloud/infra/opentofu/main.tf` disagree: only `cloud-main` uses the public networking variables; private servers explicitly disable public IPv4 and IPv6 and use NAT egress. Correct the README from source.
- `Deployment/README.md` says never delete unused targets, while `Deployment/LocalSingleNode/SingleNodeOnlyClone.md` describes an intentional dependency-aware removal. Distinguish ordinary target disabling from a deliberate code/CI simplification of a fork.
- `docs/Test.md#local-gate` permits relying on CI when local checks cannot run. `AGENTS.md` requires the local gate before pushing code. Align the guide with the working rule; do not introduce a new CI-first exception.
- Restore/build/test, headed E2E, CSS build and observability start commands recur across the README, local guide, feature guide and test guide. Their canonical owners are assigned in section 5.
- The LocalCluster audit at `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` reads the guide at its existing path. Its current guide loop requires **60 literal strings**, all present at the baseline. It also requires the guide to document **27 top-level `all.yml` keys** in backticks, all present.
- The audit separately requires verified SSH key acceptance and exact CI-run-attempt publishing guidance in **both** the LocalCluster guide and fork guide. Moving their sections without updating the consumer breaks these checks.
- `Deployment/Cloud/Scripts/doctor.sh` checks that the current Cloud guide path exists. LocalCluster lock scripts point users to the `Deployment lock` section in the current guide. Keep those entry paths and the recovery anchor reachable.

Preparation reports exist in ignored `Plans.local/` in the planning worktree: `thin-docs-inventory.json`, `thin-docs-links.json`, and `thin-docs-audit-contract.json`. They contain no live installation values. Their presence is optional; the facts above and source paths are sufficient for a new checkout. Recreate them when the baseline changes.

## 4. Acceptance criteria and editorial rules

### Reading and size targets

- Required initial reading is only `AGENTS.md`, `docs/Requirements.md` and the short root README: **at most 1,500 words combined**. Aim for README <= 350, requirements <= 450 and working rules <= 700 words.
- A routine task should require that common reading plus at most two focused documents, **at most 3,200 words combined**. Measure local start, adding a Blazor feature, adding a React feature, running normal checks and customizing a fork separately.
- A deployment phase should be accessible from the target entry plus the phase's focused slice. Aim for **at most 4,500 words** for that phase including common rules and necessary shared reference material. A whole first installation can span multiple phases.
- Aim for **at least 20% less total text** than the inspected corpus, <= 37,260 words using the same counter and scope. This is a review target, not permission to remove necessary safeguards. Record any justified overage and its cause.
- Creating additional files must reduce a concrete task's required reading. Do not move whole paragraphs into new files solely to meet per-file limits.

### Content rules

Each focused guide opens with its task, prerequisites and the exact document to read next. Operator steps retain execution location, required privilege, inputs, command, expected success and failure/recovery route. Generic background may be omitted when source or a linked canonical guide answers it.

One document owns each detailed rule or procedure. A short summary or task-specific invocation may repeat when needed to make a step usable, but it links to the owner. Shared host restrictions, secrets handling, authentication boundaries, restore procedures and deployment provenance must remain visible at the point of risk.

Link existing implementations for boilerplate. Keep a short code example only when it teaches a rule a source link cannot make clear. Do not invent a new sample feature, add generated docs, copy entire source files into guides or create another migration prompt.

Keep current limitations that change user decisions. Remove completed rollout notes, implementation packet IDs, superseded alternatives, historical dates, private-machine details, personal usernames, downstream-project instructions and unimplemented wish lists. Keep generic template role names and a project reference only when necessary to explain actual template behavior. Use package manifests and settings as the version/default authorities.

Preserve entry filenames below. Add slices adjacent to their subject rather than creating a competing documentation root. All links must resolve; links to source files must survive ordinary line-number changes. Prefer paths and symbols over fragile exact line references.

## 5. Canonical ownership and intended slices

Paths listed as new are proposed outputs, not existing links. Do not create an empty slice in advance. Keep each old entry usable during the transition.

| Topic | Canonical owner or new slice | What other docs do |
| --- | --- | --- |
| Agent workflow, integration policy, hard stops | `AGENTS.md` | Link; retain only local reminders at risky operations |
| Product/rendering/security constraints | `docs/Requirements.md` | Link rather than copying constraint lists |
| Local Docker, direct .NET, ports, CSS and EF commands | `docs/HowToRunLocally.md` | Show only the entry command or link to the needed heading |
| Feature boundaries and implementation sequence | `docs/HowToAddANewFeature.md` | Link from README and fork workflow |
| Persistence, contracts, endpoint/service/DI examples | New `docs/Features/Server.md` | Link actual Books implementations and shared contracts |
| Blazor client, state, prerender and UI integration | New `docs/Features/Blazor.md` | Link product rules and actual client code |
| Profile selection, composition, static hosting, release profile pairs | `docs/FrontendProfiles.md` | Link instead of repeating profile internals |
| React development, generation and extension | New `docs/Frontend/React.md` | Link package pins, generated contract tooling and local service setup |
| Local gate and normal test entry | `docs/Test.md` | Link from feature/local guides and `AGENTS.md` |
| Browser E2E, React regression, Lighthouse | New `docs/Testing/Browser.md` | Keep links from old test headings |
| Fixtures, architecture, hosting/cache checks, collection behavior | New `docs/Testing/Infrastructure.md` | Reference actual fixture and architecture files |
| Quality audit usage | Existing `docs/Quality/*.md` | Link from test index; audits remain optional |
| Sonar server/token/backup/upgrade maintenance | New `docs/Quality/SonarQubeMaintenance.md` | Keep usage guide focused on running and reading reports |
| Telemetry topology, source configuration and label policy | New `docs/Observability/Architecture.md` | Link from feature telemetry instructions |
| Dashboard access, queries, retention, recovery and validation | New `docs/Observability/Operations.md` | Link from `docs/ObservabilityGuide.md` and target-specific acceptance |
| Shared fork identity and frontend/target decisions | `docs/HowToForkThisRepo.md` | Target guides link to it |
| Release SHA/run-attempt/digest/migration/profile contract | New `Deployment/Common/ReleaseContract.md` | Keep target-specific commands; link shared invariants |
| SSH fingerprint comparison and approved known_hosts acceptance | New `Deployment/Common/SshTrust.md` | Keep target inputs and point to the exact trust procedure |
| Target choice and enable/disable | `Deployment/README.md` | Link from fork and root README |
| LocalCluster target route | Existing `HowToDeployLocalCluster.md` | Link new adjacent `Setup.md`, `Settings.md`, `ForkExistingCluster.md`, `Operations.md` |
| Cloud target route | Existing `HowToDeployCloud.md` | Link new adjacent `Setup.md` and `Operations.md` |
| LocalSingleNode setup and operation | Existing native setup guides plus new adjacent `Operations.md` | Keep `AgentSetup.md` as the native agent entry; no bootstrap from a controller |

Avoid a new universal configuration table: inventories, release settings, compose files, package manifests and script parameter declarations remain authoritative. Document what an operator must choose and why, and link the source of default values.

## 6. Granular implementation packets

### D1. Correct drift and establish the task entry

Inputs: section 3, `README.md`, `AGENTS.md`, `docs/Requirements.md`, the known defect files and their cited sources. Ordinary Markdown only.

- [x] **D1.1 Recheck the baseline.** Fetch main; confirm each verified defect still exists. Make an ignored table mapping every current section to keep, shorten, move or remove, with its destination/reason. Read code fences as content; heading scanners must ignore headings inside code examples. Verify the mapping covers all 34 baseline files and any new durable files.
- [x] **D1.2 Fix current drift.** Correct the Lighthouse anchor, Cloud networking summary, deployment chooser's ordinary-disable versus intentional-single-target distinction and local-gate policy wording. Verify each correction against the named source. Do not use the source network example as a live address.
- [x] **D1.3 Rewrite the root README.** Keep a brief product/profile description, one local start command and a task table for local run, feature development by profile, tests, forks, deployment and observability/quality. Remove detailed topology, middleware/default lists, complete E2E/CSS commands and sample-product prose from this entry; retain their unique current facts in their owners before removal. Verify the common reading budget.
- [x] **D1.4 Preserve mandatory rules.** Keep `CLAUDE.md` as its existing pointer. Keep `AGENTS.md` and requirements concise and authoritative. Add a brief task-reading instruction only if README routing alone is insufficient; do not expand the working rules with the plan's full taxonomy. Verify all hard stops, local-gate requirements and product constraints remain.

Exit: known defects corrected, initial task routing usable and common reading <= 1,500 words. Documentation PR follows section 7.

### D2. Make audited guide slicing possible

This packet defines the only planned code-change scope: adapting documentation checks and their declared slice map. Later D4/D7 map adjustments remain within that scope and still require code gates. The owner selected this packet because full deployment-guide slicing must keep existing audit protections without artificial filler. Inputs: the deployment audit, its local guide loop, the top-level settings check, the dual-guide SSH/provenance check and existing script test conventions. Preserve every rejection rule's intent.

- [ ] **D2.1 Build the contract map.** Extract the current 60 literal checks, 27 settings keys and the three shared SSH/provenance literals per root guide into ignored notes. Assign each to setup, settings, existing-cluster operations or shared trust/release ownership. Inventory root path requirements, stale-path checks, fence validation and script existence checks. Verify there is a destination and acceptance condition for every current rule.
- [ ] **D2.2 Add bounded documentation loading.** Keep the original entry files. Add a small explicit per-entry list of permitted documentation slices, initially empty so this PR works before movement. When a slice is declared, require its file and a reachable Markdown link from that entry or a declared intermediate slice. Do not concatenate every Markdown file or follow arbitrary paths into plans/private files. Reject missing/unreachable files and paths outside declared doc roots.
- [ ] **D2.3 Apply checks to the right owner.** Validate fences and referenced target scripts per included file; evaluate each mapped rule in its owning slice, with the existing entry as fallback until that section moves. Validate settings keys in the declared settings owner. Require both fork and target routes to reach shared SSH/provenance instructions. Preserve actionable error messages naming the failing path and rule. Replace arbitrary example-name checks only with equivalent ownership/uniqueness checks; never keep unrelated filler solely to satisfy a string check.
- [ ] **D2.4 Prove the rejection behavior.** Add focused tests for the new loader/check boundary: baseline old layout passes; correctly linked split passes; missing slice, unreachable safety guidance, deleted required rule, missing settings key, unbalanced fence and missing referenced script fail. Include a path outside the allowed root and an absent declaration in negative cases. Keep unrelated deployment rules unchanged. Use existing test locations; add a new test module only if no suitable module exists.
- [ ] **D2.5 Integrate the compatibility change.** Run the focused tests and the full current code gate locally, sequentially where .NET output is shared. Require green `build-test-push` on the exact PR head and green exact integrated main CI. Do not apply `[skip ci]`. Record the audit contract mapping and runs in the PR before D4/D7 movement begins.

Exit: old docs still pass and declared slices can carry the same protected behaviors. This packet must not deploy, provision, alter secrets or change runtime configuration.

### D3. Slice development and testing tasks

Inputs: current feature, local, frontend and test guides; `BlazorAutoApp.Core/Features/Books`, server/client Books implementations, React package/scripts, and `BlazorAutoApp.Test/Architecture` plus test support. Ordinary Markdown only after D1.

- [ ] **D3.1 Reduce the feature entry.** Retain feature ownership, implementation order, generic migration guidance and links to the two frontend paths. Keep architecture decisions in the entry and refer to requirements for product constraints. Aim for <= 650 words. Verify an executor can identify the server, Core and selected client paths without opening an entire tutorial.
- [ ] **D3.2 Write the server slice.** Move persistence, service, endpoint and DI/startup instructions to `docs/Features/Server.md`, aiming for <= 850 words. Replace lengthy invented CRUD listings with links to `IBooksApi.cs`, a use-case DTO, `BooksServerService.cs`, `BooksEndpoints.cs`, `BookEntityTypeConfiguration.cs` and Books `DependencyInjection.cs`. Preserve validation, ownership enforcement, cancellation, cache invalidation and typed response guidance. Verify every linked symbol/file exists and the writing does not treat sample Books business rules as universal requirements.
- [ ] **D3.3 Write the Blazor slice.** Move client implementation, UI/state and hydration instructions to `docs/Features/Blazor.md`, aiming for <= 850 words. Link the client service, page/modal state and existing render tests. Keep the difference between prerendered and interactive execution clear. Link Tailwind commands and product rendering constraints to their owners. Verify it does not instruct React developers to create Razor components.
- [ ] **D3.4 Separate profile contract from React workflow.** Keep selection, profile isolation, supported/public-only boundaries, static hosting and release profile pairs in `docs/FrontendProfiles.md`, aiming for <= 650 words. Move toolchain setup, HTTPS dev proxy, generation, public query behavior, error handling and feature-extension steps to `docs/Frontend/React.md`, aiming for <= 900 words. Keep optional additional publication instructions reachable; link deployment operations instead of repeating their troubleshooting table. Verify both profile selection and API regeneration can be followed from task links.
- [ ] **D3.5 Make tests task-sized.** Keep the exact complete local gate and normal invocation in `docs/Test.md`, aiming for <= 800 words if the complete gate needs it. Move fixtures, architecture/hosting/cache details to `docs/Testing/Infrastructure.md`; move E2E variables, browser suites, artifacts and Lighthouse to `docs/Testing/Browser.md`. Link source for test inventories that change often. Preserve sequential .NET build/test, Docker prerequisites, opt-in E2E, profiles, data cleanup and visible/headless behavior. Give the most common browser task a focused subsection so the reader need not load every browser recipe.
- [ ] **D3.6 Remove local-guide duplication.** Keep local prerequisites, `.env`/ports, Docker/direct-.NET paths, reset consequences, CSS and migration commands. Replace repeated test/deployment gate blocks with links to `docs/Test.md`. Reconcile `npm install` versus `npm ci` guidance with the checked-in lockfile and intended task rather than blanket replacement. Verify local reset remains scoped to the local stack and clearly identifies data deletion.
- [ ] **D3.7 Repair routes and measure.** Search all tracked Markdown for old headings and moved topics, update live inbound links and keep needed old test anchor headings as small pointers. Measure common+entry+selected slice for Blazor, React, local start and tests. Shorten repeated context until each routine task meets its budget; do not require loading the opposite frontend guide.

Exit: source-linked feature instructions, a complete canonical gate and usable task routes. No application examples or code files added.

### D4. Separate shared fork preparation from target deployment

Inputs: fork guide, chooser, current target guides, release settings, manifest validation and SSH trust procedures. Depends on D1 and D2 for full slicing.

- [ ] **D4.1 Write shared contracts.** Create `Deployment/Common/ReleaseContract.md` for source SHA, successful main-push CI attempt, digest, artifact/migration hashes and profile matching. Create `Deployment/Common/SshTrust.md` for independent fingerprint comparison and approved known_hosts acceptance. Preserve the exact protections currently enforced by the audit. Verify every target links to the relevant owner; do not centralize target-specific variable names without naming the target.
- [ ] **D4.2 Reduce the fork entry.** Keep identity choices, namespace separation, frontend selection, sample feature disposition and target routing in `docs/HowToForkThisRepo.md`, aiming for <= 850 words. Move LocalCluster preparation/deploy steps 7-18 into `Deployment/LocalCluster/ForkExistingCluster.md`. Keep the no-CI-runner ordering and single-target simplification link. Do not direct a single-node or Cloud fork through cluster-only steps.
- [ ] **D4.3 Preserve the existing-cluster workflow.** Keep side-by-side versus replacement choice, collision checks, scoped roots/ports/image/runner identity, trust verification, shared tunnel handling and exact release acceptance. Existing nodes must not be bootstrapped again. Deduplicate first-time cluster explanations by linking setup/settings slices when they exist, retaining current guide sections as owners until D7 creates them.
- [ ] **D4.4 Validate fork journeys.** Walk a native single-node fork, an existing-cluster fork and a Cloud fork using documented routes only. Verify each starts with shared identity and enters only its chosen target. Update the audit's declared slice map in a code PR if required, or include map changes with this movement as a mixed packet under section 7; never claim a PR containing Python is documentation-only.

Exit: a fork task no longer requires unrelated cluster installation instructions; its trust and release contract remain protected.

### D5. Keep quality docs operational

Inputs: existing quality docs, `Scripts/Quality` wrappers and settings/tool version manifests. Ordinary Markdown only after D1.

- [ ] **D5.1 Slim the tool guide.** Keep available tool purpose, prerequisites, exact commands, target/source scope, exit/report interpretation and timeout/owned-resource cleanup. Remove proposals, trial history and comparisons that do not affect operation. Link pinned tools to their existing manifest. Verify optional tools are not described as merge gates.
- [ ] **D5.2 Separate Sonar usage from maintenance.** Keep audit invocation, Quick/Full prerequisites, output meaning and report access in `SonarQubeAnalysis.md`. Move private namespace/credentials, token rotation, backup and upgrades to `SonarQubeMaintenance.md`. Keep limitations and credential privacy beside commands that need them. Do not remove the Windows-only Full-mode constraint or imply that Quick mode supplies Full-mode coverage.
- [ ] **D5.3 Validate quality routes.** Resolve local anchors and script paths. Link source for version pins and wrapper parameters; read parameter declarations before changing a documented flag. Keep maintenance reachable from the usage guide. Do not run scanners, start Sonar, rotate tokens or contact targets to verify a prose move.

Exit: each audit can be run and interpreted without reading server maintenance or unrelated tool history.

### D6. Slice observability by task

Inputs: `docs/ObservabilityGuide.md`, local/common observability assets, dashboards, alert rules and four existing runbooks. Ordinary Markdown only after D1.

- [ ] **D6.1 Create the task entry.** Reduce `ObservabilityGuide.md` to enable/access/diagnose/change-telemetry routes, supported target coverage and fail-open behavior, aiming for <= 650 words. Keep old heavily linked headings as pointers when practical.
- [ ] **D6.2 Create architecture guidance.** Move signal flow, configuration ownership, bounded cardinality, correlation and sampling into `docs/Observability/Architecture.md`. Use one compact diagram or topology reference. Link actual configuration rather than copying manifests. Keep public/private and app/backend/collector boundaries clear.
- [ ] **D6.3 Create operator guidance.** Move access, queries, validation, retention, capacity, disable/recovery and alert/runbook links into `docs/Observability/Operations.md`. Keep common commands canonical here; target docs keep only their target-specific tunnel/doctor/acceptance invocation and link the common operation. Preserve recovery order and data-loss consequences.
- [ ] **D6.4 Remove backlog prose and verify coverage.** Remove `Known Post-v1 Work` proposals unless a limitation affects current use; retain relevant current limitations in the correct slice. Keep the four short runbooks. Check each old section's disposition and all local/source links. No telemetry services or alerts are changed.

Exit: enabling/accessing telemetry and changing instrumentation use different focused routes, with no rollout history required.

### D7. Slice deployment without losing execution order

Inputs: target runbooks and source scripts/settings/roles. Depends on D1, D2 and D4 for full slicing. This packet edits docs and, when slice declarations are added, the narrowly scoped D2 audit map. Follow the corresponding code gate for mixed PRs.

- [ ] **D7.1 Refactor the LocalCluster entry and setup.** Keep the current entry filename, machine roles, phase order and links. Move install/control/bootstrap/router/inventory/secrets/runner/environment/first-release steps into `Setup.md` with phase headings. Each phase specifies which machine executes it and its success checkpoint. Keep router reservation before generated inventory and host trust before accepting keys. Keep the `Deployment lock` anchor in the original guide as a concise recovery pointer used by existing scripts.
- [ ] **D7.2 Separate cluster settings and operations.** Put the 27 currently checked settings keys and uniqueness choices in `Settings.md`, with source-of-default links. Put repeat deploys, backup/restore/rollback, ownership-safe maintenance, lock recovery and troubleshooting in `Operations.md`. Finish deduplication against `ForkExistingCluster.md` from D4. Verify setup, existing-cluster fork and routine maintenance each choose one route, and all original audit intentions still have reachable owners.
- [ ] **D7.3 Refactor Cloud routes.** Keep its entry path for `doctor.sh`. Move tools/keys/settings/OpenTofu/inventory/tunnel/environment/provision/first-release into `Setup.md`; move repeat deploy, acceptance, observability pointers, backup/recovery and destroy/recreate into `Operations.md`. Confirm networking against Terraform, retain private-node/NAT/firewall boundaries and distinguish resource destruction from ordinary repair. Remove alternatives and stale literal release names; link shared release settings and provenance.
- [ ] **D7.4 Refactor native single-node routes.** Keep `AgentSetup.md`, controller SSH, public setup, instance selection and readiness guides as focused tasks. Reduce `HowToDeployLocalSingleNode.md` to native setup/resume/verification routes and move detailed repeat release, maintenance, restore and rollback instructions to `Operations.md`. Preserve the native Linux-only setup restriction, the state machine's authentication/root handoff and authorization requirements. Do not duplicate those rules in every guide.
- [ ] **D7.5 Remove obsolete component prose.** Review the small component READMEs after their target routes are complete. Delete one only if it contains no unique ownership/runtime facts or entry instructions and all inbound references have replacements. Otherwise retain a small role/path description. Do not keep stale topology claims or generic empty-directory explanations.
- [ ] **D7.6 Validate operator journeys and consumers.** Trace first setup, adding an app to existing hosts, ordinary release, failed-readiness diagnosis, backup/restore and lock recovery for each applicable target. Use source comparison, not live execution. Check current doctor/lock-script path references. Run required audit/code checks for any changed audit map; document task reading budgets and unresolved source contradictions.

Exit: each target has an ordered setup route and focused operations route; no live actions occurred and no safety/provenance coverage was discarded.

### D8. Complete the documentation acceptance

- [ ] **D8.1 Check the whole scoped corpus.** Count words with the baseline scope and whitespace algorithm. Check all relative Markdown paths/anchors, balanced fences, moved-heading inbound references and source file destinations. Exclude code-example headings when computing anchors. Inspect plain-text/backtick references with `git grep`; a Markdown-link check alone does not cover them.
- [ ] **D8.2 Walk the task table as a new executor.** Starting from root README, independently follow local start, new Blazor feature, new React feature, standard gate, fork-per-target, optional quality audit, telemetry failure, backup/restore and lock recovery. Record documents and words actually needed, not whole folders. Verify each task has a concrete next action, required inputs and a failure route.
- [ ] **D8.3 Check information conservation and deletion.** Reconcile every baseline section against its keep/move/remove map. Review removals for unique runtime, authorization, ownership, data-loss or recovery information. Search live docs for other-project names, personal examples, completed packet IDs, historical handoffs and future-wish-list prose; inspect matches individually. Keep actual template behavior even when a sample name appears in source.
- [ ] **D8.4 Verify integration and close.** Fetch main, verify all selected changes and deleted paths there, and record exact commits/PRs plus budget results in section 11 or linked PR descriptions. Mixed-code packets require green exact-main CI; pure documentation packets use the existing exception. Mark this plan complete only when selected packet exits and all applicable checks pass. If the owner chooses Markdown-only scope, describe the retained deployment guide limits explicitly rather than claiming full slicing.

## 7. Verification and integration procedure

For an ordinary Markdown-only packet:

1. Inspect `git diff --name-status` and the complete diff, including old/new rename paths. Confirm every changed path is ordinary `.md`/`.mdx` documentation.
2. Run `git diff --check`. Inspect links, code fences, source paths and changed command semantics by reading source; do not execute operational examples as validation.
3. Stage explicit paths, commit with `[skip ci]`, push the task branch and create a PR. Put the section disposition, reading budgets and verification evidence in its description.
4. Review the final PR diff and exact head. Use `[skip ci]` in the squash title. Respect protection without weakening it or fabricating checks.
5. Merge, fetch and compare integrated file contents on `origin/main`. Record the merge SHA. No build, formatting/test/deployment gate or PR/main CI wait is required for this documentation-only path.

For D2 or any packet containing an audit declaration/code change:

1. Run focused meaningful audit tests, then the **complete current** local gate in `docs/Test.md#local-gate`. Keep build and test sequential in the same checkout. Do not substitute CI for a required first local run.
2. Update the audit rule when documentation behavior it protects changes. Preserve the rejection condition with a new equivalent rule and its negative test; deleting the rule is not an acceptable fix.
3. Push only after the local gate passes. Require green `build-test-push` for the exact final PR head; squash-merge and require green exact integrated main CI. Record the run URLs and source SHAs. Do not use `[skip ci]`.

If an enforced external gate fails, retain the work, record the real failure and resolve it through normal repository procedures. Installing available local tools, reading source, editing docs, preparing PRs and inspecting checks are agent work; do not convert them into manual operator tasks.

### Reproducible counting recipe

Run from the repository root using Python 3; it reads only tracked Markdown. Record output at packet boundaries. Run at baseline or after committing new files so newly added slices are included.

```python
from pathlib import Path
import subprocess

paths = subprocess.check_output(
    ["git", "ls-files", "*.md", "*.mdx"], text=True
).splitlines()
scope = [p for p in paths if p in {"README.md", "AGENTS.md", "CLAUDE.md"}
         or p.startswith(("docs/", "Deployment/"))]
counts = {p: len(Path(p).read_text(encoding="utf-8").split())
          for p in scope if Path(p).exists()}
for path, words in sorted(counts.items()):
    print(f"{words:6} {path}")
print("Total", sum(counts.values()), "words", len(counts), "files")
print("Common", sum(counts[p] for p in
                    ["AGENTS.md", "README.md", "docs/Requirements.md"]))
```

For links, inspect `](...)` destinations relative to their source file, split file paths from `#anchors`, and derive GitHub heading slugs outside fenced blocks, including duplicate-heading suffixes. Check explicitly changed anchors first, then all scoped links. An ad hoc checker stays in ignored scratch space unless the owner separately requests maintained tooling. External references need review only when their associated factual claims change; do not fetch all external links merely to rewrite local prose.

## 8. Decisions already made

- Keep all supported frontend and deployment targets; simplify documentation, not runtime support.
- Keep current guide entry paths so scripts, onboarding instructions and existing links can continue routing readers.
- Include the narrow audit compatibility work in D2 so deployment guides can move checked content while preserving equivalent rejection tests.
- Use task-sized Markdown and source links; no documentation framework, generated site, new runtime dependency or separate migration-prompt library.
- Keep product constraints and working rules authoritative. Preserve safety instructions and meaningful current limitations.
- Existing plans, downstream projects and private installation records are outside the cleanup scope.
- Use one plan file with a short execution ledger. Do not create another suite of goal prompts and historical handoff documents for this work.

## 9. Manual blockers

**No certain operator-only blocker is identified for preparing or carrying out the documentation work.** Source inspection, editing, scratch reports, link checks, PR preparation and verification are agent tasks with existing access.

Full deployment slicing needs D2's local code gate and CI, which are technical dependencies rather than planned manual actions. Diagnose/install available tools within authorized scope. Report a concrete missing capability only when it actually prevents a required check; do not preemptively assign Docker setup, GitHub login, node bootstrap, sudo, credentials or deployment actions to the owner.

Documentation verification does not require contacting a deployment node, running a backup/restore drill, starting a scanner or dispatching any deployment. Those operator handoffs remain documented for future real installations; they are not blockers for this plan.

## 10. Chosen scope

**Include D2.** Adapt the deployment audit to declared, reachable documentation slices. Move each check to its canonical owner and retain its rejection behavior with focused negative tests. Never weaken or delete a check to allow a move. This lets D4/D7 shorten deployment task reading without retaining artificial duplicate content.

D2 and later audit-map changes use code gates: run focused tests and the full local gate, require green `build-test-push` on the exact PR head, then verify green CI on integrated main. Ordinary Markdown packets continue using the documentation-only exception. No further scope decision is open.

## 11. Progress and handoff

| Packet | Status | PR / integrated commit / verification | Next action |
| --- | --- | --- | --- |
| Preparation | Read-only inventory complete; plan prepared | Baseline and findings in section 3 | Retain plan through a documentation PR |
| D1 | Prepared; pending PR integration | README 245 words; common reading 1,315 words; 34-file disposition map; source and changed links reviewed; `git diff --check` clean | Open and merge the docs-only PR, then verify `origin/main` and record the integrated SHA |
| D2 | Selected; pending | — | D2.1 Extract the audit contract map and assign each rule to its canonical slice |
| D3 | Pending | — | Follow D3.1 after D1 integration |
| D4 | Pending | — | Follow D4.1 after D1 and selected D2 scope |
| D5 | Pending | — | Follow D5.1 after D1 integration |
| D6 | Pending | — | Follow D6.1 after D1 integration |
| D7 | Pending | — | Follow D7.1 after D4 and selected D2 scope |
| D8 | Pending | — | Review task journeys after all selected packets |

Active checkpoint: D1.1–D1.4 are complete on `docs/d1-task-entry`. All changed paths are ordinary Markdown. Next: open, review and integrate the documentation PR, then record its integrated SHA before starting D2.

For each packet, record its exact next step, files owned, unresolved source contradiction, validation performed, PR/head, merge SHA and applicable main evidence. Keep detailed logs in ignored notes or the PR. A new executor should be able to select the next unchecked step without earlier conversation history.
