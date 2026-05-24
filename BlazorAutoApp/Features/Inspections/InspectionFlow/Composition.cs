using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Contracts;
using BlazorAutoApp.Features.Inspections.InspectionFlow.Endpoints;
using BlazorAutoApp.Features.Inspections.InspectionFlow.Services;

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
