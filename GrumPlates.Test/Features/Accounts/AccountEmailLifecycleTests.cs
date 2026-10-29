using System.Security.Cryptography;
using System.Text.Json;
using GrumPlates.Features.Accounts.Email;
using GrumPlates.Infrastructure.Persistence;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection.Extensions;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Test.Features.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountEmailLifecycleTests
{
    [Fact]
    public async Task Registration_IsEmailFirstAndPublicRequestsShareOneGenericAcceptedMessage()
    {
        await using var fixture = NewEmailFixture(registrationEnabled: true, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<BlockingAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport>(provider => provider.GetRequiredService<BlockingAccountMailTransport>());
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        const string email = "new-reader@example.test";

        using var registration = await PostJsonAsync(client, "/api/auth/register", new { email }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.Accepted, registration.StatusCode);
        var registrationMessage = await ReadMessageAsync(registration);
        Assert.Equal("Request received. Check your email if applicable; use resend if it does not arrive.", registrationMessage);
        await fixture.Factory.Services.GetRequiredService<BlockingAccountMailTransport>().Started.Task.WaitAsync(TimeSpan.FromSeconds(10));

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var user = await users.FindByEmailAsync(email);
            Assert.NotNull(user);
            Assert.False(user.EmailConfirmed);
            Assert.False(await users.HasPasswordAsync(user));
            var intent = await db.AccountOutbox.SingleAsync();
            Assert.Equal(user.Id, intent.UserId);
            Assert.Equal("Leased", intent.Status);
            Assert.DoesNotContain(email, intent.ProtectedPayload, StringComparison.Ordinal);
        }

        using var duplicateRegistration = await PostJsonAsync(client, "/api/auth/register", new { email }, session.CsrfToken);
        using var unknownResend = await PostJsonAsync(client, "/api/auth/resend-confirmation", new { email = "unknown@example.test" }, session.CsrfToken);
        using var unknownForgot = await PostJsonAsync(client, "/api/auth/forgot-password", new { email = "unknown@example.test" }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.Accepted, duplicateRegistration.StatusCode);
        Assert.Equal(HttpStatusCode.Accepted, unknownResend.StatusCode);
        Assert.Equal(HttpStatusCode.Accepted, unknownForgot.StatusCode);
        Assert.Equal(registrationMessage, await ReadMessageAsync(duplicateRegistration));
        Assert.Equal(registrationMessage, await ReadMessageAsync(unknownResend));
        Assert.Equal(registrationMessage, await ReadMessageAsync(unknownForgot));

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            Assert.Equal(1, await db.Users.CountAsync(user => user.Email == email));
            Assert.Equal(1, await db.AccountOutbox.CountAsync());
        }
    }

    [Fact]
    public async Task Registration_OutboxInsertFailureRollsBackPasswordlessIdentityAccount()
    {
        await using var fixture = NewEmailFixture(registrationEnabled: true, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport, BlockingAccountMailTransport>();
        });
        await fixture.InitializeAsync();
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            await db.Database.ExecuteSqlRawAsync("""
                CREATE FUNCTION "fixture_reject_outbox_insert"() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'synthetic outbox failure'; END; $$;
                """);
            await db.Database.ExecuteSqlRawAsync("""
                CREATE TRIGGER "fixture_reject_outbox_insert" BEFORE INSERT ON "AccountOutbox"
                FOR EACH ROW EXECUTE FUNCTION "fixture_reject_outbox_insert"();
                """);
        }

        using var client = fixture.CreateClient();
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        const string email = "rollback-reader@example.test";
        using var response = await PostJsonAsync(client, "/api/auth/register", new { email }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        using var scopeAfterFailure = fixture.Factory.Services.CreateScope();
        var users = scopeAfterFailure.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var dbAfterFailure = scopeAfterFailure.ServiceProvider.GetRequiredService<AppDbContext>();
        Assert.Null(await users.FindByEmailAsync(email));
        Assert.Equal(0, await dbAfterFailure.AccountOutbox.CountAsync());
    }

    [Fact]
    public async Task Confirmation_RequiresValidProofAndSetsNewPasswordInOneTransaction()
    {
        await using var fixture = NewEmailFixture(registrationEnabled: true, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<BlockingAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport>(provider => provider.GetRequiredService<BlockingAccountMailTransport>());
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        const string email = "proof-reader@example.test";
        using var registration = await PostJsonAsync(client, "/api/auth/register", new { email }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.Accepted, registration.StatusCode);
        await fixture.Factory.Services.GetRequiredService<BlockingAccountMailTransport>().Started.Task.WaitAsync(TimeSpan.FromSeconds(10));

        AccountMailPayload payload;
        string oldStamp;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var protector = scope.ServiceProvider.GetRequiredService<AccountMailPayloadProtector>();
            var user = await scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().FindByEmailAsync(email);
            Assert.NotNull(user);
            oldStamp = user.SecurityStamp!;
            payload = protector.Unprotect((await db.AccountOutbox.SingleAsync()).ProtectedPayload);
        }

        using var weakPassword = await PostJsonAsync(client, "/api/auth/confirm-email",
            new { userId = payload.UserId, token = payload.Token, newPassword = "weak" }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.BadRequest, weakPassword.StatusCode);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var user = await scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().FindByIdAsync(payload.UserId);
            Assert.NotNull(user);
            Assert.False(user.EmailConfirmed);
            Assert.False(await scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().HasPasswordAsync(user));
            Assert.Equal(oldStamp, user.SecurityStamp);
        }

        var newPassword = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        using var confirmation = await PostJsonAsync(client, "/api/auth/confirm-email",
            new { userId = payload.UserId, token = payload.Token, newPassword }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.OK, confirmation.StatusCode);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(payload.UserId);
            Assert.NotNull(user);
            Assert.True(user.EmailConfirmed);
            Assert.NotEqual(oldStamp, user.SecurityStamp);
            Assert.True((await users.CheckPasswordAsync(user, newPassword)));
        }

        using var replay = await PostJsonAsync(client, "/api/auth/confirm-email",
            new { userId = payload.UserId, token = payload.Token, newPassword }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.BadRequest, replay.StatusCode);
    }

    [Fact]
    public async Task PasswordReset_UsesQueuedProofAndRevokesPreviousCredentialStamp()
    {
        await using var fixture = NewEmailFixture(registrationEnabled: false, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<BlockingAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport>(provider => provider.GetRequiredService<BlockingAccountMailTransport>());
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        using var forgot = await PostJsonAsync(client, "/api/auth/forgot-password", new { email = user.Email }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.Accepted, forgot.StatusCode);
        Assert.Equal("Request received. Check your email if applicable; use resend if it does not arrive.", await ReadMessageAsync(forgot));
        await fixture.Factory.Services.GetRequiredService<BlockingAccountMailTransport>().Started.Task.WaitAsync(TimeSpan.FromSeconds(10));

        AccountMailPayload payload;
        string oldStamp;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var protector = scope.ServiceProvider.GetRequiredService<AccountMailPayloadProtector>();
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            oldStamp = (await users.FindByIdAsync(user.Id))!.SecurityStamp!;
            payload = protector.Unprotect((await db.AccountOutbox.SingleAsync()).ProtectedPayload);
        }

        var newPassword = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        using var reset = await PostJsonAsync(client, "/api/auth/reset-password",
            new { userId = payload.UserId, token = payload.Token, newPassword }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.OK, reset.StatusCode);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var current = await users.FindByIdAsync(user.Id);
            Assert.NotNull(current);
            Assert.NotEqual(oldStamp, current.SecurityStamp);
            Assert.False(await users.CheckPasswordAsync(current, user.Password));
            Assert.True(await users.CheckPasswordAsync(current, newPassword));
        }

        using var replay = await PostJsonAsync(client, "/api/auth/reset-password",
            new { userId = payload.UserId, token = payload.Token, newPassword = user.Password }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.BadRequest, replay.StatusCode);
    }

    [Fact]
    public async Task PublicRequest_RemainsAcceptedWhenWorkerRejectsSmtpCertificate()
    {
        await using var inbox = new TlsSmtpFixture();
        await using var fixture = new RealCookieAccountFixture(new Dictionary<string, string?>
        {
            ["Accounts:RegistrationEnabled"] = "true",
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = inbox.Port.ToString(),
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:Email:Security"] = "StartTls",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        using var response = await PostJsonAsync(client, "/api/auth/register", new { email = "smtp-failure@example.test" }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        Assert.Equal("Request received. Check your email if applicable; use resend if it does not arrive.", await ReadMessageAsync(response));

        string? failureCode = null;
        await WaitUntilAsync(async () =>
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            failureCode = row.FailureCode;
            return row.Status == "Failed" && row.ProtectedPayload.Length == 0;
        });
        Assert.Equal("TransportAuthentication", failureCode);
    }

    [Fact]
    public async Task FullOutbox_Returns503BeforeLookingUpOrCreatingRequestedAccount()
    {
        await using var fixture = new RealCookieAccountFixture(new Dictionary<string, string?>
        {
            ["Accounts:RegistrationEnabled"] = "true",
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = "1",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:Email:Security"] = "StartTls",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        });
        await fixture.InitializeAsync();
        var existing = await fixture.CreateUserAsync();
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            await db.Database.ExecuteSqlInterpolatedAsync($"""
                INSERT INTO "AccountOutbox" (
                    "Id", "MessageId", "UserId", "Purpose", "Status", "ProtectedPayload",
                    "CreatedUtc", "ExpiresUtc", "NextAttemptUtc", "Attempts", "LeaseId", "LeaseUntilUtc")
                SELECT md5('capacity-' || n::text)::uuid,
                       md5('message-' || n::text) || '@account.local',
                       {existing.Id},
                       'Capacity' || n::text,
                       'Leased', '', now(), now() + interval '45 minutes', now(), 1,
                       'capacity-' || n::text, now() + interval '1 hour'
                FROM generate_series(1, 1000) AS n
                """);
        }

        using var client = fixture.CreateClient();
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        const string requestedEmail = "not-looked-up@example.test";
        using var response = await PostJsonAsync(client, "/api/auth/register", new { email = requestedEmail }, session.CsrfToken);
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        using var mailHealth = await client.GetAsync("/health/mail");
        Assert.Contains("OutboxCapacity", await mailHealth.Content.ReadAsStringAsync(), StringComparison.Ordinal);
        using var scopeAfterRequest = fixture.Factory.Services.CreateScope();
        var dbAfterRequest = scopeAfterRequest.ServiceProvider.GetRequiredService<AppDbContext>();
        Assert.Equal(1000, await dbAfterRequest.AccountOutbox.CountAsync());
        Assert.Equal(0, await dbAfterRequest.Users.CountAsync(user => user.Email == requestedEmail));
    }

    private static RealCookieAccountFixture NewEmailFixture(bool registrationEnabled, Action<IServiceCollection>? configure = null) =>
        new(new Dictionary<string, string?>
        {
            ["Accounts:RegistrationEnabled"] = registrationEnabled.ToString(),
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = "1",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:Email:Security"] = "StartTls",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        }, configure);

    private static async Task WaitUntilAsync(Func<Task<bool>> predicate)
    {
        var timeout = DateTimeOffset.UtcNow.AddSeconds(15);
        while (DateTimeOffset.UtcNow < timeout)
        {
            if (await predicate()) return;
            await Task.Delay(50);
        }
        Assert.Fail("The account mail outbox did not reach the expected terminal state.");
    }

    private static async Task<HttpResponseMessage> PostJsonAsync(HttpClient client, string path, object body, string csrf)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, path) { Content = JsonContent.Create(body) };
        request.Headers.Add("X-CSRF-TOKEN", csrf);
        return await client.SendAsync(request);
    }

    private static async Task<string> ReadMessageAsync(HttpResponseMessage response)
    {
        using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        return json.RootElement.GetProperty("message").GetString() ?? "";
    }

    private sealed class BlockingAccountMailTransport : IAccountMailTransport
    {
        public BlockingAccountMailTransport() { }

        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public async Task SendAsync(AccountMailMessage message, CancellationToken cancellationToken)
        {
            _ = message.MessageId;
            Started.TrySetResult();
            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
        }
    }
}
