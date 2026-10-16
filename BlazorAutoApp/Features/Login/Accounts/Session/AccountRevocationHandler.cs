using System.Security.Claims;
using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts.Security;
using Microsoft.AspNetCore.Identity;
using static BlazorAutoApp.Features.Login.Accounts.Security.AccountResults;

namespace BlazorAutoApp.Features.Login.Accounts.Session;

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
