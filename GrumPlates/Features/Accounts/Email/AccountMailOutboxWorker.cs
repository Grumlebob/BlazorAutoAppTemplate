using System.Net.Sockets;
using System.Security.Cryptography;
using MailKit.Net.Smtp;
using MailKit.Security;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Features.Accounts.Email;

internal sealed class AccountMailOutboxWorker(
    IServiceScopeFactory scopes,
    AccountOptions options,
    IOptions<AccountMailWorkerSchedule> scheduleOptions,
    AccountMailHealth health,
    TimeProvider clock,
    ILogger<AccountMailOutboxWorker> logger) : BackgroundService
{
    private static readonly TimeSpan Retention = TimeSpan.FromHours(24);
    private AccountMailWorkerSchedule Schedule => scheduleOptions.Value;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var leases = await ClaimAsync(stoppingToken);
                await Parallel.ForEachAsync(leases, new ParallelOptions
                {
                    CancellationToken = stoppingToken,
                    MaxDegreeOfParallelism = Schedule.MaxConcurrency
                }, ProcessAsync);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch
            {
                // Database/driver errors can include connection details. Expose only a safe code.
                health.Failed("OutboxUnavailable", clock.GetUtcNow());
                logger.LogWarning("Account mail outbox polling failed with safe code {FailureCode}", "OutboxUnavailable");
            }

            try
            {
                await Task.Delay(Schedule.PollInterval, clock, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
        }
    }

    private async Task<IReadOnlyList<MailLease>> ClaimAsync(CancellationToken cancellationToken)
    {
        using var scope = scopes.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var now = clock.GetUtcNow();
        var strategy = db.Database.CreateExecutionStrategy();
        return await strategy.ExecuteAsync(async () =>
        {
            db.ChangeTracker.Clear();
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            await db.AccountOutbox
                .Where(message => message.Status != "Pending" && message.Status != "Leased"
                    && message.CreatedUtc <= now.Subtract(Retention))
                .ExecuteDeleteAsync(cancellationToken);

            await db.AccountOutbox
                .Where(message => message.Status == "Pending" && message.ExpiresUtc <= now
                    || message.Status == "Leased" && message.LeaseUntilUtc <= now
                        && (message.ExpiresUtc <= now || message.Attempts >= options.Email.MaxAttempts))
                .ExecuteUpdateAsync(update => update
                    .SetProperty(message => message.Status, message => message.ExpiresUtc <= now ? "Cancelled" : "Failed")
                    .SetProperty(message => message.ProtectedPayload, "")
                    .SetProperty(message => message.LeaseId, (string?)null)
                    .SetProperty(message => message.LeaseUntilUtc, (DateTimeOffset?)null)
                    .SetProperty(message => message.FailureCode, message => message.ExpiresUtc <= now ? "Expired" : "AttemptsExhausted"),
                    cancellationToken);

            var due = await db.AccountOutbox.FromSqlInterpolated($"""
                    SELECT * FROM "AccountOutbox"
                    WHERE "ExpiresUtc" > {now}
                      AND "Attempts" < {options.Email.MaxAttempts}
                      AND (("Status" = 'Pending' AND "NextAttemptUtc" <= {now})
                        OR ("Status" = 'Leased' AND "LeaseUntilUtc" <= {now}))
                    ORDER BY "NextAttemptUtc", "CreatedUtc"
                    LIMIT {Schedule.BatchSize}
                    FOR UPDATE SKIP LOCKED
                    """)
                .ToListAsync(cancellationToken);

            var leases = new List<MailLease>(due.Count);
            foreach (var message in due)
            {
                var leaseId = Guid.NewGuid().ToString("N");
                message.Status = "Leased";
                message.LeaseId = leaseId;
                message.LeaseUntilUtc = now.Add(Schedule.LeaseDuration);
                message.Attempts++;
                leases.Add(new MailLease(message.Id, message.MessageId, message.UserId, message.Purpose,
                    message.ProtectedPayload, message.ExpiresUtc, leaseId, message.Attempts));
            }

            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);
            return leases;
        });
    }

    private async ValueTask ProcessAsync(MailLease lease, CancellationToken cancellationToken)
    {
        using var scope = scopes.CreateScope();
        var services = scope.ServiceProvider;
        var db = services.GetRequiredService<AppDbContext>();
        var now = clock.GetUtcNow();
        try
        {
            if (lease.ExpiresUtc <= now)
            {
                await CompleteAsync(db, lease, "Cancelled", "Expired", now, cancellationToken);
                return;
            }

            var protector = services.GetRequiredService<AccountMailPayloadProtector>();
            var payload = protector.Unprotect(lease.ProtectedPayload);
            if (payload.Version != 1
                || payload.UserId != lease.UserId
                || !AccountMailOutbox.TryParsePurpose(lease.Purpose, out var storedPurpose)
                || storedPurpose != payload.Purpose)
            {
                await CompleteAsync(db, lease, "Failed", "PayloadInvalid", now, cancellationToken);
                return;
            }

            if (payload.LinkExpiresUtc <= now)
            {
                await CompleteAsync(db, lease, "Cancelled", "Expired", now, cancellationToken);
                return;
            }

            var users = services.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(payload.UserId);
            if (!await IsCurrentAndEligibleAsync(users, user, payload))
            {
                await CompleteAsync(db, lease, "Cancelled", "AccountChanged", now, cancellationToken);
                return;
            }

            var message = services.GetRequiredService<AccountEmailLinkFactory>().Create(payload, lease.MessageId);
            await services.GetRequiredService<IAccountMailTransport>().SendAsync(message, cancellationToken);
            await CompleteAsync(db, lease, "Sent", null, clock.GetUtcNow(), cancellationToken);
            health.Sent();
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Leave the committed lease in place. Another worker reclaims it after expiry.
        }
        catch (Exception exception)
        {
            var (failureCode, transient) = Classify(exception);
            var failedAt = clock.GetUtcNow();
            if (transient && lease.Attempts < options.Email.MaxAttempts)
            {
                var delay = lease.Attempts == 1 ? Schedule.FirstRetryDelay : Schedule.SecondRetryDelay;
                var retryAt = failedAt.Add(delay);
                if (retryAt < lease.ExpiresUtc)
                {
                    await RetryAsync(db, lease, retryAt, cancellationToken);
                    health.Retried();
                    return;
                }
            }

            await CompleteAsync(db, lease, "Failed", failureCode, failedAt, cancellationToken);
            health.Failed(failureCode, failedAt);
            logger.LogWarning("Account mail delivery stopped with safe code {FailureCode}", failureCode);
        }
    }

    private static async Task<bool> IsCurrentAndEligibleAsync(
        UserManager<ApplicationUser> users,
        ApplicationUser? user,
        AccountMailPayload payload)
    {
        if (user is null || !string.Equals(user.SecurityStamp, payload.SecurityStamp, StringComparison.Ordinal))
        {
            return false;
        }

        var tokenOptions = users.Options.Tokens;
        return payload.Purpose switch
        {
            AccountMailPurpose.Confirmation => !user.EmailConfirmed
                && string.Equals(user.Email, payload.Recipient, StringComparison.OrdinalIgnoreCase)
                && await users.VerifyUserTokenAsync(user, tokenOptions.EmailConfirmationTokenProvider, "EmailConfirmation", payload.Token),
            AccountMailPurpose.PasswordReset => user.EmailConfirmed
                && string.Equals(user.Email, payload.Recipient, StringComparison.OrdinalIgnoreCase)
                && await users.VerifyUserTokenAsync(user, tokenOptions.PasswordResetTokenProvider, "ResetPassword", payload.Token),
            AccountMailPurpose.EmailChange => user.EmailConfirmed
                && payload.TargetEmail is { Length: > 0 } target
                && string.Equals(payload.Recipient, target, StringComparison.OrdinalIgnoreCase)
                && !string.Equals(user.Email, target, StringComparison.OrdinalIgnoreCase)
                && await users.VerifyUserTokenAsync(user, tokenOptions.ChangeEmailTokenProvider, $"ChangeEmail:{target}", payload.Token),
            _ => false
        };
    }

    private static async Task RetryAsync(AppDbContext db, MailLease lease, DateTimeOffset nextAttemptUtc, CancellationToken cancellationToken)
    {
        await db.AccountOutbox.Where(message => message.Id == lease.Id
                && message.Status == "Leased" && message.LeaseId == lease.LeaseId)
            .ExecuteUpdateAsync(update => update
                .SetProperty(message => message.Status, "Pending")
                .SetProperty(message => message.NextAttemptUtc, nextAttemptUtc)
                .SetProperty(message => message.LeaseId, (string?)null)
                .SetProperty(message => message.LeaseUntilUtc, (DateTimeOffset?)null), cancellationToken);
    }

    private static async Task CompleteAsync(
        AppDbContext db,
        MailLease lease,
        string status,
        string? failureCode,
        DateTimeOffset now,
        CancellationToken cancellationToken)
    {
        await db.AccountOutbox.Where(message => message.Id == lease.Id
                && message.Status == "Leased" && message.LeaseId == lease.LeaseId)
            .ExecuteUpdateAsync(update => update
                .SetProperty(message => message.Status, status)
                .SetProperty(message => message.ProtectedPayload, "")
                .SetProperty(message => message.LeaseId, (string?)null)
                .SetProperty(message => message.LeaseUntilUtc, (DateTimeOffset?)null)
                .SetProperty(message => message.FailureCode, failureCode)
                .SetProperty(message => message.NextAttemptUtc, now), cancellationToken);
    }

    private static (string FailureCode, bool Transient) Classify(Exception exception) => exception switch
    {
        CryptographicException => ("PayloadInvalid", false),
        MailKit.Security.AuthenticationException or SslHandshakeException or System.Security.Authentication.AuthenticationException => ("TransportAuthentication", false),
        SmtpCommandException command when (int)command.StatusCode >= 500 => ("RecipientRejected", false),
        SmtpCommandException => ("SmtpTemporaryFailure", true),
        SmtpProtocolException or IOException or SocketException or TimeoutException
            or OperationCanceledException => ("TransportUnavailable", true),
        _ => ("ProcessingFailure", false)
    };

    private sealed record MailLease(
        Guid Id,
        string MessageId,
        string UserId,
        string Purpose,
        string ProtectedPayload,
        DateTimeOffset ExpiresUtc,
        string LeaseId,
        int Attempts);
}

internal sealed class AccountMailWorkerSchedule
{
    public TimeSpan PollInterval { get; set; } = TimeSpan.FromSeconds(5);
    public TimeSpan LeaseDuration { get; set; } = TimeSpan.FromSeconds(45);
    public TimeSpan FirstRetryDelay { get; set; } = TimeSpan.FromSeconds(30);
    public TimeSpan SecondRetryDelay { get; set; } = TimeSpan.FromMinutes(2);
    public int BatchSize { get; set; } = 10;
    public int MaxConcurrency { get; set; } = 5;
}
