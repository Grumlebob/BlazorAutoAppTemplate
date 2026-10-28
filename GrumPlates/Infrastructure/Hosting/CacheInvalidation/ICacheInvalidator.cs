namespace GrumPlates.Infrastructure.Hosting.CacheInvalidation;

internal interface ICacheInvalidator
{
    Task<CacheInvalidationResult> InvalidateAsync(CacheInvalidationRequest request, CancellationToken cancellationToken = default);
}
