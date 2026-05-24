# Better Slicing Plan

## Status

- [x] Phase 1: Prepare architecture tests.
- [x] Phase 2: Refactor Movies.
- [x] Phase 3: Refactor HullImages.
- [x] Phase 4: Refactor Inspection and InspectionFlow.
- [x] Phase 5: Refactor VesselPartDetails.
- [x] Phase 6: Refactor IdentityShowcase.
- [x] Phase 7: Clean up cross-cutting imports.
- [x] Phase 8: Verification.

## Goal

Move the application toward a modular monolith with feature-first vertical slices.

The target shape keeps `BlazorAutoApp.Core` as the shared, dependency-light feature contract layer, while `BlazorAutoApp` and `BlazorAutoApp.Client` keep runtime implementation details in matching feature folders.

This plan is intentionally architecture-test first: update the tests to describe the desired design, then move each feature until the tests pass.

## Target Rules

1. Core features are organized by feature, then by responsibility:

   ```text
   BlazorAutoApp.Core/
     Features/
       {Area?}/
         {Feature}/
           Domain/
           Contracts/
           UseCases/
             {UseCase}/
   ```

2. `Domain` contains entities, enums, value objects, and business rules.

3. `Contracts` contains API interfaces and shared DTOs used across multiple use cases.

4. `UseCases/{UseCase}` contains request/response DTOs for one operation.

5. Server implementation stays outside Core:

   ```text
   BlazorAutoApp/
     Features/
       {Area?}/
         {Feature}/
           Composition.cs
           Endpoints/
           Services/
           Persistence/
           Validation/
           Caching/
           Storage/
   ```

6. Client implementation mirrors the feature path:

   ```text
   BlazorAutoApp.Client/
     Features/
       {Area?}/
         {Feature}/
           {Feature}ClientService.cs
           Pages/
           Components/
           Http/
   ```

7. No feature code should use an `Infrastructure` namespace. Runtime implementation details should use clearer names such as `Persistence`, `Storage`, `Caching`, or `Services`.

8. Request/response DTOs remain public and shared, but only in `BlazorAutoApp.Core.Features.*.UseCases.*`.

9. EF entity classes live in Core `Domain` namespaces. EF configuration classes live in server feature `Persistence` namespaces.

10. Historical migrations should be left alone unless the build requires otherwise. The active `AppDbContextModelSnapshot` must reflect new entity namespaces after moving domain types.

## Architecture Test Changes

### Replace Movie-Anchored Assembly Discovery

Current architecture tests use `IMoviesApi`, `MoviesServerService`, and `MoviesClientService` as assembly anchors. Keep those types available during the transition, but change tests to discover assemblies from stable project markers or existing project-root types:

- Core assembly: any public Core API interface, or add a simple `CoreAssemblyMarker`.
- Server assembly: `Program`.
- Client assembly: `_Imports`.
- Test assembly: `WebAppFactory`.

This prevents Movies from being a special architectural dependency.

### Add Core Feature Layout Tests

Create tests that inspect source files under `BlazorAutoApp.Core/Features` and enforce:

- No `.cs` files directly in a feature root when the feature has `Domain`, `Contracts`, or `UseCases`.
- Public API interfaces ending in `Api` live under a `.Contracts` namespace and folder.
- Public request/response DTOs live under `.UseCases.{UseCase}` namespaces and folders.
- Domain entities/enums live under `.Domain`.
- Allowed Core feature folders are `Domain`, `Contracts`, and `UseCases`.

The test should support nested feature paths such as `Inspections/HullImages`.

### Update DTO Tests

Keep the existing server/client rule:

- Server assembly defines no public `*Request` or `*Response` DTOs.
- Client assembly defines no public `*Request` or `*Response` DTOs.

Add a Core rule:

- Core public `*Request` and `*Response` types must live in `.UseCases.` namespaces.

### Update API Implementation Parity Tests

For each Core `I*Api` interface:

- Exactly one server implementation exists.
- Exactly one client implementation exists.
- Server implementation namespace starts with the matching server feature namespace.
- Client implementation namespace starts with the matching client feature namespace.

Example mapping:

```text
BlazorAutoApp.Core.Features.Inspections.HullImages.Contracts.IHullImagesApi
  -> BlazorAutoApp.Features.Inspections.HullImages.*
  -> BlazorAutoApp.Client.Features.Inspections.HullImages.*
```

