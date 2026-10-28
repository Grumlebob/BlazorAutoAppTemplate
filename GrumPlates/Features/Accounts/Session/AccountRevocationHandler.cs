using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;
using System.Security.Claims;
using GrumPlates.Core.Features.Accounts.Contracts;
using GrumPlates.Features.Accounts.Security;
using Microsoft.AspNetCore.Identity;
using static GrumPlates.Features.Accounts.Security.AccountResults;

namespace GrumPlates.Features.Accounts.Session;

internal sealed class AccountRevocationHandler(
    UserManager<ApplicationUser> users,
    AccountMutationTransactions transactions,
    AccountSessionOperations sessions)
{
    public async Task<IResult> LogoutAllAsync(AccountPasswordRequest request, ClaimsPrincipal principal, CancellationToken cancellationToken)
    {
        var userId = users.GetUserId(principal);
        if (string.IsNullOrEmpty(userId)) return Denied();
        var (response, committed) = await transactions.ExecuteAsync(userId, async (attempt, user) =>
        {
            var passwordCheck = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
            if (!passwordCheck.Succeeded) return (Denied(), true);
            var result = await attempt.Users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (IdentityFailure(result), false);
            return (Success("All sessions were signed out."), true);
        }, cancellationToken, principal: principal);
        return committed && response is IStatusCodeHttpResult { StatusCode: StatusCodes.Status200OK }
            ? await sessions.LogoutAsync()
            : response;
    }
}
