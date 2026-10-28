using System.Net;
using System.Net.Http.Json;
using GrumPlates.Core.Features.Login.UseCases.Shared;
using GrumPlates.Features.Login.Accounts;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;

namespace GrumPlates.Test.Features.Login.Accounts;

public sealed class AccountOptionsTests
{
    [Fact]
    public void StartupSnapshot_DoesNotFollowPartialConfigurationReloads()
    {
        var configuration = Configuration(new() { ["Accounts:Enabled"] = "true" });
        var services = new ServiceCollection();
        services.AddAccountFeature(configuration, new Account.LocalLoginAccountSeedingRulesTests.StubEnvironment("Testing"));
        using var provider = services.BuildServiceProvider();
        var snapshot = provider.GetRequiredService<AccountOptions>();
        configuration["Accounts:Enabled"] = "false";
        configuration.Reload();
        Assert.True(snapshot.Enabled);
        Assert.Same(snapshot, provider.GetRequiredService<IOptions<AccountOptions>>().Value);
        Assert.True(provider.GetRequiredService<AccountOptions>().Enabled);
    }

    [Theory]
    [InlineData("Accounts:AdminSeed:Email", "private@example.test")]
    [InlineData("Accounts:AdminSeed:Password", "private-seed-canary")]
    [InlineData("Accounts:Email:Password", "private-smtp-canary")]
    [InlineData("Accounts:Email:Username", "private-smtp-user")]
    [InlineData("Accounts:Email:From", "private@example.test")]
    [InlineData("Accounts:Email:Host", "https://mail.example.test")]
    [InlineData("Accounts:Email:Host", " ")]
    [InlineData("Accounts:RegistrationEnabled", "true")]
    [InlineData("Accounts:AdminSeed:Enabled", "true")]
    [InlineData("Accounts:Email:Security", "None")]
    [InlineData("Accounts:Email:Port", "0")]
    [InlineData("Accounts:Email:MaxAttempts", "6")]
    [InlineData("Accounts:WriteLimit:PermitLimit", "0")]
    [InlineData("Accounts:WriteLimit:WindowSeconds", "0")]
    public void InvalidSettings_FailBeforeServicesStart_WithoutEchoingSecrets(string key, string value)
    {
        var configuration = Configuration(new() { [key] = value });
        var services = new ServiceCollection();
        var error = Assert.Throws<OptionsValidationException>(() => services.AddAccountFeature(configuration,
            new Account.LocalLoginAccountSeedingRulesTests.StubEnvironment("Testing")));
        Assert.Contains("Accounts:", error.Message);
        if (value.StartsWith("private", StringComparison.Ordinal)) Assert.DoesNotContain(value, error.Message);
    }

    [Theory]
    [InlineData("Accounts:AdminSeed:Email", "partial-admin@example.test")]
    [InlineData("Accounts:AdminSeed:Password", "a sufficiently long seed phrase")]
    public void PartialAdminSeedCredentials_FailValidationWithoutEchoingValues(string key, string value)
    {
        var configuration = Configuration(new()
        {
            ["Accounts:Enabled"] = "true",
            [key] = value
        });
        var services = new ServiceCollection();

        var error = Assert.Throws<OptionsValidationException>(() => services.AddAccountFeature(configuration,
            new Account.LocalLoginAccountSeedingRulesTests.StubEnvironment("Testing")));

        Assert.Contains("Accounts:AdminSeed:Email and Accounts:AdminSeed:Password", error.Message);
        Assert.DoesNotContain(value, error.Message);
    }

    [Theory]
    [InlineData("http://example.test")]
    [InlineData("https://user:pass@example.test")]
    [InlineData("https://example.test/path")]
    [InlineData("https://example.test/%2e%2e")]
    [InlineData("https://example.test?")]
    [InlineData("https://example.test#")]
    [InlineData("https://example.test\\path")]
    [InlineData(" https://example.test")]
    [InlineData("https://example.test\r\n")]
    public void PublicOrigin_RefusesNonOriginValues(string origin)
    {
        Assert.Throws<OptionsValidationException>(() => new ServiceCollection().AddAccountFeature(
            Configuration(new() { ["Accounts:PublicOrigin"] = origin }),
            new Account.LocalLoginAccountSeedingRulesTests.StubEnvironment("Testing")));
    }

    [Theory]
    [InlineData("https://example.test")]
    [InlineData("https://example.test/")]
    [InlineData("https://example.test:443")]
    [InlineData("https://localhost:7186")]
    public void EmailConfiguration_AcceptsBareHttpsOriginAndDefaults(string origin)
    {
        var services = new ServiceCollection();
        services.AddAccountFeature(Configuration(new()
        {
            ["Accounts:Enabled"] = "true",
            ["Accounts:RegistrationEnabled"] = "true",
            ["Accounts:PublicOrigin"] = origin,
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:From"] = "sender@example.test"
        }), new Account.LocalLoginAccountSeedingRulesTests.StubEnvironment("Testing"));
        using var provider = services.BuildServiceProvider();
        var options = provider.GetRequiredService<AccountOptions>();
        Assert.True(options.EmailEnabled);
        Assert.Equal(20, options.WriteLimit.PermitLimit);
        Assert.Equal(300, options.WriteLimit.WindowSeconds);
        Assert.Equal(3, options.Email.MaxAttempts);
    }

    [Fact]
    public void ApplicationIdentity_IsStableAndSeparatesNamesAndEnvironments()
    {
        var identity = new AccountApplicationIdentity("app", "Testing").Id;
        Assert.Matches("^[0-9a-f]{32}$", identity);
        Assert.Equal(identity, new AccountApplicationIdentity("app", "Testing").Id);
        Assert.NotEqual(identity, new AccountApplicationIdentity("app", "Production").Id);
        Assert.NotEqual(identity, new AccountApplicationIdentity("clone", "Testing").Id);
        Assert.NotEqual(new AccountApplicationIdentity("a:b", "c").Id, new AccountApplicationIdentity("a", "b:c").Id);
    }

    private static IConfigurationRoot Configuration(Dictionary<string, string?> values) =>
        new ConfigurationBuilder().AddInMemoryCollection(values).Build();
}

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class ClientConfigurationTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Capability_IsExplicitCookieFreeAndSecretFree(bool enabled)
    {
        await using var fixture = new RealCookieAccountFixture(
            new Dictionary<string, string?> { ["Accounts:Enabled"] = enabled.ToString() },
            appName: $"capability-{Guid.NewGuid():N}");
        var factory = fixture.Factory;
        await factory.InitializeAsync();
        using var client = fixture.CreateClient();
        using var response = await client.GetAsync("/api/client-config");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.True(response.Headers.CacheControl?.NoStore);
        Assert.False(response.Headers.Contains("Set-Cookie"));
        var config = await response.Content.ReadFromJsonAsync<ClientConfiguration>();
        Assert.NotNull(config);
        Assert.Equal(1, config.SchemaVersion);
        Assert.Equal(enabled, config.AccountsEnabled);
        Assert.Matches("^[0-9a-f]{32}$", config.ApplicationId);
        using var json = System.Text.Json.JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal(3, json.RootElement.EnumerateObject().Count());
        using var session = await client.GetAsync("/api/auth/session");
        Assert.Equal(enabled ? HttpStatusCode.OK : HttpStatusCode.NotFound, session.StatusCode);
    }
}
