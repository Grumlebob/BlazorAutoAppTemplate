using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails;

namespace BlazorAutoApp.Features.Inspections.VesselPartDetails;

public static class VesselPartDetailsEndpoints
{
    public static IEndpointRouteBuilder MapVesselPartDetailsEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("api/vessel-part-details");

        group.MapGet("/{vesselPartId:int}", async (int vesselPartId, IVesselPartDetailsApi api, CancellationToken ct) =>
        {
            var res = await api.GetAsync(vesselPartId, ct);
            return Results.Ok(res);
        });

        group.MapPut("/{vesselPartId:int}", async (int vesselPartId, UpsertVesselPartDetailsRequest req, IVesselPartDetailsApi api, CancellationToken ct) =>
        {
            if (req is null || req.InspectionVesselPartId != vesselPartId)
                return Results.BadRequest(new UpsertVesselPartDetailsResponse { Success = false, Error = "Invalid request" });
            var res = await api.UpsertAsync(req, ct);
            if (res.Success) return Results.Ok(res);
            return Results.BadRequest(res);
        })
        .AddEndpointFilter(new BlazorAutoApp.Features.Movies.MoviesValidateFilter<UpsertVesselPartDetailsRequest>());

        return routes;
    }
}