The mapping should ignore the trailing `.Contracts` segment.

### Update EF Architecture Tests

Add or update tests to enforce:

- `DbSet<>` entity types in `AppDbContext` live under Core `.Domain` namespaces.
- `IEntityTypeConfiguration<>` classes live under server `Features.*.Persistence` namespaces.
- Each configured entity type belongs to a Core `.Domain` namespace.

### Update Feature Test Coverage Convention

The existing `EachCoreRequest_HasMatchingFeatureTestClass` test should detect the full leaf feature path instead of only the first namespace segment after `Features`.

Example:

```text
BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.CreateHullImage.CreateHullImageRequest
  -> tests under BlazorAutoApp.Test.Features.Inspections.HullImages
```

### Endpoint Surface Tests

Keep route-specific checks, but expand them beyond Movies or group them by feature:

- Movies: `/api/movies`
- HullImages: `/api/hull-images`
- InspectionFlow: `/api/inspection-flow`
- VesselPartDetails: `/api/vessel-part-details`
- IdentityShowcase: `/api/identity-showcase`

These tests should remain behavioral guardrails, not folder-structure tests.

## Target Feature Layouts

### Movies

```text
BlazorAutoApp.Core/Features/Movies/
  Domain/
    Movie.cs
  Contracts/
    IMoviesApi.cs
  UseCases/
    GetMovies/
      GetMoviesRequest.cs
      GetMoviesResponse.cs
    GetMovie/
      GetMovieRequest.cs
      GetMovieResponse.cs
    CreateMovie/
      CreateMovieRequest.cs
      CreateMovieResponse.cs
    UpdateMovie/
      UpdateMovieRequest.cs
      UpdateMovieResponse.cs
    DeleteMovie/
      DeleteMovieRequest.cs
      DeleteMovieResponse.cs

BlazorAutoApp/Features/Movies/
  Composition.cs
  Endpoints/MoviesEndpoints.cs
  Services/MoviesServerService.cs
  Persistence/MovieEntityTypeConfiguration.cs
  Caching/MoviesCacheOptions.cs
  Validation/DataAnnotationsValidateFilter.cs

BlazorAutoApp.Client/Features/Movies/
  MoviesClientService.cs
  Pages/
```

Notes:

- Replace `MoviesValidateFilter<T>` with a reusable server-side validation filter, because `VesselPartDetails` already depends on the Movies-specific filter.
- `GetMoviesResponse` currently exposes `List<Movie>`. Keep that for the first pass to reduce behavioral risk, then consider adding a `MovieDto` later if the UI should not consume entities.

### HullImages

```text
BlazorAutoApp.Core/Features/Inspections/HullImages/
  Domain/
    HullImage.cs
  Contracts/
    IHullImagesApi.cs
  UseCases/
    GetHullImages/
    GetHullImage/
    GetHullImageByCorrelationId/
    CreateHullImage/
    UploadTus/
    DeleteHullImage/
    PruneMissingHullImages/

BlazorAutoApp/Features/Inspections/HullImages/
  Composition.cs
  Endpoints/HullImagesEndpoints.cs
  Services/HullImagesServerService.cs
  Persistence/HullImageEntityTypeConfiguration.cs
  Storage/LocalHullImageStore.cs
  Storage/HullImagesStorageOptions.cs
  Storage/ImageSignatureValidator.cs
  Storage/ThumbnailService.cs
  Tus/TusResultRegistry.cs
  Tus/TusResultRegistry.Redis.cs

BlazorAutoApp.Client/Features/Inspections/HullImages/
  HullImagesClientService.cs
  Http/ProgressStreamContent.cs
  Pages/
```

Notes:

- Decide whether `UploadTusAsync`, `DeleteAsync`, and `PruneMissingAsync` should get request/response DTOs. The architecture test should not force this immediately unless the refactor also changes those method signatures.
- Keep TUS/storage concerns server-side only.

### Inspection

```text
BlazorAutoApp.Core/Features/Inspections/Inspection/
  Domain/
    Inspection.cs

BlazorAutoApp/Features/Inspections/Inspection/
  Persistence/InspectionEntityTypeConfiguration.cs
```

Notes:

