using Microsoft.Extensions.Options;

namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed class HybridCacheInvalidator(
    ICacheInvalidationApplier applier,
    ICacheInvalidationPublisher publisher,
    IOptions<CacheInvalidationOptions> options,
    ILogger<HybridCacheInvalidator> logger) : ICacheInvalidator
{
    private readonly ICacheInvalidationApplier _applier = applier;
    private readonly ICacheInvalidationPublisher _publisher = publisher;
    private readonly CacheInvalidationOptions _options = options.Value;
    private readonly ILogger<HybridCacheInvalidator> _logger = logger;

    public async Task InvalidateAsync(CacheInvalidationRequest request, CancellationToken cancellationToken = default)
    {
        try
        {
            using var applyTimeout = new CancellationTokenSource(_options.ApplyTimeout);
            await _applier.ApplyAsync(request, applyTimeout.Token);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Local cache invalidation failed for {CacheInvalidationScope}", request.Scope);
        }

        if (!_options.Enabled)
        {
            return;
        }

        var message = new CacheInvalidationMessage(
            CacheInvalidationOptions.MessageVersion,
            _options.AppName,
            _options.EnvironmentName,
            _options.EffectiveNodeId,
            request.Scope,
            request.Keys.ToArray(),
            request.Tags.ToArray(),
            DateTimeOffset.UtcNow);

        try
        {
            using var publishTimeout = new CancellationTokenSource(_options.PublishTimeout);
            await _publisher.PublishAsync(message, publishTimeout.Token);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to publish cache invalidation for {CacheInvalidationScope}", request.Scope);
        }
    }
}
