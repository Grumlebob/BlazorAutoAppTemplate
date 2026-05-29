# Big Scores Plan

Status: In progress; deployed P0 verification completed, first optimization patch implemented locally

Date: 2026-05-28

Production URL: `https://shipinspection.jacobgrum.com/`

## Goal

Get the best practical Lighthouse, WebPageTest, PageSpeed Insights, Core Web Vitals, accessibility, best-practices, and SEO results for the deployed app without changing what the app is.

This plan is not a "make it static and bland" plan. The goal is a faster version of the same app:

- Keep the front page on Blazor Interactive Auto.
- Keep the scrolling bookcase experience.
- Keep the public home page visually rich.
- Keep Identity, passkeys, Redis, PostgreSQL, LocalCluster deployment, and Cloudflare.
- Keep static pages static where they already make sense, but do not convert the home page to a static-only landing page.
- Prefer measured fixes over score-chasing hacks.

## Hard Non-Goals

Status: Pending

- Do not remove Interactive Auto from the front page.
- Do not remove the scrolling bookcase.
- Do not replace the home page with a static marketing page.
- Do not hide real content from Lighthouse or users.
- Do not disable authentication, passkeys, Redis, PostgreSQL, migrations, or deployment checks.
- Do not cache authenticated HTML at Cloudflare or Caddy.
- Do not make destructive deployment, database, cache, or git changes.
- Do not weaken Cloudflare security just to make a synthetic score prettier unless a separate security decision explicitly accepts that tradeoff.
- Do not add fragile custom JavaScript boot hacks unless measurement proves they are safer and simpler than the current Blazor model.

## Measurement Philosophy

Status: Pending

Use several tools because each answers a different question:

- Lighthouse CLI is the repeatable local and production lab baseline.
- PageSpeed Insights is the public Google check that mixes Lighthouse lab data with Chrome UX Report field data when available.
- Chrome UX Report is the field-data source for real-user Core Web Vitals, if the site gets enough traffic.
- WebPageTest by Catchpoint is the deep waterfall, filmstrip, first-view/repeat-view, and geography/device diagnostic.
- Chrome DevTools Performance panel is the local trace tool for Blazor hydration, animation, long tasks, and rendering cost.
- Optional synthetic monitoring tools are useful after improvements land, so regressions are caught before they become normal.

Do not compare scores across tools as if they are identical. Compare trends inside each tool, and use the detailed diagnostics to decide what to fix.

## Tool Stack

Status: Pending

| Tool | Use | What to capture | Decision rule |
| --- | --- | --- | --- |
| Repo Lighthouse CLI through `RunLighthouse.ps1` | Repeatable baseline and before/after comparison | Mobile and desktop HTML/JSON reports for `/`, `/books/design-demos`, `/books/design-demos/cloth-hardback`, `/books?authorBookId=2&bookMode=view`, `/Account/Login` | Primary local regression signal |
| PageSpeed Insights | Public Google view of the deployed URL | Lab scores, field data if available, diagnostics | Use as the easy external validation link |
| Chrome UX Report | Real-user Core Web Vitals | P75 LCP, INP, CLS by origin or URL if available | Use only when traffic is enough for meaningful data |
| WebPageTest / Catchpoint | Deep production diagnosis | First view, repeat view, waterfall, filmstrip, video, CPU, request timings, bytes by resource type | Use for LCP, TTFB, cache, CDN, and visual progress debugging |
| Chrome DevTools Performance | Local code-level investigation | Main-thread trace, rendering, paint, long tasks, animation/compositing, Blazor startup | Use before changing complex UI/rendering code |
| GTmetrix | Secondary Lighthouse plus waterfall cross-check | Score, waterfall, Web Vitals, page weight | Use as a sanity check, not as the source of truth |
| DebugBear, SpeedCurve, or Catchpoint monitoring | Long-term monitoring | Scheduled Lighthouse/Web Vitals, budgets, alerts | Add only after the metric targets are stable |

Sources:

- WebPageTest by Catchpoint: `https://www.catchpoint.com/webpagetest`
- WebPageTest documentation: `https://docs.webpagetest.org/`
- PageSpeed Insights: `https://pagespeed.web.dev/`
- PageSpeed Insights API docs: `https://developers.google.com/speed/docs/insights/v5/about`
- Chrome UX Report: `https://developer.chrome.com/docs/crux`
- Lighthouse docs: `https://developer.chrome.com/docs/lighthouse`
- Chrome DevTools Performance panel: `https://developer.chrome.com/docs/devtools/performance`
- GTmetrix: `https://gtmetrix.com/`
- DebugBear: `https://www.debugbear.com/`
- SpeedCurve: `https://www.speedcurve.com/`

## Execution Log - 2026-05-28

Status: Completed for first pass; production verification after deploy remains pending.

### Direct Failures Fixed

Status: Implemented locally

1. `RunLighthouse.ps1` could not audit URLs containing `&`.
   - Symptom: `/books?authorBookId=2&bookMode=view` was split by Windows command handling, and `bookMode` was executed as a command.
   - Fix: the runner now calls the local Lighthouse CLI through `node` instead of `npm exec`.
   - Verification: `production-big-scores-query-smoke-20260528-230647` completed successfully for `/books?authorBookId=2&bookMode=view`.

