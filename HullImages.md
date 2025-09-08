HullImages Feature

Overview
- Purpose: High-throughput local image uploads for future AI processing.
- Modes: Single-shot streaming ("SIMPLE ONE SHOT") and TUS resumable uploads (default for large files).
- Limits: 1 GB per file.
- Storage: Local disk under `Storage/HullImages/yyyyMMdd/{guid}{ext}`.
  - On Windows local dev (running the server from this repo), files are created under:
    `BlazorAutoApp/Storage/HullImages/{yyyyMMdd}/{guid}{ext}`
    For example:
    `C:\Users\<you>\Documents\Programming\Csharp\BlazorAutoApp\BlazorAutoApp\Storage\HullImages\20250906\a1b2c3d4e5f6.jpg`
  - Thumbnails are cached under `Storage/HullImages/thumbs/{size}/{yyyyMMdd}/{filename}.jpg`.
  - Note: The storage root is defined by `LocalHullImageStore` using the server `ContentRootPath`. In Docker, this is inside the container unless you bind-mount a host folder.

Endpoints
- `GET /api/hull-images`: List images (metadata only).
- `GET /api/hull-images/{id}`: Get a single image’s metadata (used by the Details page).
- `POST /api/hull-images`: Single-shot streaming upload; body is raw bytes.
  - Headers: `X-File-Name: <original file name>`
  - Returns: `CreateHullImageResponse`.
- `GET /api/hull-images/{id}/original`: Download original, with range support.
- `GET /api/hull-images/{id}/thumbnail/{size}`: On-demand JPEG thumbnail generation and cached delivery. `size` is the max width/height.
- `DELETE /api/hull-images/{id}`: Delete image (DB + file).
- `POST /api/hull-images/prune-missing`: Remove DB entries whose files were deleted manually from disk.
- TUS (resumable):
  - `POST /api/hull-images/tus` with `Tus-Resumable: 1.0.0`, `Upload-Length: <bytes>`, `Upload-Metadata: filename <b64>,contentType <b64>`
- `PATCH {location}` with `Tus-Resumable`, `Upload-Offset`, and `Content-Type: application/offset+octet-stream` to send data.
  - On completion, the server streams into the configured `IHullImageStore`, validates, probes dimensions, and creates the DB record.
  - Optional metadata: `correlationId <b64-guid>` enables a server-side mapping so the client can look up the created image ID after completion.
  - `GET /api/hull-images/tus/result?correlationId=<guid>`: Lookup the created image by correlation ID.

TUS: Implementation Details (How It Works)
- Middleware: Powered by `tusdotnet` (2.10.x). Configured in `Program.cs` at path `/api/hull-images/tus`.
- Temp store: In-progress files are written to `Storage/Tus` (`TusDiskStore`).
- Metadata required: `filename` (b64); optional: `contentType` (b64), `correlationId` (b64 GUID from client).
- Completion flow:
  - Event `OnFileCompleteAsync` fires.
  - Server opens the completed TUS file stream and calls `IHullImageStore.SaveAsync` (currently `LocalHullImageStore`) to move data into the final `Storage/HullImages/yyyyMMdd/{guid}{ext}` location.
  - Validates magic numbers (JPEG/PNG/WebP/GIF/BMP) and probes image dimensions.
  - Creates a DB record via `IHullImagesApi.CreateAsync` and logs the new `Id`.
  - Deletes the temporary TUS file (via `ITusTerminationStore`).
  - If `correlationId` was provided, maps `correlationId -> imageId` in `ITusResultRegistry` so the client can query `/tus/result` to retrieve the `Id`.

Blazor UI (Server and WASM)
- Toggle: "SIMPLE ONE SHOT" or "TUS". One-shot is kept for small uploads and tooling; TUS is the default for large uploads.
- TUS client: Implemented in `/wwwroot/js/tusUpload.js` and invoked via JS interop from the Hull Images page.
- The JS module performs `POST` (create) and `PATCH` (data segments), and reports progress back to the component via `[JSInvokable]` method `ReportTusProgress`.
  - A new `correlationId` (GUID) is generated per upload and sent in TUS metadata. After completion, the component calls `GET /api/hull-images/tus/result?correlationId=...` to obtain the created image’s `Id`.
