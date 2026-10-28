using GrumPlates.Features.Login.Account;
using GrumPlates.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;

namespace GrumPlates.Test.Features.Books.TestData;

internal static class BookTestUsers
{
    public const string DefaultUserId = "integration-user@example.test";
    public const string OtherUserId = "other-user@example.test";

    public static async Task EnsureAsync(AppDbContext db, params string[] userIds)
    {
        foreach (var userId in userIds.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (await db.Users.AnyAsync(user => user.Id == userId))
            {
                continue;
            }

            var normalized = userId.ToUpperInvariant();
            db.Users.Add(new ApplicationUser
            {
                Id = userId,
                UserName = userId,
                NormalizedUserName = normalized,
                Email = userId,
                NormalizedEmail = normalized,
                EmailConfirmed = true,
                SecurityStamp = Guid.NewGuid().ToString("N"),
                ConcurrencyStamp = Guid.NewGuid().ToString("N")
            });
        }
    }
}
