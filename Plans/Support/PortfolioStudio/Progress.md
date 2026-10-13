# Portfolio progress and resume ledger

Read [master plan](../../PortfolioStudioImplementation.md), [architecture/slices](Architecture.md), [phases](DeliveryPhases.md), [execution decisions](ExecutionDecisions.md), [implementation checkpoints](ImplementationCheckpoints.md), [page briefs](PageBriefs.md), [visual production](VisualProduction.md), [source inventory](ProjectInventory.md) and [node handoff](NodeHandoff.md). The later goal prompt is [PortfolioStudioDeliveryGoal.md](../../PortfolioStudioDeliveryGoal.md).

> **Mirror.** This template copy mirrors the authoritative ledger in [Grumlebob/Portfolio](https://github.com/Grumlebob/Portfolio/blob/main/Plans/Support/PortfolioStudio/Progress.md) as of 2026-10-13. When the two differ, the Portfolio copy wins. Do the work in the Portfolio checkout (`C:/Users/jgrum/Documents/Programming/Csharp/Portfolio`).

## Current checkpoint

Last updated: 2026-10-13, at the end of the first delivery session. The authoritative ledger is this file in [Grumlebob/Portfolio](https://github.com/Grumlebob/Portfolio/blob/main/Plans/Support/PortfolioStudio/Progress.md). A fresh `/goal Plans/PortfolioStudioDeliveryGoal.md` run should read this section first, then the phase ledger and the project readiness ledger.

### Where things stand

The plan's product outcome is delivered. What remains: PR #32 (CSP nonce for Cloudflare bot detection, and a favicon) needs to land and be verified live, and owner-led story improvements continue.

- **Live site:** https://portfolio.jacobgrum.com serves all twelve stories, the Technologies page and real 404s.
- **Current release:**
  - Release `c74f5f0` (#30). Main CI: 38427217116. CD run: 38428073637.
  - Running identity: `sha256:594c7e769e21e78f9955e6942b52f2940bec0dc74e7c3f74c9f93b7e2e30d31b`, React/PortfolioPublicV1.
  - Content revision: `b60f12d3cc19aa48`.
  - LAN and public PortfolioPublicV1 acceptance pass, including the served content revision.
- **Product as built:**
  - React Router 8 framework mode with `ssr:false` + prerender, Tailwind 4 and TanStack Query, served by an ASP.NET Core host.
  - File-only runtime: no database, Redis, accounts or migrations.
  - Content is authored in `Content/Portfolio`, validated and exported by `Portfolio.ContentTool`, with Sharp image variants. Release manifest schema 3 carries the content revision.
  - Deployment is LocalSingleNode on the Portfolio node, plus Portfolio's own Cloudflare tunnel `portfolio-node-portfolio`, origin port 8085, connector `cloudflared-portfolio.service`.
- **Owner launch decision (2026-10-13):** all twelve stories are launched as drafts, to be improved later. Grumlebob uses the owner's wording: free offers automated with AutoHotkey, plus automatic billing and keeping the bookkeeping (regnskab) up to date. The DKK 500,000 / capacity statement is attributed to the owner.
- **Recovery and operations proof (P10.1), all on 2026-10-13:**

  | Step | Run | Result |
  | --- | --- | --- |
  | Rollback to `b7523f6` | CD 38420159225 | Success |
  | Roll-forward to `8ef6211` | CD 38420319542 | Deployed, LAN acceptance passed; public probe failed on a transient LAN DNS outage |
  | Deploy `c74f5f0` | CD 38428073637 | Success |
  | Web app restart | Maintenance 38428225949 | Success |
  | Connector restart | Maintenance 38428382576 | Success |
  | Reboot check | Maintenance 38428464324 | Success; node booted 16:12:37 UTC, with the connector active and the container up |
  | Acceptance after reboot | Maintenance 38428715478 | Success |

- **Release readiness and browser evidence (P7.4, P9.2):**
  - A fresh GitHub clone of main `1ad94fa` passed the full local gate and reproduced content revision `b60f12d3cc19aa48`.
  - The broad React E2E suite passed locally, including axe on four pages, themes, mobile, fragments and 404s.
  - Against the live site, every functional E2E assertion passes. The only failure is the final console check, caused by Cloudflare's injected script (owner decision 1 below).
  - Lighthouse on the live site:

    | Page / device | Performance | Accessibility | Best practices | SEO | LCP |
    | --- | --- | --- | --- | --- | --- |
    | `/` mobile | 87 | 100 | 92 | 100 | 3.4 s |
    | `/` desktop | 100 | 100 | 92 | 100 | 0.7 s |
    | `/projects/unlost` mobile | 88 | 100 | 92 | 100 | 3.2 s |
    | `/projects/unlost` desktop | 99 | 100 | 92 | 100 | 0.7 s |

    CLS is at most 0.009 and TBT is 0 ms everywhere.
- **Bugs found and fixed during verification:**
  - **#30, the hydration failure.** In Docker, Tailwind could not see `.gitignore`, so the prerender build emitted different CSS from the client build. Every page threw React #418, and readers' saved theme was lost on reload. Tailwind now scans only `app/`, and the Dockerfile fails the build unless exactly one app stylesheet exists.
  - **#27, OS-independent content revision.** Content files are now LF on every OS, so a Windows export reproduces the release revision.
  - **#29, readiness label.** The public readiness probe is now labelled "public" in logs.
- **Template fixes from this first clone:**
  - CF01 #216, CF02 #237, CF03 #241 and CF04 #240.
  - The stylesheet split: template #244.
  - The readiness label: template #245, merged as `466925c`.
  - Template #243 links the template plan to this ledger.
- **Handover docs:** `docs/HowToAddAProject.md` in Portfolio covers adding or updating a story, the validator rules, release, deploy, rollback and restarts. Private tools are in `Plans.local/Portfolio/Tools/`, with a README: the live-test sequence runner, the SVG arrowhead converter, a safe Cloudflare check and a public-setup lister.

### Remaining work, in order

1. **Land PR #32 (`fix/csp-nonce-favicon`), then verify it on the live site.** This is the owner's request for bot detection **and** high scores, without disabling Cloudflare's JavaScript detections.
   - What it does:
     - Every document response gets a fresh 128-bit `'nonce-…'` in `script-src` (`ReactFrontendHosting.WithScriptNonce`). Cloudflare [reads that nonce from the CSP header and puts it on the script it injects](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/). Our own inline scripts stay hash-authorized, and `unsafe-inline` is never added.
     - It adds a minimal SVG "JG" favicon plus a 16/32 px ICO fallback, both linked from `app/root.tsx`.
   - Evidence so far: 40 hosting tests (including the new nonce test), 28 React tests and lint all pass. The first gate and CI run on `c9e08b5` failed only because the required suite count was pinned at 173 passed. Head `5eeeb82` raises it to 174 in `Scripts/CI/validate-frontend-profiles.sh`, the audit rule and `docs/Test.md`. Re-run the full local gate on the current PR head and check its exact-head CI.
   - Steps:
     1. Full local gate PASS on the PR head.
     2. Exact-head `build-test-push` passes.
     3. `gh pr merge 32 --squash --delete-branch --match-head-commit <head>`.
     4. Main CI passes.
     5. `gh workflow run cd-localsinglenode.yml --ref main -f target_sha=<main sha>`, recording the run ID.
   - Then verify the live site:
     - The browser console is clean, with no CSP error from `/cdn-cgi/challenge-platform/`. Use the puppeteer probes in `Plans.local/Portfolio/Tools`, or run the live E2E: `RUN_E2E=1`, `E2E_BASE_URL=https://portfolio.jacobgrum.com`, `E2E_HEADLESS=1`, `dotnet test Portfolio.Test -c Release --no-build --filter "Category=ReactPublicBroad|Category=ReactPublicSmoke"`. Both should pass.
     - `/favicon.svg` and `/favicon.ico` return 200.
     - Lighthouse best practices rises from 92. Record the new scores here.
   - **If the console still shows a blocked script:** Cloudflare's script builds an iframe and runs an inline script inside it, which may not carry the nonce. In that case evaluate adding `'strict-dynamic'`. That would require putting the nonce on our own `<script>` tags at serve time, so check hydration carefully. Do not use `unsafe-inline`, and do not change zone settings.
   - Port the nonce part to the template only if the template also runs behind Cloudflare JavaScript detections. Otherwise record that it is not applicable.
2. **P6 story improvements (owner-led).** Every story is a launched draft. The project readiness ledger lists the inputs only the owner can give, such as role, dates, real captures and links. Each improvement is its own PR:
   - run `npm run content` and the full local gate;
   - merge after exact-head CI passes;
   - deploy with CD;
   - verify acceptance.

   Re-check `Plans.local/Portfolio/FactNotes/<slug>.md` before changing a story's claims.
3. **Optional operator clean-up** on the node, after the file-only switch: `/etc/portfolio/secrets.yml` and `/opt/portfolio-backups` are unused. Removing them is the operator's choice. Never prune volumes.

### Owner instructions and boundaries to keep

- **Unlost:** A* finds the same route as Dijkstra while exploring fewer edges. Never present it as picking a worse route.
- **Private data:** never publish real people, credentials or private data from source repositories (GeckoBot guide and requirements, JobHunt applicant records, KinoJoin's README test account, TraceBack's LAN addresses, Grumlebob's private folder). Examples stay invented and say so.
- **Template defects** found in Portfolio get a separate, gated template PR.
- **Repo variable** `LOCALSINGLENODE_SSH_MAIN_PC_CONNECTION` contains the node's LAN address. Never echo it in workflows or tracked files.
- **Cloudflare:** the owner approved reusing the existing jacobgrum.com API token for Portfolio's own resources (2026-10-13). Never touch the demo tunnel or its DNS.
- **Hard stops:** no sudo by the agent, no Windows/WSL node bootstrap, no guessed host values, no unscoped prune or `--volumes`, and never redispatch a run because a watcher stopped.

### Working setup for the next agent

- **Checkouts:** Portfolio is at `C:\Users\jgrum\Documents\Programming\Csharp\Portfolio`; the template is at `C:\Users\jgrum\Documents\Programming\Csharp\BlazorAutoApp`. On 2026-10-13 a stray `core.worktree` was removed from the template's `.git/config`, and the DocsD4 worktree's `.git` link was made relative so it works from Windows and WSL. Template `main` is checked out in the DocsD2 worktree, so branch from `origin/main`.
- **Local gate:** WSL `~/bin/repo-gate.sh <branch> [steps]`. Always run it in a login shell: `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -lc '...'`, because a non-login shell has no `dotnet`. Use `GATE_SRC`/`GATE_WORK` for another source; run only one gate per `GATE_WORK` at a time.
- **Node access:** SSH alias `portfolio-node`; use `/c/Windows/System32/OpenSSH/ssh.exe` from Git Bash.
- **Content rules:**
  - The SVG policy rejects `<marker>` and `<pattern>`, so draw arrowheads as polygons.
  - Alt text and captions are at most 300 characters.
  - Publication is `draft` or `published`.
- **Merge rule:** full local gate plus exact-head `build-test-push`, then `gh pr merge --squash --delete-branch --match-head-commit <sha>`. Docs-only PRs use `[skip ci]`. Stage explicit paths only.
- **Live verification:** `pwsh -NoProfile -File Scripts/Test-DeployedSite.ps1 -FrontendProfile React -AcceptanceProfile PortfolioPublicV1 -BaseUrl https://portfolio.jacobgrum.com -ExpectedContentRevision <revision>`. For the browser flow, set `RUN_E2E=1`, `E2E_BASE_URL`, `E2E_HEADLESS=1` and run `dotnet test Portfolio.Test -c Release --no-build --filter "Category=ReactPublicBroad|Category=ReactPublicSmoke"`. For Lighthouse, use `Scripts/Testing/BrowserTools` with `CHROME_PATH` set to Playwright's Chromium.

### Resume prompt for a fresh chat

> Continue Portfolio delivery: run `/goal Plans/PortfolioStudioDeliveryGoal.md`. Work in the Portfolio checkout (Grumlebob/Portfolio). Read AGENTS.md, then Plans/Support/PortfolioStudio/Progress.md § Current checkpoint, and follow "Remaining work, in order". Before acting, recheck `git status`, open PRs in both repositories, and the last CD and maintenance runs. Live operations on the Portfolio node and its own Cloudflare publication are authorized (Release and operator handoff record). Private notes: Plans.local/Portfolio/ and WSL ~/.local/share/portfolio-public/.

- Destination: [Grumlebob/Portfolio](https://github.com/Grumlebob/Portfolio), public, seeded at `59de26c4c594d59a421801611b3ce0bd8e97bd8e` on 2026-10-12. Actions run on the Portfolio node's runner (`ci-portfolio`, `localsinglenode-portfolio`); the Dependabot auto-merge workflow was re-enabled on 2026-10-13 after the stack landed.
- Source: [Grumlebob/BlazorAutoAppTemplate](https://github.com/Grumlebob/BlazorAutoAppTemplate), pinned at `6db93ed33fad6564fac68149bcfffbf98e6724f1` (see P0.1 record).
- Owner authorization: see the Release and operator handoff record below. Implementation, own-PR merges after exact-head green CI, Portfolio repository operations and live LocalSingleNode setup/deployment on the intended Portfolio node are authorized.
- The upstream [React delivery goal](../../ReactFrontendDeliveryGoal.md) and [SR1–SR6 plan](../../ReactFrontendSingleRepository.md) are complete (status 2026-10-11, final handover #176). P0.1 below records the capabilities Portfolio depends on. That agent's demo deployment stays untouched.
- Product decisions: Portfolio naming, React frontend/C# backend, Books/Blazor removal, LocalSingleNode-only deployment and intended public URL `https://portfolio.jacobgrum.com/`.
- Owner refinement: generated **Techs** on every project, top-level `/technologies` with one categorized entry per published technology, and Template added as story **P6.13**, bringing the catalog to twelve. P6.12 remains catalog review.
- Grumlebob public facts supplied: free online offer automation for passive income, approximately DKK 500,000 profit in one year and membership at capacity because of concern about being caught. Attribute result/capacity to owner; remaining restricted context stays private.
- Recovered [Unlost source](https://github.com/Grumlebob/Unlost) imported at `715fc2eb3c784937ba32fce0a29f64dce8e6252b`; fetched `origin/main` matches. Large regional maps/archives and caches are excluded; `small.osm` is retained for existing tests. No source build/test was run. Retired Git history backup and local paths are recorded privately.
- Owner architecture preference: vertical slices organized around use cases. After P0–P3, VS1 completes ImprovedDb's content/C# API/React home-reader/prerender/hosting/acceptance together; later stories repeat that journey.
- Supplied local checkout/node details: ignored `Plans.local/Portfolio/OperatorIntent.md`. Transfer privately to the downstream checkout. GitHub authentication on the fresh native node is reported, not independently verified.
- VS0 merged: #10 `a962b6b`, #11 `c36203a`, #12 `8a82abb`, #13 `249c947`, each after its exact-head `build-test-push` and a full local gate.
- Public launch authorization: recorded 2026-10-12 (see Release and operator handoff record). It covers only Portfolio-owned resources on the intended Portfolio node.

After P0 import, this ledger in **Portfolio** is authoritative. Retain a link from the template plan to downstream execution evidence. Do not maintain two competing live ledgers or import the React agent's progress as Portfolio progress.

## Vertical slice ledger

These rows record visitor/operator completion across the existing packets. Keep the phase ledger as the detailed work inventory; a phase's partial backend/frontend work does not verify a product slice.

| Slice | Status | Owned packets / exact next action | End-to-end evidence |
| --- | --- | --- | --- |
| VS0 Independent product | Verified | #10–#13 merged | Exact-head CI and full local gates per PR description |
| VS1 Read ImprovedDb | Merged | #17 `601bf97` | Content compiler, API, Studio home/reader, prerender, hosting and acceptance |
| VS2 Additional stories | Launched (owner decision 2026-10-13) | #19, #20, #22, #23, #25 | All twelve published as drafts; improvements are owner-led (readiness ledger) |
| VS3 Runtime alignment | Merged and deployed | #18 `38b8d90` | File-only runtime; schema-3 release; LAN deploy below |
| VS4 Public launch | Verified | #21, #25, #30 | Public acceptance PASS; CD runs 38419323618, 38428073637 |
| VS5 Update/recover | Verified | P10 | Rollback, roll-forward, restarts, reboot and post-reboot acceptance (Current checkpoint) |

## Phase ledger

Statuses: `pending`, `ready`, `in progress`, `blocked`, `merged`, `verified`, `owner-deferred`. `merged` records code integration; a phase becomes `verified` only when its exit evidence is satisfied. A queued CI run is not green evidence.

| Phase | Status | PR / final head / merge / main CI | Evidence or exact next action |
| --- | --- | --- | --- |
| P0 Baseline/import | Verified | Seed `59de26c`; #1; #10 `a962b6b` | P0.1–P0.3 records below |
| P1 Portfolio naming | Merged | #13 `249c947` | Gate + exact-head CI |
| P2 React-only cleanup | Merged | #11 `c36203a` | Gate + exact-head CI |
| P3 Single-node cleanup | Merged | #12 `8a82abb` | Gate + exact-head CI |
| P4 Portfolio content/API | Merged | #17 `601bf97`, #18 `38b8d90` | Content tool, export bundle, file-only API; Books removed |
| P5 Studio home/reader | Merged | #17 `601bf97` | Home, Technologies, story reader, Techs, themes |
| P6 Twelve stories | Launched as drafts | #17, #19, #20, #22, #23, #25 | Owner decision 2026-10-13; improvements ongoing |
| P7 Rendering/release | Verified | #17, #18, #21, #27, #30 | Fresh-clone gate reproduces revision; E2E and Lighthouse evidence in Current checkpoint |
| P8 Native node/SSH | Verified | CD runs 38383250151, 38417034437, 38428073637 | Identity verified; LAN acceptance PASS; backup timer retired |
| P9 Public launch | Verified | #25 `8ef6211`, #30 `c74f5f0` | Public HTTPS acceptance PASS; own tunnel and DNS |
| P10 Recovery/handover | Verified (two owner decisions open) | #28, #29; maintenance runs 38428225949, 38428382576, 38428464324, 38428715478 | Authoring guide; template link #243; remaining work in Current checkpoint |

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

### P0.1 — Upstream baseline (done 2026-10-12)

- Selected upstream: `6db93ed33fad6564fac68149bcfffbf98e6724f1` (template `main`). It is code-identical to `4a2a1da5` (#210), whose main CI [38289646632](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38289646632) succeeded. Every later commit (#211–#214 and `6db93ed3`) changes Markdown only, which was verified with `git diff --name-only`. No open upstream PRs existed.
- Upstream React delivery: complete (SR1–SR6, #176). No upstream work is a dependency for Portfolio.

| Capability needed by Portfolio | Merged evidence at baseline | Classification |
| --- | --- | --- |
| React Router framework/SPA, Vite, Tailwind, TanStack Query | `BlazorAutoApp.React`: react-router 8.4.0, vite 8.3.4, tailwindcss 4.3.3, @tanstack/react-query 5.104.1, React 19.3.0, TypeScript 5.9.3; Node 24.21.0 / npm 12.2.0 engines | Available |
| Generated API contracts | openapi-typescript 7.13.0 + openapi-fetch 0.17.0; `npm run api:generate` / `api:check` through a metadata-only host | Available |
| Local HTTPS development | `npm run dev` (Vite + C# API), docs/FrontendProfiles.md | Available |
| C# production static hosting | React host profile; reserved-route, HEAD and 404 hosting tests | Available; Portfolio needs exact prerender hosting (P7.1) |
| Release/profile labels and manifests | `Scripts/Frontend/resolve_frontend_profile.py`, `Scripts/CI/write_release_manifest.py`, `frontend-profile.txt` | Available |
| CI validation/publishing | `.github/workflows/ci.yml` (`build-test-push`), self-hosted runner labels | Available; needs a Portfolio runner (B01) |
| LocalSingleNode setup state machine | `Deployment/LocalSingleNode/Scripts/setup-status.sh`, `AgentSetup.md`, `--ci-runner` capacity path | Available |
| Controller SSH | `Deployment/LocalSingleNode/Scripts/controller-ssh.py`, `ControllerSsh.md` | Available |
| Public Cloudflare setup | `Deployment/LocalSingleNode/PublicSetup.md`, `configure-public-deployment.py`, `Deployment/Common/Scripts/setup-public-tunnel.sh` | Available |

### P0.2 — Import into Grumlebob/Portfolio (done 2026-10-12)

- Destination check: public, empty (`size 0`, no refs), no variables, secrets, environments or runners, no branch protection. Actions were enabled, so the import **disabled Actions first** (`enabled:false`).
- Checkout: sibling `Portfolio` folder with full template history (540 commits). `origin` → Portfolio, `upstream` → template.
- Seed delta (`59de26c`, parent `6db93ed3`): `frontend-profile.txt` → `React`; `Deployment/Common/release.yml` → `ghcr.io/grumlebob/portfolio` / `portfolio-migrate`; LocalSingleNode `app_name: portfolio`, `/opt/portfolio`, `/opt/portfolio-backups`; LocalCluster `app_name: portfolio` (common CI still reads it until P3); `App:Name` / `App__Name` → `portfolio`. The tracked-profile CI test now expects `React`. Project paths are unchanged until P1.
- Local gate on Linux (WSL Ubuntu 24.04, .NET 10.0.303, Node 24.21.0, Docker 29.8.2), exact seed tree: `git diff --check`, restore, frontend profile/release unit tests, format, `validate-frontend-profiles.sh` (BlazorAuto 190 passed / 13 skipped; React passed), common release, cloud, observability, deployment audit, rendered templates, yamllint, shellcheck, actionlint, and all 24 CI script-test suites passed.
- The plans arrived with the import and are authoritative here. Private operator/source notes were copied into the ignored `Plans.local/Portfolio/`.
- Workflow inventory: every job runs on `[self-hosted, linux, x64, <label>]`, with fallbacks `localcluster-books` / `localsinglenode-books` when variables are unset. Portfolio has no runner, so nothing can execute. Enable Actions only after P8.2 sets `CI_RUNNER_LABEL` / `LOCALSINGLENODE_RUNNER_LABEL` for the Portfolio runner.

### P0.3 — Design/source handover (implemented 2026-10-12, #10)

- `docs/design/studio/` holds eight clean captures of the approved Studio mockup (home and ImprovedDb story; desktop and mobile; light and dark) plus a decision/token/provenance record. Gallery review controls, abandoned alternatives, server scripts and prototype code are excluded.
- The record lists the changes approved after the mockup that the captures don't show: the Technologies header link, the generated Techs section, and no breadcrumb requirement.
- Rights note: the captures contain third-party poster/portrait imagery displayed by ImprovedDb. They are a design reference only; published story media gets its own P6.1 review.
- Private source map: `Plans.local/Portfolio/ProjectSources.md` (copied in P0.2).

### P2 — React-only frontend (implemented 2026-10-12, #11)

- Removed the Blazor client, Razor components and account UI, the BlazorAuto build/image targets, Tailwind/Client npm tooling and the optional additional-frontend publication. MSBuild accepts only `React`.
- Test suite: 140 passed / 6 opt-in skips, every test run without a profile filter (replaces the inherited 190/13 and 182/13).
- Moved axe-core and Lighthouse into the test-only `Scripts/Testing/BrowserTools` package.
- Boundary: the shared resolver and LocalSingleNode deployment verifiers still recognise the `BlazorAuto` name and legacy schema-v1 manifests. P7.3 narrows them; P3 removed the additional-application instance.

### P3 — LocalSingleNode only (implemented 2026-10-12, #12)

- Moved to `Deployment/Common/Scripts`: the deployment audit (rebuilt from the inherited rules for retained files, 2,200 → 1,056 lines, plus a removed-files guard), `ci-docker-smoke.sh` and its lifecycle test (React-only), and the Ansible check-only test. CI capacity check is self-contained.
- Deleted `Deployment/LocalCluster`, `Deployment/Cloud`, their workflows, LocalCluster/Cloud-only Common roles and validators, the template fork guides, and the additional-application instance feature (which only existed to run the other frontend profile).
- Kept inherited compatibility names: `localcluster.ci.*` CI resource labels, the `/tmp/localcluster-deploy.lockdir` lock path and `--all-localcluster-runners`.
- Runner fallback labels are `ci-portfolio` and `localsinglenode-portfolio`.

### P1 — Portfolio naming (implemented 2026-10-12, #13)

- `Portfolio.sln`, `Portfolio/Portfolio.csproj`, `Portfolio.Core`, `Portfolio.Test`, `Portfolio.React` (`portfolio-react`); namespaces/assembly `Portfolio`; image labels `com.jacobgrum.portfolio.*`. Upstream `BlazorAutoAppTemplate` provenance links and historical `Plans/` paths are unchanged. Generated OpenAPI output needed no regeneration.

Do not leave `next action: continue implementation`. Name a command from the implemented runbook or a small task/file set, such as “P3.1: inventory CI references to the old audit path and record the keep/move/delete table.” Preserve somebody else's active claim; do not infer abandonment from elapsed time alone.

## Fresh-chat handoff

Use the master's [C1–C3 recommendations](../../PortfolioStudioImplementation.md#recommended-fresh-chat-checkpoints).

**Checkpoint (2026-10-13), final for the first session:** see § Current checkpoint for the live release, recovery evidence, remaining work, boundaries, setup and resume prompt. Fill this record when its verified boundary is reached; preserve earlier handoffs or link their PR descriptions. Commit stable handoff facts through the normal documentation process. Final merge/main evidence can be saved in the linked PR description without creating another evidence-only commit. Keep private facts in ignored notes and provide their location only.

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
| P6.1 ImprovedDb | Source rechecked at `bb7f3bf6`; private fact note | Merged draft (#17) | Live captures 2026-10-11 + 2 SVGs | Owner motivation | Published draft | Owner review |
| P6.2 KinoJoin | Source at `abf8a97`; fact note | Merged draft (#20) | 3 SVGs, invented names | Not claimed | Published draft | Owner review; team/role/dates need owner input |
| P6.3 TraceBack | Docs/source; fact note | Merged draft (#19) | 4 SVGs | Not claimed | Published draft | Owner review |
| P6.4 Unlost | Report + source `715fc2e`; fact note | Merged draft (#22) | 3 genuine report captures, OSM attribution | Pathfinding (report §10) | Published draft | Owner review; A* described as same route, fewer edges (owner instruction 2026-10-13) |
| P6.5 Ship Inspections | Source at `bde4b73`; fact note | Merged draft (#22) | 3 SVGs | Not claimed | Published draft | Owner review; real captures optional |
| P6.6 MiniTwit | Report/docs/workflows at `4c4a315`; fact note | Merged draft (#22) | 2 redrawn SVGs | From own commits | Published draft | Owner review |
| P6.7 BestBets | Exam/deck + repo `282805d`; fact note | Merged draft (#22) | 3 SVGs labelled design study | Neutral team | Published draft | Owner review |
| P6.8 Geospatial research | Report + repo `5bb1db5`; fact note | Merged draft (#23) | 4 genuine report figures, basemap/NYPD attribution | Report contribution statement | Published draft | Owner review |
| P6.9 GeckoBot | Private source `af54ad3`; fact note | Merged draft (#22) | 3 SVGs, invented data | Not claimed | Published draft | Owner review; no source link |
| P6.10 Grumlebob | Owner-approved facts + owner description 2026-10-13 | Short owner-worded draft | 1 generic SVG | Outcome owner-reported | Published (launch) | Owner may extend |
| P6.11 JobHunt | Private procedures `700c92f`; no applicant data | Merged draft (#23) | 2 SVGs, invented examples | Personal/assisted boundary | Published draft | Owner review; no source link |
| P6.13 Template | Public template `c1dfd76`; fact note | Merged draft (#23) | 1 SVG | Own template | Published draft | Owner review |

Launch set: all twelve stories, approved by the owner on 2026-10-13, to be improved after launch. Private evidence tables for every story are in the ignored `Plans.local/Portfolio/FactNotes/`. Initial launch does not close unfinished story packets.

Owner source update on 2026-10-11: `Grumlebob/GeckoBot` remains the sole active private source, with rename identity/history/privacy preserved; deleted MailDemo's complete history remains privately backed up. BestBets' preferred Exam/deck text now supplies final-design/prototype-limit evidence; selected figures still need visual/reuse review. Grumlebob uses only approved public explanation; restricted source inspection is unnecessary. Exact locations, backup evidence and publication boundaries remain in ignored `Plans.local/Portfolio/ProjectSources.md`.

Execution enhancement: D01–D14 resolve dependency/compiler/media/runtime/copy/technology/catalog choices. ImplementationCheckpoints subdivides technical packets/story slices; VisualProduction specifies twelve project figure sets. Grumlebob's public explanation is supplied. Unknown roles/dates may be omitted; reuse permission and native/human authorization remain scoped inputs. This is planning evidence, not completed product work. Planning PR/head/merge/main evidence belongs in the refinement's PR description.

## Decision and blocker records

Apply D01–D14 in ExecutionDecisions. Record implementation-specific choices such as seed SHA, relocated gate paths, actual command evidence, file-only service removals, configured origin, launch set and owner-approved deferrals. Do not reopen settled defaults merely because an older outline used “choose.”

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

```text
Blocker B01 / 2026-10-12:
Affected packet: every code PR (exact-head build-test-push) and P8.
Attempted: Portfolio has no Actions runner, and the intended Portfolio node did not answer ping or SSH from the controller on 2026-10-12.
Smallest missing input/action: native node bootstrap with the documented --ci-runner capacity path (P8.1/P8.2), run by the node agent; the operator runs its single root command.
Actor: native-node agent + operator.
Independent work that can proceed: local-gated stacked code PRs (P0.3-P3, VS1), content/media preparation, docs-only PRs.
One-step handoff issued and private note location: node-agent prompt in Plans.local/Portfolio/OperatorIntent.md ("First native handoff"); issued in the goal's morning handoff.
Response/evidence received: pending.
Exact resume action: verify the runner online with labels ci-portfolio/localsinglenode-portfolio, set Actions variables, enable Actions, then run CI on the oldest stacked PR.
```

```text
Decision D-EXEC-01 / 2026-10-12:
Affected packet: P1, P2, P3.
Decision and reason: execute P2 (Blazor removal) and P3 (target removal) before P1 (rename) so code that is deleted is never renamed. Each packet still lands as its own locally gated PR, merged in order.
Evidence/source or applicable owner instruction: plan dependency map only requires ordered, green integration.
Follow-up impact: PRs #11 → #12 → #13 are stacked.
```

```text
Decision D-EXEC-02 / 2026-10-12:
Affected packet: P2, P3, P7.3.
Decision and reason: P2 keeps the shared profile resolver and LocalSingleNode verifiers unchanged (they still recognise BlazorAuto/legacy manifests) because narrowing them cascades into deployment machinery. P3 removes the inherited additional-application instance; P7.3 narrows the resolver and acceptance pairs when PortfolioPublicV1 replaces ReactPublicV1.
Evidence/source or applicable owner instruction: no Portfolio build can produce a BlazorAuto release (MSBuild/Docker/CI are React-only).
Follow-up impact: P7.3 must remove BlazorAuto/schema-v1 acceptance from the resolver, verifiers, release validator and Test-DeployedSite.ps1.
```

```text
Decision D-EXEC-03 / 2026-10-12:
Affected packet: all, template.
Decision and reason: the owner asked (2026-10-12) to fix genuine template defects found by this first clone permanently upstream. Each one gets a separate template PR with its own gate and CI; Portfolio carries only its own fix.
Evidence/source or applicable owner instruction: owner chat instruction, 2026-10-12.
Follow-up impact: template PR #216 (clone-safe frontend-profile test and fork-guide profile step). The private clone-friction log is in Plans.local/Portfolio/CloneFrictionLog.md.
```

A node/operator handoff can pause its dependent packet while independent content work remains available. If a live autonomous goal exists, follow the goal tool's status rules; this ledger alone does not authorize changing goal status. Never mark a required blocked packet complete to advance the plan.

## Release and operator handoff record

Store public/sanitized evidence here. Keep node address/login, host/runner labels, provider resource IDs, secrets and runtime paths in the private note.

Operator authorization (recorded 2026-10-12, from the owner's goal instruction in the controller session): full authority for Portfolio delivery. This covers implementation, merging own PRs after exact-head green CI, Grumlebob/Portfolio repository operations, and live operations: LocalSingleNode setup and deployment of Portfolio on the owner-named Portfolio node (identity in private notes), plus its owned Cloudflare publication at `https://portfolio.jacobgrum.com`. Boundaries that still apply: no sudo by the agent, no Windows/WSL node bootstrap, no guessed host values, no secrets in tracked files or logs, no mutation of foreign resources or the upstream demo/Blazor deployment, and no fabricated content approval.

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
