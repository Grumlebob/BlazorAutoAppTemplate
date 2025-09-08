using System.Buffers;
using System.Globalization;
using BlazorAutoApp.Core.Features.HullImages;

namespace BlazorAutoApp.Features.HullImages;

public static class HullImageEndpoints
{
    private const long MaxUploadBytes = 1_073_741_824; // 1 GB

    // TUS is the canonical chunked protocol now. The previous custom chunk
    // implementation has been removed in favor of a spec-compliant approach.

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
            // Validate by fully decoding the image and capture dimensions
            int? width = null, height = null;
            try
            {
                await using var verify = await store.OpenReadAsync(stored.StorageKey, ct);
                using var img = SixLabors.ImageSharp.Image.Load(verify);
                width = img.Width; height = img.Height;
            }
            catch
            {
                await store.DeleteAsync(stored.StorageKey, ct);
                return Results.BadRequest("Only decodable image files are allowed (jpeg, png, webp, gif, bmp)");
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

        // Prune missing files (cleanup DB entries whose files were deleted manually)
        group.MapPost("/prune-missing", async (IHullImagesApi api, ILogger<Program> log, CancellationToken ct) =>
        {
            var count = await api.PruneMissingAsync(ct);
            log.LogInformation("Pruned {Count} missing hull images", count);
            return Results.Ok(new { removed = count });
        });

        // TUS result lookup by correlationId
        group.MapGet("/tus/result", async (string correlationId, IHullImagesApi api, CancellationToken ct) =>
        {
            if (!Guid.TryParse(correlationId, out var id)) return Results.BadRequest("Invalid correlationId");
            var res = await api.GetByCorrelationIdAsync(id, ct);
            return res is null ? Results.NotFound() : Results.Ok(res);
        });

        return routes;
    }
}
