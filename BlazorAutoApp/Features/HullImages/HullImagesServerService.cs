using BlazorAutoApp.Core.Features.HullImages;

namespace BlazorAutoApp.Features.HullImages;

public class HullImagesServerService(AppDbContext db, IHullImageStore store, ILogger<HullImagesServerService> log)
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
            CreatedAtUtc = item.CreatedAtUtc
        };
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
            Sha256 = entity.Sha256
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
        await using (var verify = await store.OpenReadAsync(stored.StorageKey, ct))
        {
            if (!ImageSignatureValidator.IsSupportedImage(verify))
            {
                await store.DeleteAsync(stored.StorageKey, ct);
                throw new InvalidOperationException("Only image files are allowed (jpeg, png, webp, gif, bmp)");
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

    private class UploadSession
    {
        public required string OriginalFileName { get; init; }
        public string? ContentType { get; init; }
        public required string TempPath { get; init; }
        public int ChunkSizeBytes { get; init; } = 4 * 1024 * 1024;
    }

    private static readonly ConcurrentDictionary<Guid, UploadSession> _sessions = new();

    public Task<InitiateHullImageUploadResponse> InitiateUploadAsync(string fileName, string? contentType, CancellationToken ct = default)
    {
        var id = Guid.NewGuid();
        var tempRoot = Path.Combine(AppContext.BaseDirectory, "Storage", "TempUploads");
        Directory.CreateDirectory(tempRoot);
        var tempFile = Path.Combine(tempRoot, id.ToString("N"));
        _sessions[id] = new UploadSession { OriginalFileName = fileName, ContentType = contentType, TempPath = tempFile };
        return Task.FromResult(new InitiateHullImageUploadResponse(id, 4 * 1024 * 1024));
    }

    public async Task UploadChunkAsync(Guid sessionId, int index, Stream chunk, CancellationToken ct = default)
    {
        if (!_sessions.TryGetValue(sessionId, out var session)) throw new KeyNotFoundException("Session not found");
        await using var fs = new FileStream(session.TempPath, FileMode.Append, FileAccess.Write, FileShare.None);
        await chunk.CopyToAsync(fs, ct);
    }

    public async Task<CreateHullImageResponse> CompleteUploadAsync(Guid sessionId, CancellationToken ct = default)
    {
        if (!_sessions.TryRemove(sessionId, out var session)) throw new KeyNotFoundException("Session not found");
        await using var src = File.OpenRead(session.TempPath);
        var stored = await store.SaveAsync(src, session.OriginalFileName, session.ContentType, ct);
        await src.DisposeAsync();
        await using (var verify = await store.OpenReadAsync(stored.StorageKey, ct))
        {
            if (!ImageSignatureValidator.IsSupportedImage(verify))
            {
                await store.DeleteAsync(stored.StorageKey, ct);
                File.Delete(session.TempPath);
                throw new InvalidOperationException("Only image files are allowed (jpeg, png, webp, gif, bmp)");
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
        var created = await CreateAsync(new CreateHullImageRequest
        {
            OriginalFileName = session.OriginalFileName,
            ContentType = session.ContentType,
            ByteSize = stored.ByteSize,
            StorageKey = stored.StorageKey,
            Sha256 = stored.Sha256,
            Width = width,
            Height = height
        });
        return created;
    }
}
