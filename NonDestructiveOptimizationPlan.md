# Non-Destructive Optimization Plan

## Goal

Status: Completed

Optimize the live BlazorAutoApp template at `https://shipinspection.jacobgrum.com/` with Lighthouse and production measurements, without weakening Cloudflare security features or doing risky infrastructure changes.

The target is not a fake perfect score. The target is a faster, cleaner, measurable production app while preserving:

- Cloudflare bot detection / JavaScript detections / challenge platform.
- HTTPS and proxy security behavior.
- Interactive Auto render mode.
- Identity/authentication.
- PostgreSQL, Redis, migrations, and LocalCluster deployment.
- The visual bookcase experience.

Result: No Cloudflare security feature was disabled or bypassed in production. One safe app-level rendering optimization was prepared for the design demos page.

## Non-Goals

Status: Completed

- Do not disable Cloudflare bot detection, Bot Fight Mode, JavaScript detections, WAF, security rules, or challenge behavior.
- Do not add Cloudflare bypass rules just to improve Lighthouse.
- Do not cache authenticated HTML at Cloudflare.
- Do not remove Blazor Interactive Auto or WebAssembly hydration to chase a score.
- Do not remove visuals or make the bookcase bland unless measurements prove a specific bottleneck.
- Do not reset production PostgreSQL or Redis.
- Do not make destructive deployment changes.
- Do not introduce Lighthouse score thresholds until current variance is understood.

Result: All non-goals were respected.

## Phase 1 - Production Baseline

Status: Completed

Production health:

```text
https://shipinspection.jacobgrum.com/health/ready -> 200 Healthy
```

Reports:

- Cold-ish run: `TestResults/Lighthouse/production-nondestructive-cold-20260528-100617`
- Warm run: `TestResults/Lighthouse/production-nondestructive-warm-20260528-100905`

Cold-ish production summary:

| Page | Profile | Performance | Accessibility | Best Practices | SEO | FCP | LCP | TBT | CLS | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | mobile | 84 | 100 | 81 | 100 | 1.74s | 2.24s | 504ms | 0 | 2,562 KiB |
| `/` | desktop | 100 | 100 | 81 | 100 | 0.43s | 0.43s | 3ms | 0 | 2,562 KiB |
| `/books/design-demos` | mobile | 84 | 100 | 81 | 100 | 2.47s | 3.14s | 303ms | 0 | 2,565 KiB |
| `/books/design-demos` | desktop | 100 | 100 | 81 | 100 | 0.43s | 0.46s | 7ms | 0 | 2,565 KiB |
| `/books/author/ship` | mobile | 66 | 100 | 81 | 100 | 2.61s | 13.25s | 118ms | 0 | 2,564 KiB |
| `/books/author/ship` | desktop | 99 | 100 | 81 | 100 | 0.49s | 0.91s | 21ms | 0 | 2,564 KiB |
| `/Account/Login` | mobile | 94 | 100 | 81 | 100 | 1.89s | 1.89s | 232ms | 0 | 82 KiB |
| `/Account/Login` | desktop | 100 | 100 | 81 | 100 | 0.49s | 0.49s | 4ms | 0 | 82 KiB |

Warm production summary:

| Page | Profile | Performance | Accessibility | Best Practices | SEO | FCP | LCP | TBT | CLS | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | mobile | 80 | 100 | 81 | 100 | 2.12s | 2.15s | 631ms | 0 | 2,562 KiB |
| `/` | desktop | 99 | 100 | 81 | 100 | 0.57s | 0.58s | 47ms | 0 | 2,562 KiB |
| `/books/design-demos` | mobile | 59 | 100 | 81 | 100 | 2.53s | 13.49s | 386ms | 0 | 2,565 KiB |
| `/books/design-demos` | desktop | 99 | 100 | 81 | 100 | 0.67s | 0.83s | 12ms | 0 | 2,565 KiB |
| `/books/author/ship` | mobile | 72 | 100 | 81 | 100 | 2.32s | 3.52s | 616ms | 0 | 2,564 KiB |
| `/books/author/ship` | desktop | 99 | 100 | 77 | 100 | 0.61s | 0.76s | 7ms | 0 | 2,564 KiB |
| `/Account/Login` | mobile | 91 | 100 | 81 | 100 | 1.53s | 1.53s | 376ms | 0 | 82 KiB |
| `/Account/Login` | desktop | 100 | 100 | 81 | 100 | 0.50s | 0.50s | 34ms | 0 | 82 KiB |

Result: Production is healthy. Desktop is excellent. Mobile home/login are good. Mobile design-heavy pages show LCP/TBT variance under Lighthouse throttling.

## Phase 2 - Classify Findings

Status: Completed

Classification:

- Cloudflare security script artifact: Best Practices 77-81 is caused by `/cdn-cgi/challenge-platform/scripts/jsd/main.js` deprecation warnings.
- Blazor framework/runtime cost: about 2.56 MiB transfer on interactive pages, dominated by `dotnet.native.wasm`, `System.Private.CoreLib.wasm`, and framework WASM.
- App code: design demos overview renders many large SVG cards, which can cost mobile layout/rendering work.
- Caddy/static assets: hashed static assets have `Cache-Control: max-age=31536000, immutable`; Cloudflare cache hit was observed for hashed CSS.
- HTML/cache safety: HTML was not over-cached.
- Core Web Vitals: CLS stayed at 0.
- Network/server: server response time was short in Lighthouse, roughly 80-270 ms for root documents.

