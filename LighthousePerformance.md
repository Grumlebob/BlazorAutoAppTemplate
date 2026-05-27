# Lighthouse Performance Plan

Status: local pass done; production pass pending.

## Goal

Use Lighthouse to find and fix real performance, accessibility, best-practice, and SEO issues in the BlazorAutoApp template.

This pass has two stages:

- Stage 1: local Docker app at `https://127.0.0.1:7186`.
- Stage 2: deployed production domain after the user deploys the app.

The local pass should make the app obviously better before deployment. The production pass should verify the real network, TLS, proxy, compression, cache headers, and deployment behavior.

## Non-Goals

- Do not remove Interactive Auto render mode.
- Do not remove render-mode diagnostics.
- Do not remove Identity, passkeys, Redis, PostgreSQL, or LocalCluster deployment.
- Do not make Playwright or Lighthouse headless-only. Visible/manual inspection remains valuable.
- Do not optimize by hiding content, removing the bookcase experience, or weakening the template.
- Do not add brittle Lighthouse score thresholds before the baseline is understood.
- Do not make production-domain changes until the app is deployed and the real URL is known.

## Phase 1: Lighthouse Tooling

Status: done.

Tasks:

- Decide whether to use `npx lighthouse@latest` or add Lighthouse as a pinned dev dependency.
- Prefer a reproducible repo script over one-off terminal commands if the workflow will be repeated.
- Add report output under `TestResults/Lighthouse`.
- Keep generated reports ignored by git.
- Support local HTTPS with Chrome certificate ignoring only for local runs.
- Document commands in `TESTING.md` or a dedicated performance section.

Acceptance:

- A repo command can run Lighthouse locally without manual browser clicking.
- Reports are saved as HTML and JSON.
- Tooling does not pollute tracked files.

Execution notes:

- Added Lighthouse as a pinned client dev dependency through `package-lock.json`.
- Added `RunLighthouse.ps1` for repeatable mobile/desktop local and production runs.
- Added authenticated local Lighthouse support using the seeded Development/Docker user and a temporary ignored cookie header file under `TestResults/Lighthouse`.
- Documented Lighthouse commands in `TESTING.md`.
- Reports are written under ignored `TestResults/Lighthouse`.

Candidate commands:

```powershell
npm --prefix .\BlazorAutoApp.Client exec -- lighthouse https://127.0.0.1:7186 `
  --preset=perf `
  --output=html --output=json `
  --output-path=..\TestResults\Lighthouse\local-home-mobile `
  --chrome-flags="--ignore-certificate-errors"
```

## Phase 2: Local Baseline

Status: done.

Pages to measure:

- Anonymous home page: `/`
- Design demos: `/books/design-demos`
- Author book details route if routed directly: `/books/author/ship`
- Login page: `/Account/Login`
- Authenticated home page with seeded `user@user.com`.

Profiles:

- Mobile Lighthouse default.
- Desktop Lighthouse with `--preset=desktop`.

Tasks:

- Start local Docker stack with `.\RunLocal.ps1 -NoBrowser`.
- Confirm health at `https://127.0.0.1:7186/health/ready`.
- Run Lighthouse mobile and desktop against anonymous pages.
- For authenticated pages, use Playwright or Chrome remote debugging to create a logged-in session before Lighthouse.
- Save all reports under `TestResults/Lighthouse/<timestamp>/`.
- Summarize scores and top findings in the plan.

Acceptance:

- Baseline is recorded before changes.
- Anonymous and authenticated flows are both represented.
- Results distinguish local-only HTTPS certificate warnings from real app findings.

Execution notes:

- Local Docker health passed at `https://127.0.0.1:7186/health/ready`.
- Anonymous baseline reports: `TestResults/Lighthouse/baseline-anonymous-20260527-140019`.
- Authenticated baseline reports: `TestResults/Lighthouse/baseline-authenticated-20260527-140312`.

Baseline summary:

| Page | Profile | Performance | Accessibility | Best Practices | SEO | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `/` anonymous | mobile | 62 | 100 | 100 | 90 | 2,798 KiB |
| `/` anonymous | desktop | 99 | 100 | 100 | 90 | 2,798 KiB |
| `/` authenticated | mobile | 64 | 100 | 100 | 90 | 2,800 KiB |
| `/` authenticated | desktop | 96 | 100 | 100 | 90 | 2,800 KiB |
| `/books/design-demos` | mobile | 57 | 100 | 100 | 90 | 2,822 KiB |
| `/books/design-demos` | desktop | 93 | 100 | 100 | 90 | 2,822 KiB |
| `/books/author/ship` | mobile | 71 | 100 | 100 | 90 | 2,803 KiB |
| `/books/author/ship` | desktop | 92 | 100 | 100 | 90 | 2,803 KiB |
| `/Account/Login` | mobile | 100 | 100 | 96 | 90 | 72 KiB |
| `/Account/Login` | desktop | 100 | 100 | 96 | 90 | 72 KiB |

## Phase 3: Blazor Payload And Runtime Review

Status: done.

