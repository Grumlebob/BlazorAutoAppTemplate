using System.Buffers;
using System.Globalization;
using BlazorAutoApp.Core.Features.HullImages;

namespace BlazorAutoApp.Features.HullImages;

public static class HullImageEndpoints
{
    private const long MaxUploadBytes = 1_073_741_824; // 1 GB

    private record InitiateUploadResponse(Guid UploadSessionId, int ChunkSizeBytes);

    // Simple in-memory upload sessions for chunked API (local only)
    private class UploadSession
    {
        public required string OriginalFileName { get; init; }
        public string? ContentType { get; init; }
        public string TempPath { get; init; } = default!;
        public int ChunkSizeBytes { get; init; } = 4 * 1024 * 1024;
        public long TotalWritten { get; set; }
    }

    private static readonly ConcurrentDictionary<Guid, UploadSession> _sessions = new();

    public static IEndpointRouteBuilder MapHullImageEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/hull-images");

        group.MapGet("/", async ([AsParameters] GetHullImagesRequest req, IHullImagesApi api) =>
        {
            var res = await api.GetAsync(req);
            return Results.Ok(res);
        });

        group.MapGet("/{id:int}", async (int id, IHullImagesApi api) =>
        {
            var res = await api.GetByIdAsync(new GetHullImageRequest { Id = id });
            return res is null ? Results.NotFound() : Results.Ok(res);
        });

        // Single-shot streaming upload; body is raw bytes
        group.MapPost("/", async (HttpRequest request, IHullImageStore store, IHullImagesApi api, ILogger<Program> log, CancellationToken ct) =>
        {
            var originalName = request.Headers["X-File-Name"].ToString();
            if (string.IsNullOrWhiteSpace(originalName)) originalName = "upload.bin";
            var contentType = request.ContentType;

            if (request.ContentLength is > MaxUploadBytes)
                return Results.BadRequest($"File exceeds {MaxUploadBytes} bytes limit");

            var stored = await store.SaveAsync(request.Body, originalName, contentType, ct);
            await using (var verify = await store.OpenReadAsync(stored.StorageKey, ct))
            {
                if (!ImageSignatureValidator.IsSupportedImage(verify))
                {
                    await store.DeleteAsync(stored.StorageKey, ct);
                    return Results.BadRequest("Only image files are allowed (jpeg, png, webp, gif, bmp)");
                }
            }
            // Probe dimensions
            int? width = null, height = null;
            await using (var dim = await store.OpenReadAsync(stored.StorageKey, ct))
            {
                try
                {
                    var info = SixLabors.ImageSharp.Image.Identify(dim);
                    if (info is not null) { width = info.Width; height = info.Height; }
                }
                catch { /* ignore identify errors */ }
            }

            var created = await api.CreateAsync(new CreateHullImageRequest
            {
                OriginalFileName = originalName,
                ContentType = contentType,
                ByteSize = stored.ByteSize,
                StorageKey = stored.StorageKey,
                Sha256 = stored.Sha256,
                Width = width,
                Height = height
            });

            return Results.Created($"/api/hull-images/{created.Id}", created);
        }).DisableAntiforgery().WithMetadata(new RequestSizeLimitAttribute(MaxUploadBytes));

        // Download original with basic streaming
        group.MapGet("/{id:int}/original", async (int id, AppDbContext db, IHullImageStore store, CancellationToken ct) =>
        {
            var item = await db.Set<HullImage>().AsNoTracking().FirstOrDefaultAsync(i => i.Id == id, ct);
            if (item is null) return Results.NotFound();
            var stream = await store.OpenReadAsync(item.StorageKey, ct);
            return Results.Stream(stream, item.ContentType ?? "application/octet-stream", enableRangeProcessing: true, fileDownloadName: item.OriginalFileName);
        });

        // Thumbnail on-demand: generates and caches JPEG thumbnail
        group.MapGet("/{id:int}/thumbnail/{size:int}", async (int id, int size, AppDbContext db, IHullImageStore store, IThumbnailService thumbs, CancellationToken ct) =>
        {
            if (size <= 0) size = 256;
            var item = await db.Set<HullImage>().AsNoTracking().FirstOrDefaultAsync(i => i.Id == id, ct);
            if (item is null) return Results.NotFound();
            var rel = await thumbs.GetOrCreateThumbnailAsync(item.StorageKey, size, ct);
            var stream = await store.OpenReadAsync(rel, ct);
            return Results.Stream(stream, "image/jpeg", enableRangeProcessing: false, fileDownloadName: Path.GetFileName(rel));
        });

