# Independent React Frontend for the ASP.NET Core Template

Status: authorized delivery; P0, P1.1 complete, P1.2 in progress.
Last reviewed: 2026-10-11.
Completion requires implementation PRs merged to `main`, green main CI, recorded merge commits, and a verified public React deployment on the operator's existing native demo node. A build, container smoke test, or successful homepage response alone is not completion.

## How to use this plan

Start with the execution entry point below. Read sections 1-5 for product, architecture, security, and build contracts. Execute the work packets and phase details in section 6 in dependency order. Section 7 defines required evidence. Sections 8-11 specify public delivery, operations, template usability, and risks. Sections 12-14 record owner dependencies, settled decisions, and actual progress.

Checkboxes describe future work until their evidence is recorded. Keep this document current when implementation changes a contract. Use small reviewable PRs; retain the complete delivery scope across them. The companion goal prompt authorizes the scoped implementation and LocalSingleNode delivery described here. Follow its exclusions and the packet gates below.

### Execution entry point for a fresh chat

1. Read `AGENTS.md`, this entire plan, [Test.md](../docs/Test.md), and the ignored `Plans.local/ReactFrontendProfile.demo.md` if present. The companion [ReactFrontendDeliveryGoal.md](ReactFrontendDeliveryGoal.md) is the executable goal prompt; this plan supplies its detailed contract.
2. Inspect branch, remotes, status, registered worktrees, existing task ownership, open relevant PRs and the section 14 ledger. Resume verified existing work rather than repeating it. A previous chat's claim, pending checkbox, or local file is not proof of a merge, green check or live release.
3. Preserve the dirty source checkout. For implementation, create a task branch/worktree from fetched verified `origin/main`, using the repository's task tooling when applicable. Copy only these approved planning documents into that branch if they are still untracked here. Copy the non-secret target-intent note into the new worktree's ignored `Plans.local/` too, verifying it remains ignored; do not copy credential files. Do not import unrelated working changes, stash/reset them, or treat them as released dependencies. Bring required changes from other tasks only through their merged main commits.
4. Record the next work-packet ID, dependencies, files, acceptance cases and intended PR. Work one coherent packet at a time; related packets may share a small PR when all prerequisites exist. Never put the entire plan into one PR.
5. Implement the packet, its specified tests, generated contracts and affected audits/docs together. Run the local gate and new targeted checks before pushing. Stage explicit paths, open a PR, verify `build-test-push` on the exact current head, merge normally and wait for successful main validation/publishing as applicable. Record merge SHA and runs before releasing or advancing a dependent packet.
6. After every PR and before a chat handover, update section 14 with packet IDs, current branch/PR/head, local results, merge/main run, blockers and the exact next command/action. Keep private targets and authenticated artifacts in the ignored record. Re-read current main/runbooks before a deployment; do not execute stale command examples blindly.
7. If live node/DNS access is missing, finish independent code, tests and documentation. Keep only the dependent installation/deployment milestone pending and name the exact external action. Never invent secrets or reinterpret missing access as approval. Mail/provider activation is outside this goal.

### Scope correction from the owner

The first products, including the portfolio and public demo, do not use accounts. This revision supersedes the earlier requirement for A/B/C account parity. The executable goal completes the public React profile, its deployment and handover. It must not implement a React account system to satisfy obsolete checkboxes.

## 1. Recommendation and delivery scope

Use React, TypeScript, Vite, React Router Framework Mode with `ssr:false`, TanStack Query, Tailwind CSS and the existing ASP.NET Core host. Generate contracts with ASP.NET Core OpenAPI 3.1 and `openapi-typescript`; use `openapi-fetch` for typed requests. Serve the static production bundle from C#. No Node production process is needed.

