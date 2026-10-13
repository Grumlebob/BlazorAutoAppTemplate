# BlazorAutoApp

BlazorAutoApp is a .NET 10 application template with two frontend profiles: `BlazorAuto`, the default Interactive Auto Blazor app, and an optional public-only React SPA. Both use the same ASP.NET Core backend. PostgreSQL stores app data; Redis supports distributed caching and Data Protection.

Run the local Docker stack:

```powershell
.\Scripts\RunLocal.ps1
```

## Start here

| Task | Guide |
| --- | --- |
| Understand contributor rules and product requirements | [AGENTS.md](AGENTS.md), [Requirements](docs/Requirements.md) |
| Run the app or change local settings | [Run locally](docs/HowToRunLocally.md) |
| Add a Blazor feature | [Feature guide](docs/HowToAddANewFeature.md) |
| Add a React public feature | [React feature guide](docs/Frontend/React.md#change-a-typed-public-feature) |
| Select a frontend profile | [Frontend profiles](docs/FrontendProfiles.md) |
| Run and verify checks | [Tests](docs/Test.md) |
| Prepare a fork | [Fork guide](docs/HowToForkThisRepo.md) |
| Choose and operate a deployment target | [Deployment guide](Deployment/README.md) |
| View or diagnose telemetry | [Observability guide](docs/ObservabilityGuide.md) |
| Run optional quality audits | [Quality tools](docs/Quality/QualityTools.md), [SonarQube](docs/Quality/SonarQubeAnalysis.md) |

Read only the guides needed for your task. The contributor rules point to required checks and integration steps.

## Repository map

- `BlazorAutoApp.Core/Features/` contains shared feature contracts and domain types.
- `BlazorAutoApp/Features/` contains server behavior and endpoint mappings.
- `BlazorAutoApp.Client/Features/` contains Blazor client behavior and UI.
- `BlazorAutoApp.React/` contains the optional React client.
- `BlazorAutoApp.Test/` contains integration, architecture and browser tests.
- `Deployment/` contains the three deployment targets and shared release tooling.
- `Plans/` contains tracked plans; `Plans.local/` is ignored scratch space.
