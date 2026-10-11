# Frontend Profiles

## Status

Both `BlazorAuto` and public-only `React` are implemented and supported. The template default remains `BlazorAuto`. Builds isolate frontend dependencies and assets; React supplies a typed public catalog with safe static hosting, explicit loading/error states, route focus, security headers and browser coverage. Immutable release manifests bind the actual frontend, acceptance contract, source, CI run and registry digest. Optional additional publication and protected LocalSingleNode application selection allow both apps to share one source repository and the existing runner. See [ApplicationInstances](../Deployment/LocalSingleNode/ApplicationInstances.md) for setup and operations, and [delivery acceptance](../Plans/ReactFrontendDeliveryAcceptance.md) for recorded evidence.

## Selecting a profile

The only persisted selection is the tracked root `frontend-profile.txt`; the template value is exactly `BlazorAuto`. `Directory.Build.props` reads that file when no explicit MSBuild property is supplied. Builds reject missing, empty or unsupported values. A non-empty `FrontendProfile` environment variable is rejected so the build cannot silently select a profile from machine state.

The shared orchestration resolver trims and validates the file, then prints one canonical value:

```bash
python3 Scripts/Frontend/resolve_frontend_profile.py
```

Use `python3 Scripts/Frontend/resolve_frontend_profile.py --override React` only for temporary validation. It does not change the tracked file. The Dockerfile exposes `final-blazor` and `final-react` targets and rejects a profile/target mismatch. The React target builds with Node 24.21.0 and npm 12.2.0, stages the generated `build/client` files into the selected static root, and publishes them with C#. Node and npm are absent from both final images. `Scripts/RunLocal.ps1` resolves the tracked profile once and passes the matching target and value to Compose.

```bash
validation_profile="$(python3 Scripts/Frontend/resolve_frontend_profile.py --override React)"
docker build --target final-react --build-arg "FRONTEND_PROFILE_OVERRIDE=${validation_profile}" -f BlazorAutoApp/Dockerfile .
```

CI resolves the tracked file once and passes the validated output to MSBuild and the matching Docker target. A `BlazorAuto` validation uses `--target final-blazor`; a `React` validation uses `--target final-react`. P1.2 selects backend composition at compile time. The React profile does not register Razor UI services or compile Blazor components. P1.3 serves a selected physical web root and routes only safe HTML navigation to its shell.

A downstream React product selects `React` in its own tracked `frontend-profile.txt` after the React composition packets are merged. The upstream template and existing Blazor demo remain on Blazor Auto.

## Public React v1

React is a public catalog and reference feature served from the existing ASP.NET Core origin. It uses React, TypeScript, Vite, React Router Framework Mode with `ssr: false`, TanStack Query, Tailwind CSS and the existing C# API. ASP.NET Core serves the built static files. Production has no Node server.

The delivered routes are `/`, `/books` and `/books/author/<seed-key>`. Public book reads use the existing `/api/author-books` endpoints and seeded sample data. Resolve an author `seed-key` from the public list, then call the numeric item endpoint. Keep query bounds, rate limits and public cache behavior.

React v1 has no login, logout, registration, account settings, private bookcase, session provider or account API. It adds no SMTP/MailKit, recovery, external Google handler, passkeys, export, deletion or reauthentication support. Shared Identity cookies and authorization remain for protected backend APIs; public API requests omit credentials. Existing Blazor account pages and protected `/api/books` behavior remain in place. Anonymous protected API requests must return JSON `401`, not private data, login HTML, an SPA page or a successful write.

Reserve `/Account`, `/account`, `/api/auth` and provider callback paths case-insensitively. These inactive routes return real `404` responses. Never route API, health, missing assets or unknown reserved paths to the SPA shell.

