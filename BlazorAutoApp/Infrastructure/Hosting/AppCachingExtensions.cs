using Microsoft.AspNetCore.DataProtection;
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
        services.AddOptions<DataProtectionKeyStorageOptions>()
            .Bind(configuration.GetSection(DataProtectionKeyStorageOptions.SectionName))
            .Validate(options => !string.IsNullOrWhiteSpace(options.KeyStoragePath), "DataProtection:KeyStoragePath must be configured.")
            .ValidateOnStart();

        IConnectionMultiplexer? redis = null;
        if (hasRedis)
        {
            redis = ConnectionMultiplexer.Connect(redisConnection!);
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
        return services;
    }

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
