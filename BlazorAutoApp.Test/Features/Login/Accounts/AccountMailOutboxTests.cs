using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts;
using BlazorAutoApp.Features.Login.Accounts.Email;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Accounts;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Xunit;

namespace BlazorAutoApp.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountMailOutboxTests
{
    [Fact]
    public async Task Enqueue_ProtectsRecipientTokenAndStampAndSuppressesDuplicateActiveIntent()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var (userId, email, _) = await fixture.CreateUserAsync(confirmed: false);

        using var scope = fixture.Factory.Services.CreateScope();
        var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var outbox = scope.ServiceProvider.GetRequiredService<AccountMailOutbox>();
        var protector = scope.ServiceProvider.GetRequiredService<AccountMailPayloadProtector>();
        var user = await users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
        var token = await users.GenerateEmailConfirmationTokenAsync(user);

        await QueueAsync(outbox, userId, AccountMailPurpose.Confirmation, email, token);
        await QueueAsync(outbox, userId, AccountMailPurpose.Confirmation, email, token);

        var row = await db.AccountOutbox.SingleAsync();
        Assert.Equal("Pending", row.Status);
        Assert.Equal("Confirmation", row.Purpose);
        Assert.DoesNotContain(email, row.ProtectedPayload, StringComparison.Ordinal);
        Assert.DoesNotContain(token, row.ProtectedPayload, StringComparison.Ordinal);
        Assert.DoesNotContain(user.SecurityStamp!, row.ProtectedPayload, StringComparison.Ordinal);

