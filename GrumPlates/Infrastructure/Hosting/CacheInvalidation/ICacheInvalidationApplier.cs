namespace GrumPlates.Infrastructure.Hosting.CacheInvalidation;

internal interface ICacheInvalidationApplier
{
    Task ApplyAsync(CacheInvalidationRequest request, CancellationToken cancellationToken = default);
}
