using System.Security.Claims;
using BlazorAutoApp.Features.Login;
using Microsoft.AspNetCore.Http;
using Xunit;

namespace BlazorAutoApp.Test.Features.Login;

public sealed class HttpPrincipalCurrentUserAccessorTests
{
    [Theory]
    [InlineData(ClaimTypes.NameIdentifier, "name-id")]
    [InlineData("sub", "subject-id")]
    public async Task GetCurrentUserIdAsync_UsesAuthenticatedPrincipalIdClaim(string claimType, string expectedId)
    {
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim(claimType, expectedId)],
                authenticationType: "test"))
        };
        var accessor = new HttpPrincipalCurrentUserAccessor(new HttpContextAccessor { HttpContext = context });

        var userId = await accessor.GetCurrentUserIdAsync();

        Assert.Equal(expectedId, userId);
    }

    [Fact]
    public async Task GetCurrentUserIdAsync_IgnoresIdentityClaimsWhenPrincipalIsUnauthenticated()
    {
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity([new Claim(ClaimTypes.NameIdentifier, "client-id")]))
        };
        var accessor = new HttpPrincipalCurrentUserAccessor(new HttpContextAccessor { HttpContext = context });

        var userId = await accessor.GetCurrentUserIdAsync();

        Assert.Null(userId);
    }

    [Fact]
    public async Task GetCurrentUserIdAsync_ReturnsNullWhenNoHttpRequestExists()
    {
        var accessor = new HttpPrincipalCurrentUserAccessor(new HttpContextAccessor());

        var userId = await accessor.GetCurrentUserIdAsync();

        Assert.Null(userId);
    }

    [Fact]
    public async Task GetRequiredUserIdAsync_ThrowsWhenPrincipalHasNoAuthenticatedId()
    {
        var accessor = new HttpPrincipalCurrentUserAccessor(new HttpContextAccessor());

        await Assert.ThrowsAsync<UnauthorizedAccessException>(async () =>
        {
            await accessor.GetRequiredUserIdAsync();
        });
    }
}