React responses carry a restrictive Content Security Policy (`default-src 'self'`, no inline/eval scripts, no framing, and self-hosted assets), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: local-network-access=()`. Production uses ASP.NET Core HSTS and HTTPS redirection. Blazor keeps its existing middleware and header behavior. React startup still runs shared migrations and public author-book seeding but skips local/demo account seeding; it does not delete existing Identity rows or remove Identity storage.

In React production, the selected static root is the host's published `wwwroot`. Development defaults to `BlazorAutoApp/Frontend/React/wwwroot`; `Frontend:React:StaticRoot` may point to another repository-contained generated directory. Static files use ordinary ASP.NET Core static-file middleware. The navigation fallback serves `index.html` only for GET or HEAD requests that accept `text/html`; missing assets, API/health/account/provider/framework paths, non-HTML requests and unsafe methods remain `404`. HEAD returns shell headers without a body. The shell and un-fingerprinted assets revalidate; fingerprinted assets use a one-year immutable cache. Protected `/api/books` responses use `private, no-store`. Each frontend publish clears only the destination `wwwroot` before copying that profile's files, preventing a profile switch from retaining the other frontend's assets; publishing directly over the source `wwwroot` is rejected.

## Current repository entry points

Recheck this inventory when a packet changes one of these boundaries.

| Concern | Current entry points | Profile work |
| --- | --- | --- |
| Host composition | `BlazorAutoApp/Program.cs`; `BlazorAutoApp/BlazorAutoApp.csproj`; `BlazorAutoApp/Frontend` | `Program` calls the selected composition while common backend services remain shared. The Blazor client reference, WebAssembly server package, Google handler, Razor inputs and account UI compile only for `BlazorAuto`. React uses an HTTP-principal accessor and an isolated physical static root. |
| Client routes and state | `BlazorAutoApp.Client/Routes.razor`; `BlazorAutoApp.Client/Features/Books`; `BlazorAutoApp/Components` | Blazor retains its routes and authenticated state. React modules live under `BlazorAutoApp.React` with their own static output. |
| Public and private APIs | `BlazorAutoApp/Features/Books/Endpoints/AuthorBooksEndpoints.cs`; `BooksEndpoints.cs`; `BlazorAutoApp/Features/Books/DependencyInjection.cs` | Reuse public author-book reads. Keep owned-book routes authenticated. Move Blazor-only UI state registration out of common backend composition. |
| Identity boundary | `BlazorAutoApp/Features/Login/Account/LoginFeatureExtensions.cs`; `CurrentUserAccessor.cs`; `IdentityComponentsEndpointRouteBuilderExtensions.cs` | Keep shared Identity cookies and protected API authorization. Register Blazor authentication state, external Google handler and account endpoints only in Blazor composition. React resolves user identity only from the authenticated HTTP principal and maps no account routes. |
| API/build inputs | `Directory.Build.props`; `Directory.Packages.props`; `global.json`; `BlazorAutoApp/Dockerfile`; frontend package lockfiles | Docker uses separate final profile targets and selected static assets. Blazor npm tooling builds CSS and test tools; React has its own package/build stage. Ordinary Blazor builds do not require React npm. |
| Local orchestration | `docker-compose.yml`; `Scripts/RunLocal.ps1`; `Scripts/RunLighthouse.ps1` | Local commands resolve the explicit profile. React development uses the HTTPS Vite proxy to C#; production remains ASP.NET-hosted. |
| CI and image release | `.github/workflows/ci.yml` | CI validates both profiles and preserves required Blazor coverage. Main normally publishes the selected profile with its existing image/artifact names. Explicit optional additional publication produces a separate image, digest and manifest in the same trusted publishing job. |
| Immutable release contract | `Deployment/Common/Scripts/validate_release_manifest.py`; `Deployment/Common/Scripts/Tests`; `.github/workflows/ci.yml`; `cd-localsinglenode.yml`, `cd-localcluster.yml`, `cd-cloud.yml` | Schema-v2 manifests bind the frontend/acceptance pair to the exact source, image digest and migration bundle. Producers, consumers, fixtures and deployment audits validate the pair; schema-v1 remains Blazor-only. |
| Acceptance | `Scripts/Test-DeployedSite.ps1`; `Deployment/LocalSingleNode/Scripts/acceptance-check.sh`; `public-acceptance-check.sh`; `Deployment/LocalCluster/Scripts/ci-docker-smoke.sh` | Both frontend and acceptance profiles are explicit trusted inputs. Blazor keeps its account checks; `ReactPublicV1` reads public data, checks inactive account routes and private API denial, and uses only GET/HEAD without creating accounts, sessions or user-data fixtures. |
| Existing tests | `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs`; `BlazorAutoApp.Test/E2E` | Preserve Blazor account, Auto/WASM, simulation and cookie tests. Add explicitly selected React public fixtures and require real suite counts; do not let profile selection skip existing Blazor coverage. |

The release manifest and baked image labels identify the frontend and matching acceptance profile. Deployment verifies that identity before running acceptance, so a profile mismatch cannot select the Blazor account checks for a React release.

## Build and API contract

The tracked profile file is the only persisted selection. A single resolver validates it and passes the same value to MSBuild, Docker, CI, release metadata and acceptance. The template default is exactly `BlazorAuto`; React downstream configuration is exactly `React`.

React uses same-origin relative API paths. The HTTPS Vite development server proxies `/api` to the C# host. Production publishes the selected React Router `build/client` output beneath the ASP.NET host's web root. The host serves ordinary static files from the selected physical root and maps only safe HTML navigation to the shell. Missing assets and backend routes remain real errors. P1.3 also keeps profile inputs isolated at the host project level and clears the publish destination web root before copying the selected profile, so sequential publishes to one output directory cannot leave stale frontend assets.

Use ASP.NET Core OpenAPI 3.1 as the server contract. The minimal package at `BlazorAutoApp.React/` pins `openapi-typescript` and `openapi-fetch`; generated files are `api/openapi.json` and `app/api/generated/schema.d.ts`. Run `npm ci`, then `npm run api:generate` to update both files or `npm run api:check` to regenerate into temporary output and fail on drift without changing expected files. These commands work before React assets exist. Extraction uses the real React book-handler metadata, a fresh .NET artifacts path and the opt-in metadata-only entry; ordinary .NET builds remain generation-free. The metadata entry uses an empty builder and placeholder API services only for binding discovery. It does not load application settings or register persistence, cache, Identity, email or deployment services. Commit generated outputs with endpoint changes. Do not hand-edit them, duplicate wire DTOs or introduce a second client generator.

Build order is: validate profile; install only the selected frontend's lockfile; run isolated metadata-only OpenAPI extraction when requested; check/generate declarations; typecheck, lint, test and build React when selected; stage selected web assets; rebuild and publish the C# host; build and smoke the final image. A missing React bundle fails a React publish clearly. Profile switches use clean, profile-owned output paths; never reuse `--no-build` output from the other profile.

The final validation contract must exercise both profiles from clean output. PR CI builds and smokes both profiles. Main CI publishes only the persisted selection. The release manifest includes `frontend_profile` and `acceptance_profile` (`BlazorAuto` / `BlazorAutoV1` or `React` / `ReactPublicV1`). LocalCluster and Cloud remain supported and receive compatible profile-aware acceptance; this goal deploys only the React downstream app through LocalSingleNode.

## Initial toolchain pins

These exact stable versions were checked on 2026-10-11 against official release/support pages and npm registry metadata. Use exact versions in the package manifest and lockfile. Node is a build and development tool only.

| Tool | Initial exact version | Compatibility decision |
| --- | --- | --- |
| Node.js | `24.21.0` | Current LTS release line; supported by React Router 8 and the selected test tooling. |
| npm | `12.2.0` | Exact package-manager version; its Node engine range includes Node 24.21.0. |
| React / React DOM | `19.3.0` | Matching stable releases. |
| React Router packages | `react-router`, `@react-router/dev`, `@react-router/node` `8.4.0` | Framework Mode and SPA build. Keep the package versions aligned. `@react-router/node` is a build dependency; do not run a Node production server. |
| SPA user-agent helper | `isbot` `5.2.2` | Direct exact dependency required by React Router's type-generation and prerender tooling. |
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

## React local development

Install dependencies and run the React checks from `BlazorAutoApp.React/` with the pinned Node/npm versions:

Check `node --version` and `npm --version` before installing. The pinned Node distribution may bundle a different npm version; select npm `12.2.0` explicitly through your version manager or an isolated toolchain. Do not assume installing Node alone selects the required npm. The package rejects incompatible engines. Keep tooling changes local to the clone or your chosen development environment.

```powershell
npm ci
npm run api:check
npm run typecheck
npm run lint
npm test
npm run build
```

For live development, make compatible local PostgreSQL and Redis services available as described in [HowToRunLocally](HowToRunLocally.md#run-without-docker). Then start the React-profile C# API and Vite in separate terminals:

```powershell
npm run dev:api
```

```powershell
npm run dev
```

Open `https://localhost:5173`. The Vite server serves the app over HTTPS and proxies `/api` to `https://localhost:7186`. The dev script checks for a trusted ASP.NET Core HTTPS certificate, exports a password-protected PFX to a temporary directory, reads it into memory, and removes the directory before Vite starts. It does not change certificate trust. If no trusted certificate exists, run `dotnet dev-certs https --trust` yourself, then retry. Node uses the operating system's trusted certificates for the local HTTPS proxy. Neither dev command requires a built React bundle in the ASP.NET web root.

