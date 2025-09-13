using BlazorAutoApp.Core.Features.HullImages;

namespace BlazorAutoApp.Features.Inspections.HullImages;

public class HullImagesServerService(IDbContextFactory<AppDbContext> dbFactory, IHullImageStore store, ILogger<HullImagesServerService> log, ITusResultRegistry tusRegistry, IWebHostEnvironment env)
    : IHullImagesApi
{
    public async Task<GetHullImagesResponse> GetAsync(GetHullImagesRequest req)
    {
        await using var db = await dbFactory.CreateDbContextAsync();
        var query = db.Set<HullImage>().AsNoTracking().AsQueryable();
        if (req.VesselPartId is int vpId)
        {
            query = query.Where(x => x.InspectionVesselPartId == vpId);
        }
        var items = await query.OrderByDescending(x => x.Id).ToListAsync();
        return new GetHullImagesResponse { Items = items };
    }

    public async Task<GetHullImageResponse?> GetByIdAsync(GetHullImageRequest req)
    {
        await using var db = await dbFactory.CreateDbContextAsync();
        var item = await db.Set<HullImage>().AsNoTracking().FirstOrDefaultAsync(x => x.Id == req.Id);
        if (item is null) return null;
        return new GetHullImageResponse
        {
            Id = item.Id,
            OriginalFileName = item.OriginalFileName,
            ContentType = item.ContentType,
            ByteSize = item.ByteSize,
            Sha256 = item.Sha256,
            Width = item.Width,
            Height = item.Height,
            CreatedAtUtc = item.CreatedAtUtc,
            AiHullScore = item.AiHullScore,
            VesselName = item.VesselName,
            InspectionVesselPartId = item.InspectionVesselPartId
        };
    }

    public async Task<GetHullImageResponse?> GetByCorrelationIdAsync(Guid correlationId, CancellationToken ct = default)
    {
        // Resolve via registry and then load by id
        if (tusRegistry.TryGet(correlationId, out var imageId))
        {
            return await GetByIdAsync(new GetHullImageRequest { Id = imageId });
        }
        return null;
    }

    public async Task<CreateHullImageResponse> CreateAsync(CreateHullImageRequest req)
    {
        await using var db = await dbFactory.CreateDbContextAsync();
        var entity = new HullImage
        {
            OriginalFileName = req.OriginalFileName,
            ContentType = req.ContentType,
            ByteSize = req.ByteSize,
            Sha256 = req.Sha256,
            StorageKey = req.StorageKey,
            Width = req.Width,
            Height = req.Height,
            VesselName = string.IsNullOrWhiteSpace(req.VesselName) ? "BoatyBoat" : req.VesselName!,
            Status = "Ready",
            InspectionVesselPartId = req.InspectionVesselPartId
        };
        db.Add(entity);
        await db.SaveChangesAsync();
        log.LogInformation("Stored HullImage {Id} {Name} {Size}B", entity.Id, entity.OriginalFileName, entity.ByteSize);
        return new CreateHullImageResponse
        {
            Id = entity.Id,
            OriginalFileName = entity.OriginalFileName,
            ContentType = entity.ContentType,
            ByteSize = entity.ByteSize,
            Sha256 = entity.Sha256,
            VesselName = entity.VesselName,
            InspectionVesselPartId = entity.InspectionVesselPartId
        };
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken ct = default)
    {
        await using var db = await dbFactory.CreateDbContextAsync();
        var entity = await db.Set<HullImage>().FirstOrDefaultAsync(i => i.Id == id, ct);
        if (entity is null) return false;
        db.Remove(entity);
        await db.SaveChangesAsync(ct);
        _ = await store.DeleteAsync(entity.StorageKey, ct);
        return true;
    }

    public async Task<int> PruneMissingAsync(CancellationToken ct = default)
    {
        await using var db = await dbFactory.CreateDbContextAsync();
        var set = db.Set<HullImage>();
        var items = await set.AsNoTracking().ToListAsync(ct);
        var removed = 0;
        foreach (var item in items)
        {
            try
            {
                await using var s = await store.OpenReadAsync(item.StorageKey, ct);
            }
            catch
            {
                var tracked = await set.FirstOrDefaultAsync(x => x.Id == item.Id, ct);
                if (tracked is not null)
                {
                    db.Remove(tracked);
                    removed++;
                }
            }
        }
        if (removed > 0) await db.SaveChangesAsync(ct);
        return removed;
    }

    /// <summary>
    /// TUS uploads are handled by middleware and endpoints, not via this method.
    /// Server-side flow (exact files and key lines):
    /// - Program.cs
    ///   - Line 130: app.UseTus(...) registers tusdotnet middleware.
    ///   - Line 139: UrlPath = "/api/hull-images/tus" (TUS endpoint root).
    ///   - Line 140: Store = new TusDiskStore(tusRoot) (on-disk TUS parts).
    ///   - Line 156: Events.OnFileCompleteAsync – runs after the TUS upload finishes.
    ///       - Line 173: IHullImageStore.SaveAsync(...) persists the completed stream to final storage.
    ///       - Line 178: IHullImageStore.OpenReadAsync(...) +
    ///         Line 179: ImageSharp Image.Identify(...) validate/inspect the image.
    ///       - Line 191: IHullImagesApi.CreateAsync(new CreateHullImageRequest { ... }) creates the DB record.
    ///       - Line 211: ITusResultRegistry.Set(correlationId, imageId) maps correlationId -> created image.
    /// - Features/HullImages/Endpoints.cs
    ///   - Line 91: MapGet("/tus/result", ...) returns the created image by correlationId.
    ///   - Line 16: MapGroup("/api/hull-images") (group root); Line 33 original download; Line 42 thumbnail.
    ///
    /// Client-side (for reference):
    /// - BlazorAutoApp.Client/wwwroot/js/tusUpload.js drives TUS (POST create + PATCH data), and the page
    ///   BlazorAutoApp.Client/Pages/HullImages/Index.razor wires the JS interop and progress.
    /// </summary>
    public async Task UploadTusAsync(string fileName, string? contentType, Stream content, long size, IProgress<long>? progress = null, Guid? correlationId = null, CancellationToken ct = default)
    {
        // Server-side IHullImagesApi is not responsible for driving TUS protocol.
        // This method is not expected to be invoked on the server service directly.
        throw new NotSupportedException("TUS upload is handled by tusdotnet middleware and endpoints, not via IHullImagesApi.UploadTusAsync on server.");
    }

    public Task<IReadOnlyList<string>> ListTestAssetsAsync(CancellationToken ct = default)
    {
        var root = env.WebRootPath ?? string.Empty;
        var dir = Path.Combine(root, "test-assets");
        if (!Directory.Exists(dir))
            return Task.FromResult((IReadOnlyList<string>)Array.Empty<string>());
        var items = Directory.EnumerateFiles(dir)
            .Select(Path.GetFileName)
            .Where(n => !string.IsNullOrWhiteSpace(n))
            .Select(n => n!)
            .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
            .ToArray();
        return Task.FromResult((IReadOnlyList<string>)items);
    }
}
