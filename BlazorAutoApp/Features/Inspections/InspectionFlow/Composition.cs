using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

namespace BlazorAutoApp.Features.Inspections.InspectionFlow;

public static class Composition
{
    public static IServiceCollection AddInspectionFlowFeature(this IServiceCollection services)
    {
        services.AddScoped<IInspectionFlowApi, InspectionFlowServerService>();
        return services;
    }

    public static IEndpointRouteBuilder MapInspectionFlowFeature(this IEndpointRouteBuilder routes)
    {
        routes.MapInspectionFlowEndpoints();
        return routes;
    }
}
