using System;
using System.Collections.Generic;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

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
    public void Production_AllowsMissingRedis_WhenFallbackIsExplicitlyAllowed()
    {
        using var environment = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["Redis__Configuration"] = "CHANGE_ME",
            ["Redis__AllowMissing"] = "true"
        });
        using var factory = CreateFactory();

        _ = factory.Services;
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
                        ["App:Name"] = "BlazorAutoApp.RedisConfigurationTests",
                        ["ConnectionStrings:DefaultConnection"] = "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres;GSS Encryption Mode=Disable",
                        ["Database:RunMigrationsAtStartup"] = "false",
                        ["AuthorBooks:SeedAtStartup"] = "false"
                    });
                });
            });
}
