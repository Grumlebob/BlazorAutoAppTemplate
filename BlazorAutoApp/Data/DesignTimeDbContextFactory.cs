using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Npgsql;

namespace BlazorAutoApp.Data;

public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
{
    public AppDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<AppDbContext>();

        // Prefer environment variable first, then default.
        var conn = ConfigurePostgresConnectionString(
            Environment.GetEnvironmentVariable("DefaultConnection")
            ?? "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres");

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
