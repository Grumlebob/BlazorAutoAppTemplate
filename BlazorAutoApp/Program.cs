using BlazorAutoApp.Components;
using BlazorAutoApp.Infrastructure.Hosting;
using BlazorAutoApp.Client.Features.Books.UserBookcase;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Account.Seed;
using BlazorAutoApp.Features.Books;
using BlazorAutoApp.Features.Books.AuthorBookcase.Seed;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using ClientImports = BlazorAutoApp.Client._Imports;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddAppConfiguration(builder.Environment);
builder.AddAppObservability();
builder.Services.AddAppOptions(builder.Configuration);
builder.Services.AddProblemDetails();
builder.Services.AddValidation();

builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents()
    .AddInteractiveWebAssemblyComponents()
    .AddAuthenticationStateSerialization();

var healthChecks = builder.Services
    .AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy(), tags: ["live"]);

builder.Services.AddAppForwarding(builder.Configuration);
builder.Services.AddAppAntiforgery(builder.Environment);
builder.Services.AddAppCachingAndDataProtection(builder.Configuration, builder.Environment, healthChecks);
builder.Services.AddAppPersistence(builder.Configuration, healthChecks);
builder.Services.AddAppRateLimiting(builder.Configuration);
builder.Services.AddBooksFeature(builder.Configuration);
builder.Services.AddScoped<UserBookcaseState>();
builder.Services.AddLoginFeature(builder.Configuration);

var app = builder.Build();

app.UseAppRequestLogging();
app.UseForwardedHeaders();

if (app.Environment.IsDevelopment())
{
    app.UseWebAssemblyDebugging();
}
else
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseWhen(ShouldRenderStatusCodePage, branch =>
{
    branch.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);
});

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

await app.ApplyAppMigrationsAsync();
await app.SeedAuthorBooksAsync();
await app.SeedLocalLoginAccountsAsync();

app.MapStaticAssets();
app.MapPublicPageHeadRequests();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode()
    .AddInteractiveWebAssemblyRenderMode()
    .AddAdditionalAssemblies(typeof(ClientImports).Assembly);
app.MapAdditionalIdentityEndpoints();
app.MapAppHealthChecks();
app.MapBooksFeature();

app.Run();

static bool ShouldRenderStatusCodePage(HttpContext context)
{
    if (context.Request.Path.StartsWithSegments("/api"))
    {
        return false;
    }

    return HttpMethods.IsGet(context.Request.Method) || HttpMethods.IsHead(context.Request.Method);
}

public partial class Program;
