using System;
using System.Threading.Tasks;
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;
using Testcontainers.PostgreSql;
using Xunit;

namespace BlazorAutoApp.Test.TestSupport.Integration;

public sealed class SharedIntegrationEnvironment : IAsyncLifetime
{
    private const int RedisPort = 6379;
    private const string RedisPassword = "redis-test-password";

    private readonly PostgreSqlContainer _dbContainer = new PostgreSqlBuilder(TestContainerImages.PostgreSql)
        .Build();

    private readonly IContainer _redisContainer = new ContainerBuilder(TestContainerImages.Redis)
        .WithPortBinding(RedisPort, true)
        .WithCommand("redis-server", "--requirepass", RedisPassword, "--save", "", "--appendonly", "no")
        .WithWaitStrategy(Wait.ForUnixContainer().UntilCommandIsCompleted("redis-cli", "-a", RedisPassword, "ping"))
        .Build();

    public string AppName { get; } = $"BlazorAutoApp.CrossNodeTests.{Guid.NewGuid():N}";

    public string EnvironmentName => "CrossNodeTests";

    public string PostgresConnectionString => _dbContainer.GetConnectionString();

    public string RedisConnectionString =>
        $"127.0.0.1:{_redisContainer.GetMappedPublicPort(RedisPort)},password={RedisPassword},abortConnect=false";

    public async ValueTask InitializeAsync()
    {
        await _dbContainer.StartAsync();
        await _redisContainer.StartAsync();
    }

    public async ValueTask DisposeAsync()
    {
        await _redisContainer.StopAsync();
        await _dbContainer.StopAsync();
    }

    public WebAppFactory CreateFactory(
        string nodeId,
        bool runMigrations,
        bool cacheInvalidationEnabled = true,
        int? localListTtlSeconds = null,
        int? localItemTtlSeconds = null,
        bool? disableLocalCache = null) =>
        new(new WebAppFactoryOptions
        {
            PostgresConnectionString = PostgresConnectionString,
            RedisConnectionString = RedisConnectionString,
            CacheInvalidationNodeId = nodeId,
            CacheInvalidationEnabled = cacheInvalidationEnabled,
            AppName = AppName,
            EnvironmentName = EnvironmentName,
            RunMigrations = runMigrations,
            UseProcessEnvironmentOverrides = true,
            LocalListTtlSeconds = localListTtlSeconds,
            LocalItemTtlSeconds = localItemTtlSeconds,
            DisableLocalCache = disableLocalCache
        });
}
