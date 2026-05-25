using System.Text.Json;
using Microsoft.Extensions.Options;
using StackExchange.Redis;

namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed class RedisCacheInvalidationSubscriber(
    IConnectionMultiplexer redis,
    ICacheInvalidationApplier applier,
    IOptions<CacheInvalidationOptions> options,
    ILogger<RedisCacheInvalidationSubscriber> logger) : BackgroundService
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);
    private static readonly TimeSpan SubscribeRetryDelay = TimeSpan.FromSeconds(5);

    private readonly IConnectionMultiplexer _redis = redis;
    private readonly ICacheInvalidationApplier _applier = applier;
    private readonly CacheInvalidationOptions _options = options.Value;
    private readonly ILogger<RedisCacheInvalidationSubscriber> _logger = logger;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (!_options.Enabled)
        {
            return;
        }

        var channel = RedisChannel.Literal(_options.EffectiveChannelName);

        while (!stoppingToken.IsCancellationRequested)
        {
            ChannelMessageQueue? queue = null;

            try
            {
                queue = await _redis.GetSubscriber().SubscribeAsync(channel);
                _logger.LogInformation("Subscribed to cache invalidation channel {CacheInvalidationChannel}", channel);

                while (!stoppingToken.IsCancellationRequested)
                {
                    var channelMessage = await queue.ReadAsync(stoppingToken);
                    await HandleMessageAsync(channelMessage.Message, stoppingToken);
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Cache invalidation subscriber failed; retrying subscription");
                try
                {
                    await Task.Delay(SubscribeRetryDelay, stoppingToken);
                }
                catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
                {
                    break;
                }
            }
            finally
            {
                if (queue is not null)
                {
                    try
                    {
                        await queue.UnsubscribeAsync();
                    }
                    catch (Exception ex)
                    {
                        _logger.LogDebug(ex, "Failed to unsubscribe from cache invalidation channel");
                    }
                }
            }
        }
    }

    private async Task HandleMessageAsync(RedisValue payload, CancellationToken stoppingToken)
    {
        CacheInvalidationMessage? message;

        try
        {
            message = JsonSerializer.Deserialize<CacheInvalidationMessage>(payload.ToString(), SerializerOptions);
        }
        catch (JsonException ex)
        {
            _logger.LogWarning(ex, "Ignored malformed cache invalidation message");
            return;
        }

        if (message is null || message.Version != CacheInvalidationOptions.MessageVersion)
        {
            _logger.LogDebug("Ignored unsupported cache invalidation message");
            return;
        }

        if (!string.Equals(message.AppName, _options.AppName, StringComparison.Ordinal)
            || !string.Equals(message.EnvironmentName, _options.EnvironmentName, StringComparison.Ordinal))
        {
            _logger.LogDebug(
                "Ignored cache invalidation message for {AppName}/{EnvironmentName}",
                message.AppName,
                message.EnvironmentName);
            return;
        }

        if (string.Equals(message.SourceNodeId, _options.EffectiveNodeId, StringComparison.Ordinal))
        {
            _logger.LogDebug("Ignored same-node cache invalidation for {CacheInvalidationScope}", message.Scope);
            return;
        }

        try
        {
            using var applyTimeout = CancellationTokenSource.CreateLinkedTokenSource(stoppingToken);
            applyTimeout.CancelAfter(_options.ApplyTimeout);
            await _applier.ApplyAsync(
                new CacheInvalidationRequest(message.Scope, message.Keys, message.Tags),
                applyTimeout.Token);

            _logger.LogDebug(
                "Applied cache invalidation for {CacheInvalidationScope} from {SourceNodeId}",
                message.Scope,
                message.SourceNodeId);
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(
                ex,
                "Failed to apply cache invalidation for {CacheInvalidationScope} from {SourceNodeId}",
                message.Scope,
                message.SourceNodeId);
        }
    }
}
