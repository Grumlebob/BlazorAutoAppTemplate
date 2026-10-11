# Code quality improvement backlog

This backlog starts from the accepted SonarQube baseline at `8393173bc4f580ae1dc036a533e4e47281099add`. It records reviewed follow-up work; it does not authorize implementation. Profile-specific issue keys are kept together when they represent the same source finding. Shared findings are deduplicated for planning, and profile counts are not combined.

## Prioritized work

### Q-001 — Make the localhost TLS exception explicit in the traffic simulator

- Evidence: BlazorAuto and React analyses; `csharpsquid:S4830` keys `b8eb19f7-9c91-4235-837c-0936291cc9c7` at `BlazorAutoApp.Simulation/Http/HttpClientFactory.cs:22`, `6e842420-91f6-4947-86e0-889cbd3d99e3` at `BlazorAutoApp.Simulation/Running/ScenarioRunner.cs:128`, `4c5b91ad-ec03-4c7e-aacb-30c7c91fa049` at the first path, and `645ee031-44f8-4f4c-8ec1-69993af5277d` at the second. Both handlers use `DangerousAcceptAnyServerCertificateValidator` for local hosts.
- Why it matters: the override skips certificate-chain and host validation for HTTPS to loopback. The current check confines it to the local simulation target, which limits exposure, but also hides invalid local certificates.
- Proposed change: route discovery and scenario requests through one handler factory. Prefer the normal trusted development certificate. If self-signed local HTTPS still needs support, make the exception an explicit local-only option with a warning.
- Behavior to preserve: local HTTP simulation, trusted local HTTPS, cookie handling, and all deployed-target certificate validation.
- Verification: focused tests show invalid certificates fail by default, any opt-in applies only to loopback, non-loopback certificates are always validated, and both simulation flows still work with a trusted local certificate.
- Effort: medium; both request paths and local developer-certificate setup need coordinated behavior.
- Dependencies: none.
- Decision: defer design work; this is a constrained local trust exception, not a confirmed remote-target vulnerability.
- Acceptance: no silent certificate bypass remains; any local exception is explicit and cannot be used for a deployed target.

### Q-002 — Replace the MD5-based packaged Caddyfile check with a package-aware verification

- Evidence: `python:S4790` keys `6917f011-a7e9-4a61-ab3d-bede2d9924b0` (BlazorAuto) and `9c847807-d7f0-415f-a177-d0ac3a19699d` (React) at `Deployment/LocalSingleNode/Scripts/lib/collisions.py:21`.
- Why it matters: this privileged preflight decides whether a Caddyfile is the unmodified packaged default before allowing setup to proceed. The current code hashes the file with MD5 and compares it with dpkg's recorded conffile checksum. That is not password hashing or a cryptographic signature, but collision resistance is still relevant to a fail-closed ownership decision.
- Proposed change: check whether dpkg exposes a stronger supported verification path or whether the exact packaged default can be compared directly. If the package metadata only supplies MD5, document that constraint and keep foreign or ambiguous files rejected.
- Behavior to preserve: accept the repository-owned Caddyfile and a verified pristine package default; reject symlinks, edited files, and foreign configuration before any host changes.
- Verification: extend the Caddy collision fixtures for pristine, changed, foreign, and ambiguous files; run the LocalSingleNode setup tests and deployment audit.
- Effort: medium; the check runs before privileged host adoption and must remain fail-closed.
- Dependencies: none.
- Decision: fix through a bounded design review; do not replace the check with an unconditional allow or a weaker comparison.
- Acceptance: modified or foreign Caddy configuration never passes as a packaged default, and the verification basis is explicit.

### Q-003 — Add focused coverage for BlazorAuto authentication-management routes

- Evidence: BlazorAuto coverage report at the baseline SHA shows 0.0% for `BlazorAutoApp/Features/Login/Account/Pages/ExternalLogin.razor`, `.../Manage/Passkeys.razor`, `.../Manage/TwoFactorAuthentication.razor`, and `.../Manage/EnableAuthenticator.razor`. This is coverage evidence, not a Sonar issue key. An E2E test already visits the Passkeys route, so zero imported line coverage does not mean the route has no test at all.
- Why it matters: external-provider sign-in, passkey management, and two-factor setup are authentication-sensitive flows whose success, cancellation, and error behavior deserve direct verification.
- Proposed change: add focused component or browser tests for route entry and the relevant success, invalid-input, cancellation, and failure states in those pages. Reuse existing identity test support; do not target a percentage by excluding code.
- Behavior to preserve: current identity-provider redirects, passkey ownership checks, authenticator enrollment and reset behavior, recovery codes, and authorization boundaries.
- Verification: tests assert visible state and server-side outcomes for each changed flow; run both frontend profiles and the existing identity E2E suite where applicable.
- Effort: medium; the pages rely on authentication and browser navigation behavior.
- Dependencies: none.
- Decision: fix in a future application-quality wave.
- Acceptance: meaningful success and failure paths have behavioral tests, with coverage evidence mapped to the actual page code.

