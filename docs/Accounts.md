# Accounts

Accounts are optional and disabled by default. React reads the server capability before starting account requests. The server remains authoritative: hiding a link or route never replaces API authentication, authorization, antiforgery or cache policy.

Server implementation and Blazor Identity UI live under `GrumPlates/Features/Accounts`; shared DTOs live in `GrumPlates.Core/Features/Accounts/Contracts`. `ApplicationUser` resides in the feature's `Identity` folder but retains the CLR namespace `GrumPlates.Features.Login.Account` for Identity/EF compatibility. The shared context, design-time factory and historical migrations stay under `Infrastructure/Persistence`. The outbox entity and operations belong to Accounts; its EF mapping remains inline in the shared `AppDbContext`. See [architecture](Architecture.md) for composition and the deliberate Books-to-Accounts integration.

## Capabilities

| Configuration | Behavior |
| --- | --- |
| `Accounts:Enabled=false` | Account API routes are absent. React stays public-only, offers no private Books and creates no account session cookie. Legacy Blazor Identity behavior is retained. |
| `Accounts:Enabled=true`, email host empty | Login, logout, password change, export, deletion and private Books work. Registration, confirmation, recovery and email change stay unavailable. A configured Admin can be provisioned once with `Accounts:AdminSeed`. |
| `Accounts:Enabled=true`, email host and sender configured | The mail worker can send confirmation and recovery links. Registration additionally requires `Accounts:RegistrationEnabled=true`. `Accounts:PublicOrigin` must be a bare HTTPS origin. |

`GET /api/client-config` returns the account capability without user data or secrets. When enabled, React reads `GET /api/auth/session` for the current user, feature flags and an antiforgery token. The UI lives at `/auth/login`, `/auth/register` and related `/auth/*` routes; `/auth` redirects to login. `/my-books` is private. Account mutations use POST and the antiforgery header. API failures stay JSON responses rather than login redirects.

The authentication cookie is `Secure`, `HttpOnly`, `SameSite=Lax`, host-only and fixed at eight hours, or fourteen days when “remember me” is selected. Account and private API responses use `Cache-Control: private, no-store`. Passwords must contain 15–128 Unicode characters, contain no control characters, and differ from the application name and email; common passwords are rejected. Password changes, resets and confirmed email changes rotate the security stamp; account deletion removes the user. Each action revokes existing sessions.

Blazor retains its existing MFA, passkey and configured external-login capabilities in enabled mode. React's password-only sign-in does not bypass MFA. Blazor password recovery preserves MFA, and sensitive management still requires a valid session and current-password proof. New external users complete email-first registration, then sign in to link their provider; disabling registration also prevents external callbacks from creating accounts.

React hides private data while rechecking the session and clears private query caches when the account changes. Unsaved book drafts remain bound to their original application and user; another user must explicitly discard the previous draft before adding or editing a book. Deletion confirmation and account-management credentials do not carry across application or user changes. These boundaries follow [React's guidance on preserving and resetting state](https://react.dev/learn/preserving-and-resetting-state).

## Create a local React Admin

Use the Docker development setup from [How to run locally](HowToRunLocally.md). It generates the local HTTPS certificate used to protect the local PostgreSQL Data Protection key ring. Select `React` in `frontend-profile.txt` for this run; the file is the persisted profile selection.

Run setup if `.env` or the local certificate is missing:

```powershell
pwsh -File ./docker/setup-local.ps1
```

In the ignored `.env`, set the account values below. Keep values unquoted and edit the file directly; do not put the password in shell history. Replace the example address and placeholder password with local values.

```dotenv
Accounts__Enabled=true
Accounts__RegistrationEnabled=false
Accounts__AdminSeed__Enabled=true
Accounts__AdminSeed__Email=operator@example.test
Accounts__AdminSeed__Password=<private 15–128 character passphrase>
Accounts__PublicOrigin=
Accounts__Email__Host=
Accounts__Email__From=
Accounts__Email__Username=
Accounts__Email__Password=
```

Start the app and open the local HTTPS URL, normally `https://localhost:7186/auth/login`:

```powershell
.\Scripts\RunLocal.ps1 -NoBrowser
```

Startup creates the confirmed Admin account and `Admin` role if the address is new. It refuses to assign the role if that address already belongs to a non-admin account. The seed never changes an existing password. After the first successful startup, set `Accounts__AdminSeed__Enabled=false`, clear the seed email and password, save `.env`, and restart the app. Keep `Accounts__Enabled=true` to retain account access. The seeded role does not add an admin dashboard to the template.

The password must satisfy the account password policy and must not be common or match the email or application name. Do not use the legacy Blazor demo credentials or carry local seed values into a deployed environment. Keep `.env`, local databases and generated certificates out of commits and images.

## Email, quotas and delivery

Email requires `Accounts:Email:Host`, a valid `Accounts:Email:From`, and `Accounts:PublicOrigin`. `Accounts:Email:Security` accepts `StartTls` or `SslOnConnect`; username and password must either both be empty or both be supplied. Registration cannot be enabled without accounts and an email host. Email links use the configured HTTPS origin and keep token secrets in the URL fragment on the React routes. The exact environment keys and defaults live in [`.env.example`](../.env.example).

Enabled account POSTs are limited to 20 per client IP per five minutes. JSON account requests also use the API limit of 60 requests per minute. The outbox suppresses an active duplicate, enforces a 60-second cooldown and allows at most five intents per user and purpose per hour. It has a global capacity of 1,000 active jobs. A queued job expires after 45 minutes; its Identity link expires after one hour. The worker makes at most three attempts by default, then clears the protected payload. Public email requests return the same accepted response regardless of whether an address is known.

A database restore may replay an active pending job and produce a duplicate email; SMTP delivery cannot guarantee exactly-once delivery. The worker checks job expiry, link expiry, account confirmation and the current security stamp before sending. It cancels expired or stale intents and clears their protected payloads.

## Production key and backup recovery

When accounts are enabled, Data Protection keys and account data share the PostgreSQL database. Production keys are wrapped with the app-owned certificate and private key stored outside that database. A database dump alone cannot restore sign-in cookies or decrypt outbox jobs. Preserve the same app identity, deployment environment, database, certificate/private key and certificate password. Replicas of one app share those inputs; unrelated apps must not.

Keep the wrapping key across ordinary redeploys. Store it with protected off-host backups and never bake it into an image. Follow the selected target's backup verification and recovery procedures: [LocalCluster](../Deployment/LocalCluster/Operations.md#backup-and-restore), [Cloud](../Deployment/Cloud/Operations.md#back-up-and-restore-postgresql), or [LocalSingleNode](../Deployment/LocalSingleNode/Operations.md#backups-and-recovery). First-time legacy key-store import is a coordinated app-scoped transition; see the target operations guide and keep the old source until cookies and account mail have been verified.

Restart and restore acceptance uses disposable fixtures only. Do not treat a fixture restore test as authorization or a procedure for restoring live account data.
