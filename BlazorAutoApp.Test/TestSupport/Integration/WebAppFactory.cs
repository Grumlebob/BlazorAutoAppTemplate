using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Features.Movies.Caching;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using Respawn;
using Testcontainers.PostgreSql;
using Xunit;

namespace BlazorAutoApp.Test.TestSupport.Integration;

public class WebAppFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    private const int MaxWaitTimeMinutes = 5;
    private const string RyukImageEnvironmentVariable = "TESTCONTAINERS_RYUK_CONTAINER_IMAGE";
    private const string RyukImage = "testcontainers/ryuk:0.12.0";
    private const string ConnectionStringEnvironmentVariable = "ConnectionStrings__DefaultConnection";
    private const string RedisConfigurationEnvironmentVariable = "Redis__Configuration";
    private const string RedisAllowMissingEnvironmentVariable = "Redis__AllowMissing";
    private const string AppNameEnvironmentVariable = "App__Name";
    private const string CacheInvalidationEnabledEnvironmentVariable = "Cache__Invalidation__Enabled";
    private const string CacheInvalidationNodeIdEnvironmentVariable = "Cache__Invalidation__NodeId";
    private const string CacheMoviesLocalListTtlEnvironmentVariable = "Cache__Movies__LocalListTtlSeconds";
    private const string CacheMoviesLocalItemTtlEnvironmentVariable = "Cache__Movies__LocalItemTtlSeconds";
    private const string CacheMoviesDisableLocalEnvironmentVariable = "Cache__Movies__DisableLocalCache";
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

    private readonly WebAppFactoryOptions _options;
    private readonly PostgreSqlContainer? _dbContainer;

    private string _connectionString = default!;
    private string _redisConnectionString = "CHANGE_ME";
    private Respawner _respawner = default!;
    private EnvironmentVariableScope? _environmentOverrides;
    public HttpClient HttpClient { get; private set; } = default!;

    public WebAppFactory()
        : this(new WebAppFactoryOptions())
    {
    }

    internal WebAppFactory(WebAppFactoryOptions options)
    {
        _options = options;
        if (string.IsNullOrWhiteSpace(options.PostgresConnectionString))
        {
            _dbContainer = new PostgreSqlBuilder("postgres:16.14-alpine3.23")
                .Build();
        }
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        if (!string.IsNullOrWhiteSpace(_options.EnvironmentName))
        {
            builder.UseEnvironment(_options.EnvironmentName);
        }

        builder.ConfigureAppConfiguration((_, configuration) =>
        {
            var redisAllowMissing = string.IsNullOrWhiteSpace(_options.RedisConnectionString);
            var values = new Dictionary<string, string?>
            {
                ["App:Name"] = _options.AppName ?? "BlazorAutoApp",
                ["ConnectionStrings:DefaultConnection"] = _connectionString,
                ["Redis:Configuration"] = _redisConnectionString,
                ["Redis:AllowMissing"] = redisAllowMissing.ToString(),
                ["Database:RunMigrationsAtStartup"] = "false",
                ["ForwardedHeaders:KnownNetworks:0"] = "0.0.0.0/0",
                ["ForwardedHeaders:KnownNetworks:1"] = "::/0",
                ["RateLimiting:Api:PermitLimit"] = "60",
                ["RateLimiting:Authentication:PermitLimit"] = "20",
                ["Cache:Invalidation:Enabled"] = (_options.CacheInvalidationEnabled ?? !string.Equals(_redisConnectionString, "CHANGE_ME", StringComparison.Ordinal)).ToString()
            };

            if (!string.IsNullOrWhiteSpace(_options.CacheInvalidationNodeId))
            {
                values["Cache:Invalidation:NodeId"] = _options.CacheInvalidationNodeId;
            }

            if (_options.LocalListTtlSeconds is not null)
            {
                values["Cache:Movies:LocalListTtlSeconds"] = _options.LocalListTtlSeconds.Value.ToString();
            }

            if (_options.LocalItemTtlSeconds is not null)
            {
                values["Cache:Movies:LocalItemTtlSeconds"] = _options.LocalItemTtlSeconds.Value.ToString();
            }

            if (_options.DisableLocalCache is not null)
            {
                values["Cache:Movies:DisableLocalCache"] = _options.DisableLocalCache.Value.ToString();
            }

            configuration.AddInMemoryCollection(values);
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
            try { await cache.RemoveByTagAsync(MoviesCacheKeys.AllTag); } catch { }
        }
    }

    public async ValueTask InitializeAsync()
    {
        if (_dbContainer is not null)
        {
            await _dbContainer.StartAsync();
            _connectionString = _dbContainer.GetConnectionString();
        }
        else
        {
            _connectionString = _options.PostgresConnectionString!;
        }

        _redisConnectionString = string.IsNullOrWhiteSpace(_options.RedisConnectionString)
            ? "CHANGE_ME"
            : _options.RedisConnectionString;

        if (_options.UseProcessEnvironmentOverrides)
        {
            var redisAllowMissing = string.IsNullOrWhiteSpace(_options.RedisConnectionString);
            _environmentOverrides = new EnvironmentVariableScope(new Dictionary<string, string?>
            {
                [AppNameEnvironmentVariable] = _options.AppName ?? "BlazorAutoApp",
                [ConnectionStringEnvironmentVariable] = _connectionString,
                [RedisConfigurationEnvironmentVariable] = _redisConnectionString,
                [RedisAllowMissingEnvironmentVariable] = redisAllowMissing.ToString(),
                [CacheInvalidationEnabledEnvironmentVariable] = (_options.CacheInvalidationEnabled ?? !string.Equals(_redisConnectionString, "CHANGE_ME", StringComparison.Ordinal)).ToString(),
                [CacheInvalidationNodeIdEnvironmentVariable] = _options.CacheInvalidationNodeId,
                [CacheMoviesLocalListTtlEnvironmentVariable] = _options.LocalListTtlSeconds?.ToString(),
                [CacheMoviesLocalItemTtlEnvironmentVariable] = _options.LocalItemTtlSeconds?.ToString(),
                [CacheMoviesDisableLocalEnvironmentVariable] = _options.DisableLocalCache?.ToString(),
                [StartupMigrationsEnvironmentVariable] = "false",
                [ForwardedHeaderKnownNetworkV4EnvironmentVariable] = "0.0.0.0/0",
                [ForwardedHeaderKnownNetworkV6EnvironmentVariable] = "::/0",
                [ApiRateLimitEnvironmentVariable] = "60",
                [AuthenticationRateLimitEnvironmentVariable] = "20"
            });
        }

        HttpClient = CreateClient();
        HttpClient.Timeout = TimeSpan.FromMinutes(MaxWaitTimeMinutes);

        using var scope = Services.CreateScope();
        var services = scope.ServiceProvider;
        var dbFactory = services.GetRequiredService<IDbContextFactory<AppDbContext>>();
        if (_options.RunMigrations)
        {
            await using var context = await dbFactory.CreateDbContextAsync();
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
                SchemasToInclude = ["public"],
                TablesToIgnore = [new Respawn.Graph.Table("__EFMigrationsHistory")]
            });
    }

    public new async ValueTask DisposeAsync()
    {
        HttpClient?.Dispose();
        await base.DisposeAsync();

        if (_dbContainer is not null)
        {
            await _dbContainer.StopAsync();
        }

        _environmentOverrides?.Dispose();
        _environmentOverrides = null;
    }
}
