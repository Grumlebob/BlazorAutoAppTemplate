# Better Lighthouse Scores

## Goal

Status: Pending

Find and execute further Lighthouse improvements only where the app can stay clean, modern, and non-destructive.

This plan is intentionally measurement-first. The current easy wins have already been taken:

- Static design demo pages do not load Blazor runtime scripts.
- Passkey JavaScript is local to passkey pages.
- The author bookcase no longer repeats hidden duplicate SVG books.
- The design demo pages now show their static render mode.

The next pass must avoid chasing fake scores through ugly code.

## Non-Destructive Rules

Status: Pending

- Do not disable or bypass Cloudflare security, bot detection, JavaScript detections, WAF, or challenge behavior.
- Do not change deployment, PostgreSQL, Redis, migrations, or LocalCluster behavior.
- Do not remove Identity, passkeys, visible E2E, or the Books template experience.
- Do not replace Interactive Auto globally with Interactive Server just to score better.
- Do not remove the render mode badge from the home page.
- Do not introduce JavaScript-heavy lazy boot code unless it is simpler than the current Blazor model, which is unlikely.
- Do not inline large CSS/JS into pages just to satisfy a single Lighthouse audit.
- Do not make static pages interactive again unless a real feature requires it.

## Current Local Measurements

Status: Completed

Local app:

```text
https://127.0.0.1:7186/health/ready -> Healthy
```

Fresh reports:

- `TestResults/Lighthouse/local-better-scores-baseline-20260528-115733`
- `TestResults/Lighthouse/local-better-scores-home-repeat-20260528-115951`
- `TestResults/Lighthouse/local-better-scores-home-authenticated-20260528-120004`

Baseline summary:

| Page | Profile | Performance | Accessibility | Best Practices | SEO | FCP | LCP | TBT | TTI | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | mobile | 60 | 100 | 100 | 100 | 1.3s | 7.1s | 680ms | 7.1s | 2,535 KiB |
| `/` | desktop | 83 | 100 | 100 | 100 | 0.5s | 1.9s | 10ms | 1.9s | 2,535 KiB |
| `/books/design-demos` | mobile | 98 | 100 | 100 | 100 | 1.8s | 1.8s | 90ms | 2.0s | 171 KiB |
| `/books/design-demos` | desktop | 100 | 100 | 100 | 100 | 0.4s | 0.4s | 0ms | 0.4s | 171 KiB |
| `/books/design-demos/cloth-hardback` | mobile | 100 | 100 | 100 | 100 | 1.1s | 1.1s | 20ms | 1.2s | 34 KiB |
| `/books/design-demos/cloth-hardback` | desktop | 98 | 100 | 100 | 100 | 0.3s | 0.4s | 0ms | 0.4s | 34 KiB |
| `/Account/Login` | mobile | 99 | 100 | 100 | 100 | 1.2s | 1.2s | 40ms | 1.3s | 24 KiB |
| `/Account/Login` | desktop | 100 | 100 | 100 | 100 | 0.3s | 0.3s | 0ms | 0.3s | 24 KiB |

Home repeat checks:

| Page | State | Profile | Performance | LCP | TBT | TTI | Payload |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `/` | anonymous repeat | mobile | 77 | 6.5s | 70ms | 6.5s | 2,535 KiB |
| `/` | authenticated user | mobile | 75 | 11.3s | 60ms | 11.3s | 2,536 KiB |

Interpretation:

- Static SSR pages are already effectively solved locally.
- Login is effectively solved locally.
- Home is the remaining meaningful target.
- Authenticated and anonymous home behave similarly, so the problem is not primarily database/user book fetching.
- Home payload is dominated by Interactive Auto WebAssembly/runtime assets.
- Home performance varies because Lighthouse waits for the Blazor runtime/hydration work even though the visible SSR content appears early.

## Current Bottleneck Classification

Status: Completed

### Home

Main findings:

- Total transfer is about `2.5 MiB`.
- Large resources are Blazor WebAssembly/runtime files:
  - `dotnet.native.*.wasm`
  - `System.Private.CoreLib.*.wasm`
  - framework assemblies
  - `BlazorAutoApp.Client.*.wasm`
- Lighthouse's LCP/TTI for home tracks Interactive Auto startup more than HTML paint.
- DOM size is fine after the finite bookcase change: around `239` elements anonymous and `248` authenticated.
- Root server response time is fine, normally single-digit milliseconds in these reports.
- Render-blocking CSS remains visible in audits, but the savings are small compared to runtime startup.

### Design Demo Pages

Main findings:

- The overview page still has a large static HTML document because it renders many SVG demos, but the score is already `98-100`.
- Detail pages are tiny and score `98-100`.
- These should remain static SSR.

### Login

Main findings:

- The account pages now avoid the Blazor runtime and only load passkey JS where needed.
- Scores are `99-100`.
- Do not spend time here unless a future account feature regresses the scores.

## Phase 1 - Lock Current Static Page Improvements

Status: Pending

Purpose:

Prevent accidental regression of the wins already achieved.

Work:

- Add lightweight tests or assertions that design demo pages do not emit `_framework/blazor.web` script tags.
- Add lightweight tests or assertions that login pages do not emit `_framework/blazor.web` but do emit `PasskeySubmit.*.razor.js` when a passkey component exists.
- Add an assertion that `/books/design-demos` shows:
  - Configured: `Static SSR`
  - Assigned: `Static`
  - Current: `Static`
  - Interactive: `no`
- Add an assertion that `/` still shows `Interactive Auto`.

Acceptance:

- No browser-only hack needed.
- Tests run as normal integration tests or existing E2E checks.
- Static pages stay static.
- Home remains Interactive Auto.

Expected Lighthouse impact:

- No direct score increase.
- Prevents future accidental score loss.

## Phase 2 - Home Page Static Shell Feasibility Spike

Status: Pending

Purpose:

Determine whether the home route can become a mostly static SSR page with small interactive islands, without ugly code or loss of template clarity.

Why this matters:

- Static pages score `98-100`.
- Home currently scores `60-77` mobile locally because Interactive Auto pulls the full Blazor WebAssembly runtime.
- The home page has static content that does not need hydration:
  - page heading
  - design demo link
  - author bookcase
  - unauthenticated login prompt
- The genuinely interactive pieces are narrower:
  - user bookcase loading/editing for authenticated users
  - create/edit/delete modal
  - render mode badge for the interactive island

Spike approach:

- Prototype a static SSR home shell on a temporary local change.
- Keep the public route `/` and `/books`.
- Keep the author bookcase visible and clickable.
- Try rendering only necessary children as `InteractiveAuto` islands:
  - user bookcase area
  - book modal host when query parameters require create/edit/view
  - render mode badge or a pair of badges that clearly shows page/static shell and island/Interactive Auto.
- Verify whether Blazor's script bootstrapping can stay clean when the root page is static but child components are interactive.
- Do not keep the prototype if it requires awkward global script conditions, duplicated routing, or brittle query parsing.

Acceptance for adopting:

- Anonymous home must not download the full WebAssembly runtime unless an interactive island is actually present.
- Authenticated home must still load and edit user books correctly.
- Author book details must still open correctly.
- Create, edit, delete, close, and navigation must pass visible E2E.
- The render mode badge must become clearer, not more confusing.
- Code must remain vertically sliced inside `Features/Books`.
- No forced full-page reload workaround for normal book interactions.

Expected Lighthouse impact:

- Anonymous home mobile should move closer to static pages, likely `90+` if the runtime is avoided.
- Authenticated home may still need Interactive Auto, but can improve if the static shell paints independently.

Risk:

- Medium. This is the only major remaining performance lever, but it touches render-mode architecture.

Decision gate:

- Execute only if the spike keeps code simpler or equally clear.
- Stop if it becomes framework fighting.

## Phase 3 - Make Book Modal Conditional On Query State

Status: Pending

Purpose:

Avoid paying for modal infrastructure on a normal home visit if no modal is requested.

Current behavior:

- `BookModalHost` is present on the home page even when no `bookMode`, `bookId`, or `authorBookId` query is active.

Work:

- Check if `BookModalHost` can be rendered only when the current URI contains modal query parameters.
- Keep client-side navigation behavior correct.
- Keep direct links to modal URLs working.
- Avoid duplicate URI parsing if `BookModalRouteState` already provides the right central API.

Acceptance:

- Normal `/` visit has less interactive component work.
- `/books?authorBookId=...&bookMode=view` still opens directly.
- `/books?bookMode=create` still opens directly for authenticated users.
- Back/close behavior remains correct.
- Visible E2E passes.

Expected Lighthouse impact:

- Small to medium.
- Mostly useful if Phase 2 static shell is adopted.

Risk:

- Low to medium.

## Phase 4 - Keep Static Design Demos Lean

Status: Pending

Purpose:

Preserve near-perfect design demo scores while keeping the demo catalog useful.

Possible work:

- Keep `content-visibility:auto` on each demo card.
- Add a simple server-rendered grouping or "first N plus details links" only if the design catalog grows enough to push mobile scores below `95`.
- Avoid client-side pagination because this page is intentionally static and currently scores well.

