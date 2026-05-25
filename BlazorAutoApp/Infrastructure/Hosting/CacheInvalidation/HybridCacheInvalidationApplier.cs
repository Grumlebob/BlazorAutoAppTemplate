using Microsoft.Extensions.Caching.Hybrid;

namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed class HybridCacheInvalidationApplier(HybridCache cache) : ICacheInvalidationApplier
{
    private readonly HybridCache _cache = cache;

    public async Task ApplyAsync(CacheInvalidationRequest request, CancellationToken cancellationToken = default)
    {
        var keys = request.Keys
            .Where(key => !string.IsNullOrWhiteSpace(key))
            .Distinct(StringComparer.Ordinal)
            .ToArray();

        if (keys.Length > 0)
        {
            await _cache.RemoveAsync(keys, cancellationToken);
        }

        var tags = request.Tags
            .Where(tag => !string.IsNullOrWhiteSpace(tag))
            .Distinct(StringComparer.Ordinal)
            .ToArray();

        if (tags.Length > 0)
        {
            await _cache.RemoveByTagAsync(tags, cancellationToken);
        }
    }
}
