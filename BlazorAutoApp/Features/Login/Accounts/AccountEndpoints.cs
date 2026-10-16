using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Infrastructure.Hosting;
using BlazorAutoApp.Features.Login.Accounts.Session;
using BlazorAutoApp.Features.Login.Accounts.Security;

namespace BlazorAutoApp.Features.Login.Accounts;

internal static class AccountEndpoints
{
    public static IEndpointRouteBuilder MapAccountEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/auth").WithTags("Accounts")
            .WithPrivateNoStoreResponses()
            .WithMetadata(new AccountRequestProtection());

        group.MapGet("/session", (AccountSessionOperations accounts) => accounts.SessionAsync())
            .WithName("AccountSession").Produces<AccountSession>()
            .RequireRateLimiting(AppRateLimiting.ApiPolicyName)
            .Produces<AccountProblemDetails>(429, "application/problem+json")
            .Produces<AccountProblemDetails>(503, "application/problem+json");
        Message(group.MapPost("/login", (AccountLoginRequest request, AccountSessionOperations accounts) => accounts.LoginAsync(request)), "AccountLogin", 200, 401);
        Message(group.MapPost("/logout", (AccountSessionOperations accounts) => accounts.LogoutAsync()).WithMetadata(new ExpectedAccountUser()), "AccountLogout", 200, 401, 409);
        Message(group.MapPost("/logout-all", (AccountPasswordRequest request, AccountOperations accounts) => accounts.LogoutAllAsync(request)).WithMetadata(new ExpectedAccountUser()), "AccountLogoutAll", 200, 401, 409);
        Accepted(group.MapPost("/register", (AccountRegisterRequest request, AccountOperations accounts) => accounts.RegisterAsync(request)), "AccountRegister", 403, 503);
        Accepted(group.MapPost("/resend-confirmation", (AccountEmailRequest request, AccountOperations accounts) => accounts.ResendAsync(request)), "AccountResendConfirmation", 403, 503);
        Message(group.MapPost("/confirm-email", (AccountConfirmEmailRequest request, AccountOperations accounts) => accounts.ConfirmAsync(request)), "AccountConfirmEmail", 200, 400, 403);
        Accepted(group.MapPost("/forgot-password", (AccountEmailRequest request, AccountOperations accounts) => accounts.ForgotAsync(request)), "AccountForgotPassword", 403, 503);
        Message(group.MapPost("/reset-password", (AccountResetPasswordRequest request, AccountOperations accounts) => accounts.ResetAsync(request)), "AccountResetPassword", 200, 403);
        Message(group.MapPost("/change-password", (AccountChangePasswordRequest request, AccountOperations accounts) => accounts.ChangePasswordAsync(request)).WithMetadata(new ExpectedAccountUser()), "AccountChangePassword", 200, 401, 409);
        Accepted(group.MapPost("/change-email", (AccountChangeEmailRequest request, AccountOperations accounts) => accounts.ChangeEmailAsync(request)).WithMetadata(new ExpectedAccountUser()), "AccountChangeEmail", 401, 403, 409, 503);
        Message(group.MapPost("/confirm-email-change", (AccountConfirmEmailChangeRequest request, AccountOperations accounts) => accounts.ConfirmEmailChangeAsync(request)), "AccountConfirmEmailChange", 200, 403, 409);
        Write(group.MapPost("/export", (AccountPasswordRequest request, AccountOperations accounts) => accounts.ExportAsync(request))
            .WithMetadata(new ExpectedAccountUser()), "AccountExport", 401, 409, 413, 503)
            .Produces<AccountExport>();
        Message(group.MapPost("/delete", (AccountPasswordRequest request, AccountOperations accounts) => accounts.DeleteAsync(request)).WithMetadata(new ExpectedAccountUser()), "AccountDelete", 200, 401, 409, 503);
        RejectUnsupportedReads(group);
        return routes;
    }

    private static void RejectUnsupportedReads(RouteGroupBuilder group)
    {
        string[] postOnlyPaths =
        [
            "/login", "/logout", "/logout-all", "/register", "/resend-confirmation", "/confirm-email",
            "/forgot-password", "/reset-password", "/change-password", "/change-email",
            "/confirm-email-change", "/export", "/delete"
        ];

        foreach (var path in postOnlyPaths)
        {
            group.MapMethods(path, [HttpMethods.Get, HttpMethods.Head], async (HttpContext context) =>
            {
                context.Response.Headers.Allow = "POST";
                await AccountProblem.Create(StatusCodes.Status405MethodNotAllowed, "MethodNotAllowed",
                    "Method not allowed", "This account operation accepts POST requests only.").ExecuteAsync(context);
            }).ExcludeFromDescription();
        }
    }

    private static void Message(RouteHandlerBuilder endpoint, string name, int successStatus, params int[] errors) =>
        Write(endpoint, name, errors).Produces<AccountMessage>(successStatus);

    private static void Accepted(RouteHandlerBuilder endpoint, string name, params int[] errors) =>
        Write(endpoint, name, errors).Produces<AccountMessage>(StatusCodes.Status202Accepted);

    private static RouteHandlerBuilder Write(RouteHandlerBuilder endpoint, string name, params int[] errors)
    {
        var builder = endpoint.RequireRateLimiting(AppRateLimiting.AccountWritePolicyName).WithName(name);
        var statusCodes = new HashSet<int>([400, 413, 415, 429, 503]);
        statusCodes.UnionWith(errors);
        foreach (var statusCode in statusCodes)
        {
            builder.Produces<AccountProblemDetails>(statusCode, "application/problem+json");
        }
        return builder;
    }
}
