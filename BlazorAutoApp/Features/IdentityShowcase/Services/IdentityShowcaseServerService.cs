using System.Security.Claims;
using BlazorAutoApp.Core.Features.IdentityShowcase.Contracts;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetIdentityShowcaseAdminProbe;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetPublicIdentityShowcase;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetSecureIdentityShowcase;

namespace BlazorAutoApp.Features.IdentityShowcase.Services;

public class IdentityShowcaseServerService(IHttpContextAccessor httpContextAccessor) : IIdentityShowcaseApi
{
    private const string AdminRole = "Admin";
    private const string ViewerRole = "Viewer";

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
            HasAnyRole = roles.Length > 0,
            IsAdmin = roles.Contains(AdminRole, StringComparer.Ordinal),
            IsViewer = roles.Contains(ViewerRole, StringComparer.Ordinal),
            Roles = roles,
            ServerTimeUtc = DateTimeOffset.UtcNow
        });
    }

    public Task<IdentityShowcaseAdminProbeResponse> GetAdminProbeAsync(CancellationToken ct = default)
    {
        var user = httpContextAccessor.HttpContext?.User;
        var roles = user?.Claims
            .Where(c => c.Type is ClaimTypes.Role or "role" or "roles")
            .Select(c => c.Value)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(v => v, StringComparer.Ordinal)
            .ToArray() ?? [];

        return Task.FromResult(new IdentityShowcaseAdminProbeResponse
        {
            Success = true,
            Message = "Admin role probe passed. You can access admin-only endpoints.",
            Roles = roles,
            ServerTimeUtc = DateTimeOffset.UtcNow
        });
    }
}
