using GrumPlates.Client.Features.Books.AuthorBookcase;
using GrumPlates.Client.Features.Books.UserBookcase;
using GrumPlates.Components;
using GrumPlates.Features.Books.AuthorBookcase.Seed;
using GrumPlates.Features.Login.Account;
using GrumPlates.Features.Login.Accounts.Email;
using GrumPlates.Features.Login.Account.Seed;
using GrumPlates.Infrastructure.Hosting;
using ClientImports = GrumPlates.Client._Imports;

namespace GrumPlates.Frontend;

internal static class FrontendComposition
{
    public static void AddFrontendServices(IServiceCollection services, IConfiguration configuration)
    {
        services.AddRazorComponents()
            .AddInteractiveServerComponents()
            .AddInteractiveWebAssemblyComponents()
            .AddAuthenticationStateSerialization();

        services.AddBlazorIdentityUi(configuration);
        services.AddSingleton<IAccountMailFrontend>(AccountMailFrontend.BlazorAuto);
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

    public static void UseFrontendStaticFiles(WebApplication app)
    {
    }

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
