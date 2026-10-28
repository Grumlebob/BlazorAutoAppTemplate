using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Threading.Tasks;
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;
using Microsoft.Extensions.DependencyInjection;
using Testcontainers.PostgreSql;
using Xunit;

namespace GrumPlates.Test.TestSupport.Integration;

public sealed class SharedIntegrationEnvironment : IAsyncLifetime
{
    private const int RedisPort = 6379;
    private readonly string _redisPassword = RandomNumberGenerator.GetHexString(48);

    private readonly PostgreSqlContainer _dbContainer = TestContainerImages.CreatePostgreSqlFixture()
        .WithLabel(TestContainerLabels.For("shared-integration-postgres"))
        .WithCleanUp(true)
        .Build();

    private readonly IContainer _redisContainer;

    public SharedIntegrationEnvironment()
    {
        _redisContainer = new ContainerBuilder(TestContainerImages.Redis)
            .WithCreateParameterModifier(TestContainerImages.ConfigureRedisData)
            .WithPortBinding(RedisPort, true)
            .WithEnvironment("REDISCLI_AUTH", _redisPassword)
            .WithCommand("redis-server", "--requirepass", _redisPassword, "--save", "", "--appendonly", "no")
            .WithWaitStrategy(Wait.ForUnixContainer().UntilCommandIsCompleted("redis-cli", "ping")
                .UntilExternalTcpPortIsAvailable(RedisPort))
            .WithLabel(TestContainerLabels.For("shared-integration-redis"))
            .WithCleanUp(true)
            .Build();
    }

    public string AppName { get; } = $"GrumPlates.CrossNodeTests.{Guid.NewGuid():N}";

    public string EnvironmentName => "CrossNodeTests";

    public string PostgresConnectionString => _dbContainer.GetConnectionString();

    public string PostgresContainerId => _dbContainer.Id;

    public string RedisConnectionString =>
        $"127.0.0.1:{_redisContainer.GetMappedPublicPort(RedisPort)},password={_redisPassword},abortConnect=false";

    public async ValueTask InitializeAsync()
    {
        await _dbContainer.StartAsync();
        await _redisContainer.StartAsync();
    }

    // DisposeAsync removes the containers; StopAsync left them behind on the runner.
    public async ValueTask DisposeAsync()
    {
        List<Exception> failures = [];
        try { await _redisContainer.DisposeAsync(); } catch (Exception exception) { failures.Add(exception); }
        try { await _dbContainer.DisposeAsync(); } catch (Exception exception) { failures.Add(exception); }
        if (failures.Count > 0)
        {
            throw new AggregateException("One or more shared integration resources failed to dispose.", failures);
        }
    }

    public WebAppFactory CreateFactory(
        string nodeId,
        bool runMigrationsAtStartup,
        bool cacheInvalidationEnabled = true,
        int? localListTtlSeconds = null,
        int? localItemTtlSeconds = null,
        bool? disableLocalCache = null,
        Action<IServiceCollection>? configureTestServices = null) =>
        new(new WebAppFactoryOptions
        {
            PostgresConnectionString = PostgresConnectionString,
            RedisConnectionString = RedisConnectionString,
            CacheInvalidationNodeId = nodeId,
            CacheInvalidationEnabled = cacheInvalidationEnabled,
            AppName = AppName,
            EnvironmentName = EnvironmentName,
            RunMigrationsAtStartup = runMigrationsAtStartup,
            UseProcessEnvironmentOverrides = true,
            LocalListTtlSeconds = localListTtlSeconds,
            LocalItemTtlSeconds = localItemTtlSeconds,
            DisableLocalCache = disableLocalCache,
            ConfigureTestServices = configureTestServices
        });
}