### Q-004 — Test the route-driven book modal's asynchronous and destructive paths

- Evidence: BlazorAuto risk-ranked file `BlazorAutoApp.Client/Features/Books/BookModal/BookModalHost.razor` has 443 ncloc, risk score 57.0, and 31.9% line coverage. This is file-level coverage evidence, not an issue key.
- Why it matters: the component coordinates route changes, cancellable loads, save/delete operations, confirmation, and focus behavior. Low coverage leaves those state transitions less visible during later UI changes.
- Proposed change: add focused tests for stale-load cancellation, create/edit route changes, save errors, delete confirmation/cancel, and keyboard/focus handling. Keep pure formatting and model behavior in existing unit tests.
- Behavior to preserve: current URLs, author-book versus user-book permissions, cancellation semantics, and modal accessibility behavior.
- Verification: tests assert externally visible route, modal, and operation outcomes; run BlazorAuto browser regression and both profile gates for any code change.
- Effort: medium; asynchronous route transitions and browser focus need controlled test support.
- Dependencies: none.
- Decision: fix in a future application-quality wave.
- Acceptance: high-risk modal transitions have behavior-focused tests and the component's measured coverage improves without excluding production lines.

### Q-005 — Split the LocalSingleNode collision preflight into reviewable checks

- Evidence: `python:S3776` keys `3496b328-0b1d-43af-8ecc-4490ed4d07b6` (BlazorAuto) and `1da6b910-3731-4c5a-89e0-4234d6b7264e` (React) at `Deployment/LocalSingleNode/Scripts/lib/collisions.py:28`; the function's cognitive complexity is 131 against the rule's 15 guideline. Related findings in the same function cover the Caddy checksum and static Caddy text scan.
- Why it matters: the function combines ownership markers, symlink and directory checks, Caddy configuration, Compose port/subnet inspection, and Docker resources. This is fail-closed setup logic, so reviewers need to see each invariant clearly.
- Proposed change: extract small read-only checks for owned paths, Caddy state, Compose bindings/networks, and existing Docker resources. Keep the public `check` entry point and return or raise the same actionable failures.
- Behavior to preserve: no unowned host path, listener, network, Caddy site, or resource is adopted; no mutation occurs during the preflight.
- Verification: retain the existing collision tests, add table-driven boundary cases for each extracted check, run LocalSingleNode unit tests and the repository deployment audit.
- Effort: large; behavior spans shared-host and privileged setup boundaries.
- Dependencies: none.
- Decision: fix after the MD5 verification basis in Q-002 is settled.
- Acceptance: all existing fail-closed cases remain covered, and each check has a direct test and a narrow responsibility.

### Q-006 — Make the Redis fallback test assert the behavior it names

- Evidence: `csharpsquid:S2699` keys `655b305a-ea46-4478-9e93-289f58a8f0eb` (BlazorAuto) and `6c52aa25-d84d-4a31-871f-78729cbe2c9b` (React) at `BlazorAutoApp.Test/Infrastructure/Hosting/RedisConfigurationTests.cs:33`.
- Why it matters: the test currently resolves `factory.Services` and passes if startup does not throw. The code is intended to register an in-memory cache when `Redis:AllowMissing=true`; an explicit assertion would protect that contract from unrelated startup changes.
- Proposed change: assert that the fallback `IDistributedCache` resolves and that the Redis health check is absent when the endpoint is a placeholder and fallback is enabled. Keep the existing negative test for fallback-disabled production.
- Behavior to preserve: production requires Redis unless the operator explicitly opts into the local/test fallback.
- Verification: run the focused Redis configuration tests and both profile test suites.
- Effort: small.
- Dependencies: none.
- Decision: fix.
- Acceptance: tests assert both fallback registration and required-Redis failure, without requiring a live Redis service.

### Q-007 — Share common LocalCluster and Cloud settings validation

