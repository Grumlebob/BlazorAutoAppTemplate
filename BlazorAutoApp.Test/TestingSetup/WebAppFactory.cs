using System;
using System.Data.Common;
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

    private readonly PostgreSqlContainer _dbContainer = new PostgreSqlBuilder()
        .WithImage("postgres:latest")
        .Build();

    //Default! cause we are not initializing it here, but in the InitializeAsync method
    private DbConnection _dbConnection = default!;
    private Respawner _respawner = default!;
    public HttpClient HttpClient { get; private set; } = default!;

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        //Setup dependency injection for this test application
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

            //Setup our new Context connection to our docker postgres container
            services.AddDbContext<AppDbContext>(
                options =>
                {
                    options.UseNpgsql(_dbContainer.GetConnectionString());
                }
            );

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
        await _respawner.ResetAsync(_dbConnection);
        // Clear known cache keys used by features to avoid stale results between tests
        using var scope = Services.CreateScope();
        var cache = scope.ServiceProvider.GetService<Microsoft.Extensions.Caching.Hybrid.HybridCache>();
        if (cache is not null)
        {
            try { await cache.RemoveAsync("movies:list"); } catch { /* ignore */ }
        }
    }

    public async Task InitializeAsync()
    {
        await _dbContainer.StartAsync();

        _dbConnection = new NpgsqlConnection(_dbContainer.GetConnectionString());

        HttpClient = CreateClient();
        //Seeding data can take a long time, so we set a longer timeout
        HttpClient.Timeout = TimeSpan.FromMinutes(MaxWaitTimeMinutes);

        //THIS IS WHERE YOU CAN ADD SEED DATA
        using var scope = Services.CreateScope();
        var services = scope.ServiceProvider;
        var context = services.GetRequiredService<AppDbContext>();
        
        await context.Database.MigrateAsync();
        await InitializeRespawner();
    }

    private async Task InitializeRespawner()
    {
        await _dbConnection.OpenAsync();
        _respawner = await Respawner.CreateAsync(
            _dbConnection,
            new RespawnerOptions()
            {
                DbAdapter = DbAdapter.Postgres,
                SchemasToInclude = new[] { "public" }
            }
        );
    }

    //"New": to tell compiler that this is a new DisposeAsync method
    public new Task DisposeAsync()
    {
        return _dbContainer.StopAsync();
    }
}
