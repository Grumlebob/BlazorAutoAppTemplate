using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts.Email;
using BlazorAutoApp.Test.TestSupport.Accounts;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Xunit;

namespace BlazorAutoApp.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountEmailChangeTests
{
    [Fact]
    public async Task EmailChange_QueuesProofThenAtomicallyUpdatesEmailUsernameAndStamp()
    {
        await using var fixture = NewEmailFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var account = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        using var proofClientA = fixture.CreateClient();
        using var proofClientB = fixture.CreateClient();
        var proofSessionA = await RealCookieAccountFixture.ReadSessionAsync(proofClientA);
        var proofSessionB = await RealCookieAccountFixture.ReadSessionAsync(proofClientB);
        var targetEmail = $"changed-{Guid.NewGuid():N}@example.test";
        var supersededEmail = $"superseded-{Guid.NewGuid():N}@example.test";

        using var request = await ChangeEmailAsync(client, account.Id, session.CsrfToken, account.Password, targetEmail);
        Assert.Equal(HttpStatusCode.Accepted, request.StatusCode);
        Assert.Equal("Request received. If this change can proceed, check the new address for a confirmation message.", await ReadMessageAsync(request));
        await fixture.Factory.Services.GetRequiredService<BlockingAccountMailTransport>().Started.Task.WaitAsync(TimeSpan.FromSeconds(10));

        AccountMailPayload payload;
        string supersededToken;
        string originalStamp;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var protector = scope.ServiceProvider.GetRequiredService<AccountMailPayloadProtector>();
            var db = scope.ServiceProvider.GetRequiredService<BlazorAutoApp.Infrastructure.Persistence.AppDbContext>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            originalStamp = user.SecurityStamp!;
            Assert.Equal(account.Email, user.Email);
            Assert.Equal(account.Email, user.UserName);
            payload = protector.Unprotect((await db.AccountOutbox.SingleAsync()).ProtectedPayload);
            Assert.Equal(targetEmail, payload.TargetEmail);
            Assert.Equal(targetEmail, payload.Recipient);
            supersededToken = await users.GenerateChangeEmailTokenAsync(user, supersededEmail);
        }

