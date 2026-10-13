# Portfolio Studio delivery goal

## Status (2026-10-13)

The original goal below has been delivered:
- https://portfolio.jacobgrum.com is live with all twelve stories, from release `c74f5f0` in [Grumlebob/Portfolio](https://github.com/Grumlebob/Portfolio).
- P0–P10 are verified, including public acceptance and recovery proof (rollback, restarts and reboot).
- The template defects found by this first clone are fixed upstream.

The exact evidence and the short remaining list are in [Progress.md § Current checkpoint](Support/PortfolioStudio/Progress.md). The authoritative copy is the one in Grumlebob/Portfolio.

## Continuation goal

Continue Portfolio delivery from the recorded checkpoint, without redoing finished work.

1. **Orient.**
   - Work in the Portfolio checkout (`C:/Users/jgrum/Documents/Programming/Csharp/Portfolio`, Grumlebob/Portfolio).
   - Read AGENTS.md, this file and `Plans/Support/PortfolioStudio/Progress.md` § Current checkpoint. Read companions only when a step needs them.
   - Recheck before claiming anything: `git status`, open PRs in Portfolio and BlazorAutoAppTemplate, main CI, and the last CD and maintenance runs.
2. **Authority.** The owner gave full authority on 2026-10-12/13, recorded in Progress § Release and operator handoff record. It covers:
   - implementation;
   - Portfolio and template repository operations, including merging your own PRs after the full local gate and exact-head green `build-test-push`;
   - live operations on the Portfolio node and Portfolio's own Cloudflare publication.

   It does not cover changing shared Cloudflare zone settings or touching the demo site.
3. **Finish the remaining work in Progress order:**
   - Land and verify PR #32. It keeps Cloudflare bot detection on through a per-response CSP nonce, adds a favicon, and aims to remove the console CSP error and raise Lighthouse best practices above 92.
   - Carry out owner-led story improvements as the owner supplies inputs.

   Each code change follows the same path:
   1. one small PR with explicit staged paths;
   2. full local gate, then exact-head CI, then merge;
   3. green main CI;
   4. `cd-localsinglenode.yml` deploy with the run ID recorded;
   5. LAN and public PortfolioPublicV1 acceptance with the expected content revision.
4. **Keep Progress authoritative.** After each merge or deploy, record the PR, head, merge, CI, CD run, digest and content revision, and the next action. Mirror the checkpoint into the template's `Plans/Support/PortfolioStudio/Progress.md` with a docs-only PR when it changes materially.
5. **Fix upstream.** When Portfolio exposes a template defect, fix it in Portfolio and open a separate, gated template PR.

**Completion:** the goal is complete when both of these are true:
- PR #32 is merged and deployed, the live site shows a clean console with bot detection still active, and the favicon and Lighthouse results are recorded;
- every story improvement the owner has asked for is merged, deployed and publicly accepted, or explicitly deferred by the owner in Progress.

A story that waits for owner input is not a blocker for other work. Record the input it needs and continue.

## Rules that still apply

- Do not fabricate claims, roles, permissions or approvals. Stories describe only what their sources support. The private evidence per story is in `Plans.local/Portfolio/FactNotes/<slug>.md`.
- Unlost: A* finds the same route as Dijkstra while exploring fewer edges. Never present it as a worse route.
- Never publish real people, credentials or private data from source repositories. Examples stay invented and say so.
- Never bootstrap Windows/WSL as a node, guess host values, run sudo, expose secrets, mutate foreign resources, prune unscoped or with `--volumes`, reclaim a deploy lock, force-push main, or redispatch a run because a watcher stopped.
- Use the native runbooks and verified SSH (`portfolio-node`). Return one verified command or prompt for any human-only step, and resume after its evidence.

## Original delivery goal (achieved 2026-10-13)

Deliver Portfolio at https://portfolio.jacobgrum.com with React/TypeScript, C# and LocalSingleNode/Cloudflare.

Read AGENTS.md, Plans/PortfolioStudioImplementation.md and companions. Inspect status, remotes, claims, CI and private notes. Preserve others' work; record deviations.

Verify ReactFrontendDeliveryGoal.md and ReactFrontendSingleRepository.md against merged code/checks. Pin a merged-green baseline with P0's capabilities. Prepare content while waiting. Do not copy open PRs, revive the retired demo repo or alter the live Blazor app.

Execute P0-P10 in Grumlebob/Portfolio. Seed safe app/image/runner identity before first push/bootstrap; preserve history and destination work. Rename to Portfolio. Remove Blazor, Books/accounts, Cloud and LocalCluster after relocating shared checks. Remove unused DB/cache/migrations coherently from runtime, release, CI and operations.

Use vertical slices: finish ImprovedDb through reviewed content, C# export, generated contracts, Studio home/reader, prerendered HTML, exact hosting and PortfolioPublicV1 acceptance. Add stories through the shared metadata reader. Every project has a Techs H2; top navigation links to /technologies, a brief categorized overview deduplicated from published-project technology IDs in one registry. Include this page in API/export/prerender/sitemap and acceptance.

Deliver twelve page/figure briefs, including Template: Lighthouse, SonarQube, Qlty, Trivy, ZAP, sitespeed.io, scc; Blazor/React frontends; Cloud/LocalCluster/LocalSingleNode deployments. These describe Template capabilities; Portfolio stays React/LocalSingleNode. Use recovered Grumlebob/Unlost source with dated report/media; exclude large downloadable maps. Grumlebob automates free online offers for passive income: owner reports approximately DKK 500,000 profit in one year and membership at capacity because of concern about being caught. Preserve this attribution and private-data boundaries.

Require responsive media, both themes, native section links, mobile/keyboard accessibility, true 404s and matching revisions. Do not fabricate claims, roles, permissions or approval. Four reviewed stories may launch first; finish all twelve or record explicit owner deferrals.

Claim one checkpoint; use small PRs and explicit staged paths. Run the local gate before push, build/test sequentially; apply AGENTS.md's Markdown-only exception. Require exact-head build-test-push and green exact-main CI for implementation. Record checks, PR/head/merge/main/release and next action. Recommend fresh chats at verified C1-C3 with filled Progress handoffs; these do not pause/complete the goal.

Use native runbooks and verified SSH. Record owner authorization before live setup/deployment; never borrow another agent's authorization. Return one verified command/node-agent prompt for a native/human-only step; resume after evidence. Never bootstrap Windows/WSL, guess host values, run sudo, expose secrets, mutate foreign resources or redispatch because a watcher stopped.

Finish public HTTPS/browser/API/deep-link/denial acceptance, immutable release proof, scoped update/restart/recovery/compatible rollback, catalog disposition and authoring/operations handover. Keep Progress authoritative. Complete only with merged-green packets and public/full-handover proof; progress independent work around missing inputs.
