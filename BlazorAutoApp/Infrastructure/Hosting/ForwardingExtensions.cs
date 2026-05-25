using Microsoft.AspNetCore.HttpOverrides;
using System.Net;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class ForwardingExtensions
{
    public static IServiceCollection AddAppForwarding(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddOptions<AppForwardedHeadersOptions>()
            .Bind(configuration.GetSection(AppForwardedHeadersOptions.SectionName))
            .Validate(options => options.ForwardLimit > 0, "ForwardedHeaders:ForwardLimit must be greater than zero.")
            .Validate(options => options.KnownProxies.All(value => IPAddress.TryParse(value, out _)), "ForwardedHeaders:KnownProxies must contain valid IP addresses.")
            .Validate(options => options.KnownNetworks.All(value => System.Net.IPNetwork.TryParse(value, out _)), "ForwardedHeaders:KnownNetworks must contain valid CIDR values.")
            .ValidateOnStart();

        var configured = configuration
            .GetSection(AppForwardedHeadersOptions.SectionName)
            .Get<AppForwardedHeadersOptions>() ?? new AppForwardedHeadersOptions();

        return services.Configure<ForwardedHeadersOptions>(options =>
        {
            options.ForwardedHeaders =
                ForwardedHeaders.XForwardedFor |
                ForwardedHeaders.XForwardedProto |
                ForwardedHeaders.XForwardedHost;
            options.ForwardLimit = configured.ForwardLimit;

            options.KnownIPNetworks.Clear();
            options.KnownProxies.Clear();

            foreach (var proxy in configured.KnownProxies)
            {
                options.KnownProxies.Add(IPAddress.Parse(proxy));
            }

            foreach (var network in configured.KnownNetworks)
            {
                options.KnownIPNetworks.Add(System.Net.IPNetwork.Parse(network));
            }
        });
    }
}

internal sealed class AppForwardedHeadersOptions
{
    public const string SectionName = "ForwardedHeaders";

    public int ForwardLimit { get; init; } = 1;
    public string[] KnownProxies { get; init; } = [];
    public string[] KnownNetworks { get; init; } = [];
}
