using BlazorAutoApp.Caching;
using BlazorAutoApp.Components;
using BlazorAutoApp.Configuration;
using BlazorAutoApp.Data;
using BlazorAutoApp.Diagnostics;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Movies;
using BlazorAutoApp.Security;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using ClientImports = BlazorAutoApp.Client._Imports;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddAppConfiguration(builder.Environment);
builder.AddAppObservability();
builder.Services.AddAppOptions(builder.Configuration);

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
builder.Services.AddMoviesFeature(builder.Configuration);
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

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode()
    .AddInteractiveWebAssemblyRenderMode()
    .AddAdditionalAssemblies(typeof(ClientImports).Assembly);
app.MapAdditionalIdentityEndpoints();
app.MapAppHealthChecks();
app.MapMoviesFeature();

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
