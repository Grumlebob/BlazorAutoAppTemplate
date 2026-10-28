using Microsoft.AspNetCore.DataProtection;
using GrumPlates.Infrastructure.Hosting.CacheInvalidation;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Serilog;
using StackExchange.Redis;
using System.Security.Cryptography.X509Certificates;

namespace GrumPlates.Infrastructure.Hosting;

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
        var accountsEnabled = configuration.GetValue<bool>("Accounts:Enabled");
        var allowMissingRedis = AllowMissingRedis(configuration, environment);
        services.AddOptions<DataProtectionKeyStorageOptions>()
            .Bind(configuration.GetSection(DataProtectionKeyStorageOptions.SectionName))
            .Validate(options => accountsEnabled || !string.IsNullOrWhiteSpace(options.KeyStoragePath), "DataProtection:KeyStoragePath must be configured.")
            .Validate(options => options.HasValidLegacySource(), "DataProtection legacy key source settings are incomplete or ambiguous.")
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
            services.AddStackExchangeRedisCache(options =>
            {
                options.ConnectionMultiplexerFactory = () => Task.FromResult<IConnectionMultiplexer>(redis);
            });
            healthChecks.AddCheck<RedisHealthCheck>("redis", tags: ["ready"]);
        }
        else
        {
            services.AddDistributedMemoryCache();
        }

        var appName = configuration.GetValue<string>("App:Name") ?? "GrumPlates";
        var dataProtection = services.AddDataProtection()
            .SetApplicationName(appName);

        if (accountsEnabled)
        {
            dataProtection.PersistKeysToDbContext<AppDbContext>();
        }
        else if (redis is not null)
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

        if (accountsEnabled)
        {
            ConfigureEnabledAccountKeyEncryption(dataProtection, configuration, environment, services);
        }
        else if (environment.IsEnvironment("Docker"))
        {
            ProtectKeysWithDockerCertificate(dataProtection);
        }
        else if (OperatingSystem.IsWindows())
        {
            dataProtection.ProtectKeysWithDpapi();
        }

        services.AddHybridCache(options =>
        {
            options.MaximumKeyLength = 1024;
            options.MaximumPayloadBytes = 1024 * 1024;
            // Tag metrics add a dimension per cache tag; keep metric cardinality bounded.
            options.ReportTagMetrics = false;
        });
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

    private static void ConfigureEnabledAccountKeyEncryption(
        IDataProtectionBuilder dataProtection,
        IConfiguration configuration,
        IHostEnvironment environment,
        IServiceCollection services)
    {
        if (OperatingSystem.IsWindows() && environment.IsDevelopment())
        {
            dataProtection.ProtectKeysWithDpapi();
            return;
        }

        var certificatePath = configuration[$"{DataProtectionKeyStorageOptions.SectionName}:KeyEncryptionCertificatePath"]
            ?? Environment.GetEnvironmentVariable("ASPNETCORE_Kestrel__Certificates__Default__Path");
        var certificatePassword = configuration[$"{DataProtectionKeyStorageOptions.SectionName}:KeyEncryptionCertificatePassword"]
            ?? Environment.GetEnvironmentVariable("ASPNETCORE_Kestrel__Certificates__Default__Password");

        if (string.IsNullOrWhiteSpace(certificatePath) || !File.Exists(certificatePath))
        {
            throw new InvalidOperationException(
                "Enabled accounts require DataProtection:KeyEncryptionCertificatePath and its password outside Windows Development.");
        }

        X509Certificate2 certificate;
        try
        {
            certificate = Path.GetExtension(certificatePath).Equals(".pfx", StringComparison.OrdinalIgnoreCase)
                ? X509CertificateLoader.LoadPkcs12FromFile(
                    certificatePath,
                    certificatePassword,
                    X509KeyStorageFlags.EphemeralKeySet)
                : X509Certificate2.CreateFromEncryptedPemFile(certificatePath, certificatePassword ?? string.Empty);
        }
        catch (Exception)
        {
            throw new InvalidOperationException(
                "The configured Data Protection key-encryption certificate could not be loaded.");
        }

        if (!certificate.HasPrivateKey)
        {
            certificate.Dispose();
            throw new InvalidOperationException(
                "The configured Data Protection key-encryption certificate must include its private key.");
        }

        services.AddSingleton<X509Certificate2>(_ => certificate);
        dataProtection
            .ProtectKeysWithCertificate(certificate)
            .UnprotectKeysWithAnyCertificate(certificate);
    }
}

internal sealed class DataProtectionKeyStorageOptions
{
    public const string SectionName = "DataProtection";

    public string KeyStoragePath { get; init; } = Path.Combine("..", "data", "storage", "DataProtection-Keys");
    public string LegacyKeyStore { get; init; } = "None";
    public string LegacyRedisKey { get; init; } = string.Empty;
    public string LegacyKeyStoragePath { get; init; } = string.Empty;
    public string KeyEncryptionCertificatePath { get; init; } = string.Empty;
    public string KeyEncryptionCertificatePassword { get; init; } = string.Empty;

    public bool HasValidLegacySource()
    {
        var hasRedisKey = !string.IsNullOrWhiteSpace(LegacyRedisKey);
        var hasFilePath = !string.IsNullOrWhiteSpace(LegacyKeyStoragePath);
        return LegacyKeyStore switch
        {
            "None" => !hasRedisKey && !hasFilePath,
            "Redis" => hasRedisKey && !hasFilePath,
            "FileSystem" => hasFilePath && !hasRedisKey,
            _ => false
        };
    }
}
