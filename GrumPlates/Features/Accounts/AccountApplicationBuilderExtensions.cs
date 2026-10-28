using GrumPlates.Features.Accounts.Security;
using Microsoft.AspNetCore.Http.Features;

namespace GrumPlates.Features.Accounts;

internal static class AccountApplicationBuilderExtensions
{
    private const int MaximumJsonRequestBytes = 16 * 1024;
    private static readonly HashSet<string> AccountJsonMutationPaths = new(StringComparer.OrdinalIgnoreCase)
    {
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/logout-all",
        "/api/auth/register",
        "/api/auth/resend-confirmation",
        "/api/auth/confirm-email",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/change-password",
        "/api/auth/change-email",
        "/api/auth/confirm-email-change",
        "/api/auth/export",
        "/api/auth/delete"
    };

    public static void UseAccountRequestPolicies(this WebApplication app)
    {
        if (!app.Services.GetRequiredService<AccountOptions>().Enabled)
        {
            return;
        }

        app.Use(async (context, next) =>
        {
            var accountRequest = context.Request.Path.StartsWithSegments("/api/auth", StringComparison.OrdinalIgnoreCase)
                || context.Request.Path.StartsWithSegments("/api/books", StringComparison.OrdinalIgnoreCase)
                || context.Request.Path.StartsWithSegments("/Account", StringComparison.OrdinalIgnoreCase);
            if (accountRequest)
            {
                context.Response.Headers.CacheControl = "private, no-store";
                context.Response.Headers.Pragma = "no-cache";
                context.Response.OnStarting(static state =>
                {
                    var response = (HttpResponse)state;
                    response.Headers.CacheControl = "private, no-store";
                    response.Headers.Pragma = "no-cache";
                    return Task.CompletedTask;
                }, context.Response);
            }

            if (IsAccountJsonMutation(context))
            {
                var sizeFeature = context.Features.Get<IHttpMaxRequestBodySizeFeature>();
                if (sizeFeature is { IsReadOnly: false })
                {
                    sizeFeature.MaxRequestBodySize = MaximumJsonRequestBytes + 1;
                }
            }

            try
            {
                await next();
            }
            catch (Exception exception) when (accountRequest && !context.Response.HasStarted
                && AccountResults.IsPersistenceFailure(exception))
            {
                context.Response.Clear();
                await AccountResults.DeliveryUnavailable().ExecuteAsync(context);
            }
        });
    }

    public static void UseAccountJsonBodyLimits(this WebApplication app)
    {
        if (!app.Services.GetRequiredService<AccountOptions>().Enabled)
        {
            return;
        }

        app.Use(async (context, next) =>
        {
            if (!IsAccountJsonMutation(context))
            {
                await next();
                return;
            }

            if (!context.Request.HasJsonContentType())
            {
                await AccountProblem.Create(StatusCodes.Status415UnsupportedMediaType, "UnsupportedMediaType",
                    "JSON required", "Send this request as application/json.")
                    .ExecuteAsync(context);
                return;
            }

            if (context.Request.ContentLength > MaximumJsonRequestBytes)
            {
                await WriteRequestTooLargeAsync(context);
                return;
            }

            var originalBody = context.Request.Body;
            var boundedBody = await BufferAtMostAsync(originalBody, MaximumJsonRequestBytes, context.RequestAborted);
            if (boundedBody is null)
            {
                await WriteRequestTooLargeAsync(context);
                return;
            }

            context.Request.Body = boundedBody;
            try
            {
                await next();
            }
            finally
            {
                context.Request.Body = originalBody;
                await boundedBody.DisposeAsync();
            }
        });
    }

    private static bool IsAccountJsonMutation(HttpContext context) =>
        AccountJsonMutationPaths.Contains(context.Request.Path.Value?.TrimEnd('/') ?? "")
        && !HttpMethods.IsGet(context.Request.Method)
        && !HttpMethods.IsHead(context.Request.Method);

    private static async Task<MemoryStream?> BufferAtMostAsync(Stream source, int limit, CancellationToken cancellationToken)
    {
        var bytes = GC.AllocateUninitializedArray<byte>(limit + 1);
        var total = 0;
        while (total < bytes.Length)
        {
            var read = await source.ReadAsync(bytes.AsMemory(total), cancellationToken);
            if (read == 0)
            {
                break;
            }
            total += read;
        }

        return total > limit ? null : new MemoryStream(bytes, 0, total, writable: false, publiclyVisible: true);
    }

    private static Task WriteRequestTooLargeAsync(HttpContext context) =>
        AccountProblem.Create(StatusCodes.Status413PayloadTooLarge, "RequestTooLarge",
            "Request too large", "The request body exceeds the 16 KiB limit.")
            .ExecuteAsync(context);
}
