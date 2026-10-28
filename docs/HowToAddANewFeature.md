# Add a feature

Use this page to choose the implementation route. Read [Requirements](Requirements.md) for product rules. Check the tracked `frontend-profile.txt` to identify the target client. Read [FrontendProfiles](FrontendProfiles.md) when changing profile selection; React work follows [its feature guide](Frontend/React.md).

## Order

1. Define the behavior, data scope, access rules, routes, and what is out of scope.
2. For shared behavior, put domain types and API contracts in `GrumPlates.Core/Features/{Feature}`. UI-only features keep their state and types in the selected client; add no unused server contract or DTOs.
3. When server behavior is needed, add it in `GrumPlates/Features/{Feature}`. Skip persistence when the feature does not store data. Follow [Server feature guidance](Features/Server.md).
4. Implement the selected UI: Blazor under `GrumPlates.Client/Features/{Feature}`, or React under `GrumPlates.React/app`. Do not add both clients unless both profiles need the feature.
5. Test behavior at its boundary: components/state for UI-only work, APIs for server behavior. Add browser coverage for important user workflows. Use [Infrastructure testing](Testing/Infrastructure.md) and [Browser testing](Testing/Browser.md).
6. Update configuration, observability, or operator docs only when the feature changes those behaviors. Run the [local gate](Test.md#local-gate).

## Existing project migration

For a fork identity and deployment target, use [HowToForkThisRepo](HowToForkThisRepo.md). Before implementation, inspect the source project and make a slice plan in `Plans/` using the [plan conventions](../Plans/README.md). Map each behavior to this template's Core, server, selected client, and tests. Plan existing-data imports separately from schema migrations; do not import data during app startup. Keep each slice small enough to verify and deploy.

## Boundaries

Core owns shared contracts and types; it has no EF Core, ASP.NET Core, or browser HTTP implementation. The client references Core, never the server. Server services enforce data ownership and authorization scope even when endpoints also require authorization. The client calls shared contracts through a client service or feature state; Razor components do not inject `HttpClient`. See the [server](Features/Server.md) and [Blazor](Features/Blazor.md) pages for the details and source examples.

The Books feature is a reference implementation, not a requirement that every feature use CRUD, caching, or the same UI. Start from the smallest useful slice, then consult the architecture checks in [Infrastructure testing](Testing/Infrastructure.md) and the actual source that matches your feature.
