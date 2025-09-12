using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

namespace BlazorAutoApp.Features.Inspections.InspectionFlow;

public static class InspectionFlowEndpoints
{
    public static IEndpointRouteBuilder MapInspectionFlowEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("api/inspection-flow");

        group.MapGet("/{id:guid}", async (Guid id, IInspectionFlowApi api, CancellationToken ct) =>
        {
            var res = await api.GetAsync(id, ct);
            return Results.Ok(res);
        });

        group.MapPost("/{id:guid}", async (Guid id, UpsertInspectionFlowRequest req, IInspectionFlowApi api, CancellationToken ct) =>
        {
            if (req is null || req.Id != id) return Results.BadRequest(new UpsertInspectionFlowResponse { Success = false, Error = "Invalid request" });
            var res = await api.UpsertAsync(req, ct);
            if (res.Success) return Results.Ok(res);
            return Results.BadRequest(res);
        });

        group.MapGet("/vessels", async (IInspectionFlowApi api, CancellationToken ct) =>
        {
            var res = await api.GetVesselsAsync(ct);
            return Results.Ok(res);
        });


        return routes;
    }
}
