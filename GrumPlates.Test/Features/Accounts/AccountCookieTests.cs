using System.Security.Claims;
using GrumPlates.Core.Features.Accounts.Contracts;
using GrumPlates.Infrastructure.Persistence;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Test.Features.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountCookieTests
{
    [Theory]
    [InlineData(false, 8)]
    [InlineData(true, 336)]
    public async Task RealLogin_CookieFlagsAndFixedExpirySurviveStampAndRoleRefresh(bool rememberMe, int hours)
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using var denied = await client.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.Unauthorized, denied.StatusCode);
        var user = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, user.Email, user.Password, rememberMe);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        using (var keyScope = fixture.Factory.Services.CreateScope())
        {
            var db = keyScope.ServiceProvider.GetRequiredService<AppDbContext>();
            var storedKeys = await db.DataProtectionKeys.AsNoTracking().ToListAsync();
            Assert.NotEmpty(storedKeys);
            Assert.All(storedKeys, key => Assert.Contains("encryptedSecret", key.Xml, StringComparison.Ordinal));
        }
        var cookie = ApplicationCookie(login);
        Assert.True(cookie.Secure);
        Assert.True(cookie.HttpOnly);
        Assert.Equal(SameSiteMode.Lax, cookie.SameSite);
        Assert.Equal("/", cookie.Path.ToString());
        Assert.False(cookie.Domain.HasValue);
        Assert.Equal(rememberMe, cookie.Expires.HasValue);
        var expectedExpiry = fixture.Clock.GetUtcNow().AddHours(hours);
        var options = fixture.Factory.Services.GetRequiredService<IOptionsMonitor<CookieAuthenticationOptions>>().Get(IdentityConstants.ApplicationScheme);
        Assert.False(options.SlidingExpiration);
        var ticket = options.TicketDataFormat.Unprotect(cookie.Value.ToString());
        Assert.NotNull(ticket);
        Assert.Equal(expectedExpiry, ticket.Properties.ExpiresUtc);

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var roles = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
            Assert.True((await roles.CreateAsync(new IdentityRole("FixtureRole"))).Succeeded);
            Assert.True((await users.AddToRoleAsync((await users.FindByIdAsync(user.Id))!, "FixtureRole")).Succeeded);
        }
        fixture.Clock.Advance(TimeSpan.FromHours(1));
        using var refresh = await client.GetAsync("/api/auth/session");
        Assert.True(refresh.Headers.CacheControl?.Private ?? false, $"Cache-Control was '{refresh.Headers.CacheControl}'.");
        Assert.True(refresh.Headers.CacheControl?.NoStore ?? false);
        var session = await refresh.Content.ReadFromJsonAsync<AccountSession>();
        Assert.Equal(user.Id, session?.User?.Id);
        Assert.Contains("FixtureRole", session!.User!.Roles);
        var renewed = options.TicketDataFormat.Unprotect(ApplicationCookie(refresh).Value.ToString());
        Assert.NotNull(renewed);
        Assert.Equal(expectedExpiry, renewed.Properties.ExpiresUtc);
        fixture.Clock.Advance(TimeSpan.FromHours(hours - 1).Add(TimeSpan.FromSeconds(1)));
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using var expired = await client.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.Unauthorized, expired.StatusCode);
    }

    [Fact]
    public async Task CookieSigningIn_GivesBlazorRememberMeFourteenDaysAndPreservesExplicitExpiry()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var options = fixture.Factory.Services.GetRequiredService<IOptionsMonitor<CookieAuthenticationOptions>>()
            .Get(IdentityConstants.ApplicationScheme);
        var issuedUtc = fixture.Clock.GetUtcNow();
        var scheme = new AuthenticationScheme(IdentityConstants.ApplicationScheme, IdentityConstants.ApplicationScheme, typeof(CookieAuthenticationHandler));

        var properties = new AuthenticationProperties
        {
            IsPersistent = true,
            IssuedUtc = issuedUtc,
            ExpiresUtc = issuedUtc.Add(options.ExpireTimeSpan)
        };
        var context = new CookieSigningInContext(new Microsoft.AspNetCore.Http.DefaultHttpContext(), scheme, options,
            new ClaimsPrincipal(new ClaimsIdentity()), properties, new Microsoft.AspNetCore.Http.CookieOptions());
        await options.Events.SigningIn(context);
        Assert.Equal(issuedUtc.AddDays(14), properties.ExpiresUtc);
        Assert.False(properties.AllowRefresh);

        var explicitExpiry = new AuthenticationProperties
        {
            IsPersistent = true,
            IssuedUtc = issuedUtc,
            ExpiresUtc = issuedUtc.AddDays(14)
        };
        var explicitContext = new CookieSigningInContext(new Microsoft.AspNetCore.Http.DefaultHttpContext(), scheme, options,
            new ClaimsPrincipal(new ClaimsIdentity()), explicitExpiry, new Microsoft.AspNetCore.Http.CookieOptions());
        await options.Events.SigningIn(explicitContext);
        Assert.Equal(issuedUtc.AddDays(14), explicitExpiry.ExpiresUtc);
        Assert.Null(explicitExpiry.AllowRefresh);
    }

    [Fact]
    public async Task RealLogin_StampRevocationRejectsBothIndependentCookieJars()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var first = fixture.CreateClient();
        using var second = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        using var firstLogin = await RealCookieAccountFixture.LoginAsync(first, user.Email, user.Password);
        using var secondLogin = await RealCookieAccountFixture.LoginAsync(second, user.Email, user.Password);
        Assert.Equal(HttpStatusCode.OK, firstLogin.StatusCode);
        Assert.Equal(HttpStatusCode.OK, secondLogin.StatusCode);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            Assert.True((await users.UpdateSecurityStampAsync((await users.FindByIdAsync(user.Id))!)).Succeeded);
        }
        fixture.Clock.Advance(TimeSpan.FromSeconds(1));
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(first)).User);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(second)).User);
    }

    [Fact]
    public async Task RealLogin_UsesGenericFailureForUnknownWrongUnconfirmedAndUnsupportedAccounts()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var confirmed = await fixture.CreateUserAsync();
        var unconfirmed = await fixture.CreateUserAsync(confirmed: false);
        var stronger = await fixture.CreateUserAsync();
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            Assert.True((await users.SetTwoFactorEnabledAsync((await users.FindByIdAsync(stronger.Id))!, true)).Succeeded);
        }
        string? failureBody = null;
        foreach (var (email, password) in new[]
        {
            ($"{Guid.NewGuid():N}@example.test", confirmed.Password),
            (confirmed.Email, unconfirmed.Password),
            (unconfirmed.Email, unconfirmed.Password),
            (stronger.Email, stronger.Password)
        })
        {
            using var response = await RealCookieAccountFixture.LoginAsync(client, email, password);
            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
            var problem = System.Text.Json.Nodes.JsonNode.Parse(await response.Content.ReadAsStringAsync())!.AsObject();
            problem.Remove("traceId");
            var body = problem.ToJsonString();
            failureBody ??= body;
            Assert.Equal(failureBody, body);
            Assert.False(response.Headers.TryGetValues("Set-Cookie", out var cookies) && cookies.Any(value => value.StartsWith("__Host-Accounts-", StringComparison.Ordinal)));
        }
    }

    [Fact]
    public async Task RealLogin_LocksOutAfterFiveFailuresWithTheSameGenericFailure()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        string? failureBody = null;

        for (var attempt = 0; attempt < 5; attempt++)
        {
            using var failed = await RealCookieAccountFixture.LoginAsync(client, user.Email, "incorrect password");
            Assert.Equal(HttpStatusCode.Unauthorized, failed.StatusCode);
            var body = await ReadSafeProblemAsync(failed);
            failureBody ??= body;
            Assert.Equal(failureBody, body);
        }

        using (var locked = await RealCookieAccountFixture.LoginAsync(client, user.Email, user.Password))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, locked.StatusCode);
            Assert.Equal(failureBody, await ReadSafeProblemAsync(locked));
        }

        using var scope = fixture.Factory.Services.CreateScope();
        var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var lockedUser = await users.FindByIdAsync(user.Id);
        Assert.NotNull(lockedUser?.LockoutEnd);
        var remainingLockout = lockedUser!.LockoutEnd!.Value - DateTimeOffset.UtcNow;
        Assert.InRange(remainingLockout, TimeSpan.FromMinutes(14), TimeSpan.FromMinutes(15));
    }

    [Fact]
    public async Task RealLogoutAll_RequiresCurrentPasswordAndRevokesBothCookieJars()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var first = fixture.CreateClient();
        using var second = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        using var firstLogin = await RealCookieAccountFixture.LoginAsync(first, user.Email, user.Password);
        using var secondLogin = await RealCookieAccountFixture.LoginAsync(second, user.Email, user.Password);
        Assert.Equal(HttpStatusCode.OK, firstLogin.StatusCode);
        Assert.Equal(HttpStatusCode.OK, secondLogin.StatusCode);
        var firstSession = await RealCookieAccountFixture.ReadSessionAsync(first);
        var secondSession = await RealCookieAccountFixture.ReadSessionAsync(second);

        using (var rejected = await LogoutAllAsync(first, user.Id, firstSession.CsrfToken, "wrong password"))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, rejected.StatusCode);
            using var problem = System.Text.Json.JsonDocument.Parse(await rejected.Content.ReadAsStringAsync());
            Assert.Equal("CredentialsInvalid", problem.RootElement.GetProperty("code").GetString());
        }
        Assert.Equal(user.Id, (await RealCookieAccountFixture.ReadSessionAsync(first)).User?.Id);
        Assert.Equal(user.Id, (await RealCookieAccountFixture.ReadSessionAsync(second)).User?.Id);

        using var revoked = await LogoutAllAsync(first, user.Id, firstSession.CsrfToken, user.Password);
        Assert.Equal(HttpStatusCode.OK, revoked.StatusCode);
        fixture.Clock.Advance(TimeSpan.FromSeconds(1));
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(first)).User);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(second)).User);
        Assert.NotEqual(firstSession.CsrfToken, secondSession.CsrfToken);
    }

    [Fact]
    public async Task RealChangePassword_RequiresFreshProofAndRevokesBothCookieJars()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var first = fixture.CreateClient();
        using var second = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        using var firstLogin = await RealCookieAccountFixture.LoginAsync(first, user.Email, user.Password);
        using var secondLogin = await RealCookieAccountFixture.LoginAsync(second, user.Email, user.Password);
        Assert.Equal(HttpStatusCode.OK, firstLogin.StatusCode);
        Assert.Equal(HttpStatusCode.OK, secondLogin.StatusCode);
        var firstSession = await RealCookieAccountFixture.ReadSessionAsync(first);
        var secondSession = await RealCookieAccountFixture.ReadSessionAsync(second);

        using (var rejected = await ChangePasswordAsync(first, user.Id, firstSession.CsrfToken, "wrong current password", NewPassword()))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, rejected.StatusCode);
            using var problem = System.Text.Json.JsonDocument.Parse(await rejected.Content.ReadAsStringAsync());
            Assert.Equal("CredentialsInvalid", problem.RootElement.GetProperty("code").GetString());
        }
        Assert.Equal(user.Id, (await RealCookieAccountFixture.ReadSessionAsync(first)).User?.Id);

        using (var rejectedPolicy = await ChangePasswordAsync(first, user.Id, firstSession.CsrfToken, user.Password, user.Email))
        {
            Assert.Equal(HttpStatusCode.BadRequest, rejectedPolicy.StatusCode);
            using var problem = System.Text.Json.JsonDocument.Parse(await rejectedPolicy.Content.ReadAsStringAsync());
            Assert.Equal("PasswordRejected", problem.RootElement.GetProperty("code").GetString());
            Assert.True(problem.RootElement.GetProperty("errors").TryGetProperty("newPassword", out _));
        }
        Assert.Equal(user.Id, (await RealCookieAccountFixture.ReadSessionAsync(first)).User?.Id);

        var newPassword = NewPassword();
        using var changed = await ChangePasswordAsync(first, user.Id, firstSession.CsrfToken, user.Password, newPassword);
        Assert.Equal(HttpStatusCode.OK, changed.StatusCode);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(first)).User);
        fixture.Clock.Advance(TimeSpan.FromSeconds(1));
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(second)).User);
        using (var expired = await ChangePasswordAsync(
            second, user.Id, secondSession.CsrfToken, user.Password, NewPassword()))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, expired.StatusCode);
            using var problem = System.Text.Json.JsonDocument.Parse(await expired.Content.ReadAsStringAsync());
            Assert.Equal("AuthenticationRequired", problem.RootElement.GetProperty("code").GetString());
        }

        using var fresh = fixture.CreateClient();
        using (var oldPassword = await RealCookieAccountFixture.LoginAsync(fresh, user.Email, user.Password))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, oldPassword.StatusCode);
            using var problem = System.Text.Json.JsonDocument.Parse(await oldPassword.Content.ReadAsStringAsync());
            Assert.Equal("CredentialsInvalid", problem.RootElement.GetProperty("code").GetString());
        }
        using var newPasswordLogin = await RealCookieAccountFixture.LoginAsync(fresh, user.Email, newPassword);
        Assert.Equal(HttpStatusCode.OK, newPasswordLogin.StatusCode);
    }

    [Fact]
    public async Task RealChangePassword_VerifiesLostCommitAcknowledgementWithoutRepeatingCredentialFailure()
    {
        var interceptor = new CommitUncertaintyInterceptor();
        await using var fixture = new RealCookieAccountFixture(
            configureTestServices: services => services.AddSingleton<IDbTransactionInterceptor>(interceptor));
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, user.Email, user.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        var newPassword = NewPassword();
        interceptor.ThrowAfterNextCommit();

        using var changed = await ChangePasswordAsync(client, user.Id, session.CsrfToken, user.Password, newPassword);

        Assert.Equal(HttpStatusCode.OK, changed.StatusCode);
        Assert.Equal(1, interceptor.ThrownCount);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var stored = await users.FindByIdAsync(user.Id);
            Assert.NotNull(stored);
            Assert.Equal(0, await users.GetAccessFailedCountAsync(stored));
        }
        using var fresh = fixture.CreateClient();
        using var newPasswordLogin = await RealCookieAccountFixture.LoginAsync(fresh, user.Email, newPassword);
        Assert.Equal(HttpStatusCode.OK, newPasswordLogin.StatusCode);
    }

    [Theory]
    [InlineData("/api/auth/logout-all")]
    [InlineData("/api/auth/change-password")]
    [InlineData("/api/auth/export")]
    [InlineData("/api/auth/delete")]
    public async Task SensitiveMutation_RetryRevalidatesCredentialsAndDoesNotReuseRolledBackSuccess(string path)
    {
        var interceptor = new AccountRetryInterceptor();
        await using var fixture = new RealCookieAccountFixture(
            configureTestServices: services => services.AddSingleton<IDbTransactionInterceptor>(interceptor));
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, user.Email, user.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        var replacementPassword = NewPassword();
        string? replacementStamp = null;
        interceptor.RollBackNextCommit(async () =>
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var stored = await users.FindByIdAsync(user.Id);
            Assert.NotNull(stored);
            var token = await users.GeneratePasswordResetTokenAsync(stored);
            Assert.True((await users.ResetPasswordAsync(stored, token, replacementPassword)).Succeeded);
            replacementStamp = stored.SecurityStamp;
        });
        using var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = JsonContent.Create(new { password = user.Password, newPassword = NewPassword() })
        };
        request.Headers.Add("X-Expected-User", user.Id);
        request.Headers.Add("X-CSRF-TOKEN", session.CsrfToken);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        using var problem = System.Text.Json.JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal("AuthenticationRequired", problem.RootElement.GetProperty("code").GetString());
        Assert.Equal(1, interceptor.RetriedCount);
        using var verificationScope = fixture.Factory.Services.CreateScope();
        var verificationUsers = verificationScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var remaining = await verificationUsers.FindByIdAsync(user.Id);
        Assert.NotNull(remaining);
        Assert.Equal(replacementStamp, remaining.SecurityStamp);
        Assert.True(await verificationUsers.CheckPasswordAsync(remaining, replacementPassword));
        Assert.Equal(0, await verificationUsers.GetAccessFailedCountAsync(remaining));
    }

    private static async Task<string> ReadSafeProblemAsync(HttpResponseMessage response)
    {
        var problem = System.Text.Json.Nodes.JsonNode.Parse(await response.Content.ReadAsStringAsync())!.AsObject();
        problem.Remove("traceId");
        return problem.ToJsonString();
    }

    private static async Task<HttpResponseMessage> LogoutAllAsync(HttpClient client, string userId, string csrfToken, string password)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/auth/logout-all")
        {
            Content = JsonContent.Create(new { password })
        };
        request.Headers.Add("X-Expected-User", userId);
        request.Headers.Add("X-CSRF-TOKEN", csrfToken);
        return await client.SendAsync(request);
    }

    private static async Task<HttpResponseMessage> ChangePasswordAsync(
        HttpClient client,
        string userId,
        string csrfToken,
        string currentPassword,
        string newPassword)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/auth/change-password")
        {
            Content = JsonContent.Create(new { password = currentPassword, newPassword })
        };
        request.Headers.Add("X-Expected-User", userId);
        request.Headers.Add("X-CSRF-TOKEN", csrfToken);
        return await client.SendAsync(request);
    }

    private static string NewPassword() => $"Updated account phrase {Guid.NewGuid():N}";

    private static SetCookieHeaderValue ApplicationCookie(HttpResponseMessage response) =>
        SetCookieHeaderValue.Parse(Assert.Single(response.Headers.GetValues("Set-Cookie"),
            value => value.StartsWith("__Host-Accounts-", StringComparison.Ordinal)));
}
