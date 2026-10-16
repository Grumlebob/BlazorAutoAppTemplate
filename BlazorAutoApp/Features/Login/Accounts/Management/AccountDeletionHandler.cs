using System.Security.Claims;
using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts.Security;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using static BlazorAutoApp.Features.Login.Accounts.Security.AccountResults;

namespace BlazorAutoApp.Features.Login.Accounts.Management;

internal sealed class AccountDeletionHandler(
    UserManager<ApplicationUser> users,
    SignInManager<ApplicationUser> signIn,
    AccountMutationTransactions transactions)
{
    public async Task<IResult> DeleteAsync(AccountPasswordRequest request, ClaimsPrincipal principal, CancellationToken cancellationToken)
    {
        var userId = users.GetUserId(principal);
        if (string.IsNullOrEmpty(userId)) return SessionRequired();
        try
        {
            var (response, committed) = await transactions.ExecuteAsync(userId, async (attempt, user) =>
            {
                var proof = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
                if (!proof.Succeeded) return (Denied(), true);

                await attempt.Db.AccountOutbox
                    .Where(message => message.UserId == user.Id && (message.Status == "Pending" || message.Status == "Leased"))
                    .ExecuteUpdateAsync(update => update
                        .SetProperty(message => message.Status, "Cancelled")
                        .SetProperty(message => message.ProtectedPayload, "")
                        .SetProperty(message => message.FailureCode, "AccountDeleted")
                        .SetProperty(message => message.LeaseId, (string?)null)
                        .SetProperty(message => message.LeaseUntilUtc, (DateTimeOffset?)null), cancellationToken);

                var privateBooks = await attempt.Db.UserBooks
                    .Where(mapping => mapping.OwnerUserId == user.Id
                        && !attempt.Db.AuthorBooks.Any(catalog => catalog.BookId == mapping.BookId))
                    .Select(mapping => mapping.Book)
                    .ToListAsync(cancellationToken);
                attempt.Db.Books.RemoveRange(privateBooks);
                await attempt.Db.SaveChangesAsync(cancellationToken);

                var result = await attempt.Users.DeleteAsync(user);
                if (!result.Succeeded) return (Check(result, ""), false);
                return (Success("Account deleted."), true);
            }, cancellationToken, principal: principal, verifyUserDeleted: true);
            if (committed && response is IStatusCodeHttpResult { StatusCode: StatusCodes.Status200OK }) await signIn.SignOutAsync();
            return response;
        }
        catch (Exception exception) when (IsPersistenceFailure(exception))
        {
            return DeliveryUnavailable();
        }
    }
}
