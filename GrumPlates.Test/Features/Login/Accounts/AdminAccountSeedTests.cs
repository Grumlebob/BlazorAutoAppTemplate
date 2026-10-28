using GrumPlates.Features.Login.Account;
using GrumPlates.Features.Login.Accounts;
using GrumPlates.Infrastructure.Persistence;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace GrumPlates.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AdminAccountSeedTests
{
    [Fact]
    public async Task DisabledSeed_ReturnsWithoutResolvingDatabaseServices()
    {
        using var services = new ServiceCollection().BuildServiceProvider();
        var options = new AccountOptions { AdminSeed = new AdminSeedOptions { Enabled = false } };

        await AdminAccountSeed.SeedConfiguredAdminAsync(options, services, NullLogger.Instance);
    }

    [Fact]
    public async Task Seed_CreatesConfirmedAdminOnceAndDoesNotResetPasswordOrUnlock()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var email = $"admin-{Guid.NewGuid():N}@example.test";
        var password = NewPassword();
        await SeedAsync(fixture, email, password);

        string hash;
        string stamp;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var admin = await users.FindByEmailAsync(email);
            Assert.NotNull(admin);
            Assert.True(admin.EmailConfirmed);
            Assert.True(await users.CheckPasswordAsync(admin, password));
            Assert.True(await users.IsInRoleAsync(admin, "Admin"));
            using var client = fixture.CreateClient();
            using var login = await RealCookieAccountFixture.LoginAsync(client, email, password);
            Assert.Equal(System.Net.HttpStatusCode.OK, login.StatusCode);
            var session = await RealCookieAccountFixture.ReadSessionAsync(client);
            Assert.False(session.EmailEnabled);
            Assert.False(session.RegistrationEnabled);
            Assert.Equal(admin.Id, session.User?.Id);
            Assert.Contains("Admin", session.User!.Roles);
            hash = admin.PasswordHash!;
            stamp = admin.SecurityStamp!;
            Assert.True((await users.SetLockoutEnabledAsync(admin, true)).Succeeded);
            Assert.True((await users.SetLockoutEndDateAsync(admin, DateTimeOffset.MaxValue)).Succeeded);
        }

        await SeedAsync(fixture, email, NewPassword());

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var admin = await users.FindByEmailAsync(email);
            Assert.NotNull(admin);
            Assert.Equal(hash, admin.PasswordHash);
            Assert.Equal(stamp, admin.SecurityStamp);
            Assert.True(admin.LockoutEnabled);
            Assert.Equal(DateTimeOffset.MaxValue, admin.LockoutEnd);
            Assert.True(await users.CheckPasswordAsync(admin, password));
            Assert.True(await users.IsInRoleAsync(admin, "Admin"));
        }
    }

    [Fact]
    public async Task Seed_RefusesToPromoteAnExistingOrdinaryAccount()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var email = $"ordinary-{Guid.NewGuid():N}@example.test";
        var password = NewPassword();
        string id;
        string hash;
        string stamp;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = new ApplicationUser { Email = email, UserName = email, EmailConfirmed = false };
            Assert.True((await users.CreateAsync(user, password)).Succeeded);
            id = user.Id;
            hash = user.PasswordHash!;
            stamp = user.SecurityStamp!;
        }

        var error = await Assert.ThrowsAsync<InvalidOperationException>(() => SeedAsync(fixture, email, NewPassword()));
        Assert.DoesNotContain(password, error.Message);

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(id);
            Assert.NotNull(user);
            Assert.False(user.EmailConfirmed);
            Assert.Equal(hash, user.PasswordHash);
            Assert.Equal(stamp, user.SecurityStamp);
            Assert.False(await users.IsInRoleAsync(user, "Admin"));
        }
    }

    [Fact]
    public async Task ConcurrentSeeds_CreateOneCompleteAdmin()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var email = $"concurrent-admin-{Guid.NewGuid():N}@example.test";
        var password = NewPassword();

        await Task.WhenAll(Enumerable.Range(0, 4).Select(_ => SeedAsync(fixture, email, password)));

        using var scope = fixture.Factory.Services.CreateScope();
        var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var admin = await users.FindByEmailAsync(email);
        Assert.NotNull(admin);
        Assert.True(admin.EmailConfirmed);
        Assert.True(await users.CheckPasswordAsync(admin, password));
        Assert.True(await users.IsInRoleAsync(admin, "Admin"));
        Assert.Equal(1, await users.Users.CountAsync(user => user.NormalizedEmail == users.NormalizeEmail(email)));
    }

    [Fact]
    public async Task Seed_RollsBackUserAndRoleWhenRoleAssignmentFails()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var email = $"rollback-admin-{Guid.NewGuid():N}@example.test";
        await using (var scope = fixture.Factory.Services.CreateAsyncScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            await db.Database.ExecuteSqlRawAsync("""
                CREATE OR REPLACE FUNCTION "RejectFixtureAdminRole"() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'synthetic admin role failure'; END;
                $$;
                """);
            await db.Database.ExecuteSqlRawAsync("""
                CREATE TRIGGER "RejectFixtureAdminRole" BEFORE INSERT ON "AspNetUserRoles"
                FOR EACH ROW EXECUTE FUNCTION "RejectFixtureAdminRole"();
                """);
        }

        try
        {
            await Assert.ThrowsAnyAsync<Exception>(() => SeedAsync(fixture, email, NewPassword()));
        }
        finally
        {
            await using var scope = fixture.Factory.Services.CreateAsyncScope();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            await db.Database.ExecuteSqlRawAsync("DROP TRIGGER IF EXISTS \"RejectFixtureAdminRole\" ON \"AspNetUserRoles\";");
            await db.Database.ExecuteSqlRawAsync("DROP FUNCTION IF EXISTS \"RejectFixtureAdminRole\"();");
        }

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var roles = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
            Assert.Null(await users.FindByEmailAsync(email));
            Assert.False(await roles.RoleExistsAsync("Admin"));
        }
    }

    [Fact]
    public async Task Seed_RetriesUncertainCommitWithoutRepeatingAccountEffects()
    {
        var interceptor = new CommitUncertaintyInterceptor();
        await using var fixture = new RealCookieAccountFixture(
            configureTestServices: services => services.AddSingleton<IDbTransactionInterceptor>(interceptor));
        await fixture.InitializeAsync();
        var email = $"uncertain-admin-{Guid.NewGuid():N}@example.test";
        var password = NewPassword();
        interceptor.ThrowAfterNextCommit();

        await SeedAsync(fixture, email, password);

        Assert.Equal(1, interceptor.ThrownCount);
        using var scope = fixture.Factory.Services.CreateScope();
        var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var admin = await users.FindByEmailAsync(email);
        Assert.NotNull(admin);
        Assert.True(await users.CheckPasswordAsync(admin, password));
        Assert.True(await users.IsInRoleAsync(admin, "Admin"));
        Assert.Equal(1, await users.Users.CountAsync(user => user.NormalizedEmail == users.NormalizeEmail(email)));
    }

    private static Task SeedAsync(RealCookieAccountFixture fixture, string email, string password) =>
        AdminAccountSeed.SeedConfiguredAdminAsync(
            new AccountOptions
            {
                Enabled = true,
                AdminSeed = new AdminSeedOptions { Enabled = true, Email = email, Password = password }
            },
            fixture.Factory.Services,
            NullLogger.Instance);

    private static string NewPassword() => $"Seed admin phrase {Guid.NewGuid():N}";
}
