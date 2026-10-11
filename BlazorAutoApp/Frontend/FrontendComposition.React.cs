using BlazorAutoApp.Features.Login;

namespace BlazorAutoApp.Frontend;

internal static class FrontendComposition
{
    public static void AddFrontendServices(IServiceCollection services, IConfiguration configuration)
    {
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

        ReactFrontendHosting.UseSecurityHeaders(app);
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
