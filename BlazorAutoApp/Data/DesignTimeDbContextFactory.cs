using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace BlazorAutoApp.Data;

public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
{
    public AppDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<AppDbContext>();

        // Prefer environment variable first, then default.
        var conn = Environment.GetEnvironmentVariable("DefaultConnection")
                   ?? "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres";

        optionsBuilder.UseNpgsql(conn);
        return new AppDbContext(optionsBuilder.Options);
    }
}

