using System.Reflection;
using System.Threading.RateLimiting;
using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Features.Books;
using BlazorAutoApp.Infrastructure.Hosting;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.OpenApi;
using Microsoft.OpenApi;

namespace BlazorAutoApp.Frontend.OpenApi;

internal static class OpenApiMetadataHosting
{
    private const string GeneratorEntryAssemblyName = "GetDocument.Insider";
    private const string CookieSchemeName = "IdentityApplicationCookie";
    private const string CookieName = ".AspNetCore.Identity.Application";

    public static bool IsOpenApiGenerationProcess() =>
        string.Equals(
            Assembly.GetEntryAssembly()?.GetName().Name,
            GeneratorEntryAssemblyName,
            StringComparison.Ordinal);

    public static WebApplicationBuilder CreateBuilder()
    {
        var builder = WebApplication.CreateEmptyBuilder(new WebApplicationOptions
        {
            ApplicationName = typeof(Program).Assembly.GetName().Name,
            Args = [],
            EnvironmentName = Environments.Production
        });

        builder.Services.AddRouting();
        builder.Services.AddAuthorization();
        builder.Services.AddRateLimiter(options =>
            options.AddPolicy(
                AppRateLimiting.ApiPolicyName,
                _ => RateLimitPartition.GetNoLimiter("openapi-metadata")));

        // Minimal API binding uses IServiceProviderIsService to distinguish service
        // parameters from request bodies. These metadata-only registrations make
        // the real handlers' service parameters unambiguous without constructing
        // persistence or cache services.
        builder.Services.AddScoped<IBooksApi>(_ =>
            throw new InvalidOperationException("Book services are unavailable during OpenAPI metadata generation."));
        builder.Services.AddScoped<IAuthorBooksApi>(_ =>
            throw new InvalidOperationException("Author-book services are unavailable during OpenAPI metadata generation."));

        builder.Services.AddOpenApi("v1", options =>
        {
            options.OpenApiVersion = OpenApiSpecVersion.OpenApi3_1;
            options.AddDocumentTransformer((document, _, _) =>
            {
                document.Info ??= new OpenApiInfo();
                document.Info.Title = "Blazor Auto public and private API";
                document.Info.Version = "v1";
                document.Components ??= new OpenApiComponents();
                document.Components.SecuritySchemes ??= new Dictionary<string, IOpenApiSecurityScheme>();
                document.Components.SecuritySchemes[CookieSchemeName] = new OpenApiSecurityScheme
                {
                    Type = SecuritySchemeType.ApiKey,
                    In = ParameterLocation.Cookie,
                    Name = CookieName,
                    Description = "The existing ASP.NET Core Identity application cookie."
                };

                return Task.CompletedTask;
            });
            options.AddOperationTransformer((operation, context, _) =>
            {
                var endpointMetadata = context.Description.ActionDescriptor.EndpointMetadata;
                var requiresAuthorization = endpointMetadata.OfType<IAuthorizeData>().Any()
                    && !endpointMetadata.OfType<IAllowAnonymous>().Any();

                if (requiresAuthorization)
                {
                    operation.Security ??= [];
                    operation.Security.Add(new OpenApiSecurityRequirement
                    {
                        [new OpenApiSecuritySchemeReference(CookieSchemeName, context.Document)] = []
                    });
                }

                return Task.CompletedTask;
            });
        });

        return builder;
    }

    public static void MapEndpoints(WebApplication app)
    {
        app.MapBooksFeature();
        app.MapOpenApi();
    }
}
