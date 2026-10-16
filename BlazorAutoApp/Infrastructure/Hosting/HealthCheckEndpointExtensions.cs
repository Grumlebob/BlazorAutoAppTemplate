using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using System.Text.Json;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class HealthCheckEndpointExtensions
{
    public static IEndpointRouteBuilder MapAppHealthChecks(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapHealthChecks("/health/live", new HealthCheckOptions
        {
            Predicate = check => check.Tags.Contains("live")
        });
        endpoints.MapHealthChecks("/health/ready", new HealthCheckOptions
        {
            Predicate = check => check.Tags.Contains("ready")
        });
        endpoints.MapHealthChecks("/health", new HealthCheckOptions
        {
            Predicate = check => check.Tags.Contains("ready")
        });
        endpoints.MapHealthChecks("/health/mail", new HealthCheckOptions
        {
            Predicate = check => check.Tags.Contains("account-mail"),
            ResponseWriter = async (context, report) =>
            {
                context.Response.ContentType = "application/json";
                var checks = report.Entries.ToDictionary(
                    entry => entry.Key,
                    entry => new { status = entry.Value.Status.ToString(), description = entry.Value.Description, data = entry.Value.Data });
                await JsonSerializer.SerializeAsync(context.Response.Body, new { status = report.Status.ToString(), checks }, cancellationToken: context.RequestAborted);
            }
        });

        return endpoints;
    }
}