- Auto mode (prerender + interactive): Upload controls render during prerender but only become active once interactive. TUS still runs entirely in the browser after interactivity is established (works identically for Blazor Server and WASM).

Client/Server Separation
- Components do not inject `HttpClient` directly (enforced by tests). The component calls JS to run the TUS protocol in the browser.
- Business logic (validation, thumbnails, persistence) stays in the server via `IHullImagesApi` and `IHullImageStore`.

Validation
- Server-side: Validates magic numbers for allowed types (jpeg, png, webp, gif, bmp, tiff) and then fully decodes via ImageSharp to confirm. Non-images are rejected with `400`.
- Client-side: Filters by extension before upload (.jpg, .jpeg, .png, .webp, .gif, .bmp, .tif, .tiff). Max 1 GB enforced by input stream limit.

Post-Processing
- Dimension probing: After saving an image, the server probes Width/Height and stores them in metadata to display on the Details page.

Blazor UI
- Route: `/hull-images`.
- Upload toggle: "SIMPLE ONE SHOT" or "TUS" via switch.
- Progress bar: Shows bytes and percentage in both modes.
- TUS controls: Pause/Resume UI.
- Thumbnails: You can link to `/api/hull-images/{id}/thumbnail/256` or `/thumbnail/512` for previews.
- Gallery: Toggle between Gallery and Table view. Gallery has a thumbnail size selector (128/256/512).
- Prune Missing: Button to remove DB entries for missing files, then refresh the list.

Core Interface (vertical slice)
- `IHullImagesApi` (Core) is used by components.
- Server: `HullImagesServerService` streams directly to disk and DB (no HttpClient).
- Client: `HullImagesClientService` uses `HttpClient` to call endpoints.

Testing
- Integration tests cover single-shot upload, listing, range download, delete, and TUS end-to-end.
- Tests generate minimal JPEG-like data (magic number + padding).

Configuration
- Limits and storage paths are local; storage directories are created on demand.
 - Configure base storage path via `Storage:HullImages:RootPath` in `appsettings.json`. Relative paths are resolved against server content root.
 - If you manually delete files from disk, run the `Prune Missing` action in the UI (or call the prune API) to clean up DB records.

S3/Azure Readiness
- Swap `IHullImageStore` to a cloud-backed implementation (e.g., S3 multipart). TUS flow and UI remain unchanged.
- Optional advanced path: replace `TusDiskStore` with an S3-backed `ITusStore` to store in-progress parts in S3; the completion callback still creates the DB record via `IHullImagesApi`.

Troubleshooting
- Ensure `tusdotnet` package restores (nuget.org source available).
- If uploads complete but the UI can’t find the new ID, verify the client is sending a valid `correlationId` and that `/api/hull-images/tus/result` is reachable.
- For large files, verify server write permissions under `Storage/Tus` and `Storage/HullImages`.

Future Work
- Add resumable TUS uploads across page reloads with a status endpoint and real byte-position queries.
- Add thumbnail generation and dimension probing, plus EXIF handling.
- Optional S3/Azure backends with multipart uploads.
  
Thumbnails: Implementation Notes
- Library: SixLabors.ImageSharp (cross-platform) to resize and encode JPEG at quality 80.
- Storage: Cached under `Storage/HullImages/thumbs/{size}/{yyyyMMdd}/{filename}.jpg`.
- Behavior: No upscaling; preserves aspect ratio based on `max(size)` of width/height.

UI: Details Page
- Route: `/hull-images/{id}` shows a 512px thumbnail preview and metadata.
- Actions: "Download Original" (saves file) and "Open Original" (opens in a new tab).
 - Shows Dimensions (Width x Height) when available.

For manual testing of large images:
https://svs.gsfc.nasa.gov/12144/
