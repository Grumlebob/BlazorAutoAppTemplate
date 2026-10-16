using System.Net;
using System.Security.Claims;
using System.Text.RegularExpressions;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Accounts;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;

namespace BlazorAutoApp.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
[Trait("FrontendProfile", "BlazorAuto")]
public sealed class BlazorExternalAccountCompatibilityTests
{
    [Theory]
    [InlineData(false, false)]
    [InlineData(true, false)]
    [InlineData(false, true)]
    public async Task ExistingExternalLogin_UsesRealIdentityAndPreservesTwoFactorAndPasswordSetup(bool twoFactor, bool passwordless)
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync();
        var providerKey = Guid.NewGuid().ToString("N");
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.True((await users.AddLoginAsync(user, new UserLoginInfo("FixtureExternal", providerKey, "Fixture external"))).Succeeded);
            if (passwordless) Assert.True((await users.RemovePasswordAsync(user)).Succeeded);
            if (twoFactor)
            {
                Assert.True((await users.ResetAuthenticatorKeyAsync(user)).Succeeded);
                Assert.True((await users.SetTwoFactorEnabledAsync(user, true)).Succeeded);
            }
        }
        using var client = fixture.CreateClient();
        SupplyExternalProviderCookie(fixture, client, providerKey, account.Email);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using var anonymousBooks = await client.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.Unauthorized, anonymousBooks.StatusCode);

        using var callback = await client.GetAsync("/Account/ExternalLogin?Action=LoginCallback&ReturnUrl=%2FAccount%2FManage");

        Assert.Equal(HttpStatusCode.Redirect, callback.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        if (twoFactor)
        {
            Assert.Contains("/Account/LoginWith2fa", callback.Headers.Location?.OriginalString, StringComparison.Ordinal);
            Assert.Null(session.User);
            using var challenge = await client.GetAsync(callback.Headers.Location);
            Assert.Equal(HttpStatusCode.OK, challenge.StatusCode);
            return;
        }
        Assert.Equal(account.Id, session.User?.Id);
        Assert.True(callback.Headers.TryGetValues("Set-Cookie", out var cookies)
            && cookies.Any(value => value.StartsWith("__Host-Accounts-", StringComparison.Ordinal)));
        if (!passwordless) return;

        using var passwordPage = await client.GetAsync("/Account/Manage/SetPassword");
        Assert.Equal(HttpStatusCode.OK, passwordPage.StatusCode);
        var fields = ReadHiddenInputs(await passwordPage.Content.ReadAsStringAsync());
        var newPassword = $"External account password {Guid.NewGuid():N}";
        fields["Input.NewPassword"] = newPassword;
        fields["Input.ConfirmPassword"] = newPassword;
        using var passwordSet = await client.PostAsync("/Account/Manage/SetPassword", new FormUrlEncodedContent(fields));
        Assert.Equal(HttpStatusCode.Redirect, passwordSet.StatusCode);
        using var freshClient = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(freshClient, account.Email, newPassword);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task UnknownExternalLogin_CannotBypassEmailFirstRegistrationOrCreateOnCallbackGet(bool registrationEnabled)
    {
        var settings = registrationEnabled ? new Dictionary<string, string?>
        {
            ["Accounts:RegistrationEnabled"] = "true",
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = "1",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        } : null;
        await using var fixture = new RealCookieAccountFixture(settings);
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var email = $"external-{Guid.NewGuid():N}@example.test";
        SupplyExternalProviderCookie(fixture, client, Guid.NewGuid().ToString("N"), email);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        var expectedDestination = registrationEnabled ? "/Account/Register" : "/Account/Login";

        using var callback = await client.GetAsync("/Account/ExternalLogin?Action=LoginCallback");
        Assert.Equal(HttpStatusCode.Redirect, callback.StatusCode);
        Assert.Contains(expectedDestination, callback.Headers.Location?.OriginalString, StringComparison.Ordinal);
        using var request = new HttpRequestMessage(HttpMethod.Post, "/Account/ExternalLogin")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["_handler"] = "confirmation",
                ["Input.Email"] = email
            })
        };
        request.Headers.Add("X-CSRF-TOKEN", session.CsrfToken);
        using var directPost = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.Redirect, directPost.StatusCode);
        Assert.Contains(expectedDestination, directPost.Headers.Location?.OriginalString, StringComparison.Ordinal);
        using var verification = fixture.Factory.Services.CreateScope();
        var db = verification.ServiceProvider.GetRequiredService<AppDbContext>();
        Assert.False(await db.Users.AnyAsync());
        Assert.False(await db.UserLogins.AnyAsync());
        Assert.False(await db.AccountOutbox.AnyAsync());
    }

    private static void SupplyExternalProviderCookie(RealCookieAccountFixture fixture, HttpClient client, string providerKey, string email)
    {
        // Only the upstream-provider cookie is synthetic. The application principal
        // remains anonymous until production SignInManager resolves a stored login.
        var options = fixture.Factory.Services.GetRequiredService<IOptionsMonitor<CookieAuthenticationOptions>>()
            .Get(IdentityConstants.ExternalScheme);
        var identity = new ClaimsIdentity([
            new Claim(ClaimTypes.NameIdentifier, providerKey),
            new Claim(ClaimTypes.Email, email)
        ], "FixtureExternal");
        var properties = new AuthenticationProperties
        {
            IssuedUtc = fixture.Clock.GetUtcNow(),
            ExpiresUtc = fixture.Clock.GetUtcNow().AddMinutes(5)
        };
        properties.Items["LoginProvider"] = "FixtureExternal";
        var ticket = new AuthenticationTicket(new ClaimsPrincipal(identity), properties, IdentityConstants.ExternalScheme);
        client.DefaultRequestHeaders.Add("Cookie", $"{options.Cookie.Name}={options.TicketDataFormat.Protect(ticket)}");
    }

    private static Dictionary<string, string> ReadHiddenInputs(string html)
    {
        var fields = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (Match input in Regex.Matches(html, "<input\\b[^>]*\\btype=\"hidden\"[^>]*>", RegexOptions.IgnoreCase | RegexOptions.Singleline))
        {
            var name = Regex.Match(input.Value, "\\bname=\"([^\"]*)\"", RegexOptions.IgnoreCase);
            var value = Regex.Match(input.Value, "\\bvalue=\"([^\"]*)\"", RegexOptions.IgnoreCase);
            if (name.Success) fields[WebUtility.HtmlDecode(name.Groups[1].Value)] = value.Success ? WebUtility.HtmlDecode(value.Groups[1].Value) : "";
        }
        return fields;
    }
}