2. `/books/author/ship` returned `404` in production.
   - Cause: the old pretty author URL was still used in plans, but the current app uses the query-modal route.
   - Fix: added `/books/author/{SeedKey}` as a compatibility route that resolves the author seed key and redirects into `/books?authorBookId=<id>&bookMode=view`.
   - Supporting fix: author-book API DTOs now expose `seedKey`.
   - Verification: focused tests passed, and local `HEAD /books/author/ship` returned `200` after rebuild.

3. Public page `HEAD` requests returned `404`.
   - Symptom: `curl -I https://shipinspection.jacobgrum.com/` returned `404` even though `GET /` returned `200`.
   - Fix: mapped explicit `HEAD` responses for the public benchmark pages.
   - Verification: local `HEAD /` and `HEAD /books/author/ship` returned `200`.
   - Production verification: pending deploy.

4. Client Node engine did not match the pinned Lighthouse requirement.
   - Symptom: `package.json` allowed Node `>=20`, but Lighthouse 13.3 requires Node `>=22.19`.
   - Fix: updated `BlazorAutoApp.Client/package.json` and `package-lock.json` to require Node `>=22.19`.
   - Verification: `npm --prefix .\BlazorAutoApp.Client install --package-lock-only` passed with 0 vulnerabilities.

Focused test command:

```powershell
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --filter "FullyQualifiedName~HeadRequestTests|FullyQualifiedName~GetAuthorBook"
```

Result:

```text
Passed: 6, Failed: 0, Skipped: 0
```

Full local headless fast E2E command:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
$env:E2E_HEADLESS='1'
$env:E2E_SLOW_MO_MS='0'
$env:E2E_NAVIGATION_TIMEOUT_MS='60000'
$env:E2E_ACTION_TIMEOUT_MS='30000'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~E2E"
```

Result:

```text
Passed: 6, Failed: 0, Skipped: 0, Duration: 21s
```

This includes the mobile regression `AuthorBookcase_AllAuthorBooksCanOpenOnMobile`, which verifies the author shelf is manually horizontally scrollable on a phone-sized viewport, disables the auto-scroll animation at phone width so finger swiping is native, and confirms every author book opens without a forced click.

### Corrected Production Lighthouse Baseline

Status: Completed

Report folder:

```text
TestResults/Lighthouse/production-big-scores-corrected-baseline-20260528-230715
```

| Page | Profile | Performance | Accessibility | Best Practices | SEO | FCP | LCP | TBT | CLS | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | mobile | 72 | 100 | 81 | 100 | 2.0s | 12.5s | 50ms | 0 | 2,554 KiB |
| `/` | desktop | 100 | 100 | 81 | 100 | 0.5s | 0.6s | 0ms | 0 | 2,552 KiB |
| `/books/design-demos` | mobile | 100 | 100 | 81 | 100 | 1.3s | 1.6s | 10ms | 0 | 36 KiB |
| `/books/design-demos` | desktop | 100 | 100 | 81 | 100 | 0.4s | 0.5s | 0ms | 0 | 36 KiB |
| `/books/design-demos/cloth-hardback` | mobile | 99 | 100 | 81 | 100 | 1.3s | 1.6s | 0ms | 0 | 32 KiB |
| `/books/design-demos/cloth-hardback` | desktop | 100 | 100 | 81 | 100 | 0.4s | 0.5s | 0ms | 0 | 31 KiB |
| `/books?authorBookId=2&bookMode=view` | mobile | 72 | 100 | 77 | 100 | 2.0s | 12.4s | 50ms | 0 | 2,553 KiB |
| `/books?authorBookId=2&bookMode=view` | desktop | 99 | 100 | 81 | 100 | 0.5s | 0.7s | 0ms | 0 | 2,553 KiB |
| `/Account/Login` | mobile | 100 | 100 | 81 | 100 | 1.3s | 1.6s | 0ms | 0 | 33 KiB |
| `/Account/Login` | desktop | 100 | 100 | 81 | 100 | 0.4s | 0.6s | 0ms | 0 | 33 KiB |

Interpretation:

- Static SSR pages and login are already effectively solved for performance.
- The only meaningful Lighthouse performance target is the Interactive Auto home/detail experience.
- Mobile home/detail are limited by Lighthouse LCP/TTI around 12.4-12.5s, while TBT is only about 50ms and CLS is 0.
- Desktop is already 99-100.
- Best Practices 77-81 is not app-owned in production; it is caused by Cloudflare challenge-platform scripts.

### Local Fixed Smoke

Status: Completed

Report folder:

```text
TestResults/Lighthouse/local-big-scores-fixed-smoke-20260528-231426
```

| Page | Profile | Performance | Accessibility | Best Practices | SEO | FCP | LCP | TBT | CLS | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | mobile | 75 | 100 | 100 | 100 | 1.5s | 11.6s | 60ms | 0 | 2,543 KiB |
| `/books/author/ship` | mobile | 75 | 100 | 100 | 100 | 1.5s | 13.7s | 60ms | 0 | 2,549 KiB |
| `/books?authorBookId=23&bookMode=view` | mobile | 75 | 100 | 100 | 100 | 1.5s | 13.7s | 50ms | 0 | 2,549 KiB |

Interpretation:

- Local app-owned Best Practices is 100, which confirms the production score loss is external.
- The compatibility route behaves like the canonical route.
- The Interactive Auto score cap appears before Cloudflare, so the next optimization work should focus on Blazor startup/LCP classification, not Cloudflare.

### Publish Asset Findings

Status: Completed

Publish folder:

```text
artifacts/publish-big-scores
```

Largest framework assets:

| Asset | Uncompressed | Brotli |
| --- | ---: | ---: |
| `dotnet.native.*.wasm` | 2,932 KiB | 954 KiB |
| `System.Private.CoreLib.*.wasm` | 1,612 KiB | 501 KiB |
| `System.Text.Json.*.wasm` | 401 KiB | 129 KiB |
| `System.Linq.Expressions.*.wasm` | 349 KiB | 111 KiB |
| `Microsoft.AspNetCore.Components.*.wasm` | 256 KiB | 92 KiB |
| `BlazorAutoApp.Client.*.wasm` | 202 KiB | about 60-70 KiB compressed |

Static asset summary:

- `.wasm`: about 7,062 KiB uncompressed.
- `.br`: about 2,602 KiB.
- `.gz`: about 3,159 KiB.
- CSS: about 50 KiB uncompressed total.

Interpretation:

- The interactive-page payload is mostly standard .NET WebAssembly runtime/framework cost.
- App-owned client assembly size is not the dominant transfer cost.
- Any large payload improvement must come from a clean assembly/lazy-loading split or from changing when WebAssembly is fetched, while still preserving Interactive Auto.

### Live Header Findings

Status: Completed

Production GET `/`:

- `200 OK`.
- `Content-Encoding: br`.
- `Cache-Control: no-cache, no-store, max-age=0`.
- Antiforgery cookie is emitted.
- `content-security-policy: frame-ancestors 'self'`.
- `x-frame-options: SAMEORIGIN`.
- `strict-transport-security: max-age=2592000`.

Production framework asset:

- `dotnet.native.*.wasm` returns `200 OK`.
- `Content-Encoding: br`.
- `Cache-Control: max-age=31536000, immutable`.
- `cf-cache-status: DYNAMIC` in this sample.

Production CSS asset:

- Fingerprinted `tailwind.*.css` returns `200 OK`.
- `Content-Encoding: br`.
- `Cache-Control: max-age=31536000, immutable`.
- `cf-cache-status: HIT`.

Interpretation:

- Compression and immutable cache headers are correct for app-owned static assets.
- HTML no-store and antiforgery cookie behavior should be investigated for anonymous public pages because Lighthouse reports bfcache failures tied to `no-store`; do not change this until Identity, antiforgery, and forms are checked.

### External Tool Attempts

Status: Partially blocked

PageSpeed Insights API:

- Attempted with `https://www.googleapis.com/pagespeedonline/v5/runPagespeed`.
- Result: blocked by Google quota for the unauthenticated/shared caller, with daily quota `0`.
- Follow-up: use the browser UI at `https://pagespeed.web.dev/` manually or add a project API key before automating.

