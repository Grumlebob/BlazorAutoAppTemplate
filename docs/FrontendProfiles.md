# Frontend profiles

The tracked `frontend-profile.txt` is the only persisted selection. Its template value is `BlazorAuto`. The resolver validates the value for builds and orchestration; do not select a profile through machine environment state.

```powershell
python Scripts/Frontend/resolve_frontend_profile.py
python Scripts/Frontend/resolve_frontend_profile.py --override React
```

The override is temporary and does not edit the tracked file. To select React in a fork, change `frontend-profile.txt` to `React`.

## Supported profiles

- **BlazorAuto** is the default Interactive Auto Blazor client. It supports the template's account pages and protected user workflows.
- **React** is an optional public-only SPA. It adds no account UI or authenticated client API; protected APIs remain protected. See [Requirements](Requirements.md) for public/private product constraints and [React development](Frontend/React.md) for implementation.

Build inputs and output are isolated by profile: BlazorAuto compiles the Blazor client; React excludes it and serves a static client through ASP.NET Core, with no Node server in the final image. Releases pair BlazorAuto with BlazorAutoV1, or React with ReactPublicV1; deployment verifies the pair from the immutable release manifest. See [deployment operations](../Deployment/README.md).

## React hosting contract

The React host serves its selected static root. Only GET or HEAD requests accepting `text/html` fall back to `index.html`; never send API, health, missing assets, unsupported methods, or reserved account/provider paths to the SPA shell. `/Account`, `/account`, `/api/auth`, and provider callbacks are reserved case-insensitively and return 404. HEAD returns headers without a body. Public requests omit credentials; protected APIs keep returning JSON 401 to anonymous callers.

The production Content-Security-Policy (CSP) is self-only and blocks inline/eval scripts and framing. Responses also set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: local-network-access=()`. Production uses HSTS and HTTPS redirection. The shell and ordinary assets revalidate; fingerprinted assets are immutable. Keep these profile boundaries when extending the static client.

## Publish the other profile

A clone publishes the selected profile by default. To publish the other supported profile too, set the Actions variable `ADDITIONAL_FRONTEND_PROFILES` to the other profile name. Leave it unset for selected-only publication. CI builds and smoke-tests both releases; a failure in the additional release fails the workflow. This creates an image and migration artifact; it does not create an app instance or deploy it. Follow the chosen target's deployment guide to deploy a release.
