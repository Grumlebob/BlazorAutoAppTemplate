using System.Security.Cryptography;
using System.Text;
using GrumPlates.Core.Features.Accounts.Contracts;

namespace GrumPlates.Features.Accounts;

internal sealed class AccountApplicationIdentity(string appName, string environmentName)
{
    public string AppName { get; } = appName;
    // Length prefixes keep separators in names from creating ambiguous identities.
    public string Id { get; } = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(
        $"{appName.Length}:{appName}{environmentName.Length}:{environmentName}")))[..32];
}

internal static class ClientConfigurationEndpoints
{
    public static IEndpointRouteBuilder MapClientConfiguration(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapGet("/api/client-config", (HttpContext context, AccountOptions options, AccountApplicationIdentity identity) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return TypedResults.Ok(new ClientConfiguration(1, options.Enabled, identity.Id));
        }).WithName("ClientConfiguration").WithTags("Accounts").AllowAnonymous();
        return endpoints;
    }
}
