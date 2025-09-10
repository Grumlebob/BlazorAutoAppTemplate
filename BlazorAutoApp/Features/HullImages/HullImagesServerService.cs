using BlazorAutoApp.Core.Features.HullImages;

namespace BlazorAutoApp.Features.HullImages;

public class HullImagesServerService(AppDbContext db, IHullImageStore store, ILogger<HullImagesServerService> log, ITusResultRegistry tusRegistry, IWebHostEnvironment env)
    : IHullImagesApi
{
    public async Task<GetHullImagesResponse> GetAsync(GetHullImagesRequest req)
    {
        var items = await db.Set<HullImage>().AsNoTracking().OrderByDescending(x => x.Id).ToListAsync();
        return new GetHullImagesResponse { Items = items };
    }

    public async Task<GetHullImageResponse?> GetByIdAsync(GetHullImageRequest req)
    {
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
            VesselName = item.VesselName
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
            Status = "Ready"
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
            VesselName = entity.VesselName
        };
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken ct = default)
    {
        var entity = await db.Set<HullImage>().FirstOrDefaultAsync(i => i.Id == id, ct);
        if (entity is null) return false;
        db.Remove(entity);
        await db.SaveChangesAsync(ct);
        _ = await store.DeleteAsync(entity.StorageKey, ct);
        return true;
    }

    public async Task<int> PruneMissingAsync(CancellationToken ct = default)
    {
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

    public async Task<CreateHullImageResponse> UploadAsync(string fileName, string? contentType, Stream content, long? size, IProgress<long>? progress, CancellationToken ct = default)
    {
        var stored = await store.SaveAsync(content, fileName, contentType, ct);
        int? width = null, height = null;
        await using (var verify = await store.OpenReadAsync(stored.StorageKey, ct))
        {
            var info = SixLabors.ImageSharp.Image.Identify(verify);
            if (info is null)
            {
                await store.DeleteAsync(stored.StorageKey, ct);
                throw new InvalidOperationException("Only decodable image files are allowed (jpeg, png, webp, gif, bmp, tiff)");
            }
            width = info.Width; height = info.Height;
        }
        var created = await CreateAsync(new CreateHullImageRequest
        {
            OriginalFileName = fileName,
            ContentType = contentType,
            ByteSize = stored.ByteSize,
            StorageKey = stored.StorageKey,
            Sha256 = stored.Sha256,
            Width = width,
            Height = height
        });
        return created;
    }

    public async Task UploadTusAsync(string fileName, string? contentType, Stream content, long size, IProgress<long>? progress = null, Guid? correlationId = null, CancellationToken ct = default)
    {
        // Server-side IHullImagesApi is not responsible for driving TUS protocol.
        // Fallback to single-shot storage if invoked directly.
        _ = await UploadAsync(fileName, contentType, content, size, progress, ct);
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
