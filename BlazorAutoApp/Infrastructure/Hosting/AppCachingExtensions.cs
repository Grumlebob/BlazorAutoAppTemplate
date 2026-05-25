using Microsoft.AspNetCore.DataProtection;
using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Serilog;
using StackExchange.Redis;
using System.Security.Cryptography.X509Certificates;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class AppCachingExtensions
{
    public static IServiceCollection AddAppCachingAndDataProtection(
        this IServiceCollection services,
        IConfiguration configuration,
        IHostEnvironment environment,
        IHealthChecksBuilder healthChecks)
    {
        var redisConnection = configuration.GetSection("Redis").GetValue<string>("Configuration");
        var hasRedis = !AppOptionsExtensions.IsPlaceholder(redisConnection);
        var allowMissingRedis = AllowMissingRedis(configuration, environment);
        services.AddOptions<DataProtectionKeyStorageOptions>()
            .Bind(configuration.GetSection(DataProtectionKeyStorageOptions.SectionName))
            .Validate(options => !string.IsNullOrWhiteSpace(options.KeyStoragePath), "DataProtection:KeyStoragePath must be configured.")
            .ValidateOnStart();

        if (!hasRedis && !allowMissingRedis)
        {
            throw new InvalidOperationException(
                "Redis:Configuration must be configured outside development/test environments. " +
                "Set Redis:AllowMissing=true only for deliberate local or test fallback.");
        }

        IConnectionMultiplexer? redis = null;
        if (hasRedis)
        {
            try
            {
                redis = ConnectionMultiplexer.Connect(redisConnection!);
            }
            catch (Exception ex) when (allowMissingRedis)
            {
                hasRedis = false;
                Log.Warning(ex, "Redis is configured but unavailable; using local development cache fallbacks.");
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException(
                    "Redis is required outside development/test environments but the configured Redis endpoint is unavailable. " +
                    "Fix Redis:Configuration or set Redis:AllowMissing=true only for deliberate local or test fallback.",
                    ex);
            }
        }

        if (redis is not null)
        {
            services.AddSingleton(redis);
            services.AddStackExchangeRedisCache(options => options.Configuration = redisConnection);
            healthChecks.AddCheck<RedisHealthCheck>("redis", tags: ["ready"]);
        }
        else
        {
            services.AddDistributedMemoryCache();
        }

        var appName = configuration.GetValue<string>("App:Name") ?? "BlazorAutoApp";
        var dataProtection = services.AddDataProtection()
            .SetApplicationName(appName);

        if (redis is not null)
        {
            dataProtection.PersistKeysToStackExchangeRedis(redis, "DataProtection-Keys");
        }
        else
        {
            var keyStorageOptions = configuration
                .GetSection(DataProtectionKeyStorageOptions.SectionName)
                .Get<DataProtectionKeyStorageOptions>() ?? new DataProtectionKeyStorageOptions();
            var keysPath = ResolveDataProtectionKeyStoragePath(keyStorageOptions, environment);
            Directory.CreateDirectory(keysPath);
            dataProtection.PersistKeysToFileSystem(new DirectoryInfo(keysPath));
        }

        if (environment.IsEnvironment("Docker"))
        {
            ProtectKeysWithDockerCertificate(dataProtection);
        }
        else if (OperatingSystem.IsWindows())
        {
            dataProtection.ProtectKeysWithDpapi();
        }

        services.AddHybridCache();
        services.AddAppCacheInvalidation(configuration, environment, hasRedis);
        return services;
    }

    private static bool AllowMissingRedis(IConfiguration configuration, IHostEnvironment environment) =>
        environment.IsDevelopment()
        || environment.IsEnvironment("Testing")
        || configuration.GetSection("Redis").GetValue<bool>("AllowMissing");

    private static string ResolveDataProtectionKeyStoragePath(
        DataProtectionKeyStorageOptions options,
        IHostEnvironment environment)
    {
        return Path.GetFullPath(options.KeyStoragePath, environment.ContentRootPath);
    }

    private static void ProtectKeysWithDockerCertificate(IDataProtectionBuilder dataProtection)
    {
        var certificatePath = Environment.GetEnvironmentVariable("ASPNETCORE_Kestrel__Certificates__Default__Path");
        var certificatePassword = Environment.GetEnvironmentVariable("ASPNETCORE_Kestrel__Certificates__Default__Password");
        if (string.IsNullOrWhiteSpace(certificatePath) || !File.Exists(certificatePath))
        {
            return;
        }

        try
        {
            dataProtection.ProtectKeysWithCertificate(
                X509CertificateLoader.LoadPkcs12FromFile(certificatePath, certificatePassword));
        }
        catch (Exception ex)
        {
            Log.Warning(ex, "Failed to configure Data Protection certificate encryption from {CertificatePath}", certificatePath);
        }
    }
}

internal sealed class DataProtectionKeyStorageOptions
{
    public const string SectionName = "DataProtection";

    public string KeyStoragePath { get; init; } = Path.Combine("..", "data", "storage", "DataProtection-Keys");
}
