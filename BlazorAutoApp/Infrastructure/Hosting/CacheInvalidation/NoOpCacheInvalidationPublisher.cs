namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed class NoOpCacheInvalidationPublisher : ICacheInvalidationPublisher
{
    public Task PublishAsync(CacheInvalidationMessage message, CancellationToken cancellationToken = default) =>
        Task.CompletedTask;
}
