namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal interface ICacheInvalidator
{
    Task InvalidateAsync(CacheInvalidationRequest request, CancellationToken cancellationToken = default);
}
