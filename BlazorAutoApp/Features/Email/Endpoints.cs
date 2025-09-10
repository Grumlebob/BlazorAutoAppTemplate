using BlazorAutoApp.Core.Features.Email;

namespace BlazorAutoApp.Features.Email;

public static class EmailEndpoints
{
    public static IEndpointRouteBuilder MapEmailEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/email");

        group.MapPost("/send", async (SendEmailRequest req, IEmailApi email, CancellationToken ct) =>
        {
            if (string.IsNullOrWhiteSpace(req.To)) return Results.BadRequest("Missing 'To'");
            var res = await email.SendAsync(req, ct);
            return res.Success ? Results.Accepted("/api/email/send", res) : Results.BadRequest(res);
        });

        return routes;
    }
}

