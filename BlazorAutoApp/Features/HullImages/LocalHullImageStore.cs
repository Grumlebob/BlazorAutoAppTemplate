using System.Buffers;
using System.Security.Cryptography;

namespace BlazorAutoApp.Features.HullImages;

public record StoredHullImage(string StorageKey, long ByteSize, string Sha256);

public interface IHullImageStore
{
    Task<StoredHullImage> SaveAsync(Stream source, string originalFileName, string? contentType, CancellationToken ct = default);
    Task<Stream> OpenReadAsync(string storageKey, CancellationToken ct = default);
    Task<bool> DeleteAsync(string storageKey, CancellationToken ct = default);
}

public class LocalHullImageStore(IWebHostEnvironment env, IOptions<HullImagesStorageOptions> opts, ILogger<LocalHullImageStore> log) : IHullImageStore
{
    private readonly string _root = BuildRoot(env, opts?.Value?.RootPath);

    private static string BuildRoot(IWebHostEnvironment env, string? configured)
    {
        var rootPath = string.IsNullOrWhiteSpace(configured) ? "Storage/HullImages" : configured!;
        return Path.IsPathRooted(rootPath) ? rootPath : Path.Combine(env.ContentRootPath, rootPath);
    }

    public async Task<StoredHullImage> SaveAsync(Stream source, string originalFileName, string? contentType, CancellationToken ct = default)
    {
        Directory.CreateDirectory(_root);

        // Use a random file name; sharded by date to avoid hot directories
        var day = DateTime.UtcNow.ToString("yyyyMMdd");
        var folder = Path.Combine(_root, day);
        Directory.CreateDirectory(folder);

        var fileId = Guid.NewGuid().ToString("N");
        var ext = Path.GetExtension(originalFileName);
        var fileName = fileId + ext;
        var path = Path.Combine(folder, fileName);

        long total = 0;
        var sha = SHA256.Create();
        var rented = ArrayPool<byte>.Shared.Rent(1024 * 1024);
        try
        {
            await using var fs = File.Create(path);
            int read;
            while ((read = await source.ReadAsync(rented.AsMemory(0, rented.Length), ct)) > 0)
            {
                await fs.WriteAsync(rented.AsMemory(0, read), ct);
                sha.TransformBlock(rented, 0, read, null, 0);
                total += read;
            }
            sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
        }
        finally
        {
            ArrayPool<byte>.Shared.Return(rented);
        }

        var hash = Convert.ToHexString(sha.Hash!);
        var key = Path.GetRelativePath(_root, path).Replace('\\', '/');
        return new StoredHullImage(key, total, hash);
    }

    public Task<Stream> OpenReadAsync(string storageKey, CancellationToken ct = default)
    {
        var path = Path.Combine(_root, storageKey.Replace('/', Path.DirectorySeparatorChar));
        Stream s = File.OpenRead(path);
        return Task.FromResult(s);
    }

    public Task<bool> DeleteAsync(string storageKey, CancellationToken ct = default)
    {
        var path = Path.Combine(_root, storageKey.Replace('/', Path.DirectorySeparatorChar));
        if (File.Exists(path))
        {
            File.Delete(path);
            return Task.FromResult(true);
        }
        return Task.FromResult(false);
    }
}
