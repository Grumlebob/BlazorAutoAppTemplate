using Microsoft.AspNetCore.HttpOverrides;

namespace BlazorAutoApp.Diagnostics;

internal static class ForwardingExtensions
{
    public static IServiceCollection AddAppForwarding(this IServiceCollection services)
    {
        return services.Configure<ForwardedHeadersOptions>(options =>
        {
            options.ForwardedHeaders =
                ForwardedHeaders.XForwardedFor |
                ForwardedHeaders.XForwardedProto |
                ForwardedHeaders.XForwardedHost;
            options.KnownIPNetworks.Clear();
            options.KnownProxies.Clear();
        });
    }
}
