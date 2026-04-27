# Vertical Slice Cleanup Plan

## Status
Completed on April 27, 2026.

## Objective
Move the solution to strict feature-first vertical slices across `Core`, `Server`, `Client`, and `Test`, and remove the remaining `Services`-style structure in favor of `Features`.

## Current Gaps
- `BlazorAutoApp.Client` still uses `Services/*` and `BlazorAutoApp.Client.Services` namespaces.
- Core hull-image contracts live in `Core/Features/HullImages` while server/test place hull-images under inspections.
- `Program.cs` contains large feature-specific startup/pipeline logic (especially TUS upload flow) that should be feature-owned.
- Architecture tests currently enforce `*ClientService` / `*ServerService` naming, which conflicts with feature-centric naming.
- Client UI pages/components are under generic `Pages/*`, not fully co-located with feature API adapters.

## Target Shape

### Core
- `BlazorAutoApp.Core/Features/Movies/*`
- `BlazorAutoApp.Core/Features/Inspections/HullImages/*`
- `BlazorAutoApp.Core/Features/Inspections/InspectionFlow/*`
- `BlazorAutoApp.Core/Features/Inspections/VesselPartDetails/*`

### Server
- `BlazorAutoApp/Features/Movies/*`
- `BlazorAutoApp/Features/Inspections/HullImages/*`
- `BlazorAutoApp/Features/Inspections/InspectionFlow/*`
- `BlazorAutoApp/Features/Inspections/VesselPartDetails/*`
- Each feature owns:
  - endpoint mapping
  - server implementation(s)
  - EF configuration
  - feature registration/mapping extensions (composition)

### Client
- `BlazorAutoApp.Client/Features/Movies/*`
- `BlazorAutoApp.Client/Features/Inspections/HullImages/*`
- `BlazorAutoApp.Client/Features/Inspections/InspectionFlow/*`
- `BlazorAutoApp.Client/Features/Inspections/VesselPartDetails/*`
- Co-locate:
  - API client implementation
  - feature pages
  - feature components

### Test
- Keep and strengthen `BlazorAutoApp.Test/Features/*` structure.
- Update architecture tests to enforce feature namespaces instead of service naming.

## Phased Execution Plan

### Phase 1: Baseline and Safety Net
- Freeze baseline with full `build` + `test`.
- Snapshot current architecture test behavior.
- Define refactor constraints:
  - no route changes
  - no API contract changes
  - no DB schema changes

### Phase 2: Client `Services` to Feature Folders
- Move files from:
  - `BlazorAutoApp.Client/Services/MoviesClientService.cs`
  - `BlazorAutoApp.Client/Services/HullImagesClientService.cs`
  - `BlazorAutoApp.Client/Services/InspectionFlowClientService.cs`
  - `BlazorAutoApp.Client/Services/VesselPartDetailsClientService.cs`
  - `BlazorAutoApp.Client/Services/Http/ProgressStreamContent.cs`
- Into feature paths under `BlazorAutoApp.Client/Features/...`.
- Rename namespaces to `BlazorAutoApp.Client.Features.*`.
- Update DI registration in `BlazorAutoApp.Client/Program.cs`.
- Keep behavior identical.

### Phase 3: Core Namespace and Slice Alignment
- Move `BlazorAutoApp.Core/Features/HullImages/*` to `BlazorAutoApp.Core/Features/Inspections/HullImages/*`.
- Update namespaces/imports across server/client/test.
- Split large mixed files (no logic changes):
  - `InspectionFlow.cs` into contracts/entities by concern.
  - `VesselPartDetails.cs` into entities/contracts/enums.

### Phase 4: Server Feature Composition Extraction
- Add per-feature composition extensions, e.g.:
  - `AddMoviesFeature(...)`, `MapMoviesFeature(...)`
  - `AddHullImagesFeature(...)`, `MapHullImagesFeature(...)`
  - `AddInspectionFlowFeature(...)`, `MapInspectionFlowFeature(...)`
  - `AddVesselPartDetailsFeature(...)`, `MapVesselPartDetailsFeature(...)`
- Move TUS-specific setup from `Program.cs` into hull-images feature extension(s).
- Reduce `Program.cs` to orchestration and shared hosting concerns only.

### Phase 5: Client UI Co-location by Feature
- Move feature pages/components from generic `Pages/*` into each feature folder.
- Keep route templates unchanged (`@page` values remain the same).
- Keep shared layout/root routing in existing top-level app files.

### Phase 6: Architecture Rule Updates
- Replace naming-only rules (`*ClientService` / `*ServerService`) with slice rules:
  - implementation namespaces must be under `BlazorAutoApp.Client.Features.*` and `BlazorAutoApp.Features.*`.
  - no top-level `BlazorAutoApp.Client.Services` namespace remains.
  - API interfaces in Core still require client + server implementations.
- Update tests that anchor on old `Client.Services.*` type names.
- Update testing docs (`BlazorAutoApp.Test/TESTING.md`) to new conventions.

### Phase 7: Final Cleanup and Hardening
- Remove now-empty legacy folders.
- Run formatting/linting and full test suite.
- Do final grep sweeps for stale namespaces/paths:
  - `BlazorAutoApp.Client.Services`
  - `/Services/`
  - old class names that violate new conventions

## Acceptance Criteria
- Zero files under `BlazorAutoApp.Client/Services`.
- No internal namespace starts with `BlazorAutoApp.Client.Services`.
- All feature APIs implemented by exactly one client and one server implementation.
- `Program.cs` no longer contains feature-specific upload pipeline internals.
- All existing routes still resolve unchanged.
- `dotnet build BlazorAutoApp.sln` passes.
- `dotnet test BlazorAutoApp.sln` passes.

## Risks and Mitigations
- Namespace churn may break DI/type discovery.
  - Mitigation: phase-by-phase compile/test after each move.
- Razor component moves can break imports.
  - Mitigation: explicit `_Imports.razor` updates per feature area.
- Architecture tests may become brittle during rename window.
  - Mitigation: update tests in same commit as namespace/folder move.

## Suggested Commit Sequence
1. Client services folder + namespace migration.
2. Core hull-images relocation + namespace updates.
3. Server composition extraction from `Program.cs`.
4. Client page/component co-location by feature.
5. Architecture tests + docs updates.
6. Final cleanup commit (empty folders, residual references, final verification).
