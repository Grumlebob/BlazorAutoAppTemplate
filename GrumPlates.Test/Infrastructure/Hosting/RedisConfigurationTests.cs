using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using GrumPlates.Features.Login.Account;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Options;
using StackExchange.Redis;
using GrumPlates.Test.TestSupport.Integration;
using Xunit;

namespace GrumPlates.Test.Infrastructure.Hosting;

[Collection(TestCollectionNames.EnvironmentMutation)]
public sealed class RedisConfigurationTests
{
    [Fact]
    public void Production_RequiresRedisConfiguration_WhenFallbackIsNotAllowed()
    {
        using var environment = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["Redis__Configuration"] = "CHANGE_ME",
            ["Redis__AllowMissing"] = "false"
        });
        using var factory = CreateFactory();

        var exception = Assert.Throws<InvalidOperationException>(() => _ = factory.Services);
        Assert.Contains("Redis:Configuration must be configured", exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Production_AllowsMissingRedis_WhenFallbackIsExplicitlyAllowed()
    {
        using var environment = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["Redis__Configuration"] = "CHANGE_ME",
            ["Redis__AllowMissing"] = "true"
        });
        using var factory = CreateFactory();

        var services = factory.Services;
        var cache = services.GetRequiredService<IDistributedCache>();
        var key = $"redis-fallback:{Guid.NewGuid():N}";
        const string expected = "stored by the local fallback";

        await cache.SetStringAsync(key, expected);

        Assert.Equal(expected, await cache.GetStringAsync(key));
        Assert.Null(services.GetService<IConnectionMultiplexer>());
        Assert.DoesNotContain(
            services.GetRequiredService<IOptions<HealthCheckServiceOptions>>().Value.Registrations,
            registration => registration.Name == "redis");
    }

    private static WebApplicationFactory<Program> CreateFactory() =>
        new WebApplicationFactory<Program>()
            .WithWebHostBuilder(builder =>
            {
                builder.UseEnvironment("Production");
                builder.ConfigureAppConfiguration((_, configuration) =>
                {
                    configuration.AddInMemoryCollection(new Dictionary<string, string?>
                    {
                        ["App:Name"] = "GrumPlates.RedisConfigurationTests",
                        ["ConnectionStrings:DefaultConnection"] = "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres;GSS Encryption Mode=Disable",
                        ["Database:RunMigrationsAtStartup"] = "false",
                        ["AuthorBooks:SeedAtStartup"] = "false"
                    });
                });
                builder.ConfigureTestServices(services =>
                    services.AddScoped<IUserStore<ApplicationUser>, EmptyIdentityUserEmailStore>());
            });
}
