using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Data;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using Respawn;
using Testcontainers.PostgreSql;
using Xunit;

namespace BlazorAutoApp.Test.TestingSetup;

public class WebAppFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    private const int MaxWaitTimeMinutes = 5;
    private const string RyukImageEnvironmentVariable = "TESTCONTAINERS_RYUK_CONTAINER_IMAGE";
    private const string RyukImage = "testcontainers/ryuk:0.12.0";
    private const string ConnectionStringEnvironmentVariable = "ConnectionStrings__DefaultConnection";
    private const string RedisConfigurationEnvironmentVariable = "Redis__Configuration";
    private const string StartupMigrationsEnvironmentVariable = "Database__RunMigrationsAtStartup";
    private const string ForwardedHeaderKnownNetworkV4EnvironmentVariable = "ForwardedHeaders__KnownNetworks__0";
    private const string ForwardedHeaderKnownNetworkV6EnvironmentVariable = "ForwardedHeaders__KnownNetworks__1";
    private const string ApiRateLimitEnvironmentVariable = "RateLimiting__Api__PermitLimit";
    private const string AuthenticationRateLimitEnvironmentVariable = "RateLimiting__Authentication__PermitLimit";
    static WebAppFactory()
    {
        if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(RyukImageEnvironmentVariable)))
        {
            Environment.SetEnvironmentVariable(RyukImageEnvironmentVariable, RyukImage);
        }
    }

    private readonly PostgreSqlContainer _dbContainer = new PostgreSqlBuilder("postgres:16.14-alpine3.23")
        .Build();

    private string _connectionString = default!;
    private Respawner _respawner = default!;
    private EnvironmentVariableScope? _environmentOverrides;
    public HttpClient HttpClient { get; private set; } = default!;

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration((_, configuration) =>
        {
            configuration.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["ConnectionStrings:DefaultConnection"] = _connectionString,
                ["Redis:Configuration"] = "CHANGE_ME",
                ["Database:RunMigrationsAtStartup"] = "false",
                ["ForwardedHeaders:KnownNetworks:0"] = "0.0.0.0/0",
                ["ForwardedHeaders:KnownNetworks:1"] = "::/0",
                ["RateLimiting:Api:PermitLimit"] = "60",
                ["RateLimiting:Authentication:PermitLimit"] = "20"
            });
        });
    }

    public async Task ResetDatabaseAsync()
    {
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        await _respawner.ResetAsync(connection);

        using var scope = Services.CreateScope();
        var cache = scope.ServiceProvider.GetService<Microsoft.Extensions.Caching.Hybrid.HybridCache>();
        if (cache is not null)
        {
            try { await cache.RemoveAsync("movies:list"); } catch { }
        }
    }

    public async ValueTask InitializeAsync()
    {
        await _dbContainer.StartAsync();

        _connectionString = _dbContainer.GetConnectionString();
        _environmentOverrides = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            [ConnectionStringEnvironmentVariable] = _connectionString,
            [RedisConfigurationEnvironmentVariable] = "CHANGE_ME",
            [StartupMigrationsEnvironmentVariable] = "false",
            [ForwardedHeaderKnownNetworkV4EnvironmentVariable] = "0.0.0.0/0",
            [ForwardedHeaderKnownNetworkV6EnvironmentVariable] = "::/0",
            [ApiRateLimitEnvironmentVariable] = "60",
            [AuthenticationRateLimitEnvironmentVariable] = "20"
        });

        HttpClient = CreateClient();
        HttpClient.Timeout = TimeSpan.FromMinutes(MaxWaitTimeMinutes);

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
            new RespawnerOptions
            {
                DbAdapter = DbAdapter.Postgres,
                SchemasToInclude = ["public"]
            });
    }

    public new async ValueTask DisposeAsync()
    {
        await _dbContainer.StopAsync();
        _environmentOverrides?.Dispose();
        _environmentOverrides = null;
    }
}
