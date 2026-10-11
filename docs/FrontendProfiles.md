# Frontend Profiles

## Status

This guide defines the approved public React v1 profile and its build contract. P1.1 adds fail-closed profile selection. P1.2 splits the selected frontend composition and shared Identity backend. P1.3 isolates host inputs and adds physical static-file hosting with safe SPA navigation. P3.1 keeps React account-free and adds its response security policy; later packets add the built React bundle, profile-aware validation and release metadata. Do not treat this design guide as proof those later features already exist.

## Selecting a profile

The only persisted selection is the tracked root `frontend-profile.txt`; the template value is exactly `BlazorAuto`. `Directory.Build.props` reads that file when no explicit MSBuild property is supplied. Builds reject missing, empty or unsupported values. A non-empty `FrontendProfile` environment variable is rejected so the build cannot silently select a profile from machine state.

The shared orchestration resolver trims and validates the file, then prints one canonical value:

```bash
python3 Scripts/Frontend/resolve_frontend_profile.py
```

Use `python3 Scripts/Frontend/resolve_frontend_profile.py --override React` only for temporary validation. It does not change the tracked file. Pass its canonical output to Docker as `FRONTEND_PROFILE_OVERRIDE`; the Dockerfile applies that same value to restore, build and publish. Without an override, Docker reads the copied tracked file.

```bash
validation_profile="$(python3 Scripts/Frontend/resolve_frontend_profile.py --override React)"
docker build --build-arg "FRONTEND_PROFILE_OVERRIDE=${validation_profile}" -f BlazorAutoApp/Dockerfile .
```

CI resolves the tracked file once and passes the validated output to MSBuild and Docker. P1.2 selects backend composition at compile time. The React profile does not register Razor UI services or compile Blazor components. P1.3 serves a selected physical web root and routes only safe HTML navigation to its shell; the production React bundle arrives in a later packet.

A downstream React product selects `React` in its own tracked `frontend-profile.txt` after the React composition packets are merged. The upstream template and existing Blazor demo remain on Blazor Auto.

## Public React v1

React is a public catalog and reference feature served from the existing ASP.NET Core origin. It uses React, TypeScript, Vite, React Router Framework Mode with `ssr: false`, TanStack Query, Tailwind CSS and the existing C# API. ASP.NET Core serves the built static files. Production has no Node server.

The delivered routes are `/`, `/books` and `/books/author/<seed-key>`. Public book reads use the existing `/api/author-books` endpoints and seeded sample data. Resolve an author `seed-key` from the public list, then call the numeric item endpoint. Keep query bounds, rate limits and public cache behavior.

React v1 has no login, logout, registration, account settings, private bookcase, session provider or account API. It adds no SMTP/MailKit, recovery, external Google handler, passkeys, export, deletion or reauthentication support. Shared Identity cookies and authorization remain for protected backend APIs; public API requests omit credentials. Existing Blazor account pages and protected `/api/books` behavior remain in place. Anonymous protected API requests must return JSON `401`, not private data, login HTML, an SPA page or a successful write.

Reserve `/Account`, `/account`, `/api/auth` and provider callback paths case-insensitively. These inactive routes return real `404` responses. Never route API, health, missing assets or unknown reserved paths to the SPA shell.

