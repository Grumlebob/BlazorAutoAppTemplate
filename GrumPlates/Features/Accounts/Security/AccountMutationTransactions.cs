using System.Security.Claims;
using GrumPlates.Features.Accounts.Persistence;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Options;
using Npgsql;
using static GrumPlates.Features.Accounts.Security.AccountResults;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Features.Accounts.Security;

internal sealed class AccountMutationTransactions(
    IDbContextFactory<AppDbContext> dbFactory,
    IServiceScopeFactory scopes,
    IOptions<IdentityOptions> identityOptions)
{
    public async Task<(IResult Response, bool Committed)> ExecuteAsync(
        string userId,
        Func<AccountMutationContext, ApplicationUser, Task<(IResult Response, bool Commit)>> operation,
        CancellationToken cancellationToken,
        ClaimsPrincipal? principal = null,
        bool verifyUserDeleted = false)
    {
        await using var strategyDb = await dbFactory.CreateDbContextAsync(cancellationToken);
        var strategy = strategyDb.Database.CreateExecutionStrategy();
        var mutationState = new AccountMutationAttempt(userId, Guid.NewGuid().ToString("N"), verifyUserDeleted);
        try
        {
            return await strategy.ExecuteAsync(
                mutationState,
                async (_, state, attemptCancellation) =>
                {
                    await using var scope = scopes.CreateAsyncScope();
                    var services = scope.ServiceProvider;
                    var attempt = new AccountMutationContext(
                        services.GetRequiredService<AppDbContext>(),
                        services.GetRequiredService<UserManager<ApplicationUser>>(),
                        services.GetRequiredService<SignInManager<ApplicationUser>>());
                    await using var transaction = await attempt.Db.Database.BeginTransactionAsync(attemptCancellation);
                    var user = await attempt.Users.FindByIdAsync(state.UserId);
                    if (user is null)
                    {
                        await transaction.RollbackAsync(attemptCancellation);
                        return (principal is not null ? SessionRequired() : InvalidToken(), false);
                    }
                    if (!await AccountUserLock.TryLockAndReloadAsync(attempt.Db, user, attemptCancellation))
                    {
                        await transaction.RollbackAsync(attemptCancellation);
                        return (principal is not null ? SessionRequired() : InvalidToken(), false);
                    }
                    if (principal is not null && !CurrentCookieMatches(user, principal))
                    {
                        await transaction.RollbackAsync(attemptCancellation);
                        return (SessionRequired(), false);
                    }

                    var (response, commit) = await operation(attempt, user);
                    if (commit)
                    {
                        state.Result = (response, commit);
                        if (!state.VerifyUserDeleted)
                        {
                            // This stable per-request marker commits with the account mutation and lets
                            // EF distinguish a lost commit acknowledgement from a rolled-back attempt.
                            user.ConcurrencyStamp = state.OperationId;
                        }
                        await attempt.Db.SaveChangesAsync(attemptCancellation);
                        await transaction.CommitAsync(attemptCancellation);
                    }
                    else
                    {
                        await transaction.RollbackAsync(attemptCancellation);
                    }
                    return (response, commit);
                },
                async (_, state, verifyCancellation) =>
                {
                    if (state.Result is null)
                    {
                        return new ExecutionResult<(IResult Response, bool Committed)>(false, default!);
                    }

                    await using var verifyDb = await dbFactory.CreateDbContextAsync(verifyCancellation);
                    var succeeded = await verifyDb.Users.AsNoTracking().AnyAsync(
                        candidate => candidate.Id == state.UserId && candidate.ConcurrencyStamp == state.OperationId,
                        verifyCancellation);
                    if (!succeeded && state.VerifyUserDeleted && state.Result.Value.Committed)
                    {
                        succeeded = !await verifyDb.Users.AsNoTracking()
                            .AnyAsync(candidate => candidate.Id == state.UserId, verifyCancellation);
                    }
                    return new ExecutionResult<(IResult Response, bool Committed)>(succeeded, state.Result.Value);
                },
                cancellationToken);
        }
        catch (DbUpdateException exception) when (IsEmailUniquenessConflict(exception))
        {
            return (Conflict(), false);
        }
    }

    private static bool IsEmailUniquenessConflict(DbUpdateException exception) =>
        exception.InnerException is PostgresException
        {
            SqlState: PostgresErrorCodes.UniqueViolation,
            ConstraintName: "EmailIndex" or "UserNameIndex"
        };

    public bool CurrentCookieMatches(ApplicationUser user, ClaimsPrincipal principal)
    {
        var claimType = identityOptions.Value.ClaimsIdentity.SecurityStampClaimType;
        var cookieStamp = principal.FindFirstValue(claimType);
        return !string.IsNullOrEmpty(cookieStamp)
            && string.Equals(cookieStamp, user.SecurityStamp, StringComparison.Ordinal);
    }

    private sealed class AccountMutationAttempt(string userId, string operationId, bool verifyUserDeleted)
    {
        public string UserId { get; } = userId;
        public string OperationId { get; } = operationId;
        public bool VerifyUserDeleted { get; } = verifyUserDeleted;
        public (IResult Response, bool Committed)? Result { get; set; }
    }
}

internal sealed record AccountMutationContext(
    AppDbContext Db,
    UserManager<ApplicationUser> Users,
    SignInManager<ApplicationUser> SignIn);
