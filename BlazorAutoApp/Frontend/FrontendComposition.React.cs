using BlazorAutoApp.Features.Login;

namespace BlazorAutoApp.Frontend;

internal static class FrontendComposition
{
    public static void AddFrontendServices(IServiceCollection services, IConfiguration configuration)
    {
        services.AddScoped<ICurrentUserAccessor, HttpPrincipalCurrentUserAccessor>();
    }

    public static void UseFrontendMiddleware(WebApplication app)
    {
        if (!app.Environment.IsDevelopment())
        {
            app.UseExceptionHandler();
            app.UseHsts();
        }
    }

    public static Task SeedFrontendDataAsync(WebApplication app) => Task.CompletedTask;

    public static void MapFrontendEndpoints(WebApplication app)
    {
        // React static assets and SPA routes are added by the static-hosting packet.
    }
}
