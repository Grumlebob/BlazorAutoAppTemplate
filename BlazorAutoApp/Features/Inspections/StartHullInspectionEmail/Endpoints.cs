using BlazorAutoApp.Core.Features.Inspections.StartHullInspectionEmail;

namespace BlazorAutoApp.Features.Inspections.StartHullInspectionEmail;

public static class StartHullInspectionEmailEndpoints
{
    public static IEndpointRouteBuilder MapStartHullInspectionEmailEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("api/start-hull-inspection-email");

        group.MapGet("/companies", async (IStartHullInspectionEmailApi api, CancellationToken ct) =>
        {
            var res = await api.GetCompaniesAsync(ct);
            return Results.Ok(res);
        });

        group.MapPost("/start", async (StartHullInspectionRequest req, IStartHullInspectionEmailApi api, CancellationToken ct) =>
        {
            if (req is null) return Results.BadRequest(new StartHullInspectionResponse { Success = false, Error = "Invalid request" });
            var res = await api.StartAsync(req, ct);
            if (res.Success) return Results.Accepted($"/api/start-hull-inspection-email/start/{req.CompanyId}", res);
            return Results.BadRequest(res);
        });

        return routes;
    }
}