If the C# API uses another HTTPS origin, set `REACT_API_ORIGIN` to that origin in both terminals before starting the API and Vite.

`npm run build` creates the static client in `build/client`; ASP.NET Core still owns production hosting. The package ignores that output and React Router's generated route types.

The public client exposes only the generated author-book read operations. It sends same-origin requests with browser credentials omitted and passes TanStack Query's abort signal through to `fetch`. HTTP failures become typed errors with safe JSON ProblemDetails, field errors, `Retry-After` bounded to 60 seconds, and an available correlation ID. Empty, malformed, or unexpected-media-type success bodies become invalid-response errors without exposing upstream HTML. The app-level QueryClient keeps results fresh for 60 seconds, removes unused entries after five minutes, and refetches on focus and reconnect. It retries once only for network failures and HTTP 502/503/504; it does not retry 4xx responses, including 429. The public client adds no auth or CSRF bootstrap.

The public shell is at `/`, the read-only catalog is at `/books`, and a book detail is linked as `/books/author/<seed-key>`. Details resolve the key against the generated public catalog response before calling the numeric-ID detail endpoint. Missing keys/items have a public not-found state. Catalog and detail pages show explicit loading, empty, rate-limit, network, invalid-response and server-error states; retries are user-triggered. External book links render only for HTTP or HTTPS URLs.

