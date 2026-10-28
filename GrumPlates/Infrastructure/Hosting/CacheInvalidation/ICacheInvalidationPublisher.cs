namespace GrumPlates.Infrastructure.Hosting.CacheInvalidation;

internal interface ICacheInvalidationPublisher
{
    Task PublishAsync(CacheInvalidationMessage message, CancellationToken cancellationToken = default);
}
