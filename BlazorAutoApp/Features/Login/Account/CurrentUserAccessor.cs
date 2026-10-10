using System.Security.Claims;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.AspNetCore.Identity;
using BlazorAutoApp.Features.Login;

namespace BlazorAutoApp.Features.Login.Account;

internal sealed class BlazorCurrentUserAccessor(
    IHttpContextAccessor httpContextAccessor,
    IEnumerable<AuthenticationStateProvider> authenticationStateProviders,
    UserManager<ApplicationUser> userManager) : ICurrentUserAccessor
{
    private readonly AuthenticationStateProvider? _authenticationStateProvider = authenticationStateProviders.FirstOrDefault();

    public async ValueTask<string?> GetCurrentUserIdAsync(CancellationToken cancellationToken = default)
    {
        var httpContext = httpContextAccessor.HttpContext;
        var principal = httpContext?.User;
        var userId = GetUserId(principal);
        if (string.IsNullOrWhiteSpace(userId)
            && httpContext is null
            && _authenticationStateProvider is not null)
        {
            var authenticationState = await _authenticationStateProvider.GetAuthenticationStateAsync();
            principal = authenticationState.User;
            userId = GetUserId(principal);
        }

        if (string.IsNullOrWhiteSpace(userId))
        {
            userId = await ResolveUserIdByNameAsync(principal);
        }

        return userId;
    }

    public async ValueTask<string> GetRequiredUserIdAsync(CancellationToken cancellationToken = default)
    {
        var userId = await GetCurrentUserIdAsync(cancellationToken);
        return string.IsNullOrWhiteSpace(userId)
            ? throw new UnauthorizedAccessException("An authenticated user is required.")
            : userId;
    }

    private static string? GetUserId(ClaimsPrincipal? user)
    {
        if (user?.Identity?.IsAuthenticated != true)
        {
            return null;
        }

        return user.FindFirstValue(ClaimTypes.NameIdentifier) ??
               user.FindFirstValue("sub");
    }

    private async Task<string?> ResolveUserIdByNameAsync(ClaimsPrincipal? user)
    {
        if (user?.Identity?.IsAuthenticated != true)
        {
            return null;
        }

        var userName = user.FindFirstValue(ClaimTypes.Name) ?? user.Identity.Name;
        if (string.IsNullOrWhiteSpace(userName))
        {
            return null;
        }

        var identityUser = await userManager.FindByNameAsync(userName) ??
                           await userManager.FindByEmailAsync(userName);
        return identityUser?.Id;
    }
}