WebPageTest:

- Attempted unauthenticated API call to `https://www.webpagetest.org/runtest.php`.
- Result: `403 Forbidden` from WebPageTest/Cloudflare.
- Follow-up: run manually in WebPageTest/Catchpoint UI, or configure an API key/account path that is allowed from this environment.

CrUX:

- Not available from this run.
- Follow-up: check through PageSpeed Insights UI/API with a key. Treat it as absent unless Google reports field data for the origin or URL.

## Measurement-Backed Follow-Up Backlog

Status: Pending

### P0 - Deploy And Verify The Direct Fixes

Status: Completed on 2026-05-29.

Result:

- `HEAD /` now returns `200 OK`.
- `HEAD /books/author/ship` now returns `200 OK`.
- `GET /books/author/ship` returns `302 Found` to `/books?authorBookId=2&bookMode=view`.
- Production query-string Lighthouse runs complete successfully.

Report folder:

```text
TestResults/Lighthouse/production-big-scores-direct-fixes-after-deploy-20260529-085906
```

| Page | Profile | Performance | Accessibility | Best Practices | SEO |
| --- | --- | ---: | ---: | ---: | ---: |
| `/` | mobile | 70 | 100 | 81 | 100 |
| `/books/author/ship` | mobile | 91 | 100 | 81 | 100 |
| `/books?authorBookId=2&bookMode=view` | mobile | 92 | 100 | 81 | 100 |