React responses carry a restrictive Content Security Policy (`default-src 'self'`, no inline/eval scripts, no framing, and self-hosted assets), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: local-network-access=()`. Production uses ASP.NET Core HSTS and HTTPS redirection. Blazor keeps its existing middleware and header behavior. React startup still runs shared migrations and public author-book seeding but skips local/demo account seeding; it does not delete existing Identity rows or remove Identity storage.

In React production, the selected static root is the host's published `wwwroot`. Development defaults to `BlazorAutoApp/Frontend/React/wwwroot`; `Frontend:React:StaticRoot` may point to another repository-contained generated directory. Static files use ordinary ASP.NET Core static-file middleware. The navigation fallback serves `index.html` only for GET or HEAD requests that accept `text/html`; missing assets, API/health/account/provider/framework paths, non-HTML requests and unsafe methods remain `404`. HEAD returns shell headers without a body. Each frontend publish clears only the destination `wwwroot` before copying that profile's files, preventing a profile switch from retaining the other frontend's assets; publishing directly over the source `wwwroot` is rejected.

## Current repository entry points

Recheck this inventory when a packet changes one of these boundaries.

| Concern | Current entry points | Profile work |
| --- | --- | --- |
| Host composition | `BlazorAutoApp/Program.cs`; `BlazorAutoApp/BlazorAutoApp.csproj`; `BlazorAutoApp/Frontend` | `Program` calls the selected composition while common backend services remain shared. The Blazor client reference, WebAssembly server package, Google handler, Razor inputs and account UI compile only for `BlazorAuto`. React uses an HTTP-principal accessor and an isolated physical static root. |
| Client routes and state | `BlazorAutoApp.Client/Routes.razor`; `BlazorAutoApp.Client/Features/Books`; `BlazorAutoApp/Components` | Keep existing Blazor routes and authenticated state. Add React modules under `BlazorAutoApp.React`; do not copy the Blazor web root into that profile. |
| Public and private APIs | `BlazorAutoApp/Features/Books/Endpoints/AuthorBooksEndpoints.cs`; `BooksEndpoints.cs`; `BlazorAutoApp/Features/Books/DependencyInjection.cs` | Reuse public author-book reads. Keep owned-book routes authenticated. Move Blazor-only UI state registration out of common backend composition. |
| Identity boundary | `BlazorAutoApp/Features/Login/Account/LoginFeatureExtensions.cs`; `CurrentUserAccessor.cs`; `IdentityComponentsEndpointRouteBuilderExtensions.cs` | Keep shared Identity cookies and protected API authorization. Register Blazor authentication state, external Google handler and account endpoints only in Blazor composition. React resolves user identity only from the authenticated HTTP principal and maps no account routes. |
| API/build inputs | `Directory.Build.props`; `Directory.Packages.props`; `global.json`; `BlazorAutoApp/Dockerfile`; `BlazorAutoApp.Client/package.json` and lockfile | Current Docker build copies both server and Blazor client projects. Existing client npm tooling builds Blazor CSS and Lighthouse assets. Add a separate React package and build stage; keep ordinary Blazor builds independent of React npm. |
| Local orchestration | `docker-compose.yml`; `Scripts/RunLocal.ps1`; `Scripts/RunLighthouse.ps1` | Add explicit profile-aware local commands and an HTTPS Vite proxy to C#. Do not infer profile from a hostname or installed output. |
| CI and image release | `.github/workflows/ci.yml` | CI currently installs the Blazor client package, rebuilds committed Tailwind CSS, builds and smokes a Docker image on PRs, then publishes the main image and migration manifest. Validate both clean profiles on PRs; publish only the repository's selected profile from main. |
| Immutable release contract | `Deployment/Common/Scripts/validate_release_manifest.py`; `Deployment/Common/Scripts/Tests`; `.github/workflows/ci.yml`; `cd-localsinglenode.yml`, `cd-localcluster.yml`, `cd-cloud.yml` | The current manifest is schema version 1 and has no frontend field. P7 must version the contract, bind profile and acceptance identity to the exact source, image digest and migration bundle, and update every producer, consumer, fixture and audit together. |
| Acceptance | `Scripts/Test-DeployedSite.ps1`; `Deployment/LocalSingleNode/Scripts/acceptance-check.sh`; `public-acceptance-check.sh`; `Deployment/LocalCluster/Scripts/ci-docker-smoke.sh` | Keep the existing Blazor account acceptance. Add a separate `ReactPublicV1` path that reads public data, checks account routes and private API denial, and creates no account or user-data fixture. |
| Existing tests | `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs`; `BlazorAutoApp.Test/E2E` | Preserve Blazor account, Auto/WASM, simulation and cookie tests. Add explicitly selected React public fixtures and require real suite counts; do not let profile selection skip existing Blazor coverage. |

The current main release manifest has no frontend identity. Until P7 is merged, it cannot prove that a React image is selected or that a public acceptance suite matches the image.

## Build and API contract

The tracked profile file is the only persisted selection. A single resolver validates it and passes the same value to MSBuild, Docker, CI, release metadata and acceptance. The template default is exactly `BlazorAuto`; React downstream configuration is exactly `React`.

React uses same-origin relative API paths. The HTTPS Vite development server proxies `/api` to the C# host. Production publishes the selected React Router `build/client` output beneath the ASP.NET host's web root. The host serves ordinary static files from the selected physical root and maps only safe HTML navigation to the shell. Missing assets and backend routes remain real errors. P1.3 also keeps profile inputs isolated at the host project level and clears the publish destination web root before copying the selected profile, so sequential publishes to one output directory cannot leave stale frontend assets.

Use ASP.NET Core OpenAPI 3.1 as the server contract. Generate `api/openapi.json` and TypeScript declarations with pinned `openapi-typescript`; call the API through one typed `openapi-fetch` client and feature adapters. Generation is opt-in, isolated from ordinary builds and startup, and must work with DB, Redis, mail, OAuth and deployment secrets unavailable. Commit generated outputs with endpoint changes. Do not hand-edit them, duplicate wire DTOs or introduce a second client generator.

Build order is: validate profile; install only the selected frontend's lockfile; run isolated metadata-only OpenAPI extraction when requested; check/generate declarations; typecheck, lint, test and build React when selected; stage selected web assets; rebuild and publish the C# host; build and smoke the final image. A missing React bundle fails a React publish clearly. Profile switches use clean, profile-owned output paths; never reuse `--no-build` output from the other profile.

The final validation contract must exercise both profiles from clean output. PR CI builds and smokes both profiles. Main CI publishes only the persisted selection. The release manifest includes `frontend_profile` and `acceptance_profile` (`BlazorAuto` / `BlazorAutoV1` or `React` / `ReactPublicV1`). LocalCluster and Cloud remain supported and receive compatible profile-aware acceptance; this goal deploys only the React downstream app through LocalSingleNode.

## Initial toolchain pins

These exact stable versions were checked on 2026-10-10 against official release/support pages and npm registry metadata. Use exact versions in the eventual package manifest and lockfile. Recheck before P4/P5 package installation if implementation starts after an upstream release; update this table and record compatibility evidence in that packet. Node is a build and development tool only.

| Tool | Initial exact version | Compatibility decision |
| --- | --- | --- |
| Node.js | `24.21.0` | Current LTS release line; supported by React Router 8 and the selected test tooling. |
| npm | `12.2.0` | Exact package-manager version; its Node engine range includes Node 24.21.0. |
| React / React DOM | `19.3.0` | Matching stable releases. |
| React Router packages | `react-router`, `@react-router/dev`, `@react-router/node` `8.4.0` | Framework Mode and SPA build. Keep the package versions aligned. `@react-router/node` is a build dependency; do not run a Node production server. |
| Vite | `8.3.4` | Current supported Vite minor; React Router 8 supports Vite 8. |
| Tailwind CSS | `tailwindcss`, `@tailwindcss/vite` `4.3.3` | Match the existing repository's Tailwind 4.3.3 line. React CSS remains separate from Blazor output. |
| TanStack Query | `@tanstack/react-query` `5.104.1` | Stable React Query package; supports React 19. |
| TypeScript | `5.9.3` | `openapi-typescript` 7.13.0 declares TypeScript 5.x peer support; React Router and typescript-eslint accept this version. |
| OpenAPI | `openapi-typescript` `7.13.0`; `openapi-fetch` `0.17.0` | One generator and one typed fetch client. |
| Test runner | `vitest` `5.0.3`; `jsdom` `30.1.2` | Vitest supports Vite 8 and Node 24; jsdom's Node range includes 24.21.0. |
| React test helpers | `@testing-library/react` `16.3.3`; `@testing-library/user-event` `14.6.7`; `@testing-library/dom` `10.4.2`; `@testing-library/jest-dom` `7.0.1` | Matching current stable packages for behavior tests. |
| Type declarations | `@types/react` and `@types/react-dom` `19.3.0`; `@types/node` `24.19.2` | Match React 19 and the Node 24 build target. |
| Lint | `eslint` `10.12.0`; `@eslint/js` `10.0.1`; `typescript-eslint` `8.71.1`; `eslint-plugin-react-hooks` `7.1.1`; `eslint-plugin-react-refresh` `0.5.7` | Peer ranges cover ESLint 10 and TypeScript 5.9.3. |

Selected React Router 8 and Vite 8 releases support one another. OpenAPI generator compatibility keeps TypeScript on 5.x even though TypeScript 7.0.2 is also stable. Node 24.21.0 meets the selected Router, Vitest, jsdom and npm minimums. Use the pinned Node 24 toolchain for React work, and do not change a developer's global installation as part of the profile implementation.

Primary references: [Node 24.21.0 LTS](https://nodejs.org/en/blog/release/v24.21.0), [React 19.3](https://react.dev/blog/2026/09/09/react-19-3), [React Router v8 release contract](https://reactrouter.com/start/start/changelog), [React Router SPA mode](https://reactrouter.com/how-to/spa), [Vite supported releases](https://vite.dev/releases), [Tailwind CSS v4.3](https://tailwindcss.com/blog/tailwindcss-v4-3). Package engine and peer ranges were checked from npm registry metadata on the review date.

## Verification and handover

Keep the repository's full local gate in `docs/Test.md`. React adds `api:check`, `typecheck`, `lint`, `test` and `build` checks plus both-profile image smoke. Build and test sequentially in a checkout. Record discovered, executed, skipped and blocked suite counts; skipped or absent required checks do not pass.

Track implementation evidence against R01-R16 in the [delivery plan](../Plans/ReactFrontendProfile.md#requirement-traceability).

Use the existing C# Playwright harness. React acceptance covers Chromium public flows broadly and Firefox/WebKit smoke before release, with mobile layouts, keyboard/focus, axe checks, manual screen-reader spot checks and repeatable Lighthouse budgets. Public acceptance remains read-only and creates no account or user-data fixture.

For the separate demo, retain the upstream remote and use a private downstream repository whose main is set to `React`. Validate both profiles there and publish that repository's own immutable image. Never install a PR image, mutable tag or upstream Blazor image as the React demo.

Implementation status, packet evidence and deployment target details live in `Plans/ReactFrontendProfile.md` and ignored `Plans.local/ReactFrontendProfile.demo.md` / `ReactFrontendProfile.delivery.md`. Keep hostnames, node identity, resource IDs, ports, capacity, credentials, run IDs and authenticated deployment evidence in ignored or protected records, never here.
