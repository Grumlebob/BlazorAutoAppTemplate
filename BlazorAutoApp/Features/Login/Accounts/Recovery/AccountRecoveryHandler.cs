using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts.Email;
using BlazorAutoApp.Features.Login.Accounts.Security;
using BlazorAutoApp.Features.Login.Accounts.Session;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using System.Security.Claims;
using static BlazorAutoApp.Features.Login.Accounts.Security.AccountResults;

namespace BlazorAutoApp.Features.Login.Accounts.Recovery;

internal sealed class AccountRecoveryHandler(
    AccountMailOutbox email,
    AccountMutationTransactions transactions,
    IOptions<AccountOptions> options)
{
    public async Task<IResult> ForgotAsync(AccountEmailRequest request, CancellationToken cancellationToken)
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
        }, DeliveryUnavailable(), cancellationToken);
    }

    public async Task<IResult> ResetAsync(AccountResetPasswordRequest request, CancellationToken cancellationToken)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        var (response, _) = await transactions.ExecuteAsync(request.UserId, async (attempt, user) =>
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
        }, cancellationToken);
        return response;
    }
}
