namespace BlazorAutoApp.Configuration;

internal static class AppOptionsExtensions
{
    public static IServiceCollection AddAppOptions(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddOptions<AppOptions>()
            .Bind(configuration.GetSection(AppOptions.SectionName))
            .ValidateDataAnnotations()
            .Validate(options => !IsPlaceholder(options.Name), "App:Name must be configured.")
            .ValidateOnStart();

        return services;
    }

    internal static bool IsPlaceholder(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ||
            string.Equals(value, "INJECT_THIS_IN_ORDER_TO_RUN", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(value, "CHANGE_ME", StringComparison.OrdinalIgnoreCase);
    }
}
