namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal static class CacheInvalidationServiceCollectionExtensions
{
    public static IServiceCollection AddAppCacheInvalidation(
        this IServiceCollection services,
        IConfiguration configuration,
        IHostEnvironment environment,
        bool hasRedis)
    {
        var section = configuration.GetSection(CacheInvalidationOptions.SectionName);
        var enabled = section.GetSection(nameof(CacheInvalidationOptions.Enabled)).Exists()
            ? section.GetValue<bool>(nameof(CacheInvalidationOptions.Enabled))
            : hasRedis;
        var invalidationEnabled = hasRedis && enabled;
        var appName = configuration.GetValue<string>("App:Name") ?? "BlazorAutoApp";
        var environmentName = environment.EnvironmentName;
        var nodeId = section.GetValue<string>(nameof(CacheInvalidationOptions.NodeId))
            ?? Environment.GetEnvironmentVariable("CACHE_INVALIDATION_NODE_ID");

        services.AddOptions<CacheInvalidationOptions>()
            .Bind(section)
            .Configure(options =>
            {
                options.Enabled = invalidationEnabled;
                options.AppName = appName;
                options.EnvironmentName = environmentName;
                options.NodeId = string.IsNullOrWhiteSpace(options.NodeId) ? nodeId : options.NodeId;
            })
            .Validate(options => !string.IsNullOrWhiteSpace(options.AppName), "Cache invalidation app name must be configured.")
            .Validate(options => !string.IsNullOrWhiteSpace(options.EnvironmentName), "Cache invalidation environment name must be configured.")
            .Validate(options => options.PublishTimeoutSeconds > 0, "Cache:Invalidation:PublishTimeoutSeconds must be greater than 0.")
            .Validate(options => options.ApplyTimeoutSeconds > 0, "Cache:Invalidation:ApplyTimeoutSeconds must be greater than 0.")
            .ValidateOnStart();

        services.AddSingleton<ICacheInvalidationApplier, HybridCacheInvalidationApplier>();
        services.AddSingleton<ICacheInvalidator, HybridCacheInvalidator>();

        if (invalidationEnabled)
        {
            services.AddSingleton<ICacheInvalidationPublisher, RedisCacheInvalidationPublisher>();
            services.AddHostedService<RedisCacheInvalidationSubscriber>();
        }
        else
        {
            services.AddSingleton<ICacheInvalidationPublisher, NoOpCacheInvalidationPublisher>();
        }

        return services;
    }
}