- This is a domain-only feature today. Architecture tests must allow features without contracts or use cases.

### InspectionFlow

```text
BlazorAutoApp.Core/Features/Inspections/InspectionFlow/
  Domain/
    InspectionFlow.cs
    InspectionType.cs
    InspectionVesselPart.cs
  Contracts/
    IInspectionFlowApi.cs
    InspectionVesselPartDto.cs
  UseCases/
    GetInspectionFlow/
      GetInspectionFlowResponse.cs
    UpsertInspectionFlow/
      UpsertInspectionFlowRequest.cs
      UpsertInspectionFlowResponse.cs

BlazorAutoApp/Features/Inspections/InspectionFlow/
  Composition.cs
  Endpoints/InspectionFlowEndpoints.cs
  Services/InspectionFlowServerService.cs
  Persistence/InspectionFlowEntityTypeConfiguration.cs
  Persistence/InspectionVesselPartEntityTypeConfiguration.cs

BlazorAutoApp.Client/Features/Inspections/InspectionFlow/
  InspectionFlowClientService.cs
  Pages/
  Components/
```

Notes:

- `InspectionVesselPart` depends on `HullImage`; update using statements after `HullImage` moves to `HullImages.Domain`.
- Current client pages use fully qualified Core namespaces. Replace those with imports after the Core namespaces settle.

### VesselPartDetails

```text
BlazorAutoApp.Core/Features/Inspections/VesselPartDetails/
  Domain/
    VesselPartDetails.cs
    FoulingObservation.cs
    CoatingCondition.cs
    HullCondition.cs
    HullRating.cs
    FoulingType.cs
    HullRatingValue.cs
  Contracts/
    IVesselPartDetailsApi.cs
    FoulingObservationDto.cs
    CoatingConditionDto.cs
    HullConditionDto.cs
    HullRatingDto.cs
  UseCases/
    GetVesselPartDetails/
      GetVesselPartDetailsResponse.cs
    UpsertVesselPartDetails/
      UpsertVesselPartDetailsRequest.cs
      UpsertVesselPartDetailsResponse.cs

BlazorAutoApp/Features/Inspections/VesselPartDetails/
  Composition.cs
  Endpoints/VesselPartDetailsEndpoints.cs
  Services/VesselPartDetailsServerService.cs
  Persistence/VesselPartDetailsEntityTypeConfiguration.cs
  Persistence/FoulingObservationEntityTypeConfiguration.cs
  Persistence/CoatingConditionEntityTypeConfiguration.cs
  Persistence/HullConditionEntityTypeConfiguration.cs
  Persistence/HullRatingEntityTypeConfiguration.cs

BlazorAutoApp.Client/Features/Inspections/VesselPartDetails/
  VesselPartDetailsClientService.cs
```

Notes:

- The current `VesselPartDetails.Contracts.cs` mixes DTOs, validation, response models, and API interface. Split it carefully because many client components use these types.

### IdentityShowcase

```text
BlazorAutoApp.Core/Features/IdentityShowcase/
  Contracts/
    IIdentityShowcaseApi.cs
  UseCases/
    GetPublicIdentityShowcase/
      IdentityShowcasePublicInfo.cs
    GetSecureIdentityShowcase/
      IdentityShowcaseSecureInfo.cs
    GetIdentityShowcaseAdminProbe/
      IdentityShowcaseAdminProbeResponse.cs

BlazorAutoApp/Features/IdentityShowcase/
  Composition.cs
  Endpoints/IdentityShowcaseEndpoints.cs
  Services/IdentityShowcaseServerService.cs

BlazorAutoApp.Client/Features/IdentityShowcase/
  IdentityShowcaseClientService.cs
```

Notes:

- This feature has no domain model today. That is fine; do not create empty `Domain` folders just to satisfy symmetry.

## Execution Plan

### Phase 1: Prepare Architecture Tests

- Replace hard-coded Movies assembly anchors with project-level assembly discovery.
- Add Core folder/namespace convention tests.
- Strengthen DTO placement tests.
- Update API implementation parity tests to understand `.Contracts`.
- Add EF entity/configuration placement tests.
- Update feature test coverage convention to use full nested feature paths.
- Expand endpoint surface tests to include all current API route groups.

Expected result: tests describe the target architecture and will fail until the refactor is complete.

