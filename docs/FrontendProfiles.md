# Frontend profiles

The tracked `frontend-profile.txt` is the only persisted selection. Its template value is `BlazorAuto`. The resolver validates the value for builds and orchestration; do not select a profile through machine environment state.

```powershell
python Scripts/Frontend/resolve_frontend_profile.py
python Scripts/Frontend/resolve_frontend_profile.py --override React
```

The override is temporary and does not edit the tracked file. To select React in a fork, change `frontend-profile.txt` to `React`.

## Supported profiles

- **BlazorAuto** is the default Interactive Auto Blazor client. It supports the template's account pages and protected user workflows.
- **React** is an optional static SPA with public catalog pages and a cookie-based account experience that is disabled by default. When enabled, it includes login, recovery and private Books routes while public catalog requests remain credential-free. See [Accounts](Accounts.md), [Requirements](Requirements.md), and [React development](Frontend/React.md).

Build inputs and output are isolated by profile: BlazorAuto compiles the Blazor client; React excludes it and serves a static client through ASP.NET Core, with no Node server in the final image. Releases pair BlazorAuto with BlazorAutoV1, or React with ReactPublicV1; deployment verifies the pair from the immutable release manifest. See [deployment operations](../Deployment/README.md).

## React hosting contract

The React host serves its selected static root. Only GET or HEAD requests accepting `text/html` fall back to `index.html`; never send API, health, missing assets, unsupported methods, or reserved account/provider paths to the SPA shell. `/Account`, `/account`, `/api/auth`, and provider callbacks are reserved case-insensitively and return 404 when the matching account feature is unavailable. `GET /api/client-config` exposes the no-store account capability; when accounts are enabled, React reads `/api/auth/session` and uses same-origin secure cookies plus the antiforgery header for writes. Private APIs return JSON 401 to anonymous callers. Public catalog requests omit credentials. `/auth` and `/my-books` are React client routes.

The production Content-Security-Policy (CSP) is self-only and blocks eval, framing and inline scripts other than the shell's hashed ones. HTML responses add a fresh `'nonce-…'` to `script-src` so Cloudflare JavaScript detections can inject their script; the app's own markup never uses the nonce. Responses also set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: strict-origin-when-cross-origin`. The React host adds `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-site` and a `Permissions-Policy` that denies camera, microphone, geolocation, payment, USB and local network access; the Blazor profile sends `Permissions-Policy: local-network-access=()`. Production uses HSTS and HTTPS redirection. The shell and ordinary assets revalidate; fingerprinted assets are immutable. Keep these profile boundaries when extending the static client.

## Publish the other profile

A clone publishes the selected profile by default. To publish the other supported profile too, set the Actions variable `ADDITIONAL_FRONTEND_PROFILES` to the other profile name. Leave it unset for selected-only publication. CI builds and smoke-tests both releases; a failure in the additional release fails the workflow. This creates an application image and a digest-pinned GHCR payload with its migration bundle; it does not create an app instance or deploy it. Follow the chosen target's deployment guide to deploy a release.
