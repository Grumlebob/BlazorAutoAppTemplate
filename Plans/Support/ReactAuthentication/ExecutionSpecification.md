# React authentication: execution specification

Authority: [ReactAuthenticationFoundation.md](../../ReactAuthenticationFoundation.md) defines scope. This document supplies final implementation decisions and executable checkpoints. [Progress.md](Progress.md) records evidence. The preserved draft is input for review, not the specification. Goal activation authorizes implementation and verification; this review publishes documentation only.

## 1. Review findings and resolved decisions

| Finding in the earlier plan/draft | Required resolution |
| --- | --- |
| A 404 session probe could mean disabled, wrong deployment or broken routing | Public cookie-free client configuration explicitly declares account capability; missing enabled routes are errors |
| Account logic concentrated in AccountOperations and one large route component | Small vertical operations and focused page components; shared security/transport primitives only |
| Module-scoped CSRF/user variables and overlapping refresh promises | One session controller per mounted application, with generation checks and single-flight refresh owned by that generation |
| A cookie could change after the browser checked its owner | Server compares an expected-user header with the actual principal before private use cases |
| Existing callback pages mutate state during GET | Enabled callbacks render proof forms; mutation occurs only on protected POST |
| Registering a password before mailbox proof can preserve an attacker's password | Public registration takes email only; confirmation includes explicit password choice |
| SMTP failure could disclose whether an account exists; creation and delivery intent were separate | Uniform public 202 responses plus atomic encrypted outbox intent; SMTP runs outside request transactions |
| Retried transactions could use stale password proof or repeat side effects | Fresh scope/account lock and credential/stamp checks inside each attempt; explicit commit verification |
| Confirmation-required shared policies could strand Blazor users behind a no-op sender | Enabled Blazor consumes shared policy/delivery; disabled legacy mode remains compatible |
| The old logout route disables antiforgery and password login disables failed-attempt lockout | Enabled shared mode applies the selected policy to both frontend entry points |
| Identity's unique-email option does not establish a database constraint | Reversible migration adds unique normalized-email enforcement after a refusing preflight |
| Default password length counted UTF-16 while the plan promised characters | One authoritative code-point validator, bounded DTOs and matching frontend validation |
| The phrase "use a password list" left licensing and runtime dependencies open | Pin the source/hash/license below; embed a bounded resource; no runtime download |
| Local .env was confused with production secret propagation | Explicit adapter and render checks for every retained deployment target |
| ReactPublicV1 checks assumed account endpoints could never exist | Capability-aware HTTP checks retain disabled assertions and add enabled checks; real auth browser/API tests are mandatory |
| Test factory can supply a fake authenticated principal | Account acceptance uses real Identity cookies and an anonymous baseline; fake principals do not count |
| Bare "preserve draft" could leave a new chat blocked on private files | Reuse the local draft or recover its verified patch; otherwise implement from tracked contracts |
| Earlier pause/permission wording could stop an activated goal repeatedly | Invoking the goal authorizes implementation, tests and gated PR integration; live operations remain outside scope |

These are source-review findings and design corrections, not runtime exploit results. No account security feature is considered passed by compilation alone.

## 2. Code shape and compatibility boundaries

Keep the existing Identity registration and EF database; extend them rather than registering another competing application scheme. Use `Accounts` startup options as an immutable validated snapshot. Route mapping, frontend capabilities, seeding, worker registration and security policy must observe the same snapshot. Metadata-only hosting describes real contracts without starting seeders/workers or contacting services.

Suggested feature layout under `BlazorAutoApp/Features/Login/Accounts/`:

- `Session/`: session query, login/logout/revoke operations and DTOs.
- `Provisioning/`: admin seeder and its PostgreSQL transaction lock.
- `Registration/`: email-only request and proof/password completion.
- `Recovery/`: reset request and token/password completion.
- `Management/`: change password/email, export and delete, each with a focused handler.
- `Email/`: link factory, outbox entity/configuration/worker and `IAccountMailTransport` with MailKit implementation.
- `Security/`: request guards, password validator, safe result/error mapping and options validation.

Use thin HTTP adapters calling focused handlers. A handler may use UserManager/SignInManager directly. Keep HttpContext, IResult and transport parsing at the HTTP boundary where practical. Do not create a generic repository, generic account command bus, custom password hasher or a new framework to implement these operations. A narrow mail transport seam supports real SMTP and deterministic failure fixtures; it is not a provider marketplace.