Read-only production mobile E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://shipinspection.jacobgrum.com'
$env:E2E_HEADLESS='1'
$env:E2E_SLOW_MO_MS='0'
$env:E2E_NAVIGATION_TIMEOUT_MS='60000'
$env:E2E_ACTION_TIMEOUT_MS='30000'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --filter "FullyQualifiedName~AuthorBookcase_AllAuthorBooksCanOpenOnMobile"
```

Result:

```text
Passed: 1, Failed: 0, Skipped: 0
```

Work:

- Deploy the current branch.
- Verify production:

  ```powershell
  curl.exe -I https://shipinspection.jacobgrum.com/
  curl.exe -I https://shipinspection.jacobgrum.com/books/author/ship
  ```

- Re-run:

  ```powershell
  .\RunLighthouse.ps1 `
    -BaseUrl https://shipinspection.jacobgrum.com `
    -Paths "/", "/books/author/ship", "/books?authorBookId=2&bookMode=view" `
    -Profile mobile `
    -Label production-big-scores-direct-fixes-after-deploy
  ```

Acceptance:

- `HEAD /` is no longer `404`.
- `/books/author/ship` is no longer `404`.
- Query-string Lighthouse runs stay reliable.

### P1 - Investigate Anonymous HTML No-Store And Antiforgery Cookie

Status: Investigated; no code change yet.

2026-05-29 findings:

- Production anonymous `/`, `/books/design-demos`, and `/Account/Login` all emit the app antiforgery cookie and `Cache-Control: no-store` style headers.
- Static design-demo pages still pass Lighthouse bfcache, because they do not load the interactive Blazor runtime or open the Blazor WebSocket.
- Interactive Auto pages fail bfcache for the expected combination of WebSocket plus main-resource `no-store`.
- Account/login bfcache remains constrained by account-page security behavior and WebAuthentication/passkey support.
- Do not remove or globally weaken antiforgery until a narrower framework-supported option is proven safe for Identity, passkeys, and authenticated book mutations.

Why:

- Production GET `/` emits `Cache-Control: no-cache, no-store, max-age=0` and an antiforgery cookie.
- Lighthouse reports bfcache failures partly because the main resource has `no-store`.
- The home page has no obvious anonymous form submission, but Identity and modal flows must not be weakened.

Work:

- Identify exactly which component or middleware causes antiforgery token generation on `/`.
- Check whether public anonymous pages can avoid antiforgery cookie creation without breaking account pages, forms, or authenticated book mutations.
- If safe, scope antiforgery/no-store behavior to endpoints/components that need it.
- If not safe, document the bfcache limitation as an accepted security/framework cost.

Acceptance:

- Anonymous home either stops emitting unnecessary antiforgery/no-store headers, or the reason is documented with tests.
- Account/login/passkey and authenticated CRUD still pass.

Expected score impact:

- Potentially small to medium for Best Practices/bfcache and repeat visits.
- Do not expect this alone to solve the 12s Lighthouse LCP/TTI issue.

### P1 - Trace The Interactive Auto LCP/TTI Plateau

Status: Investigated with Lighthouse JSON; DevTools/WebPageTest filmstrip still pending.

2026-05-29 findings from `production-big-scores-after-deploy-full-baseline-20260529-090002`:

- Home mobile simulated Lighthouse LCP/TTI: about `12.7s`.
- Home observed trace LCP: about `1.6s`.
- Home observed last visual change: about `1.8s`.
- Detail mobile shows the same pattern: simulated LCP/TTI about `12.5s`, observed LCP about `1.6s`.
- TBT is only about `50ms`, CLS is `0`, and server response is fast.
- Current interpretation: the poor mobile performance score is mostly Lighthouse Lantern modeling the Interactive Auto WebAssembly dependency path, not the first viewport being visually blank for 12 seconds.

Why:

- Mobile home/detail LCP and TTI are both around 12.4-12.5s.
- TBT is only about 50ms and CLS is 0.
- Lighthouse LCP breakdown points to visible text/SVG rendering much earlier than the final LCP number, so this needs a trace-level explanation before code changes.

Work:

- Open the Lighthouse trace for `home-mobile.report.json`.
- Compare screenshot filmstrip, LCP event, TTI, and WebAssembly fetch/compile/initialize timing.
- Use Chrome DevTools Performance against local `/`.
- Confirm whether Lighthouse is effectively waiting on Blazor Auto/WebAssembly readiness rather than actual visual completeness.
- If visual completion is early, use WebPageTest filmstrip after manual/account access to validate real user perception.

Acceptance:

- We know whether the 12s metric is a true visual LCP problem or a Blazor Auto startup/accounting problem.
- Any optimization has a specific trace target.

Expected score impact:

- High if a real delayed LCP element is found.
- Limited if this is mostly expected Interactive Auto WebAssembly startup under Lighthouse throttling.

### P1 - WebAssembly Payload Dependency Review

Status: In progress; publish asset review refreshed after CSS cleanup.

2026-05-29 publish folder:

```text
artifacts/publish-big-scores-after-css-cleanup
```

Largest WebAssembly assets remain framework/runtime dominated:

| Asset | Uncompressed |
| --- | ---: |
| `dotnet.native.*.wasm` | 2,932 KiB |
| `System.Private.CoreLib.*.wasm` | 1,612 KiB |
| `System.Text.Json.*.wasm` | 401 KiB |
| `System.Linq.Expressions.*.wasm` | 349 KiB |
| `Microsoft.AspNetCore.Components.*.wasm` | 256 KiB |
| `BlazorAutoApp.Client.*.wasm` | 201 KiB |

Current conclusion:

- App-owned client payload is not the dominant transfer cost.
- A meaningful payload win probably requires a clean lazy-loading split or a framework-supported change to when Auto downloads WebAssembly.
- Do not chase small app-code edits expecting them to move the 2.5 MiB Interactive Auto transfer meaningfully.

Why:

- Interactive pages transfer about 2.55 MiB.
- Largest payload is standard runtime/framework, but `System.Linq.Expressions`, `System.ComponentModel.TypeConverter`, and similar assemblies should be checked for avoidable roots.

Work:

- Inspect app-owned client assembly dependencies.
- Identify whether validation, reflection, JSON options, or editor code roots large assemblies on home.
- Evaluate clean .NET-supported lazy loading only if rarely used book editor/modal code can be split without framework fighting.
- Avoid brittle linker descriptor tricks.

Acceptance:

- Either reduce app-owned/client-rooted payload measurably, or document why the remaining payload is expected.

Expected score impact:

- Medium only if a clean dependency split exists.

### P2 - Render-Blocking CSS Cleanup

Status: Implemented locally; pending deploy and production re-measure.

2026-05-29 change:

- Moved reconnect modal behavior styles from scoped CSS into `BlazorAutoApp.Client/Styles/input.css` under a Tailwind component layer.
- Moved reconnect modal visual primitives into Tailwind utility classes in `ReconnectModal.razor`.
- Removed the `BlazorAutoApp.styles.css` link from the document shell.
- Deleted `ReconnectModal.razor.css`.
- Added integration tests that static/account pages do not load `blazor.web.js`, the home page still loads Interactive Auto, and public pages no longer reference the removed scoped CSS bundle.

Local Lighthouse after change:

```text
TestResults/Lighthouse/local-big-scores-tailwind-css-cleanup-20260529-091905
```

| Page | Profile | Performance | Accessibility | Best Practices | SEO | Render-blocking CSS |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `/` | mobile | 75 | 100 | 100 | 100 | `app.css`, `tailwind.css` |
| `/books/design-demos` | mobile | 100 | 100 | 100 | 100 | `app.css`, `tailwind.css` |
| `/books?authorBookId=2&bookMode=view` | mobile | 75 | 100 | 100 | 100 | `app.css`, `tailwind.css` |

Validation:

- `npm --prefix .\BlazorAutoApp.Client run css:build` passed.
- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore` passed.
- `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~RenderModeHtmlTests|FullyQualifiedName~HeadRequestTests"` passed: `8` tests.
- Local headless fast E2E passed: `6` tests.
- Release test suite passed: `94` passed, `6` skipped, `100` total.

