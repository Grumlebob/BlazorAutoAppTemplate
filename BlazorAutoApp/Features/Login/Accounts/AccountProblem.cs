using Microsoft.AspNetCore.Mvc;

namespace BlazorAutoApp.Features.Login.Accounts;

internal sealed class AccountProblemDetails : ValidationProblemDetails
{
    public string Code { get; init; } = "RequestInvalid";
}

internal static class AccountProblem
{
    public static IResult Create(int status, string code, string title, string? detail = null) =>
        Results.Problem(statusCode: status, title: title, detail: detail,
            extensions: new Dictionary<string, object?> { ["code"] = code });

    public static IResult Validation(
        int status,
        string code,
        string title,
        string detail,
        IDictionary<string, string[]> errors)
    {
        return Results.Problem(statusCode: status, title: title, detail: detail,
            extensions: new Dictionary<string, object?>
            {
                ["code"] = code,
                ["errors"] = errors
            });
    }
}
