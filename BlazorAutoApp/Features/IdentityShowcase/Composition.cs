using BlazorAutoApp.Core.Features.IdentityShowcase;

namespace BlazorAutoApp.Features.IdentityShowcase;

public static class Composition
{
    public static IServiceCollection AddIdentityShowcaseFeature(this IServiceCollection services)
    {
        services.AddHttpContextAccessor();
        services.AddScoped<IIdentityShowcaseApi, IdentityShowcaseServerService>();
        return services;
    }

    public static IEndpointRouteBuilder MapIdentityShowcaseFeature(this IEndpointRouteBuilder routes)
    {
        routes.MapIdentityShowcaseEndpoints();
        return routes;
    }
}
