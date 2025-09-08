using Microsoft.Extensions.Caching.Distributed;

namespace BlazorAutoApp.Features.HullImages;

public class TusResultRegistryRedis : ITusResultRegistry
{
    private readonly IDistributedCache _cache;
    private static readonly TimeSpan DefaultTtl = TimeSpan.FromHours(1);

    public TusResultRegistryRedis(IDistributedCache cache)
    {
        _cache = cache;
    }

    private static string Key(Guid id) => $"tus:result:{id}";

    public void Set(Guid correlationId, int imageId)
    {
        var bytes = BitConverter.GetBytes(imageId);
        var options = new DistributedCacheEntryOptions
        {
            AbsoluteExpirationRelativeToNow = DefaultTtl
        };
        _cache.Set(Key(correlationId), bytes, options);
    }

    public bool TryGet(Guid correlationId, out int imageId)
    {
        var data = _cache.Get(Key(correlationId));
        if (data is { Length: 4 })
        {
            imageId = BitConverter.ToInt32(data, 0);
            return true;
        }
        imageId = 0;
        return false;
    }
}

