HullImages Feature

Overview
- Purpose: High-throughput local image uploads for future AI processing.
- Modes: Single-shot streaming (default) and simple chunked uploads (optional).
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
- Chunked (simple):
  - `POST /api/hull-images/uploads`: Initiate. Headers: `X-File-Name`, `X-Content-Type`; returns `{ uploadSessionId, chunkSizeBytes }`.
  - `PUT /api/hull-images/uploads/{id}/chunks/{index}`: Append raw chunk bytes (append-only protocol).
  - `POST /api/hull-images/uploads/{id}/complete`: Finalize and persist metadata.

Validation
- Server-side: Validates magic numbers for allowed types (jpeg, png, webp, gif, bmp). Non-images are rejected with `400`.
- Client-side: Filters by extension before upload (.jpg, .jpeg, .png, .webp, .gif, .bmp). Max 1 GB enforced by input stream limit.

Post-Processing
- Dimension probing: After saving an image, the server probes Width/Height and stores them in metadata to display on the Details page.

Blazor UI
- Route: `/hull-images`.
- Upload toggle: "NOT CHUNKED" or "CHUNKED" modes via switch.
- Progress bar: Shows bytes and percentage in both modes.
- Chunked controls: Pause/Resume UI (Resume requires reselecting the same file; session id is stored in `sessionStorage`).
- Thumbnails: You can link to `/api/hull-images/{id}/thumbnail/256` or `/thumbnail/512` for previews.
- Gallery: Toggle between Gallery and Table view. Gallery has a thumbnail size selector (128/256/512).
- Prune Missing: Button to remove DB entries for missing files, then refresh the list.

Core Interface (vertical slice)
- `IHullImagesApi` (Core) is used by components.
- Server: `HullImagesServerService` streams directly to disk and DB (no HttpClient).
- Client: `HullImagesClientService` uses `HttpClient` to call endpoints.

Testing
- Integration tests cover single-shot upload, listing, range download, delete, and chunked end-to-end.
- Tests generate minimal JPEG-like data (magic number + padding).

Configuration
- Limits and storage paths are local; storage directories are created on demand.
 - Configure base storage path via `Storage:HullImages:RootPath` in `appsettings.json`. Relative paths are resolved against server content root.
 - If you manually delete files from disk, run the `Prune Missing` action in the UI (or call the prune API) to clean up DB records.

Future Work
- Add resumable chunked uploads across page reloads with a status endpoint and real byte-position queries.
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
