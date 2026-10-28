using System.Data.Common;
using GrumPlates.Core.Features.Accounts.Contracts;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;

namespace GrumPlates.Features.Accounts.Security;

internal static class AccountResults
{
    public static IResult Success(string message) => Results.Ok(new AccountMessage(message));
    public static IResult Accepted(string message) => Results.Accepted(value: new AccountMessage(message));
    public static IResult InvalidToken() =>
        AccountProblem.Create(400, "TokenInvalid", "The link could not be completed", "The link is invalid, expired or unavailable.");
    public static IResult Denied() =>
        AccountProblem.Create(401, "CredentialsInvalid", "Sign-in failed", "Check your credentials and account confirmation, then try again.");
    public static IResult EmailDisabled() =>
        AccountProblem.Create(403, "CapabilityDisabled", "This account operation is unavailable");
    public static IResult SessionRequired() =>
        AccountProblem.Create(401, "AuthenticationRequired", "Sign-in required");
    public static IResult DeliveryUnavailable() =>
        AccountProblem.Create(503, "AccountServiceUnavailable", "Account requests are temporarily unavailable", "Please try again later.");
    public static IResult Conflict() =>
        AccountProblem.Create(409, "AccountConflict", "The account could not be updated", "The request conflicts with the current account state.");
    public static IResult ExportTooLarge() =>
        AccountProblem.Create(413, "ExportTooLarge", "Account export too large", "The account data exceeds the export limits.");
    public const string PublicEmailResponse = "Request received. Check your email if applicable; use resend if it does not arrive.";
    public const int MaximumExportRecords = 10_000;
    public const int MaximumExportBytes = 10 * 1024 * 1024;

    public static IResult IdentityFailure(IdentityResult result, string? passwordField = null)
    {
        var codes = result.Errors.Select(error => error.Code).ToArray();
        if (codes.Any(code => code is "DuplicateEmail" or "DuplicateUserName"))
        {
            return Conflict();
        }
        if (codes.Any(code => code.StartsWith("Password", StringComparison.Ordinal)) || passwordField is not null)
        {
            return AccountProblem.Validation(400, "PasswordRejected", "Password rejected", "Choose a password that meets the account password policy.",
                new Dictionary<string, string[]> { [passwordField ?? "password"] = ["The password does not meet the account password policy."] });
        }
        return AccountProblem.Validation(400, "RequestInvalid", "Account request failed", "The request could not be completed.",
            new Dictionary<string, string[]> { ["account"] = ["The request could not be completed."] });
    }

    public static bool IsPersistenceFailure(Exception exception) =>
        exception is DbException or DbUpdateException or TimeoutException or RetryLimitExceededException;
}
