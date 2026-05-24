namespace BlazorAutoApp.Security;

internal static class AntiforgeryExtensions
{
    public static IServiceCollection AddAppAntiforgery(
        this IServiceCollection services,
        IHostEnvironment environment)
    {
        return services.AddAntiforgery(options =>
        {
            options.Cookie.Name = environment.IsEnvironment("Docker")
                ? "BlazorAutoApp.Antiforgery.Docker"
                : "BlazorAutoApp.Antiforgery";
        });
    }
}
