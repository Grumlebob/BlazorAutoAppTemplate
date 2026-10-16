using System.Data.Common;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts.Persistence;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;

namespace BlazorAutoApp.Features.Login.Accounts.Email;

internal sealed class AccountMailOutbox(
    AppDbContext db,
    IDbContextFactory<AppDbContext> dbFactory,
    IServiceScopeFactory scopes,
    AccountMailPayloadProtector protector,
    TimeProvider clock,
    AccountMailHealth health)
{
    private const long AdmissionLockKey = 0x4241417574684D;
    private const int MaximumActiveJobs = 1000;
    private static readonly TimeSpan JobLifetime = TimeSpan.FromMinutes(45);
    private static readonly TimeSpan TokenLifetime = TimeSpan.FromHours(1);
    private static readonly TimeSpan Cooldown = TimeSpan.FromSeconds(60);
    private static readonly TimeSpan QuotaWindow = TimeSpan.FromHours(1);
    private const int MaximumIntentsPerHour = 5;
    private readonly HashSet<string> _lockedUserIds = new(StringComparer.Ordinal);
    private bool _admissionOpen;
    private Guid _stableMessageId;

    public async Task<T> RunAdmittedAsync<T>(
        Func<AccountMailAdmissionContext, CancellationToken, Task<T>> operation,
        T capacityOrUnavailableResult,
        CancellationToken cancellationToken)
    {
        try
        {
            var stableMessageId = Guid.NewGuid();
            await using var strategyDb = await dbFactory.CreateDbContextAsync(cancellationToken);
            var strategy = strategyDb.Database.CreateExecutionStrategy();
            return await strategy.ExecuteAsync(async () =>
            {
                await using var scope = scopes.CreateAsyncScope();
                var services = scope.ServiceProvider;
                var attemptOutbox = services.GetRequiredService<AccountMailOutbox>();
                return await attemptOutbox.RunAdmissionAttemptAsync(
                    services, operation, capacityOrUnavailableResult, stableMessageId, cancellationToken);
            });
        }
        catch (Exception exception) when (exception is DbException or DbUpdateException or TimeoutException)
        {
            health.Failed("OutboxUnavailable", clock.GetUtcNow());
            return capacityOrUnavailableResult;
        }
    }

    private async Task<T> RunAdmissionAttemptAsync<T>(
        IServiceProvider services,
        Func<AccountMailAdmissionContext, CancellationToken, Task<T>> operation,
        T capacityOrUnavailableResult,
        Guid stableMessageId,
        CancellationToken cancellationToken)
    {
        _lockedUserIds.Clear();
        _stableMessageId = stableMessageId;
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        _admissionOpen = true;
        try
        {
            await AcquireAdmissionLockAsync(cancellationToken);
            var activeCount = await db.AccountOutbox.CountAsync(message =>
                message.Status == "Pending" || message.Status == "Leased", cancellationToken);
            if (activeCount >= MaximumActiveJobs)
            {
                health.Failed("OutboxCapacity", clock.GetUtcNow());
                await transaction.RollbackAsync(cancellationToken);
                return capacityOrUnavailableResult;
            }

            var users = services.GetRequiredService<UserManager<ApplicationUser>>();
            var signIn = services.GetRequiredService<SignInManager<ApplicationUser>>();
            var result = await operation(new AccountMailAdmissionContext(users, signIn, this), cancellationToken);
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);
            return result;
        }
        finally
        {
            _admissionOpen = false;
            _lockedUserIds.Clear();
            _stableMessageId = Guid.Empty;
        }
    }

    public async Task LockUserForUpdateAsync(ApplicationUser user, CancellationToken cancellationToken)
    {
        EnsureAdmissionOpen();
        if (_lockedUserIds.Contains(user.Id)) return;

        await using var command = db.Database.GetDbConnection().CreateCommand();
        command.Transaction = db.Database.CurrentTransaction!.GetDbTransaction();
        command.CommandText = "SELECT 1 FROM \"AspNetUsers\" WHERE \"Id\" = @userId FOR UPDATE";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "userId";
        parameter.Value = user.Id;
        command.Parameters.Add(parameter);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken))
        {
            throw new DbUpdateException("The account disappeared during an admitted account mail operation.");
        }
        await reader.DisposeAsync();
        await db.Entry(user).ReloadAsync(cancellationToken);
        _lockedUserIds.Add(user.Id);
    }

    public async Task<AccountMailEnqueueResult> EnqueueAsync(
        ApplicationUser user,
        AccountMailPurpose purpose,
        string recipient,
        string token,
        string? targetEmail = null,
        CancellationToken cancellationToken = default)
    {
        EnsureAdmissionOpen();
        if (!_lockedUserIds.Contains(user.Id))
        {
            throw new InvalidOperationException("Lock the account row before adding account mail intent.");
        }

        var purposeName = ToStorageName(purpose);
        var now = clock.GetUtcNow();
        var active = await db.AccountOutbox.AnyAsync(message =>
            message.UserId == user.Id && message.Purpose == purposeName
            && (message.Status == "Pending" || message.Status == "Leased"), cancellationToken);
        if (active)
        {
            return AccountMailEnqueueResult.Suppressed;
        }

        var sinceHour = now.Subtract(QuotaWindow);
        var recent = await db.AccountOutbox.CountAsync(message =>
            message.UserId == user.Id && message.Purpose == purposeName && message.CreatedUtc >= sinceHour,
            cancellationToken);
        if (recent > 0)
        {
            var latest = await db.AccountOutbox
                .Where(message => message.UserId == user.Id && message.Purpose == purposeName)
                .MaxAsync(message => (DateTimeOffset?)message.CreatedUtc, cancellationToken);
            if (latest >= now.Subtract(Cooldown)) return AccountMailEnqueueResult.Suppressed;
        }
        if (recent >= MaximumIntentsPerHour) return AccountMailEnqueueResult.Suppressed;

        var id = _stableMessageId;
        var payload = new AccountMailPayload(
            Version: 1,
            Recipient: recipient,
            UserId: user.Id,
            Purpose: purpose,
            SecurityStamp: user.SecurityStamp ?? throw new InvalidOperationException("Identity security stamp is unavailable."),
            Token: token,
            TargetEmail: targetEmail,
            LinkExpiresUtc: now.Add(TokenLifetime));

        await db.AccountOutbox.AddAsync(new AccountOutboxMessage
        {
            Id = id,
            MessageId = $"{id:N}@account.local",
            UserId = user.Id,
            Purpose = purposeName,
            Status = "Pending",
            ProtectedPayload = protector.Protect(payload),
            CreatedUtc = now,
            ExpiresUtc = now.Add(JobLifetime),
            NextAttemptUtc = now,
            Attempts = 0
        }, cancellationToken);
        return AccountMailEnqueueResult.Queued;
    }

    private async Task AcquireAdmissionLockAsync(CancellationToken cancellationToken)
    {
        await using var command = db.Database.GetDbConnection().CreateCommand();
        command.Transaction = db.Database.CurrentTransaction!.GetDbTransaction();
        command.CommandText = "SELECT pg_advisory_xact_lock(@lockKey)";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "lockKey";
        parameter.Value = AdmissionLockKey;
        command.Parameters.Add(parameter);
        await command.ExecuteScalarAsync(cancellationToken);
    }

    private void EnsureAdmissionOpen()
    {
        if (!_admissionOpen || db.Database.CurrentTransaction is null)
        {
            throw new InvalidOperationException("Account mail admission must hold its database transaction.");
        }
    }

    public static string ToStorageName(AccountMailPurpose purpose) => purpose switch
    {
        AccountMailPurpose.Confirmation => "Confirmation",
        AccountMailPurpose.PasswordReset => "PasswordReset",
        AccountMailPurpose.EmailChange => "EmailChange",
        _ => throw new ArgumentOutOfRangeException(nameof(purpose))
    };

    public static bool TryParsePurpose(string value, out AccountMailPurpose purpose)
    {
        purpose = value switch
        {
            "Confirmation" => AccountMailPurpose.Confirmation,
            "PasswordReset" => AccountMailPurpose.PasswordReset,
            "EmailChange" => AccountMailPurpose.EmailChange,
            _ => (AccountMailPurpose)(-1)
        };
        return Enum.IsDefined(purpose);
    }
}

internal enum AccountMailEnqueueResult
{
    Queued,
    Suppressed
}

internal sealed record AccountMailAdmissionContext(
    UserManager<ApplicationUser> Users,
    SignInManager<ApplicationUser> SignIn,
    AccountMailOutbox Outbox);
