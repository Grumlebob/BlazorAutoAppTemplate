using GrumPlates.Features.Accounts.Email;
using GrumPlates.Features.Accounts.Identity;

namespace GrumPlates.Frontend;

internal static class FrontendComposition
{
    public static void AddFrontendServices(IServiceCollection services, IConfiguration configuration)
    {
        ReactFrontendHosting.AddResponseCompression(services);
        services.AddSingleton<IAccountMailFrontend>(AccountMailFrontend.React);
        services.AddScoped<ICurrentUserAccessor, HttpPrincipalCurrentUserAccessor>();
        services.AddSingleton<ReactFrontendStaticRoot>();
    }

    public static void UseFrontendMiddleware(WebApplication app)
    {
        if (!app.Environment.IsDevelopment())
        {
            app.UseExceptionHandler();
            app.UseHsts();
        }

        var staticRoot = app.Services.GetService<ReactFrontendStaticRoot>();
        ReactFrontendHosting.UseSecurityHeaders(app, staticRoot?.FileProvider);
    }

    public static void UseFrontendStaticFiles(WebApplication app)
    {
        ReactFrontendHosting.UseStaticFiles(
            app,
            app.Services.GetRequiredService<ReactFrontendStaticRoot>().FileProvider);
    }

    public static Task SeedFrontendDataAsync(WebApplication app) => Task.CompletedTask;

    public static void MapFrontendEndpoints(WebApplication app)
    {
        ReactFrontendHosting.MapNavigationFallback(
            app,
            app.Services.GetRequiredService<ReactFrontendStaticRoot>().FileProvider);
    }
}
