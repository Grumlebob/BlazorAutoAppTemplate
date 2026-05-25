using System.Globalization;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Net.Http.Headers;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class AppRateLimiting
{
    public const string ApiPolicyName = "api";
    public const string AuthenticationPolicyName = "authentication";

    public static IServiceCollection AddAppRateLimiting(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        var configuredOptions = new AppRateLimitingOptions();
        configuration.GetSection(AppRateLimitingOptions.SectionName).Bind(configuredOptions);

        services.AddOptions<AppRateLimitingOptions>()
            .Bind(configuration.GetSection(AppRateLimitingOptions.SectionName))
            .ValidateDataAnnotations()
            .Validate(options => options.AllRulesAreValid(), "Rate limiting windows and permit limits must be greater than zero.")
            .ValidateOnStart();

        services.AddRateLimiter(options =>
        {
            options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
            options.OnRejected = WriteTooManyRequestsResponseAsync;

            options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(context =>
            {
                var isAccountWrite = IsAccountWriteRequest(context);
                var policy = isAccountWrite ? AuthenticationPolicyName : "global";
                var rule = isAccountWrite ? configuredOptions.Authentication : configuredOptions.Global;

                return RateLimitPartition.GetFixedWindowLimiter(
                    GetPartitionKey(context, policy),
                    _ => ToFixedWindow(rule));
            });

            options.AddPolicy(ApiPolicyName, context =>
                RateLimitPartition.GetSlidingWindowLimiter(
                    GetPartitionKey(context, ApiPolicyName),
                    _ => ToSlidingWindow(configuredOptions.Api)));

        });

        return services;
    }

    public static IApplicationBuilder UseAppRateLimiting(this IApplicationBuilder app)
    {
        return app.UseRateLimiter();
    }

    private static ValueTask WriteTooManyRequestsResponseAsync(
        OnRejectedContext context,
        CancellationToken cancellationToken)
    {
        var response = context.HttpContext.Response;
        var retryAfterSeconds = context.Lease.TryGetMetadata(MetadataName.RetryAfter, out var retryAfter)
            ? Math.Max(1, (int)Math.Ceiling(retryAfter.TotalSeconds))
            : 1;

        response.Headers[HeaderNames.RetryAfter] = retryAfterSeconds.ToString(CultureInfo.InvariantCulture);

        response.ContentType = "application/problem+json";
        return new ValueTask(Results.Problem(
            statusCode: StatusCodes.Status429TooManyRequests,
            title: "Too many requests",
            detail: "The request rate limit was exceeded. Try again later.")
            .ExecuteAsync(context.HttpContext));
    }

    private static string GetPartitionKey(HttpContext context, string policy)
    {
        var userId = context.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (!string.IsNullOrWhiteSpace(userId))
        {
            return $"{policy}:user:{userId}";
        }

        return $"{policy}:ip:{context.Connection.RemoteIpAddress?.ToString() ?? "unknown"}";
    }

    private static bool IsAccountWriteRequest(HttpContext context)
    {
        return context.Request.Path.StartsWithSegments("/Account")
            && !HttpMethods.IsGet(context.Request.Method)
            && !HttpMethods.IsHead(context.Request.Method);
    }

    private static FixedWindowRateLimiterOptions ToFixedWindow(RateLimitRuleOptions rule)
    {
        return new FixedWindowRateLimiterOptions
        {
            AutoReplenishment = true,
            PermitLimit = rule.PermitLimit,
            QueueLimit = rule.QueueLimit,
            QueueProcessingOrder = QueueProcessingOrder.OldestFirst,
            Window = TimeSpan.FromSeconds(rule.WindowSeconds)
        };
    }

    private static SlidingWindowRateLimiterOptions ToSlidingWindow(RateLimitRuleOptions rule)
    {
        return new SlidingWindowRateLimiterOptions
        {
            AutoReplenishment = true,
            PermitLimit = rule.PermitLimit,
            QueueLimit = rule.QueueLimit,
            QueueProcessingOrder = QueueProcessingOrder.OldestFirst,
            SegmentsPerWindow = Math.Max(1, Math.Min(6, rule.WindowSeconds)),
            Window = TimeSpan.FromSeconds(rule.WindowSeconds)
        };
    }
}
