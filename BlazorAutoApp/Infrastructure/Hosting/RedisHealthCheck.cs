using Microsoft.Extensions.Diagnostics.HealthChecks;
using StackExchange.Redis;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal sealed class RedisHealthCheck(IConnectionMultiplexer redis) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await redis.GetDatabase().PingAsync();
            return redis.IsConnected
                ? HealthCheckResult.Healthy()
                : HealthCheckResult.Unhealthy("Redis is disconnected.");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("Redis health check failed.", ex);
        }
    }
}