### Extend a typed public feature

Change the actual C# response or endpoint contract first. Run `npm run api:check` to see stale generated output fail, then deliberately run `npm run api:generate` and review both generated files. Generation requires the .NET SDK and pinned frontend tooling, but no running database, Redis, email service or React bundle. Commit backend, schema and generated declarations together.

Add the route or component using the generated public API and existing query keys. Pass the query abort signal to the transport, preserve explicit loading/empty/error states, and add a focused component test. Run `typecheck`, `lint`, `test` and `build`, then the repository local gate. A backend response change should fail a typed consumer before regeneration and compile after it. Cosmetic Vite HMR edits should update the open browser without restarting the API or changing generated contracts.

Primary references: [Node 24.21.0 LTS](https://nodejs.org/en/blog/release/v24.21.0), [React 19.3](https://react.dev/blog/2026/09/09/react-19-3), [React Router v8 release contract](https://reactrouter.com/start/start/changelog), [React Router SPA mode](https://reactrouter.com/how-to/spa), [Vite supported releases](https://vite.dev/releases), [Tailwind CSS v4.3](https://tailwindcss.com/blog/tailwindcss-v4-3). Package engine and peer ranges were checked from npm registry metadata on the review date.

## Verification and handover

Keep the repository's full local gate in `docs/Test.md`. React adds `api:check`, `typecheck`, `lint`, `test` and `build` checks plus both-profile image smoke. Build and test sequentially in a checkout. Record discovered, executed, skipped and blocked suite counts; skipped or absent required checks do not pass.

Track implementation evidence against R01-R16 in the [delivery plan](../Plans/ReactFrontendProfile.md#requirement-traceability).

Use the existing C# Playwright harness. React acceptance covers Chromium public flows broadly and Firefox/WebKit smoke before release, with mobile layouts, keyboard/focus, axe checks, manual screen-reader spot checks and repeatable Lighthouse budgets. Public acceptance remains read-only and creates no account or user-data fixture.

Both profiles are supported in this repository; selecting or validating React does not require another GitHub repository. The template default remains `BlazorAuto`. The former separate demo repository approach is withdrawn. A second public app uses explicit optional publication, a protected additional application identity and the existing native runner. Keep the default profile stable and require a verified main release and immutable digest for each deployment.

Implementation status, packet evidence and deployment target details live in `Plans/ReactFrontendProfile.md` and applicable ignored installation records. Keep hostnames, node identity, resource IDs, ports, capacity, credentials, run IDs and authenticated deployment evidence in ignored or protected records, never here.

## Optional additional frontend releases

Clones publish only the profile selected by `frontend-profile.txt` by default. The selected profile keeps the image repository from `Deployment/Common/release.yml` and the existing migration artifact name. Changing the frontend locally does not publish another release.

To publish the other supported frontend alongside the selected profile, explicitly set the repository Actions variable `ADDITIONAL_FRONTEND_PROFILES` to `React` when the selected profile is `BlazorAuto`, or to `BlazorAuto` when the selected profile is `React`. Leave the variable unset for ordinary selected-only publication. Profile names are case-sensitive. Unknown names, duplicates, empty list entries and the selected profile repeated as an additional profile fail publication.

The existing trusted-main publishing job builds and smoke-tests releases sequentially. The additional image repository is `<app_image>-<lowercase-profile>` and its artifact is `<migration_artifact_name>-<lowercase-profile>`; primary names remain unchanged. Both releases use the same source SHA, CI run and attempt. Each has its own digest and schema-v2 manifest containing the actual frontend and acceptance profile. The additional artifact contains only the verified migration bundle and its own manifest, with seven-day retention. Migration bytes are shared only after staging provenance and hashes are validated again.

An additional publication failure fails `build-test-push`, even if the primary image was already pushed. Deployment must require the entire successful source CI run and validate the specific image, artifact, profile and digest. A successful selected-only run does not prove an additional release exists. This setting enables publication only; it does not create an app instance, install a runner or dispatch a deployment. Remove the variable to stop publishing additional releases on future runs.