        using (var getProof = await client.GetAsync(
            $"/api/auth/confirm-email-change?userId={Uri.EscapeDataString(payload.UserId)}&email={Uri.EscapeDataString(targetEmail)}&token={Uri.EscapeDataString(payload.Token)}"))
        {
            Assert.Equal(HttpStatusCode.MethodNotAllowed, getProof.StatusCode);
            var body = await getProof.Content.ReadAsStringAsync();
            var headers = $"{getProof.Headers}{getProof.Content.Headers}Body: {body}";
            var hasAllow = getProof.Headers.NonValidated.TryGetValues("Allow", out var allowValues)
                || getProof.Content.Headers.NonValidated.TryGetValues("Allow", out allowValues);
            Assert.True(hasAllow, headers);
            Assert.Equal("POST", Assert.Single(allowValues!));
            using var problem = JsonDocument.Parse(body);
            Assert.Equal("MethodNotAllowed", problem.RootElement.GetProperty("code").GetString());
        }
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var user = await scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.Equal(account.Email, user.Email);
            Assert.Equal(originalStamp, user.SecurityStamp);
        }

        var confirmations = await Task.WhenAll(
            ConfirmEmailChangeAsync(proofClientA, proofSessionA.CsrfToken, account.Id, targetEmail, payload.Token),
            ConfirmEmailChangeAsync(proofClientB, proofSessionB.CsrfToken, account.Id, supersededEmail, supersededToken));
        try
        {
            Assert.Single(confirmations, response => response.StatusCode == HttpStatusCode.OK);
            Assert.Single(confirmations, response => response.StatusCode == HttpStatusCode.BadRequest);
        }
        finally
        {
            foreach (var response in confirmations) response.Dispose();
        }
        var finalEmail = confirmations[0].StatusCode == HttpStatusCode.OK ? targetEmail : supersededEmail;
        fixture.Clock.Advance(TimeSpan.FromSeconds(1));
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.Equal(finalEmail, user.Email);
            Assert.Equal(finalEmail, user.UserName);
            Assert.Equal(users.NormalizeEmail(finalEmail), user.NormalizedEmail);
            Assert.Equal(users.NormalizeName(finalEmail), user.NormalizedUserName);
            Assert.NotEqual(originalStamp, user.SecurityStamp);
            Assert.True(await users.CheckPasswordAsync(user, account.Password));
        }

        using var fresh = fixture.CreateClient();
        using var newAddressLogin = await RealCookieAccountFixture.LoginAsync(fresh, finalEmail, account.Password);
        Assert.Equal(HttpStatusCode.OK, newAddressLogin.StatusCode);
    }

    [Fact]
    public async Task EmailChange_DoesNotDiscloseAnAlreadyOwnedTargetAddress()
    {
        await using var fixture = NewEmailFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var account = await fixture.CreateUserAsync();
        var owner = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);

        using var usedTarget = await ChangeEmailAsync(client, account.Id, session.CsrfToken, account.Password, owner.Email);

        Assert.Equal(HttpStatusCode.Accepted, usedTarget.StatusCode);
        Assert.Equal("Request received. If this change can proceed, check the new address for a confirmation message.", await ReadMessageAsync(usedTarget));
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<BlazorAutoApp.Infrastructure.Persistence.AppDbContext>();
            Assert.Empty(await db.AccountOutbox.ToListAsync());
            var user = await scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().FindByIdAsync(account.Id);
            Assert.Equal(account.Email, user?.Email);
        }
    }

    [Fact]
    public async Task EmailChange_MapsTargetClaimedBeforeConfirmationToSafeConflictAndRollsBack()
    {
        await using var fixture = NewEmailFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var account = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        var targetEmail = $"raced-{Guid.NewGuid():N}@example.test";
        using var request = await ChangeEmailAsync(client, account.Id, session.CsrfToken, account.Password, targetEmail);
        Assert.Equal(HttpStatusCode.Accepted, request.StatusCode);
        await fixture.Factory.Services.GetRequiredService<BlockingAccountMailTransport>().Started.Task.WaitAsync(TimeSpan.FromSeconds(10));

        AccountMailPayload payload;
        string originalStamp;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var protector = scope.ServiceProvider.GetRequiredService<AccountMailPayloadProtector>();
            var db = scope.ServiceProvider.GetRequiredService<BlazorAutoApp.Infrastructure.Persistence.AppDbContext>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            originalStamp = user.SecurityStamp!;
            payload = protector.Unprotect((await db.AccountOutbox.SingleAsync()).ProtectedPayload);
            var other = new ApplicationUser { Email = targetEmail, UserName = targetEmail, EmailConfirmed = true };
            var created = await users.CreateAsync(other, $"Fixture target owner {Guid.NewGuid():N}");
            Assert.True(created.Succeeded);
        }

        using var confirmation = await ConfirmEmailChangeAsync(client, session.CsrfToken, account.Id, targetEmail, payload.Token);
        Assert.Equal(HttpStatusCode.Conflict, confirmation.StatusCode);
        using (var problem = JsonDocument.Parse(await confirmation.Content.ReadAsStringAsync()))
        {
            Assert.Equal("AccountConflict", problem.RootElement.GetProperty("code").GetString());
            Assert.DoesNotContain(targetEmail, problem.RootElement.ToString(), StringComparison.Ordinal);
        }
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.Equal(account.Email, user.Email);
            Assert.Equal(account.Email, user.UserName);
            Assert.Equal(originalStamp, user.SecurityStamp);
        }
    }

    private static RealCookieAccountFixture NewEmailFixture() =>
        new(new Dictionary<string, string?>
        {
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = "1",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:Email:Security"] = "StartTls",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        }, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<BlockingAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport>(provider => provider.GetRequiredService<BlockingAccountMailTransport>());
        });

    private static async Task<HttpResponseMessage> ChangeEmailAsync(
        HttpClient client,
        string userId,
        string csrfToken,
        string password,
        string email)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/auth/change-email")
        {
            Content = JsonContent.Create(new { password, email })
        };
        request.Headers.Add("X-Expected-User", userId);
        request.Headers.Add("X-CSRF-TOKEN", csrfToken);
        return await client.SendAsync(request);
    }

    private static async Task<HttpResponseMessage> ConfirmEmailChangeAsync(
        HttpClient client,
        string csrfToken,
        string userId,
        string email,
        string token)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/auth/confirm-email-change")
        {
            Content = JsonContent.Create(new { userId, email, token })
        };
        request.Headers.Add("X-CSRF-TOKEN", csrfToken);
        return await client.SendAsync(request);
    }

    private static async Task<string> ReadMessageAsync(HttpResponseMessage response)
    {
        using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        return json.RootElement.GetProperty("message").GetString() ?? "";
    }

    private sealed class BlockingAccountMailTransport : IAccountMailTransport
    {
        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public async Task SendAsync(AccountMailMessage message, CancellationToken cancellationToken)
        {
            _ = message.MessageId;
            Started.TrySetResult();
            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
        }
    }
}
