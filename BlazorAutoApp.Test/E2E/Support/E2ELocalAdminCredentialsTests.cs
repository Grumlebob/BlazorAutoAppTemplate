using System.Collections.Generic;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.E2E.Support;

[Collection(TestCollectionNames.E2E)]
public sealed class E2ELocalAdminCredentialsTests
{
    [Fact]
    public void EmailAndPassword_FallBackToLocalSeedDefaults()
    {
        using var _ = NewScope(
            ("E2E_LOCAL_ADMIN_EMAIL", null),
            ("E2E_LOCAL_ADMIN_PASSWORD", null),
            ("LocalAccounts__Admin__Email", null),
            ("LocalAccounts__Admin__Password", null));

        Assert.Equal("admin@admin.com", E2ELocalAdminCredentials.Email);
        Assert.Equal("Admin123", E2ELocalAdminCredentials.Password);
    }

    [Fact]
    public void EmailAndPassword_UseApplicationAdminConfigurationBeforeDefaults()
    {
        using var _ = NewScope(
            ("E2E_LOCAL_ADMIN_EMAIL", null),
            ("E2E_LOCAL_ADMIN_PASSWORD", null),
            ("LocalAccounts__Admin__Email", "configured-admin@example.test"),
            ("LocalAccounts__Admin__Password", "ConfiguredPassword123"));

        Assert.Equal("configured-admin@example.test", E2ELocalAdminCredentials.Email);
        Assert.Equal("ConfiguredPassword123", E2ELocalAdminCredentials.Password);
    }

    [Fact]
    public void EmailAndPassword_UseE2EOverridesBeforeApplicationConfiguration()
    {
        using var _ = NewScope(
            ("E2E_LOCAL_ADMIN_EMAIL", "e2e-admin@example.test"),
            ("E2E_LOCAL_ADMIN_PASSWORD", "E2EPassword123"),
            ("LocalAccounts__Admin__Email", "configured-admin@example.test"),
            ("LocalAccounts__Admin__Password", "ConfiguredPassword123"));

        Assert.Equal("e2e-admin@example.test", E2ELocalAdminCredentials.Email);
        Assert.Equal("E2EPassword123", E2ELocalAdminCredentials.Password);
    }

    private static EnvironmentVariableScope NewScope(params (string Key, string? Value)[] values)
    {
        var variables = new Dictionary<string, string?>();
        foreach (var (key, value) in values)
        {
            variables[key] = value;
        }

        return new EnvironmentVariableScope(variables);
    }
}
