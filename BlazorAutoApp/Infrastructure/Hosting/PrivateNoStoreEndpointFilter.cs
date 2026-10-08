using Microsoft.Net.Http.Headers;

namespace BlazorAutoApp.Infrastructure.Hosting;

/// <summary>
/// Marks responses that contain data for the current user as non-cacheable, so
/// proxies and the browser cache never store or replay them for someone else.
/// </summary>
internal sealed class PrivateNoStoreEndpointFilter : IEndpointFilter
{
    public ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var headers = context.HttpContext.Response.Headers;
        headers[HeaderNames.CacheControl] = "private, no-store";
        headers[HeaderNames.Pragma] = "no-cache";
        return next(context);
    }
}

internal static class PrivateNoStoreEndpointExtensions
{
    public static TBuilder WithPrivateNoStoreResponses<TBuilder>(this TBuilder builder)
        where TBuilder : IEndpointConventionBuilder =>
        builder.AddEndpointFilter(new PrivateNoStoreEndpointFilter());
}
