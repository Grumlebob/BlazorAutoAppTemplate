using Microsoft.AspNetCore.Identity;

namespace BlazorAutoApp.Features.Login.Account.Seed;

internal static class LocalLoginAccountSeedExtensions
{
    private const string SectionName = "LocalAccounts";
    private const string AdminRole = "Admin";
    private const string UserRole = "User";

    public static async Task SeedLocalLoginAccountsAsync(this WebApplication app)
    {
        var isLocalEnvironment = app.Environment.IsDevelopment() || app.Environment.IsEnvironment("Docker");
        var enabled = app.Configuration.GetValue($"{SectionName}:Enabled", isLocalEnvironment);
        if (!enabled)
        {
            return;
        }

        var logger = app.Services.GetRequiredService<ILoggerFactory>()
            .CreateLogger("LocalLoginAccountSeed");

        if (!isLocalEnvironment)
        {
            logger.LogWarning("Local login account seeding is enabled but skipped outside Development/Docker.");
            return;
        }

        var accounts = new[]
        {
            new LocalSeedAccount(
                GetValue(app.Configuration, "Admin:Email", "admin@admin.com"),
                GetValue(app.Configuration, "Admin:Password", "Admin123"),
                GetValue(app.Configuration, "Admin:Role", AdminRole)),
            new LocalSeedAccount(
                GetValue(app.Configuration, "User:Email", "user@user.com"),
                GetValue(app.Configuration, "User:Password", "User123"),
                GetValue(app.Configuration, "User:Role", UserRole))
        };

        using var scope = app.Services.CreateScope();
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

    private sealed record LocalSeedAccount(string Email, string Password, string Role);
}
