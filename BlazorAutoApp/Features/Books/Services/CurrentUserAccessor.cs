using System.Security.Claims;

namespace BlazorAutoApp.Features.Books.Services;

internal interface ICurrentUserAccessor
{
    string GetRequiredUserId();
}

internal sealed class CurrentUserAccessor(IHttpContextAccessor httpContextAccessor) : ICurrentUserAccessor
{
    public string GetRequiredUserId()
    {
        var userId = httpContextAccessor.HttpContext?.User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (string.IsNullOrWhiteSpace(userId))
        {
            throw new UnauthorizedAccessException("An authenticated user is required for user books.");
        }

        return userId;
    }
}
