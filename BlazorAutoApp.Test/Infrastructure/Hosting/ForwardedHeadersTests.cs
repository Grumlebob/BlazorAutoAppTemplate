using System.Collections.Generic;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

public sealed class ForwardedHeadersTests
{
    [Fact]
    public void DefaultConfiguration_DoesNotTrustAllForwardedHeaders()
    {
        using var environment = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["Database__RunMigrationsAtStartup"] = "false",
            ["Redis__Configuration"] = "CHANGE_ME",
            ["Redis__AllowMissing"] = "true",
            ["ForwardedHeaders__KnownNetworks__0"] = null,
            ["ForwardedHeaders__KnownNetworks__1"] = null,
            ["ForwardedHeaders__KnownProxies__0"] = null
        });
        using var factory = CreateFactory([]);

        var options = factory.Services.GetRequiredService<IOptions<ForwardedHeadersOptions>>().Value;

        Assert.Empty(options.KnownProxies);
        Assert.Empty(options.KnownIPNetworks);
        Assert.Equal(1, options.ForwardLimit);
        Assert.True(options.ForwardedHeaders.HasFlag(ForwardedHeaders.XForwardedFor));
        Assert.True(options.ForwardedHeaders.HasFlag(ForwardedHeaders.XForwardedProto));
        Assert.True(options.ForwardedHeaders.HasFlag(ForwardedHeaders.XForwardedHost));
    }

    [Fact]
    public void ConfiguredTrustedNetwork_IsAppliedExplicitly()
    {
        using var environment = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["Database__RunMigrationsAtStartup"] = "false",
            ["Redis__Configuration"] = "CHANGE_ME",
            ["Redis__AllowMissing"] = "true",
            ["ForwardedHeaders__KnownNetworks__0"] = "10.0.0.0/8",
            ["ForwardedHeaders__KnownProxies__0"] = "127.0.0.1"
        });
        using var factory = CreateFactory([]);

        var options = factory.Services.GetRequiredService<IOptions<ForwardedHeadersOptions>>().Value;

        Assert.Contains(options.KnownProxies, proxy => proxy.ToString() == "127.0.0.1");
        Assert.Contains(options.KnownIPNetworks, network => network.PrefixLength == 8 && network.BaseAddress.ToString() == "10.0.0.0");
    }

    private static WebApplicationFactory<Program> CreateFactory(Dictionary<string, string?> overrides)
    {
        var testConfiguration = new Dictionary<string, string?>
        {
            ["ConnectionStrings:DefaultConnection"] = "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres;GSS Encryption Mode=Disable",
            ["Database:RunMigrationsAtStartup"] = "false",
            ["LocalAccounts:Enabled"] = "false",
            ["Redis:Configuration"] = "CHANGE_ME",
            ["Redis:AllowMissing"] = "true"
        };

        foreach (var (key, value) in overrides)
        {
            testConfiguration[key] = value;
        }

        return new WebApplicationFactory<Program>()
            .WithWebHostBuilder(builder =>
            {
                builder.UseEnvironment("Testing");
                builder.ConfigureAppConfiguration((_, configuration) =>
                {
                    configuration.AddInMemoryCollection(testConfiguration);
                });
            });
    }
}