Use classes with bounded properties for secret-bearing request/options objects; avoid generated record ToString output containing passwords. Split option checks into named rules with setting-name-only errors. Pass CancellationToken and TimeProvider through handlers/worker so cancellation and expiry are testable. Match existing repository conventions where an equivalent structure is simpler; document any material deviation in Progress.

React uses small pages/forms under `app/features/accounts/`, a separate typed credentialed client and one application-owned session controller. Public transport remains unchanged. Do not add account state to a process-wide singleton or public query cache. Keep the existing SPA hosting, CSP and HTTPS development flow.

Enabled Blazor is another consumer of the same policy, not a second independent account implementation. Adapt its email-first register/confirm, login, logout, password/reset/email management, and Books transport. Keep its existing advanced sign-in features working without exposing them in React. The new password-only React endpoints refuse users whose existing account requires an unsupported additional sign-in step; they must not bypass that requirement. Legacy disabled behavior stays compatible, including published-demo-account cleanup. Do not add new demo credentials.

## 3. Wire contracts, guards and state

### Capability and session

- `GET /api/client-config`: `{schemaVersion:1, accountsEnabled:boolean, applicationId:string}`; public credentials omitted, Cache-Control no-store, no Set-Cookie. applicationId is a stable non-secret 32-hex-character digest of App:Name plus environment, never a user/host/version value. A malformed/missing response is unavailable, never inferred-disabled.
- `GET /api/auth/session`: enabled-only, credentialed, no-store; `{enabled:true, registrationEnabled, emailEnabled, csrfToken, user:null|{id,email,roles}}`. A 200 anonymous session is different from disabled/unavailable. Never return password hashes, stamps, pending-email secrets or tokens other than the request CSRF token.
- Start in `loading`; configuration selects `disabled` or session discovery. Session discovery selects `anonymous`, `authenticated` or `unavailable`. During `checking`, suppress private results and disable mutations while preserving the current user's draft in memory. Failed transport does not become a false anonymous/disabled success.

### Request DTOs

The main plan names endpoint paths. Apply these final bodies; JSON property names follow the existing web serializer:

| Operation | Body |
| --- | --- |
| login | email, password, rememberMe |
| register / resend-confirmation / forgot-password | email |
| confirm-email | userId, token, newPassword |
| reset-password | userId, token, newPassword |
| confirm-email-change | userId, token, email |
| change-password | password, newPassword |
| change-email | password, email |
| logout | empty JSON object |
| logout-all / export / delete | password |

Normalize submitted email by trimming outer whitespace and using Identity's configured normalizer; preserve a sensible display value. Email-as-username and normalized-email uniqueness are explicit app policy, not a claim that all mail servers compare local parts identically. Never renumber existing user IDs.

Requests must be application/json, at most 16 KiB, email at most 254 UTF-16 units, user ID at most 128, token at most 4096. Password DTO transport bound is 256 UTF-16 units; the authoritative validator accepts 15–128 Unicode code points for new passwords. Login/current-password proof accepts existing shorter credentials up to that transport bound. Do not trim/normalize password contents before hashing or verification. Report actual field names; never echo submitted values.

### Principal, expected user and CSRF

1. HTTPS/trusted forwarded-header handling precedes auth. Private no-store and body limits cover errors before endpoint execution. Rate policies cover both shared account route families and do not disappear behind an authorization failure.
2. Authenticate with the actual Identity cookie. For private operations, missing/expired authentication returns 401 before user-specific work.
3. Enabled private account operations and private Books reads/writes require `X-Expected-User` equal to the current principal's immutable local ID. Missing/mismatched value returns 409 `AccountChanged`, without returning either ID. It is a race guard, never a source of identity. Public catalog/client-config, session bootstrap and anonymous login/proof/email-request endpoints do not require it.
4. Validate `X-CSRF-TOKEN` for every new JSON mutation and retained enabled cookie-authenticated write before use-case execution. Blazor forms use framework antiforgery; remove the logout bypass in enabled mode. Do not put CSRF tokens in URLs.
5. Client attaches its captured expected user, never a value silently overwritten by a later session refresh. Compare the captured session generation when any response arrives. Discard responses from older generations, including success bodies and late errors.