Why:

- Lighthouse estimates about 450ms render-blocking savings on interactive pages.
- CSS bytes are small, so the risk of overengineering is real.

Work:

- Check whether the four CSS files can be naturally reduced or reordered.
- Remove stale scoped CSS if any exists.
- Avoid manual critical CSS unless trace data shows a real LCP win.

Acceptance:

- CSS remains maintainable.
- Any change is backed by Lighthouse before/after.

Expected score impact:

- Small.

### P2 - Cloudflare Best Practices Decision

Why:

- Production Best Practices is 77-81 due to `/cdn-cgi/challenge-platform/scripts/jsd/main.js`.
- Local Best Practices is 100.

Work:

- Decide whether score purity is worth changing Cloudflare JavaScript Detections/Bot Fight/challenge settings.
- If security settings stay as-is, record the score loss as an accepted external artifact.

Acceptance:

- The plan does not keep chasing app code for a Cloudflare-owned warning.

### P2 - Add Optional External Tool Automation

Status: Blocked until credentials/account path are available.

2026-05-29 external tool attempts:

- PageSpeed Insights API returned `429 Too Many Requests` with default unauthenticated quota `0`.
- Chrome UX Report API returned `403 Permission Denied` because it requires an API key or other caller identity.
- WebPageTest API returned `403 Forbidden` from Cloudflare for this IP/session.
- Manual browser UI runs or configured API keys are required before these can become repeatable automated artifacts.

Work:

- Add optional `RunPageSpeed.ps1` only if an API key is available.
- Add optional WebPageTest/Catchpoint runner only if an API key/account path is available.
- Keep API keys out of git.

Acceptance:

- Manual runs remain documented.
- Automated runs are repeatable when credentials exist.

## Baseline Pass

Status: Completed for Lighthouse production after deploy; PSI/WebPageTest still blocked or manual.

Production Lighthouse folder:

```text
TestResults/Lighthouse/production-big-scores-after-deploy-full-baseline-20260529-090002
```

