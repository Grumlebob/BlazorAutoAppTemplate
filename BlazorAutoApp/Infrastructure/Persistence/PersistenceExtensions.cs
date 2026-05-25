using Microsoft.Extensions.Diagnostics.HealthChecks;
using Npgsql;

namespace BlazorAutoApp.Infrastructure.Persistence;

internal static class PersistenceExtensions
{
    public static IServiceCollection AddAppPersistence(
        this IServiceCollection services,
        IConfiguration configuration,
        IHealthChecksBuilder healthChecks)
    {
        var hasConnectionString = !string.IsNullOrWhiteSpace(configuration.GetConnectionString("DefaultConnection"));
        services.AddOptions<DatabaseOptions>()
            .Bind(configuration.GetSection(DatabaseOptions.SectionName))
            .Validate(options => hasConnectionString || options.HasRequiredValues(), "Either ConnectionStrings:DefaultConnection or complete Database:* settings must be configured.")
            .Validate(options => options.Port > 0 && options.Port <= 65535, "Database:Port must be between 1 and 65535.")
            .ValidateOnStart();

        var connectionString = BuildConnectionString(configuration);

        void ConfigureDbContext(DbContextOptionsBuilder options)
        {
            options.UseNpgsql(connectionString);
        }

        services.AddDbContextFactory<AppDbContext>(ConfigureDbContext);
        services.AddScoped(sp => sp.GetRequiredService<IDbContextFactory<AppDbContext>>().CreateDbContext());
        healthChecks.AddCheck<PostgresHealthCheck>("postgres", tags: ["ready"]);

        return services;
    }

    public static async Task ApplyAppMigrationsAsync(this WebApplication app)
    {
        var runMigrations = app.Configuration.GetValue(
            "Database:RunMigrationsAtStartup",
            app.Environment.IsDevelopment());

        if (!runMigrations)
        {
            return;
        }

        using var scope = app.Services.CreateScope();
        var dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
        var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();

        try
        {
            await using var db = await dbFactory.CreateDbContextAsync();
            var pending = (await db.Database.GetPendingMigrationsAsync()).ToList();
            if (pending.Count > 0)
            {
                logger.LogInformation("Applying {Count} EF migrations: {Migrations}", pending.Count, string.Join(", ", pending));
            }
            else
            {
                logger.LogInformation("No EF migrations pending");
            }

            await db.Database.MigrateAsync();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "EF migrations failed at startup");
            throw;
        }
    }

    private static string BuildConnectionString(IConfiguration configuration)
    {
        var configured = configuration.GetConnectionString("DefaultConnection");
        var connectionString = !string.IsNullOrWhiteSpace(configured)
            ? configured
            : configuration.GetRequiredSection(DatabaseOptions.SectionName).Get<DatabaseOptions>()!.ToConnectionString();

        var builder = new NpgsqlConnectionStringBuilder(connectionString);
        if (!builder.ContainsKey("GSS Encryption Mode"))
        {
            builder.GssEncryptionMode = GssEncryptionMode.Disable;
        }

        return builder.ConnectionString;
    }
}
