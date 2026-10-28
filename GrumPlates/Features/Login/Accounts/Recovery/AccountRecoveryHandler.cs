using GrumPlates.Core.Features.Login.UseCases.Shared;
using GrumPlates.Features.Login.Accounts.Email;
using GrumPlates.Features.Login.Accounts.Security;
using Microsoft.Extensions.Options;
using static GrumPlates.Features.Login.Accounts.Security.AccountResults;

namespace GrumPlates.Features.Login.Accounts.Recovery;

internal sealed class AccountRecoveryHandler(
    AccountMailOutbox email,
    AccountMutationTransactions transactions,
    IOptions<AccountOptions> options)
{
    // The Blazor adapter selects MFA recovery internally; this capability is never bound from request data.
    public async Task<IResult> ForgotAsync(AccountEmailRequest request, CancellationToken cancellationToken, bool supportsTwoFactor = false)
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
                if (user.EmailConfirmed && (supportsTwoFactor || !user.TwoFactorEnabled))
                {
                    var token = await users.GeneratePasswordResetTokenAsync(user);
                    await outbox.EnqueueAsync(user, AccountMailPurpose.PasswordReset, user.Email!, token,
                        cancellationToken: cancellationToken);
                }
            }
            return Accepted(PublicEmailResponse);
        }, DeliveryUnavailable(), cancellationToken);
    }

    public async Task<IResult> ResetAsync(AccountResetPasswordRequest request, CancellationToken cancellationToken, bool supportsTwoFactor = false)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        var (response, _) = await transactions.ExecuteAsync(request.UserId, async (attempt, user) =>
        {
            var users = attempt.Users;
            if (!user.EmailConfirmed || (!supportsTwoFactor && user.TwoFactorEnabled)) return (InvalidToken(), false);
            var result = await users.ResetPasswordAsync(user, request.Token, request.NewPassword);
            if (!result.Succeeded)
            {
                var safe = result.Errors.Any(error => error.Code == "InvalidToken")
                    ? InvalidToken()
                    : IdentityFailure(result, "newPassword");
                return (safe, false);
            }
            result = await users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (IdentityFailure(result), false);
            return (Success("Password reset. Sign in with your new password."), true);
        }, cancellationToken);
        return response;
    }
}
