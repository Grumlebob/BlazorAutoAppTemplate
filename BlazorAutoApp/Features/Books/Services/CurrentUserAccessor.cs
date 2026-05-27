using System.Security.Claims;
using BlazorAutoApp.Features.Login.Account;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.AspNetCore.Identity;

namespace BlazorAutoApp.Features.Books.Services;

internal interface ICurrentUserAccessor
{
    ValueTask<string> GetRequiredUserIdAsync(CancellationToken cancellationToken = default);
}

internal sealed class CurrentUserAccessor(
    IHttpContextAccessor httpContextAccessor,
    IEnumerable<AuthenticationStateProvider> authenticationStateProviders,
    UserManager<ApplicationUser> userManager) : ICurrentUserAccessor
{
    private readonly AuthenticationStateProvider? _authenticationStateProvider = authenticationStateProviders.FirstOrDefault();

    public async ValueTask<string> GetRequiredUserIdAsync(CancellationToken cancellationToken = default)
    {
        var principal = httpContextAccessor.HttpContext?.User;
        var userId = GetUserId(principal);
        if (string.IsNullOrWhiteSpace(userId))
        {
            // Interactive component calls may not have a useful HttpContext principal.
            if (_authenticationStateProvider is not null)
            {
                var authenticationState = await _authenticationStateProvider.GetAuthenticationStateAsync();
                principal = authenticationState.User;
                userId = GetUserId(principal);
            }
        }

        if (string.IsNullOrWhiteSpace(userId))
        {
            userId = await ResolveUserIdByNameAsync(principal);
        }

        return string.IsNullOrWhiteSpace(userId)
            ? throw new UnauthorizedAccessException("An authenticated user is required for user books.")
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
