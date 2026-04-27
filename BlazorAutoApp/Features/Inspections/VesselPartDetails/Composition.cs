using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails;

namespace BlazorAutoApp.Features.Inspections.VesselPartDetails;

public static class Composition
{
    public static IServiceCollection AddVesselPartDetailsFeature(this IServiceCollection services)
    {
        services.AddScoped<IVesselPartDetailsApi, VesselPartDetailsServerService>();
        return services;
    }

    public static IEndpointRouteBuilder MapVesselPartDetailsFeature(this IEndpointRouteBuilder routes)
    {
        routes.MapVesselPartDetailsEndpoints();
        return routes;
    }
}
