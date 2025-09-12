Refactor: Inspections/HullImages Subslice and Per‑Part Uploads

Scope
- Move existing HullImages server logic under a new subslice at `Features/Inspections/HullImages`, reusing all existing models, storage, TUS, and thumbnailing.
- Implement per‑part hull image uploads in the Inspection Flow UI, showing thumbnails + filenames and linking to details.
- Link `InspectionVesselPart` to `HullImage` with a proper FK, `ON DELETE SET NULL`.
- Remove the dev HullImages index page and nav links; keep details page and API endpoints unchanged.

Server Changes
- Move files to `BlazorAutoApp/Features/Inspections/HullImages` and update namespaces accordingly:
  - `Endpoints.cs`
  - `HullImagesServerService.cs`
  - `HullImageEntityTypeConfiguration.cs`
  - `LocalHullImageStore.cs`
  - `ThumbnailService.cs`
  - `ImageSignatureValidator.cs`
  - `TusResultRegistry.cs`
  - `TusResultRegistry.Redis.cs`
- Keep API routes the same (`/api/hull-images`, `/api/hull-images/tus`) for compatibility and tests.
- Update DI registrations and `MapHullImageEndpoints()` imports in `Program.cs` to the new namespace.
- Update `AppDbContext.OnModelCreating` to apply the moved entity configuration.
- Add FK from `InspectionVesselParts.HullImageId` to `HullImages.Id` with `ON DELETE SET NULL` via EF config and a migration.

Data Model
- `InspectionVesselPart`: add navigation `HullImage? HullImage`.
- EF config for `InspectionVesselPart`:
  - Existing: FK to `InspectionFlow` (cascade delete).
  - New: `HasOne<HullImage>().WithMany().HasForeignKey(x => x.HullImageId).OnDelete(DeleteBehavior.SetNull)`.

Client/UI Changes
- In `Pages/Inspection/Flow.razor`:
  - Inject `IHullImagesApi` and `IJSRuntime`.
  - Replace simple `HullImageId` numeric input with a table of selected parts:
    - Columns: Part, Upload (button), Image (thumbnail + filename).
    - Clicking Upload opens file dialog and starts TUS for that row, using `/wwwroot/js/tusUpload.js`.
    - On completion, resolve created image by correlationId via `IHullImagesApi.GetByCorrelationIdAsync` and set `_hullImageByPart[code]`.
    - Show thumbnail via `/api/hull-images/{id}/thumbnail/64` and filename (fetched once via `GetByIdAsync` and cached per id).
    - Thumbnail links to details `/hull-images/{id}`.
  - Persisting: existing Save continues to send `HullImageId` per part.

-The page currently doesn't compile. FIX THIS.

Cleanup
- Remove `BlazorAutoApp.Client/Pages/HullImages/Index.razor` and `.css` (dev page).
- Remove `/hull-images` link from `Client/Layout/NavMenu.razor`.
- Keep details page `/hull-images/{id}` for deep linking.

Verification
- TUS upload flow unchanged; middleware at `/api/hull-images/tus` continues to store files and create metadata.
- Thumbnails served via `/api/hull-images/{id}/thumbnail/{size}`.
- Tests that exercise the API paths continue to pass (unchanged routes and behavior).
- New migration applies an FK only; no table renames.

