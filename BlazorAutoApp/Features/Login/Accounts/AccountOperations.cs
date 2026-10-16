using System.Data.Common;
using System.Security.Claims;
using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts.Session;
using BlazorAutoApp.Features.Login.Accounts.Email;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Options;
using Npgsql;

namespace BlazorAutoApp.Features.Login.Accounts;

internal sealed class AccountOperations(
    UserManager<ApplicationUser> users,
    SignInManager<ApplicationUser> signIn,
    IDbContextFactory<AppDbContext> dbFactory,
    IServiceScopeFactory scopes,
    IHttpContextAccessor accessor,
    AccountSessionOperations sessions,
    IOptions<AccountOptions> options,
    IOptions<IdentityOptions> identityOptions,
    IOptions<Microsoft.AspNetCore.Http.Json.JsonOptions> jsonOptions,
    AccountMailOutbox email)
{
    private HttpContext Context => accessor.HttpContext ?? throw new InvalidOperationException("An account request requires an HTTP context.");
    private static IResult Success(string message) => Results.Ok(new AccountMessage(message));
    private static IResult Accepted(string message) => Results.Accepted(value: new AccountMessage(message));
    private static IResult Invalid(string detail = "The request could not be completed.") =>
        AccountProblem.Create(400, "RequestInvalid", "Account request failed", detail);
    private static IResult InvalidToken() =>
        AccountProblem.Create(400, "TokenInvalid", "The link could not be completed", "The link is invalid, expired or unavailable.");
    private static IResult Denied() =>
        AccountProblem.Create(401, "CredentialsInvalid", "Sign-in failed", "Check your credentials and account confirmation, then try again.");
    private static IResult EmailDisabled() =>
        AccountProblem.Create(403, "CapabilityDisabled", "This account operation is unavailable");
    private static IResult SessionRequired() =>
        AccountProblem.Create(401, "AuthenticationRequired", "Sign-in required");
    private static IResult DeliveryUnavailable() =>
        AccountProblem.Create(503, "AccountServiceUnavailable", "Account requests are temporarily unavailable", "Please try again later.");
    private static IResult Conflict() =>
        AccountProblem.Create(409, "AccountConflict", "The account could not be updated", "The request conflicts with the current account state.");
    private static IResult ExportTooLarge() =>
        AccountProblem.Create(413, "ExportTooLarge", "Account export too large", "The account data exceeds the export limits.");
    private const string PublicEmailResponse = "Request received. Check your email if applicable; use resend if it does not arrive.";
    private const int MaximumExportRecords = 10_000;
    private const int MaximumExportBytes = 10 * 1024 * 1024;

    private static IResult Check(IdentityResult result, string success, string? passwordField = null)
    {
        if (result.Succeeded) return Success(success);
        var codes = result.Errors.Select(error => error.Code).ToArray();
        if (codes.Any(code => code is "DuplicateEmail" or "DuplicateUserName"))
        {
            return AccountProblem.Create(409, "AccountConflict", "The account could not be updated", "The request conflicts with the current account state.");
        }
        if (codes.Any(code => code.StartsWith("Password", StringComparison.Ordinal)) || passwordField is not null)
        {
            return AccountProblem.Validation(400, "PasswordRejected", "Password rejected", "Choose a password that meets the account password policy.",
                new Dictionary<string, string[]> { [passwordField ?? "password"] = ["The password does not meet the account password policy."] });
        }
        return AccountProblem.Validation(400, "RequestInvalid", "Account request failed", "The request could not be completed.",
            new Dictionary<string, string[]> { ["account"] = ["The request could not be completed."] });
    }

    public async Task<IResult> LogoutAllAsync(AccountPasswordRequest request)
    {
        var userId = users.GetUserId(Context.User);
        if (string.IsNullOrEmpty(userId)) return Denied();
        var revoked = false;
        var (response, _) = await ExecuteLockedUserTransactionAsync(userId, async (attempt, user) =>
        {
            if (user.TwoFactorEnabled) return (Denied(), false);
            var passwordCheck = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
            if (!passwordCheck.Succeeded) return (Denied(), true);
            var result = await attempt.Users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (Check(result, ""), false);
            revoked = true;
            return (Success("All sessions were signed out."), true);
        }, Context.RequestAborted, requireCurrentCookie: true);
        return revoked ? await sessions.LogoutAsync() : response;
    }

    public async Task<IResult> RegisterAsync(AccountRegisterRequest request)
    {
        if (!options.Value.RegistrationEnabled) return EmailDisabled();
        return await email.RunAdmittedAsync(async (admission, cancellationToken) =>
        {
            var users = admission.Users;
            var outbox = admission.Outbox;
            var address = request.Email.Trim();
            if (await users.FindByEmailAsync(address) is not null) return Accepted(PublicEmailResponse);
            var user = new ApplicationUser { UserName = address, Email = address };
            var result = await users.CreateAsync(user);
            if (!result.Succeeded)
            {
                if (result.Errors.Any(error => error.Code is "DuplicateEmail" or "DuplicateUserName")) return Accepted(PublicEmailResponse);
                return Check(result, PublicEmailResponse);
            }

            await outbox.LockUserForUpdateAsync(user, cancellationToken);
            var token = await users.GenerateEmailConfirmationTokenAsync(user);
            await outbox.EnqueueAsync(user, AccountMailPurpose.Confirmation, user.Email!, token,
                cancellationToken: cancellationToken);
            return Accepted(PublicEmailResponse);
        }, DeliveryUnavailable(), Context.RequestAborted);
    }

    public async Task<IResult> ResendAsync(AccountEmailRequest request)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        return await email.RunAdmittedAsync(async (admission, cancellationToken) =>
        {
            var users = admission.Users;
            var outbox = admission.Outbox;
            var user = await users.FindByEmailAsync(request.Email.Trim());
            if (user is not null)
            {
                await outbox.LockUserForUpdateAsync(user, cancellationToken);
                if (!user.EmailConfirmed)
                {
                    var token = await users.GenerateEmailConfirmationTokenAsync(user);
                    await outbox.EnqueueAsync(user, AccountMailPurpose.Confirmation, user.Email!, token,
                        cancellationToken: cancellationToken);
                }
            }
            return Accepted(PublicEmailResponse);
        }, DeliveryUnavailable(), Context.RequestAborted);
    }

    public async Task<IResult> ConfirmAsync(AccountConfirmEmailRequest request)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        var (response, _) = await ExecuteLockedUserTransactionAsync(request.UserId, async (attempt, user) =>
        {
            var users = attempt.Users;
            var tokenOptions = users.Options.Tokens;
            if (user.EmailConfirmed || !await users.VerifyUserTokenAsync(user,
                    tokenOptions.EmailConfirmationTokenProvider, "EmailConfirmation", request.Token))
            {
                return (InvalidToken(), false);
            }

            var result = await users.ConfirmEmailAsync(user, request.Token);
            if (!result.Succeeded) return (InvalidToken(), false);
            if (await users.HasPasswordAsync(user))
            {
                result = await users.RemovePasswordAsync(user);
                if (!result.Succeeded) return (Check(result, "", "newPassword"), false);
            }

            result = await users.AddPasswordAsync(user, request.NewPassword);
            if (!result.Succeeded) return (Check(result, "", "newPassword"), false);
            result = await users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (Check(result, ""), false);
            return (Success("Email confirmed. You can now sign in."), true);
        }, Context.RequestAborted);
        return response;
    }

    public async Task<IResult> ForgotAsync(AccountEmailRequest request)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        return await email.RunAdmittedAsync(async (admission, cancellationToken) =>
        {
            var users = admission.Users;
            var outbox = admission.Outbox;
            var user = await users.FindByEmailAsync(request.Email.Trim());
            if (user is not null)
            {
                await outbox.LockUserForUpdateAsync(user, cancellationToken);
                if (user.EmailConfirmed && !user.TwoFactorEnabled)
                {
                    var token = await users.GeneratePasswordResetTokenAsync(user);
                    await outbox.EnqueueAsync(user, AccountMailPurpose.PasswordReset, user.Email!, token,
                        cancellationToken: cancellationToken);
                }
            }
            return Accepted(PublicEmailResponse);
        }, DeliveryUnavailable(), Context.RequestAborted);
    }

    public async Task<IResult> ResetAsync(AccountResetPasswordRequest request)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        var (response, _) = await ExecuteLockedUserTransactionAsync(request.UserId, async (attempt, user) =>
        {
            var users = attempt.Users;
            if (!user.EmailConfirmed || user.TwoFactorEnabled) return (InvalidToken(), false);
            var result = await users.ResetPasswordAsync(user, request.Token, request.NewPassword);
            if (!result.Succeeded)
            {
                var safe = result.Errors.Any(error => error.Code == "InvalidToken")
                    ? InvalidToken()
                    : Check(result, "", "newPassword");
                return (safe, false);
            }
            result = await users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (Check(result, ""), false);
            return (Success("Password reset. Sign in with your new password."), true);
        }, Context.RequestAborted);
        return response;
    }

    public async Task<IResult> ChangePasswordAsync(AccountChangePasswordRequest request)
    {
        var userId = users.GetUserId(Context.User);
        if (string.IsNullOrEmpty(userId)) return Denied();
        var passwordChanged = false;
        var (response, _) = await ExecuteLockedUserTransactionAsync(userId, async (attempt, user) =>
        {
            passwordChanged = false;
            if (user.TwoFactorEnabled) return (Denied(), false);
            var passwordCheck = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
            if (!passwordCheck.Succeeded) return (Denied(), true);
            var result = await attempt.Users.ChangePasswordAsync(user, request.Password, request.NewPassword);
            if (!result.Succeeded) return (Check(result, ""), false);
            result = await attempt.Users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (Check(result, ""), false);
            passwordChanged = true;
            return (Success("Password changed. Sign in again."), true);
        }, Context.RequestAborted, requireCurrentCookie: true);
        if (passwordChanged) await signIn.SignOutAsync();
        return response;
    }

    public async Task<IResult> ChangeEmailAsync(AccountChangeEmailRequest request)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        return await email.RunAdmittedAsync(async (admission, cancellationToken) =>
        {
            var users = admission.Users;
            var userId = users.GetUserId(Context.User);
            if (string.IsNullOrEmpty(userId)) return SessionRequired();
            var user = await users.FindByIdAsync(userId);
            if (user is null) return SessionRequired();
            await admission.Outbox.LockUserForUpdateAsync(user, cancellationToken);
            if (!CurrentCookieMatches(user)) return SessionRequired();
            if (user.TwoFactorEnabled) return Denied();
            var passwordCheck = await admission.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
            if (!passwordCheck.Succeeded) return Denied();

            var targetEmail = request.Email.Trim();
            if (string.Equals(user.Email, targetEmail, StringComparison.OrdinalIgnoreCase)
                || await users.FindByEmailAsync(targetEmail) is not null)
            {
                return Accepted("Request received. If this change can proceed, check the new address for a confirmation message.");
            }

            var token = await users.GenerateChangeEmailTokenAsync(user, targetEmail);
            await admission.Outbox.EnqueueAsync(user, AccountMailPurpose.EmailChange, targetEmail, token, targetEmail, cancellationToken);
            return Accepted("Request received. If this change can proceed, check the new address for a confirmation message.");
        }, DeliveryUnavailable(), Context.RequestAborted);
    }

    public async Task<IResult> ConfirmEmailChangeAsync(AccountConfirmEmailChangeRequest request)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        var (response, committed) = await ExecuteLockedUserTransactionAsync(request.UserId, async (attempt, user) =>
        {
            var users = attempt.Users;
            if (string.Equals(user.Email, request.Email, StringComparison.OrdinalIgnoreCase)) return (InvalidToken(), false);
            var tokenOptions = users.Options.Tokens;
            if (!await users.VerifyUserTokenAsync(user, tokenOptions.ChangeEmailTokenProvider,
                    $"ChangeEmail:{request.Email}", request.Token))
            {
                return (InvalidToken(), false);
            }

            var changed = await users.ChangeEmailAsync(user, request.Email, request.Token);
            if (!changed.Succeeded) return (Check(changed, ""), false);
            changed = await users.SetUserNameAsync(user, request.Email);
            if (!changed.Succeeded) return (Check(changed, ""), false);
            changed = await users.UpdateSecurityStampAsync(user);
            if (!changed.Succeeded) return (Check(changed, ""), false);
            return (Success("Email changed. Sign in again."), true);
        }, Context.RequestAborted);
        if (committed) await signIn.SignOutAsync();
        return response;
    }

    public async Task<IResult> ExportAsync(AccountPasswordRequest request)
    {
        var userId = users.GetUserId(Context.User);
        if (string.IsNullOrEmpty(userId)) return SessionRequired();
        try
        {
            var (response, _) = await ExecuteLockedUserTransactionAsync(userId, async (attempt, user) =>
            {
                if (user.TwoFactorEnabled) return (Denied(), false);
                var proof = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
                if (!proof.Succeeded) return (Denied(), true);

                var books = await attempt.Db.UserBooks.AsNoTracking()
                    .Where(book => book.OwnerUserId == user.Id)
                    .OrderBy(book => book.BookId)
                    .Take(MaximumExportRecords + 1)
                    .Select(book => new AccountExportBook(book.BookId, book.Book.Title, book.Book.Author, book.Book.Url))
                    .ToListAsync(Context.RequestAborted);
                if (books.Count > MaximumExportRecords) return (ExportTooLarge(), true);

                var profile = new AccountProfile(user.Id, user.Email ?? "", (await attempt.Users.GetRolesAsync(user)).ToArray());
                var export = new AccountExport(profile, books);
                var bytes = System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(export, jsonOptions.Value.SerializerOptions);
                return (bytes.Length > MaximumExportBytes ? ExportTooLarge() : Results.Ok(export), true);
            }, Context.RequestAborted, requireCurrentCookie: true);
            return response;
        }
        catch (Exception exception) when (IsPersistenceFailure(exception))
        {
            return DeliveryUnavailable();
        }
    }

    public async Task<IResult> DeleteAsync(AccountPasswordRequest request)
    {
        var userId = users.GetUserId(Context.User);
        if (string.IsNullOrEmpty(userId)) return SessionRequired();
        var accountDeleted = false;
        try
        {
            var (response, _) = await ExecuteLockedUserTransactionAsync(userId, async (attempt, user) =>
            {
                if (user.TwoFactorEnabled) return (Denied(), false);
                var proof = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
                if (!proof.Succeeded) return (Denied(), true);

                await attempt.Db.AccountOutbox
                    .Where(message => message.UserId == user.Id && (message.Status == "Pending" || message.Status == "Leased"))
                    .ExecuteUpdateAsync(update => update
                        .SetProperty(message => message.Status, "Cancelled")
                        .SetProperty(message => message.ProtectedPayload, "")
                        .SetProperty(message => message.FailureCode, "AccountDeleted")
                        .SetProperty(message => message.LeaseId, (string?)null)
                        .SetProperty(message => message.LeaseUntilUtc, (DateTimeOffset?)null), Context.RequestAborted);

                var privateBooks = await attempt.Db.UserBooks
                    .Where(mapping => mapping.OwnerUserId == user.Id
                        && !attempt.Db.AuthorBooks.Any(catalog => catalog.BookId == mapping.BookId))
                    .Select(mapping => mapping.Book)
                    .ToListAsync(Context.RequestAborted);
                attempt.Db.Books.RemoveRange(privateBooks);
                await attempt.Db.SaveChangesAsync(Context.RequestAborted);

                var result = await attempt.Users.DeleteAsync(user);
                if (!result.Succeeded) return (Check(result, ""), false);
                accountDeleted = true;
                return (Success("Account deleted."), true);
            }, Context.RequestAborted, requireCurrentCookie: true, verifyUserDeleted: true);
            if (accountDeleted) await signIn.SignOutAsync();
            return response;
        }
        catch (Exception exception) when (IsPersistenceFailure(exception))
        {
            return DeliveryUnavailable();
        }
    }

    private static bool IsPersistenceFailure(Exception exception) =>
        exception is DbException or DbUpdateException or TimeoutException or RetryLimitExceededException;

    private async Task<(IResult Response, bool Committed)> ExecuteLockedUserTransactionAsync(
        string userId,
        Func<AccountMutationContext, ApplicationUser, Task<(IResult Response, bool Commit)>> operation,
        CancellationToken cancellationToken,
        bool requireCurrentCookie = false,
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
                        return (requireCurrentCookie ? SessionRequired() : InvalidToken(), false);
                    }
                    if (!await LockAndReloadUserAsync(attempt.Db, user, attemptCancellation))
                    {
                        await transaction.RollbackAsync(attemptCancellation);
                        return (requireCurrentCookie ? SessionRequired() : InvalidToken(), false);
                    }
                    if (requireCurrentCookie && !CurrentCookieMatches(user))
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

    private bool CurrentCookieMatches(ApplicationUser user)
    {
        var claimType = identityOptions.Value.ClaimsIdentity.SecurityStampClaimType;
        var cookieStamp = Context.User.FindFirstValue(claimType);
        return !string.IsNullOrEmpty(cookieStamp)
            && string.Equals(cookieStamp, user.SecurityStamp, StringComparison.Ordinal);
    }

    private static async Task<bool> LockAndReloadUserAsync(AppDbContext db, ApplicationUser user, CancellationToken cancellationToken)
    {
        await using var command = db.Database.GetDbConnection().CreateCommand();
        command.Transaction = db.Database.CurrentTransaction!.GetDbTransaction();
        command.CommandText = "SELECT 1 FROM \"AspNetUsers\" WHERE \"Id\" = @userId FOR UPDATE";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "userId";
        parameter.Value = user.Id;
        command.Parameters.Add(parameter);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken)) return false;
        await reader.DisposeAsync();
        await db.Entry(user).ReloadAsync(cancellationToken);
        return true;
    }

    private sealed record AccountMutationContext(
        AppDbContext Db,
        UserManager<ApplicationUser> Users,
        SignInManager<ApplicationUser> SignIn);

    private sealed class AccountMutationAttempt(string userId, string operationId, bool verifyUserDeleted)
    {
        public string UserId { get; } = userId;
        public string OperationId { get; } = operationId;
        public bool VerifyUserDeleted { get; } = verifyUserDeleted;
        public (IResult Response, bool Committed)? Result { get; set; }
    }

}
