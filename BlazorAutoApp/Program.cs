using BlazorAutoApp.Frontend;
using BlazorAutoApp.Infrastructure.Hosting;
using BlazorAutoApp.Features.Books;
using BlazorAutoApp.Features.Books.AuthorBookcase.Seed;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.Extensions.Diagnostics.HealthChecks;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddAppConfiguration(builder.Environment);
builder.AddAppObservability();
builder.Services.AddAppOptions(builder.Configuration);
builder.Services.AddProblemDetails();
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
FrontendComposition.AddFrontendServices(builder.Services, builder.Configuration);

var app = builder.Build();

app.UseAppRequestLogging();
app.UseForwardedHeaders();

FrontendComposition.UseFrontendMiddleware(app);

app.UseHttpsRedirection();

app.UseAuthentication();
app.UseAuthorization();

app.UseAppRateLimiting();
app.UseAntiforgery();

app.Use(async (ctx, next) =>
{
    ctx.Response.Headers["Permissions-Policy"] = "local-network-access=()";
    await next();
});

FrontendComposition.UseFrontendStaticFiles(app);

await app.ApplyAppMigrationsAsync();
await app.SeedAuthorBooksAsync();
await FrontendComposition.SeedFrontendDataAsync(app);

FrontendComposition.MapFrontendEndpoints(app);
app.MapAppHealthChecks();
app.MapBooksFeature();

app.Run();

public partial class Program;