Use one named `account-writes` policy with Accounts:WriteLimit defaults 20 permits/300 seconds and QueueLimit=0. Validate positive permit/window bounds; tests override these through the same options. Partition by resolved client IP so changing usernames or signing out cannot create fresh limits. Keep persistent per-account failed-password lockout and database mail cooldowns as separate protections. Do not replace the chosen limit with the template's looser legacy authentication limit or imply that each replica's memory counters are globally shared.

Private 401/409 clears visible private data, cancels/removes private queries and refreshes session once. Do not loop or replay a mutation automatically. A rejected login/current-password check is not itself proof that a previously valid session ended; use a distinct error code and refresh only when appropriate. Broadcast only an account-change signal; session cookies and profile data never enter BroadcastChannel/localStorage. Scope the channel to applicationId from client-config so separate instances never share a global channel name. Focus/session rechecking still works when BroadcastChannel is unavailable.

Single-flight refresh is held inside the session controller. Only its own generation may publish or clear its pending promise. Unmount aborts requests and invalidates that generation. Focus, visibility, logout, reset/change, broadcasts and 401/409 transitions all use this one path. Form drafts are associated with an owner ID; another user's session cannot reveal or submit them. Safe return paths are limited to known local `/my-books` and `/auth/settings` destinations; reject encoded/protocol-relative/backslash variants rather than inventing an open redirect parser.

### Status and problem codes

Use a stable `code` extension in ProblemDetails and declare actual success/error statuses in OpenAPI. HTTP adapters map known domain/Identity failures explicitly, not by returning arbitrary result.Errors descriptions.

| Status | Contract |
| --- | --- |
| 200 | session/config/profile/export or a completed account mutation |
| 202 | generic register/resend/forgot/change-email acknowledgement; no delivery or target-availability guarantee |
| 400 | RequestInvalid, CsrfInvalid, TokenInvalid or PasswordRejected; bounded field errors; token failures do not reveal account existence |
| 401 | AuthenticationRequired for missing session, CredentialsInvalid for rejected sign-in/password proof; no lockout/unconfirmed/existence flags |
| 403 | CapabilityDisabled or actual forbidden policy; do not encode a wrong password as forbidden |
| 404 / 405 | unknown/disabled route or known route's unsupported method; never SPA HTML for API errors; declare Allow for 405 |
| 409 | AccountChanged or generic AccountConflict; no other user's email/ID or raw uniqueness exception |
| 413 / 415 | bounded-body/export limit or unsupported JSON content type |
| 429 | bounded authentication rate limit with Retry-After; per-recipient cooldown is a silent generic 202 on public email endpoints |
| 503 | actual unavailable database/queue capacity, not recipient-specific SMTP outcome |

All private/account responses are no-store; credential/token responses never enter analytics, traces or exception payloads. React renders errors as text and has pending, retry, empty and failure states. New views require keyboard focus, label/field-error association, password-manager support and a show-password control that does not alter values.

## 4. Identity policy, persistence and transactions

Use the main plan's cookie flags, fixed lifetimes and every-request stamp validation. Verify cookie renewal events do not extend absolute expiry. A remember-me choice persists the cookie for fourteen days; normal login has an eight-hour ticket and a browser-session cookie. No per-device session-list/revoke UI is promised: logout revokes this browser, logout-all revokes all by stamp. Stamp checks consult current account state/roles; account deletion or a revoked stamp fails closed. Keep these claims distinct from cancellation of already-running requests.

Prefer framework cookie/stamp behavior with an asserted fixed ExpiresUtc over another custom validator. The pinned framework already contains renewal handling for non-sliding tickets; prove actual expiry before retaining the draft's event wrapper. Do not replace the framework principal validator while trying to disable renewal. [Pinned validator source](https://github.com/dotnet/aspnetcore/blob/v10.0.13/src/Identity/Core/src/SecurityStampValidator.cs).