Tasks:

- Inspect Lighthouse transfer sizes and request waterfall.
- Check `_framework` payload size, WASM boot resources, CSS, JS, and static assets.
- Verify compression is active in Docker/deployment-representative hosting where applicable.
- Review cache headers for hashed assets such as scoped CSS, Tailwind CSS, JS modules, and framework files.
- Confirm no unused package or static asset is inflating publish output.
- Review whether render-mode diagnostics add meaningful payload or layout cost.

Acceptance:

- Blazor payload costs are understood and documented.
- Any easy wins are fixed without fighting the .NET 10 Blazor Web App model.
- Static asset caching remains production-safe.

Execution notes:

- The main Lighthouse payload cost is the expected .NET WebAssembly runtime and framework payload for Interactive Auto.
- Enabled `InvariantGlobalization` in `BlazorAutoApp.Client` to avoid shipping ICU data for this English-only template default.
- Documented the globalization tradeoff in `TemplateCustomization.md`.
- Optimized anonymous home payload from about 2,798 KiB to about 2,640 KiB.
- Optimized design demo payload from about 2,822 KiB to about 2,661 KiB.
- Verified publish output; largest shipped assets remain `dotnet.native.wasm`, `System.Private.CoreLib.wasm`, and normal Blazor framework assets.
- Static asset cache insight was already clean in Lighthouse.

Verification:

```powershell
dotnet publish .\BlazorAutoApp\BlazorAutoApp.csproj -c Release -o .\artifacts\publish-inspect
Get-ChildItem .\artifacts\publish-inspect\wwwroot -Recurse | Sort-Object Length -Descending | Select-Object -First 30 FullName,Length
```

## Phase 4: Bookcase Rendering Performance

Status: done.

Tasks:

- Inspect SVG book cover DOM size and repeated markup cost.
- Check whether infinite bookcase animation causes layout, paint, or compositing issues.
- Confirm hover/open animations do not cause layout shifts.
- Review mobile rendering cost with fewer visible books but still a full experience.
- Consider lightweight component reuse or data simplification only if Lighthouse/Performance traces show real cost.
- Keep the current visual quality unless measurement proves a performance issue.

Acceptance:

- No expensive animation or layout pattern is left unexamined.
- Bookcase remains visually rich and responsive.
- Changes are measurement-driven.

Execution notes:

- Lighthouse reported no CLS and no non-composited animation issue.
- DOM size was acceptable: roughly 1,004 elements on home and 1,229 on design demos.
- Added `content-visibility: auto` with stable intrinsic sizes to offscreen book frames so large SVG books do less offscreen rendering work while preserving layout and scroll width.
- Visible desktop E2E and mobile Books E2E passed after the change.

