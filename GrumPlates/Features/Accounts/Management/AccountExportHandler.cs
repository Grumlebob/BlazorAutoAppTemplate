using System.Security.Claims;
using GrumPlates.Core.Features.Accounts.Contracts;
using GrumPlates.Features.Accounts.Security;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using static GrumPlates.Features.Accounts.Security.AccountResults;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Features.Accounts.Management;

internal sealed class AccountExportHandler(
    UserManager<ApplicationUser> users,
    AccountMutationTransactions transactions,
    IOptions<Microsoft.AspNetCore.Http.Json.JsonOptions> jsonOptions)
{
    public async Task<IResult> ExportAsync(AccountPasswordRequest request, ClaimsPrincipal principal, CancellationToken cancellationToken)
    {
        var userId = users.GetUserId(principal);
        if (string.IsNullOrEmpty(userId)) return SessionRequired();
        try
        {
            var (response, _) = await transactions.ExecuteAsync(userId, async (attempt, user) =>
            {
                var proof = await attempt.SignIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
                if (!proof.Succeeded) return (Denied(), true);

                var books = await attempt.Db.UserBooks.AsNoTracking()
                    .Where(book => book.OwnerUserId == user.Id)
                    .OrderBy(book => book.BookId)
                    .Take(MaximumExportRecords + 1)
                    .Select(book => new AccountExportBook(book.BookId, book.Book.Title, book.Book.Author, book.Book.Url))
                    .ToListAsync(cancellationToken);
                if (books.Count > MaximumExportRecords) return (ExportTooLarge(), true);

                var profile = new AccountProfile(user.Id, user.Email ?? "", (await attempt.Users.GetRolesAsync(user)).ToArray());
                var export = new AccountExport(profile, books);
                var bytes = System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(export, jsonOptions.Value.SerializerOptions);
                return (bytes.Length > MaximumExportBytes ? ExportTooLarge() : Results.Ok(export), true);
            }, cancellationToken, principal: principal);
            return response;
        }
        catch (Exception exception) when (IsPersistenceFailure(exception))
        {
            return DeliveryUnavailable();
        }
    }
}
