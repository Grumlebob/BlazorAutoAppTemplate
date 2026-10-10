using System.Security.Claims;

namespace BlazorAutoApp.Features.Login;

internal sealed class HttpPrincipalCurrentUserAccessor(IHttpContextAccessor httpContextAccessor) : ICurrentUserAccessor
{
    public ValueTask<string?> GetCurrentUserIdAsync(CancellationToken cancellationToken = default)
    {
        var principal = httpContextAccessor.HttpContext?.User;
        if (principal?.Identity?.IsAuthenticated != true)
        {
            return ValueTask.FromResult<string?>(null);
        }

        var userId = principal.FindFirstValue(ClaimTypes.NameIdentifier) ?? principal.FindFirstValue("sub");
        return ValueTask.FromResult(string.IsNullOrWhiteSpace(userId) ? null : userId);
    }

    public async ValueTask<string> GetRequiredUserIdAsync(CancellationToken cancellationToken = default)
    {
        var userId = await GetCurrentUserIdAsync(cancellationToken);
        return string.IsNullOrWhiteSpace(userId)
            ? throw new UnauthorizedAccessException("An authenticated user is required.")
            : userId;
    }
}
