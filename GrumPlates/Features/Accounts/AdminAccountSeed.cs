using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Features.Accounts;

internal static class AdminAccountSeed
{
    public static Task SeedConfiguredAdminAsync(this WebApplication app) =>
        SeedConfiguredAdminAsync(
            app.Services.GetRequiredService<IOptions<AccountOptions>>().Value,
            app.Services,
            app.Logger);

    internal static async Task SeedConfiguredAdminAsync(
        AccountOptions options,
        IServiceProvider services,
        ILogger logger)
    {
        if (!options.AdminSeed.Enabled)
        {
            return;
        }

        using var strategyScope = services.CreateScope();
        var strategy = strategyScope.ServiceProvider.GetRequiredService<AppDbContext>().Database.CreateExecutionStrategy();
        await strategy.ExecuteAsync(async () =>
        {
            using var scope = services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var roles = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
            await using var transaction = await db.Database.BeginTransactionAsync();
            // A transaction-scoped database lock coordinates replicas, not just this process.
            await db.Database.ExecuteSqlRawAsync("SELECT pg_advisory_xact_lock(73529301015421)");
            var existing = await users.FindByEmailAsync(options.AdminSeed.Email);
            if (existing is not null)
            {
                if (!await users.IsInRoleAsync(existing, "Admin"))
                {
                    throw new InvalidOperationException("Admin seed refused: the configured email already belongs to a non-admin account.");
                }

                await transaction.CommitAsync();
                logger.LogInformation("Configured admin account already exists; no account changes made.");
                return;
            }

            if (!await roles.RoleExistsAsync("Admin"))
            {
                Ensure(await roles.CreateAsync(new IdentityRole("Admin")));
            }
            var user = new ApplicationUser
            {
                UserName = options.AdminSeed.Email,
                Email = options.AdminSeed.Email,
                EmailConfirmed = true
            };
            Ensure(await users.CreateAsync(user, options.AdminSeed.Password));
            Ensure(await users.AddToRoleAsync(user, "Admin"));
            await transaction.CommitAsync();
            logger.LogInformation("Configured admin account provisioned.");
        });
    }

    private static void Ensure(IdentityResult result)
    {
        if (!result.Succeeded)
        {
            // Codes identify the failing rule without including any configured credential.
            throw new InvalidOperationException($"Admin seed failed: {string.Join(", ", result.Errors.Select(error => error.Code))}.");
        }
    }
}
