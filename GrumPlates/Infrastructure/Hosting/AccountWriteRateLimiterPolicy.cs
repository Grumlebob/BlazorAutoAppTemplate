using System.Collections.Concurrent;
using System.Threading.RateLimiting;
using GrumPlates.Features.Login.Accounts;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Extensions.Options;

namespace GrumPlates.Infrastructure.Hosting;

internal readonly record struct AccountWriteLimiterPartition(string ClientIp, string? ApiPartitionKey);

/// <summary>
/// Limits enabled account writes by resolved client IP. The /api/auth family also
/// retains the normal API window, partitioned by authenticated user or client IP.
/// </summary>
internal sealed class AccountWriteRateLimiterPolicy : IRateLimiterPolicy<AccountWriteLimiterPartition>, IDisposable
{
    private readonly AccountWriteLimitOptions _writeLimit;
    private readonly RateLimitRuleOptions _apiLimit;
    private readonly ConcurrentDictionary<string, Lazy<FixedWindowRateLimiter>> _writeLimiters = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, Lazy<SlidingWindowRateLimiter>> _apiLimiters = new(StringComparer.Ordinal);

    public AccountWriteRateLimiterPolicy(AccountOptions accounts, IOptions<AppRateLimitingOptions> rateLimiting)
    {
        _writeLimit = accounts.WriteLimit;
        _apiLimit = rateLimiting.Value.Api;
    }

    public Func<OnRejectedContext, CancellationToken, ValueTask>? OnRejected => null;

    public RateLimitPartition<AccountWriteLimiterPartition> GetPartition(HttpContext httpContext)
    {
        var request = httpContext.Request;
        if (HttpMethods.IsGet(request.Method) || HttpMethods.IsHead(request.Method))
        {
            return RateLimitPartition.GetNoLimiter(new AccountWriteLimiterPartition("read", null));
        }

        var isApiAccountRequest = request.Path.StartsWithSegments("/api/auth", StringComparison.OrdinalIgnoreCase);
        var isBlazorAccountRequest = request.Path.StartsWithSegments("/Account", StringComparison.OrdinalIgnoreCase);
        if (!isApiAccountRequest && !isBlazorAccountRequest)
        {
            return RateLimitPartition.GetNoLimiter(new AccountWriteLimiterPartition("unscoped", null));
        }

        var clientIp = httpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";
        var apiPartitionKey = isApiAccountRequest
            ? AppRateLimiting.GetPartitionKey(httpContext, AppRateLimiting.ApiPolicyName)
            : null;
        var partition = new AccountWriteLimiterPartition(clientIp, apiPartitionKey);
        return RateLimitPartition.Get(partition, CreateLimiter);
    }

    public void Dispose()
    {
        foreach (var limiter in _writeLimiters.Values)
        {
            if (limiter.IsValueCreated) limiter.Value.Dispose();
        }
        foreach (var limiter in _apiLimiters.Values)
        {
            if (limiter.IsValueCreated) limiter.Value.Dispose();
        }
    }

    private RateLimiter CreateLimiter(AccountWriteLimiterPartition partition)
    {
        var writeLimiter = _writeLimiters.GetOrAdd(partition.ClientIp, _ => new Lazy<FixedWindowRateLimiter>(CreateWriteLimiter)).Value;
        if (partition.ApiPartitionKey is null)
        {
            return RateLimiter.CreateChained(writeLimiter);
        }

        var apiLimiter = _apiLimiters.GetOrAdd(partition.ApiPartitionKey, _ => new Lazy<SlidingWindowRateLimiter>(CreateApiLimiter)).Value;
        // Check the account-specific quota first so rejected writes do not burn API permits.
        return RateLimiter.CreateChained(writeLimiter, apiLimiter);
    }

    private FixedWindowRateLimiter CreateWriteLimiter() => new(new FixedWindowRateLimiterOptions
    {
        AutoReplenishment = true,
        PermitLimit = _writeLimit.PermitLimit,
        QueueLimit = 0,
        QueueProcessingOrder = QueueProcessingOrder.OldestFirst,
        Window = TimeSpan.FromSeconds(_writeLimit.WindowSeconds)
    });

    private SlidingWindowRateLimiter CreateApiLimiter() => new(new SlidingWindowRateLimiterOptions
    {
        AutoReplenishment = true,
        PermitLimit = _apiLimit.PermitLimit,
        QueueLimit = _apiLimit.QueueLimit,
        QueueProcessingOrder = QueueProcessingOrder.OldestFirst,
        SegmentsPerWindow = Math.Max(1, Math.Min(6, _apiLimit.WindowSeconds)),
        Window = TimeSpan.FromSeconds(_apiLimit.WindowSeconds)
    });
}
