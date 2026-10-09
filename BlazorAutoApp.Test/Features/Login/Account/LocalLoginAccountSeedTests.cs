using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Account.Seed;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
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

    [Fact]
    public void DevelopmentSettings_DoNotConfigureAnAdminAccount()
    {
        var path = Path.Combine(SourceRoot(), "BlazorAutoApp", "appsettings.Development.json");
        var configuration = new ConfigurationBuilder().AddJsonFile(path).Build();

        Assert.True(configuration.GetValue<bool>("LocalAccounts:Enabled"));
        Assert.Null(configuration["LocalAccounts:Admin:Email"]);
        Assert.Null(configuration["LocalAccounts:Admin:Password"]);
        Assert.Null(configuration["LocalAccounts:Admin:Role"]);
    }

    [Theory]
    [InlineData("Development", true, "admin@admin.com")]
    [InlineData("Development", false, "admin@admin.com")]
    [InlineData("Docker", true, "admin@admin.com")]
    [InlineData("Docker", false, "admin@admin.com,user@user.com")]
    [InlineData("Production", false, "admin@admin.com")]
    public void PublishedAccountsToLock_AlwaysIncludesLegacyAdminAndLocksUserOnlyInDockerWithoutSeeding(
        string environment,
        bool seedingEnabled,
        string expectedEmails)
    {
        var accounts = LocalLoginAccountSeedExtensions.GetAccountsToLock(
            new StubEnvironment(environment), seedingEnabled);

        Assert.Equal(expectedEmails.Split(','), accounts.Select(account => account.Email));
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

    internal sealed class StubEnvironment(string environmentName) : IHostEnvironment
    {
        public string EnvironmentName { get; set; } = environmentName;
        public string ApplicationName { get; set; } = "BlazorAutoApp";
        public string ContentRootPath { get; set; } = AppContext.BaseDirectory;
        public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
    }

    [Fact]
    public async Task LockPublishedDefaultAccounts_FailsStartupWhenTheAccountCannotBeVerified()
    {
        using var serviceProvider = new ServiceCollection().BuildServiceProvider();
        using var userManager = new UserManager<ApplicationUser>(
            new UserStoreWithoutEmail(),
            Options.Create(new IdentityOptions()),
            new PasswordHasher<ApplicationUser>(),
            [],
            [],
            new UpperInvariantLookupNormalizer(),
            new IdentityErrorDescriber(),
            serviceProvider,
            NullLogger<UserManager<ApplicationUser>>.Instance);

        await Assert.ThrowsAsync<NotSupportedException>(() =>
            LocalLoginAccountSeedExtensions.LockPublishedDefaultAccountsAsync(
                userManager,
                NullLogger.Instance,
                [("legacy-admin@example.test", "published-password")]));
    }

    private sealed class UserStoreWithoutEmail : IUserStore<ApplicationUser>
    {
        public Task<ApplicationUser?> FindByIdAsync(string userId, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<ApplicationUser?> FindByNameAsync(string normalizedUserName, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<string> GetUserIdAsync(ApplicationUser user, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<string?> GetUserNameAsync(ApplicationUser user, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task SetUserNameAsync(ApplicationUser user, string? userName, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<string?> GetNormalizedUserNameAsync(ApplicationUser user, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task SetNormalizedUserNameAsync(ApplicationUser user, string? normalizedName, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<IdentityResult> CreateAsync(ApplicationUser user, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<IdentityResult> UpdateAsync(ApplicationUser user, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<IdentityResult> DeleteAsync(ApplicationUser user, CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public void Dispose()
        {
        }
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

        try
        {
            var defaultUser = await CreateUserAsync(userManager, defaultEmail, publishedPassword);
            var changedUser = await CreateUserAsync(userManager, changedEmail, "Changed-Pass-456");
            Assert.True((await userManager.SetLockoutEnabledAsync(defaultUser, true)).Succeeded);
            Assert.True((await userManager.SetLockoutEndDateAsync(defaultUser, DateTimeOffset.UtcNow.AddMinutes(5))).Succeeded);
            var stampBefore = await userManager.GetSecurityStampAsync(defaultUser);
            var accounts = new[]
            {
                (defaultEmail, publishedPassword),
                (changedEmail, publishedPassword),
                (missingEmail, publishedPassword),
            };

            await LocalLoginAccountSeedExtensions.LockPublishedDefaultAccountsAsync(userManager, NullLogger.Instance, accounts);
            defaultUser = (await userManager.FindByEmailAsync(defaultEmail))!;
            var stampAfterLock = await userManager.GetSecurityStampAsync(defaultUser);
            await LocalLoginAccountSeedExtensions.LockPublishedDefaultAccountsAsync(userManager, NullLogger.Instance, accounts);

            Assert.True(await userManager.IsLockedOutAsync(defaultUser));
            Assert.Equal(DateTimeOffset.MaxValue, await userManager.GetLockoutEndDateAsync(defaultUser));
            Assert.NotEqual(stampBefore, stampAfterLock);
            Assert.Equal(stampAfterLock, await userManager.GetSecurityStampAsync(defaultUser));
            changedUser = (await userManager.FindByEmailAsync(changedEmail))!;
            Assert.False(await userManager.IsLockedOutAsync(changedUser));
            Assert.True(await userManager.CheckPasswordAsync(changedUser, "Changed-Pass-456"));
        }
        finally
        {
            await DeleteUserIfExistsAsync(userManager, defaultEmail);
            await DeleteUserIfExistsAsync(userManager, changedEmail);
        }
    }

    [Fact]
    public async Task DevelopmentStartupSeedsOnlyConfiguredUserAndLocksLegacyAdmin()
    {
        const string legacyAdminEmail = "admin@admin.com";
        const string legacyAdminPassword = "Admin123";
        var suffix = Guid.NewGuid().ToString("N");
        var localUserEmail = $"seed-user-{suffix}@example.test";
        var localUserPassword = $"Seed-User-{suffix}-123";
        var localUserRole = $"seed-review-{suffix}";
        var legacyAdminCreated = false;
        string stampBefore;
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["LocalAccounts:Enabled"] = "true",
                ["LocalAccounts:User:Email"] = localUserEmail,
                ["LocalAccounts:User:Password"] = localUserPassword,
                ["LocalAccounts:User:Role"] = localUserRole
            })
            .Build();

        try
        {
            using (var preSeedScope = factory.Services.CreateScope())
            {
                var userManager = preSeedScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
                Assert.Null(await userManager.FindByEmailAsync(legacyAdminEmail));
            }

            await LocalLoginAccountSeedExtensions.SeedLocalLoginAccountsAsync(
                new LocalLoginAccountSeedingRulesTests.StubEnvironment("Development"),
                configuration,
                factory.Services);

            using (var seedVerificationScope = factory.Services.CreateScope())
            {
                var userManager = seedVerificationScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
                var seededAdmin = await userManager.FindByEmailAsync(legacyAdminEmail);
                legacyAdminCreated = seededAdmin is not null;
                Assert.Null(seededAdmin);

                var localUser = await userManager.FindByEmailAsync(localUserEmail);
                Assert.NotNull(localUser);
                Assert.True(await userManager.CheckPasswordAsync(localUser, localUserPassword));
                Assert.True(await userManager.IsInRoleAsync(localUser, localUserRole));
            }

            using (var setupScope = factory.Services.CreateScope())
            {
                var userManager = setupScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
                var legacyAdmin = new ApplicationUser
                {
                    UserName = legacyAdminEmail,
                    Email = legacyAdminEmail,
                    EmailConfirmed = true
                };
                var createResult = await userManager.CreateAsync(legacyAdmin);
                legacyAdminCreated = createResult.Succeeded;
                Assert.True(createResult.Succeeded, string.Join("; ", createResult.Errors.Select(error => error.Description)));
                legacyAdmin.PasswordHash = userManager.PasswordHasher.HashPassword(legacyAdmin, legacyAdminPassword);
                var passwordResult = await userManager.UpdateAsync(legacyAdmin);
                Assert.True(passwordResult.Succeeded, string.Join("; ", passwordResult.Errors.Select(error => error.Description)));
                stampBefore = await userManager.GetSecurityStampAsync(legacyAdmin);
            }

            await LocalLoginAccountSeedExtensions.SeedLocalLoginAccountsAsync(
                new LocalLoginAccountSeedingRulesTests.StubEnvironment("Development"),
                configuration,
                factory.Services);

            using (var verificationScope = factory.Services.CreateScope())
            {
                var userManager = verificationScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
                var legacyAdmin = (await userManager.FindByEmailAsync(legacyAdminEmail))!;
                Assert.True(await userManager.IsLockedOutAsync(legacyAdmin));
                Assert.Equal(DateTimeOffset.MaxValue, await userManager.GetLockoutEndDateAsync(legacyAdmin));
                Assert.NotEqual(stampBefore, await userManager.GetSecurityStampAsync(legacyAdmin));

                var localUser = await userManager.FindByEmailAsync(localUserEmail);
                Assert.NotNull(localUser);
                Assert.True(await userManager.CheckPasswordAsync(localUser, localUserPassword));
                Assert.True(await userManager.IsInRoleAsync(localUser, localUserRole));
            }
        }
        finally
        {
            using var cleanupScope = factory.Services.CreateScope();
            var userManager = cleanupScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var roleManager = cleanupScope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
            if (legacyAdminCreated)
            {
                await DeleteUserIfExistsAsync(userManager, legacyAdminEmail);
            }

            await DeleteUserIfExistsAsync(userManager, localUserEmail);
            var localRole = await roleManager.FindByNameAsync(localUserRole);
            if (localRole is not null)
            {
                var result = await roleManager.DeleteAsync(localRole);
                Assert.True(result.Succeeded, string.Join("; ", result.Errors.Select(error => error.Description)));
            }
        }
    }

    private static async Task DeleteUserIfExistsAsync(UserManager<ApplicationUser> userManager, string email)
    {
        var user = await userManager.FindByEmailAsync(email);
        if (user is not null)
        {
            var result = await userManager.DeleteAsync(user);
            Assert.True(result.Succeeded, string.Join("; ", result.Errors.Select(error => error.Description)));
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
