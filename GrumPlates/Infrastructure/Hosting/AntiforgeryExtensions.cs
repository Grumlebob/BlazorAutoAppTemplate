namespace GrumPlates.Infrastructure.Hosting;

internal static class AntiforgeryExtensions
{
    public static IServiceCollection AddAppAntiforgery(
        this IServiceCollection services,
        IHostEnvironment environment)
    {
        return services.AddAntiforgery(options =>
        {
            options.Cookie.Name = environment.IsEnvironment("Docker")
                ? "GrumPlates.Antiforgery.Docker"
                : "GrumPlates.Antiforgery";
        });
    }
}