Verification:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~BooksE2ETests"
```

## Phase 5: Core Web Vitals And Layout Stability

Status: done.

Tasks:

- Review Largest Contentful Paint on home and design demo pages.
- Review Cumulative Layout Shift during prerender to hydration.
- Review Total Blocking Time and main-thread work during Blazor startup.
- Confirm book/modal dimensions are stable on mobile and desktop.
- Check font loading and text rendering.
- Check if render-mode badge or authentication state causes visible shifts.

Acceptance:

- Lighthouse does not report avoidable CLS.
- LCP element is intentional and not delayed by unnecessary work.
- Hydration does not make the app feel broken or jumpy.

Execution notes:

- CLS stayed at `0` across measured pages.
- Anonymous mobile home improved from 62 to 71.
- Authenticated mobile home rerun improved from 64 to 75.
- Design demo mobile improved from 57 to 60.
- Login stayed at 100 performance on mobile and desktop.
- Remaining mobile score limits are mostly Lighthouse's simulated cost of downloading/initializing the Blazor WebAssembly runtime under mobile throttling.

## Phase 6: Accessibility, Best Practices, And SEO

Status: done.

Tasks:

- Fix Lighthouse accessibility findings that are valid for a template app.
- Confirm buttons, links, modals, focus order, labels, and accessible names are correct.
- Confirm modal close/edit/save/delete controls work by keyboard.
- Review color contrast, especially book buttons and modal controls.
- Add or fix meta description and page titles if Lighthouse reports them.
- Confirm HTTPS, CSP-relevant headers, and best-practice findings are clean or intentionally deferred.

Acceptance:

- Lighthouse accessibility findings are either fixed or explicitly documented with a reason.
- Keyboard and screen-reader basics are not sacrificed for SVG visuals.
- SEO basics are sane for a template app.

Execution notes:

- Added a global meta description in `App.razor`.
- SEO improved from 90 to 100 on measured pages.
- Fixed the login best-practices issue by suppressing non-user-initiated conditional passkey mediation console errors on unsupported local domains.
- Login best practices improved from 96 to 100.
- Accessibility stayed at 100 across measured pages.

## Phase 7: Local Optimization Pass

Status: done.

Tasks:

- Apply the lowest-risk fixes from the baseline.
- Re-run Lighthouse after each meaningful category of change.
- Avoid broad refactors unless a measured bottleneck justifies them.
- Keep the app working in both prerendered and hydrated states.
- Keep tests and visual E2E green after each round.

Acceptance:

- Local Lighthouse scores improve or findings are reduced.
- No regression in build, tests, CSS generation, or visible E2E.
- Every performance change has a concrete finding behind it.

Execution notes:

- Optimized anonymous reports: `TestResults/Lighthouse/optimized-anonymous-20260527-141600`.
- Optimized authenticated reports: `TestResults/Lighthouse/optimized-authenticated-20260527-141758`.
- Authenticated mobile rerun report: `TestResults/Lighthouse/optimized-authenticated-rerun-20260527-141921`.

Optimized summary:

| Page | Profile | Performance | Accessibility | Best Practices | SEO | Payload |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `/` anonymous | mobile | 71 | 100 | 100 | 100 | 2,640 KiB |
| `/` anonymous | desktop | 91 | 100 | 100 | 100 | 2,640 KiB |
| `/` authenticated | mobile rerun | 75 | 100 | 100 | 100 | 2,641 KiB |
| `/` authenticated | desktop | 99 | 100 | 100 | 100 | 2,641 KiB |
| `/books/design-demos` | mobile | 60 | 100 | 100 | 100 | 2,661 KiB |
| `/books/design-demos` | desktop | 93 | 100 | 100 | 100 | 2,661 KiB |
| `/books/author/ship` | mobile | 72 | 100 | 100 | 100 | 2,645 KiB |
| `/books/author/ship` | desktop | 88 | 100 | 100 | 100 | 2,645 KiB |
| `/Account/Login` | mobile | 100 | 100 | 100 | 100 | 72 KiB |
| `/Account/Login` | desktop | 100 | 100 | 100 | 100 | 72 KiB |

Verification:

```powershell
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
```

## Phase 8: Production-Domain Pass After Deploy

Status: pending.

Prerequisite:

- User deploys the app and provides the real production URL.

Tasks:

- Run Lighthouse mobile and desktop against the production home page.
- Run Lighthouse against the public design demo page if it remains public.
- Run authenticated performance checks if a safe production test account exists.
- Compare production results with the local baseline.
- Check real TLS, HTTP/2 or HTTP/3, compression, static asset cache headers, proxy headers, redirects, and server latency.
- Check whether Cloudflare/Caddy/LocalCluster behavior changes scores.
- Record production reports under `TestResults/Lighthouse/production-<timestamp>/`.

Acceptance:

- Production Lighthouse report is saved and summarized.
- Any local-vs-production gap is classified as app, deployment, network, proxy, or expected variance.
- Follow-up deployment fixes are planned separately if needed.

Candidate commands:

```powershell
$env:LIGHTHOUSE_BASE_URL='https://your-real-domain.example'
npm --prefix .\BlazorAutoApp.Client exec -- lighthouse "$env:LIGHTHOUSE_BASE_URL" `
  --output=html --output=json `
  --output-path=..\TestResults\Lighthouse\production-home-mobile

npm --prefix .\BlazorAutoApp.Client exec -- lighthouse "$env:LIGHTHOUSE_BASE_URL" `
  --preset=desktop `
  --output=html --output=json `
  --output-path=..\TestResults\Lighthouse\production-home-desktop
```

## Final Verification Gate

Status: local pass done.

Run after local optimization:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
npm --prefix .\BlazorAutoApp.Client run css:build
git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json
git diff --check
.\RunLocal.ps1 -NoBrowser
```

Run visible E2E after performance changes:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter "FullyQualifiedName~E2E"
```

Execution notes:

- `dotnet restore .\BlazorAutoApp.sln` passed.
- `dotnet build .\BlazorAutoApp.sln -c Release --no-restore` passed.
- `dotnet test .\BlazorAutoApp.sln -c Release --no-build` passed: 77 passed, 5 skipped.
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore` passed.
- `npm --prefix .\BlazorAutoApp.Client run css:build` passed.
- `git diff --check` passed.
- Docker web image rebuilt and local health passed.
- Visible E2E passed: 5/5.
- Visible mobile Books E2E passed: 2/2.
- `npm audit --audit-level=moderate` passed with 0 vulnerabilities.
- `git diff --exit-code -- BlazorAutoApp/wwwroot/tailwind.css BlazorAutoApp.Client/package-lock.json` shows intentional tracked changes from adding Lighthouse and regenerating Tailwind for the new `content-visibility` utilities; rerunning the generators produced no additional unexpected files.

## Done Criteria

Status: local pass done; production pending.

- Local Lighthouse reports exist for mobile and desktop.
- Authenticated and anonymous performance are both understood.
- Valid Lighthouse findings have been fixed or documented.
- Build, tests, formatting, CSS generation, Docker health, and visible E2E pass.
- The plan contains a clear handoff point for production-domain testing after deployment.

Execution notes:

- Local Lighthouse reports exist for anonymous, authenticated, mobile, and desktop paths.
- Valid local findings were fixed or documented.
- The remaining work is the production-domain pass after deployment.