Acceptance:

- `/books/design-demos` stays static SSR.
- Mobile Lighthouse stays `95+`.
- Design review UX remains good.

Expected Lighthouse impact:

- Current score is already `98-100`; no urgent change.

Risk:

- Low if deferred until needed.

## Phase 5 - CSS Audit Pass

Status: Pending

Purpose:

Look for small clean CSS wins, but avoid overengineering.

Findings so far:

- Render-blocking CSS appears in Lighthouse.
- Estimated savings are usually around `60-150ms`.
- CSS transfer is small, roughly `8-9 KiB` across stylesheets.

Possible work:

- Review whether `BlazorAutoApp.styles.css` and `BlazorAutoApp.Client.*.bundle.scp.css` can be consolidated naturally by the existing build, if not, leave them alone.
- Review whether old scoped CSS remains for components that no longer exist.
- Keep Tailwind generated CSS verified by CI.

Non-goals:

- No manual critical CSS extraction.
- No large inline style blocks.
- No custom CSS bundler unless the repo already moves that way for other reasons.

Expected Lighthouse impact:

- Small.

Risk:

- Low.

## Phase 6 - WebAssembly Payload Review

Status: Pending

Purpose:

Confirm the Interactive Auto payload is as lean as it reasonably can be without changing the app's render-mode goal.

Work:

- Inspect published framework asset list and identify unusually large app-owned assemblies.
- Confirm trimming/linking remains enabled in publish.
- Check whether rarely used features are accidentally rooted in the client assembly.
- Consider .NET WebAssembly lazy loading only if it has a clean .NET 10 path and a clear app-owned assembly split.

Non-goals:

- Do not hand-tune the linker around fragile reflection assumptions.
- Do not remove Identity or Books functionality.
- Do not move everything to Interactive Server.

Expected Lighthouse impact:

- Potentially medium, but only if there is a clean assembly split.
- Likely less effective than Phase 2.

Risk:

- Medium.

## Phase 7 - Production Verification

Status: Pending

Purpose:

After any adopted improvement, verify against both local and production.

Local commands:

```powershell
.\RunLighthouse.ps1 `
  -BaseUrl https://127.0.0.1:7186 `
  -Paths "/", "/books/design-demos", "/books/design-demos/cloth-hardback", "/Account/Login" `
  -Profile both `
  -Label local-better-scores-after-change `
  -IgnoreCertificateErrors

.\RunLighthouse.ps1 `
  -BaseUrl https://127.0.0.1:7186 `
  -Paths "/" `
  -Profile mobile `
  -Label local-better-scores-after-change-authenticated `
  -IgnoreCertificateErrors `
  -AuthenticatedLocalUser
```

Production commands after deploy:

```powershell
.\RunLighthouse.ps1 `
  -BaseUrl https://shipinspection.jacobgrum.com `
  -Paths "/", "/books/design-demos", "/books/design-demos/cloth-hardback", "/Account/Login" `
  -Profile both `
  -Label production-better-scores-after-deploy
```

Notes:

- Production Best Practices may still be capped by Cloudflare challenge/security scripts.
- Do not disable Cloudflare safety features to improve that category.
- Compare production against production, not only local against local.

## Phase 8 - Validation Gate

Status: Pending

Run after any code change:

```powershell
npm --prefix .\BlazorAutoApp.Client run css:build
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
git diff --check
.\RunLocal.ps1 -NoBrowser -NoBuild -TimeoutSeconds 30
```

If render modes, routing, identity, or book modals change:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
$env:E2E_HEADLESS='0'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter FullyQualifiedName~E2E
```

## Recommended Execution Order

Status: Pending

1. Phase 1: lock current static-page and script-loading improvements with tests.
2. Phase 2: do the static home shell feasibility spike.
3. If Phase 2 is clean, continue with Phase 3 modal conditional rendering.
4. If Phase 2 is not clean, stop there and keep the current architecture.
5. Run Phase 6 WebAssembly payload review only after deciding whether the home route remains fully Interactive Auto.
6. Defer Phase 5 CSS work unless a quick stale CSS cleanup is found.
7. Re-measure locally and then on production after deploy.

## Done Criteria

Status: Pending

- No Cloudflare safety setting was disabled.
- No deployment/database/cache destructive change was made.
- Static SSR pages remain static.
- Home either improves cleanly or the plan explicitly documents why the clean architecture was not worth changing.
- Lighthouse reports are saved under `TestResults/Lighthouse`.
- Visible E2E passes for any routing/render-mode changes.
