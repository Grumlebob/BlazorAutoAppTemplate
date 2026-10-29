using System.Security.Claims;
using GrumPlates.Core.Features.Accounts.Contracts;
using GrumPlates.Features.Accounts.Email;
using GrumPlates.Features.Accounts.Security;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using static GrumPlates.Features.Accounts.Security.AccountResults;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Features.Accounts.Management;

internal sealed class AccountEmailChangeHandler(
    AccountMailOutbox email,
    AccountMutationTransactions transactions,
    SignInManager<ApplicationUser> signIn,
    IOptions<AccountOptions> options)
{
    public async Task<IResult> ChangeEmailAsync(AccountChangeEmailRequest request, ClaimsPrincipal principal, CancellationToken cancellationToken)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        return await email.RunAdmittedAsync(async (admission, cancellationToken) =>
        {
            var users = admission.Users;
            var userId = users.GetUserId(principal);
            if (string.IsNullOrEmpty(userId)) return SessionRequired();
            var user = await users.FindByIdAsync(userId);
            if (user is null) return SessionRequired();
            await admission.Outbox.LockUserForUpdateAsync(user, cancellationToken);
            if (!transactions.CurrentCookieMatches(user, principal)) return SessionRequired();
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
        }, DeliveryUnavailable(), cancellationToken);
    }

    public async Task<IResult> ConfirmEmailChangeAsync(AccountConfirmEmailChangeRequest request, CancellationToken cancellationToken)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        var (response, committed) = await transactions.ExecuteAsync(request.UserId, async (attempt, user) =>
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
            if (!changed.Succeeded) return (IdentityFailure(changed), false);
            changed = await users.SetUserNameAsync(user, request.Email);
            if (!changed.Succeeded) return (IdentityFailure(changed), false);
            changed = await users.UpdateSecurityStampAsync(user);
            if (!changed.Succeeded) return (IdentityFailure(changed), false);
            return (Success("Email changed. Sign in again."), true);
        }, cancellationToken);
        if (committed) await signIn.SignOutAsync();
        return response;
    }
}
