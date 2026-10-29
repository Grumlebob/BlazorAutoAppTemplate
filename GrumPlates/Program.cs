using GrumPlates.Features.Accounts;
using GrumPlates.Features.Accounts.Endpoints;
using GrumPlates.Features.Accounts.Identity;
using GrumPlates.Features.Accounts.Security;
using GrumPlates.Features.Books;
using GrumPlates.Features.Books.AuthorBookcase.Seed;
using GrumPlates.Frontend;
using GrumPlates.Frontend.OpenApi;
using GrumPlates.Infrastructure.Hosting;
using GrumPlates.Infrastructure.Persistence;
using Microsoft.Extensions.Diagnostics.HealthChecks;

if (OpenApiMetadataHosting.IsOpenApiGenerationProcess())
{
    var metadataBuilder = OpenApiMetadataHosting.CreateBuilder();
    var metadataApp = metadataBuilder.Build();
    OpenApiMetadataHosting.MapEndpoints(metadataApp);
    await metadataApp.RunAsync();
    return;
}

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddAppConfiguration(builder.Environment);
builder.AddAppObservability();
builder.Services.AddAppOptions(builder.Configuration);
builder.Services.AddProblemDetails(options =>
{
    options.CustomizeProblemDetails = context =>
    {
        if (!context.HttpContext.Request.Path.StartsWithSegments("/api/auth", StringComparison.OrdinalIgnoreCase)
            || context.ProblemDetails.Extensions.ContainsKey("code"))
        {
            return;
        }

        context.ProblemDetails.Extensions["code"] = context.ProblemDetails.Status switch
        {
            StatusCodes.Status400BadRequest => "RequestInvalid",
            StatusCodes.Status401Unauthorized => "AuthenticationRequired",
            StatusCodes.Status403Forbidden => "CapabilityDisabled",
            StatusCodes.Status409Conflict => "AccountConflict",
            StatusCodes.Status413PayloadTooLarge => "RequestTooLarge",
            StatusCodes.Status415UnsupportedMediaType => "UnsupportedMediaType",
            StatusCodes.Status429TooManyRequests => "RateLimited",
            StatusCodes.Status503ServiceUnavailable => "AccountServiceUnavailable",
            _ => "AccountRequestFailed"
        };
    };
});
builder.Services.AddAppApiJson();
builder.Services.AddValidation();

var healthChecks = builder.Services
    .AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy(), tags: ["live"]);

builder.Services.AddAppForwarding(builder.Configuration);
builder.Services.AddAppAntiforgery(builder.Environment);
builder.Services.AddAppCachingAndDataProtection(builder.Configuration, builder.Environment, healthChecks);
builder.Services.AddAppPersistence(builder.Configuration, healthChecks);
builder.Services.AddAppRateLimiting(builder.Configuration);
builder.Services.AddBooksFeature(builder.Configuration);
builder.Services.AddIdentityBackend();
builder.Services.AddAccountFeature(builder.Configuration, builder.Environment);
FrontendComposition.AddFrontendServices(builder.Services, builder.Configuration);

var app = builder.Build();

app.UseAppRequestLogging();
app.UseForwardedHeaders();

FrontendComposition.UseFrontendMiddleware(app);

// Account middleware reads endpoint markers before authentication and body binding.
app.UseRouting();
app.UseHttpsRedirection();
app.UseAccountRequestPolicies();

app.UseAuthentication();
app.UseAppRateLimiting();
app.UseAccountJsonBodyLimits();
app.UseAuthorization();
app.UseAccountPrincipalGuards();

app.UseAntiforgery();

app.Use(async (ctx, next) =>
{
    // The React host sets its wider policy earlier in the pipeline; the Blazor profile keeps this one.
    ctx.Response.Headers.TryAdd("Permissions-Policy", "local-network-access=()");
    await next();
});

FrontendComposition.UseFrontendStaticFiles(app);

await app.ApplyAppMigrationsAsync();
await app.ImportAndValidateDataProtectionKeysAsync();
await app.SeedConfiguredAdminAsync();
await app.SeedAuthorBooksAsync();
await FrontendComposition.SeedFrontendDataAsync(app);

FrontendComposition.MapFrontendEndpoints(app);
app.MapAppHealthChecks();
app.MapBooksFeature();
app.MapClientConfiguration();
if (app.Services.GetRequiredService<AccountOptions>().Enabled)
{
    app.MapAccountEndpoints();
}

app.Run();
