# React authentication foundation

Status: implementation verified on main on 2026-10-16. All S00–S39 and AUTH01–AUTH36 evidence is recorded in [Progress.md](Support/ReactAuthentication/Progress.md), with final documentation integration and resource cleanup in the closeout PR linked from implementation PR #320. Selected: ASP.NET Core Identity with app cookies, separate accounts per cloned product, email/password account flows and optional environment-configured admin seeding. Live deployment and external email provisioning remain separate operator tasks; CarbonCalculator work requires a later request.

Read this plan, [ExecutionSpecification.md](Support/ReactAuthentication/ExecutionSpecification.md) and [Progress.md](Support/ReactAuthentication/Progress.md). This plan owns scope and delivery order; the execution specification owns exact contracts and resolves ambiguity in older prose or draft code. Progress owns evidence and the next action. Implementation must satisfy all three; preserve security requirements when making a documented equivalent implementation choice. No unanswered product preference blocks execution.

## 1. Scope

<a id="11-long-term-production-recommendation-after-the-account-isolation-decision"></a>

Build a frontend-independent Identity backend and React account UI. Reuse UserManager, SignInManager, EF stores and Data Protection. The ASP.NET host serves the SPA and API on the same HTTPS origin. Use app cookies and explicit antiforgery validation for JSON mutations. Do not implement password hashing, session tokens or recovery cryptography independently. [Microsoft SPA guidance](https://learn.microsoft.com/en-us/aspnet/core/security/authentication/identity-api-authorization?view=aspnetcore-10.0).

Included:

- Email/password login, logout, session status and session revocation.
- Optional self-registration, confirmation, resend, forgot/reset password and email change through configured email delivery and a bounded encrypted database outbox.
- Account settings, password change, personal-data export and deletion with password reauthentication.
- Optional operator-provisioned Admin through ordinary ASP.NET environment variables and the ignored root `.env` for local Compose.
- An authenticated React Books example with owner-scoped create/list/update/delete.
- Disabled mode preserving the existing public React baseline.

MFA, passkeys and Google/other external login are excluded. Do not add their React UI, endpoints, configuration or delivery phases. Existing Blazor capabilities/schema remain supported; this task does not remove unrelated template behavior. No shared cross-product identity, SSO service, browser bearer tokens or additional production server.

The template owns identity/session primitives. Product projects, invoices, retention, membership and permissions belong to the later product plan. Do not edit CarbonCalculatorDelivery.md during this task.

## 2. Inspected starting point

- LoginFeatureExtensions already registers Identity cookies, EF stores, roles and framework token providers.
- React deliberately omits credentials and account endpoints; Vite already proxies `/api` over HTTPS.
- Blazor account email is a no-op; it cannot represent working delivery in the new feature.
- Legacy Blazor demo seeding has published-account cleanup. Preserve that cleanup without overwriting the operator admin.
- Books already filters by immutable user ID. Add explicit CSRF protection for enabled cookie-authenticated writes.
- Data Protection persists through Redis/filesystem. Independent products need separate stable App:Name, session identity and storage/database access.
- ReactPublicV1 remains the release acceptance identifier. Its public checks stay intact and gain a capability-aware enabled-mode branch; authenticated acceptance also needs actual browser/API evidence. There is no additional frontend build target.

These are source observations, not a completed security audit.

## 3. Configuration contract

Bind startup-validated options under `Accounts` through existing JSON/environment providers. Compose passes the ignored root `.env`. Direct `dotnet run` uses environment variables; use the existing secret/configuration mechanism rather than assuming user secrets take precedence after AddAppConfiguration. The React API development script reads only `Accounts__*` values from root `.env` with Node's standard parser, with existing process variables taking precedence. Do not import Docker service names/connection settings into host development. Never expose seed/SMTP secrets to Vite or browser builds. No runtime dotenv parser is needed in the web host. Changes to account capability/configuration require an app restart; do not hot-reload routing and security policy independently.

| Setting | Default | Meaning |
| --- | --- | --- |
| Accounts:Enabled | false | Map new account APIs and enable their policies; disabled React remains public-only. |
| Accounts:RegistrationEnabled | false | Self-registration; requires configured email delivery. Provisioned-account-only mode needs no mail service. |
| Accounts:WriteLimit:PermitLimit / WindowSeconds | 20 / 300 | Additional account-write limiter; no request queue; applies to both enabled account route families. |
| Accounts:PublicOrigin | empty | Canonical HTTPS frontend origin for email links; required with email. Never construct links from untrusted Host headers. |
| Accounts:Email:Host | empty | SMTP host; empty explicitly disables email/recovery capability. |
| Accounts:Email:Port | 587 | TLS SMTP port. |
| Accounts:Email:Security | StartTls | StartTls or SslOnConnect only; keep certificate verification. |
| Accounts:Email:Username / Password | empty | Private SMTP credentials; both present together when used. |
| Accounts:Email:From | empty | Valid sender mailbox required with SMTP. |
| Accounts:Email:MaxAttempts | 3 | Bounded outbox attempts; delivery/lease rules are fixed in the execution specification. |
| Accounts:AdminSeed:Enabled | false | Explicit startup provision after migrations. |
| Accounts:AdminSeed:Email / Password | empty | Required when seeding is enabled; framework validation applies. No default credentials. |

Use centrally pinned MailKit for SMTP. An existing SMTP service or suitable free tier works; no paid provider is mandatory. Validate setting names without printing full options or secrets. Send plain-text messages with encoded one-time tokens. Use the existing PostgreSQL database and an ASP.NET BackgroundService for a bounded encrypted outbox; no additional queue service is needed. Public email requests acknowledge processing uniformly with 202, never expose a recipient-specific SMTP error and never claim delivery. The worker records redacted failure metrics and bounded retries. This deliberately replaces the draft's synchronous SMTP/503 behavior: direct sending leaks account existence during recipient/provider failures and leaves account creation separate from delivery intent. Follow the exact schema, capacity, lease, retry and privacy rules in ExecutionSpecification.md §5.

Validation must reject partial seed credentials, invalid sender/recipient formats, malformed canonical origins and mismatched SMTP username/password. Require a bare HTTPS origin with no userinfo, query, fragment or additional path. An enabled seed password must meet the same policy as a new ordinary account. Empty or disabled settings must never activate a default account. Keep configuration/secret names portable; no machine-specific deployment values belong in this plan.

### Optional admin setup

Document this shape with empty credentials in `.env.example`:

```dotenv
Accounts__Enabled=true
Accounts__AdminSeed__Enabled=true
Accounts__AdminSeed__Email=
Accounts__AdminSeed__Password=
```

Fill the ignored file or protected runtime environment, start after migrations, then use normal React login. Direct development uses the same variable names in the API process. No committed passwords and no automatic real admin creation during this task.

Seeder contract:

1. Disabled means no account/role writes. Enabled while Accounts is disabled is invalid configuration.
2. Validate complete email/password configuration and framework password rules before changing data. Even if an Admin already exists, validate supplied settings without replacing its credentials.
3. Create the fixed Admin role and a new confirmed local user with that role atomically. Trusted operator provisioning supplies email ownership proof for this account.
4. An existing Admin at that email is unchanged: no password reset, unlock, confirmation change or security-stamp change on restart.
5. An existing ordinary account at that email causes a clear failure. Never promote it automatically.
6. Serialize concurrent seeds for one database and roll back partial creation. Wrap the transaction in the existing EF execution strategy; use the current PostgreSQL transaction lock rather than a process-local semaphore.
7. Disable/remove seed settings after provisioning. Deleting an account while seeding stays enabled intentionally recreates it on a later restart; document this.
8. Log generic outcomes, never credentials. Admin does not bypass resource ownership. No administration dashboard is required.

Admin here means the fixed Identity role and an authenticated account available to future product policies. The example's private Books remain owner-scoped. No special login form, password bypass or all-users management API is included. This seed is initial provisioning, not an ongoing password-reset mechanism. With email disabled, recovery is a deliberate operator procedure; document how to enable delivery or use a separately authorized framework-based recovery operation. Never reset or unlock an existing admin automatically because the environment password changed.

## 4. HTTP and session contract

Map `/api/auth` only when enabled. An always-available, credential-free `GET /api/client-config` returns `{ schemaVersion: 1, accountsEnabled: boolean, applicationId: string }` without issuing cookies. React uses that explicit capability before requesting a session. A missing/invalid configuration response, or a missing session endpoint when accounts are enabled, is an unavailable/misconfigured state; never interpret an arbitrary 404 as feature-disabled. Metadata generation describes the real endpoints without opening a database or SMTP connection. Disabled account runtime endpoints remain 404.

| Operation | Contract |
| --- | --- |
| GET /session | Anonymous-safe capability/current-user DTO plus antiforgery token; no-store. Signed-in profile contains stable user ID, email and role names. |
| POST /login | Email/password/remember-me; failed-password lockout enabled; generic 401 for invalid, unconfirmed, locked or unsupported credentials. |
| POST /logout | Authenticated and CSRF validated; clear current app cookie. |
| POST /logout-all | Authenticated and current password verified; rotate security stamp and clear current cookie. |
| POST /register | Registration capability required; accept email only, return generic 202 for existing/new email, and atomically create an eligible pending account plus confirmation intent. Password is chosen after mailbox proof; no automatic login. |
| POST /resend-confirmation | Email capability required; generic 202 regardless of existing/confirmed status, duplicates or recipient cooldown. |
| POST /confirm-email | Validate user/token through Identity, then atomically set the user-chosen password and confirmed status. No automatic login. |
| POST /forgot-password | Email capability required; generic 202 for unknown/unconfirmed/eligible users; durable intent for eligible users only. |
| POST /reset-password | Validate framework token and new password; revoke prior sessions; no automatic login. |
| POST /change-password | Authenticate current password, rotate security stamp, sign out; require subsequent login. |
| POST /change-email | Authenticate current password; persist confirmation intent for the proposed address without changing the account yet. |
| POST /confirm-email-change | Validate user/email/token, update email and username consistently, revoke sessions; no automatic login. |
| POST /export | Authenticate current password; export profile and owned example records, excluding all credentials/keys/tokens. |
| POST /delete | Authenticate current password; atomically delete owned example records and account, then sign out. |

Use bounded annotated request DTOs, typed responses and safe ProblemDetails. Bound account bodies to 16 KiB before JSON binding; bound emails to 254 characters, IDs to 128 characters and tokens to 4096 characters. Every JSON mutation validates `X-CSRF-TOKEN`, including login and token-consumption endpoints. Private fetch is same-origin and never automatically retries mutations. Refresh the antiforgery token after session changes. Apply auth rate limiting to `/api/auth` independently of `/Account`, and retain the normal API/global protections. Start with an additional per-client limit of 20 account writes per five minutes; password lockout also bounds attacks distributed across client addresses. Document that in-process rate counters do not become a distributed limiter across replicas. Public author-book reads remain credential-free.

Enabled private operations also require `X-Expected-User` containing the user ID observed by the UI/session bootstrap. Compare it against the authenticated principal before use-case execution; it never supplies identity or grants access. Missing/mismatched expected user returns the specified 409 session-change problem. Apply this to private Books reads/writes and authenticated account operations, including logout. Both React and the retained Blazor transport participate. This closes the cookie-change race between a client-side session precheck and the actual request. See ExecutionSpecification.md §3.

Protect enabled private Books writes too. When the shared policy is enabled for a Blazor build, adapt its WebAssembly Books transport to obtain a request token; do not break a retained consumer while securing React. Disabled mode must preserve existing Blazor behavior. If enabled Blazor registration consumes IEmailSender, bind actual configured delivery or make that capability honestly unavailable; a no-op email sender must not silently strand newly confirmation-required accounts. The future implementation must resolve this compatibility seam explicitly, not assume the React UI replaces all Blazor account paths.

Enabled cookies are app-specific, host-only, Secure/HttpOnly and SameSite Lax, with a `__Host-` name, Path=/ and no Domain. Derive a safe stable cookie identifier from App:Name and the environment; never include a deployment version or replica ID. The antiforgery cookie is separately named, Secure/HttpOnly and host-only. Use eight-hour fixed expiry, or fourteen-day fixed expiry with remember-me; no sliding renewal. Validate security stamps on every authenticated request for prompt revocation, accepting the account-store lookup cost. Identity's stamp validator can request cookie renewal: explicitly preserve absolute expiry instead of accidentally extending tickets while refreshing claims. Password change/reset, logout-all and deletion invalidate old sessions on the next validation; in-flight requests are not retroactively cancelled. Confirmation/reset tokens last one hour.

Use minimum **15 Unicode code points** for new passwords and maximum 128, framework hashing, five failed attempts and fifteen-minute lockout. The execution specification pins the offline common-password source and defines consistent Unicode/DTO handling. Do not require arbitrary character mixtures; allow spaces, password managers, paste and autofill. Do not trim, truncate or silently change existing credentials. Existing valid credentials can still sign in without satisfying the new-password length rule. No arbitrary periodic changes; require change on evidence of compromise. These choices are informed by current guidance, without claiming formal NIST compliance. Generic email responses reduce enumeration without claiming identical timing. Never log bodies, email-link secrets or cookies. React email callback secrets use URL fragments and are removed from history before forms render. Retained Blazor callbacks need explicit query redaction and a clean redirect because they use existing server-rendered routes. [Antiforgery](https://learn.microsoft.com/en-us/aspnet/core/security/anti-request-forgery?view=aspnetcore-10.0), [Identity configuration](https://learn.microsoft.com/en-us/aspnet/core/security/authentication/identity-configuration?view=aspnetcore-10.0), [password guidance](https://pages.nist.gov/800-63-4/sp800-63b.html).

Framework-generated confirmation tokens are not automatically a complete one-use workflow. Refuse confirmation after the account is already confirmed; refuse an email-change replay after it is committed; verify that password reset invalidates its token through the updated security stamp. Confirmation/change/reset races must not create mismatched username/email state. Use the EF execution strategy and transactions for multi-write sensitive operations, with fresh tracked state on retry. Do not rely on process-local locks across replicas.

Email-first registration is deliberate: an attacker must not choose a password for somebody else's address and retain it when that person later confirms. A new public pending account has no usable password. Confirmation requires explicit mailbox proof and choosing a password; existing unconfirmed accounts also replace any old password only after that proof. Repeated registration never overwrites credentials, confirms users or clears lockout. Enabled Blazor registration/confirmation must use the same rule; preserve legacy disabled-mode behavior separately.

Anonymous private endpoints return 401 rather than login HTML. Set no-store on account/private responses including errors before endpoint execution. Preserve legacy Blazor behavior when the new Accounts feature is disabled.

## 5. React experience

- Preserve public Home/Books and add compact account navigation only when enabled.
- Routes: `/auth/login`, `/auth/register`, `/auth/confirm-email`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/confirm-email-change`, `/auth/settings`, `/my-books`. Existing `/Account` remains reserved for Blazor.
- Keep account feature state in memory. Use the generated OpenAPI contract and a separate credentialed client; public calls still omit credentials.
- Show labels, pending states, errors and honest disabled-capability messages. Prevent duplicate submits.
- Registration first asks for email. The confirmation page asks for a new password after the emailed proof is opened. State the next step clearly; do not advertise public signup when registration is disabled.
- Cancel/remove private queries on account transitions. Keys include user ID; session changes broadcast across tabs without tokens/private data. Recheck session on focus and before private mutations.
- A private 401 invalidates session and asks for login without retrying writes or exposing another user's cached data. Preserve unsaved form input until deliberate navigation. Allow only safe local return paths.
- Ignore late session/query results after an account transition or unmount. A read/write initiated for one account must not be displayed or saved as another account's action if the shared cookie changes. Bind private request results to the expected user and recheck the server principal where needed; cancellation alone does not prove isolation. Keep an expired user's unsaved draft in memory, but hide it from a different newly signed-in user until explicitly discarded. Do not persist passwords or callback tokens in browser storage, query caches, analytics or broadcasts.
- Settings provide password/email change, logout-all, export and explicitly confirmed deletion with current password. Seeded Admin is a role, not an ownership bypass.
- My Books demonstrates existing owner-scoped CRUD. Keep the SPA SSR-disabled and production served by ASP.NET.

## 6. Granular delivery packets

Execute the numbered checklist in ExecutionSpecification.md §8; each entry names its evidence and prerequisite. A00 recovers/reconciles the draft and establishes the verification fixtures. A01–A06 below group the work; they are not permission to postpone tests or accumulate a single unreviewed implementation. Use small coherent code PRs with all applicable gates. For a new, finer requirement in the execution specification, add the corresponding evidence rather than treating the shorter acceptance row as a waiver.

### A01 — Shared options and composition

1. Inspect the preserved draft, current origin/main and the source map in section 10. Adopt useful code after review; do not blindly reapply its patch.
2. Add startup-validated Accounts options and annotated contracts under Login; reconcile the draft's old password limits with the final 15-character policy.
3. Extend Identity composition with configuration/environment inputs; keep disabled legacy behavior and review enabled Blazor compatibility.
4. Configure cookie isolation, stamp validation without lifetime extension, token/password/lockout policy and the bounded offline password validator.
5. Register feature services without live resource dependencies during metadata generation. OpenAPI must describe the actual enabled contract even though runtime mapping is optional.
6. Add no-store/body-limit middleware, explicit JSON CSRF and auth route throttling.
7. Implement credential-free client capability discovery and the expected-user guard before private use-case execution.

Exit: one documented startup capability controls real endpoint composition, valid configuration and consistent security policy; disabled/public and retained frontend behavior remain explicit.

### A02 — Optional admin bootstrap

1. Add scoped startup seeding after migrations, using UserManager/RoleManager and transactional database locking.
2. Enforce create-only/idempotent/refuse-promotion behavior in section 3.
3. Wire it independently of Blazor demo seeds.
4. Add opt-in examples with empty credentials and local API `.env` loading.
5. Document deployment through protected runtime environment, never tracked secrets.

Exit: repeated/concurrent startup safely provisions one complete Admin, ordinary users cannot be promoted, and no SMTP service is required. Prove normal React sign-in when A03 is available; do not create an A02/A03 dependency cycle just to declare the seed complete.

### A03 — Session and private vertical slice

1. Implement session/login/logout/logout-all and regenerate real OpenAPI/TypeScript contracts.
2. Add private client and session provider with fresh CSRF, 401 handling and tab coordination.
3. Implement login, account navigation and protected My Books CRUD.
4. Protect enabled Books writes; retain credential-free public catalog calls.
5. Preserve disabled/public route and release behavior.

Exit: two separate real accounts can maintain their private collections, and cookie/account changes cannot leak previous query results or save a draft under the wrong user. A fake principal or login screenshot alone does not satisfy this packet.

### A04 — Account lifecycle and email

1. Add TLS-only SMTP adapter, canonical link factory, encrypted database outbox/migration/worker and explicit email capability.
2. Implement register/resend/confirm and generic forgot/reset flows; commit account state and mail intent together and keep SMTP outside database transactions/retry delegates.
3. Add password/email changes, revocation, export and transactional deletion.
4. Build matching views; consume fragment secrets once and clear history.
5. Keep provisioned-account mode honest when email is disabled; no silent no-op delivery.

Exit: actual messages are captured by an isolated local SMTP fixture, account links work through the HTTPS frontend origin, and token/password/data failure cases leave consistent persisted state. No external messages or paid provider account are necessary to prove implementation behavior.

### A05 — Runtime configuration through retained deployment targets

1. Trace settings from inventory/private inputs through generated app.env, Compose/container environment and ASP.NET configuration for LocalSingleNode, LocalCluster and Cloud. Root `.env` is a local convenience; it is not automatically propagated to production containers.
2. Add optional public account settings and optional private seed/SMTP inputs through each target's established configuration and secret mechanisms. Default to disabled and do not make new secrets mandatory for existing public/Blazor releases.
3. Validate/escape newline, quote and interpolation characters when generating dotenv, JSON, YAML or environment files. SMTP/seed passwords must never be inserted through shell-built commands, logged diffs, command-line arguments or readable artifacts. Preserve an existing protected value unless deliberate rotation is authorized.
4. Keep generated secret files protected and task-scoped. Document an idempotent provisioning/update procedure and how to disable seeding without destroying data. Do not add a second unmanaged host-level auth service.
5. Extend render/audit/fixture coverage for disabled, provisioned-only and email-enabled configurations. Preserve app-isolated key persistence and same-app replica compatibility. Reuse scoped deployment scripts and locks; this task does not dispatch deployments or create real users on a shared node.

Exit: all retained target configurations can carry the optional feature without hand-editing running containers, exposing secrets or breaking unchanged deployments.

### A06 — Documentation, verification and integration

1. Update Requirements, FrontendProfiles, React development and focused account operations docs.
2. Keep the immutable public release pairing and add explicit capability-aware checks plus mandatory enabled authentication browser/API acceptance. Disabled mode still requires /api/auth/login to be absent; enabled mode requires a genuine method error for GET on the POST-only route. Missing assets/callbacks and unknown API paths remain real 404s in both modes.
3. Update deployment audit rules if behavior they inspect changes; retain disabled/public checks.
4. When implementation and verification are authorized, add/run authentication, seed, CSRF, revocation and ownership coverage and the full local gate. Keep dotnet build/test sequential. Tests were not authorized or run during the paused draft session.
5. Review complete diff; stage explicit paths; open code PR; require green build-test-push on exact head; merge and verify exact-main CI.
6. Record commits/evidence and remove finished task checkout/branches under AGENTS.md. Preserve other sessions.

## 7. Acceptance inventory

All pending until demonstrated.

| ID | Required result |
| --- | --- |
| AUTH01 | Disabled routes stay 404, public React acceptance passes, private APIs deny anonymous access. |
| AUTH02 | Provisioned Admin signs in through React; role exists and credentials remain private. |
| AUTH03 | Disabled/partial/invalid seed settings behave correctly; restarts never change passwords/lockout. |
| AUTH04 | Ordinary accounts cannot be promoted; concurrent starts create one complete Admin without partial records. |
| AUTH05 | Cookie isolation/flags and fixed normal/remember-me lifetimes match section 4. |
| AUTH06 | Missing/wrong CSRF rejects every account mutation and enabled private Books writes. |
| AUTH07 | Invalid/unconfirmed/locked login is generic; failed-password policy and throttling work. |
| AUTH08 | Two real users cannot access each other's records; Admin remains owner-scoped. |
| AUTH09 | Expiry/account changes clear private caches across tabs without exposing stale user records. |
| AUTH10 | Register/confirmation/resend/reset/email change work against controlled local SMTP; unknown addresses get generic responses. |
| AUTH11 | Invalid/expired/replayed framework tokens fail; callback secrets stay out of HTTP queries and consumed history. |
| AUTH12 | Wrong password permits no sensitive operation; credential changes, logout-all and deletion revoke old sessions. |
| AUTH13 | Export excludes credentials; account/data deletion is atomic and owner-scoped. |
| AUTH14 | Provisioned login works without SMTP; registration/recovery cannot pretend delivery works. |
| AUTH15 | Metadata needs no database/email; schemas match endpoints; React typecheck/lint/build pass. |
| AUTH16 | Both frontend profiles, required audits, exact-head and exact-main CI pass; Blazor remains supported. |
| AUTH17 | Persistent user database and app-isolated keys are included in documented backup/restore boundaries. |
| AUTH18 | Optional account/seed/SMTP settings flow safely through all retained deployment targets; disabled releases require no new secrets. |
| AUTH19 | New password rules, failure throttling and absolute ticket expiry are consistent; claims/stamp renewal never extends the fixed lifetime. |
| AUTH20 | Enabled shared policies do not break retained Blazor registration or WebAssembly Books writes; unavailable email is honest. |
| AUTH21 | Late responses, cross-tab cookie changes and user transitions cannot expose another account's results or save its unsaved draft. |
| AUTH22 | Explicit cookie-free capability discovery distinguishes disabled, unavailable and misconfigured states. |
| AUTH23 | Server expected-user checks reject cookie-change races before private reads/writes; client never labels a response as another owner. |
| AUTH24 | Registration and mail intent commit atomically; public email requests keep generic statuses during recipient failures. |
| AUTH25 | Outbox leases, bounded retries, expiry, deduplication and replica contention operate without sending inside transactions. |
| AUTH26 | Sensitive data/password proof is revalidated after account locks on retries; commit uncertainty cannot repeat destructive effects. |
| AUTH27 | Duplicate legacy normalized-email preflight refuses unsafe enforcement; clean fixtures upgrade without automatic account merging or confirmation. |
| AUTH28 | Pinned password-list/license/hash and code-point length policy work consistently across seed, DTOs and both frontends. |
| AUTH29 | Errors have declared codes/statuses; validation does not expose email existence or raw Identity/provider exceptions. |
| AUTH30 | Test/browser fixtures use real Identity cookies, isolated PostgreSQL, TLS SMTP and application-owned teardown; no fake-principal coverage substitution. |
| AUTH31 | Enabled Blazor login/logout/register/reset/management follows shared policy and cannot bypass disabled registration or CSRF. |
| AUTH32 | Enabled accounts use the selected PostgreSQL key store; legacy key import, outbox decryption, restart and isolated restore are proven. |
| AUTH33 | Runtime settings round-trip special-character credentials through every retained target without printing or corrupting secrets. |
| AUTH34 | Packaged React image passes enabled and disabled HTTP/browser checks; metadata/OpenAPI/gates run without production credentials. |
| AUTH35 | Progress maps every acceptance ID and numbered step to final integrated commits and evidence; no required row is silently deferred. |
| AUTH36 | Email-first registration cannot preserve an attacker-chosen password after mailbox confirmation; repeats never alter credentials before proof. |

Authorization for tests/browser checks and actual external email follows session instructions. Local SMTP fixtures send nothing to real people. Do not claim live delivery, restored deployment state or an independent security audit from compilation/source inspection.

## 8. Clone contract

Each clone owns its user store, stable App:Name, cookie identity, Data Protection storage and permissions. Never copy template account data or real secrets. Replicas of one product share compatible keys; sibling products do not. The same email can have independent accounts/passwords/deletion in multiple products.

Identity provides authentication. Products extend resource ownership, membership, retention, export and deletion. Admin claims do not imply unrestricted customer-data access.

## 9. After completion

Return to CarbonCalculatorDelivery.md only after this foundation is integrated and verified. Then reconcile saved-project and file contracts around authenticated server ownership while retaining the approved product journey. This task does not implement or deploy CarbonCalculator.

## 10. Execution evidence

### 10.1 Owner steering and present state

The owner selected the simplified scope and requested the plan before implementation. A partial draft was started under the earlier wording, then paused when the owner clarified **do not implement yet**. The owner subsequently instructed that the small changes/draft must be kept and mentioned here so a new chat can continue. The current task therefore publishes only this Markdown plan. Do not interpret the draft's existence as permission to finish, merge, deploy or run authentication tests now.

The draft is preserved as uncommitted changes in the registered worktree on branch `feat/react-authentication-foundation-20261015`, based on `8599ffa527239a699f888c4aceea808f9829573a`. Locate it with `git worktree list`; do not assume a machine-specific path. This checkout remains intentionally open, owned by the paused React authentication task and needed for the next chat. Do not clean, reset, overwrite or delete it. The separate documentation task branch/worktree can be closed after this plan is integrated.

A second copy exists in the primary checkout's ignored `Plans.local/ReactAuthenticationFoundation/DeferredImplementation-20261015.patch`. Verified SHA-256: `DAC42AD1A33F1B5FBF3C956C4042A5DDAE181FCEC636A243E96F53CB6466B08A`. It contains the draft code/configuration/generated API changes, not this revised plan. The patch was restored into the paused worktree after its hash and applicability were checked. Do not apply it again on top of those changes. It is a recovery aid, not a verified implementation or retained repository artifact.

### 10.2 What the preserved draft contains

| Area | Existing draft paths and behavior | Remaining review |
| --- | --- | --- |
| Backend | `BlazorAutoApp/Features/Login/Accounts/`: options, contracts, endpoints, operations, SMTP sender, request protection and transactional admin seed | Review every failure/race/authorization path against this final plan; draft uses the earlier 12-character minimum |
| Composition | `Program.cs`, Books endpoints, AppRateLimiting and metadata-only OpenAPI host | Validate enabled/disabled wiring, actual auth limiter and frontend compatibility |
| React | `BlazorAutoApp.React/app/features/accounts/`, `app/routes/account.tsx`, `app/routes/my-books.tsx`, root/routes/site shell | Review session races, cache/draft isolation, token consumption, accessibility and generated client behavior |
| Blazor transport | `BlazorAutoApp.Client/Features/Books/BooksAntiforgeryHandler.cs` and client Program | Latest addition has not been built or exercised; review enabled behavior and avoid hidden compatibility regressions |
| Local setup | `.env.example`, React `scripts/dev-api.mjs` | Empty opt-in seed/SMTP examples and API-only Accounts env loading; no real .env or credential was created |
| Packages/contracts | MailKit 4.18.1, centrally pinned System.Security.Cryptography.Pkcs 10.0.13, generated OpenAPI/TypeScript files | Recheck exact dependency compatibility and advisories; regenerate contracts after final changes |

The package pin was added because the first MailKit restore reported vulnerable transitive Pkcs 10.0.0. A subsequent React backend build had zero warnings/errors after the pin. This is evidence from that checkpoint, not a blanket dependency security claim.

### 10.3 Checks actually performed before the pause

- An earlier React backend checkpoint compiled successfully, with zero warnings/errors after the dependency pin.
- OpenAPI/TypeScript generation succeeded without live database or SMTP.
- React typecheck and lint succeeded after initial issues were corrected.
- A production React build succeeded, including its existing root prerender and SPA fallback.
- Later changes to cookie renewal, Blazor transport, account draft ownership and development env loading were not all rebuilt together. Do not label the final preserved draft verified.
- No tests were added or run. No browser sign-in, seeded account, database/runtime authentication, actual SMTP message, deployment, provider registration or production infrastructure change was performed. No implementation commit or PR was created.

### 10.4 First actions in the next chat

1. Read this plan, the execution specification, Progress and AGENTS.md. Activating the linked goal is the implementation/verification request; do not ask the owner to authorize those same actions again. Without activation or an equivalent request, keep planning only.
2. Locate the paused branch with `git worktree list`. Inspect tracked, untracked and ignored files and any live processes. Resume its task binding using the local agent workflow if applicable. Preserve other sessions' work.
3. Fetch origin/main and review changes since the recorded base. The primary plan on main is authoritative; the paused checkout may still contain the older investigation text. Bring the new plan into the implementation context without overwriting its uncommitted source changes or other sessions' files.
4. Inspect the draft against this plan and the archive manifest/hash. Reuse sound portions; address known gaps before expanding. Do not apply the archive twice or assume generated files prove runtime behavior. If both private draft and archive are unavailable, implement from the tracked specification; their absence is not a product blocker.
5. Start A01, then A02/A03 as vertical outcomes, A04, A05 and A06. Carry backend, client, failure paths and relevant acceptance together. Ask for missing information only when it genuinely blocks progress.
6. Follow the implementation gate and exact-head/main CI rules when authorized. Do not publish or deploy merely because the new chat resumes implementation. Return to CarbonCalculator only after this foundation is integrated and verified.

### 10.5 Readiness and human inputs

The plan is ready to start in a new chat. No unresolved product choice blocks A01–A03: independent email/password accounts, cookie sessions and optional create-once Admin are specified. Provisioned-account mode does not require SMTP. The implementer can use isolated generated credentials/database fixtures and local SMTP for authorized verification; do not ask the owner to provision external services just to begin.

Only enabling real public registration/recovery later needs a usable sender/SMTP account, its protected credentials and any sender-domain verification. Those are optional deployment inputs, outside template-goal completion; prove delivery behavior using the local TLS fixture. Use existing authorized services/credentials if available in a later deployment task. Manual provider-console or inbox interaction is a blocker only if the agent cannot perform it safely. Actual deployment remains a separate authorized action. No manual blocker prevents completing this template implementation.

### 10.6 Suggested new-chat request

> /goal Plans/ReactAuthenticationFoundationGoal.md