        var payload = protector.Unprotect(row.ProtectedPayload);
        Assert.Equal(1, payload.Version);
        Assert.Equal(email, payload.Recipient);
        Assert.Equal(userId, payload.UserId);
        Assert.Equal(AccountMailPurpose.Confirmation, payload.Purpose);
        Assert.Equal(user.SecurityStamp, payload.SecurityStamp);
        Assert.Equal(token, payload.Token);
        Assert.Equal(fixture.Clock.GetUtcNow().AddHours(1), payload.LinkExpiresUtc);
        Assert.Equal(fixture.Clock.GetUtcNow().AddMinutes(45), row.ExpiresUtc);
        Assert.Equal($"{row.Id:N}@account.local", row.MessageId);
    }

    [Fact]
    public void LinkFactory_UsesOnlyKnownReactAndBlazorRoutesAndStatesActualExpiry()
    {
        var payload = new AccountMailPayload(1, "reader@example.test", "user-1", AccountMailPurpose.PasswordReset,
            "stamp-secret", "token-secret+/=", null, DateTimeOffset.Parse("2026-10-15T12:34:56Z"));
        var settings = new AccountOptions { PublicOrigin = "https://books.example.test" };

        var react = new AccountEmailLinkFactory(settings, AccountMailFrontend.React)
            .Create(payload, "message-id");
        Assert.Contains("https://books.example.test/auth/reset-password#userId=user-1&token=token-secret%2B%2F%3D", react.Text, StringComparison.Ordinal);
        Assert.Contains("before 2026-10-15 12:34:56 UTC", react.Text, StringComparison.Ordinal);
        Assert.DoesNotContain("stamp-secret", react.Text, StringComparison.Ordinal);

        var blazor = new AccountEmailLinkFactory(settings, AccountMailFrontend.BlazorAuto)
            .Create(payload, "message-id");
        Assert.Contains("https://books.example.test/Account/ResetPassword?userId=user-1&code=", blazor.Text, StringComparison.Ordinal);
        Assert.DoesNotContain("#", blazor.Text, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Enqueue_EnforcesSixtySecondCooldownAndFiveIntentsPerHour()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var (userId, email, _) = await fixture.CreateUserAsync(confirmed: false);
        using var scope = fixture.Factory.Services.CreateScope();
        var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var outbox = scope.ServiceProvider.GetRequiredService<AccountMailOutbox>();
        var user = await users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
        var token = await users.GenerateEmailConfirmationTokenAsync(user);

        Assert.Equal(AccountMailEnqueueResult.Queued, await QueueAsync(outbox, userId, AccountMailPurpose.Confirmation, email, token));
        await MarkTerminalAsync(db);
        fixture.Clock.Advance(TimeSpan.FromSeconds(59));
        Assert.Equal(AccountMailEnqueueResult.Suppressed, await QueueAsync(outbox, userId, AccountMailPurpose.Confirmation, email, token));
        fixture.Clock.Advance(TimeSpan.FromSeconds(2));

        for (var intent = 2; intent <= 5; intent++)
        {
            Assert.Equal(AccountMailEnqueueResult.Queued, await QueueAsync(outbox, userId, AccountMailPurpose.Confirmation, email, token));
            await MarkTerminalAsync(db);
            fixture.Clock.Advance(TimeSpan.FromSeconds(61));
        }

        Assert.Equal(AccountMailEnqueueResult.Suppressed, await QueueAsync(outbox, userId, AccountMailPurpose.Confirmation, email, token));
        Assert.Equal(5, await db.AccountOutbox.CountAsync());
    }

    [Fact]
    public async Task EnabledWorker_SendsProtectedIntentOverTrustedStartTlsAndClearsPayload()
    {
        await using var inbox = new TlsSmtpFixture();
        await using var fixture = NewEmailFixture(inbox, trustCertificate: true);
        await fixture.InitializeAsync();
        var (userId, email, _) = await fixture.CreateUserAsync(confirmed: false);

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
            var token = await users.GenerateEmailConfirmationTokenAsync(user);
            await QueueAsync(scope.ServiceProvider.GetRequiredService<AccountMailOutbox>(), userId,
                AccountMailPurpose.Confirmation, email, token);
        }

        using var received = await inbox.ReadMessageAsync().WaitAsync(TimeSpan.FromSeconds(20));
        Assert.Equal(email, received.To.Mailboxes.Single().Address);
        Assert.Contains("before ", received.TextBody, StringComparison.Ordinal);
        var frontend = fixture.Factory.Services.GetRequiredService<IAccountMailFrontend>();
        var routeSuffix = frontend.UsesFragmentSecrets ? "#" : "?";
        Assert.Contains($"/{frontend.GetRoute(AccountMailPurpose.Confirmation)}{routeSuffix}", received.TextBody, StringComparison.Ordinal);

        await WaitUntilAsync(async () =>
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            return row.Status == "Sent" && row.ProtectedPayload.Length == 0 && row.LeaseId is null;
        });
    }

    [Fact]
    public async Task EnabledWorker_RejectsUntrustedCertificateAndReportsSafeMailHealthOnly()
    {
        await using var inbox = new TlsSmtpFixture();
        await using var fixture = NewEmailFixture(inbox, trustCertificate: false);
        await fixture.InitializeAsync();
        var (userId, email, _) = await fixture.CreateUserAsync(confirmed: false);

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
            var token = await users.GenerateEmailConfirmationTokenAsync(user);
            await QueueAsync(scope.ServiceProvider.GetRequiredService<AccountMailOutbox>(), userId,
                AccountMailPurpose.Confirmation, email, token);
        }

        string? safeFailureCode = null;
        await WaitUntilAsync(async () =>
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            safeFailureCode = row.FailureCode;
            return row.Status == "Failed" && row.ProtectedPayload.Length == 0 && row.FailureCode is not null;
        });

        using var client = fixture.CreateClient();
        using var mailHealth = await client.GetAsync("/health/mail");
        Assert.Equal(System.Net.HttpStatusCode.OK, mailHealth.StatusCode);
        var mailJson = await mailHealth.Content.ReadAsStringAsync();
        Assert.True(safeFailureCode is "TransportAuthentication" or "TransportUnavailable",
            $"Unexpected safe failure code: {safeFailureCode}");
        Assert.Contains(safeFailureCode!, mailJson, StringComparison.Ordinal);
        Assert.DoesNotContain(email, mailJson, StringComparison.Ordinal);
        using var readiness = await client.GetAsync("/health/ready");
        Assert.Equal(System.Net.HttpStatusCode.OK, readiness.StatusCode);
    }

    [Fact]
    public async Task RestartedWorker_ReclaimsExpiredLeaseAndSendsSameMessageId()
    {
        const string appName = "account-mail-lease-recovery-fixture";
        var accountSettings = new Dictionary<string, string?>
        {
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = "1",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:Email:Security"] = "StartTls",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        };
        await using var first = new RealCookieAccountFixture(accountSettings, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<BlockingAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport>(provider => provider.GetRequiredService<BlockingAccountMailTransport>());
            services.Configure<AccountMailWorkerSchedule>(schedule =>
            {
                schedule.PollInterval = TimeSpan.FromMilliseconds(20);
                schedule.LeaseDuration = TimeSpan.FromMilliseconds(100);
            });
        }, appName);
        await first.InitializeAsync();
        var (userId, email, _) = await first.CreateUserAsync(confirmed: false);

        string originalMessageId;
        using (var scope = first.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
            var token = await users.GenerateEmailConfirmationTokenAsync(user);
            var outbox = scope.ServiceProvider.GetRequiredService<AccountMailOutbox>();
            await outbox.RunAdmittedAsync(async (admission, cancellationToken) =>
            {
                var attemptUser = await admission.Users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
                await admission.Outbox.LockUserForUpdateAsync(attemptUser, cancellationToken);
                return await admission.Outbox.EnqueueAsync(attemptUser, AccountMailPurpose.Confirmation, email, token,
                    cancellationToken: cancellationToken);
            }, AccountMailEnqueueResult.Suppressed, CancellationToken.None);
        }
        await first.Factory.Services.GetRequiredService<BlockingAccountMailTransport>().Started.Task.WaitAsync(TimeSpan.FromSeconds(10));
        using (var scope = first.Factory.Services.CreateScope())
        {
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            Assert.Equal("Leased", row.Status);
            Assert.Equal(1, row.Attempts);
            originalMessageId = row.MessageId;
        }

        var firstLifetime = first.Factory.Services.GetRequiredService<IHostApplicationLifetime>();
        firstLifetime.StopApplication();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            Task.Delay(Timeout.InfiniteTimeSpan, firstLifetime.ApplicationStopped).WaitAsync(TimeSpan.FromSeconds(10)));

        await using var second = new RealCookieAccountFixture(accountSettings, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<CapturingAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport>(provider => provider.GetRequiredService<CapturingAccountMailTransport>());
            services.Configure<AccountMailWorkerSchedule>(schedule =>
            {
                schedule.PollInterval = TimeSpan.FromMilliseconds(20);
                schedule.LeaseDuration = TimeSpan.FromMilliseconds(100);
            });
        }, appName, first.Factory.ConnectionString,
            keyEncryptionCertificatePath: first.KeyEncryptionCertificatePath);
        await second.InitializeAsync();
        var delivered = await second.Factory.Services.GetRequiredService<CapturingAccountMailTransport>()
            .Sent.Task.WaitAsync(TimeSpan.FromSeconds(10));
        Assert.Equal(originalMessageId, delivered.MessageId);

        await WaitUntilAsync(async () =>
        {
            using var scope = second.Factory.Services.CreateScope();
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            return row.Status == "Sent" && row.Attempts == 2 && row.ProtectedPayload.Length == 0;
        });
    }

    [Fact]
    public async Task Worker_RetriesTransientFailuresAtBoundedBackoffAndPreservesMessageId()
    {
        var settings = new Dictionary<string, string?>
        {
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = "1",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:Email:Security"] = "StartTls",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        };
        await using var fixture = new RealCookieAccountFixture(settings, services =>
        {
            services.RemoveAll<IAccountMailTransport>();
            services.AddSingleton<FlakyAccountMailTransport>();
            services.AddSingleton<IAccountMailTransport>(provider => provider.GetRequiredService<FlakyAccountMailTransport>());
            services.Configure<AccountMailWorkerSchedule>(schedule =>
            {
                schedule.PollInterval = TimeSpan.FromMilliseconds(20);
                schedule.FirstRetryDelay = TimeSpan.FromMilliseconds(100);
                schedule.SecondRetryDelay = TimeSpan.FromMilliseconds(200);
            });
        });
        await fixture.InitializeAsync();
        var (userId, email, _) = await fixture.CreateUserAsync(confirmed: false);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
            var token = await users.GenerateEmailConfirmationTokenAsync(user);
            await QueueAsync(scope.ServiceProvider.GetRequiredService<AccountMailOutbox>(), userId,
                AccountMailPurpose.Confirmation, email, token);
        }

        string messageId = "";
        await WaitUntilAsync(async () =>
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            messageId = row.MessageId;
            return row.Status == "Pending" && row.Attempts == 1;
        });
        fixture.Clock.Advance(TimeSpan.FromMilliseconds(101));

        await WaitUntilAsync(async () =>
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            return row.Status == "Pending" && row.Attempts == 2;
        });
        fixture.Clock.Advance(TimeSpan.FromMilliseconds(201));

        var delivered = await fixture.Factory.Services.GetRequiredService<FlakyAccountMailTransport>()
            .Sent.Task.WaitAsync(TimeSpan.FromSeconds(10));
        Assert.Equal(messageId, delivered.MessageId);
        await WaitUntilAsync(async () =>
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var row = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.SingleAsync();
            return row.Status == "Sent" && row.Attempts == 3 && row.ProtectedPayload.Length == 0;
        });
    }

    private static RealCookieAccountFixture NewEmailFixture(TlsSmtpFixture inbox, bool trustCertificate) =>
        new(new Dictionary<string, string?>
        {
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = inbox.Port.ToString(),
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:Email:Security"] = "StartTls",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        }, services =>
        {
            if (trustCertificate)
            {
                services.Configure<AccountMailTransportOptions>(options =>
                    options.ServerCertificateValidationCallback = inbox.ValidateCertificate);
            }
        });

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

    private static Task<AccountMailEnqueueResult> QueueAsync(
        AccountMailOutbox outbox,
        string userId,
        AccountMailPurpose purpose,
        string recipient,
        string token) => outbox.RunAdmittedAsync(async (admission, cancellationToken) =>
        {
            var user = await admission.Users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
            await admission.Outbox.LockUserForUpdateAsync(user, cancellationToken);
            return await admission.Outbox.EnqueueAsync(user, purpose, recipient, token, cancellationToken: cancellationToken);
        }, AccountMailEnqueueResult.Suppressed, CancellationToken.None);

    private static Task MarkTerminalAsync(AppDbContext db) => db.AccountOutbox.ExecuteUpdateAsync(update => update
        .SetProperty(message => message.Status, "Sent")
        .SetProperty(message => message.ProtectedPayload, ""));

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

    private sealed class CapturingAccountMailTransport : IAccountMailTransport
    {
        public CapturingAccountMailTransport() { }
        public TaskCompletionSource<AccountMailMessage> Sent { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public Task SendAsync(AccountMailMessage message, CancellationToken cancellationToken)
        {
            Sent.TrySetResult(message);
            return Task.CompletedTask;
        }
    }

    private sealed class FlakyAccountMailTransport : IAccountMailTransport
    {
        private int _attempts;
        public FlakyAccountMailTransport() { }
        public TaskCompletionSource<AccountMailMessage> Sent { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public Task SendAsync(AccountMailMessage message, CancellationToken cancellationToken)
        {
            if (Interlocked.Increment(ref _attempts) < 3)
            {
                throw new IOException("synthetic transient delivery failure");
            }
            Sent.TrySetResult(message);
            return Task.CompletedTask;
        }
    }
}