- Evidence: `python:S3776` identifies `validate()` at `Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py:73` (keys `9c3b9547-18f7-4c0e-bfe6-9b21a717a8d8` / `1e253611-143a-4c1d-935f-f0a98d1d0805`, complexity 78) and `Deployment/Cloud/Scripts/Component/lib/cloud_settings.py:77` (keys `54491309-ebe7-42c6-838e-76ef052d42df` / `51185cca-82ba-448c-94a6-a637108a186b`, complexity 92). The reports also show 131 duplicated lines between the files.
- Why it matters: common port, DNS, retention, path, and observability validation can drift across deployment targets. Their required settings and Cloud-only network checks still differ.
- Proposed change: move only schema-independent validators into `Deployment/Common`; retain target-specific key sets and Cloud-only address checks in their owning modules.
- Behavior to preserve: exact accepted settings, error conditions, defaults, and rendered deployment contracts for both targets.
- Verification: add parity cases for shared inputs and target-specific cases, then run common, Cloud, LocalCluster, and deployment audit suites.
- Effort: medium; shared validators affect multiple deployment surfaces.
- Dependencies: none.
- Decision: fix.
- Acceptance: shared rules have one implementation, target-specific validation remains explicit, and both settings contracts produce equivalent results for equivalent input.

### Q-008 — Decompose simulation option parsing after higher-risk items

- Evidence: `csharpsquid:S3776` keys `c07fa85c-36ee-4a95-af69-094d5041a4db` (BlazorAuto) and `042277aa-50b9-4ac1-bc06-88876f1de0b2` (React) at `BlazorAutoApp.Simulation/Options/SimulationOptions.cs:67`; cognitive complexity 41. The existing `SimulationOptionsAuthTests` cover several credential and write-gate cases.
- Why it matters: option parsing mixes target selection, credential policy, write authorization, and profile validation. Small helpers would make safety gates easier to review without changing the CLI.
- Proposed change: separate target resolution, auth configuration, and write/deployed-target validation while retaining one immutable result and aggregated errors.
- Behavior to preserve: no password on the command line, environment-only credentials, local-only seeded demo account, and explicit gates for deployed targets and writes.
- Verification: expand table-driven parser tests for each option group; preserve `Scripts/RunSimulation.ps1` help and exit behavior; run the simulation contract tests.
- Effort: medium.
- Dependencies: Q-001 should settle the shared HTTP handler contract first if that code is changed in the same wave.
- Decision: defer until the security and coverage work is planned.
- Acceptance: the same arguments produce the same options/errors and safety gates, with each validation group independently tested.

## Reviewed findings with no immediate follow-up

| Finding | Review and decision |
|---|---|
| `python:S3516` at `Deployment/LocalSingleNode/Scripts/lib/doctor.py:46` (keys `2ae477d5-b59b-4429-88c5-0a2a1223e67a` / `54eb0af8-565a-42d6-850b-dc6f18194ce4`) | The method builds and returns a list of named checks whose boolean results depend on live host state. It does not always return the same value. Reviewed noise; no code change. |
| `python:S5332` at `Deployment/LocalSingleNode/Scripts/lib/collisions.py:85` (keys `439e80ec-6d02-4fda-b363-3879b4e68a8b` / `5bb47505-d963-4089-b136-65c7b77d5cdb`) | The `http://` literal is matched inside Caddy configuration text to detect a port-80 collision; this code does not issue an HTTP request. Reviewed noise; keep the static collision check. |
| `csharpsquid:S2068` on `User123` and `postgres` defaults (for example `7a82f2b5-f3eb-47a3-8811-cb53cbb32f21`, `8414802e-46f7-4940-9ca0-fab2d83c054f`, `6cc2cb39-bcb1-4397-82ee-0b7406a8ae68`, `85c584f0-a498-4a73-ac6d-2d91a009efd0`) | The findings point to local/demo credentials and sample connection strings. The simulation default is guarded to the local target, Docker local account seeding is controlled by `LocalAccounts:Enabled`, `.env.example` documents local PostgreSQL defaults, and deployment compositions inject connection strings from protected settings. No report finding identifies a live secret. Reviewed noise; keep production secrets injected and do not copy these defaults into deployment settings. |
| `csharpsquid:S2245` at `BlazorAutoApp.Simulation/Running/ScenarioRunner.cs:29` (keys `5e42d43c-bc21-4706-8e18-ac320bf64c56` / `5fbb4709-60cd-4a38-ae00-4de542e24da4`) | `Random` is seeded by `options.Seed` to make synthetic scenario selection reproducible. It does not generate credentials, tokens, or cryptographic material. Reviewed noise. |
| `javascript:S8786` at `BlazorAutoApp.React/scripts/openapi-contract.mjs:41` (key `34d0470d-6ef0-42d6-9b23-f7bd1fb49fa4`) | The expression `\n*` normalizes trailing line feeds in generated text; it is a single-character repetition rather than a nested or ambiguous backtracking pattern. Reviewed noise; no performance defect was observed. |

The SonarQube quality gate remains informational. Implement these items only through separately authorized, tested changes; do not suppress rules or exclude source just to reduce counts.