Cloudflare diagnostic:

- Report: `TestResults/Lighthouse/production-nondestructive-cloudflare-diagnostic-20260528-101401`
- Home mobile with only `*/cdn-cgi/challenge-platform/*` blocked locally: Performance 53, Accessibility 100, Best Practices 100, SEO 100.

Result: The persistent Best Practices finding is external to app code. The blocked run was diagnostic only and did not change production.

## Phase 3 - Safe App-Level Optimizations

Status: Completed

Change made:

- Added `content-visibility: auto` with stable `contain-intrinsic-size` to each design demo card in `BlazorAutoApp.Client/Features/Books/DesignDemos/BookDesignDemos.razor`.
- Regenerated `BlazorAutoApp/wwwroot/tailwind.css`.

Reason:

- The design demos overview is the one page in the measured set that intentionally renders many large SVG book designs at once.
- The bookcase already uses this technique safely.
- This keeps the visuals and links intact while allowing the browser to skip offscreen card rendering work.

Local spot check after change:

- Report: `TestResults/Lighthouse/local-nondestructive-design-demos-check-20260528-102155`
- `/books/design-demos` mobile local: Performance 65, Accessibility 100, Best Practices 100, SEO 100.

Result: A low-risk app-owned optimization is ready. It requires deployment before production Lighthouse can measure the live effect.

## Phase 4 - Safe Server And Header Optimizations

Status: Completed

Findings:

- Fingerprinted CSS links are emitted by `@Assets[...]`, for example `tailwind.<fingerprint>.css`.
- Fingerprinted CSS responses had `Cache-Control: max-age=31536000, immutable`.
- Cloudflare reported cache hits for hashed CSS.
- Framework assets also used long-lived immutable caching.
- HTML was not converted to public immutable caching.
- No redirect/header issue was found that justified a Caddy or Cloudflare change.

Result: No server/header code change was justified in this pass.

## Phase 5 - Core Web Vitals Pass

Status: Completed

Findings:

- CLS is 0 across measured pages.
- Home mobile LCP was stable around 2.15-2.24s.
- Login mobile LCP was stable around 1.53-1.89s.
- Design-heavy pages showed mobile LCP variance, including occasional 13s simulated LCP readings.
- Testing the canonical author detail query URL directly still showed similar LCP variance, so the old `/books/author/ship` compatibility route is not the primary cause.
- No non-composited animation or layout-shift issue was reported.

Result: The main remaining app-controlled area is reducing offscreen SVG/rendering work on design-heavy pages, addressed by the design demo card containment change.

## Phase 6 - Accessibility, Best Practices, SEO

Status: Completed

Findings:

- Accessibility stayed 100 on all measured pages.
- SEO stayed 100 on all measured pages.
- App-controlled best-practices issues were not found.
- Cloudflare challenge script reported three deprecated API warnings from `/cdn-cgi/challenge-platform/scripts/jsd/main.js`.
- One warm desktop detail run also logged a Chrome inspector issue, but the recurring weighted finding was still Cloudflare deprecations.

Result: App-controlled accessibility, SEO, and best-practices are clean. Remaining best-practices score loss is accepted as a Cloudflare security-product artifact.

## Phase 7 - Repeat Measurements

Status: Pending production deployment

Completed:

- Cold and warm production measurements were captured before code changes.
- A local mobile Lighthouse spot check was captured after the design demo containment change.

Pending:

- Deploy the current branch.
- Re-run production Lighthouse against:

  ```powershell
  .\RunLighthouse.ps1 `
    -BaseUrl https://shipinspection.jacobgrum.com `
    -Paths "/", "/books/design-demos", "/books/author/ship", "/Account/Login" `
    -Profile both `
    -Label production-nondestructive-after-deploy
  ```

Acceptance after deploy:

- Compare design demos mobile LCP/TBT before and after.
- Confirm Cloudflare best-practices artifact remains classified, not treated as app code.

## Phase 8 - Validation Gate

Status: Completed

Validation run:

```text
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
npm --prefix .\BlazorAutoApp.Client run css:build
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:1.7.12
python -m yamllint .github Deployment/LocalCluster
git diff --check
.\RunLocal.ps1 -NoBrowser
RUN_E2E=1 visible Playwright E2E against https://127.0.0.1:7186
```

Results:

- Build passed.
- Tests passed: 77 passed, 5 skipped.
- Formatting verification passed.
- Tailwind build passed.
- Deployment audit passed.
- Rendered template validation passed.
- actionlint passed.
- yamllint passed.
- `git diff --check` passed.
- Local Docker app rebuilt and `/health/ready` passed.
- Visible E2E passed: 5 passed, 0 skipped.

Note:

- `BlazorAutoApp/wwwroot/tailwind.css` intentionally changed because Tailwind generated the new `contain-intrinsic-size` utilities.

## Phase 9 - Done Criteria

Status: Completed except production after-deploy comparison

Done:

- Production Lighthouse baseline and warm reports exist.
- App-controlled findings were fixed or documented.
- Remaining Cloudflare challenge-script findings are explicitly accepted as security-product artifacts.
- No Cloudflare safety feature was disabled.
- No destructive database/Redis/deployment operation was used.
- Validation gates passed.

Pending after deployment:

- Re-run production Lighthouse to measure the live effect of the design demos containment change.

