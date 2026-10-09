using Microsoft.AspNetCore.Identity;

namespace BlazorAutoApp.Features.Login.Account.Seed;

internal static class LocalLoginAccountSeedExtensions
{
    private const string SectionName = "LocalAccounts";
    private const string UserRole = "User";

    private static readonly (string Email, string Password) PublishedDefaultAdminAccount =
        ("admin@admin.com", "Admin123");

    // Earlier versions seeded these accounts in every Docker deployment and reset their
    // passwords on each start. Startup locks any account that still uses its published password.
    internal static readonly IReadOnlyList<(string Email, string Password)> PublishedDefaultAccounts =
    [
        PublishedDefaultAdminAccount,
        ("user@user.com", "User123"),
    ];

    public static Task SeedLocalLoginAccountsAsync(this WebApplication app) =>
        SeedLocalLoginAccountsAsync(app.Environment, app.Configuration, app.Services);

    internal static async Task SeedLocalLoginAccountsAsync(
        IHostEnvironment environment,
        IConfiguration configuration,
        IServiceProvider services)
    {
        var logger = services.GetRequiredService<ILoggerFactory>()
            .CreateLogger("LocalLoginAccountSeed");
        var seedingEnabled = IsSeedingEnabled(environment, configuration);

        using (var lockScope = services.CreateScope())
        {
            await LockPublishedDefaultAccountsAsync(
                lockScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>(),
                logger,
                GetAccountsToLock(environment, seedingEnabled));
        }

        if (!seedingEnabled)
        {
            if (configuration.GetValue($"{SectionName}:Enabled", false))
            {
                logger.LogWarning("Local login account seeding is enabled but skipped outside Development/Docker.");
            }

            return;
        }

        var accounts = GetLocalSeedAccounts(configuration);

        using var scope = services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var roleManager = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();

        foreach (var account in accounts)
        {
            await EnsureRoleAsync(roleManager, account.Role);
            var user = await EnsureUserAsync(userManager, account);
            await EnsureUserRoleAsync(userManager, user, account.Role);

            logger.LogInformation("Local login account ready: {Email} / {Role}", account.Email, account.Role);
        }
    }

    // Local demo account seeding is on by default only in Development. Docker runs seed only
    // when LocalAccounts:Enabled is set (the root docker-compose.yml does this for the User).
    internal static bool IsSeedingEnabled(IHostEnvironment environment, IConfiguration configuration)
    {
        var enabled = configuration.GetValue($"{SectionName}:Enabled", environment.IsDevelopment());
        return enabled && (environment.IsDevelopment() || environment.IsEnvironment("Docker"));
    }

    internal static IReadOnlyList<(string Email, string Password)> GetAccountsToLock(
        IHostEnvironment environment,
        bool seedingEnabled) =>
        environment.IsEnvironment("Docker") && !seedingEnabled
            ? PublishedDefaultAccounts
            : [PublishedDefaultAdminAccount];

    internal static IReadOnlyList<LocalSeedAccount> GetLocalSeedAccounts(IConfiguration configuration) =>
    [
        new LocalSeedAccount(
            GetValue(configuration, "User:Email", "user@user.com"),
            GetValue(configuration, "User:Password", "User123"),
            GetValue(configuration, "User:Role", UserRole))
    ];

    internal static async Task<int> LockPublishedDefaultAccountsAsync(
        UserManager<ApplicationUser> userManager,
        ILogger logger,
        IEnumerable<(string Email, string Password)> accounts)
    {
        var locked = 0;
        foreach (var (email, password) in accounts)
        {
            try
            {
                var user = await userManager.FindByEmailAsync(email);
                if (user is null
                    || !await userManager.CheckPasswordAsync(user, password))
                {
                    continue;
                }

                var lockoutEnabled = await userManager.GetLockoutEnabledAsync(user);
                var lockoutEnd = await userManager.GetLockoutEndDateAsync(user);
                if (lockoutEnabled && lockoutEnd == DateTimeOffset.MaxValue)
                {
                    continue;
                }

                ThrowIfFailed(await userManager.SetLockoutEnabledAsync(user, true), $"enable lockout for '{email}'");
                ThrowIfFailed(await userManager.SetLockoutEndDateAsync(user, DateTimeOffset.MaxValue), $"lock '{email}'");
                ThrowIfFailed(await userManager.UpdateSecurityStampAsync(user), $"sign out '{email}'");
                locked++;
                logger.LogWarning(
                    "Locked {Email}: it still used the published default password. Delete it, or reset its password and unlock it.",
                    email);
            }
            catch (Exception exception) when (exception is not OperationCanceledException)
            {
                // Never block startup; the warning tells the operator to remove the account.
                logger.LogError(exception, "Could not check or lock the published default account {Email}.", email);
            }
        }

        return locked;
    }

    private static string GetValue(IConfiguration configuration, string key, string fallback) =>
        configuration[$"{SectionName}:{key}"] ?? fallback;

    private static async Task EnsureRoleAsync(RoleManager<IdentityRole> roleManager, string role)
    {
        if (await roleManager.RoleExistsAsync(role))
        {
            return;
        }

        var result = await roleManager.CreateAsync(new IdentityRole(role));
        ThrowIfFailed(result, $"create local role '{role}'");
    }

    private static async Task<ApplicationUser> EnsureUserAsync(
        UserManager<ApplicationUser> userManager,
        LocalSeedAccount account)
    {
        var user = await userManager.FindByEmailAsync(account.Email);
        if (user is null)
        {
            user = new ApplicationUser
            {
                UserName = account.Email,
                Email = account.Email,
                EmailConfirmed = true
            };

            SetPasswordHash(userManager, user, account.Password);
            var createResult = await userManager.CreateAsync(user);
            ThrowIfFailed(createResult, $"create local login user '{account.Email}'");
            return user;
        }

        var changed = false;
        if (user.UserName != account.Email)
        {
            user.UserName = account.Email;
            changed = true;
        }

        if (user.Email != account.Email)
        {
            user.Email = account.Email;
            changed = true;
        }

        if (!user.EmailConfirmed)
        {
            user.EmailConfirmed = true;
            changed = true;
        }

        if (!await userManager.CheckPasswordAsync(user, account.Password))
        {
            SetPasswordHash(userManager, user, account.Password);
            changed = true;
        }

        if (changed)
        {
            var updateResult = await userManager.UpdateAsync(user);
            ThrowIfFailed(updateResult, $"update local login user '{account.Email}'");
        }

        return user;
    }

    private static void SetPasswordHash(
        UserManager<ApplicationUser> userManager,
        ApplicationUser user,
        string password)
    {
        user.PasswordHash = userManager.PasswordHasher.HashPassword(user, password);
        user.SecurityStamp = Guid.NewGuid().ToString("N");
    }

    private static async Task EnsureUserRoleAsync(
        UserManager<ApplicationUser> userManager,
        ApplicationUser user,
        string role)
    {
        if (await userManager.IsInRoleAsync(user, role))
        {
            return;
        }

        var result = await userManager.AddToRoleAsync(user, role);
        ThrowIfFailed(result, $"add local login user to role '{role}'");
    }

    private static void ThrowIfFailed(IdentityResult result, string action)
    {
        if (result.Succeeded)
        {
            return;
        }

        var errors = string.Join("; ", result.Errors.Select(error => error.Description));
        throw new InvalidOperationException($"Failed to {action}: {errors}");
    }

    internal sealed record LocalSeedAccount(string Email, string Password, string Role);
}