The tool selection remains appropriate. Router owns navigation and route modules; Query owns API reads/cache. Do not duplicate server state in loaders or introduce Redux, Axios, a second generated client or another backend. Framework SPA mode gives a documented path to future portfolio prerendering without requiring it in this release. See [SPA mode](https://reactrouter.com/how-to/spa), [Query's role](https://tanstack.com/query/latest/docs/framework/react/overview) and [typed fetch](https://openapi-ts.dev/openapi-fetch/).

### Required v1 scope

1. One tracked build selection produces Blazor Auto or React from the same backend. Template default stays `BlazorAuto`.
2. React is a polished public application: coherent shell, public sample-book catalog/details, responsive layouts, accessible navigation and complete loading/empty/error states. Reuse the existing public author-book APIs and sample data; do not turn private user books into public data.
3. Generated API types, local development, clean production builds, both-profile CI and immutable release provenance work from a fresh checkout.
4. A separate React demo runs on the selected existing native node and public hostname. Preserve the existing Blazor demo. Verify the React application in a real browser through public HTTPS.
5. Documentation explains extension, profile selection, release/update and the simple existing backup/doctor/recovery path. Completion requires PR merges, green main CI and recorded public evidence.

### Account area: minimal by omission

React v1 has no login/logout/register menu, account settings, private bookcase UI or account onboarding. Add no React account API, auth/session provider, email sender, password recovery, Google integration, passkeys, personal-data export/deletion or custom reauthentication/challenge store. Do not install MailKit or add SMTP/provider secrets for this work.

Preserve existing Blazor accounts, Identity storage, policies and migrations. Keep shared private APIs protected. React does not map Razor account pages or provider callbacks. Public acceptance creates no accounts and writes no user data, so it needs no fixture-deletion helper or account-deletion implementation. Existing account defects are separate follow-up work unless they directly prevent the selected profile from starting safely.

Future accounts require a separately authorized feature plan for an actual product. Do not add dormant account scaffolding, generic capability switches or fake-success recovery endpoints now. Record the absence clearly in frontend documentation; the demo must not imply account features exist.

### Boundaries and settled defaults

- Portfolio and other products remain independent repositories/deployments. The template demonstrates a public API-backed feature; it does not implement their product features, CMS, blog or authentication requirements.
- Keep LocalSingleNode, LocalCluster and Cloud supported in the template. Only LocalSingleNode is deployed for this React demo.
- Preserve the separate React hostname selected by the owner. Actual node names, origins, resource IDs, addresses and ports stay in private configuration or ignored `Plans.local/` notes. Tracked examples use placeholders.
- Start with a static SPA. A portfolio needing search-visible HTML can add deliberate public prerendering later using the same Router stack. No mandatory prerender fixture or live-data SSR is part of this delivery.
- Use existing deployment, diagnostic and backup tooling. Check status, record the previous compatible release, and verify one scoped app restart. No new recovery platform, automatic rollback or routine restore/reboot drill. Rehearse deeper recovery only for relevant changed schema/backup risks.

## 2. Repository findings and change map

Recheck these findings if intervening PRs change the relevant files.

| Existing location | Finding / required treatment |
| --- | --- |
| `BlazorAutoApp/Program.cs` | Razor, Interactive Server/WASM, UI state, Identity UI, migrations, seeds and APIs share startup. Extract profile composition. |
| `BlazorAutoApp/BlazorAutoApp.csproj` | Client reference and WASM Server package are unconditional. Condition dependencies, Razor inputs and publish content. |
| `BlazorAutoApp/Features/Books/DependencyInjection.cs` | Backend registration references client `AuthorBookcaseState`. Move UI state to Blazor composition. |
| `BlazorAutoApp/Features/Login/Account/LoginFeatureExtensions.cs` | Common Identity/EF/cookies mixed with Blazor auth state, redirect helpers and optional provider registration. Keep Google remote-handler registration in Blazor composition only. |
| `BlazorAutoApp/Features/Login/Account/CurrentUserAccessor.cs` | HTTP principal plus circuit fallback. Preserve Blazor behavior; add HTTP-only React implementation behind the same interface. |
| `BlazorAutoApp/Features/Login/Account/IdentityComponentsEndpointRouteBuilderExtensions.cs` | References Razor page types. Compile/map only for Blazor. |
| `BlazorAutoApp/Infrastructure/Hosting/AntiforgeryExtensions.cs` | Preserve existing Blazor protection. React public reads need no new token bootstrap or shared enforcement rollout. |
| `BlazorAutoApp/Infrastructure/Hosting/AppRateLimiting.cs` | Preserve public API limits and trusted forwarding; no new auth paths are introduced. |
| `BlazorAutoApp/Infrastructure/Hosting/HeadRequestExtensions.cs` | Hard-coded public HEAD routes. Keep Blazor mapping separate. |
| `BlazorAutoApp/Infrastructure/Hosting/AppCachingExtensions.cs` | Registration connects to Redis and persists keys. Schema extraction needs side-effect-free composition. |
| `BlazorAutoApp/Infrastructure/Persistence/AppDbContext.cs` | Shared Identity schema includes .NET 10 passkeys. Reuse store/migrations. |
| `BlazorAutoApp.Client/Features/Books/BooksClientService.cs` | Preserve the existing Blazor HTTP client and authenticated regression; no React private-write consumer is added. |
| `BlazorAutoApp.Simulation/Auth/BrowserAuthBootstrap.cs`, `Books/AuthenticatedBooksClient.cs` | Existing authenticated simulation remains Blazor-specific. Preserve it; React coverage uses public reads without inventing a login flow. |
| `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs` | Keep default Blazor fixtures; add explicitly selected React public/authorization-boundary fixtures. |
| `BlazorAutoApp.Test/E2E/Features/Login/IdentityE2ETests.cs` | Existing account tests remain required for Blazor, not for the account-free React UI. |
| Dockerfile, `.dockerignore`, root Compose, `Scripts/RunLocal.ps1` | Add selected frontend build; explicitly include required scripts currently excluded by Docker context rules. |
| `.github/workflows/ci.yml` | Node 24; required PR check `build-test-push`. Validate both profiles; publish only clone selection. |
| `docs/Requirements.md` | Requirements currently assume Blazor rendering. Define common and profile-specific rules. |
| `Scripts/Test-DeployedSite.ps1` | Hard-coded Blazor assets/forms and account deletion; add a trusted React public acceptance branch that never registers/deletes users. Preserve the Blazor branch. |
| `Deployment/LocalSingleNode/Scripts/acceptance-check.sh`, `public-acceptance-check.sh` | LAN and public checks invoke the Blazor acceptance script. Pass verified profile metadata and retain readiness validation. |
| `Deployment/Common/Scripts/validate_release_manifest.py`, release-contract tests, all CD consumers | Current release manifest schema v1 has no frontend field. Version the contract and verify profile alongside repository/SHA/run/attempt/image/migration provenance. |
| `Deployment/LocalSingleNode/Scripts/lib/collisions.py`, `public_collisions.py` | Refuse foreign app roots, listeners, subnets, Caddy sites and public connector resources. Reuse these checks for the second app. |
| `Deployment/LocalSingleNode/PublicSetup.md`, `HowToDeployLocalSingleNode.md` | Existing public setup and node lifecycle runbooks; adapt profile assertions, preserve native-node and ownership requirements. |
| `.github/workflows/cd-localsinglenode.yml` | Verifies native hostname, main ancestry, successful push CI and digest before deployment; extend profile validation without a runtime frontend switch. |

Current backend policy includes `RequireConfirmedAccount=false`, a no-op email sender, optional Google credentials and Identity cookies. Preserve existing Blazor behavior. React v1 introduces no account UI or signin flow and needs no mail/provider configuration.

Book APIs already separate public author books from owned private books. Reuse public DTOs/services; preserve private authorization and cache headers. Add no account or private-write endpoints for the React demo. Experimental design-demo layouts are not required React functionality.

The original source checkout contains uncommitted LocalSingleNode public-deployment work. That work remains untouched and is excluded from the React task worktree. Use only behavior already merged to main; bring any required deployment changes through a separate PR first.

## 3. Settled architecture

### Responsibilities

| Component | Owns |
| --- | --- |
| React Router | URLs, route modules/layouts, navigation, lazy route loading, route errors |
| TanStack Query | Public API data, request lifecycle, query keys and cache; no account/session store |
| Local React state | Form drafts and temporary UI state |
| ASP.NET Core | Auth, authorization, validation, business rules, persistence/cache, OAuth/WebAuthn verification |
| OpenAPI tooling | TypeScript API shapes generated from C# metadata |

Use Query hooks in route components initially. Add `clientLoader` prefetching only when useful, reusing the same QueryClient/query definitions. Do not duplicate API results in Router loader state. No Redux, second server-state store, second backend, CMS, or runtime SSR is required.

Use accessible native inputs, server validation, Tailwind and a small local component set. Add a form library or accessible headless primitives only for concrete needs. Do not make component-library choice another prerequisite.

### URLs and hosting

```text
https://<app-host>/                         selected frontend
https://<app-host>/books                    public sample catalog
https://<app-host>/books/author/<seed-key>  public author details
https://<app-host>/api/author-books/...     public C# JSON API
https://<app-host>/api/books/...            existing protected API; no React UI
https://<app-host>/health/...               existing health checks
```

Use one origin. React maps no `/account`, `/Account`, `/api/auth` or provider-callback endpoints. Reserve those paths from SPA fallback and return real 404 when inactive. ASP.NET case-insensitive routing must not expose Blazor account handlers in React.

Resolve `/books/author/<seed-key>` from the existing public catalog's `SeedKey` to its numeric book ID, matching the existing compatibility URL. The public item API is `/api/author-books/{id:int}`; do not pass a seed key to that integer endpoint. Missing keys/items show the public not-found state. No new lookup API is required.

Keep the current demo on Blazor. Deliver a separate React demo as a required part of this plan. Each app serves its own UI and API on one origin; the two demos do not call each other's API or share accounts. Public hostname setup, isolated deployment, and live verification are specified in section 8.

Local development uses an HTTPS Vite browser origin proxying `/api` to C#. No OAuth callback/redirect setup is needed. Do not add wildcard CORS or weaken existing backend cookies. Reuse or safely generate a development certificate through existing tooling.

### Persistent build choice and isolation

Add tracked root `frontend-profile.txt`, containing exactly `BlazorAuto` or `React`. Template default is `BlazorAuto`. Read it in `Directory.Build.props` when `FrontendProfile` is not explicitly supplied. MSBuild/Docker arguments are temporary validation overrides, not another persisted setting.

Add one resolver for orchestration: trim whitespace; reject missing/empty/unknown values; pass the same validated choice to MSBuild and Docker. CI reads it for releases and overrides it for validation. Never infer profile from hostname, environment, installed packages or existing bundles.

Keep one ASP.NET host project:

1. Extract selected frontend registration, middleware and mapping behind a small composition boundary.
2. Include one of two composition source files with MSBuild conditions, keeping the calling API identical. Avoid widespread preprocessor branches.
3. Move `AuthorBookcaseState`/`UserBookcaseState` registrations into Blazor composition.
4. Keep common Identity setup independent of `AuthenticationStateProvider`/`IdentityRedirectManager`; register them only for Blazor.
5. Split `ICurrentUserAccessor` into a common interface. Preserve circuit-aware Blazor implementation and add HTTP-principal React implementation. Never accept client user IDs as authorization context.
6. Condition client project reference, WASM Server package, Razor compilation inputs, associated scripts/styles and Blazor-only helper files. Inspect evaluated `Compile`, `RazorComponent`, `Content` and static-web-asset items; removing content alone may leave Razor compilation active.
7. Stage an explicit selected web root. Do not copy Blazor `wwwroot` wholesale into React. Copy truly common icons/assets explicitly.
8. Bake profile into assembly/image metadata. No runtime setting switches the published UI.

Keep `MapStaticAssets` for Blazor. For React, prefer ordinary ASP.NET static-file hosting over the selected physical web root, plus explicit frontend navigation handling. In publish output that root is `wwwroot`; local asset hosting resolves the generated `BlazorAutoApp.React/build/client` directory. Vite development does not require a built React shell. Do not rely on Blazor's generated static-web-asset manifest to discover late-copied React files.

Validate profiles in separate clean workspaces. Profile-switch scripts may clean only verified repository-owned generated paths; do not use `--no-build` across a switch. Solution/test builds may still compile Blazor client tests; the deployed React host must have no client dependency or WASM payload.

**P1 is a feasibility gate:** prove both clean publishes first. If SDK item isolation still forces inactive dependencies/assets, document the failing inputs and use one small Razor Class Library for Blazor UI, the preselected fallback. Keep one host and shared backend. Do not duplicate backend logic or spread build conditionals through features.

### Rendering and portfolio

Start with `ssr:false`. Router still renders the root at build time, so no initial-render `window`, localStorage, WebAuthn or live authenticated API access. See [SPA mode](https://reactrouter.com/how-to/spa).

If the later portfolio clone needs prerendering, use repository content for public home/about/project routes with the same stack; content changes require rebuild. This is guidance for that product, not required template implementation. See [prerendering](https://reactrouter.com/how-to/pre-rendering).

V1 builds the SPA shell without production catalog/database access. Document the portfolio prerender option, but do not implement a second rendering configuration or require a prerender hosting proof in this goal. Do not claim API-loaded books are server-rendered.

Inspect the pinned Router version's actual SPA output and serve its generated shell. If a later product enables prerendering, recheck HTML/data/fallback layout then; do not build dormant dual-rendering logic now. Missing static or Router data artifacts return 404 rather than HTML.

Retain build-time dependencies required by the selected Router release, including `@react-router/node` where its build requires it. The restriction is no Node process or Node executable in the production image, not removal of dependencies needed to produce correct static output. Verify behavior against the selected version rather than copying a version-specific output layout unchecked. See the [SPA build requirements](https://reactrouter.com/how-to/spa).

### UI and feature contract

Keep Books as a coherent reference feature. Write ordinary product copy; do not expose template plumbing in registration, book forms, or error messages. Use a small consistent system for spacing, typography, colors, focus, buttons, inputs, validation, cards, dialogs, and feedback. Reuse common patterns without building a generic application framework.

| Surface | Required behavior |
| --- | --- |
| Shell | Responsive navigation, skip link, route focus, consistent typography/spacing and useful page titles |
| Public catalog | Existing supported public query behavior, useful sample books, author detail URLs, bounded reads |
| Failures | Loading/empty states, missing item, throttling, offline/network failure, safe unexpected-error screen and retry |
| Account area | Absent: no login menu, signup, private bookcase or account settings |

Every public data view defines loading, empty, success, missing item, throttling, offline/network and server-error behavior. Cancel stale reads on navigation and provide useful retry. No credential forms, private mutations or optimistic CRUD behavior are required. Keep errors safe and preserve any public filter state across recoverable failures.

Target WCAG 2.2 AA for the delivered screens. Acceptance includes semantic structure, visible keyboard focus, correct labels and autocomplete, linked errors, announcements for async results, dialog focus/return, contrast, reduced motion, 200% text zoom, and reflow at 320 CSS pixels. Run automated axe checks and manual keyboard/screen-reader spot checks; a Lighthouse or axe score alone is insufficient. Use the [WCAG 2.2 recommendation](https://www.w3.org/TR/WCAG22/) as the checklist.

Support current stable Chromium, Firefox and WebKit through the existing Playwright harness, plus mobile viewports. Record browser/OS/version, set `lang`, route titles and meaningful descriptions. Do not claim SPA titles provide prerendered SEO or expose private data in generated HTML. Product-specific canonical/sitemap/prerender work belongs to that product's scope.

## 4. Public profile and security contract

### Authentication boundary

- Keep common Identity/authorization registration where the backend needs it; compile/map Blazor account UI only in the Blazor profile. Register optional Google/other remote authentication handlers only for Blazor: their middleware can intercept callbacks even without a mapped Razor page. React's HTTP current-user accessor remains a backend integration detail for protected shared APIs, not a new frontend account feature.
- React v1 consumes only anonymous public APIs, with no user-specific output. Use `credentials: 'omit'` in its public typed client. Public pages must not acquire an auth/CSRF session merely to load the catalog.
- Existing private book reads/writes still require authentication. Anonymous protected JSON requests return `401`, never an SPA shell, login HTML, private data or a successful write. Existing Blazor tests retain authenticated `403` permission-failure coverage where applicable. If cookie redirects need adjustment, scope JSON behavior carefully and preserve Blazor's browser signin behavior.
- Do not make protected endpoints anonymous to get a React demo working. No anonymous CRUD, browser database access, seeded public admin login or test backdoor.
- Preserve existing CSRF protection and authenticated callers in Blazor/simulation. This public-only release adds no authenticated mutations and does not introduce a new shared CSRF bootstrap/enforcement rollout. A later account feature must implement explicit CSRF for its cookie-based mutations.
- No React `/api/auth/*`, Razor account routes or signin callbacks. Test reserved paths case-insensitively; the SPA fallback must not turn inactive auth endpoints into successful pages.

### HTTP, privacy and production hardening

- Public API responses must remain independent of cookies/users and follow their existing cache contract. Private JSON responses retain private/no-store behavior. Error responses expose only safe details/correlation IDs.
- Maintain explicit production host/proxy trust. Verify the Cloudflare-to-Caddy-to-host host/scheme chain; arbitrary forwarding headers must not affect application URLs or client identity.
- Validate CSP against the actual Router SPA output, preferring self-hosted assets and generated hashes for required inline scripts. Do not add broad `unsafe-inline`/`unsafe-eval` workarounds. Preserve Blazor's separate policy.
- Check framing protection, `X-Content-Type-Options`, Referrer-Policy, Permissions-Policy and HTTPS/HSTS at the intended app/proxy boundary. Do not change sibling-app headers or parent-domain policy incidentally.
- Retain existing server payload/query bounds and public read rate limits. Do not globally weaken limits to make acceptance traffic pass.
- Keep secrets out of `VITE_*`, client bundles, source maps, artifacts and image layers. All frontend configuration is public. Document source-map publication and inspect built output.
- Preserve independent app database/Redis ownership, host-only backend cookies and Data Protection identity. Ports alone do not isolate cookies when apps share a LAN host; preserve app-specific naming through the existing runbook without building React cookie state.
- Skip local/demo account-seeding paths for React while retaining public author-book seeds and common migrations. Never delete existing account rows or remove Identity tables. Preserve Blazor's configured seed behavior. Do not alter shared Identity policies, fix unrelated deletion behavior or provision mail/Google solely for this frontend change.
- Public acceptance is read-only: no account fixtures, token minting, account cleanup or private-book writes. Persistence is demonstrated by stable public seed data through an app restart; existing backend tests retain their private-data coverage.

### Future account work

When a product actually needs accounts, scope login/session/CSRF/recovery together and reuse ASP.NET Core Identity. Choose mail delivery then; MailKit is an SMTP adapter option, not a v1 dependency or a reason to operate an SMTP server. Google, passkeys, account management and passwordless verification require their own justified feature plan. Do not preimplement any of them in this goal.

## 5. API contract and build pipeline

### Settled client-generation choice

Use ASP.NET Core's OpenAPI generator with `openapi-typescript` and `openapi-fetch`. This is the chosen toolchain for this template, not an unresolved comparison or an instruction for the owner to select a generator. Add the packages during implementation; they are not installed by this planning revision.

| Layer | Selected tool / code | Responsibility and output |
| --- | --- | --- |
| API source of truth | C# endpoints, DTOs and actual JSON serialization | Methods, paths, parameters, bodies, statuses, security and wire shapes |
| Schema producer | `Microsoft.AspNetCore.OpenApi` plus `Microsoft.Extensions.ApiDescription.Server` | Deterministic build-time OpenAPI JSON without infrastructure |
| Type generator | `openapi-typescript` as a pinned dev dependency | Generated `paths`, `operations` and `components` TypeScript declarations |
| HTTP client | `openapi-fetch` as a runtime dependency | Native-fetch requests typed from the generated `paths` contract |
| App integration | Small authored transport/error modules and feature functions | Public same-origin reads, cancellation, safe errors and readable feature methods |
| Remote state | Existing chosen TanStack Query | Query keys, caching, invalidation and read lifecycle through the feature functions |

`openapi-typescript` generates types; it does not emit an executable class with one method per endpoint. `openapi-fetch` supplies the executable client, with method/path/parameter/body/response types inferred from those declarations. The schema is a build artifact, not JSON loaded into the browser at runtime. See the [type generator](https://openapi-ts.dev/introduction) and [typed client](https://openapi-ts.dev/openapi-fetch/).

NSwag is a valid alternative and offers a TypeScript Fetch generator for client classes; see its [TypeScript generator](https://github.com/RicoSuter/NSwag/wiki/TypeScriptClientGenerator). It can consume the same OpenAPI document. For this React template, choose `openapi-typescript` plus `openapi-fetch`: transport behavior stays in one small shared module, contract changes stay in generated declarations, and feature adapters fit the chosen Query boundaries. The tradeoff is that readable feature-method names are authored as small adapters instead of generated as client classes. Keep one toolchain rather than generating the same contract through both.

Use ordinary TanStack Query options/hooks over the typed client. No additional hook generator is needed. Author small public feature adapters for catalog/author reads; reference generated request/response types instead of hand-copying wire DTOs. No session provider or mutation framework is needed.

### Schema composition and generation

Use centrally versioned `Microsoft.AspNetCore.OpenApi` and `Microsoft.Extensions.ApiDescription.Server`, consistent with existing .NET packages. Include supported JSON APIs with stable operations, DTOs, statuses, errors and actual security metadata. Exclude HTML/fallback/OAuth/health unless consumed. Describe existing behavior; do not add auth/CSRF infrastructure to fill a schema template.

Explicitly select OpenAPI 3.1 JSON for this .NET 10 toolchain and pin compatible generators. Do not allow a future SDK default to silently change the document dialect. Runtime OpenAPI exposure stays development-only unless separately configured. See [ASP.NET Core generation/version configuration](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/aspnetcore-openapi?view=aspnetcore-10.0).

Generate with an opt-in target/script. Detect the documented generator entry assembly `GetDocument.Insider` before side-effectful composition. Register real handlers and enough service types for accurate binding, using metadata-only setup. Generation invokes startup; see [Microsoft's explanation](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/aspnetcore-openapi?view=aspnetcore-10.0#customize-runtime-behavior-during-build-time-document-generation).

Disable automatic document generation on ordinary builds unless the explicit extraction workflow enables it. Schema extraction must not unexpectedly become part of every `dotnet build`, application startup or frontend HMR cycle. A backend contract edit requires explicit regeneration; a cosmetic React edit does not.

Schema mode must not connect to DB/Redis, migrate/seed, persist keys, start subscribers, contact telemetry/mail/OAuth or require secrets. Use deterministic metadata settings; no broad development-mode bypass of production safeguards. Prove extraction with unavailable infrastructure.

Generate and commit:

```text
BlazorAutoApp.React/api/openapi.json
BlazorAutoApp.React/app/api/generated/schema.d.ts
```

Never hand-edit generated files. Keep UI-only view models separate, remove environment-specific server URLs and ensure stable ordering. Generated types do not provide runtime validation; backend validation remains authoritative. Do not use type assertions to make a response match an incorrect schema.

Add a minimal `BlazorAutoApp.React/package.json` and its lockfile for contract tooling in P4, before the UI scaffold in P5. P5 extends that package rather than creating a second frontend package/lockfile. Blazor's existing stylesheet tooling remains separate; do not merge unrelated lockfiles just to satisfy the React setup.

Generation derives the document from the selected backend composition, not from a running deployed URL. Generate the common JSON book contract from React backend composition. Existing protected book operations may remain in the schema, with their actual security metadata; this does not add a React private-book UI. Shared endpoint shapes match Blazor. No account APIs or provider-dependent inventory are generated.

### Wire-format and endpoint-metadata contract

Declare actual runtime behavior in the schema. Typed return values help describe success responses; endpoint filters, authorization, rate limiting, antiforgery and exception handling can add responses outside the handler's return type. Add shared metadata for those responses where appropriate and verify it against real HTTP calls. Metadata annotations alone do not implement validation or change what the handler returns. See [ASP.NET Core endpoint metadata](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/include-metadata?view=aspnetcore-10.0).

| Concern | Required contract |
| --- | --- |
| Operations | Preserve existing stable book names (`ListBooks`, `GetBook`, `CreateBook`, `UpdateBook`, `DeleteBook` and author equivalents); no invented account operations |
| Parameters | Actual casing, path/query/header location, required status, nullability, defaults and bounds; use schema path names rather than interpolating URLs by hand |
| JSON names | Match configured `System.Text.Json` wire names; keep lower-camel-case keys when that is the actual server behavior |
| Required versus nullable | Distinguish missing properties from explicit `null`, including optional author/URL; do not infer optionality from a UI form |
| Validation | Describe supported constraints, but retain server enforcement for custom validators such as the existing optional absolute HTTP/HTTPS book URL rule |
| Numbers | Existing 32-bit book IDs are numbers. For future `long`/`decimal` fields, choose an explicit safe wire representation before exposing values JavaScript cannot represent exactly |
| Dates and identifiers | JSON dates/UUIDs remain strings in generated types; parse/display dates deliberately in view models, with no global JSON reviver |
| Enums | Preserve the actual numeric or string serialization; do not enable a global enum converter just to change generated output |
| Responses | Explicit success statuses/bodies, `204` with no JSON, validation/problem responses, bare `401`/`403`, `404`, `415`, `429`/`Retry-After`, and relevant safe server failures |
| Non-JSON operations | Downloads explicitly declare their media type/body; OAuth redirects are browser navigation and excluded from typed JSON operations |
| Security | Public reads are anonymous; existing protected operations retain actual cookie/security requirements. Do not claim a new `X-CSRF-TOKEN` contract exists. No cookie/token values, credentials or deployment origins appear in the schema. |

Use named DTOs and safe ProblemDetails extensions for the actual supported operations. Ensure distinct DTOs do not accidentally share a conflicting generated schema name. Keep public DTOs separate from EF/Identity entities so database/navigation/secret fields cannot leak through schema generation.

### Shared client and error boundary

Use `app/api/client.ts` for configured `openapi-fetch`, `app/api/errors.ts` for normalized API failures, generated declarations under `app/api/generated`, and feature-level adapters/query definitions under the existing feature boundaries. UI components do not construct raw fetch calls or hand-copy request/response interfaces. A type alias referencing generated `components` is acceptable; a duplicate handwritten wire DTO is not.

Illustrative browser-side call, using the shared configured `api` instance:

```ts
function getPublicBookRequest(id: number, signal?: AbortSignal) {
  return api.GET("/api/author-books/{id}", {
    params: { path: { id } },
    signal,
  });
}
```

The path, path parameters and returned body are checked from the generated contract. Feature query functions unwrap this result through the shared error boundary. Do not return an error result as successful TanStack Query data: HTTP failures must become the app's typed errors, while cancellation remains cancellation. Do not assume `fetch` throws for `4xx`/`5xx`. See [client middleware/error behavior](https://openapi-ts.dev/openapi-fetch/middleware-auth).

The transport contract is:

1. Use same-origin relative public API paths with `credentials: 'omit'`. Vite proxies them in development. No demo hostname, auth token or secret is embedded in the client.
2. Pass caller AbortSignal and preserve cancellation. Do not toast normal navigation cancellation or retain stale route results.
3. Normalize safe ProblemDetails/field errors, status, bounded `Retry-After` and correlation ID. Handle empty/malformed/non-JSON responses without exposing raw upstream HTML or losing the status.
4. Throw normalized failures to Query; do not cache an error result as success. Distinguish unavailable network, invalid response and cancellation. Existing generated write methods are not used by the public UI.
5. Implement no auth/token refresh middleware, private Query cache, browser session protocol or account download/export path.

Prefer small explicit normalization helpers and `openapi-fetch` middleware over a generic homegrown client framework. Validate external/error boundaries as needed; do not add a second generated runtime-validation system for every server DTO without a concrete requirement.

### Regeneration and drift workflow

Define exact implementations during P4/P5, with these stable user-facing command meanings from `BlazorAutoApp.React/`:

| Command | Required behavior |
| --- | --- |
| `npm ci` | Install the committed lockfile's tools; no schema fetch, production service access or application startup |
| `npm run api:generate` | Orchestrate isolated C# schema extraction plus local type generation, then deliberately update both committed generated files |
| `npm run api:check` | Regenerate both files into owned temporary output, compare with committed files, print a concise drift summary and fail without rewriting them |
| `npm run typecheck` | Generate Router route types and run the TypeScript compiler, including API call sites and meaningful compile-time contract cases |

The local generator step is equivalent to the installed lockfile tool's `openapi-typescript api/openapi.json -o app/api/generated/schema.d.ts`; invoke the local package through an npm script. Never rely on `npx` downloading an unspecified generator or on a globally installed version. See the [generator CLI](https://openapi-ts.dev/cli).

The full regeneration command must work before a React bundle exists and must not reuse an old compiled host. Isolate its metadata-only build output from normal builds and clear only validated task-owned temporary paths. Sort deterministically and omit timestamps, environment-specific server URLs and absolute build paths. Normalize line endings intentionally for Windows/Linux; never conceal a changed schema by suppressing arbitrary diff sections.

CI proves a stale schema or declaration causes `api:check` to fail, verifies that the check leaves expected files untouched, and runs it with DB/Redis/provider access unavailable. In P5, add small typecheck cases for an invalid path, wrong ID type, missing required body and nullable response handling. Pair compile-time checks with representative real HTTP response/request checks; generated types are only as accurate as the server metadata.

When changing an endpoint: update C# behavior/metadata and tests, run `api:generate`, inspect schema/type diffs, fix affected feature adapters/UI, then run `api:check` and typecheck. Commit source and generated outputs in the same PR. A backend-only edit can require contract regeneration even when the persisted production frontend is Blazor.

For ordinary template-internal additive changes, use review plus schema diff and compile/tests rather than adding a separate API compatibility service. A breaking wire change must account for open tabs from the previous release: preserve compatibility for the documented rollout window or provide bounded reload/recovery behavior without retrying writes. SDK/schema-generator upgrades get a distinct readable diff and the same contract checks.

### Build ordering

```text
validate profile
install selected frontend tooling from the lockfile when required
build C# metadata without frontend assets
generate OpenAPI without infrastructure
generate/check TypeScript types
typecheck/lint/test/build selected frontend
publish C# with selected staged assets
build/smoke final image
```

Add a clearly named asset-free build flag for contract/dev orchestration only; never permit incomplete production publish. Missing React output fails publish with instructions. Docker/documented build command orchestrate the sequence. No cycle where schema generation needs React output that needs schema.

Final publish must rebuild/evaluate the selected static-file inputs after assets are staged. Do not publish with `--no-build` against the earlier metadata-only output. Verify that all required build scripts are present in Docker context and that contracts are regenerated from the same backend source revision as the shipped image.

Ordinary .NET/Blazor builds remain independent of npm. Development consumes committed types and explicit regeneration; CI compares them against current C# contracts. Update contract/types in the same PR.

Use public-query defaults `staleTime=60_000`, `gcTime=300_000` and focus/reconnect refetch. Retry at most once for a network error or `502/503/504`; never blindly retry `400/401/403/404/429`. Show bounded `Retry-After` and explicit retry where appropriate. No persisted cache or auth/session query is needed. Review [Query defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults) and test the explicit overrides.

### Code quality rules for implementation review

- Keep TypeScript strict and lint authored code for explicit `any`, floating promises and unsafe assertions. Narrow unknown error/extension data at the boundary. Do not repair a broken schema with `as unknown as`, `@ts-ignore`, disabled strictness or copied DTOs. Dedicated negative compiler cases may use `@ts-expect-error` with a reason and must fail if the expected error disappears.
- Keep route modules thin, feature adapters named for user operations, shared UI presentational, and server modules separated by capability. Avoid a giant auth component/client/endpoint file, dependency-injection service locator, catch-all action dispatcher or a generic CRUD framework for one reference feature.
- Server authorization and owned-data selection stay server-side. Capability flags control honest availability, never permission checks. Do not trust React user IDs, email matches, return URLs, timestamps or success indicators as authentication.
- Avoid effect-driven writes, unconditional mutation retries, optimistic destructive account actions, credential-bearing query strings, secret-bearing mutation caches and swallowed cancellation/errors. Inspect dependency arrays and Strict Mode behavior; cleanup aborts/invalidates stale work without replaying it.
- Add tests for observable behavior and security boundaries. Do not turn required assertions into snapshots, skip suites to get green CI, weaken cookie/CSRF policy for tests, or replace actual cookie tests with fake auth headers.
- Keep abstractions proportional: one transport, one QueryClient, existing backend services and deployment/backup tooling. Add a package or abstraction only when a concrete repeated requirement justifies it.

### Repository and release conventions

- Pin compatible Node, package-manager and frontend dependency versions; commit one npm lockfile. Use `npm ci` in CI/Docker. Keep central .NET versions and the existing SDK policy. Evaluate stable releases at P0 rather than pinning a stale major in this document.
- Keep feature logic under `app/features`, route orchestration under route modules, API transport/query definitions under their documented boundary, and shared presentational controls under `app/components/ui`. Do not hand-copy server DTOs or place business authorization in React.
- Check in generated schema/types, not `node_modules`, route type output, `build`, local certificates, coverage, Playwright traces, or secret-bearing fixtures. Define precise ignore/context rules and human-readable regenerate/check failures.
- Provide one documented command per operation: dev, contract regeneration, typecheck, lint, test, production build and image build. Scripts return nonzero on missing prerequisites and explain the next action. Do not silently start Docker, perform migrations on a live node, or dispatch deployment from a frontend build.
- React's stylesheet is built from its own source and shared design inputs deliberately included for React. A React build must not overwrite the committed Blazor stylesheet. Rebuild that stylesheet whenever changed Razor classes or Blazor style inputs require it.
- Keep authored application code, schema generation, selected assets and migration bundle tied to the same source revision. Add frontend/profile fields through a versioned release-manifest change; update producer, validators, fixtures, audits and all deployment consumers together.
- Record profile, source commit, image digest, schema/type fingerprint and frontend asset-manifest fingerprint in protected release evidence as appropriate. A small public version response may expose only non-sensitive identity such as profile and short commit; never use a writable runtime flag as proof of the baked profile.
- Run dependency vulnerability/license review across direct and transitive runtime dependencies. Resolve exploitable high/critical findings before release or record a reviewed, time-limited exception with rationale and follow-up. Do not use broad audit suppressions or unreviewed automated major upgrades.

## 6. Granular implementation phases

Required sequence: P0, P1, P2, P3, P4, P5, P6, P7, P7a, P7b, P9. P8 is explicitly deferred and is not part of this goal. Read-only target preparation may overlap local work; no host/public mutation occurs before ownership and authorization checks. Missing live access blocks only P7a/P7b/P9 dependent checks, not independent local implementation.

Each packet is one reviewable unit; related small packets may share a PR. Add behavior, tests, affected audit rules and docs together. Run the local gate before push, require `build-test-push` on the exact PR head, merge normally and record green main evidence. Do not implement the whole plan in one PR. Build/test sequentially in each checkout, with isolated profile output.

| Packet | Prerequisites | Work and files | Required exit evidence |
| --- | --- | --- | --- |
| P0.1 | None | Read rules/requirements/runbooks, inspect main and dirty work, create clean task worktree | Baseline, task ownership and no unrelated changes imported |
| P0.2 | P0.1 | Document public-only scope in `docs/FrontendProfiles.md`; inventory route/build/release callers and pin compatible stable tool versions | Requirements map, explicit no-accounts policy and private target record |
| P1.1 | P0.2 | Add `frontend-profile.txt`, resolver and `Directory.Build.props` selection | Missing/empty/invalid choices fail; one effective choice everywhere |
| P1.2 | P1.1 | Split frontend composition, UI state, common Identity and current-user implementations | Default Blazor behavior preserved; React backend needs no Razor UI services |
| P1.3 | P1.2 | Condition host project items/references/assets; add static placeholder and safe navigation handling | Both clean publishes; no Blazor client/WASM assets in React; stale-output switches and reserved-path/HEAD/404/traversal tests |
| P2.1 | P1.3 | Verify public read APIs and existing private-route authorization; preserve current cookie/CSRF callers | Anonymous public responses; protected reads/writes denied without changes; no HTML API redirect/fallback leak |
| P3.1 | P2.1 | Establish account-free React route/asset/seed contract and HTTP security policy | No account UI/API/callbacks, no mail/provider requirement, no default privileged production seed |
| P4.1 | P3.1 | Add centrally versioned OpenAPI packages and side-effect-free metadata entry path | Actual book DTO/status/security metadata; extraction without DB/Redis/mail/secrets or startup side effects |
| P4.2 | P4.1 | Add minimal React package/lock, committed schema/types and `api:generate`/`api:check` scripts | Deterministic Windows/Linux output; check fails on drift without editing expected files |
| P5.1 | P4.2 | Extend package into Router SPA/Tailwind/strict TS scaffold with lint/unit tools and HTTPS dev scripts | Fresh Vite-to-C# dev without prebuilt assets; complete static production build |
| P5.2 | P5.1 | Add typed public transport/error adapters and one QueryClient | Compile-time contract negatives; cancellation/empty/error/non-JSON behavior; no auth/CSRF bootstrap |
| P5.3 | P5.2 | Build public shell/catalog/author-details and all read states | Useful sample data, stable links, keyboard/mobile layout and initial bundle baseline |
| P6.1 | P5.3 | Complete route titles/focus, accessibility, safe errors, navigation/refresh/back and responsive polish | Public browser/component checks; no account links or private UI; no effect-driven writes |
| P6.2 | P6.1 | Extend existing C# Playwright harness for public React and preserve Blazor/simulation regression | Required suite counts, Chromium broad flow, Firefox/WebKit smoke and public-data isolation |
| P7.1 | P6.2 | Docker/context, selected clean assets, local/Compose orchestration and cache/header policy | Both final image smokes, public/deep links/HEAD/404, no inactive assets or Node runtime |
| P7.2 | P7.1 | Version release frontend/acceptance metadata; update producer, validators, every CD consumer and negative fixtures together | Profile/source/digest mismatch rejected before migration; legacy verified Blazor treatment explicit |
| P7.3 | P7.2 | Split `Test-DeployedSite.ps1` and all callers into trusted Blazor and `ReactPublicV1` acceptance | React public checks create no accounts/data; Blazor keeps its existing checks; no false shared account requirement |
| P7.4 | P7.3 | CI aggregate, profile isolation, affected audit replacements and all-target generated-config/syntax checks | Both profiles actually validated; required suites cannot pass by skip; only persisted selection published on main |
| P7.5 | P7.4 | Full local gate, dependency/security review, quality budgets and upstream release | Exact-head PR green, merge SHA and successful main validation/publishing recorded |
| P7a.1 | P7.5 | Verify native node/DNS ownership, capacity, app identity, free ports/subnet and sibling baseline | Private collision-free settings, simple backup/recovery status and scoped authorization before mutation |
| P7a.2 | P7a.1 | Independent downstream repo bootstrap/config PR, own image and app-specific runner | Actions-disabled verified seed; exact-head config PR; own green main-push React release |
| P7b.1 | P7a.2 | Owned public setup and one exact-SHA LocalSingleNode dispatch | CI/CD run/attempt, migrations/readiness, running digest/profile and normal HTTPS checks |
| P7b.2 | P7b.1 | Independent public browser/HTTP acceptance, one scoped app restart and sibling smoke | Public catalog/details/navigation/headers; seed data survives restart; no test accounts; Blazor still healthy |
| P9.1 | P7b.2 | Fresh-clone walkthrough, final operations/status, short observation and docs reconciliation | Documented commands and release/update/recovery path; all required R01-R16 evidence |
| P9.2 | P9.1 | Final evidence/docs PR and handover | Merge/main CI recorded; approved public release verified; no required blocker |

### Phase details and hard gates

**P0 - Inventory.** Re-read current merged deployment work; do not import this checkout's unrelated pending public-deployment changes. Inspect available local SDK/Node/Docker/browser prerequisites and current exact package versions. Pin compatible stable dependencies and one npm lockfile. Do not require access to a live provider/node before starting P1-P7.

**P1 - Profile proof.** Preserve one host and shared backend. Inspect evaluated `Compile`, Razor, content and static-web-asset items rather than removing files blindly. If conditional isolation still forces inactive dependencies into React, use one small Razor Class Library for Blazor UI, the preselected fallback; document the SDK evidence and pass the same gates. No duplicated backend/second host/widespread `#if`. Prove missing API/health/assets/framework/auth/callback paths, unsafe methods and non-HTML requests are real failures. Unknown normal SPA navigation may return HTTP 200 with a client not-found screen; document that limitation.

**P2/P3 - Public boundary.** Reuse author-book read APIs and public seeds. Keep user books private. No account endpoints, new Identity policy, unique-email migration, mail adapter, provider settings, reauthentication protocol or deletion fix. Preserve existing authenticated Blazor/WASM/simulation behavior and test it. Enforce the section 4 public security contract.

**P4 - Contract proof.** Install tooling before generation; extraction must work before React assets exist. Normal .NET builds remain npm-independent. Commit source/schema/types together; prove stale-file failure and real-handler wire agreement. Never publish the metadata-only output as an application.

**P5/P6 - Application proof.** Implement one public vertical slice completely. Use public generated types, local UI state, one QueryClient and clear read error handling. Define `typecheck`, `lint`, `test`, `build`, `api:generate`, `api:check` and documented start commands. Typecheck includes Router type generation and negative call-site cases. Reuse existing C# Playwright rather than adding a duplicate JavaScript E2E stack. Explicitly select React for its new public fixtures; retain Blazor selection for existing account/Auto/WASM/simulation fixtures. Define required suites/counts per profile so a global profile switch neither breaks Blazor tests nor hides missing React coverage behind skips. No account feature scaffold.

**P7 - Release proof.** Docker resolves profile once, skips React npm in Blazor builds and stages only selected assets. Missing React output fails production publish. Extend all manifest consumers before selecting the release; do not defer provenance/acceptance changes until installation. PR validation builds/smokes both profiles, main publishes only the repository's selected profile. Retain LocalCluster/Cloud checks without dispatching them. Update changed audit behavior by replacing assertions, never deleting coverage.

**P7a/P7b - Public proof.** Follow sections 8/9 and current native-node runbooks. Keep independent image/data/keys/ports/roots and preserve the existing Blazor demo. Use verified main release/digest and existing scoped authorization. Record a dispatch immediately; after a watcher interruption inspect/resume that run rather than dispatching again. Verify LAN plus independent public browser access with normal certificate validation. No registration/cleanup flow is required or allowed by React public acceptance.

**P8 - Deferred roadmap.** Accounts, private-bookcase UI/CRUD, email delivery/recovery, Google, passkeys, export/deletion and account management are outside v1. Product-specific public prerendering is also later work. Reopen only for a concrete product requirement and explicit scope instruction. Do not execute old P8a-P8f tasks from earlier revisions.

**P9 - Completion.** Verify fresh-clone dev/build/selection/generation/deployment documentation, simple diagnostics/backups/recovery and final observation. Evidence-only docs commits may follow the last deployed application commit; record both. Any runtime/build-contract fix needs a new verified image and renewed affected public checks. Finish only after required merges/main CI and public evidence exist.

## 7. Required verification and acceptance

### Requirement traceability

| ID | Required v1 outcome | Phase / evidence |
| --- | --- | --- |
| R01 | One persisted profile with isolated dependencies/assets | P1/P7; invalid choices, clean publishes/images, stale-output switching |
| R02 | Safe same-origin static hosting and routing | P1/P5/P7b; direct links, refresh, HEAD, real backend/asset/auth 404s |
| R03 | Anonymous public data and preserved private authorization | P2/P3; anonymous GETs, denied private reads/writes, no login HTML or fallback leak |
| R04 | Useful public reference feature | P5/P6/P7b; actual catalog/author data, states, navigation and no user-book exposure |
| R05 | Reproducible typed API contract | P4/P5/P7; unavailable-infrastructure generation, drift failure, real-wire/compiler cases |
| R06 | Coherent accessible UI and browser support | P5/P6/P9; keyboard/mobile/reflow, axe, screen-reader spot checks, browser matrix |
| R07 | Honest rendering, cache and performance | P5/P7/P9; SPA limits, actual headers, bundle and repeatable Lighthouse measurements |
| R08 | Intentionally absent React account area | P3/P6/P7b; no account menu/registration/settings or active auth routes, no SMTP/provider prerequisites |
| R09 | No speculative account framework | P3/P9; no new auth/session store, email/challenge service, account secrets or unused packages |
| R10 | Immutable release provenance across supported targets | P7/P7a; producer/validator negatives, exact SHA/run/attempt/digest/profile and audits |
| R11 | Independent public React demo beside Blazor | P7a/P7b; scoped CD, running identity, independent HTTP/browser and sibling checks |
| R12 | Production configuration/security isolation | P2/P3/P7a; hosts/proxies/headers, separate data/keys/cookies, no public default admin |
| R13 | Persistence and simple operations | P7b/P9; public seed data through restart, connector and existing backup/doctor status, recovery command |
| R14 | Fresh-clone usability and maintenance | P0/P7/P9; profile/dev/build/generation/update/extension/deployment walkthrough |
| R15 | Existing Blazor and all deployment targets preserved | P1-P9; Auto/WASM/Identity/simulation regression and profile-aware target validation |
| R16 | Reviewable delivery and resumable evidence | Every phase/P9; local gates, exact-head checks, merges, main CI and private public record |

### Test layers and execution

- Unit/component: typed errors, query behavior, public UI states and navigation; deterministic Vitest/React Testing Library.
- ASP.NET integration: actual public handlers, existing protected-route denial, real wire shapes and host/profile routing. Preserve existing real-cookie Blazor tests; React needs no signin fixtures.
- Host/publish/image: both clean profiles and both PR images, no inactive UI/runtime, correct headers and metadata-only isolation.
- Browser: existing C# Playwright with explicit `RUN_E2E=1` where required. Broad Chromium public flow on relevant PRs; Firefox/WebKit smoke before release. Record discovered/executed/skipped counts.
- Public: read-only LAN/HTTPS HTTP and independent browser tests of the verified release. No accounts, private writes or cleanup helpers.
- Operations: existing status/doctor/backups and one app restart. No required reboot/restore/rollback drill unless changed risks justify it.

`build-test-push` must aggregate both profiles and required deployment/script validation. Failed/cancelled/absent/zero-test/unexpectedly skipped suites cannot pass acceptance. No SMTP, Google, live credentials or physical passkey device is a CI/release prerequisite. Preserve existing untrusted-PR permissions and self-hosted-runner protections.

### Local gate

Follow the full current [docs/Test.md](../docs/Test.md#local-gate), including affected script checks. Familiar starting commands are:

```text
dotnet format BlazorAutoApp.sln --verify-no-changes
dotnet build BlazorAutoApp.sln --configuration Release
dotnet test BlazorAutoApp.sln --configuration Release --no-build
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
```

Run React `api:check`, `typecheck`, `lint`, `test` and `build`, then affected profile/image/browser checks. Build/test sequentially, isolate profile output and require Docker where integration tests need it. Never reuse another profile's `--no-build` output. Record blocked checks truthfully; continue independent checks without counting a blocked gate as success. Planning edits are not application-test evidence.

### Quality targets

Record harness, page/dataset, browser/Lighthouse version, compression, throttling and cold/warm-cache conditions. Public initial JS target: at most 200 KiB gzip across required chunks; CSS: at most 40 KiB gzip. Median public-page Lighthouse performance target: at least 90 across three runs under each documented desktop/mobile configuration. Lab mobile LCP target: at most 2.5 s; CLS: at most 0.1. Record measurements and any evidence-backed adjustment before release; never silently raise budgets. Growth above 10% of baseline needs review even within the hard cap. Do not label lab results field Core Web Vitals.

Target WCAG 2.2 AA for delivered screens: no unresolved serious/critical axe findings plus manual keyboard, focus, labels, announcements, contrast, reduced-motion, 200% text zoom, 320 CSS-pixel reflow and screen-reader spot checks. Automated scores alone do not prove conformance. Browser support covers Chromium/Firefox/WebKit and mobile viewports. App restart recovery target is initially five minutes, measured rather than assumed.

## 8. Public demo architecture and execution

### Two apps and two release sources

The upstream template keeps `frontend-profile.txt=BlazorAuto`. Create an independent downstream React demo repository under the operator's current account, initialized from the upstream's verified main history, and commit `frontend-profile.txt=React` through its configuration PR. Its own main push CI validates both profiles and publishes its selected React image to its own registry repository. This preserves the one-file template contract and existing release provenance without adding a special dual-profile publishing pipeline just for the demo.

The existing Blazor deployment continues to consume its current release source. The React app consumes the downstream repository's verified main release. Never install a PR image, a local override build, a mutable `latest` tag, or the upstream Blazor image as the React release. Do not toggle the upstream selection to refresh one demo and then toggle it back.

Keep downstream customization small: selected frontend, app/image identity and intended deployment configuration. Retain an `upstream` remote and sync upstream main through a normal downstream branch/PR, preserving its React profile and identity. Resolve conflicts explicitly, run the downstream local gate and exact-head required check, merge, wait for successful main publishing, then deploy its immutable digest. Record the upstream merge commit and downstream release commit; they can differ. Use ordinary history-preserving merges, never a destructive reset or forced main rewrite.

This is the default for the required demo, even if GitHub's fork button is available. It avoids assumptions about own-account forking, template status and cross-fork PR permissions. Generic third-party forks remain supported template consumers. No new release channel is needed.

### Downstream repository bootstrap: avoid the CI chicken-and-egg

Perform these steps only during authorized execution. The new goal prompt covers this scoped repository setup when the owner runs it; the present planning turn does not perform it.

1. Verify the authenticated GitHub identity, upstream remote/default branch, completed P7 merge and green main release. Read the intended downstream owner/name from the private record. Default to a new private demo repository, with no README/license initialization because upstream history already supplies them. If the chosen name is occupied, verify whether it is this task's recorded repository; otherwise choose a collision-free suffix and record it. Never adopt/overwrite an unrelated repository. Private source/package visibility does not prevent a public application; retain authenticated image pulls through the existing deployment path.
2. Create the empty repository without pushing. Immediately disable its Actions through GitHub's repository Actions-permissions API and verify the disabled state. No app secrets, inherited runner credentials or deployment variables are copied from upstream. See the [official Actions permissions API](https://docs.github.com/en/rest/actions/permissions#set-github-actions-permissions-for-a-repository).
3. In a separate clean clone of upstream main, verify the selected seed SHA equals the recorded green P7 main commit. Keep upstream as the `upstream` remote and add the new repository as `origin`. Push only that existing verified commit to the new repository's `main`. This one initialization push contains no new code changes; subsequent changes use PRs. Never use mirror push, force push, all-ref push or copy this controller's dirty checkout. Set/verify the default branch is main. Actions remain disabled, so this seed cannot publish the upstream image or dispatch anything.
4. Prepare a downstream configuration branch/PR: React selection, unique app/internal identity, own lowercase registry owner/image, migration-bundle identity, target settings and README identity. Keep internal project/namespace names and all upstream deployment/test folders. Enable only `localsinglenode` for live use. CI may still read common/LocalCluster identity; change the required identity inputs consistently without inventing a partial single-node pruning exercise. Keep actual node facts/secrets in the runbooks' private configuration. Run the full local gate and React checks before pushing the configuration branch.
5. Establish the app-specific CI runner and repository variables through the native-node runbook before enabling Actions. Verify label and native hostname, capacity, one-service registration, Docker/tool prerequisites and no theft of the existing Blazor runner. If initial runner registration needs the operator's native-node sudo command, prepare its concrete inputs first and keep this dependent setup pending; implementation can continue elsewhere. The copied main workflow must be inspected to confirm PR validation reads checked-out PR configuration and cannot publish; do not assume this from its name.
6. Set least-privilege workflow/package permissions and environment/deploy inputs through the existing setup scripts. Enable Actions, then trigger the configuration PR's normal validation by pushing its final locally checked head. Require the actual `build-test-push` check on that exact head. Enabling Actions does not retroactively validate the seed, and a manual CI dispatch is not main-push release provenance. Use the normal PR path; do not merge a failing configuration PR to bootstrap CI.
7. Merge the green configuration PR. Require its own successful main-push validation/publishing, own image digest, new profile manifest and migration artifacts. Validate that no upstream package was overwritten. Configure branch protection if the account supports it; enforce exact-head checks in the execution workflow regardless, without treating unavailable paid settings as an implementation blocker. Only this configured downstream main release is eligible for P7b.
8. Rehearse one history-preserving upstream synchronization through a downstream PR when a real upstream update exists. Before final acceptance, ensure all required upstream v1 merges are ancestors of the deployed downstream release and its React selection/identity remain intact. Do not create a meaningless code change merely to manufacture a sync rehearsal.

### Private installation record

Before installation, create/update a protected private record with these values. Use ignored `Plans.local/ReactFrontendProfile.demo.md` for non-secret target intent and coordination, and the runbooks' protected files for credentials. Do not copy real installation values or tokens into this tracked plan.

| Group | Required record |
| --- | --- |
| Intent/authorization | Selected native node and public hostname, app purpose, operator instruction/scope, authorized mutations and maintenance actions |
| Sources | Upstream/demo repository URLs, app slug, registry repository, branch, selected profile and required environment |
| Native host | Verified hostname/OS, existing app markers, current running releases, runner labels and current ownership |
| Isolation | Deploy/backup/secrets roots, Docker project/subnet/volumes, database/Redis, Data Protection application identity/key ownership |
| Networking | App/database/Redis/LAN/public-origin ports and bindings, LAN hostname if needed, proxy trust, public hostname and HTTPS origin |
| Cloudflare | Account/zone, owned tunnel/DNS IDs, unique tunnel name, state/config references and credential file locations without credential values |
| Release | Main SHA, successful CI run/attempt, manifest version/profile, image digest, migration bundle hash and migration IDs |
| Recovery | Existing backup/last-success, previous compatible release if one exists, migration compatibility, existing runbook/commands and service ownership |
| Verification | CI/CD run IDs, controller/browser/time, acceptance results, evidence locations, observation and cleanup status |

Do not assume the requested node spelling matches its native hostname, or that the proposed DNS name is unused. Verify both before writing repository inputs or DNS. The user-selected React hostname is the default; change it only for a verified conflict or owner instruction. Preserve the existing Blazor hostname.

### Host readiness and isolation

Use [HowToDeployLocalSingleNode.md](../Deployment/LocalSingleNode/HowToDeployLocalSingleNode.md), [PublicSetup.md](../Deployment/LocalSingleNode/PublicSetup.md), and, only on the intended native node, [AgentSetup.md](../Deployment/LocalSingleNode/AgentSetup.md). Verify their current merged instructions first. Distinguish initial infrastructure installation checks from frontend update acceptance: the current public guide includes restart/reboot drills, and its update path must reflect the owner's simple-operations scope in section 9. A controller session discussing the node does not authorize bootstrapping the controller as a node. Reject Windows/WSL node bootstrap.

- Inspect CPU, available memory, disk, Docker storage, current workloads and runner concurrency. Include PostgreSQL/Redis and CI build peaks in capacity planning; two runtime apps fitting at idle does not prove a local build is safe.
- Use unique app slug, image, deployment/backup/secrets paths, Docker project, subnet, published ports, database/Redis and backup service names. Current LocalSingleNode collision logic requires distinct requested listeners, including the LAN HTTP port; do not assume the second app can reuse port 80.
- Verify shared Caddy includes and current app/public ownership markers before writes. Use the deployment scripts for shared services. Never replace a foreign root config or install a second shared service to bypass ownership checks.
- Keep database/Redis/app backend ports bound as required by the runbook, with public-origin ingress on its dedicated loopback listener. Public exposure uses the app's connector/site; database/Redis, metrics and runner control stay private.
- Register/verify a correctly labelled repository runner without stealing the existing app's registration. Per-repository Actions concurrency does not serialize two repositories on one node; retain the host's shared deployment lock and bound CI resource use.
- Check network/subnet overlap, stale app identity and nonempty roots. Fail on foreign resources; never adopt or delete them automatically.
- Preserve independent app data and credentials. Shared host access remains root-equivalent according to the runbook; separate app identities do not create strong isolation against a privileged host compromise.

### Release and acceptance contract

Use release manifest schema v2 with required `frontend_profile` and `acceptance_profile`: `React` maps to `ReactPublicV1`, and `BlazorAuto` maps to `BlazorAutoV1` retaining existing Blazor acceptance. Bind fields to source selection and baked assembly/image metadata; reject unknown or mismatched pairs. No runtime flag may enable unsupported account acceptance. Update producer and all validators/CD consumers together. Legacy manifest v1 may support a previously verified Blazor rollback if safely identified; it never describes React. New releases require v2. Preserve existing repository, main ancestry, successful push CI, run/attempt, digest and migration checks.

Before migrations or service replacement, verify the release profile equals the intended app's profile and inspect the pulled image by digest. Compare baked identity with the running service after deployment. Do not select acceptance behavior from hostname, a client-supplied header, or whichever script happens to find assets. A misconfigured expected profile is a deployment failure.

`Scripts/Test-DeployedSite.ps1` gains a validated profile parameter supplied by trusted release/deployment inputs, plus the trusted acceptance profile. Common checks retain readiness, protected API denial, release identity and applicable security headers. Blazor checks retain its real forms/assets/transport, account/default-credential and cookie assertions. React checks cover public JSON/data, actual React assets and inactive auth routes; they must not create a session or inherit Blazor account assertions. Browser acceptance remains necessary because an HTTP script cannot prove the UI works.

`ReactPublicV1` acceptance performs only public reads and negative authorization/routing checks. It must not register/login/delete users, write private books, bootstrap CSRF sessions or require mail/provider secrets. Preserve existing Blazor acceptance behavior in its separate branch. A shared caller must not run Blazor account assumptions against React or create disposable accounts before selecting the correct branch.

### Public setup sequence

1. Revalidate the private target, existing Blazor baseline, source identities, green CI, digest, schema compatibility, backups and applicable operator authorization. If authorization is absent, prepare all independently reviewable work first and request only the concrete remaining action.
2. Through the existing runbooks, provision/reconcile only the React app prerequisites and runner. Avoid reinstalling or replacing shared services that already satisfy the node contract. Record any operator-required native-node action without assigning automatable configuration work to the owner.
3. Inspect Cloudflare DNS/tunnels/ingress and Caddy/listeners. Use the public setup script with the unique private config/state and protected token files. Keep the dedicated tunnel/connector design required by LocalSingleNode; do not attach to the existing Blazor connector as an unrelated replica.
4. Reconcile the intended repository's public variables/secret and native node using the configuration script. Foreign DNS/tunnel/port/identity conflicts stop mutation. Keep the script's read-only/idempotency check as separate evidence.
5. Dispatch `CD - Deploy LocalSingleNode` from verified main for the exact target SHA once. Record the run ID/attempt immediately. A timeout or disconnected watcher is not evidence that dispatch failed; inspect/resume the same run before considering a retry.
6. Require successful provenance validation, migrations when required, scoped stack deployment, connector readiness, LAN checks, public checks and running digest/profile match. Retain the normal shared lock; never reclaim it automatically.
7. From an independent controller, verify normal public certificate validation and real browser behavior. Check edge cache/Access/challenge policies if the public response differs from the origin. Never disable certificate verification or bypass a broken public path to claim success.
8. Run the read-only React public checklist, compare existing Blazor availability/identity, and record results. No account/data fixtures need cleanup. Repair defects through PR/local-gate/exact-head CI/green main before deploying a replacement.

### Public browser acceptance checklist

| Area | Required proof |
| --- | --- |
| Release | Expected downstream repository, SHA/digest, baked React profile and `ReactPublicV1` contract |
| Public app | Normal HTTPS, catalog/author details from actual API data, direct links, refresh/back/forward, responsive layout and loading/empty/error/retry behavior |
| Accounts | No login/register/account settings/private-bookcase UI; inactive account/callback routes fail instead of rendering Blazor or SPA success |
| Security | Private API reads/writes denied anonymously; no private/user data in public output; correct headers/proxy behavior and no exposed default admin |
| Assets/browser | Correct React assets, no Blazor framework or Node runtime; missing assets/API paths fail correctly; supported browser smoke/accessibility and performance |
| Operations | One scoped app restart, public seed data persists, connector healthy and existing backup/doctor status checked |
| Existing app | Blazor public smoke and independent resource/cookie/data identity remain intact |

Record actual results, timestamps, browser versions and private evidence locations. Public tests need no account fixtures or cleanup. Never replace a public-path failure with insecure certificate settings or direct-origin-only evidence.

## 9. Simple operations and update behavior

Use the repository's existing maintenance tools and runbooks. Required baseline: deployed services are healthy, data survives one app restart, the existing backup setup/status is checked, and the previous compatible release plus recovery commands are recorded. Deeper recovery work is conditional on a relevant change, not a separate frontend deliverable.

### Health and diagnostics

Preserve existing liveness/readiness semantics and exact expected health response checks. Readiness must reflect required PostgreSQL/Redis dependencies and completed startup, while observability failure remains non-blocking for app requests. Public responses expose no internal connection details. Keep metrics/log backends and management surfaces private.

Carry correlation/request IDs through ProblemDetails and structured server diagnostics. Record low-cardinality profile/release context, response status, duration, bounded dependency failures and authentication outcome categories without identity secrets. Redact cookies, Authorization, CSRF/email/reset/provider/passkey payloads, sensitive URL parameters and request bodies. Frontend error reporting is opt-in, scrubbed and useful without a third-party analytics dependency. Retained Playwright traces/network artifacts can contain credentials; restrict, redact and expire them rather than publishing raw authenticated traces in PRs.

Provide short diagnostics for app/container status, readiness, running digest/profile, recent redacted logs, connector, backups and runner. Use existing maintenance/doctor scripts. Record symptom-to-action guidance for 5xx, pending readiness, missing chunks, failed public API requests and connector/DNS failures. No mail/account troubleshooting guide is required.

### Migrations, persistence and backup

- Reuse the existing migration bundle/provenance and deployment sequencing. No JavaScript migration owner and no separate React schema. Frontend selection alone should not need a database migration.
- Snapshot/backup before a release whose data/schema changes require it. Record compatibility with the previous image; use additive/expand-contract changes where practical. Do not let normal startup race an independently executing migration bundle.
- Verify public sample books survive the scoped app restart and retain existing database/key-store mounts. Preserve existing Blazor account/key coverage in its tests; do not create React account fixtures to test persistence. Distinguish transient Redis cache from persisted backend keys in operational documentation.
- Preserve the existing app-scoped PostgreSQL backup and secret/key recovery setup. Use existing doctor/maintenance commands to inspect timer/service status and recent `last-success`. For a new app without a scheduled run yet, one app-scoped backup through the existing script is sufficient; record that the timer path has not yet been observed.
- Record the existing retention/storage behavior and relevant limitations in a short handover. A new backup architecture, off-node replication service, recovery-objective project or disaster-recovery platform is outside this frontend change.
- If this implementation changes backup/restore behavior or introduces schema/data changes that make existing compatibility evidence insufficient, use the existing restore procedure in a separate app-owned disposable environment. Verify representative public records and record the result. Never overwrite the active database as a rehearsal.

### Rollback and browser continuity

Record the previous compatible verified React image and the existing command/runbook for redeploying it. On first installation, record that no previous React release exists. A normal frontend-only update with unchanged schema needs no live rollback drill. If this work changes rollback logic or introduces incompatible schema/data changes, verify the recovery path in disposable infrastructure before release. A digest rollback is valid only if the prior application can read the current schema/data; otherwise use a reviewed forward repair or explicitly authorized restore procedure. Never automatically run destructive down migrations.

After a failed deployment, retain failed run IDs/logs, ownership state, volumes and backup artifacts. Follow the repository's supported rollback dispatch/recovery procedure and authorization. Do not invent a deployment path that bypasses immutable-release checks to make an older image run. Verify both the restored app and the existing Blazor demo afterward.

HTML revalidates; fingerprinted assets are immutable. Test an open tab across releases: an old shell may request a removed lazy chunk. Use one bounded controlled refresh with clear recovery UI, and avoid reload loops. Do not introduce an asset-retention platform or service worker for this public SPA unless evidence requires it.

Test public navigation/focus/reconnect and back-forward cache restoration without stale route errors or abandoned requests. No identity-transition or private browser cache protocol is needed in this version.

### Service recovery and observation

At P7b, restart only the owned app container once and verify readiness, public content, public data persistence and existing key-store behavior within the initial five-minute target. Check the app's dedicated connector is healthy and configured through the existing runbook. A connector restart drill is conditional on changed connector/recovery behavior or an explicit runbook requirement. A node reboot is not required for frontend acceptance; if changed boot/service behavior makes it necessary, follow the node runbook and obtain applicable shared-host maintenance authorization first.

Check readiness, ordinary public catalog activity and redacted server/container/connector status during a brief final observation, initially 15 minutes. Investigate repeated restarts, persistent 5xx or resource exhaustion. Record existing backup status honestly; no overnight drill is required when the existing scoped backup check passes.

### Rotation and removal

Link existing app-scoped rotation procedures for database/Redis, backend keys, connector token and registry access. No credential rotation drill or mail/provider procedure is added. Follow the public runbook's identity/credential-change protections rather than overwriting state during a normal deployment.

Removal is separately authorized maintenance. Prove ownership before removing this app's connector, Caddy site, runner, repository inputs or Cloudflare resources. Preserve volumes/backups by default and verify the remaining shared configuration. Never run global Docker prune, remove a deployment lock automatically, or use Compose `down --volumes` on the node.

## 10. Template experience and documentation deliverables

### Fresh-clone walkthrough

Perform this from a clean checkout that does not inherit the developer's previous generated output or private settings. Keep credentials, native-node installation values and protected provider state out of the example.

1. Read prerequisites and verify supported SDK/Node/Docker/browser tooling. Commands diagnose a missing tool or invalid profile clearly.
2. Run default Blazor locally through its documented path, then select React using only `frontend-profile.txt` and documented local settings. Blazor users are not required to install React tooling.
3. Start the HTTPS Vite-to-C# dev path, prove public API proxying and cancellation, change a route/component and observe HMR without backend restart or contract regeneration for a cosmetic edit.
4. Change a backend response in a disposable branch, regenerate schema/types, observe the expected compiler/drift failure until consumers are updated, then restore through ordinary reviewed edits. No generation requires live DB/Redis/provider credentials.
5. Add a small representative feature using the documented vertical slice, typed API, Query keys, route, validation and ownership/test conventions. Verify the extension instructions rather than committing a second sample application solely for this exercise.
6. Build/run the final production image for each profile from clean output; verify the expected routes/assets and absence of the inactive frontend. Test a deliberate missing React bundle fails publish clearly.
7. Follow the fork identity/release/deployment guide through a disposable configuration rehearsal, then compare it with the actual downstream installation. Prove instructions have no hard-coded developer hostnames, paths or secrets.
8. Follow documented update/recovery instructions and locate public deployment evidence from a fresh session. Record every undocumented prerequisite found and fix the guide before completion.

### Documentation map

| Document | Required update |
| --- | --- |
| `README.md` | Frontend choices, quick start, feature/capability summary, rendering limits, links to profile and deployment guides |
| `docs/FrontendProfiles.md` | Selection contract, architecture/module layout, dev/build commands, route/fallback/assets behavior, settled schema/type/client toolchain, regenerate/check workflow and intentional profile differences |
| `docs/Requirements.md` | Common security/data/operations requirements; Blazor Auto requirements scoped to Blazor; SPA/prerender and accessibility requirements scoped correctly |
| `docs/Test.md` | Exact React checks, profile isolation, public React E2E and retained Blazor real-cookie setup, executed/skipped policy, browser/performance coverage and artifact hygiene |
| `docs/HowToForkThisRepo.md` | One-file frontend choice, app/image/DP identity, dependency/contract updates and independent deployment/account data |
| Local-run/Compose guides | HTTPS proxy, certificates, contract/build prerequisites, both profile commands and clear production differences |
| LocalSingleNode deployment/public guides | Trusted profile input, `ReactPublicV1` versus existing Blazor acceptance, multi-app listeners/ownership, read-only acceptance, rollback/backup and public verification |
| LocalCluster/Cloud guides and audits | Correct selected-profile artifacts/acceptance, retained supported contracts and any manifest transition instructions |
| Account scope note | React v1 has no account area or SMTP/provider prerequisites; existing Blazor accounts are preserved; future account work is separate |
| Maintenance/handover | Update path, previous release, existing diagnostic/backup/recovery commands, connector/credential configuration and scoped removal |

Choose exact locations for new guides during P0 and cross-link them; avoid duplicating command lists that drift. Keep machine details private. Examples use safe placeholders and fake credentials explicitly identified as local-only. Persisted docs, comments, commits and PR text use ordinary prose.

### Maintenance contract

Dependency upgrades include lockfile review, generated-contract check, compatible Router type/build output, browser smoke and bundle comparison. Keep security-sensitive .NET source references aligned with the installed patch. Use the existing dependency automation and required checks, with documented exceptions, rather than introducing unmaintained parallel automation.

Document how to add a capability across endpoint contract, server authorization/validation, generated types, UI, capability metadata, tests and deployed acceptance. Prefer feature-level modules and a small reusable UI set. Review dead code, unused packages, sample scaffold files, duplicate query stores, stale TODOs, and accidental cross-profile dependencies before P9.

The source-selectable template retains both frontends. If a downstream product wants to remove an unused frontend or deployment target, treat pruning as a separate scoped change that updates solution references, CI, audits and docs together. A new clone must not need pruning to function.

## 11. Risks and stop conditions

| Risk | Required decision/check |
| --- | --- |
| Razor/assets remain coupled | P1 clean publish proof; small UI-library fallback if needed; one host/backend |
| Schema generation starts infrastructure or needs UI assets | P4 isolated metadata path and unavailable-infrastructure/side-effect checks |
| Generated types disagree with wire data | Real-handler metadata checks, strict compiler cases and drift failure |
| Account scope creeps back through old acceptance/docs | Public-only goal, no account code/packages, `ReactPublicV1` selected before any test account creation |
| Private data becomes public for convenience | Existing authorization and cache policies retained; negative integration/public checks |
| Wrong downstream identity/image or bootstrap failure | Actions-disabled verified seed, own config PR/runner/image, exact-head and main-push provenance |
| Host capacity, listener/subnet/foreign resource conflict | Read-only native-host inventory and existing collision/ownership scripts before mutation |
| Existing unmerged deployment work is assumed released | Re-read main/runbooks; integrate only merged dependencies; preserve unrelated dirty work |
| New app affects existing Blazor demo | Separate roots/data/keys/cookies/ports/connectors; shared locks and before/after sibling smoke |
| Frontend fallback/CSP breaks API/assets or hydration | Actual artifact/browser checks, reserved paths, header policy and real 404 assertions |
| CI green through skipped tests | Required suite counts and aggregate check; missing/skipped evidence fails acceptance |
| Recovery work expands beyond frontend risk | Existing status/backup/recovery command and app restart; deeper rehearsal only for relevant changed risks |
| Live node/DNS access unavailable | Continue local code/CI/docs; name the precise external action and keep dependent milestone pending |

On a failed gate, preserve evidence/data and fix the responsible packet before dependent release work. Do not widen permissions, weaken authorization, remove audit rules, reclaim locks, adopt foreign resources or claim completion without evidence. Do not use account roadmap work as a substitute for finishing the public release.

## 12. Owner actions and authorization

Frontend implementation, contracts and deterministic tests need no SMTP/Google credentials or account setup. Use existing authorized repository/node/Cloudflare access and automate scriptable work through current runbooks. Missing live access leaves only dependent installation/deployment checks pending.

Possible owner-only steps are authentication/scoped access to the intended repository/node/Cloudflare account, the specific native-node operator command required by its runbook, or a concrete deployment/shared-maintenance approval not already covered by the session. Prepare reviewable artifacts/config/checks before requesting any missing approval and explain its source. Reuse existing applicable authorization; never ask merely because another phase has started. The controller PC must not be bootstrapped as a node.

The executable goal authorizes its described React repository/public setup and LocalSingleNode releases when the owner runs it. It does not authorize Cloud/LocalCluster dispatch, foreign-resource deletion, paid services, unrelated shared-host disruption or any account/provider implementation. This planning turn performs no external writes/deployment.

## 13. Settled decisions and external dependencies

| Decision | Default |
| --- | --- |
| Stack | React/TypeScript/Vite, Router Framework SPA, Query, Tailwind and existing C# host |
| Client | ASP.NET OpenAPI 3.1, `openapi-typescript`, `openapi-fetch`; no parallel NSwag/Axios pipeline |
| Product scope | Public catalog/reference app and reusable public frontend baseline |
| Accounts | No React account area or new account APIs; preserve existing Blazor/backend authorization |
| Email/providers | No SMTP/MailKit, confirmation/recovery, Google or passkeys in v1 |
| Rendering | Static SPA; product-specific prerendering later, no Node production process |
| Selection/release | One tracked profile file; upstream Blazor default; independent downstream React main/image |
| Live target | Separate React origin on selected existing native node; LocalSingleNode only |
| Operations | Existing diagnostics/backups/recovery and one scoped app restart |
| Completion | Required PR merges and green main CI, verified public app and fresh-clone/handover evidence |

Reverify repository ownership/name, native hostname/capacity, free app resources and owned hostname/DNS/tunnel state from the private record. Default downstream repository naming and hostname intent are already recorded privately; choose a collision-free alternative only for a verified conflict. Exact stable package versions are pinned at P0 using current official compatibility information. No mail/provider account is a blocker or deliverable.

## 14. Evidence and completion

P0.1 and P0.2 are complete. P0.1 used verified origin/main at 1bd71f73b151e68f1ab40720840704fba9261afa; main CI run 38066456492 passed. P0.2 merged through PR #132 as e2bdd54e911c2e67de3082a705172221decdadc5; main CI run 38090907816 passed on that exact commit. P1.1 profile selection and resolver work merged through PR #133 as e964c4195b0368919b15884b1b61eb585075c9b8; main CI run 38093686407 passed on that exact commit. P1.2 is in progress from verified main on branch `feat/react-p1-backend-composition`: compile-selected compositions, common Identity backend registration, Blazor-only UI/account services and HTTP-principal-only React user resolution are implemented locally. Both profile builds and focused profile tests pass; the default full suite passed 181 tests with 11 deliberately skipped E2E/lifecycle tests, and the deployment audit passed. Next: review the full diff, commit explicit paths, open a PR and wait for exact-head checks. No React UI or account implementation, downstream repository, live node/DNS/provider changes or deployment have been performed. The owner clarified that the first products do not need accounts; this supersedes earlier full account-parity scope.

### Phase ledger

| Phase | Status | PR / merge commit | Evidence / next action |
| --- | --- | --- | --- |
| P0 | Complete | PR #132; e2bdd54e911c2e67de3082a705172221decdadc5 | P0.1 verified main 1bd71f7 (CI 38066456492); P0.2 PR head eebf657d07219bbe4368d5ab654812e6eb77e234 passed build-test-push; main CI 38090907816 is green on merge commit e2bdd54e. |
| P1 | In progress | P1.1 PR #133; e964c4195b0368919b15884b1b61eb585075c9b8 | P1.1 head 7b4474a0dc77a27844773eba4ba278894bdfe5fa passed `build-test-push`; main CI 38093686407 passed. P1.2 local checks: BlazorAuto and React Release builds passed; focused composition/accessor tests 6/6 under both profiles; default suite 181 passed, 11 skipped; deployment audit passed. P1.2 branch `feat/react-p1-backend-composition` is uncommitted; review, stage explicit paths and open the PR next. |
| P2 | Pending | - | Public/private backend boundary |
| P3 | Pending | - | Account-free profile/security contract |
| P4 | Pending | - | Reproducible schema/types |
| P5 | Pending | - | Public React vertical slice |
| P6 | Pending | - | Public UX/browser polish and regression |
| P7 | Pending | - | CI/images/provenance and public acceptance |
| P7a | Pending | - | Isolated downstream/node/public readiness |
| P7b | Pending | - | Verified public React delivery |
| P8 | Deferred; outside v1 | - | Accounts and product-specific feature expansion; do not execute |
| P9 | Pending | - | Operations, fresh-clone docs and final handover |

Record each packet's requirements, branch/worktree/PR, exact head, local commands and suite counts/results, merge SHA, main run/attempt/result, release evidence, blockers and exact next action. Pending/failed/skipped checks remain visible. Keep private targets and authenticated artifacts in ignored/protected records; never commit secrets or real installation values.

### Packet record template

```text
Packet / requirement IDs / status:
Prerequisite merged commits:
Repository / task branch / worktree reference:
Files and behavior changed:
Local commands / suite counts / results:
PR / exact checked head / required check run:
Merge SHA / main run-attempt-result:
Contract/image/public evidence:
Blocker or deviation / exact next action:
```

### Private public-delivery record

```text
Timestamp / applicable operator authorization:
Verified native node / React origin / app identity / repository:
Existing Blazor origin / baseline / post-check:
Upstream merge / downstream release SHA:
Manifest version / frontend profile / ReactPublicV1:
Main CI run-attempt-result / image digest / migration artifact hash:
CD run-attempt-result / running digest-profile verification:
LAN / independent public HTTPS / browser results:
Account routes and private API denial / no test accounts created:
Browser versions / screenshots / accessibility / performance:
Scoped app restart / persisted public seed data / connector health:
Backup-doctor status / previous compatible release / recovery command:
Brief observation / conditional risk checks / remaining blockers:
```

### Final completion checklist

- [ ] R01-R16 have actual evidence for this public-only scope; no old account milestone is treated as required.
- [ ] Source/doc changes are merged with exact-head PR checks and green main CI in the applicable repositories; merge commits recorded.
- [ ] Final app/assets/contracts/migration artifacts match the verified release; running image/profile and `ReactPublicV1` acceptance agree.
- [ ] Separate public React app passes real HTTPS/browser/public-data checks; existing Blazor demo remains healthy.
- [ ] React has no account UI/endpoints or SMTP/provider setup; protected APIs remain protected and no test accounts were created.
- [ ] Required browser/accessibility/performance/security suites ran; blocked/skipped checks are not counted as success.
- [ ] Public seed data survives app restart; connector and existing backup/doctor status plus simple recovery instructions are verified.
- [ ] Fresh-clone dev/build/selection/generation/extension/release/deployment docs and handover are complete.
- [ ] No required v1 blocker remains. Only then mark this plan complete; deferred P8 stays outside this goal.
