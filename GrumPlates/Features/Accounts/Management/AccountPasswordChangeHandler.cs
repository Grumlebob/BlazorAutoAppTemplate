using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;
using System.Security.Claims;
using GrumPlates.Core.Features.Accounts.Contracts;
using GrumPlates.Features.Accounts.Security;
using Microsoft.AspNetCore.Identity;
using static GrumPlates.Features.Accounts.Security.AccountResults;

namespace GrumPlates.Features.Accounts.Management;

internal sealed class AccountPasswordChangeHandler(
    UserManager<ApplicationUser> users,
    SignInManager<ApplicationUser> signIn,
    AccountMutationTransactions transactions)
{
    public async Task<IResult> ChangePasswordAsync(AccountChangePasswordRequest request, ClaimsPrincipal principal, CancellationToken cancellationToken)
    {
        var userId = users.GetUserId(principal);
        if (string.IsNullOrEmpty(userId)) return Denied();
        var (response, committed) = await transactions.ExecuteAsync(userId, async (attempt, user) =>
        {
            var passwordCheck = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
            if (!passwordCheck.Succeeded) return (Denied(), true);
            var result = await attempt.Users.ChangePasswordAsync(user, request.Password, request.NewPassword);
            if (!result.Succeeded) return (IdentityFailure(result, "newPassword"), false);
            result = await attempt.Users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (IdentityFailure(result), false);
            return (Success("Password changed. Sign in again."), true);
        }, cancellationToken, principal: principal);
        if (committed && response is IStatusCodeHttpResult { StatusCode: StatusCodes.Status200OK }) await signIn.SignOutAsync();
        return response;
    }
}
