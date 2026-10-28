using System.Collections.Concurrent;
using System.Data.Common;
using GrumPlates.Features.Accounts.Email;
using GrumPlates.Infrastructure.Persistence;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Xunit;

namespace GrumPlates.Test.Features.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountReplicaOutboxTests
{
    [Fact]
    public async Task ConcurrentWorkers_SkipLockedClaimsAndSendOnlyAfterLeaseCommit()
    {
        const int jobCount = 20;
        var appName = $"account-outbox-replicas-{Guid.NewGuid():N}";
        await using var seed = new RealCookieAccountFixture(appName: appName);
        await seed.InitializeAsync();
        for (var index = 0; index < jobCount; index++)
        {
            var account = await seed.CreateUserAsync(confirmed: false);
            using var scope = seed.Factory.Services.CreateScope();
            var outbox = scope.ServiceProvider.GetRequiredService<AccountMailOutbox>();
            var result = await outbox.RunAdmittedAsync(async (admission, cancellationToken) =>
            {
                var user = await admission.Users.FindByIdAsync(account.Id);
                Assert.NotNull(user);
                await admission.Outbox.LockUserForUpdateAsync(user, cancellationToken);
                var token = await admission.Users.GenerateEmailConfirmationTokenAsync(user);
                return await admission.Outbox.EnqueueAsync(user, AccountMailPurpose.Confirmation,
                    account.Email, token, cancellationToken: cancellationToken);
            }, AccountMailEnqueueResult.Suppressed, CancellationToken.None);
            Assert.Equal(AccountMailEnqueueResult.Queued, result);
        }

        var releaseSends = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var firstClaim = new ClaimBarrier();
        var firstCapture = new ReplicaCapture(releaseSends.Task);
        var secondCapture = new ReplicaCapture(releaseSends.Task);
        var settings = new Dictionary<string, string?>
        {
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        };
        try
        {
            await using var first = Replica(firstCapture, firstClaim);
            await first.InitializeAsync();
            await firstClaim.RowsLocked.Task.WaitAsync(TimeSpan.FromSeconds(30));
            await using var second = Replica(secondCapture);
            await second.InitializeAsync();
            await secondCapture.Started.Task.WaitAsync(TimeSpan.FromSeconds(30));
            Assert.False(firstCapture.Started.Task.IsCompleted);
            firstClaim.Release.TrySetResult();
            await firstCapture.Started.Task.WaitAsync(TimeSpan.FromSeconds(30));

            // Both live replicas have committed their claims while delivery is blocked.
            // Each replica may send five messages concurrently from its ten-row batch.
            await WaitUntilAsync(() => Task.FromResult(firstCapture.StartedSends == 5 && secondCapture.StartedSends == 5));
            using (var scope = seed.Factory.Services.CreateScope())
            {
                var rows = await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.AsNoTracking().ToListAsync();
                Assert.Equal(jobCount, rows.Count);
                Assert.All(rows, row => { Assert.Equal("Leased", row.Status); Assert.Equal(1, row.Attempts); });
                Assert.Equal(jobCount, rows.Select(row => row.LeaseId).Distinct().Count());
            }

            releaseSends.TrySetResult();
            await WaitUntilAsync(async () =>
            {
                using var scope = seed.Factory.Services.CreateScope();
                return await scope.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox
                    .CountAsync(row => row.Status == "Sent") == jobCount;
            });

            Assert.Equal(10, firstCapture.Deliveries.Count);
            Assert.Equal(10, secondCapture.Deliveries.Count);
            Assert.Empty(firstCapture.Deliveries.Keys.Intersect(secondCapture.Deliveries.Keys));
            Assert.All(firstCapture.Deliveries.Values.Concat(secondCapture.Deliveries.Values), count => Assert.Equal(1, count));
            Assert.Equal(0, firstCapture.SendsInsideTransaction + secondCapture.SendsInsideTransaction);
            Assert.Equal(0, firstCapture.SendsBeforeLeaseCommit + secondCapture.SendsBeforeLeaseCommit);
            using var verification = seed.Factory.Services.CreateScope();
            var completed = await verification.ServiceProvider.GetRequiredService<AppDbContext>().AccountOutbox.AsNoTracking().ToListAsync();
            Assert.All(completed, row =>
            {
                Assert.Equal(1, row.Attempts);
                Assert.Equal("", row.ProtectedPayload);
                Assert.Null(row.LeaseId);
                Assert.Null(row.LeaseUntilUtc);
            });
        }
        finally
        {
            firstClaim.Release.TrySetResult();
            releaseSends.TrySetResult();
        }

        RealCookieAccountFixture Replica(ReplicaCapture capture, ClaimBarrier? claimBarrier = null) => new(settings, services =>
        {
            if (claimBarrier is not null) services.AddSingleton<DbCommandInterceptor>(claimBarrier);
            services.RemoveAll<IAccountMailTransport>();
            services.AddScoped<IAccountMailTransport>(provider =>
                new ReplicaTransport(capture, provider.GetRequiredService<AppDbContext>()));
            services.Configure<AccountMailWorkerSchedule>(schedule => schedule.PollInterval = TimeSpan.FromMilliseconds(20));
        }, appName, seed.Factory.ConnectionString, seed.Clock,
            keyEncryptionCertificatePath: seed.KeyEncryptionCertificatePath);
    }

    private static async Task WaitUntilAsync(Func<Task<bool>> condition)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        while (!await condition()) await Task.Delay(20, timeout.Token);
    }

    private sealed class ClaimBarrier : DbCommandInterceptor
    {
        private int _armed = 1;
        public TaskCompletionSource RowsLocked { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Release { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public override async ValueTask<DbDataReader> ReaderExecutedAsync(
            DbCommand command, CommandExecutedEventData eventData, DbDataReader result,
            CancellationToken cancellationToken = default)
        {
            if (command.CommandText.Contains("FOR UPDATE SKIP LOCKED", StringComparison.Ordinal)
                && Interlocked.Exchange(ref _armed, 0) == 1)
            {
                RowsLocked.TrySetResult();
                await Release.Task.WaitAsync(cancellationToken);
            }
            return result;
        }
    }

    private sealed class ReplicaCapture(Task releaseSends)
    {
        public Task ReleaseSends { get; } = releaseSends;
        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public ConcurrentDictionary<string, int> Deliveries { get; } = new();
        public int StartedSends;
        public int SendsInsideTransaction;
        public int SendsBeforeLeaseCommit;
    }

    private sealed class ReplicaTransport(ReplicaCapture capture, AppDbContext db) : IAccountMailTransport
    {
        public async Task SendAsync(AccountMailMessage message, CancellationToken cancellationToken)
        {
            if (db.Database.CurrentTransaction is not null) Interlocked.Increment(ref capture.SendsInsideTransaction);
            if (!await db.AccountOutbox.AsNoTracking().AnyAsync(row => row.MessageId == message.MessageId
                && row.Status == "Leased" && row.Attempts == 1 && row.LeaseId != null, cancellationToken))
            {
                Interlocked.Increment(ref capture.SendsBeforeLeaseCommit);
            }
            Interlocked.Increment(ref capture.StartedSends);
            capture.Started.TrySetResult();
            await capture.ReleaseSends.WaitAsync(cancellationToken);
            capture.Deliveries.AddOrUpdate(message.MessageId, 1, (_, count) => count + 1);
        }
    }
}
