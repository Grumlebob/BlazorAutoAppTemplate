namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal interface ICacheInvalidationPublisher
{
    Task PublishAsync(CacheInvalidationMessage message, CancellationToken cancellationToken = default);
}