        // Create metadata record (used by client service; assumes file already stored)
        group.MapPost("/metadata", async (CreateHullImageRequest dto, IHullImagesApi api) =>
        {
            var created = await api.CreateAsync(dto);
            return Results.Created($"/api/hull-images/{created.Id}", created);
        });

        group.MapDelete("/{id:int}", async (int id, IHullImagesApi api, ILogger<Program> log, CancellationToken ct) =>
        {
            var ok = await api.DeleteAsync(id, ct);
            if (!ok) return Results.NotFound();
            log.LogInformation("Deleted HullImage {Id}", id);
            return Results.NoContent();
        });

        // Chunked API - initiate
        group.MapPost("/uploads", async (HttpRequest request, IWebHostEnvironment env) =>
        {
            var originalName = request.Headers["X-File-Name"].ToString();
            if (string.IsNullOrWhiteSpace(originalName)) originalName = "upload.bin";
            var contentType = request.Headers["X-Content-Type"].ToString();
            var id = Guid.NewGuid();
            var tempRoot = Path.Combine(env.ContentRootPath, "Storage", "TempUploads");
            Directory.CreateDirectory(tempRoot);
            var tempFile = Path.Combine(tempRoot, id.ToString("N"));
            var session = new UploadSession { OriginalFileName = originalName, ContentType = contentType, TempPath = tempFile };
            _sessions[id] = session;
            return Results.Ok(new InitiateUploadResponse(id, session.ChunkSizeBytes));
        }).DisableAntiforgery();

        // Prune missing files (cleanup DB entries whose files were deleted manually)
        group.MapPost("/prune-missing", async (IHullImagesApi api, ILogger<Program> log, CancellationToken ct) =>
        {
            var count = await api.PruneMissingAsync(ct);
            log.LogInformation("Pruned {Count} missing hull images", count);
            return Results.Ok(new { removed = count });
        });

        // Upload chunk (append-only simple protocol)
        group.MapPut("/uploads/{id:guid}/chunks/{index:int}", async (Guid id, int index, HttpRequest request, ILogger<Program> log, CancellationToken ct) =>
        {
            if (!_sessions.TryGetValue(id, out var session)) return Results.NotFound();
            await using var fs = new FileStream(session.TempPath, FileMode.Append, FileAccess.Write, FileShare.None);
            var buffer = ArrayPool<byte>.Shared.Rent(1024 * 1024);
            try
            {
                int read;
                long total = 0;
                while ((read = await request.Body.ReadAsync(buffer.AsMemory(0, buffer.Length), ct)) > 0)
                {
                    await fs.WriteAsync(buffer.AsMemory(0, read), ct);
                    total += read;
                }
                session.TotalWritten += total;
                log.LogDebug("Chunk {Index} for {Id} wrote {Bytes} bytes (total {Total})", index, id, total, session.TotalWritten);
            }
            finally
            {
                ArrayPool<byte>.Shared.Return(buffer);
            }
            return Results.Accepted();
        }).DisableAntiforgery().WithMetadata(new RequestSizeLimitAttribute(MaxUploadBytes));

        // Complete upload (move to store)
        group.MapPost("/uploads/{id:guid}/complete", async (Guid id, IHullImageStore store, IHullImagesApi api, ILogger<Program> log, CancellationToken ct) =>
        {
            if (!_sessions.TryRemove(id, out var session)) return Results.NotFound();
            await using var src = File.OpenRead(session.TempPath);
            var stored = await store.SaveAsync(src, session.OriginalFileName, session.ContentType, ct);
            await src.DisposeAsync();
            await using (var verify = await store.OpenReadAsync(stored.StorageKey, ct))
            {
                if (!ImageSignatureValidator.IsSupportedImage(verify))
                {
                    await store.DeleteAsync(stored.StorageKey, ct);
                    File.Delete(session.TempPath);
                    return Results.BadRequest("Only image files are allowed (jpeg, png, webp, gif, bmp)");
                }
            }
            int? width = null, height = null;
            await using (var dim = await store.OpenReadAsync(stored.StorageKey, ct))
            {
                try
                {
                    var info = SixLabors.ImageSharp.Image.Identify(dim);
                    if (info is not null) { width = info.Width; height = info.Height; }
                }
                catch { }
            }
            File.Delete(session.TempPath);
            var created = await api.CreateAsync(new CreateHullImageRequest
            {
                OriginalFileName = session.OriginalFileName,
                ContentType = session.ContentType,
                ByteSize = stored.ByteSize,
                StorageKey = stored.StorageKey,
                Sha256 = stored.Sha256,
                Width = width,
                Height = height
            });
            log.LogInformation("Completed chunked upload {Id} -> HullImage {ImageId}", id, created.Id);
            return Results.Ok(created);
        }).DisableAntiforgery();

        return routes;
    }
}
