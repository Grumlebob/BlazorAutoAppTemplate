using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Runtime.ExceptionServices;
using System.Threading;
using System.Threading.Tasks;
using BlazorAutoApp.Features.Books.Caching;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.TestHost;
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
    // Integration tests share one client IP; generous defaults keep unrelated tests
    // from tripping limits. Rate-limit tests set low limits explicitly.
    private const int DefaultGlobalPermitLimit = 10_000;
    private const int DefaultApiPermitLimit = 1_000;
    private const int DefaultAuthenticationPermitLimit = 1_000;
    private const string RyukImageEnvironmentVariable = "TESTCONTAINERS_RYUK_CONTAINER_IMAGE";
    private const string ConnectionStringEnvironmentVariable = "ConnectionStrings__DefaultConnection";
    private const string RedisConfigurationEnvironmentVariable = "Redis__Configuration";
    private const string RedisAllowMissingEnvironmentVariable = "Redis__AllowMissing";
    private const string AppNameEnvironmentVariable = "App__Name";
    private const string CacheInvalidationEnabledEnvironmentVariable = "Cache__Invalidation__Enabled";
    private const string CacheInvalidationNodeIdEnvironmentVariable = "Cache__Invalidation__NodeId";
    private const string CacheBooksLocalListTtlEnvironmentVariable = "Cache__Books__LocalListTtlSeconds";
    private const string CacheBooksLocalItemTtlEnvironmentVariable = "Cache__Books__LocalItemTtlSeconds";
    private const string CacheBooksDisableLocalEnvironmentVariable = "Cache__Books__DisableLocalCache";
    private const string StartupMigrationsEnvironmentVariable = "Database__RunMigrationsAtStartup";
    private const string ForwardedHeaderKnownNetworkV4EnvironmentVariable = "ForwardedHeaders__KnownNetworks__0";
    private const string ForwardedHeaderKnownNetworkV6EnvironmentVariable = "ForwardedHeaders__KnownNetworks__1";
    private const string GlobalRateLimitEnvironmentVariable = "RateLimiting__Global__PermitLimit";
    private const string ApiRateLimitEnvironmentVariable = "RateLimiting__Api__PermitLimit";
    private const string AuthenticationRateLimitEnvironmentVariable = "RateLimiting__Authentication__PermitLimit";
    private const string LocalAccountsEnabledEnvironmentVariable = "LocalAccounts__Enabled";
    private const string AuthorBooksSeedAtStartupEnvironmentVariable = "AuthorBooks__SeedAtStartup";
    private const string OpenTelemetryEnabledEnvironmentVariable = "Observability__OpenTelemetry__Enabled";
    private const string OpenTelemetryEndpointEnvironmentVariable = "Observability__OpenTelemetry__Endpoint";
    static WebAppFactory()
    {
        if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(RyukImageEnvironmentVariable)))
        {
            Environment.SetEnvironmentVariable(RyukImageEnvironmentVariable, TestContainerImages.Ryuk);
        }
    }

    private readonly WebAppFactoryOptions _options;
    private readonly PostgreSqlContainer? _dbContainer;

    private string _connectionString = default!;
    private string _redisConnectionString = "CHANGE_ME";
    private Respawner? _respawner;
    private EnvironmentVariableScope? _environmentOverrides;
    private int _disposed;
    public HttpClient HttpClient { get; private set; } = default!;
    internal string ConnectionString => _connectionString;

    public WebAppFactory()
        : this(new WebAppFactoryOptions())
    {
    }

    internal WebAppFactory(WebAppFactoryOptions options)
    {
        _options = options;
        if (string.IsNullOrWhiteSpace(options.PostgresConnectionString))
        {
            _dbContainer = new PostgreSqlBuilder(TestContainerImages.PostgreSql)
                .WithCreateParameterModifier(TestContainerImages.ConfigurePostgreSqlData)
                .WithLabel(TestContainerLabels.For("web-app-factory-postgres"))
                .WithCleanUp(true)
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
                ["Database:RunMigrationsAtStartup"] = _options.RunStartupMigrations.ToString(),
                ["AuthorBooks:SeedAtStartup"] = _options.AuthorBooksSeedAtStartup.ToString(),
                ["LocalAccounts:Enabled"] = "false",
                ["ForwardedHeaders:KnownNetworks:0"] = "0.0.0.0/0",
                ["ForwardedHeaders:KnownNetworks:1"] = "::/0",
                ["RateLimiting:Global:PermitLimit"] = (_options.GlobalRateLimitPermitLimit ?? DefaultGlobalPermitLimit).ToString(),
                ["RateLimiting:Api:PermitLimit"] = (_options.ApiRateLimitPermitLimit ?? DefaultApiPermitLimit).ToString(),
                ["RateLimiting:Authentication:PermitLimit"] = (_options.AuthenticationRateLimitPermitLimit ?? DefaultAuthenticationPermitLimit).ToString(),
                ["Observability:OpenTelemetry:Enabled"] = (_options.OpenTelemetryEnabled ?? false).ToString(),
                ["Observability:OpenTelemetry:Endpoint"] = _options.OpenTelemetryEndpoint ?? "http://127.0.0.1:4317",
                ["Cache:Invalidation:Enabled"] = (_options.CacheInvalidationEnabled ?? !string.Equals(_redisConnectionString, "CHANGE_ME", StringComparison.Ordinal)).ToString()
            };

            if (!string.IsNullOrWhiteSpace(_options.CacheInvalidationNodeId))
            {
                values["Cache:Invalidation:NodeId"] = _options.CacheInvalidationNodeId;
            }

            foreach (var (key, value) in _options.ConfigurationOverrides)
            {
                values[key] = value;
            }

            if (_options.LocalListTtlSeconds is not null)
            {
                values["Cache:Books:LocalListTtlSeconds"] = _options.LocalListTtlSeconds.Value.ToString();
            }

            if (_options.LocalItemTtlSeconds is not null)
            {
                values["Cache:Books:LocalItemTtlSeconds"] = _options.LocalItemTtlSeconds.Value.ToString();
            }

            if (_options.DisableLocalCache is not null)
            {
                values["Cache:Books:DisableLocalCache"] = _options.DisableLocalCache.Value.ToString();
            }

            configuration.AddInMemoryCollection(values);
        });

        builder.ConfigureTestServices(services =>
        {
            services.AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = TestAuthenticationHandler.SchemeName;
                options.DefaultChallengeScheme = _options.UseIdentityCookieChallenge
                    ? IdentityConstants.ApplicationScheme
                    : TestAuthenticationHandler.SchemeName;
            })
            .AddScheme<AuthenticationSchemeOptions, TestAuthenticationHandler>(
                TestAuthenticationHandler.SchemeName,
                _ => { });

            _options.ConfigureTestServices?.Invoke(services);
        });
    }

    public async Task ResetDatabaseAsync()
    {
        if (_respawner is null)
        {
            throw new InvalidOperationException(
                "Database respawner was not initialized. Set WebAppFactoryOptions.InitializeDatabaseRespawner to true before using ResetDatabaseAsync.");
        }

        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        await _respawner.ResetAsync(connection);

        using var scope = Services.CreateScope();
        var cache = scope.ServiceProvider.GetService<Microsoft.Extensions.Caching.Hybrid.HybridCache>();
        if (cache is not null)
        {
            try { await cache.RemoveByTagAsync(BooksCacheKeys.AllTag); } catch { }
            try { await cache.RemoveByTagAsync(AuthorBooksCacheKeys.AllTag); } catch { }
        }
    }

    public HttpClient CreateAuthenticatedClient(string userName = "integration-user@example.test")
    {
        var client = CreateClient();
        client.Timeout = TimeSpan.FromMinutes(MaxWaitTimeMinutes);
        client.DefaultRequestHeaders.Add(TestAuthenticationHandler.UserHeader, userName);
        return client;
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
            // Minimal hosting reads some configuration before WebApplicationFactory
            // configuration callbacks can replace it. Keep these overrides scoped
            // and test parallelization disabled while this startup-time coupling exists.
            var redisAllowMissing = string.IsNullOrWhiteSpace(_options.RedisConnectionString);
            _environmentOverrides = new EnvironmentVariableScope(new Dictionary<string, string?>
            {
                [AppNameEnvironmentVariable] = _options.AppName ?? "BlazorAutoApp",
                [ConnectionStringEnvironmentVariable] = _connectionString,
                [RedisConfigurationEnvironmentVariable] = _redisConnectionString,
                [RedisAllowMissingEnvironmentVariable] = redisAllowMissing.ToString(),
                [CacheInvalidationEnabledEnvironmentVariable] = (_options.CacheInvalidationEnabled ?? !string.Equals(_redisConnectionString, "CHANGE_ME", StringComparison.Ordinal)).ToString(),
                [CacheInvalidationNodeIdEnvironmentVariable] = _options.CacheInvalidationNodeId,
                [CacheBooksLocalListTtlEnvironmentVariable] = _options.LocalListTtlSeconds?.ToString(),
                [CacheBooksLocalItemTtlEnvironmentVariable] = _options.LocalItemTtlSeconds?.ToString(),
                [CacheBooksDisableLocalEnvironmentVariable] = _options.DisableLocalCache?.ToString(),
                [StartupMigrationsEnvironmentVariable] = _options.RunStartupMigrations.ToString(),
                [AuthorBooksSeedAtStartupEnvironmentVariable] = _options.AuthorBooksSeedAtStartup.ToString(),
                [LocalAccountsEnabledEnvironmentVariable] = "false",
                [ForwardedHeaderKnownNetworkV4EnvironmentVariable] = "0.0.0.0/0",
                [ForwardedHeaderKnownNetworkV6EnvironmentVariable] = "::/0",
                [GlobalRateLimitEnvironmentVariable] = (_options.GlobalRateLimitPermitLimit ?? DefaultGlobalPermitLimit).ToString(),
                [ApiRateLimitEnvironmentVariable] = (_options.ApiRateLimitPermitLimit ?? DefaultApiPermitLimit).ToString(),
                [AuthenticationRateLimitEnvironmentVariable] = (_options.AuthenticationRateLimitPermitLimit ?? DefaultAuthenticationPermitLimit).ToString(),
                [OpenTelemetryEnabledEnvironmentVariable] = (_options.OpenTelemetryEnabled ?? false).ToString(),
                [OpenTelemetryEndpointEnvironmentVariable] = _options.OpenTelemetryEndpoint ?? "http://127.0.0.1:4317"
            });
        }

        HttpClient = CreateClient();
        HttpClient.Timeout = TimeSpan.FromMinutes(MaxWaitTimeMinutes);

        using var scope = Services.CreateScope();
        var services = scope.ServiceProvider;
        var dbFactory = services.GetRequiredService<IDbContextFactory<AppDbContext>>();
        if (_options.RunMigrations && !_options.RunStartupMigrations)
        {
            await using var context = await dbFactory.CreateDbContextAsync();
            await context.Database.MigrateAsync();
        }

        if (_options.InitializeDatabaseRespawner)
        {
            await InitializeRespawner();
        }
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
        if (Interlocked.Exchange(ref _disposed, 1) != 0)
        {
            return;
        }

        List<Exception> failures = [];
        try
        {
            HttpClient?.Dispose();
            await base.DisposeAsync();
        }
        catch (Exception exception)
        {
            failures.Add(exception);
        }

        try
        {
            // DisposeAsync removes the container; StopAsync left it on the runner.
            if (_dbContainer is not null)
            {
                await _dbContainer.DisposeAsync();
            }
        }
        catch (Exception exception)
        {
            failures.Add(exception);
        }
        finally
        {
            try
            {
                _environmentOverrides?.Dispose();
            }
            catch (Exception exception)
            {
                failures.Add(exception);
            }

            _environmentOverrides = null;
        }

        if (failures.Count == 1)
        {
            ExceptionDispatchInfo.Capture(failures[0]).Throw();
        }

        if (failures.Count > 1)
        {
            throw new AggregateException("One or more integration resources failed to dispose.", failures);
        }
    }
}
