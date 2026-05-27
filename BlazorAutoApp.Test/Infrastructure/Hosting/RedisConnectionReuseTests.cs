using System;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.DependencyInjection;
using StackExchange.Redis;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

public sealed class RedisConnectionReuseTests(SharedIntegrationEnvironment environment)
    : IClassFixture<SharedIntegrationEnvironment>
{
    [Fact]
    public async Task RedisBackedServices_UseRegisteredMultiplexer()
    {
        await using var factory = environment.CreateFactory(
            $"redis-reuse-{Guid.NewGuid():N}",
            runMigrations: true);
        await factory.InitializeAsync();

        var multiplexer = factory.Services.GetRequiredService<IConnectionMultiplexer>();
        var distributedCache = factory.Services.GetRequiredService<IDistributedCache>();
        var key = $"redis-reuse:{Guid.NewGuid():N}";

        await distributedCache.SetStringAsync(key, "ok");
        var value = await distributedCache.GetStringAsync(key);

        Assert.True(multiplexer.IsConnected);
        Assert.Equal("ok", value);
        Assert.Same(multiplexer, factory.Services.GetRequiredService<IConnectionMultiplexer>());
    }
}
