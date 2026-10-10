using BlazorAutoApp.Client.Features.Books.AuthorBookcase;
using BlazorAutoApp.Client.Features.Books.UserBookcase;
using BlazorAutoApp.Components;
using BlazorAutoApp.Features.Books.AuthorBookcase.Seed;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Account.Seed;
using BlazorAutoApp.Infrastructure.Hosting;
using ClientImports = BlazorAutoApp.Client._Imports;

namespace BlazorAutoApp.Frontend;

internal static class FrontendComposition
{
    public static void AddFrontendServices(IServiceCollection services, IConfiguration configuration)
    {
        services.AddRazorComponents()
            .AddInteractiveServerComponents()
            .AddInteractiveWebAssemblyComponents()
            .AddAuthenticationStateSerialization();

        services.AddBlazorIdentityUi(configuration);
        services.AddScoped<AuthorBookcaseState>();
        services.AddScoped<UserBookcaseState>();
    }

    public static void UseFrontendMiddleware(WebApplication app)
    {
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
    }

    public static Task SeedFrontendDataAsync(WebApplication app) => app.SeedLocalLoginAccountsAsync();

    public static void MapFrontendEndpoints(WebApplication app)
    {
        app.MapStaticAssets();
        app.MapPublicPageHeadRequests();
        app.MapRazorComponents<App>()
            .AddInteractiveServerRenderMode()
            .AddInteractiveWebAssemblyRenderMode()
            .AddAdditionalAssemblies(typeof(ClientImports).Assembly);
        app.MapAdditionalIdentityEndpoints();
    }

    private static bool ShouldRenderStatusCodePage(HttpContext context)
    {
        if (context.Request.Path.StartsWithSegments("/api"))
        {
            return false;
        }

        return HttpMethods.IsGet(context.Request.Method) || HttpMethods.IsHead(context.Request.Method);
    }
}
