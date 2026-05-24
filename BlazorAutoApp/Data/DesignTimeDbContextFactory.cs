using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;

namespace BlazorAutoApp.Data;

public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
{
    public AppDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<AppDbContext>();

        var conn = ConfigurePostgresConnectionString(
            Environment.GetEnvironmentVariable("ConnectionStrings__DefaultConnection")
            ?? "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres");

        optionsBuilder.UseApplicationServiceProvider(new ServiceCollection()
            .Configure<IdentityOptions>(options => options.Stores.SchemaVersion = IdentitySchemaVersions.Version3)
            .BuildServiceProvider());
        optionsBuilder.UseNpgsql(conn);
        return new AppDbContext(optionsBuilder.Options);
    }

    private static string ConfigurePostgresConnectionString(string connectionString)
    {
        var connectionBuilder = new NpgsqlConnectionStringBuilder(connectionString);
        if (!connectionBuilder.ContainsKey("GSS Encryption Mode"))
        {
            connectionBuilder.GssEncryptionMode = GssEncryptionMode.Disable;
        }

        return connectionBuilder.ConnectionString;
    }
}
