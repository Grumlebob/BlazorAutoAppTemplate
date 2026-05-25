namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class AppConfigurationExtensions
{
    public static IConfigurationBuilder AddAppConfiguration(
        this IConfigurationBuilder configuration,
        IHostEnvironment environment)
    {
        configuration
            .AddJsonFile("settings.defaults.json", optional: false, reloadOnChange: true)
            .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
            .AddJsonFile($"appsettings.{environment.EnvironmentName}.json", optional: true, reloadOnChange: true);

        if (environment.IsEnvironment("Docker"))
        {
            configuration.AddJsonFile("appsettings.Docker.json", optional: true);
        }

        return configuration.AddEnvironmentVariables();
    }
}
