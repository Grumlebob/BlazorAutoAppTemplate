using BlazorAutoApp.Core.Features.IdentityShowcase;

namespace BlazorAutoApp.Features.IdentityShowcase;

public static class Endpoints
{
    public static IEndpointRouteBuilder MapIdentityShowcaseEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/identity-showcase");

        group.MapGet("/public", async (IIdentityShowcaseApi api, CancellationToken ct) =>
        {
            var result = await api.GetPublicAsync(ct);
            return Results.Ok(result);
        });

        group.MapGet("/secure", async (IIdentityShowcaseApi api, CancellationToken ct) =>
        {
            var result = await api.GetSecureAsync(ct);
            return result is null ? Results.Unauthorized() : Results.Ok(result);
        })
        .RequireAuthorization();

        group.MapGet("/admin-probe", async (IIdentityShowcaseApi api, CancellationToken ct) =>
        {
            var result = await api.GetAdminProbeAsync(ct);
            return Results.Ok(result);
        })
        .RequireAuthorization(policy => policy.RequireRole("Admin"));

        return routes;
    }
}
