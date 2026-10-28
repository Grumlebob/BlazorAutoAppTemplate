using GrumPlates.Core.Features.Login.UseCases.Shared;
using GrumPlates.Features.Login.Account;
using GrumPlates.Features.Login.Accounts.Email;
using GrumPlates.Features.Login.Accounts.Security;
using Microsoft.Extensions.Options;
using static GrumPlates.Features.Login.Accounts.Security.AccountResults;

namespace GrumPlates.Features.Login.Accounts.Registration;

internal sealed class AccountRegistrationHandler(
    AccountMailOutbox email,
    AccountMutationTransactions transactions,
    IOptions<AccountOptions> options)
{
    public async Task<IResult> RegisterAsync(AccountRegisterRequest request, CancellationToken cancellationToken)
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
                return IdentityFailure(result);
            }

            await outbox.LockUserForUpdateAsync(user, cancellationToken);
            var token = await users.GenerateEmailConfirmationTokenAsync(user);
            await outbox.EnqueueAsync(user, AccountMailPurpose.Confirmation, user.Email!, token,
                cancellationToken: cancellationToken);
            return Accepted(PublicEmailResponse);
        }, DeliveryUnavailable(), cancellationToken);
    }

    public async Task<IResult> ResendAsync(AccountEmailRequest request, CancellationToken cancellationToken)
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
        }, DeliveryUnavailable(), cancellationToken);
    }

    public async Task<IResult> ConfirmAsync(AccountConfirmEmailRequest request, CancellationToken cancellationToken)
    {
        if (!options.Value.EmailEnabled) return EmailDisabled();
        var (response, _) = await transactions.ExecuteAsync(request.UserId, async (attempt, user) =>
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
                if (!result.Succeeded) return (IdentityFailure(result, "newPassword"), false);
            }

            result = await users.AddPasswordAsync(user, request.NewPassword);
            if (!result.Succeeded) return (IdentityFailure(result, "newPassword"), false);
            result = await users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (IdentityFailure(result), false);
            return (Success("Email confirmed. You can now sign in."), true);
        }, cancellationToken);
        return response;
    }
}
