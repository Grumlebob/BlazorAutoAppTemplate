using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Http.Json;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class ApiJsonExtensions
{
    /// <summary>
    /// Numbers are numbers on the wire. The web defaults also accept numeric strings,
    /// which makes the OpenAPI schema (and generated TypeScript) type every integer as
    /// <c>number | string</c>.
    /// </summary>
    public static IServiceCollection AddAppApiJson(this IServiceCollection services) =>
        services.Configure<JsonOptions>(options => options.SerializerOptions.NumberHandling = JsonNumberHandling.Strict);
}