| Page | Profile | Performance | Accessibility | Best Practices | SEO | FCP | LCP | TBT | CLS | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | mobile | 72 | 100 | 81 | 100 | 2.0s | 12.7s | 50ms | 0 | 2,553 KiB |
| `/` | desktop | 99 | 100 | 81 | 100 | 0.3s | 0.4s | 0ms | 0 | 2,553 KiB |
| `/books/design-demos` | mobile | 100 | 100 | 81 | 100 | 1.3s | 1.6s | 20ms | 0 | 36 KiB |
| `/books/design-demos` | desktop | 100 | 100 | 81 | 100 | 0.4s | 0.5s | 0ms | 0 | 36 KiB |
| `/books/design-demos/cloth-hardback` | mobile | 99 | 100 | 77 | 100 | 1.3s | 1.6s | 10ms | 0 | 32 KiB |
| `/books/design-demos/cloth-hardback` | desktop | 100 | 100 | 81 | 100 | 0.4s | 0.5s | 0ms | 0 | 31 KiB |
| `/books?authorBookId=2&bookMode=view` | mobile | 72 | 100 | 81 | 100 | 2.0s | 12.5s | 50ms | 0 | 2,554 KiB |
| `/books?authorBookId=2&bookMode=view` | desktop | 99 | 100 | 81 | 100 | 0.6s | 0.8s | 0ms | 0 | 2,554 KiB |
| `/Account/Login` | mobile | 99 | 100 | 81 | 100 | 1.4s | 1.8s | 0ms | 0 | 33 KiB |
| `/Account/Login` | desktop | 100 | 100 | 81 | 100 | 0.4s | 0.6s | 0ms | 0 | 33 KiB |

Purpose:

Establish a clean deployed baseline after the current deployment, without relying on interrupted or partial runs.

Local command:

```powershell
.\RunLighthouse.ps1 `
  -BaseUrl https://127.0.0.1:7186 `
  -Paths "/", "/books/design-demos", "/books/design-demos/cloth-hardback", "/books?authorBookId=23&bookMode=view", "/Account/Login" `
  -Profile both `
  -Label local-big-scores-baseline `
  -IgnoreCertificateErrors
```

Production command:

```powershell
.\RunLighthouse.ps1 `
  -BaseUrl https://shipinspection.jacobgrum.com `
  -Paths "/", "/books/design-demos", "/books/design-demos/cloth-hardback", "/books?authorBookId=2&bookMode=view", "/Account/Login" `
  -Profile both `
  -Label production-big-scores-baseline