Use one code-point password validator across public completion/reset/change and admin provisioning. Embed SecLists `Passwords/Common-Credentials/10k-most-common.txt` from commit `f1196104c5594a19d78b486c52c0794b9d947993`, raw SHA-256 `68782d6a4a19a4768d5f15dd66bd534e7a33055cc755411e33f16d18c50fdcce` (10,001 source lines), with its MIT notice and source metadata. Parse line endings once, bound resource size to 256 KiB and compare complete candidates case-insensitively; do not reject arbitrary substrings. Also reject the complete app-name/email-as-password value. Do not claim this covers every breached password. Fetch once during authorized implementation, verify the hash, retain attribution and embed the resource; no runtime external call. [Source](https://github.com/danielmiessler/SecLists/blob/f1196104c5594a19d78b486c52c0794b9d947993/Passwords/Common-Credentials/10k-most-common.txt), [license](https://github.com/danielmiessler/SecLists/blob/f1196104c5594a19d78b486c52c0794b9d947993/LICENSE).

Framework defaults must not silently add conflicting character/UTF-16 rules. Retain framework hashing and token providers; custom code checks policy, not cryptography. Count code points with .NET Rune enumeration and matching JavaScript code-point logic. Invalid Unicode/control characters receive a bounded validation error; test spaces/non-BMP characters, exact bounds and unchanged existing credential verification.

Add migrations for unique non-null NormalizedEmail, outbox and the selected PostgreSQL Data Protection key table. Preflight duplicate non-null normalized emails and incompatible existing values; refuse with counts and private remediation instructions, never merge accounts, confirm users, reset passwords or delete rows. Fixture tests prove both clean upgrade and safe refusal. Actual production data remediation is a later operator decision, not a blocker to implementing a correct refusing migration. Preserve existing Identity/passkey tables and unrelated Books migrations. Validate migration bundles for both profiles.

For multi-write sensitive operations and provisioning, create a fresh DI scope/UserManager/AppDbContext inside each execution-strategy attempt; both stores must share that context/transaction. Use a transaction-scoped PostgreSQL advisory lock for provisioning and a parameterized account-row lock for mutations. Never hold a lock during SMTP. Recheck current account state and cookie security stamp after the lock, then validate password/token inside that attempt. Proof captured before a lock/retry is insufficient.

Make commit-uncertainty handling explicit: generate stable operation/job IDs outside retry delegates, verify persisted success where EF supports commit verification, and recognize an already completed state without repeating external effects. Do not clear a broadly shared ChangeTracker to simulate a fresh unit of work. Return authentication cookies/results only after the database work commits. Return a safe 409 on real concurrency conflict; no unbounded retries or exposed provider exceptions. [EF retry/commit guidance](https://learn.microsoft.com/en-us/ef/core/miscellaneous/connection-resiliency), [transactions](https://learn.microsoft.com/en-us/ef/core/saving/transactions).

Public pending registration creates no password. Eligible pending accounts queue confirmation; confirmed duplicates get the same 202 without account changes. On confirmation, lock/reload the account, validate its framework confirmation token, apply a newly chosen valid password and confirmed status atomically, then revoke any old stamp. This also handles a legacy unconfirmed password safely after proof. Wrong/expired/replayed tokens change nothing. Reject unsupported stronger-account requirements rather than bypassing them.

Change-email confirms the proposed address before changing email/username; commit those fields and stamp together. The first valid committed change invalidates other outstanding tokens via the changed stamp. Its request returns the same 202 for an eligible, already-owned or unchanged target; do not disclose address availability through a duplicate-only 409. Invalid proof and a conflict discovered while committing return the declared safe token/conflict error without identifying another owner. Password reset rotates the stamp but does not automatically clear lockout. Do not automatically unlock an account from bootstrap, repeated signup or failed proof. Document the fifteen-minute lockout wait.

Export requires current password and includes only the profile and owned sample data, without keys/stamps/credential material/outbox payload. Bound the sample export to 10,000 records and 10 MiB, returning a declared 413 rather than truncating. Delete requires current password inside the transaction, cancels queued mail, deletes user-owned mappings/private Books and the Identity account atomically. Preserve public catalog records or any referenced record not exclusively private to that owner. The other user's records and template seeds must be unchanged.

## 5. Durable email without a new service

Use one outbox table in the existing database. Minimum fields: stable ID/Message-ID, user ID, purpose, status, encrypted payload, CreatedUtc, ExpiresUtc, NextAttemptUtc, Attempts, LeaseId, LeaseUntilUtc and a safe failure code. Put recipient, callback/token/body and issuance stamp inside Data Protection-encrypted payload, not plaintext columns/logs. Use a dedicated protection purpose with a version. Store no plaintext password in this table. Back up keys and DB consistently.

- Purposes are confirmation, reset and email-change. Frontend composition supplies known React/Blazor route choices; the worker never accepts an arbitrary callback URL. PublicOrigin is a validated bare HTTPS origin. React links use a fragment; enabled Blazor proof GET is read-only, query secrets are redacted and redirect/navigation is cleaned after proof. Never log token-bearing SMTP bodies or worker exception details.
- Public request DTOs validate before account lookup. In one short transaction, apply account eligibility/creation and persist mail intent. SMTP never runs in the request or an EF retry delegate. Existing/unknown/ineligible users get the same 202 wording: request received; check email if applicable, and use resend if it does not arrive. Do not claim the email has been delivered or queued for an unknown address.
- Serialize capacity/deduplication decisions in PostgreSQL. Cap active jobs at 1,000; check capacity before account eligibility so a global 503 cannot identify an account. Operations enqueueing email acquire locks in the order global admission, account row, then outbox rows; keep this order consistent to avoid deadlocks. Permit one active intent per user/purpose, a sixty-second resend cooldown and at most five intents per user/purpose/hour. Suppressed public duplicates still return the same 202. Authenticated email changes may report their own cooldown explicitly, independent of target availability. Retain safe terminal metadata for 24 hours for quota accounting; clear payload on success/final failure and purge old metadata.
- Register an ASP.NET BackgroundService only for enabled email runtime, never metadata generation. Poll every five seconds, claim up to ten due jobs using SKIP LOCKED, commit a 45-second lease before sending, and use bounded concurrency. Reclaim expired leases. Every lease attempt consumes an attempt; default MaxAttempts=3, allowed range 1–5. Process shutdown cancels pending work without marking cancellation as delivered.
- Before sending, reload the account and validate the payload's issuance stamp/purpose/state. Cancel deleted, confirmed/no-longer-eligible or changed-stamp intents. Jobs expire after 45 minutes; framework tokens expire after one hour. State the actual link expiry time in the email rather than promising a fresh hour after a delayed send.
- SMTP is TLS-only, normal certificate validation, fifteen-second send timeout. Commit lease first, send outside transactions, and acknowledge using matching LeaseId. Retry transient failures after thirty seconds then two minutes, bounded by job/token expiry. Permanent recipient/authentication/decryption errors stop that job and set a safe health signal rather than crashing the worker. Retries can duplicate mail after an uncertain SMTP acknowledgement; reuse Message-ID, document this and keep token consumption safe. Do not claim exactly-once or guaranteed delivery after bounded failures.
- Capture counters/last-safe-health status without recipient/token labels. Queue outage/failure must be visible to the operator through existing observability/diagnostics; public success means accepted request, not delivered mail. SMTP degradation alone must not fail global liveness/readiness and take provisioned login/public catalog/database recovery offline. Database failure remains a real readiness failure. Do not dump worker exceptions containing SMTP conversation/recipient details.

The local SMTP fixture supports STARTTLS with a fixture CA trusted only by test-injected transport options. Production cannot set an insecure skip-certificate flag. Prove real SMTP capture and a separate rejected-certificate test. No external service account, DNS verification or human inbox is necessary for goal completion.

## 6. Configuration, keys and deployment acceptance

All feature switches default off. Seed-only requires no SMTP. Self-registration requires enabled accounts and complete email configuration; email-enabled/private recovery is independent of public registration. Validate partial SMTP/seed settings without reading secrets into diagnostic text. Use the main plan's root .env API-only allowlist; direct process environment wins. The sample file has empty passwords. New credentials never reach Vite, client-config, generated OpenAPI or public artifacts.

Trace optional fields through all retained targets' inventory/schema/private inputs, generated app.env/Compose and ASP.NET options. Use an explicit allowlist rather than allowing arbitrary environment injection. Safely encode dollar signs, hashes, quotes, spaces and equals signs; reject unsupported CR/LF instead of inventing an unsafe escaping scheme. Add round-trip render fixtures. Fresh seed settings must not rotate an existing app's protected values or be copied between apps. The implementation uses an isolated synthetic environment, never a live node or real account database.

For enabled accounts, select **PostgreSQL Data Protection persistence in the existing app database**, using the official Microsoft.AspNetCore.DataProtection.EntityFrameworkCore package and PersistKeysToDbContext with IDataProtectionKeyContext. This is a selected implementation, not another option for the executor to research. Same-app replicas share the app DB/ring/discriminator; independent products use separate app databases and stable cookie identities. Ordinary protected database backups now include users, outbox and keys together; test their restoration. Retain existing certificate/DPAPI key protection where configured and protect database/backups as secret material. Do not claim encryption-at-rest from persistence alone. Disabled legacy mode keeps its existing key-store behavior. [Official key-store provider](https://learn.microsoft.com/en-us/aspnet/core/security/data-protection/implementation/key-storage-providers?view=aspnetcore-10.0).

Enabled production keys must be wrapped with an app-owned certificate/private key stored outside the database; otherwise a database dump contains both outbox ciphertext and its usable decryption keys. Reuse the configured app-owned wrapping certificate where suitable; add DataProtection:KeyEncryptionCertificatePath/Password for targets without that existing source, and use framework ProtectKeysWithCertificate. Existing secret-setup adapters generate/protect a per-app certificate when needed, with no paid service. Share it only among that app's replicas; mount read-only with restricted access, back it up through protected secret recovery and never bake it into an image. Windows development can retain DPAPI; fixture Linux/production uses a generated certificate. Validate production readiness before starting accounts instead of silently storing unwrapped keys. Lost wrapping-key recovery is not solved by copying the database alone, so restart/restore acceptance must prove both inputs. Do not rotate/delete the old wrapping key on ordinary redeploy.

Add an idempotent legacy key import for initial enabled activation: after schema migration and before serving requests/starting the worker, read the configured app-owned old Redis/file XML repository and copy its framework repository elements into the DB without regenerating or deleting them. Preserve key IDs, revocation records and wrapping metadata; copying only key elements can resurrect revoked keys. Use framework XML repository semantics and stable document identities, not a custom key format. Preserve App:Name/discriminator and access to wrapping certificates/private keys. Serialize imports and reject conflicting XML for the same identity; an unreadable or ambiguously owned source fails activation rather than pretending there were no keys. Empty fresh installs can create a new ring normally. Keep old key sources untouched until upgrade/rollback is verified. Use coordinated app-scoped maintenance for a store transition; do not promise mixed-version/mixed-store rolling compatibility. Prove migration, revoked-key denial and repeated import in disposable fixtures, not real node mutations. Do not prune old keys while reports, tokens, cookies or outbox payloads may need them.

Keep ReactPublicV1 as the release acceptance identifier. Extend its HTTP runner to read client-config first. Disabled mode retains exact inactive-route 404/no-cookie checks. Enabled mode expects session JSON and known POST-only routes to reject GET with 405, while unknown API routes, callbacks, Blazor paths and missing assets remain 404. Public catalog requests stay credential-free. The public HTTP routine does not submit credentials. Add a separate deterministic browser/API account suite to the existing required CI job; it exercises a packaged React image in both runtime modes, including direct /auth and /my-books navigation and CSP/no-console-error checks. Preserve other deployment gates/audit rules rather than weakening them.

## 7. Verification fixtures and completion evidence

Extend the repository's existing test support. Use isolated PostgreSQL/Redis resources with owned labels, generated non-published test credentials, HTTPS origins and per-run cookie/key state. Read current CI/tool pins; do not invent fixed node addresses or change shared infrastructure to make tests pass.

Account integration must force real Identity authentication, not only its challenge handler: the current factory can install a fake test principal. Prove the initial anonymous client receives 401, then acquire an antiforgery token and sign in with the actual cookie flow when S13 is implemented. Use two separate cookie jars and an additional Admin. Cover disabled, seed-only and email-enabled configurations under both frontend profiles where shared behavior is affected. Use TimeProvider/fake time for application-owned lease/expiry and supported framework clocks. The pinned Identity token provider uses DateTimeOffset.UtcNow directly: assert the one-hour production setting, then use an isolated brief test lifetime and bounded wait to prove token expiry, not an ineffective fake-clock advance or a custom cryptographic provider. Use explicit fixture lockout end dates/short durations where the framework lacks a clock seam. Use barriers/deferred responses for cross-tab/transaction races. [Pinned token provider source](https://github.com/dotnet/aspnetcore/blob/v10.0.13/src/Identity/Core/src/DataProtectorTokenProvider.cs).

The mandatory auth suite covers every AUTH row in the main plan, including failures. Link each row to exact test names/commands and a sanitized result artifact in Progress. Use Playwright for actual React forms, reloads, token links, keyboard flows, privacy after account changes and packaged-image navigation. Browser tests must run explicitly in required CI rather than remain silently skipped behind the repository's default RUN_E2E opt-in. Never substitute mocked account UI for SMTP or real cookie acceptance.

For restart/restore proof, use only a disposable app database/key ring: create/sign in, queue mail, stop the fixture, restart using the same persisted inputs, then perform an isolated restore and prove expected account access, stamp behavior and outbox decryption. Expired jobs stay expired. Capture migration revision and owned resource cleanup. This is fixture recovery proof, not authorization to restore a live deployment.

Run the full current local gate in [docs/Test.md](../../../docs/Test.md#local-gate), generated API checks, React typecheck/lint/unit/build and the explicit auth browser/image suite before code push. Keep dotnet build/test sequential in a checkout. When Razor classes change, rebuild/commit Tailwind output. CI must validate new migrations, render fixtures and applicable deployment audit rules as well as the runtime feature.

Completion requires all S00–S39 checkpoints and AUTH01–AUTH36 demonstrated on the integrated source; exact-head build-test-push before merge; green exact-main CI; complete documents/runbook; private secrets preserved; and finished-task cleanup. Optional public SMTP provisioning, live deployment, MFA/external login and CarbonCalculator implementation are outside this goal and cannot be mistaken for unfinished template work.

Final Progress-only documentation updates use AGENTS.md's documentation-only exception. Record the last green integrated code-main SHA and the final documentation-main SHA; verify code/configuration content is unchanged between them. Do not wait for a deliberately skipped documentation CI run or create an endless follow-up commit merely to record the previous documentation commit's SHA. PR descriptions may hold final integration/cleanup evidence.

## 8. Numbered execution checklist

Each checkpoint is small enough to resume independently. Implement its failure paths and tests with the behavior, not as a final afterthought. Use small coherent gated PRs; do not publish a half-enabled account runtime. Dependencies below are logical, not a requirement to open forty PRs.

| ID / packet | Action | Evidence / prerequisite |
| --- | --- | --- |
| S00 / A00 | Read goal, plan, this spec, Progress, AGENTS and current repo status | Activation recorded; no repeated implementation/test approval request |
| S01 / A00 | Locate/resume preserved draft, verify archive hash if used, inspect all edits/processes | Saved manifest; never apply patch twice; clean implementation fallback if absent |
| S02 / A00 | Fetch main, reconcile newer changes without stashing/resetting others, inventory applicable gates | Recorded source/base/tool versions and next action |
| S03 / A00 | Establish real-cookie HTTPS integration and local TLS SMTP fixtures | Anonymous denial/TLS readiness, generated test users and owned resources; actual production sign-in proof follows at S13 |
| S04 / A01 | Split draft into focused handlers/forms and replace module-global session state | Code review records removed unsafe coupling; no custom auth framework |
| S05 / A01 | Implement validated immutable options and cookie-free client-config | Disabled/enabled/error capability tests; no secrets/cookies in config |
| S06 / A01 | Add safe DTO/error contracts and metadata-only mapping | OpenAPI generation without services; declared statuses/problem codes |
| S07 / A01 | Configure cookies/stamps/fixed expiry and authoritative password validator | Boundary/legacy-password/renewal tests, pinned resource/license/hash |
| S08 / A01 | Add unique-email preflight/migration, outbox and DB key-store schema | Clean upgrade, duplicate refusal, both profile migration bundle checks |
| S09 / A01 | Add no-store/body limits, CSRF, expected-user guards and account limiter | Guard ordering, missing/mismatch, oversized JSON and 429 tests |
| S10 / A02 | Implement locked transactional create-once Admin seeding | Disabled/partial/invalid/existing-admin/ordinary-user cases |
| S11 / A02 | Prove concurrent seed, rollback, uncertain commit and role assignment | One complete account, no password/unlock changes, generic logs |
| S12 / A02 | Add empty .env examples and API-only Accounts allowlist loading | Process-env precedence, special characters and no Vite secret leak |
| S13 / A03 | Implement session/login/logout/logout-all over real Identity | Generic failures, lockout, correct cookie properties and revocation |
| S14 / A03 | Implement session controller/state machine/generation ownership | Deferred old success/error, focus/unmount and single-flight race tests |
| S15 / A03 | Add login/account navigation and user-scoped private transport | Keyboard/browser login, fresh CSRF, expected-user captured per request |
| S16 / A03 | Complete My Books CRUD with private queries and owner-bound drafts | Two users/Admin, expiration, wrong-owner reads/writes, no automatic mutation replay |
| S17 / A03 | Adapt enabled Blazor session/logout/Books guards | Real forms/WASM transport work; disabled regression preserved |
| S18 / A04 | Implement encrypted mail intent/transport/link factory | Payload secrets absent from DB plaintext/logs; known React/Blazor origins |
| S19 / A04 | Implement outbox worker leases/capacity/cooldown/retry/expiry | Concurrent workers, dead worker, full queue, TLS/rejected certificate and failure capture |
| S20 / A04 | Implement email-only registration and password-choice confirmation | Atomic account+intent; duplicates/pending/replay/pre-hijack tests |
| S21 / A04 | Implement resend/forgot/reset and matching forms | Uniform 202 during SMTP/recipient failure, token expiry/revocation, no delivery claim |
| S22 / A04 | Implement current-password change and logout-all UI | Fresh locked proof, stamp invalidation, correct wrong-password versus expired-session errors |
| S23 / A04 | Implement proposed email proof/commit and matching forms | Email/username/stamp atomicity, concurrent changes, no GET mutation |
| S24 / A04 | Implement bounded export and atomic owner-safe deletion | No secrets/public/other-owner data loss; outbox cancellation; rollback/size tests |
| S25 / A04 | Complete enabled Blazor registration/recovery/management adapters | Shared capability/policy/delivery honored; legacy callback redaction; no stronger-auth bypass |
| S26 / A04 | Regenerate API/types and finish error/accessibility states | No hand-edited schema, strict typecheck/lint, malformed response/error tests |
| S27 / A05 | Trace each deployment adapter's settings and secret flow | Explicit inventory of actual files; optional inputs default off |
| S28 / A05 | Implement optional LocalSingleNode account/seed/mail environment | Render/schema/secret round-trip fixtures; no live node writes |
| S29 / A05 | Implement matching LocalCluster and Cloud adapters | Existing public/Blazor inputs remain valid; safe quoting/redaction |
| S30 / A05 | Implement enabled PostgreSQL key persistence and idempotent legacy import/backup contract | Legacy Redis/file fixtures, same-app replicas, coordinated transition and synthetic backup/restore evidence |
| S31 / A06 | Extend capability-aware HTTP acceptance and deployment audit | Both modes, real 404/405, unchanged missing-asset/credential-free public checks |
| S32 / A06 | Make auth integration/unit/browser/image suites mandatory in required CI | No production credentials, no silently skipped account browsers |
| S33 / A06 | Run complete enabled/disabled packaged React journeys | Direct routes, CSP/console, real forms/TLS SMTP, two users/tabs/reload |
| S34 / A06 | Prove disposable restart/restore with account DB, keys and jobs | Same revision, expected session semantics, no token resurrection |
| S35 / A06 | Update focused Accounts runbook, Requirements, FrontendProfiles and React docs | Exact local admin recipe, capabilities, recovery/quota/backup and clone boundaries |
| S36 / A06 | Review all changed paths and execute full local gate plus auth checks | Sequential builds/tests; failure fixes precede push; sanitize artifacts |
| S37 / A06 | Open/finish PRs and require exact-head green build-test-push | Record full head and merge SHAs; retarget dependent PRs before branch cleanup |
| S38 / A06 | Fetch final main and require exact-main CI plus content/acceptance verification | Every AUTH row points to final evidence; no material unmerged fix remains |
| S39 / A06 | Close Progress and clean reconciled task resources/worktrees/branches | Preserve primary/private inputs/other sessions; archive required evidence with SHA-256 |

## 9. Open-question disposition and operating limits

No product question is left for the executor: use the selected defaults/contracts, PostgreSQL already in the template for identity/outbox/enabled key persistence, MailKit, separate accounts, optional Admin, disabled public registration until configured, and the numbered order. Standard library/package versions may change; recheck official sources and advisories at implementation, choose the smallest compatible free update and record it. Do not pause for routine naming/layout choices.

Do not require an operator's production SMTP account, DNS, deployed hostname, hardware authenticator, runner registration or live deployment to finish this goal. Loopback HTTPS, isolated databases, generated fixture accounts and TLS SMTP prove the template behavior. Actual production credentials or an incompatible live dataset are deployment inputs; document them honestly without turning fixture readiness into a false production claim. If required CI/tooling fails, diagnose/fix authorized repository problems and continue independent work; never weaken gates or claim completion while a real blocker remains.

## 10. Review checkpoint

2026-10-15: reviewed the tracked plan and preserved draft source without modifying implementation. Resolved the findings in section 1 and expanded the executable contract, acceptance and goal. Original compile checkpoints remain historical; the reviewed implementation has not been tested during this documentation task. Integration evidence for this review belongs in its PR; Progress remains pending for goal execution.
