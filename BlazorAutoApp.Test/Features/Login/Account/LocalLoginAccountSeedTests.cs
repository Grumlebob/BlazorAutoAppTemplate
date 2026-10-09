using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Account.Seed;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace BlazorAutoApp.Test.Features.Login.Account;

public sealed class LocalLoginAccountSeedingRulesTests
{
    [Theory]
    [InlineData("Development", null, true)]
    [InlineData("Development", "false", false)]
    [InlineData("Docker", null, false)]
    [InlineData("Docker", "true", true)]
    [InlineData("Production", null, false)]
    [InlineData("Production", "true", false)]
    public void IsSeedingEnabled_IsOnByDefaultOnlyInDevelopment(string environment, string? enabled, bool expected)
    {
        var settings = new Dictionary<string, string?>();
        if (enabled is not null)
        {
            settings["LocalAccounts:Enabled"] = enabled;
        }

        var configuration = new ConfigurationBuilder().AddInMemoryCollection(settings).Build();

        Assert.Equal(expected, LocalLoginAccountSeedExtensions.IsSeedingEnabled(new StubEnvironment(environment), configuration));
    }

    [Fact]
    public void DockerSettings_DoNotSeedOrShipPasswords()
    {
        var path = Path.Combine(SourceRoot(), "BlazorAutoApp", "appsettings.Docker.json");
        var configuration = new ConfigurationBuilder().AddJsonFile(path).Build();

        Assert.False(configuration.GetValue<bool>("LocalAccounts:Enabled"));
        Assert.Null(configuration["LocalAccounts:Admin:Password"]);
        Assert.Null(configuration["LocalAccounts:User:Password"]);
    }

    private static string SourceRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "BlazorAutoApp", "appsettings.Docker.json")))
        {
            directory = directory.Parent;
        }

        return directory?.FullName ?? throw new DirectoryNotFoundException("Repository root not found.");
    }

    private sealed class StubEnvironment(string environmentName) : IHostEnvironment
    {
        public string EnvironmentName { get; set; } = environmentName;
        public string ApplicationName { get; set; } = "BlazorAutoApp";
        public string ContentRootPath { get; set; } = AppContext.BaseDirectory;
        public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
    }
}

[Collection(TestCollectionNames.Integration)]
public sealed class LocalLoginAccountLockTests(WebAppFactory factory)
{
    [Fact]
    public async Task LockPublishedDefaultAccounts_LocksOnlyAccountsStillUsingTheDefaultPassword()
    {
        using var scope = factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var suffix = Guid.NewGuid().ToString("N");
        var defaultEmail = $"seed-default-{suffix}@example.test";
        var changedEmail = $"seed-changed-{suffix}@example.test";
        var missingEmail = $"seed-missing-{suffix}@example.test";
        const string publishedPassword = "Published-123";

        var defaultUser = await CreateUserAsync(userManager, defaultEmail, publishedPassword);
        var changedUser = await CreateUserAsync(userManager, changedEmail, "Changed-Pass-456");
        var stampBefore = await userManager.GetSecurityStampAsync(defaultUser);

        try
        {
            var accounts = new[]
            {
                (defaultEmail, publishedPassword),
                (changedEmail, publishedPassword),
                (missingEmail, publishedPassword),
            };

            var locked = await LocalLoginAccountSeedExtensions.LockPublishedDefaultAccountsAsync(
                userManager, NullLogger.Instance, accounts);
            var lockedAgain = await LocalLoginAccountSeedExtensions.LockPublishedDefaultAccountsAsync(
                userManager, NullLogger.Instance, accounts);

            Assert.Equal(1, locked);
            Assert.Equal(0, lockedAgain);
            defaultUser = (await userManager.FindByEmailAsync(defaultEmail))!;
            Assert.True(await userManager.IsLockedOutAsync(defaultUser));
            Assert.NotEqual(stampBefore, await userManager.GetSecurityStampAsync(defaultUser));
            changedUser = (await userManager.FindByEmailAsync(changedEmail))!;
            Assert.False(await userManager.IsLockedOutAsync(changedUser));
        }
        finally
        {
            await userManager.DeleteAsync((await userManager.FindByEmailAsync(defaultEmail))!);
            await userManager.DeleteAsync((await userManager.FindByEmailAsync(changedEmail))!);
        }
    }

    private static async Task<ApplicationUser> CreateUserAsync(
        UserManager<ApplicationUser> userManager,
        string email,
        string password)
    {
        var user = new ApplicationUser { UserName = email, Email = email, EmailConfirmed = true };
        var result = await userManager.CreateAsync(user, password);
        Assert.True(result.Succeeded, string.Join("; ", result.Errors.Select(error => error.Description)));
        return user;
    }
}
