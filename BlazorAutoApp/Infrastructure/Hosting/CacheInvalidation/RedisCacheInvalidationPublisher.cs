using System.Text.Json;
using Microsoft.Extensions.Options;
using StackExchange.Redis;

namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed class RedisCacheInvalidationPublisher(
    IConnectionMultiplexer redis,
    IOptions<CacheInvalidationOptions> options,
    ILogger<RedisCacheInvalidationPublisher> logger) : ICacheInvalidationPublisher
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);

    private readonly IConnectionMultiplexer _redis = redis;
    private readonly CacheInvalidationOptions _options = options.Value;
    private readonly ILogger<RedisCacheInvalidationPublisher> _logger = logger;

    public async Task PublishAsync(CacheInvalidationMessage message, CancellationToken cancellationToken = default)
    {
        var payload = JsonSerializer.Serialize(message, SerializerOptions);
        var subscriber = _redis.GetSubscriber();
        var recipients = await subscriber
            .PublishAsync(RedisChannel.Literal(_options.EffectiveChannelName), payload)
            .WaitAsync(cancellationToken);

        if (recipients == 0)
        {
            _logger.LogInformation(
                "Published cache invalidation for {CacheInvalidationScope} with no active Redis subscriber acknowledgements",
                message.Scope);
            return;
        }

        _logger.LogDebug(
            "Published cache invalidation for {CacheInvalidationScope} to {SubscriberCount} subscriber(s)",
            message.Scope,
            recipients);
    }
}