```

WebPageTest setup:

- Test from at least one nearby European location and one US location.
- Run at least 3 test runs per page, preferably 5 for the home page.
- Capture first view and repeat view.
- Use mobile and desktop profiles.
- Save the share links in this plan after each run.
- Focus on visual progress, LCP element, request waterfall, compression, cacheability, TTFB, and large framework assets.

PageSpeed Insights setup:

- Run `/` and `/Account/Login` first.
- Add `/books/design-demos` and `/books/design-demos/cloth-hardback` after the home page baseline is clear.
- Record whether field data is available. If no CrUX data exists yet, treat PSI as lab-only.

Acceptance:

- Every baseline report is saved under `TestResults/Lighthouse`.
- WebPageTest share links are recorded in this file or a follow-up measurement log.
- PSI screenshots or JSON/API output are recorded.
- Any Cloudflare-injected diagnostics are separated from app-owned findings.

## Phase 1 - Preserve Current Wins With Tests

Status: Pending

Purpose:

Avoid regressing the pages that already should score very high.

Work:

- Add integration or E2E assertions that static design demo pages do not emit unnecessary Blazor runtime script tags.
- Add assertions that account pages avoid the Blazor runtime unless a component truly needs it.
- Add assertions that `/` remains Interactive Auto.
- Add assertions that `/books/design-demos` and detail demo pages remain static SSR.
- Keep the render mode badge meaningful so future render-mode changes are visible.

Expected score impact:

- No direct score gain.
- Prevents accidental future loss.

Acceptance:

- Tests run in the normal test suite or a clearly named E2E filter.
- Static pages stay static.
- Home stays Interactive Auto.

## Phase 2 - Front Page Interactive Auto Payload Review

Status: Pending

Purpose:

Keep the home page Interactive Auto, but reduce the cost paid by the browser.

Work:

- Inspect published assets sorted by transfer size and decoded size.
- Confirm Release publish uses trimming and compression as expected.
- Confirm invariant globalization remains intentional and documented.
- Identify any app-owned client assemblies or packages that are rooted on home but only used elsewhere.
- Check whether a clean .NET-supported WebAssembly lazy loading split exists for rarely used book editing or demo code.
- Review whether modal/editor code is loaded or initialized on normal `/` visits when no modal query is active.
- Keep changes inside established feature slices.

Non-goals:

- Do not switch home to static SSR.
- Do not switch home globally to Interactive Server just to score better.
- Do not hand-tune linker behavior around fragile reflection assumptions.

Expected score impact:

- Medium if unnecessary client code is rooted.
- Small if the remaining payload is mostly unavoidable Blazor WebAssembly runtime.

Acceptance:

- App-owned payload reduction is measured in publish output and Lighthouse/WebPageTest.
- Home remains Interactive Auto.
- Book create, edit, delete, view, and auth flows still pass E2E.

## Phase 3 - Bookcase Rendering And Animation Performance

Status: Pending

Purpose:

Keep the scrolling bookcase, but make it cheap for layout, paint, and compositing.

Work:

- Use Chrome DevTools Performance and WebPageTest filmstrip to confirm what the bookcase costs during first paint, hydration, and scrolling animation.
- Verify the animation uses compositor-friendly transforms instead of properties that trigger layout or paint every frame.
- Keep stable dimensions for shelves, books, hover states, and modal links.
- Keep `content-visibility` and containment where it helps offscreen rendering without breaking layout.
- Remove repeated hidden DOM or SVG duplication if any still exists.
- Memoize or precompute book cover geometry if traces show repeated expensive calculations.
- Keep `prefers-reduced-motion` behavior correct without turning off the normal scrolling bookcase for everyone.
- Check mobile viewport rendering separately from desktop.

Non-goals:

- Do not remove the scrolling effect.
- Do not reduce the bookcase to a static image.
- Do not hide most books from the DOM unless the visible behavior and accessibility remain correct.

Expected score impact:

- Medium for mobile LCP/TBT if rendering cost is currently significant.
- Low if Lighthouse is mostly blocked on Blazor runtime startup.

Acceptance:

- No CLS regression.
- No non-composited animation warning.
- Visible E2E and visual regression checks pass.
- WebPageTest filmstrip still shows the intended rich first viewport.

## Phase 4 - LCP Improvement Without Changing The Design

Status: Pending

Purpose:

Make the current first viewport appear faster without replacing it.

Work:

- Identify the actual LCP element for home in Lighthouse, PSI, DevTools, and WebPageTest.
- Confirm server-rendered HTML contains enough first-viewport content for early paint.
- Check whether any render-blocking CSS can be reduced safely.
- Avoid manual critical CSS extraction unless the savings are large and the maintenance cost is low.
- Keep CSS files small and cacheable.
- Verify no redirect, cookie, Cloudflare, or Caddy behavior delays the document response.
- Keep fonts system-based unless a real design need justifies web font cost.
- Preload only assets that consistently help the measured LCP path.

Expected score impact:

- Medium if LCP is a visible bookcase element delayed by CSS/rendering.
- Small if LCP tracks Blazor hydration rather than visual paint.

Acceptance:

- Home LCP improves in at least two independent tools or repeated Lighthouse runs.
- Visual design is unchanged.
- CSS remains understandable.

## Phase 5 - Total Blocking Time And INP Readiness

Status: Pending

Purpose:

Reduce main-thread pressure during startup and interaction.

Work:

- Use DevTools to find long tasks during initial home load.
- Separate Blazor runtime startup cost from app component work.
- Review expensive lifecycle methods in bookcase, modal host, cover rendering, and render-mode diagnostics.
- Render modal/editor infrastructure conditionally when route/query state actually needs it, if this reduces startup work without harming direct links.
- Avoid broad JavaScript rewrites.
- Add a small Web Vitals/RUM endpoint only if privacy, noise, and storage are handled clearly.

Expected score impact:

- Medium for Lighthouse mobile if app-owned long tasks exist.
- Long-term value for INP once real-user data exists.

Acceptance:

- TBT does not regress.
- Direct modal URLs still work.
- Back/close navigation remains correct.
- E2E covers create/edit/view/delete and logged-out states.

## Phase 6 - Delivery, Compression, Caching, And CDN

Status: Pending

Purpose:

Make sure the deployed site delivers the existing app as efficiently as possible.

Work:

- Verify Brotli and gzip are active for framework, CSS, JS, and HTML where appropriate.
- Verify fingerprinted assets have long-lived immutable cache headers.
- Verify HTML is not cached as immutable public content.
- Verify Cloudflare caches fingerprinted static assets and respects origin cache headers.
- Verify Caddy serves precompressed assets when available.
- Check HTTP/2 and HTTP/3 behavior from the public domain.
- Check TTFB in WebPageTest by geography.
- Check whether Cloudflare challenge scripts are affecting only Lighthouse best-practices score or also real loading performance.
- Keep security headers strong, including HSTS where appropriate.

Non-goals:

- Do not cache authenticated pages incorrectly.
- Do not disable Cloudflare protections just to get Best Practices 100 unless that becomes a separate explicit security decision.

Expected score impact:

- Medium if compression or CDN caching is wrong.
- Low if current cache headers are already clean.

Acceptance:

- WebPageTest repeat view is materially better than first view for static/framework assets.
- Lighthouse no longer reports avoidable cache/compression findings for app-owned assets.
- Cloudflare findings are documented separately from app-owned findings.

## Phase 7 - Accessibility, Best Practices, SEO, And Standards

Status: Pending

Purpose:

Keep non-performance categories at or near 100 without gaming them.

Work:

- Keep keyboard navigation, focus order, modal focus behavior, accessible names, and contrast covered by tests or manual checks.
- Confirm all buttons and icon-only controls have accessible names.
- Confirm pages have stable titles and descriptions.
- Add Open Graph and structured metadata only where it improves real sharing/search behavior.
- Review app-owned console warnings and browser deprecations.
- Review Content Security Policy feasibility for Blazor, passkeys, Cloudflare, and inline framework requirements.
- Keep `robots.txt`, canonical URLs, and status codes clean.
- Keep form inputs named and autocomplete-friendly where appropriate.

Known issue class:

- Cloudflare challenge or bot-detection scripts can reduce Lighthouse Best Practices through third-party deprecation warnings. Classify this separately from app code. If absolute score purity is required, evaluate a Cloudflare configuration decision separately with a clear security tradeoff.

Expected score impact:

- High only if a current app-owned standards issue exists.
- Otherwise this preserves 100s.

Acceptance:

- Accessibility remains 100 in Lighthouse and manual keyboard checks.
- SEO remains 100 in Lighthouse.
- App-owned Best Practices findings are fixed or explicitly deferred.

## Phase 8 - WebPageTest Deep-Dive Procedure

Status: Pending

Run this after each meaningful deploy.

Pages:

- `/`
- `/books/design-demos`
- `/books/design-demos/cloth-hardback`
- `/books?authorBookId=2&bookMode=view`
- `/books/author/ship` as a compatibility-route smoke check after deploy
- `/Account/Login`

Test matrix:

- Mobile first view, 5 runs, median result.
- Mobile repeat view, 5 runs, median result.
- Desktop first view, 3 runs.
- Desktop repeat view, 3 runs.
- Nearby Europe location.
- One distant location, such as US East or US West.

Record:

- Test URL/share link.
- Location and browser/device profile.
- First Byte.
- Start Render.
- FCP.
- LCP and LCP element.
- Speed Index.
- Total Blocking Time or equivalent main-thread signal.
- CLS.
- Total bytes.
- Requests by type.
- Largest resources.
- Cache hit/miss behavior on repeat view.
- Visual filmstrip notes.

Decision rules:

- If first byte is high across regions, inspect origin, Caddy, Cloudflare, and database dependencies.
- If repeat view is not much faster, inspect cache headers and Cloudflare caching.
- If filmstrip is blank while HTML is downloaded, inspect render-blocking CSS or first-viewport markup.
- If LCP is late but visual content appears early, inspect Lighthouse/WebPageTest LCP element classification.
- If CPU dominates, use DevTools and Blazor component profiling before changing infrastructure.

## Phase 9 - PageSpeed Insights And CrUX Procedure

Status: Pending

Purpose:

Use Google's public perspective and real-user data when available.

Work:

- Run PageSpeed Insights for the production home page after each deploy.
- Save mobile and desktop results.
- Note whether origin-level or URL-level field data exists.
- If CrUX data exists, track P75 LCP, INP, and CLS.
- If CrUX data does not exist yet, do not pretend PSI lab data is field data.
- Consider PageSpeed Insights API automation only after manual runs prove useful.

Targets:

- CLS: `0` or as close as practical.
- INP: Good in field data when available.
- LCP: Move toward the good threshold while preserving the current experience.
- Field data should matter more than synthetic score variance once enough traffic exists.

## Phase 10 - Budgets And Regression Gates

Status: Pending

Purpose:

Make performance improvements stick.

Initial budgets:

- Home page CLS must stay `0` in Lighthouse runs.
- Static pages should stay near `95-100` performance on mobile.
- Login should stay near `95-100` performance on mobile.
- Home mobile performance should improve from the measured production baseline without losing Interactive Auto.
- App-owned transfer size should not grow without a written reason.
- App-owned Lighthouse Best Practices findings should stay at `100`; Cloudflare findings are tracked separately.

CI approach:

- Start with report generation and trend review.
- Add soft budget warnings before hard failures.
- Use hard failures only for stable, app-owned regressions such as large payload jumps, CLS regressions, missing SEO metadata, or accidental Blazor runtime on static pages.

Acceptance:

- A new report folder exists for every optimization pass.
- The plan records before/after numbers, not just conclusions.
- CI does not fail randomly because of normal Lighthouse network variance.

## Phase 11 - Execution Order

Status: Pending

1. Capture a clean production baseline with Lighthouse, PSI, and WebPageTest.
2. Lock existing static-page wins with tests.
3. Inspect home Interactive Auto payload and published asset sizes.
4. Profile the bookcase and home startup in DevTools.
5. Apply the smallest app-owned home/bookcase optimization justified by traces.
6. Re-run local Lighthouse and visible E2E.
7. Deploy.
8. Re-run production Lighthouse, WebPageTest, and PSI.
9. Classify remaining findings as app, Cloudflare, network, browser variance, or accepted framework cost.
10. Add soft budgets only after two or three stable measurement rounds.

## Validation Gate

Status: Pending

Run after code changes:

```powershell
npm --prefix .\BlazorAutoApp.Client run css:build
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
git diff --check
```

Run after render-mode, routing, modal, bookcase, or auth-adjacent changes:

```powershell
.\RunLocal.ps1 -NoBrowser

$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
$env:E2E_HEADLESS='0'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter FullyQualifiedName~E2E
```

Run after deploy:

```powershell
.\RunLighthouse.ps1 `
  -BaseUrl https://shipinspection.jacobgrum.com `
  -Paths "/", "/books/design-demos", "/books/design-demos/cloth-hardback", "/books?authorBookId=2&bookMode=view", "/Account/Login" `
  -Profile both `
  -Label production-big-scores-after-deploy
```

## Done Criteria

Status: Pending

- Home page remains Interactive Auto.
- Scrolling bookcase remains present and visually rich.
- Static demo and account pages stay lean.
- Lighthouse reports exist for local and production before/after.
- WebPageTest links exist for key production pages.
- PageSpeed Insights results are recorded.
- CrUX field data is tracked if available.
- Any Cloudflare score artifact is explicitly classified.
- App-owned accessibility, SEO, and best-practices findings are fixed or documented.
- Performance changes are backed by measured before/after data.
- Build, tests, formatting, CSS generation, and visible E2E pass after changes.
