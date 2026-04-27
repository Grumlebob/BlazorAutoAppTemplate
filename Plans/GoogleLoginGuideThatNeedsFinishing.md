# Google Login Guide (Needs Finishing)

This project now supports Google login in code, but final setup still requires Google Cloud credentials and deployment-specific redirects.

## What Is Already Done In Code

1. Added Google auth package:
   - `Microsoft.AspNetCore.Authentication.Google`
2. Added config keys in `BlazorAutoApp/appsettings.json`:
   - `Authentication:Google:ClientId`
   - `Authentication:Google:ClientSecret`
3. Added conditional Google auth wiring in `BlazorAutoApp/Program.cs`:
   - Google is only enabled when both values are non-empty.
4. Home navigation label changed from `Register` to `Account`.

## Remaining Setup (Required)

## 1) Create OAuth Credentials In Google Cloud

1. Go to Google Cloud Console.
2. Create/select a project.
3. Configure OAuth consent screen.
4. Create OAuth Client ID (type: Web application).
5. Add Authorized redirect URIs:
   - `https://localhost:7186/signin-google` (local HTTPS profile)
   - `https://<your-production-domain>/signin-google` (production)
6. Copy Client ID and Client Secret.

## 2) Add Credentials To App Configuration

Prefer environment variables (recommended):

```powershell
$env:Authentication__Google__ClientId="YOUR_CLIENT_ID"
$env:Authentication__Google__ClientSecret="YOUR_CLIENT_SECRET"
```

Or set them in secure config/secrets for your host.

## 3) Run And Verify

1. Start app:
   - `dotnet run --project BlazorAutoApp/BlazorAutoApp.csproj`
2. Open login page:
   - `/Identity/Account/Login`
3. Confirm Google login option is visible.
4. Test full round-trip sign-in.

## 4) Production Checklist

- Ensure production redirect URI is configured exactly (scheme/host/path must match).
- Ensure app runs behind HTTPS in production.
- Store secrets securely (do not commit real values to source control).
- Confirm callback path remains `/signin-google` unless intentionally customized.

## Known Gaps / TODO

- TODO: Add a short troubleshooting section for common Google OAuth errors (`redirect_uri_mismatch`, invalid client, consent issues).
- TODO: Add environment-specific examples (Docker/Kubernetes/Azure App Service).
- TODO: Add screenshot snippets of Google Console setup for team onboarding.