### Phase 2: Refactor Movies First

- Move Core Movies files into `Domain`, `Contracts`, and `UseCases`.
- Update namespaces and using statements in server, client, tests, and `AppDbContext`.
- Move server Movies files into `Endpoints`, `Services`, `Persistence`, `Caching`, and `Validation`.
- Replace `MoviesValidateFilter<T>` usage with a feature-neutral validation filter.
- Update `AppDbContextModelSnapshot` for the new `Movie` entity namespace.
- Run Movies feature tests and architecture tests.

Reason: Movies is small and already has good endpoint/test coverage, so it is the safest pilot slice.

### Phase 3: Refactor HullImages

- Move `HullImage` into Core `Domain`.
- Move `IHullImagesApi` into `Contracts`.
- Move request/response DTOs into use case folders.
- Move server persistence/storage/TUS files into explicit subfolders.
- Update client imports and pages.
- Update EF snapshot for `HullImage`.
- Run HullImages tests and architecture tests.

### Phase 4: Refactor InspectionFlow and Inspection

- Move Inspection domain entity into `Inspection/Domain`.
- Move InspectionFlow entities/enums into `InspectionFlow/Domain`.
- Split `InspectionFlow.Contracts.cs` into `Contracts` and `UseCases`.
- Move server endpoint/service/persistence files into target folders.
- Update all aliases for `InspectionFlowEntity`, `InspectionVesselPartEntity`, and `InspectionEntity`.
- Update EF snapshot.
- Run InspectionFlow tests and architecture tests.

### Phase 5: Refactor VesselPartDetails

- Split domain entities/enums from `VesselPartDetails.Entities.cs`.
- Split DTOs/API/use cases from `VesselPartDetails.Contracts.cs`.
- Move server endpoint/service/persistence files into target folders.
- Update client components and pages that use the DTOs.
- Update EF snapshot.
- Run VesselPartDetails tests and architecture tests.

### Phase 6: Refactor IdentityShowcase

- Split `IdentityShowcase.Contracts.cs` into `Contracts` and use case response files.
- Move server endpoint/service files into target folders.
- Update client service and DI imports.
- Run IdentityShowcase-related architecture and endpoint tests.

### Phase 7: Clean Up Cross-Cutting Imports

- Update `BlazorAutoApp/Usings.cs`.
- Update `BlazorAutoApp.Client/_Imports.razor`.
- Remove stale using statements and fully qualified names.
- Confirm no feature code imports old Core feature root namespaces.
- Confirm no public DTOs remain outside Core use case folders.

### Phase 8: Verification

Run:

```powershell
dotnet test
```

If the full suite is slow or blocked by external services, run targeted suites first:

```powershell
dotnet test --filter FullyQualifiedName~Architecture
dotnet test --filter FullyQualifiedName~Features.Movies
dotnet test --filter FullyQualifiedName~Features.Inspections.HullImages
dotnet test --filter FullyQualifiedName~Features.Inspections.InspectionFlow
dotnet test --filter FullyQualifiedName~Features.Inspections.VesselPartDetails
```

Final acceptance:

- Architecture tests pass.
- Feature tests pass.
- The solution builds without stale namespace imports.
- EF model snapshot matches the moved domain entity namespaces.
- No unrelated migrations are generated by namespace-only moves.

## Risks And Decisions

- Moving entity namespaces can make EF think entities changed identity. Mitigation: update the active model snapshot and check for accidental drop/create migrations.
- Splitting large contract files can create noisy namespace churn. Mitigation: refactor one feature at a time and run targeted tests after each feature.
- Some current API methods use primitives instead of request/response DTOs. Decision: do not force every method into DTOs in the first pass unless it reduces complexity.
- `GetMoviesResponse` and `GetHullImagesResponse` currently expose domain entities. Decision: keep behavior during the structural refactor; consider DTO projection in a later behavior-focused change.
- Historical migration designer files contain old entity namespace strings. Decision: leave them alone unless build or EF tooling proves they must change.

## Suggested Commit Slices

1. Architecture tests for target slicing.
2. Movies refactor.
3. HullImages refactor.
4. Inspection and InspectionFlow refactor.
5. VesselPartDetails refactor.
6. IdentityShowcase refactor.
7. Import cleanup, EF snapshot cleanup, and final verification.
