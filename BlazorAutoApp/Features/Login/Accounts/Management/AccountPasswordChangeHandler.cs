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

namespace BlazorAutoApp.Features.Login.Accounts.Management;

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
            if (user.TwoFactorEnabled) return (Denied(), false);
            var passwordCheck = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
            if (!passwordCheck.Succeeded) return (Denied(), true);
            var result = await attempt.Users.ChangePasswordAsync(user, request.Password, request.NewPassword);
            if (!result.Succeeded) return (Check(result, ""), false);
            result = await attempt.Users.UpdateSecurityStampAsync(user);
            if (!result.Succeeded) return (Check(result, ""), false);
            return (Success("Password changed. Sign in again."), true);
        }, cancellationToken, principal: principal);
        if (committed && response is IStatusCodeHttpResult { StatusCode: StatusCodes.Status200OK }) await signIn.SignOutAsync();
        return response;
    }
}
