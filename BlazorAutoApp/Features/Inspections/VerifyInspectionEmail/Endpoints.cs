using BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail;

namespace BlazorAutoApp.Features.Inspections.VerifyInspectionEmail;

public static class InspectionEndpoints
{
    public static IEndpointRouteBuilder MapInspectionEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("api/inspection");

        group.MapPost("/{id:guid}/verify", async (Guid id, VerifyInspectionPasswordRequest req, IInspectionApi api, CancellationToken ct) =>
        {
            if (req is null || req.Id != id) return Results.BadRequest(new VerifyInspectionPasswordResponse { Success = false, Error = "Invalid request" });
            var res = await api.VerifyPasswordAsync(req, ct);
            if (res.Success) return Results.Ok(res);
            return Results.BadRequest(res);
        });

        group.MapGet("/{id:guid}/status", async (Guid id, IInspectionApi api, CancellationToken ct) =>
        {
            var res = await api.GetStatusAsync(id, ct);
            return Results.Ok(res);
        });

        return routes;
    }
}
