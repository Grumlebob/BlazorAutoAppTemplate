using System;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Data;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using Respawn;
using Testcontainers.PostgreSql;
using Xunit;

namespace BlazorAutoApp.Test.TestingSetup;

//WebApplicationFactory is a class that allows us to create a test server for our application in memory, but setup with real dependencies.
public class WebAppFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    private const int MaxWaitTimeMinutes = 5;
    private const string RyukImageEnvironmentVariable = "TESTCONTAINERS_RYUK_CONTAINER_IMAGE";
    private const string RyukImage = "testcontainers/ryuk:0.12.0";

    static WebAppFactory()
    {
        if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(RyukImageEnvironmentVariable)))
        {
            Environment.SetEnvironmentVariable(RyukImageEnvironmentVariable, RyukImage);
        }
    }

    private readonly PostgreSqlContainer _dbContainer = new PostgreSqlBuilder("postgres:16-alpine")
        .Build();

    //Default! cause we are not initializing it here, but in the InitializeAsync method
    private string _connectionString = default!;
    private Respawner _respawner = default!;
    public HttpClient HttpClient { get; private set; } = default!;

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        //Setup dependency injection for this test application
        // Provide required env vars so Program.cs doesn't throw GetEnvVar() exceptions
        // Database envs are ignored in tests (DI overridden), but set to avoid early checks
        Environment.SetEnvironmentVariable("Database__Host", "localhost");
        Environment.SetEnvironmentVariable("Database__Port", "5432");
        Environment.SetEnvironmentVariable("Database__Name", "testdb");
        Environment.SetEnvironmentVariable("Database__Username", "postgres");
        Environment.SetEnvironmentVariable("Database__Password", "postgres");
        // Tests replace distributed caching with memory; do not require a host Redis instance.
        Environment.SetEnvironmentVariable("Redis__Configuration", "CHANGE_ME");
        builder.ConfigureTestServices(services =>
        {
            //Remove the existing KinoContext from the services
            var descriptor = services.SingleOrDefault(d =>
                d.ServiceType == typeof(DbContextOptions<AppDbContext>)
            );

            if (descriptor != null)
            {
                services.Remove(descriptor);
            }

            // Remove any existing factory to avoid lifetime mismatches
            var factoryDesc = services.SingleOrDefault(d => d.ServiceType == typeof(IDbContextFactory<AppDbContext>));
            if (factoryDesc != null)
            {
                services.Remove(factoryDesc);
            }

            // Register factory (factory-only approach)
            services.AddDbContextFactory<AppDbContext>(options =>
            {
                options.UseNpgsql(_dbContainer.GetConnectionString());
            });

            // Ensure HybridCache uses in-memory distributed cache in tests (no Redis)
            var dcDescs = services.Where(d => d.ServiceType == typeof(Microsoft.Extensions.Caching.Distributed.IDistributedCache)).ToList();
            foreach (var dc in dcDescs)
            {
                services.Remove(dc);
            }
            services.AddDistributedMemoryCache();
            services.AddHybridCache();
        });
    }

    public async Task ResetDatabaseAsync()
    {
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        await _respawner.ResetAsync(connection);
        // Clear known cache keys used by features to avoid stale results between tests
        using var scope = Services.CreateScope();
        var cache = scope.ServiceProvider.GetService<Microsoft.Extensions.Caching.Hybrid.HybridCache>();
        if (cache is not null)
        {
            try { await cache.RemoveAsync("movies:list"); } catch { /* ignore */ }
        }
    }

    public async ValueTask InitializeAsync()
    {
        await _dbContainer.StartAsync();

        _connectionString = _dbContainer.GetConnectionString();

        HttpClient = CreateClient();
        //Seeding data can take a long time, so we set a longer timeout
        HttpClient.Timeout = TimeSpan.FromMinutes(MaxWaitTimeMinutes);

        //THIS IS WHERE YOU CAN ADD SEED DATA
        using var scope = Services.CreateScope();
        var services = scope.ServiceProvider;
        var dbFactory = services.GetRequiredService<IDbContextFactory<AppDbContext>>();
        await using (var context = await dbFactory.CreateDbContextAsync())
        {
            await context.Database.MigrateAsync();
        }
        await InitializeRespawner();
    }

    private async Task InitializeRespawner()
    {
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        _respawner = await Respawner.CreateAsync(
            connection,
            new RespawnerOptions()
            {
                DbAdapter = DbAdapter.Postgres,
                SchemasToInclude = ["public"]
            }
        );
    }

    //"New": to tell compiler that this is a new DisposeAsync method
    public new async ValueTask DisposeAsync()
    {
        await _dbContainer.StopAsync();
    }
}
