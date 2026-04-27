using System.Security.Claims;
using BlazorAutoApp.Core.Features.IdentityShowcase;

namespace BlazorAutoApp.Features.IdentityShowcase;

public class IdentityShowcaseServerService(IHttpContextAccessor httpContextAccessor) : IIdentityShowcaseApi
{
    public Task<IdentityShowcasePublicInfo> GetPublicAsync(CancellationToken ct = default)
    {
        return Task.FromResult(new IdentityShowcasePublicInfo
        {
            AppName = "BlazorAutoApp",
            Message = "Identity showcase is active. Public endpoint is reachable.",
            ServerTimeUtc = DateTimeOffset.UtcNow
        });
    }

    public Task<IdentityShowcaseSecureInfo?> GetSecureAsync(CancellationToken ct = default)
    {
        var user = httpContextAccessor.HttpContext?.User;
        if (user?.Identity?.IsAuthenticated != true)
        {
            return Task.FromResult<IdentityShowcaseSecureInfo?>(null);
        }

        var roles = user.Claims
            .Where(c => c.Type is ClaimTypes.Role or "role" or "roles")
            .Select(c => c.Value)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(v => v, StringComparer.Ordinal)
            .ToArray();

        var userId =
            user.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? user.FindFirstValue("sub")
            ?? user.FindFirstValue("userid")
            ?? "";

        return Task.FromResult<IdentityShowcaseSecureInfo?>(new IdentityShowcaseSecureInfo
        {
            IsAuthenticated = true,
            UserName = user.Identity?.Name ?? "Authenticated user",
            UserId = userId,
            AuthenticationType = user.Identity?.AuthenticationType ?? "Unknown",
            ClaimCount = user.Claims.Count(),
            Roles = roles,
            ServerTimeUtc = DateTimeOffset.UtcNow
        });
    }
}
